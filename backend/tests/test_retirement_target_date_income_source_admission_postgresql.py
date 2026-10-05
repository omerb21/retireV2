"""Opt-in PostgreSQL snapshot/transaction validation for RTISA."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from threading import Event

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session

from app.db.base import load_all_models
from app.models.planning_input_decision import PlanningInputDecision
from app.models.retirement_facts import RecurringIncome
from app.services import planning_input_service
from app.services import retirement_target_date_income_source_admission_service as subject
from test_canonical_conversion_migration import migrate
from test_recovery_migration_postgresql import postgres_url

load_all_models()


@pytest.fixture
def pg_engine(postgres_url):
    migrate(postgres_url, "upgrade", "a2b8c5e1f309")
    engine = create_engine(postgres_url, pool_size=5)
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO clients(client_id,display_name,id_number) VALUES(1,'test','123')"))
        connection.execute(text("INSERT INTO planning_input_decisions "
                                "(client_id,version,planning_base_date,retirement_target_date,"
                                "retirement_target_decision_actor,retirement_target_reference_fingerprint,actor) "
                                "VALUES(1,1,'2026-01-01','2030-01-01','planner:test',repeat('a',64),'planner:test')"))
        connection.execute(text("INSERT INTO recurring_income "
                                "(client_id,income_category,description,amount,amount_basis,frequency,continuation_status,"
                                "lifecycle_status,source_status,verification_state,start_date) "
                                "VALUES(1,'rental','rent',1200.00,'gross','monthly','ongoing','current','planner entered','reviewed','2025-01-01')"))
    yield engine
    engine.dispose()


def _expected(engine):
    with Session(engine) as db:
        return planning_input_service.read(db, 1)["planning_calculation_input_fingerprint"]


def test_postgresql_repeatable_read_read_only_and_current_result(pg_engine):
    expected = _expected(pg_engine)
    statements = []
    def capture(conn, cursor, statement, parameters, context, many): statements.append(statement.strip().upper())
    event.listen(pg_engine, "before_cursor_execute", capture)
    try:
        with Session(pg_engine) as db:
            result = subject.read(db, 1, expected)
    finally:
        event.remove(pg_engine, "before_cursor_execute", capture)
    assert statements[0] == "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"
    assert result["included_source_ids"] == ["income:1"] and result["admission_ready"] is True
    with pg_engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM recurring_income")) == 1


def test_postgresql_concurrent_change_is_snapshot_consistent_and_fresh_read_changes_identity(pg_engine):
    expected = _expected(pg_engine)
    paused, resume = Event(), Event()
    reader_connection = [None]

    def intercept(conn, cursor, statement, parameters, context, many):
        upper = statement.strip().upper()
        if reader_connection[0] is None and upper.startswith("SET TRANSACTION"):
            reader_connection[0] = conn
        if conn is reader_connection[0] and upper.startswith("SELECT") and not paused.is_set():
            paused.set(); assert resume.wait(20)

    event.listen(pg_engine, "after_cursor_execute", intercept)
    def read_old():
        with Session(pg_engine) as db:
            return subject.read(db, 1, expected)
    try:
        with ThreadPoolExecutor(1) as pool:
            pending = pool.submit(read_old)
            assert paused.wait(20)
            try:
                with Session(pg_engine) as writer, writer.begin():
                    writer.get(RecurringIncome, 1).amount = Decimal("1300.00")
            finally:
                resume.set()
            old = pending.result(timeout=30)
    finally:
        resume.set(); event.remove(pg_engine, "after_cursor_execute", intercept)
    assert old["source_entries"][0]["native_amount"]["amount"] == "1200.00"
    new_expected = _expected(pg_engine)
    assert new_expected != expected
    with Session(pg_engine) as db:
        fresh = subject.read(db, 1, new_expected)
    assert fresh["source_entries"][0]["native_amount"]["amount"] == "1300.00"
    assert fresh["admission_result_fingerprint"] != old["admission_result_fingerprint"]


@pytest.mark.parametrize("operation", ["insert", "delete", "membership"])
def test_postgresql_synchronized_membership_changes_preserve_reader_snapshot(pg_engine, operation):
    expected = _expected(pg_engine)
    paused, resume = Event(), Event()
    reader_connection = [None]

    def intercept(conn, cursor, statement, parameters, context, many):
        upper = statement.strip().upper()
        if reader_connection[0] is None and upper.startswith("SET TRANSACTION"):
            reader_connection[0] = conn
        if conn is reader_connection[0] and upper.startswith("SELECT") and not paused.is_set():
            paused.set()
            assert resume.wait(20)

    event.listen(pg_engine, "after_cursor_execute", intercept)
    def read_old():
        with Session(pg_engine) as db:
            return subject.read(db, 1, expected)
    try:
        with ThreadPoolExecutor(1) as pool:
            pending = pool.submit(read_old)
            assert paused.wait(20)
            try:
                with Session(pg_engine) as writer, writer.begin():
                    if operation == "insert":
                        writer.add(RecurringIncome(
                            client_id=1, income_category="business", description="new business",
                            amount=Decimal("700.00"), amount_basis="gross", frequency="monthly",
                            continuation_status="ongoing", lifecycle_status="current",
                            source_status="planner entered", verification_state="reviewed",
                            start_date=date(2025, 1, 1),
                        ))
                    elif operation == "delete":
                        writer.delete(writer.get(RecurringIncome, 1))
                    else:
                        writer.get(RecurringIncome, 1).lifecycle_status = "superseded"
            finally:
                resume.set()
            old = pending.result(timeout=30)
    finally:
        resume.set()
        event.remove(pg_engine, "after_cursor_execute", intercept)
    assert old["included_source_ids"] == ["income:1"]
    new_expected = _expected(pg_engine)
    assert new_expected != expected
    with Session(pg_engine) as db:
        fresh = subject.read(db, 1, new_expected)
    expected_ids = ["income:1", "income:2"] if operation == "insert" else []
    assert fresh["included_source_ids"] == expected_ids
    assert fresh["admission_result_fingerprint"] != old["admission_result_fingerprint"]


def test_postgresql_expire_on_commit_false_does_not_reuse_stale_identity_map(pg_engine):
    expected = _expected(pg_engine)
    with Session(pg_engine, expire_on_commit=False) as db:
        stale = db.get(RecurringIncome, 1)
        assert stale.amount == Decimal("1200.00")
        db.commit()
        with Session(pg_engine) as writer, writer.begin():
            writer.get(RecurringIncome, 1).amount = Decimal("1400.00")
        current = _expected(pg_engine)
        result = subject.read(db, 1, current)
    assert current != expected
    assert result["source_entries"][0]["native_amount"]["amount"] == "1400.00"


def test_postgresql_direct_failure_after_authority_loading_rolls_back(pg_engine, monkeypatch):
    expected = _expected(pg_engine)
    original = planning_input_service.derive
    class TechnicalDatabaseFailure(RuntimeError):
        pass
    def fail_after_loading(db, client_id):
        original(db, client_id)
        raise TechnicalDatabaseFailure("after authority loading")
    monkeypatch.setattr(planning_input_service, "derive", fail_after_loading)
    with Session(pg_engine) as db:
        with pytest.raises(TechnicalDatabaseFailure, match="after authority loading"):
            subject.read(db, 1, expected)
        assert not db.in_transaction()
