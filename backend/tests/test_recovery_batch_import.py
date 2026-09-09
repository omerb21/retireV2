"""One atomic clearinghouse engine, including N=1 and sparse cross-file facts."""
import asyncio
import hashlib
import inspect
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
from threading import Barrier
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException, UploadFile
from sqlalchemy import event, func, select, text
from sqlalchemy.orm import Session

from app.models.pension_product import COMPONENT_CODES, PensionProduct, PensionProductComponent, PensionProductSourceLink, PensionProductAuditEvent
from app.services import pension_product_import_service as service
from app.services.pension_product_service import PensionProductError, delete_product
from test_recovery_pension_products import engine, api, source, layer

PATH = "/api/clients/1/pension-products/imports"


def ingest(engine, files, client_id=1):
    with Session(engine) as db, db.begin():
        return service.import_source_batch(db, client_id, files, "test")


def snapshot(engine):
    with engine.connect() as connection:
        return {table: connection.execute(text(f"SELECT * FROM {table} ORDER BY 1")).all()
                for table in ("pension_products", "pension_product_components", "pension_product_source_links", "pension_product_audit_events")}


def test_complementary_components_metadata_union_and_evidence(engine):
    a = source(layers=layer("2", "1", "10"), fields="<SHEM-MAASIK>ב</SHEM-MAASIK><TOTAL-CHISACHON-MTZBR>100</TOTAL-CHISACHON-MTZBR>")
    b = source(layers=layer("3", "1", "20"), fields="<SHEM-MAASIK>א</SHEM-MAASIK><SHEM-MAASIK>ב</SHEM-MAASIK>")
    result = ingest(engine, [("a.xml", a), ("b.dat", b)])
    assert result["file_count"] == 2 and result["product_count"] == 1
    product = result["products"][0]
    assert product["historical_employers"] == ["א", "ב"]
    assert product["reported_product_total"] == "100.00"
    assert product["components"][COMPONENT_CODES[5]] == "10.00"
    assert product["components"][COMPONENT_CODES[8]] == "20.00"
    assert len(product["components"]) == 11
    assert product["reconciliation"]["product_discrepancy"] == "70.00"
    with Session(engine) as db:
        links = db.scalars(select(PensionProductSourceLink)).all()
        assert {row.raw_content for row in links} == {a, b}
        assert {row.filename for row in links} == {"a.xml", "b.dat"}
        assert {row.checksum for row in links} == {hashlib.sha256(raw).hexdigest() for raw in (a, b)}
        assert {row.batch_identity for row in links} == {result["batch_identity"]}
        assert all(row.diagnostics and row.statement_date.isoformat() == "2026-09-01" for row in links)
        for prefix in ("m02_intake_records", "m03_review_revisions", "m04_classification_revisions", "m05_ledger_revisions"):
            assert db.scalar(text(f"SELECT count(*) FROM {prefix}")) == 0


def test_identical_facts_deduplicate_without_cross_file_sum(engine):
    a = source(layers=layer("2", "1", "10") + layer("2", "1", "5"))
    b = source(layers=layer("2", "1", "15"), fields="<Note>different raw evidence</Note>")
    result = ingest(engine, [("a.xml", a), ("b.xml", b)])
    assert result["product_count"] == 1
    assert result["products"][0]["components"][COMPONENT_CODES[5]] == "15.00"
    assert len(result["products"][0]["components"]) == 11


@pytest.mark.parametrize("other", ["component", "name", "type", "total", "rewards", "severance", "statement", "start"])
def test_cross_file_conflict_fails_before_professional_write(engine, other):
    fields = "<TOTAL-CHISACHON-MTZBR>100</TOTAL-CHISACHON-MTZBR><YITRAT-KASPEY-TAGMULIM>30</YITRAT-KASPEY-TAGMULIM><YITRAT-PITZUIM>70</YITRAT-PITZUIM><TAARICH-TCHILA>20000101</TAARICH-TCHILA>"
    a = source(layers=layer("2", "1", "10"), fields=fields)
    replacements = {
        "component": (b">10<", b">11<"), "name": ("תכנית".encode(), "אחרת".encode()),
        "type": (b">3<", b">4<"), "total": (b">100<", b">101<"), "rewards": (b">30<", b">31<"),
        "severance": (b">70<", b">71<"), "statement": (b"20260901", b"20260902"),
        "start": (b"20000101", b"20000102"),
    }
    b = a.replace(*replacements[other])
    before = snapshot(engine)
    writes = []
    def capture(conn, cursor, statement, params, context, many):
        if statement.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE")) and "pension_product" in statement:
            writes.append(statement)
    event.listen(engine, "before_cursor_execute", capture)
    try:
        with pytest.raises(PensionProductError) as failure:
            ingest(engine, [("left.xml", a), ("right.xml", b)])
        assert failure.value.code == "SOURCE_BATCH_CONFLICT" and failure.value.status_code == 409
        assert "left.xml" in failure.value.message and "right.xml" in failure.value.message
        assert writes == [] and snapshot(engine) == before
    finally:
        event.remove(engine, "before_cursor_execute", capture)


