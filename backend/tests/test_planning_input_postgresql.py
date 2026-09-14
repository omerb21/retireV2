from concurrent.futures import ThreadPoolExecutor
from threading import Event, Barrier
from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy import create_engine, text, event, inspect
from sqlalchemy.orm import Session
from app.models.retirement_facts import RecurringIncome, RecurringExpense, CapitalAsset
from app.schemas.planning_input import BaseDateDecision, IncomeResolutionDecision
from app.services import planning_input_service as planning
from app.services.pension_product_service import PensionProductError
from test_recovery_migration_postgresql import postgres_url
from test_canonical_conversion_migration import migrate
from test_planning_input import view, choose, income


@pytest.fixture
def pg_engine(postgres_url):
    migrate(postgres_url, "upgrade", "b7c3e0f6a854")
    engine = create_engine(postgres_url)
    with engine.begin() as db:
        db.execute(text("INSERT INTO clients(client_id,display_name,id_number) VALUES(1,'test','123'),(2,'other','456')"))
    yield engine
    engine.dispose()


def test_pg_migration_capital_persistence_and_constraints(postgres_url):
    from test_planning_input import test_capital_ordinary_api_missing_date
    migrate(postgres_url, "upgrade", "a6b2d9e5f743")
    engine = create_engine(postgres_url)
    try:
        with engine.begin() as db:
            db.execute(text("INSERT INTO clients(client_id,display_name,id_number) VALUES(1,'test','123')"))
            db.execute(text("INSERT INTO capital_asset(client_id,asset_category,asset_description,known_value_amount,value_as_of_date) VALUES(1,'other','legacy',123.45,'2020-01-01')"))
        with engine.connect() as db:
            before = db.execute(text("SELECT * FROM capital_asset ORDER BY id")).all()
        checks = {c["name"]: c["sqltext"] for c in inspect(engine).get_check_constraints("capital_asset")}
        migrate(postgres_url, "upgrade", "b7c3e0f6a854")
        after_checks = {c["name"]: c["sqltext"] for c in inspect(engine).get_check_constraints("capital_asset")}
        del checks["ck_capital_asset_value_date_required"]
        assert checks == after_checks
        with engine.connect() as db:
            assert db.execute(text("SELECT * FROM capital_asset ORDER BY id")).all() == before
        migrate(postgres_url, "downgrade", "a6b2d9e5f743")
        assert "ck_capital_asset_value_date_required" in {c["name"] for c in inspect(engine).get_check_constraints("capital_asset")}
        migrate(postgres_url, "upgrade", "b7c3e0f6a854")
        test_capital_ordinary_api_missing_date(engine)
        failure = migrate(postgres_url, "downgrade", "a6b2d9e5f743", success=False)
        assert "PLANNING_DOWNGRADE_INCOMPLETE_CAPITAL" in failure
    finally:
        engine.dispose()


def test_pg_version_race_and_reclassification_rollback(pg_engine):
    barrier = Barrier(2)
    def write_date():
        barrier.wait(timeout=10)
        try:
            with Session(pg_engine) as db, db.begin():
                planning.set_base_date(db, 1, BaseDateDecision(expected_version=0, planning_base_date=date(2030, 1, 1)))
            return "ok"
        except PensionProductError as error:
            return error.code
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: write_date(), range(2)))
    assert sorted(results) == ["PLANNING_DECISION_STALE", "ok"]
    iid = income(pg_engine, income_category="pension")
    old = view(pg_engine)
    payload = IncomeResolutionDecision(expected_version=1,
        expected_income_fingerprint=old["excluded_sources"][0]["source_fingerprint"],
        decision_kind="MISCLASSIFIED_GENERAL_INCOME", income_category="rental", reference="professional decision")
    with pytest.raises(RuntimeError):
        with Session(pg_engine) as db, db.begin():
            planning.resolve_income(db, 1, iid, payload)
            raise RuntimeError("late failure")
    assert view(pg_engine) == old
    with Session(pg_engine) as db, db.begin():
        planning.resolve_income(db, 1, iid, payload)
    result = view(pg_engine)
    assert result["planning_input_ready"] and result["general_income_inputs"][0]["income_category"] == "rental"


@pytest.mark.parametrize("kind", ["income", "expense", "decision", "capital", "manual_pension"])
def test_pg_read_only_consistent_concurrent_write(pg_engine, kind):
    choose(pg_engine)
    iid = income(pg_engine)
    with Session(pg_engine) as db, db.begin():
        expense = RecurringExpense(client_id=1, expense_category="housing", description="expense", amount=Decimal(10),
            frequency="monthly", expense_type="mandatory", continuation_status="ongoing", start_date=date(2020, 1, 1))
        db.add(expense); db.flush(); eid = expense.id
    old = view(pg_engine)
    paused, resume = Event(), Event()
    reader_connection = [None]
    statements = []
    def intercept(conn, cursor, statement, parameters, context, many):
        if reader_connection[0] is None:
            reader_connection[0] = conn
        if conn is reader_connection[0]:
            statements.append(statement.strip().upper())
            if statement.strip().upper().startswith("SELECT") and not paused.is_set():
                paused.set()
                assert resume.wait(15)
    event.listen(pg_engine, "after_cursor_execute", intercept)
    try:
        with ThreadPoolExecutor(1) as pool:
            pending = pool.submit(view, pg_engine)
            assert paused.wait(15)
            try:
                with Session(pg_engine) as db, db.begin():
                    if kind == "income": db.get(RecurringIncome, iid).amount = Decimal(22)
                    elif kind == "expense": db.get(RecurringExpense, eid).amount = Decimal(22)
                    elif kind == "decision": planning.set_base_date(db, 1, BaseDateDecision(expected_version=1, planning_base_date=date(2031, 1, 1)))
                    elif kind == "capital": db.add(CapitalAsset(client_id=1, asset_category="other", asset_description="new", known_value_amount=Decimal(22)))
                    else:
                        from app.services.canonical_manual_pension_service import create
                        from test_professional_source_snapshot import facts
                        create(db, 1, facts())
            finally:
                resume.set()
            assert pending.result(timeout=15) == old
    finally:
        resume.set()
        event.remove(pg_engine, "after_cursor_execute", intercept)
    assert all(s.startswith(("SELECT", "SET TRANSACTION", "BEGIN")) for s in statements)
    assert view(pg_engine)["planning_input_fingerprint"] != old["planning_input_fingerprint"]
