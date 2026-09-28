from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy import select, event, text
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import get_db
from app.models.retirement_facts import RecurringIncome, RecurringExpense, CapitalAsset
from app.models.planning_input_decision import PlanningInputDecision, PensionIncomeResolution
from app.schemas.planning_input import BaseDateDecision, IncomeResolutionDecision
from app.services import planning_input_service as planning
from app.services import canonical_manual_pension_service as manual
from app.services.pension_product_service import PensionProductError
from test_recovery_pension_products import engine
from test_professional_source_snapshot import facts


def view(engine, client=1):
    with Session(engine) as db:
        return planning.read(db, client)


def choose(engine, version=0):
    with Session(engine) as db, db.begin():
        planning.set_base_date(db, 1, BaseDateDecision(expected_version=version, planning_base_date=date(2030, 1, 1)))


def income(engine, **changes):
    with Session(engine) as db, db.begin():
        row = RecurringIncome(**dict(client_id=1, income_category="rental", description="same",
            amount=Decimal("0.01"), frequency="quarterly", amount_basis="gross", start_date=date(2020, 1, 1),
            continuation_status="ongoing") | changes)
        db.add(row)
        db.flush()
        return row.id


def test_empty_read_explicit_base_no_write(engine):
    statements = []
    def capture(conn, cursor, statement, parameters, context, many):
        statements.append(statement.strip().upper())
    event.listen(engine, "before_cursor_execute", capture)
    first = view(engine)
    assert first == view(engine)
    assert first["planning_base_date"] is None and not first["planning_input_ready"]
    assert first["blocking_facts"] == [{"source_id": None, "code": "planning_base_date_missing"}]
    assert all(s.startswith(("SELECT", "BEGIN")) for s in statements)
    event.remove(engine, "before_cursor_execute", capture)
    with Session(engine) as db:
        assert db.scalar(select(PlanningInputDecision)) is None
    choose(engine)
    second = view(engine)
    assert second["planning_base_date"] == "2030-01-01" and second["planning_input_ready"]
    assert first["planning_input_fingerprint"] != second["planning_input_fingerprint"]
    with pytest.raises(PensionProductError):
        choose(engine)


@pytest.mark.parametrize("frequency,denominator", [("monthly", 1), ("quarterly", 3), ("annual", 12), ("other", None)])
def test_exact_income_expense_normalization(engine, frequency, denominator):
    choose(engine)
    income(engine, frequency=frequency)
    with Session(engine) as db, db.begin():
        db.add(RecurringExpense(client_id=1, expense_category="housing", description="expense", amount=Decimal("0.01"),
            frequency=frequency, expense_type="mandatory", continuation_status="ongoing", start_date=date(2020, 1, 1)))
    result = view(engine)
    for key in ("general_income_inputs", "expense_inputs"):
        item = result[key][0]
        assert item["amount"] == "0.01"
        assert item["monthly_equivalent_ratio"] == ({"numerator": "0.01", "denominator": denominator} if denominator else None)
    assert result["planning_input_ready"] == (denominator is not None)


@pytest.mark.parametrize("changes,applicability,ready", [
    ({"start_date": date(2040, 1, 1)}, "future_start", True),
    ({"end_date": date(2025, 1, 1), "continuation_status": "known end date"}, "ended", True),
    ({"start_date": None}, "active_at_base", False),
    ({"start_date": date(2040, 1, 1), "end_date": date(2020, 1, 1)}, "future_start", False),
    ({"continuation_status": "known end date"}, "active_at_base", False),
    ({"amount_basis": "unknown"}, "active_at_base", False),
])
def test_applicability(engine, changes, applicability, ready):
    choose(engine)
    income(engine, **changes)
    result = view(engine)
    assert result["planning_input_ready"] == ready
    assert result["general_income_inputs"][0]["applicability"] == applicability


def test_similarity_nonblocking_and_basis_separate(engine):
    choose(engine)
    a, b = income(engine), income(engine)
    income(engine, amount_basis="net")
    result = view(engine)
    assert result["planning_input_ready"]
    assert len(result["general_income_inputs"]) == 3
    assert {r["id"] for r in result["general_income_inputs"]} >= {a, b}
    assert any(w["code"] == "potential_duplicate_warning" for w in result["warnings"])
    assert "total" not in result


