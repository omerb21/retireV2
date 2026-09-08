from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, event, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base, load_all_models
from app.models.client import Client
from app.models.pension_product import COMPONENT_CODES, PensionProduct, PensionProductAuditEvent, PensionProductComponent, PensionProductSourceLink
from app.schemas.pension_product import ProductCreate, ProductUpdate, SaveSelected, exact_money
from app.services.canonical_pension_source_reader import current_products, conversion_source_availability
from app.services.pension_product_import_service import SEVERANCE_TAGS, import_source, parse_source, rewards_component
from app.services.pension_product_reconciliation import reconcile
from app.services.pension_product_service import PensionProductError, create_product, delete_product, product_response, save_selected, update_product


@pytest.fixture
def engine(tmp_path):
    load_all_models()
    engine = create_engine(f"sqlite:///{tmp_path / 'canonical.db'}", connect_args={"timeout": 20})
    @event.listens_for(engine, "connect")
    def foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(engine)
    with Session(engine) as db, db.begin():
        db.add(Client(client_id=1, display_name="בדיקה", id_number="123456789"))
        db.add(Client(client_id=2, display_name="נפרד", id_number="987654321"))
    yield engine
    engine.dispose()


def create(db):
    return create_product(db, 1, ProductCreate(product_name="תכנית", product_type="קופת גמל", reported_product_total="123.45"), "test")


def edit(product, value="1.01", version=None):
    return ProductUpdate(product_name=product.product_name, product_type=product.product_type, reported_product_total="123.45", expected_version=product.version if version is None else version, components=dict.fromkeys(COMPONENT_CODES, value))


def source(*, layers="", fields="", account="A", statement="20260901"):
    return f'<Root><SHEM-YATZRAN>גוף מנהל</SHEM-YATZRAN><Account><MISPAR-HESHBON>{account}</MISPAR-HESHBON><SHEM-TOCHNIT>תכנית</SHEM-TOCHNIT><SUG-MUTZAR>3</SUG-MUTZAR><TAARICH-NECHONUT-YITROT>{statement}</TAARICH-NECHONUT-YITROT>{fields}<BlockItrot>{layers}</BlockItrot></Account></Root>'.encode()


def layer(role, period, amount="12.34"):
    return f'<PerutYitraLeTkufa><REKIV-ITRA-LETKUFA>{role}</REKIV-ITRA-LETKUFA><KOD-TECHULAT-SHICHVA>{period}</KOD-TECHULAT-SHICHVA><SACH-ITRA-LESHICHVA-BESHACH>{amount}</SACH-ITRA-LESHICHVA-BESHACH></PerutYitraLeTkufa>'


def test_manual_zero_ontology_and_separate_totals(engine):
    with Session(engine) as db, db.begin():
        product = create(db)
        response = product_response(db, product)
        assert len(response["components"]) == 11
        assert set(response["components"].values()) == {"0.00"}
        assert response["reported_product_total"] == "123.45"
        assert response["reported_rewards_total"] is None
        assert response["reported_severance_total"] is None
        assert response["reconciliation"]["product_discrepancy"] == "123.45"


@pytest.mark.parametrize("code", [COMPONENT_CODES[0], "contribution_component", "תגמולים"])
def test_database_uniqueness_and_fixed_ontology(engine, code):
    with Session(engine) as db, db.begin():
        product_id = create(db).product_id
    with pytest.raises(IntegrityError), Session(engine) as db, db.begin():
        db.add(PensionProductComponent(component_id="duplicate", product_id=product_id, component_code=code, balance=1))
        db.flush()


@pytest.mark.parametrize("role,person", [("2", "עובד"), ("8", "עובד"), ("3", "מעביד"), ("9", "מעביד")])
@pytest.mark.parametrize("period,suffix", [("1", "עד_2000"), ("2", "אחרי_2000"), ("7", "אחרי_2008_לא_משלמת"), ("9", "אחרי_2008_לא_משלמת"), ("13", "אחרי_2008_לא_משלמת")])
def test_exact_rewards_mapping(role, person, period, suffix):
    code = f"תגמולי_{person}_{suffix}"
    assert rewards_component(role, period) == code
    account = parse_source(source(layers=layer(role, period)))[0]
    assert account["components"][code] == Decimal("12.34")
    assert sum(account["components"].values()) == Decimal("12.34")