def test_explicit_zero_conflicts_but_absence_does_not(engine):
    zero = source(layers=layer("2", "1", "0"))
    absent = source()
    positive = source(layers=layer("2", "1", "1"))
    assert service._prepare_batch([("zero.xml", zero), ("absent.xml", absent)])[1][0]["components"][COMPONENT_CODES[5]] == 0
    with pytest.raises(PensionProductError, match="סותרים"):
        ingest(engine, [("zero.xml", zero), ("positive.xml", positive)])


def test_unknown_balances_are_diagnostic_not_distributed(engine):
    result = ingest(engine, [("unknown.xml", source(layers=layer("99", "99", "999"), fields="<TOTAL-CHISACHON-MTZBR>500</TOTAL-CHISACHON-MTZBR>"))])
    assert set(result["products"][0]["components"].values()) == {"0.00"}
    assert result["products"][0]["reconciliation"]["product_discrepancy"] == "500.00"
    assert any(d["code"] == "unmapped_layer" for entry in result["diagnostics"] for d in entry["diagnostics"])


def test_exact_retry_identity_order_filename_and_all_rows_unchanged(engine):
    files = [("a.xml", source()), ("b.xml", source(account="B"))]
    first = ingest(engine, files)
    before = snapshot(engine)
    second = ingest(engine, [("renamed-b.dat", files[1][1]), ("renamed-a.dat", files[0][1])])
    expected = hashlib.sha256(("pension-source-batch-v1" + "".join(sorted(hashlib.sha256(raw).hexdigest() for _, raw in files))).encode()).hexdigest()
    assert first["batch_identity"] == second["batch_identity"] == expected
    assert first["product_count"] == second["product_count"] == 2
    assert snapshot(engine) == before


@pytest.mark.parametrize("mode", ["subset", "superset", "mixed"])
def test_partial_overlap_no_mutation(engine, mode):
    a, b, c = ("a.xml", source()), ("b.xml", source(account="B")), ("c.xml", source(account="C"))
    ingest(engine, [a, b])
    before = snapshot(engine)
    files = {"subset": [a], "superset": [a, b, c], "mixed": [a, c]}[mode]
    with pytest.raises(PensionProductError) as failure:
        ingest(engine, files)
    assert failure.value.code == "PARTIAL_OVERLAP_SOURCE_BATCH" and failure.value.status_code == 409
    assert snapshot(engine) == before


def test_deleted_product_retry_cannot_resurrect(engine):
    files = [("a.xml", source()), ("b.xml", source(account="B"))]
    first = ingest(engine, files)
    with Session(engine) as db, db.begin():
        delete_product(db, 1, first["products"][0]["product_id"], 1, "test")
    before = snapshot(engine)
    with pytest.raises(PensionProductError) as failure:
        ingest(engine, files)
    assert failure.value.code == "DELETED_SOURCE_PRODUCT" and snapshot(engine) == before


def test_client_scoped_batch_identity(engine):
    files = [("a.xml", source())]
    first, second = ingest(engine, files), ingest(engine, files, 2)
    assert first["batch_identity"] == second["batch_identity"]
    assert first["products"][0]["product_id"] != second["products"][0]["product_id"]


@pytest.mark.parametrize("bad,code", [(b"bad", "INVALID_SOURCE_XML"), (b"<Root/>", "NO_SOURCE_ACCOUNTS"), (b"<Account><Account/></Account>", "AMBIGUOUS_ACCOUNT_STRUCTURE"), (b"", "INVALID_SOURCE_SIZE"), (b"x" * 26_214_401, "INVALID_SOURCE_SIZE")], ids=["xml", "no-account", "nested", "empty", "oversize"])
def test_bad_file_batch_api_atomic_and_names_file(api, engine, bad, code):
    before = snapshot(engine)
    result = api.post(PATH, files=[("files", ("good.xml", source())), ("files", ("bad.dat", bad))])
    assert result.status_code == 422 and result.json()["detail"]["code"] == code
    assert "bad.dat" in result.json()["detail"]["message"]
    assert snapshot(engine) == before


def test_duplicate_selected_checksum_rejected(api, engine):
    result = api.post(PATH, files=[("files", ("a.xml", source())), ("files", ("renamed.dat", source()))])
    assert result.status_code == 422 and result.json()["detail"]["code"] == "DUPLICATE_BATCH_FILE"
    assert all(not rows for rows in snapshot(engine).values())


