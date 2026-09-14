from datetime import date
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import event, select, text
from sqlalchemy.orm import Session
from app.main import app
from app.db.session import get_db
from app.models.canonical_manual_pension_source import CanonicalManualPensionSource as Manual
from app.models.pension_product import PensionProductComponent
from app.models.retirement_facts import CapitalAsset, RecurringIncome
from app.schemas.canonical_manual_pension_source import ManualPensionInput, ManualPensionUpdate, ManualPensionSupersede
from app.schemas.canonical_conversion import ReversalRequest
from app.services import canonical_manual_pension_service as manual
from app.services.professional_source_snapshot_service import snapshot
from app.services.canonical_component_conversion_service import execute, reverse
from app.services.pension_product_service import PensionProductError
from test_recovery_pension_products import engine
from test_canonical_component_conversion import seeded, request


def read(engine, client=1, **kwargs):
    with Session(engine) as db:
        return snapshot(db, client, **kwargs)


def facts(**kwargs):
    return ManualPensionInput(input_mode="entered", payer_name="משלם", monthly_amount="100.00",
        pension_start_date=date(2040, 1, 1), tax_treatment="taxable", indexation_method="none", **kwargs)


@pytest.mark.parametrize("mode,amount", [("entered", "0.00"), ("entered", "0.01"),
                                        ("calculated", "0.00"), ("calculated", "0.01")])
def test_manual_positive_basis_readiness(engine, mode, amount):
    assert_positive_basis_readiness(engine, mode, amount)


def assert_positive_basis_readiness(engine, mode, amount):
    payload = {**facts().model_dump(mode="json"), "input_mode": mode}
    payload.update({"monthly_amount": amount} if mode == "entered" else
                   {"monthly_amount": None, "balance": amount, "annuity_factor": "3"})
    def session():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[get_db] = session
    try:
        with TestClient(app) as client:
            response = client.post("/api/clients/1/canonical-pension-sources/manual", json=payload)
            assert response.status_code == 200, response.text
            sid = response.json()["manual_pension_source_id"]
            view = client.get("/api/clients/1/professional-source-snapshot").json()
        source = next(s for s in view["pension_sources"] if s["manual_pension_source_id"] == sid)
        assert source["visible"]
        assert source["calculation_ready"] == (Decimal(amount) > 0)
        field = "monthly_amount" if mode == "entered" else "balance"
        assert source[field] == amount
        assert source["missing_or_blocking_facts"] == ([] if Decimal(amount) > 0 else [field + "_not_positive"])
        assert source["amount_authority"] == (
            {"authority_kind": "entered_monthly_amount", "amount": amount} if mode == "entered" else
            {"authority_kind": "manual_balance_ratio", "numerator": amount, "denominator": "3"})
        # The positive 0.01/3 ratio stays exact, not a rounded zero authority.
        with Session(engine) as db:
            assert getattr(db.get(Manual, sid), field) == Decimal(amount)
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize("method,rate,code", [
    ("fixed", None, "fixed_indexation_rate_missing"),
    ("fixed", "-1", "fixed_indexation_rate_not_positive"),
    ("fixed", "0", "fixed_indexation_rate_not_positive"),
    ("fixed", "0.000000000000000000000000001", None),
    ("none", None, None), ("cpi", None, None),
])
def test_fixed_rate_readiness_v1(engine, method, rate, code):
    assert_fixed_rate_readiness(engine, method, rate, code)


def assert_fixed_rate_readiness(engine, method, rate, code):
    # Direct persistence also covers pre-correction negative source facts.
    with Session(engine) as db, db.begin():
        row = Manual(**facts().model_dump(), manual_pension_source_id="rate-case", client_id=1)
        row.indexation_method, row.fixed_indexation_rate = method, rate
        db.add(row)
    source = next(s for s in read(engine)["pension_sources"] if s["manual_pension_source_id"] == "rate-case")
    assert source["visible"] and source["calculation_ready"] == (code is None)
    assert source["missing_or_blocking_facts"] == ([] if code is None else [code])
    assert source["fixed_indexation_rate"] == rate
    assert source["amount_authority"] == {"authority_kind": "entered_monthly_amount", "amount": "100.00"}
    with Session(engine) as db:
        assert db.get(Manual, "rate-case").fixed_indexation_rate == rate