@pytest.mark.parametrize("tag,code", SEVERANCE_TAGS.items())
def test_exact_severance_mapping(tag, code):
    account = parse_source(source(fields=f"<{tag}>19.83</{tag}>"))[0]
    assert account["components"][code] == Decimal("19.83")
    assert sum(account["components"].values()) == Decimal("19.83")


@pytest.mark.parametrize("role,period", [("4", "1"), ("2", "99"), ("", "2"), ("7", "2"), ("10", "1"), ("11", "1")])
def test_unknown_mapping_no_generic_balance(role, period):
    account = parse_source(source(layers=layer(role, period)))[0]
    assert sum(account["components"].values()) == 0
    assert any(item["code"] == "unmapped_layer" for item in account["diagnostics"])
    assert set(account["components"]) == set(COMPONENT_CODES)


def test_three_reconciliations_no_mutation():
    balances = {code: Decimal("1.11") for code in COMPONENT_CODES}
    original = balances.copy()
    result = reconcile(balances, Decimal("100"), Decimal("20"), Decimal("30"))
    assert result == {"rewards_component_sum": Decimal("6.66"), "severance_component_sum": Decimal("5.55"), "product_component_sum": Decimal("12.21"), "rewards_discrepancy": Decimal("13.34"), "severance_discrepancy": Decimal("24.45"), "product_discrepancy": Decimal("87.79")}
    assert balances == original


@pytest.mark.parametrize("value", [1.01, True, "NaN", "Infinity", "1.001", "1000000000000000000"])
def test_no_float_rounding_or_out_of_range(value):
    with pytest.raises(ValueError):
        exact_money(value)


def test_direct_edit_and_stale_write(engine):
    with Session(engine) as db, db.begin():
        product_id = create(db).product_id
    with Session(engine) as db, db.begin():
        product = db.get(PensionProduct, product_id)
        update_product(db, 1, product_id, edit(product), "test")
        assert product.version == 2
        assert set(product_response(db, product)["components"].values()) == {"1.01"}
    with pytest.raises(PensionProductError, match="המוצר השתנה"), Session(engine) as db, db.begin():
        product = db.get(PensionProduct, product_id)
        update_product(db, 1, product_id, edit(product, "99", version=1), "test")
    with Session(engine) as db:
        assert db.get(PensionProduct, product_id).version == 2


def test_atomic_selected_preflight(engine):
    with Session(engine) as db, db.begin():
        first, second = create(db), create(db)
        ids = first.product_id, second.product_id
    with pytest.raises(PensionProductError), Session(engine) as db, db.begin():
        first, second = [db.get(PensionProduct, product_id) for product_id in ids]
        request = SaveSelected(products=[dict(edit(first).model_dump(), product_id=ids[0]), dict(edit(second, version=2).model_dump(), product_id=ids[1])])
        save_selected(db, 1, request, "test")
    with Session(engine) as db:
        assert [db.get(PensionProduct, product_id).version for product_id in ids] == [1, 1]
        assert set(db.scalars(select(PensionProductComponent.balance)).all()) == {Decimal("0.00")}


def test_delete_preserves_technical_history_and_isolation(engine):
    with Session(engine) as db, db.begin():
        product_id = create(db).product_id
    with pytest.raises(PensionProductError), Session(engine) as db, db.begin():
        delete_product(db, 2, product_id, 1, "test")
    with Session(engine) as db, db.begin():
        delete_product(db, 1, product_id, 1, "test")
    with Session(engine) as db:
        assert db.get(PensionProduct, product_id) is None
        assert db.scalar(select(func.count()).select_from(PensionProductComponent)) == 0
        assert db.scalar(select(func.count()).select_from(PensionProductAuditEvent)) == 2