def test_empty_and_old_multipart_contract_rejected(api):
    assert api.post(PATH).status_code == 422
    assert api.post(PATH, files={"file": ("old.xml", source())}).status_code == 422
    with pytest.raises(PensionProductError) as failure:
        service._prepare_batch([])
    assert failure.value.code == "EMPTY_SOURCE_BATCH"


def test_api_batch_one_lock_one_commit(api, engine, monkeypatch):
    locks, commits = [], []
    original = service.lock_client
    def lock(db, client_id):
        locks.append(client_id)
        return original(db, client_id)
    monkeypatch.setattr(service, "lock_client", lock)
    def committed(session):
        commits.append(1)
    event.listen(Session, "after_commit", committed)
    try:
        result = api.post(PATH, files=[("files", ("a.xml", source())), ("files", ("b.xml", source(account="B")))])
    finally:
        event.remove(Session, "after_commit", committed)
    assert result.status_code == 200, result.text
    assert result.json()["file_count"] == result.json()["product_count"] == 2
    assert locks == [1] and commits == [1]


def test_currentization_preflight_and_atomic_newer_batch(engine):
    ingest(engine, [("a.xml", source()), ("b.xml", source(account="B"))])
    before = snapshot(engine)
    with pytest.raises(PensionProductError) as failure:
        ingest(engine, [("new-a.xml", source(statement="20260902")), ("stale-b.xml", source(account="B", statement="20260801"))])
    assert failure.value.code == "SOURCE_NOT_NEWER" and snapshot(engine) == before
    result = ingest(engine, [("new-a.xml", source(statement="20260902")), ("new-b.xml", source(account="B", statement="20260902"))])
    assert {p["version"] for p in result["products"]} == {2}
    assert {p["statement_date"] for p in result["products"]} == {"2026-09-02"}


def test_late_database_failure_rolls_back_every_product(api, engine):
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE TRIGGER batch_injected_failure BEFORE INSERT ON pension_product_source_links WHEN (SELECT count(*) FROM pension_product_source_links)>0 BEGIN SELECT RAISE(ABORT,'injected'); END")
    before = snapshot(engine)
    result = api.post(PATH, files=[("files", ("a.xml", source())), ("files", ("b.xml", source(account="B")))])
    assert result.status_code == 409 and snapshot(engine) == before


@pytest.mark.parametrize("failure_mode", ["none", "parse", "read"])
def test_every_upload_closed_on_success_or_failure(engine, failure_mode):
    from app.api.pension_product_routes import import_products
    uploads = [UploadFile(filename="a.xml", file=BytesIO(source())), UploadFile(filename="b.xml", file=BytesIO(b"invalid" if failure_mode == "parse" else source(account="B")))]
    if failure_mode == "read":
        uploads[0].read = AsyncMock(side_effect=OSError("read failed"))
    with Session(engine) as db:
        if failure_mode == "none":
            assert asyncio.run(import_products(1, uploads, db))["file_count"] == 2
        else:
            with pytest.raises((HTTPException, OSError)):
                asyncio.run(import_products(1, uploads, db))
    assert all(upload.file.closed for upload in uploads)


def test_concurrent_identical_batches_have_one_authority(engine):
    barrier = Barrier(2)
    files = [("a.xml", source()), ("b.xml", source(account="B"))]
    def run(_):
        barrier.wait(timeout=10)
        return ingest(engine, files)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, range(2)))
    assert results[0]["batch_identity"] == results[1]["batch_identity"]
    with Session(engine) as db:
        for model, count in [(PensionProduct, 2), (PensionProductComponent, 22), (PensionProductSourceLink, 2), (PensionProductAuditEvent, 2)]:
            assert db.scalar(select(func.count()).select_from(model)) == count


def test_only_one_registered_import_endpoint_and_no_single_file_engine():
    from app.main import app
    routes = [route for route in app.routes if "POST" in getattr(route, "methods", set()) and route.path.endswith("/pension-products/imports")]
    assert len(routes) == 1
    assert not hasattr(service, "import_source") and not hasattr(service, "parse_source")
    assert list(inspect.signature(service.import_source_batch).parameters) == ["db", "client_id", "files", "actor"]
    root = Path(__file__).resolve().parents[2]
    screen = (root / "frontend/src/pages/PensionProductsScreen.tsx").read_text(encoding="utf-8")
    api_source = (root / "frontend/src/api/pensionProductsApi.ts").read_text(encoding="utf-8")
    assert "files?.[0]" not in screen and "useState<File |" not in screen
    assert 'body.append("file",' not in api_source and 'body.append("files", file)' in api_source