def test_manual_link_stale_and_reclassification(engine):
    choose(engine)
    iid = income(engine, income_category="pension")
    with Session(engine) as db, db.begin():
        manual.create(db, 1, facts())
    result = view(engine)
    source = result["pension_inputs"][0]
    assert source["applicability"] == "future_start" and source["source_calculation_ready"]
    assert not source["active_at_base"]
    unresolved = result["excluded_sources"][0]
    assert not result["planning_input_ready"] and result["general_income_inputs"] == []
    payload = IncomeResolutionDecision(expected_version=1, expected_income_fingerprint=unresolved["source_fingerprint"],
        decision_kind="SAME_CANONICAL_PENSION", canonical_source_id=source["source_id"],
        expected_canonical_fingerprint=source["source_fingerprint"], reference="explicit")
    with Session(engine) as db, db.begin():
        planning.resolve_income(db, 1, iid, payload)
    assert view(engine)["planning_input_ready"]
    assert len(view(engine)["pension_inputs"]) == 1
    with Session(engine) as db, db.begin():
        db.get(RecurringIncome, iid).description = "material edit"
    result = view(engine)
    assert not result["planning_input_ready"]
    assert result["excluded_sources"][0]["blocking_facts"] == ["identity_resolution_stale"]
    with Session(engine) as db, db.begin():
        planning.resolve_income(db, 1, iid, IncomeResolutionDecision(expected_version=2,
            expected_income_fingerprint=result["excluded_sources"][0]["source_fingerprint"],
            decision_kind="MISCLASSIFIED_GENERAL_INCOME", income_category="rental", reference="correct category"))
    result = view(engine)
    assert result["planning_input_ready"] and len(result["general_income_inputs"]) == 1
    assert view(engine, 2)["pension_inputs"] == []


def test_capital_ordinary_api_missing_date(engine):
    def session():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[get_db] = session
    try:
        with TestClient(app) as client:
            response = client.post("/api/clients/1/capital-assets", json={"asset_category": "other", "asset_description": "incomplete", "known_value_amount": "123.45"})
            assert response.status_code == 200, response.text
            assert response.json()["value_as_of_date"] is None
            asset_id = response.json()["id"]
            choose(engine)
            response = client.get("/api/clients/1/retirement-planning-input")
            assert response.status_code == 200, response.text
            result = response.json()
            assert not result["planning_input_ready"]
            asset = next(a for a in result["capital_inputs"] if a["id"] == asset_id)
            assert asset["known_value_amount"] == "123.45" and asset["value_as_of_date"] is None
            assert asset["inclusion_state"] == "unresolved"
            assert "capital_valuation_date_missing" in asset["blocking_facts"]
            path = f"/api/clients/1/capital-assets/{asset_id}"
            dated = client.put(path, json={"value_as_of_date": "2029-01-01"})
            assert dated.status_code == 200, dated.text
            cleared = client.put(path, json={"value_as_of_date": None})
            assert cleared.status_code == 200, cleared.text
            reloaded = client.get(path).json()
            assert reloaded["known_value_amount"] == "123.45" and reloaded["value_as_of_date"] is None
    finally:
        app.dependency_overrides.clear()


def test_sqlite_migration_preserves_and_guards_downgrade(tmp_path):
    from sqlalchemy import create_engine, inspect
    from test_canonical_conversion_migration import migrate
    url = "sqlite:///" + (tmp_path / "migration.db").as_posix()
    migrate(url, "upgrade", "a6b2d9e5f743")
    engine = create_engine(url)
    with engine.begin() as db:
        db.execute(text("INSERT INTO clients(client_id,display_name,id_number) VALUES(1,'test','123')"))
        db.execute(text("INSERT INTO capital_asset(client_id,asset_category,asset_description,known_value_amount,value_as_of_date) VALUES(1,'other','old','123.45','2020-01-01')"))
    with engine.connect() as db:
        before = db.execute(text("SELECT * FROM capital_asset")).all()
        triggers = db.execute(text("SELECT name,sql FROM sqlite_master WHERE type='trigger' ORDER BY name")).all()
    migrate(url, "upgrade", "b7c3e0f6a854")
    with engine.connect() as db:
        assert db.execute(text("SELECT * FROM capital_asset")).all() == before
        assert db.execute(text("SELECT name,sql FROM sqlite_master WHERE type='trigger' ORDER BY name")).all() == triggers
    migrate(url, "upgrade", "e0f6b3c9d187")
    test_capital_ordinary_api_missing_date(engine)
    failure = migrate(url, "downgrade", "a6b2d9e5f743", success=False)
    assert "PLANNING_DOWNGRADE_INCOMPLETE_CAPITAL" in failure
    engine.dispose()


