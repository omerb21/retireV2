"""Opt-in PostgreSQL snapshot/transaction validation for RTICB."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from threading import Event

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.models.retirement_facts import RecurringIncome
from app.services import planning_input_service
from app.services import retirement_monthly_income_target_service as target_service
from app.services import retirement_target_date_income_comparison_basis_service as subject
from app.services import retirement_target_date_income_source_admission_service as rtisa_service
from test_canonical_conversion_migration import migrate
from test_planning_input import choose, view
from test_recovery_migration_postgresql import postgres_url
from test_retirement_target import payload as target_payload, save as save_target
from test_retirement_monthly_income_target_postgresql import command, confirm


@pytest.fixture
def pg_engine(postgres_url):
    migrate(postgres_url, "upgrade", "a2b8c5e1f309")
    engine = create_engine(postgres_url, pool_size=5)
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO clients(client_id,display_name,id_number) VALUES(1,'test','123')"))
    with Session(engine) as db, db.begin():
        db.add(RecurringIncome(
            client_id=1, income_category="rental", description="rent",
            amount=Decimal("1200.00"), amount_basis="gross", frequency="monthly",
            continuation_status="ongoing", lifecycle_status="current",
            source_status="planner entered", verification_state="reviewed",
            start_date=date(2025, 1, 1),
        ))
    choose(engine)
    save_target(engine, target_payload(engine))
    confirm(engine, command(engine))
    yield engine
    engine.dispose()


def _request(engine):
    planning = view(engine)
    return {
        "client_id": 1,
        "expected_planning_calculation_input_fingerprint": planning["planning_calculation_input_fingerprint"],
        "expected_retirement_target_date": planning["retirement_target"]["retirement_target_date"],
    }


def _assert_ordinary_success(engine, request):
    with Session(engine) as db:
        result = subject.assess(db, request)
        assert result["classification_complete"] is True, result
        assert not db.in_transaction()
    return result


def test_postgresql_read_only_repeatable_read_one_session_and_cleanup(pg_engine, monkeypatch):
    request = _request(pg_engine)
    with Session(pg_engine) as verification_db:
        upstream = rtisa_service.read(
            verification_db, 1, request["expected_planning_calculation_input_fingerprint"]
        )
    assert upstream["admission_ready"] is True, upstream
    statements = []
    def capture(conn, cursor, statement, parameters, context, many):
        statements.append(statement.strip().upper())
    event.listen(pg_engine, "before_cursor_execute", capture)
    monkeypatch.setattr(target_service, "assess", lambda *_: (_ for _ in ()).throw(AssertionError("nested target owner")))
    monkeypatch.setattr(rtisa_service, "read", lambda *_: (_ for _ in ()).throw(AssertionError("nested RTISA owner")))
    try:
        with Session(pg_engine) as db:
            result = subject.assess(db, request)
            assert not db.in_transaction()
    finally:
        event.remove(pg_engine, "before_cursor_execute", capture)
    assert statements[0] == "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"
    assert not any(statement.startswith(("INSERT ", "UPDATE ", "DELETE ")) for statement in statements)
    assert result["classification_complete"] is True, result
    assert [entry["source_id"] for entry in result["source_comparisons"]] == ["income:1"]


def test_postgresql_concurrent_writer_cannot_mix_target_and_rtisa_snapshots(pg_engine):
    request = _request(pg_engine)
    with Session(pg_engine) as verification_db:
        before = rtisa_service.read(
            verification_db, 1, request["expected_planning_calculation_input_fingerprint"]
        )
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
            return subject.assess(db, request)
    try:
        with ThreadPoolExecutor(1) as pool:
            pending = pool.submit(read_old)
            assert paused.wait(20)
            try:
                with Session(pg_engine) as writer, writer.begin():
                    writer.get(RecurringIncome, 1).amount = Decimal("999.00")
            finally:
                resume.set()
            old = pending.result(timeout=30)
    finally:
        resume.set()
        event.remove(pg_engine, "after_cursor_execute", intercept)
    assert old["classification_complete"] is True, old
    assert old["rtisa_admission_result_fingerprint"] == before["admission_result_fingerprint"]
    with Session(pg_engine) as db:
        fresh = subject.assess(db, _request(pg_engine))
    assert fresh["result_state"] == "block_no_result"
    assert fresh["failure_detail_code"] == "RTICB_TARGET_AUTHORITY_NOT_READY"


def test_postgresql_identity_map_is_expired_before_authoritative_snapshot(pg_engine):
    request = _request(pg_engine)
    with Session(pg_engine, expire_on_commit=False) as db:
        stale = db.get(RecurringIncome, 1)
        assert stale.amount != Decimal("777.00")
        db.commit()
        with Session(pg_engine) as writer, writer.begin():
            writer.get(RecurringIncome, 1).amount = Decimal("777.00")
        result = subject.assess(db, request)
        assert not db.in_transaction()
    assert result["result_state"] == "block_no_result"
    assert result["failure_detail_code"] == "RTICB_TARGET_AUTHORITY_NOT_READY"


def test_postgresql_semantic_and_technical_failure_cleanup(pg_engine, monkeypatch):
    request = _request(pg_engine)
    with Session(pg_engine) as db:
        semantic = subject.assess(db, request | {"expected_retirement_target_date": "2031-01-01"})
        assert semantic["result_state"] == "block_no_result"
        assert not db.in_transaction()

    original = planning_input_service.derive
    def fail_after_query(db, client_id):
        original(db, client_id)
        db.connection().exec_driver_sql("SELECT * FROM rticb_intentionally_missing_relation")
    monkeypatch.setattr(planning_input_service, "derive", fail_after_query)
    with Session(pg_engine) as db:
        with pytest.raises(DBAPIError, match="rticb_intentionally_missing_relation"):
            subject.assess(db, request)
        assert not db.in_transaction()


def test_postgresql_fresh_session_rejection_does_not_touch_caller_transaction(pg_engine):
    request = _request(pg_engine)
    with Session(pg_engine) as db:
        db.connection().exec_driver_sql("SELECT 1")
        transaction = db.get_transaction()
        result = subject.assess(db, request)
        assert result["failure_detail_code"] == "RTICB_REQUIRES_FRESH_TRANSACTION"
        assert db.get_transaction() is transaction
        assert db.in_transaction()
        db.rollback()


def test_mutation_oracle_detects_second_session_construction_on_actual_producer_flow(
    pg_engine, monkeypatch,
):
    request = _request(pg_engine)
    original = target_service.assess_in_snapshot
    reached = []
    connections = set()

    def capture(conn, cursor, statement, parameters, context, many):
        connections.add(id(conn))

    def mutated(db, client_id):
        result = original(db, client_id)
        with Session(pg_engine) as second:
            second.execute(text("SELECT 1"))
        reached.append("second_session")
        return result

    event.listen(pg_engine, "before_cursor_execute", capture)
    monkeypatch.setattr(target_service, "assess_in_snapshot", mutated)
    try:
        with pytest.raises(AssertionError, match="one database connection"):
            result = _assert_ordinary_success(pg_engine, request)
            assert len(connections) == 1, "RTICB must use one database connection"
    finally:
        event.remove(pg_engine, "before_cursor_execute", capture)
    assert reached == ["second_session"]
    monkeypatch.setattr(target_service, "assess_in_snapshot", original)
    _assert_ordinary_success(pg_engine, request)


def test_mutation_oracle_detects_commit_on_actual_producer_flow(pg_engine, monkeypatch):
    request = _request(pg_engine)
    original_reader = target_service.assess_in_snapshot
    reached = []
    with Session(pg_engine) as db:
        original_commit = db.commit
        commit_calls = []

        def observed_commit():
            commit_calls.append("commit")
            return original_commit()

        def mutated(received_db, client_id):
            result = original_reader(received_db, client_id)
            reached.append("commit")
            received_db.commit()
            return result

        monkeypatch.setattr(db, "commit", observed_commit)
        monkeypatch.setattr(target_service, "assess_in_snapshot", mutated)
        result = subject.assess(db, request)
        with pytest.raises(AssertionError, match="must not commit"):
            assert result["classification_complete"] is True
            assert commit_calls == [], "RTICB must not commit"
    assert reached == commit_calls == ["commit"]
    monkeypatch.setattr(target_service, "assess_in_snapshot", original_reader)
    _assert_ordinary_success(pg_engine, request)


def test_mutation_oracle_detects_explicit_flush_on_actual_producer_flow(pg_engine, monkeypatch):
    request = _request(pg_engine)
    original_reader = target_service.assess_in_snapshot
    reached = []
    with Session(pg_engine) as db:
        original_flush = db.flush
        flush_calls = []

        def observed_flush(*args, **kwargs):
            flush_calls.append("flush")
            return original_flush(*args, **kwargs)

        def mutated(received_db, client_id):
            result = original_reader(received_db, client_id)
            reached.append("flush")
            received_db.flush()
            return result

        monkeypatch.setattr(db, "flush", observed_flush)
        monkeypatch.setattr(target_service, "assess_in_snapshot", mutated)
        result = subject.assess(db, request)
        with pytest.raises(AssertionError, match="must not flush"):
            assert result["classification_complete"] is True
            assert flush_calls == [], "RTICB must not flush"
    assert reached == flush_calls == ["flush"]
    monkeypatch.setattr(target_service, "assess_in_snapshot", original_reader)
    _assert_ordinary_success(pg_engine, request)


def test_mutation_oracle_detects_actual_write_in_read_only_snapshot(pg_engine, monkeypatch):
    request = _request(pg_engine)
    original_reader = target_service.assess_in_snapshot
    reached = []

    def mutated(db, client_id):
        result = original_reader(db, client_id)
        reached.append("write")
        db.execute(text("UPDATE clients SET display_name=display_name WHERE client_id=1"))
        return result

    monkeypatch.setattr(target_service, "assess_in_snapshot", mutated)
    with Session(pg_engine) as db:
        with pytest.raises(DBAPIError, match="read-only"):
            subject.assess(db, request)
        assert not db.in_transaction()
    assert reached == ["write"]
    monkeypatch.setattr(target_service, "assess_in_snapshot", original_reader)
    _assert_ordinary_success(pg_engine, request)


def test_mutation_oracle_detects_nested_target_public_owner(pg_engine, monkeypatch):
    request = _request(pg_engine)
    original_reader = target_service.assess_in_snapshot
    reached = []

    def mutated(db, client_id):
        reached.append("target_public_assess")
        return target_service.assess(db, client_id)

    monkeypatch.setattr(target_service, "assess_in_snapshot", mutated)
    with Session(pg_engine) as db:
        with pytest.raises(target_service.RetirementMonthlyIncomeTargetError):
            subject.assess(db, request)
        assert not db.in_transaction()
    assert reached == ["target_public_assess"]
    monkeypatch.setattr(target_service, "assess_in_snapshot", original_reader)
    _assert_ordinary_success(pg_engine, request)


def test_mutation_oracle_detects_nested_rtisa_public_owner(pg_engine, monkeypatch):
    request = _request(pg_engine)
    original_reader = rtisa_service.read_in_snapshot
    reached = []

    def mutated(db, client_id, expected):
        reached.append("rtisa_public_read")
        return rtisa_service.read(db, client_id, expected)

    monkeypatch.setattr(rtisa_service, "read_in_snapshot", mutated)
    with Session(pg_engine) as db:
        with pytest.raises(rtisa_service.RetirementTargetIncomeSourceAdmissionError):
            subject.assess(db, request)
        assert not db.in_transaction()
    assert reached == ["rtisa_public_read"]
    monkeypatch.setattr(rtisa_service, "read_in_snapshot", original_reader)
    _assert_ordinary_success(pg_engine, request)