@pytest.mark.parametrize("changes", [
    {"monthly_amount": "-0.01"},
    {"input_mode": "calculated", "monthly_amount": None, "balance": "-0.01"},
    {"input_mode": "calculated", "monthly_amount": None, "balance": "1", "annuity_factor": "0"},
    {"input_mode": "calculated", "monthly_amount": None, "balance": "1", "annuity_factor": "-1"},
    {"indexation_method": "fixed", "fixed_indexation_rate": "-1"},
])
def test_invalid_manual_basis_api_rejected(engine, changes):
    payload = {**facts().model_dump(mode="json"), **changes}
    with pytest.raises(ValidationError):
        ManualPensionInput(**payload)
    def session():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[get_db] = session
    try:
        with TestClient(app) as client:
            assert client.post("/api/clients/1/canonical-pension-sources/manual", json=payload).status_code == 422
        assert read(engine)["pension_sources"] == []
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize("amount", ["40.00", "100.00"])
@pytest.mark.parametrize("destination", ["pension", "capital"])
def test_conversion_remaining_and_reversal(engine, amount, destination):
    source = seeded(engine)
    with Session(engine) as db, db.begin():
        result = execute(db, 1, request(source, amount=amount, destination=destination), "test")
    view = read(engine)
    product = view["pension_products"][0]
    assert len(product["components"]) == 11
    assert product["reported_controls"]["authority"] == "CONTROL_RECONCILIATION_ONLY"
    assert product["reported_controls"]["reported_product_total"] == "100.00"
    assert next(c for c in product["components"] if c["component_id"] == source[1])["balance"] == format(Decimal(100) - Decimal(amount), ".2f")
    assert len(view["pension_sources"] if destination == "pension" else view["capital_sources"]) == 1
    with Session(engine) as db, db.begin():
        reverse(db, 1, result["conversions"][0]["conversion_id"], ReversalRequest(expected_conversion_version=1,
            expected_product_version=3, idempotency_key="undo", reason="test"), "test")
    restored = read(engine)
    assert restored["pension_sources"] == restored["capital_sources"] == []
    assert next(c for c in restored["pension_products"][0]["components"] if c["component_id"] == source[1])["balance"] == "100.00"


def test_manual_modes_version_supersede_and_cross_client(engine):
    with Session(engine) as db, db.begin():
        a = manual.create(db, 1, facts())
        b = manual.create(db, 1, ManualPensionInput(input_mode="calculated", payer_name="משלם", balance="1.00", annuity_factor="3", tax_treatment="exempt", pension_start_date=date(2040, 1, 1), indexation_method="none"))
    view = read(engine, as_of=date(2030, 1, 1))
    assert all(s["calculation_ready"] and not s["has_started"] for s in view["pension_sources"])
    ratio = next(s for s in view["pension_sources"] if s["input_mode"] == "calculated")["amount_authority"]
    assert ratio == {"authority_kind": "manual_balance_ratio", "numerator": "1.00", "denominator": "3"}
    assert read(engine, 2)["pension_sources"] == []
    assert view == read(engine, as_of=date(2030, 1, 1))
    update = ManualPensionUpdate(**{**facts().model_dump(), "monthly_amount": "200.00"}, expected_version=1)
    with Session(engine) as db, db.begin():
        manual.change(db, 1, a["manual_pension_source_id"], update)
    for client in (1, 2):
        with Session(engine) as db:
            with pytest.raises(PensionProductError):
                manual.change(db, client, a["manual_pension_source_id"], update)
    with Session(engine) as db, db.begin():
        manual.change(db, 1, a["manual_pension_source_id"], ManualPensionSupersede(expected_version=2), supersede=True)
    assert len(read(engine)["pension_sources"]) == 1
    with Session(engine) as db:
        assert db.get(Manual, a["manual_pension_source_id"]).lifecycle_status == "superseded"


@pytest.mark.parametrize("changes,code", [
    ({"pension_start_date": None}, "pension_start_date_missing"),
    ({"tax_treatment": None}, "tax_treatment_missing_or_unsupported"),
    ({"tax_treatment": "unknown"}, "tax_treatment_missing_or_unsupported"),
    ({"tax_treatment": "capital_gains"}, "tax_treatment_missing_or_unsupported"),
    ({"indexation_method": "fixed"}, "fixed_indexation_rate_missing"),
    ({"monthly_amount": None}, "monthly_amount_missing"),
])
def test_incomplete_visible_without_defaults(engine, changes, code):
    payload = ManualPensionInput(**{**facts().model_dump(), **changes})
    with Session(engine) as db, db.begin():
        manual.create(db, 1, payload)
    source = read(engine)["pension_sources"][0]
    assert source["visible"] and not source["calculation_ready"]
    assert code in source["missing_or_blocking_facts"]
    for key, value in changes.items():
        assert source[key] == value