@pytest.mark.parametrize("kind", ["income", "expense", "decision", "capital", "manual_pension"])
def test_sqlite_consistent_concurrent_read(engine, kind):
    from test_planning_input_postgresql import test_pg_read_only_consistent_concurrent_write
    with engine.connect() as db:
        assert db.scalar(text("PRAGMA journal_mode=WAL")) == "wal"
    test_pg_read_only_consistent_concurrent_write(engine, kind)


@pytest.mark.parametrize("mutation", ["wrong_client", "stale_amount", "superseded", "missing"])
def test_link_requires_existing_current_same_client_source(engine, mutation):
    from app.models.canonical_manual_pension_source import CanonicalManualPensionSource
    choose(engine)
    iid = income(engine, income_category="pension")
    with Session(engine) as db, db.begin():
        created = manual.create(db, 1, facts())
    result = view(engine)
    source = result["pension_inputs"][0]
    sid = created["manual_pension_source_id"]
    with Session(engine) as db, db.begin():
        row = db.get(CanonicalManualPensionSource, sid)
        if mutation == "wrong_client": row.client_id = 2
        elif mutation == "stale_amount": row.monthly_amount = Decimal(222)
        elif mutation == "superseded": row.lifecycle_status = "superseded"
    payload = IncomeResolutionDecision(expected_version=1, expected_income_fingerprint=result["excluded_sources"][0]["source_fingerprint"],
        decision_kind="PENSION_NOT_YET_CANONICAL", canonical_source_id="manual:missing" if mutation == "missing" else source["source_id"],
        expected_canonical_fingerprint=source["source_fingerprint"], reference="explicit")
    with pytest.raises(PensionProductError):
        with Session(engine) as db, db.begin():
            planning.resolve_income(db, 1, iid, payload)
    assert view(engine)["decision_version"] == 1
    assert not view(engine)["planning_input_ready"]


def test_conversion_exact_authority_and_components_reference_only(engine):
    from test_canonical_component_conversion import seeded, request
    from app.services.canonical_component_conversion_service import execute
    source = seeded(engine)
    choose(engine)
    with Session(engine) as db, db.begin():
        execute(db, 1, request(source, destination="pension"), "test")
    result = view(engine)
    assert len(result["pension_inputs"]) == 1
    pension = result["pension_inputs"][0]
    assert pension["amount_authority"]["authority_kind"] == "persisted_conversion_ratio"
    assert "monthly_display_amount" not in pension
    components = [r for r in result["reference_only"] if r.get("classification") == "remaining_unconverted_source"]
    assert len(components) == 11
    assert not result["capital_inputs"] and not result["general_income_inputs"]


def test_client_age_and_timing_are_not_automatic_date_decisions(engine):
    from app.models.client import Client
    from app.models.retirement_facts import RetirementTimingWorkIntention
    with Session(engine) as db, db.begin():
        client = db.get(Client, 1)
        client.planned_retirement_age = 67
        client.birth_date = date(1960, 1, 1)
        db.add(RetirementTimingWorkIntention(client_id=1, timing_confidence="known", work_after_retirement_intention="stop working",
            planned_work_end_date=date(2027, 1, 1), intended_pension_start_date=date(2028, 1, 1)))
    result = view(engine)
    assert result["planning_base_date"] is None and result["decision_version"] == 0
    assert {c["field"] for c in result["date_candidates"]} == {"planned_work_end_date", "intended_pension_start_date"}
    assert result["client_reference_facts"]["planned_retirement_age"] == 67