def test_delete_restricts_downstream_fk_and_rolls_back(engine):
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE downstream_test (id INTEGER PRIMARY KEY, product_id VARCHAR(64) REFERENCES pension_products(product_id) ON DELETE RESTRICT)"))
    with Session(engine) as db, db.begin():
        product_id = create(db).product_id
        db.execute(text("INSERT INTO downstream_test(id, product_id) VALUES (1, :id)"), {"id": product_id})
    with pytest.raises(IntegrityError), Session(engine) as db, db.begin():
        delete_product(db, 1, product_id, 1, "test")
    with Session(engine) as db:
        assert len(product_response(db, db.get(PensionProduct, product_id))["components"]) == 11
        assert db.scalar(select(func.count()).select_from(PensionProductAuditEvent)) == 1


def test_import_idempotency_newer_and_raw_checksum(engine):
    raw = source(layers=layer("2", "1"))
    with Session(engine) as db, db.begin():
        product_id = import_source(db, 1, raw, "source.xml", "test")[0].product_id
    with Session(engine) as db, db.begin():
        assert import_source(db, 1, raw, "renamed.xml", "test")[0].product_id == product_id
        assert db.scalar(select(func.count()).select_from(PensionProductSourceLink)) == 1
    with Session(engine) as db, db.begin():
        product = import_source(db, 1, source(layers=layer("2", "1", "98.76"), statement="20260902"), "new.xml", "test")[0]
        assert product.product_id == product_id
        assert product.version == 2
        assert product_response(db, product)["components"][COMPONENT_CODES[5]] == "98.76"
    with Session(engine) as db:
        assert raw in db.scalars(select(PensionProductSourceLink.raw_content)).all()
        assert db.scalar(select(func.count()).select_from(PensionProductSourceLink)) == 2


def test_reader_queries_canonical_only_and_conversion_closed(engine):
    statements = []
    with Session(engine) as db, db.begin():
        create(db)
    def capture(conn, cursor, statement, params, context, executemany):
        statements.append(statement)
    event.listen(engine, "before_cursor_execute", capture)
    try:
        with Session(engine) as db:
            assert len(current_products(db, 1)) == 1
            assert conversion_source_availability(db, 1)["available"] is False
        assert all("m02_" not in sql and "m03_" not in sql and "m04_" not in sql and "m05_" not in sql for sql in statements)
    finally:
        event.remove(engine, "before_cursor_execute", capture)


@pytest.mark.parametrize("action", ["list_candidates", "start_conversion", "resolve_conversion", "review_warnings", "correct_coefficient", "supersede_conversion"])
def test_m06_actions_use_only_canonical_source_and_fail_closed(engine, action):
    from app.services import m06_conversion_service as m06

    with Session(engine) as db, db.begin():
        create(db)
    statements = []
    def capture(conn, cursor, statement, params, context, executemany):
        statements.append(statement.lower())
    event.listen(engine, "before_cursor_execute", capture)
    try:
        with Session(engine) as db, pytest.raises(m06.M06ConversionError) as failure:
            getattr(m06, action)(db, 1)
        assert failure.value.status_code == 409
        assert failure.value.code == "CANONICAL_CONVERSION_CONTRACT_NOT_IMPLEMENTED"
        assert any("pension_products" in sql for sql in statements)
        assert not any(prefix in sql for sql in statements for prefix in ("m02_", "m03_", "m04_", "m05_"))
        assert not any(sql.lstrip().startswith(("insert", "delete")) for sql in statements)
    finally:
        event.remove(engine, "before_cursor_execute", capture)


def test_m06_missing_client_has_deterministic_error(engine):
    from app.services.m06_conversion_service import M06ConversionError, list_candidates
    with Session(engine) as db, pytest.raises(M06ConversionError) as failure:
        list_candidates(db, 999999)
    assert failure.value.status_code == 404
    assert failure.value.code == "CLIENT_NOT_FOUND"


def test_concurrent_stale_updates_one_winner(engine):
    with Session(engine) as db, db.begin():
        product_id = create(db).product_id
    barrier = Barrier(2)
    def save(value):
        request = ProductUpdate(product_name="תכנית", product_type="קופה", reported_product_total="100", expected_version=1, components=dict.fromkeys(COMPONENT_CODES, value))
        barrier.wait(timeout=10)
        try:
            with Session(engine) as db, db.begin():
                update_product(db, 1, product_id, request, "test")
            return "saved"
        except PensionProductError as error:
            return error.code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(save, ["1.23", "4.56"]))
    assert sorted(results) == ["STALE_PRODUCT_VERSION", "saved"]
    with Session(engine) as db:
        assert db.get(PensionProduct, product_id).version == 2
        assert db.scalar(select(func.count()).select_from(PensionProductComponent)) == 11


