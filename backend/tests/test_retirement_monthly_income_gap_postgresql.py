"""PostgreSQL 16 snapshot and cleanup evidence for RMIGA."""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Event

import pytest
from sqlalchemy import event, text
from sqlalchemy.exc import DBAPIError, InvalidRequestError
from sqlalchemy.orm import Session

from app.models.retirement_facts import RecurringIncome
from app.services import retirement_monthly_income_gap_service as subject
from app.services import retirement_target_date_comparable_monthly_income_service as cmia
from test_recovery_migration_postgresql import postgres_url
from test_retirement_target_date_comparable_monthly_income_postgresql import (
    _request, pg_engine,
)


def test_rmiga_postgresql_single_read_only_snapshot_exact_gap_and_cleanup(pg_engine):
    request = _request(pg_engine)
    statements = []

    def capture(_conn, _cursor, statement, _parameters, _context, _many):
        statements.append(statement.strip().upper())

    event.listen(pg_engine, "before_cursor_execute", capture)
    try:
        with Session(pg_engine) as db:
            result = subject.assess(db, request)
            assert not db.in_transaction()
    finally:
        event.remove(pg_engine, "before_cursor_execute", capture)
    assert statements[0] == "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"
    assert not any(statement.startswith(("INSERT ", "UPDATE ", "DELETE ", "COMMIT")) for statement in statements)
    assert result["result_state"] == "COMPLETE"
    assert result["comparable_monthly_income"]["numerator"] == "1200"
    assert result["target_monthly_amount"]["numerator"] == "24000"
    assert result["monthly_gap"] == {
        "numerator": "22800", "denominator": "1", "currency": "ILS", "frequency": "MONTHLY",
    }
    assert result["gap_state"] == "SHORTFALL"


def test_rmiga_postgresql_concurrent_writer_cannot_mix_target_and_income_snapshot(pg_engine):
    request = _request(pg_engine)
    paused = Event()
    resume = Event()
    reader_connection = [None]

    def intercept(conn, _cursor, statement, _parameters, _context, _many):
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
    assert old["result_state"] == "COMPLETE"
    assert old["comparable_monthly_income"]["numerator"] == "1200"
    assert old["target_monthly_amount"]["numerator"] == "24000"
    assert old["monthly_gap"]["numerator"] == "22800"
    with Session(pg_engine) as db:
        fresh = subject.assess(db, _request(pg_engine))
    assert fresh["result_state"] == "BLOCK_NO_GAP"
    assert fresh["observed_cmia_failure_detail_code"] == "CMIA_UPSTREAM_COMPARISON_BLOCKED"


def test_rmiga_postgresql_fresh_session_rejection_preserves_caller_transaction(pg_engine):
    with Session(pg_engine) as db:
        db.connection().exec_driver_sql("SELECT 1")
        transaction = db.get_transaction()
        with pytest.raises(subject.RMIGAContractError) as caught:
            subject.assess(db, _request(pg_engine))
        assert caught.value.code == "RMIGA_REQUIRES_FRESH_TRANSACTION"
        assert db.get_transaction() is transaction and db.in_transaction()
        db.rollback()


def test_rmiga_postgresql_technical_database_failure_rolls_back_and_propagates(
    pg_engine, monkeypatch,
):
    request = _request(pg_engine)

    def database_failure(db, _request_value):
        db.execute(text("SELECT * FROM rmiga_deliberately_missing_relation"))

    monkeypatch.setattr(cmia, "assess_with_target_in_snapshot", database_failure)
    with Session(pg_engine) as db:
        with pytest.raises(DBAPIError):
            subject.assess(db, request)
        assert not db.in_transaction()


def test_rmiga_postgresql_partial_connection_acquisition_after_autobegin_is_cleaned(
    pg_engine, monkeypatch,
):
    request = _request(pg_engine)
    with Session(pg_engine) as db:
        acquire = db.connection

        def partial_acquisition():
            acquire()
            assert db.in_transaction()
            raise OSError("partial acquisition")

        monkeypatch.setattr(db, "connection", partial_acquisition)
        with pytest.raises(OSError, match="partial acquisition"):
            subject.assess(db, request)
        assert not db.in_transaction()


@pytest.mark.parametrize("original_failure", [False, True])
def test_rmiga_postgresql_rollback_failure_wins_invalidates_and_poisons_session(
    pg_engine, monkeypatch, original_failure,
):
    request = _request(pg_engine)
    with Session(pg_engine) as db:
        retained = []
        invalidations = []
        acquire = db.connection

        def capture_connection():
            connection = acquire()
            if not retained:
                retained.append(connection)
                invalidate = connection.invalidate

                def capture_invalidate(*args, **kwargs):
                    invalidations.append(True)
                    return invalidate(*args, **kwargs)

                monkeypatch.setattr(connection, "invalidate", capture_invalidate)
            return connection

        monkeypatch.setattr(db, "connection", capture_connection)
        monkeypatch.setattr(
            db, "rollback", lambda: (_ for _ in ()).throw(OSError("rmiga rollback failed")),
        )
        if original_failure:
            monkeypatch.setattr(
                cmia, "assess_with_target_in_snapshot",
                lambda *_: (_ for _ in ()).throw(RuntimeError("original technical failure")),
            )
        with pytest.raises(OSError, match="rmiga rollback failed"):
            subject.assess(db, request)
        assert retained and invalidations
        with pytest.raises(InvalidRequestError, match="permanently unusable"):
            db.scalar(text("SELECT 1"))