def test_duplicate_reference_not_payer_name_and_fixed_positive_explicit(engine):
    with Session(engine) as db, db.begin():
        for _ in range(2):
            manual.create(db, 1, ManualPensionInput(**{**facts().model_dump(), "indexation_method": "fixed", "fixed_indexation_rate": "0.01"}))
    assert all(s["calculation_ready"] for s in read(engine)["pension_sources"])
    with Session(engine) as db, db.begin():
        for row in db.scalars(select(Manual)):
            row.source_reference = "explicit-external-reference"
    result = read(engine)
    assert len(result["pension_sources"]) == 2
    assert all("potential_duplicate_source" in s["missing_or_blocking_facts"] for s in result["pension_sources"])


def test_read_only_api_no_statement_writes_and_fingerprint(engine):
    seeded(engine)
    with Session(engine) as db, db.begin():
        manual.create(db, 1, facts())
        db.add(CapitalAsset(client_id=1, asset_category="other", asset_description="missing"))
        db.add(RecurringIncome(client_id=1, income_category="pension", description="general only",
            amount=Decimal("900"), amount_basis="gross", frequency="monthly", continuation_status="ongoing"))
    statements = []
    def capture(conn, cursor, statement, parameters, context, many):
        statements.append(statement.strip())
    event.listen(engine, "before_cursor_execute", capture)
    def session():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[get_db] = session
    try:
        with TestClient(app) as client:
            first = client.get("/api/clients/1/professional-source-snapshot")
            second = client.get("/api/clients/1/professional-source-snapshot")
            assert first.status_code == 200, first.text
            assert first.json() == second.json()
            assert len(first.json()["pension_sources"]) == 1
            assert first.json()["capital_sources"][0]["missing_or_blocking_facts"] == ["known_value_missing"]
        assert statements and all(s.upper().startswith(("SELECT", "BEGIN")) for s in statements)
    finally:
        app.dependency_overrides.clear()
        event.remove(engine, "before_cursor_execute", capture)


@pytest.mark.parametrize("payload", [
    {"input_mode": "entered", "monthly_amount": "-1"},
    {"input_mode": "calculated", "annuity_factor": "0"},
    {"input_mode": "calculated", "annuity_factor": "NaN"},
    {"input_mode": "entered", "balance": "1"},
    {"input_mode": "calculated", "monthly_amount": "1"},
])
def test_manual_validation(payload):
    with pytest.raises(ValidationError):
        ManualPensionInput(**payload)


def test_old_execution_unregistered_and_archive_marked(engine):
    routes = {r.path: getattr(r, "methods", set()) for r in app.routes}
    assert all(methods == {"GET"} for path, methods in routes.items() if "/m09/" in path)
    assert not any("/m10/" in path for path in routes)
    def session():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[get_db] = session
    try:
        with TestClient(app) as client:
            for path in ("m09/inventories", "m09/runs", "m09/subjects", "m09/subjects/baseline", "m09/subjects/x/runs", "m10/compare"):
                assert client.post("/api/clients/1/" + path, json={}).status_code in (404, 405)
            response = client.get("/api/clients/1/m09/runs")
            assert response.status_code == 200
            assert response.json() == {"authority": "archive_only", "records": []}
            assert response.headers["X-Professional-Authority"] == "archive-only"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize("mutation,valid", [
    ({"monthly_display_amount": Decimal("999999.99")}, True),
    ({"monthly_denominator": "0"}, False),
    ({"monthly_numerator": "123"}, False),
    ({"client_id": 2}, False),
])
def test_persisted_ratio_never_falls_back_to_display(engine, monkeypatch, mutation, valid):
    # Corruption is injected at the read boundary, without weakening or
    # disabling PKG-002's database immutability guards.
    from types import SimpleNamespace
    source = seeded(engine)
    with Session(engine) as db, db.begin():
        execute(db, 1, request(source, destination="pension"), "test")
    baseline = read(engine)
    with Session(engine) as db:
        original = db.execute
        def intercepted(statement, *args, **kwargs):
            result = original(statement, *args, **kwargs)
            tables = [t.name for t in statement.get_final_froms()] if hasattr(statement, "get_final_froms") else []
            if tables == ["canonical_pension_destinations"]:
                rows = [{**dict(row), **mutation} for row in result.mappings()]
                return SimpleNamespace(mappings=lambda: SimpleNamespace(all=lambda: rows))
            return result
        monkeypatch.setattr(db, "execute", intercepted)
        if valid:
            assert snapshot(db, 1) == baseline
        else:
            with pytest.raises(PensionProductError) as error:
                snapshot(db, 1)
            assert error.value.code == "SOURCE_STRUCTURE_INVALID"