def test_concurrent_identical_import_one_product(engine):
    barrier = Barrier(2)
    def ingest(_):
        barrier.wait(timeout=10)
        with Session(engine) as db, db.begin():
            return import_source(db, 1, source(), "same.xml", "test")[0].product_id
    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(ingest, range(2)))
    assert ids[0] == ids[1]
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(PensionProductComponent)) == 11
        assert db.scalar(select(func.count()).select_from(PensionProductSourceLink)) == 1


def test_full_precision_storage_without_float(engine):
    amount = "999999999999999999.99"
    with Session(engine) as db, db.begin():
        product = create_product(db, 1, ProductCreate(product_name="דיוק", product_type="קופה", reported_product_total=amount), "test")
        product_id = product.product_id
    with Session(engine) as db:
        product = db.get(PensionProduct, product_id)
        assert product_response(db, product)["reported_product_total"] == amount
        assert db.scalar(text("SELECT typeof(reported_product_total) FROM pension_products WHERE product_id=:id"), {"id": product_id}) == "text"


def test_nested_layer_total_not_product_summary():
    account = parse_source(source(layers="<PerutYitrot><KOD-SUG-HAFRASHA>2</KOD-SUG-HAFRASHA><TOTAL-CHISACHON-MTZBR>100</TOTAL-CHISACHON-MTZBR></PerutYitrot>"))[0]
    assert account["metadata"].reported_product_total is None
    assert sum(account["components"].values()) == 0


@pytest.fixture
def api(engine):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api.pension_product_routes import router
    from app.db.session import get_db
    application = FastAPI()
    application.include_router(router)
    def session():
        with Session(engine) as db:
            yield db
    application.dependency_overrides[get_db] = session
    with TestClient(application) as client:
        yield client


def test_api_direct_access_and_no_legacy_records(api, engine):
    path = "/api/clients/1/pension-products"
    response = api.post(path, json={"product_name": "תכנית", "product_type": "קופה", "reported_product_total": "123.45"})
    assert response.status_code == 201, response.text
    product = response.json()
    assert len(product["components"]) == 11
    assert api.get(path).json()[0]["product_id"] == product["product_id"]
    payload = {key: product[key] for key in ProductCreate.model_fields}
    payload.update(expected_version=1, components=dict.fromkeys(COMPONENT_CODES, "1.23"))
    assert api.put(f"{path}/{product['product_id']}", json=payload).status_code == 200
    assert api.put(f"{path}/{product['product_id']}", json=payload).status_code == 409
    assert api.delete(f"{path}/{product['product_id']}?expected_version=1").status_code == 409
    assert api.delete(f"{path}/{product['product_id']}?expected_version=2").status_code == 204
    with Session(engine) as db:
        for table in ("m02_intake_records", "m03_review_revisions", "m04_classification_revisions", "m05_ledger_revisions"):
            assert db.scalar(text(f"SELECT COUNT(*) FROM {table}")) == 0


def test_api_import_atomic_rollback(api, engine):
    path = "/api/clients/1/pension-products/imports"
    assert api.post(path, files={"file": ("source.xml", source(), "application/xml")}).status_code == 200
    # First account would be new; the second fails statement currentization.
    first = source(account="B").decode().split("<Account>", 1)[1].split("</Account>", 1)[0]
    second = source(statement="20260801").decode().split("<Account>", 1)[1].split("</Account>", 1)[0]
    raw = f"<Root><SHEM-YATZRAN>גוף מנהל</SHEM-YATZRAN><Account>{first}</Account><Account>{second}</Account></Root>".encode()
    assert api.post(path, files={"file": ("source.xml", raw, "application/xml")}).status_code == 409
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(PensionProduct)) == 1
        assert db.scalar(select(func.count()).select_from(PensionProductComponent)) == 11
        assert db.scalar(select(func.count()).select_from(PensionProductSourceLink)) == 1