@pytest.mark.parametrize("start,end,continuation,expected", [
    (date(2020, 1, 1), None, "ongoing", "included"),
    (date(2040, 1, 1), None, "ongoing", "included"),
    (date(2020, 1, 1), date(2025, 1, 1), "known end date", "reference_only"),
    (date(2040, 1, 1), date(2020, 1, 1), "known end date", "unresolved"),
    (None, None, "ongoing", "unresolved"),
])
def test_expense_applicability(engine, start, end, continuation, expected):
    choose(engine)
    with Session(engine) as db, db.begin():
        db.add(RecurringExpense(client_id=1, expense_category="housing", description="expense", amount=Decimal(10), frequency="monthly",
            expense_type="mandatory", continuation_status=continuation, start_date=start, end_date=end))
    result = view(engine)
    assert result["expense_inputs"][0]["inclusion_state"] == expected
    if start == date(2040, 1, 1):
        assert result["expense_inputs"][0]["applicability"] == "future_start"


def test_explicit_conflicting_decision_blocks_but_source_notes_do_not(engine):
    choose(engine)
    iid = income(engine, income_category="pension", source_note="shared note")
    result = view(engine)
    with Session(engine) as db, db.begin():
        planning.resolve_income(db, 1, iid, IncomeResolutionDecision(expected_version=1,
            expected_income_fingerprint=result["excluded_sources"][0]["source_fingerprint"],
            decision_kind="MISCLASSIFIED_GENERAL_INCOME", income_category="rental", reference="explicit decision"))
    income(engine, source_note="shared note")
    result = view(engine)
    assert result["planning_input_ready"] and len(result["general_income_inputs"]) == 2
    with Session(engine) as db, db.begin():
        db.get(PensionIncomeResolution, iid).canonical_source_id = "manual:contradictory-link"
    result = view(engine)
    assert not result["planning_input_ready"]
    assert result["excluded_sources"][0]["blocking_facts"] == ["identity_resolution_stale"]
    assert len(result["general_income_inputs"]) == 1


def test_wrong_client_decision_rejected(engine):
    choose(engine)
    iid = income(engine, income_category="pension")
    result = view(engine)
    with pytest.raises(PensionProductError):
        with Session(engine) as db, db.begin():
            planning.resolve_income(db, 2, iid, IncomeResolutionDecision(expected_version=0,
                expected_income_fingerprint=result["excluded_sources"][0]["source_fingerprint"],
                decision_kind="MISCLASSIFIED_GENERAL_INCOME", income_category="rental", reference="wrong client"))
    assert view(engine, 2)["decision_version"] == 0


def test_reclassification_rejects_empty_canonical_link():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        IncomeResolutionDecision(expected_version=0, expected_income_fingerprint="0" * 64,
            decision_kind="MISCLASSIFIED_GENERAL_INCOME", income_category="rental",
            canonical_source_id="", reference="explicit")


def test_planning_boundary_has_no_legacy_or_browser_authority():
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    source = (root / "backend/app/services/planning_input_service.py").read_text(encoding="utf-8")
    for term in ("PensionHolding", "pension_holding", "m02_", "m03_", "m04_", "m05_", "m06_", "m09_", "m10_"):
        assert term not in source
    assert "lock_client" not in source[source.index("def read("):source.index("def writable_decision(")]
    for relative in ("frontend/src/pages/PlanningInputScreen.tsx", "frontend/src/api/planningInputApi.ts"):
        ui = (root / relative).read_text(encoding="utf-8")
        for term in ("localStorage", "sessionStorage", 'type="date"', "m09", "m10", "monthly_display_amount"):
            assert term not in ui


@pytest.mark.parametrize("payload", [
    {"monthly_amount": "12.34"},
    {"input_mode": "calculated", "monthly_amount": None, "balance": "0.01", "annuity_factor": "3"},
])
def test_pension_exact_authority_preserved(engine, payload):
    from app.schemas.canonical_manual_pension_source import ManualPensionInput
    choose(engine)
    with Session(engine) as db, db.begin():
        manual.create(db, 1, ManualPensionInput(**{**facts().model_dump(), **payload}))
    source = view(engine)["pension_inputs"][0]
    assert source["source_calculation_ready"] and not source["active_at_base"]
    if payload.get("input_mode") == "calculated":
        assert source["amount_authority"] == {"authority_kind": "manual_balance_ratio", "numerator": "0.01", "denominator": "3"}
    else:
        assert source["amount_authority"] == {"authority_kind": "entered_monthly_amount", "amount": "12.34"}