def test_manual_conversion_duplicate_link_and_calendar_fingerprint(engine):
    source = seeded(engine)
    with Session(engine) as db, db.begin():
        execute(db, 1, request(source, destination="pension"), "test")
    identifier = read(engine)["pension_sources"][0]["source_id"]
    with Session(engine) as db, db.begin():
        manual.create(db, 1, facts(source_reference=identifier))
    before = read(engine, as_of=date(2029, 1, 1))
    after = read(engine, as_of=date(2041, 1, 1))
    assert len(before["pension_sources"]) == 2
    assert all(not s["calculation_ready"] for s in before["pension_sources"])
    assert len(before["source_warnings"]) == 2
    assert before["source_state_fingerprint"] == after["source_state_fingerprint"]
    assert all(s["has_started"] for s in after["pension_sources"])


def test_manual_api_version_isolation_supersede_and_no_conversion_edit(engine):
    def session():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[get_db] = session
    root = "/api/clients/1/canonical-pension-sources/manual"
    try:
        with TestClient(app) as client:
            created = client.post(root, json=facts().model_dump(mode="json"))
            assert created.status_code == 200, created.text
            sid = created.json()["manual_pension_source_id"]
            payload = {**facts().model_dump(mode="json"), "expected_version": 1, "monthly_amount": "200.00"}
            assert client.put(root + "/" + sid, json=payload).status_code == 200
            assert client.put(root + "/" + sid, json=payload).status_code == 409
            assert client.put(root.replace("/1/", "/2/") + "/" + sid, json=payload).status_code == 404
            assert client.put(root + "/conversion:fake", json=payload).status_code == 404
            removed = client.request("DELETE", root + "/" + sid, json={"expected_version": 2})
            assert removed.status_code == 200
            assert removed.json()["lifecycle_status"] == "superseded"
            assert client.get("/api/clients/1/professional-source-snapshot").json()["pension_sources"] == []
    finally:
        app.dependency_overrides.clear()


def test_sqlite_single_additive_migration_and_no_automatic_income_copy(tmp_path):
    from sqlalchemy import create_engine, inspect
    from test_canonical_conversion_migration import migrate
    url = "sqlite:///" + (tmp_path / "migration.db").as_posix()
    migrate(url, "upgrade", "f5a1c8d4e632")
    db_engine = create_engine(url)
    before = set(inspect(db_engine).get_table_names())
    migrate(url, "upgrade", "a6b2d9e5f743")
    assert set(inspect(db_engine).get_table_names()) - before == {"canonical_manual_pension_sources"}
    with db_engine.connect() as db:
        assert db.scalar(text("SELECT count(*) FROM canonical_manual_pension_sources")) == 0
        assert db.scalar(text("SELECT version_num FROM alembic_version")) == "a6b2d9e5f743"
    migrate(url, "downgrade", "f5a1c8d4e632")
    assert set(inspect(db_engine).get_table_names()) == before
    db_engine.dispose()


@pytest.mark.parametrize("kind", ["product", "conversion", "manual_pension", "manual_capital"])
def test_sqlite_wal_snapshot_coherent_during_committed_writer(engine, kind):
    from test_professional_source_postgresql import test_postgresql_snapshot_coherent_during_committed_writer as check_coherence
    with engine.connect() as db:
        assert db.scalar(text("PRAGMA journal_mode=WAL")) == "wal"
    check_coherence(engine, kind)


@pytest.mark.parametrize("changes", [
    {"monthly_amount": "-1.00"}, {"input_mode": "calculated", "annuity_factor": "0"},
    {"input_mode": "calculated", "annuity_factor": "-1"}, {"balance": "1.00"},
    {"client_id": 999}, {"version": 0}, {"lifecycle_status": "deleted"},
])
def test_manual_database_constraints(engine, changes):
    from sqlalchemy.exc import DBAPIError
    with Session(engine) as db:
        db.add(Manual(**{"manual_pension_source_id": "invalid", "client_id": 1, "input_mode": "entered", **changes}))
        with pytest.raises((DBAPIError, ValueError)):
            db.flush()
        db.rollback()
