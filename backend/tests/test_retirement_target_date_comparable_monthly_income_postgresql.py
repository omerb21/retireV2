"""PostgreSQL 16 snapshot and transaction evidence for CMIA."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from threading import Event

import pytest
from pydantic import TypeAdapter
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.models.retirement_facts import RecurringIncome
from app.schemas.retirement_income_source_basis import CRTISBACommand
from app.services import planning_input_service
from app.services import retirement_monthly_income_target_service as target_service
from app.services import retirement_target_date_comparable_monthly_income_service as subject
from app.services import retirement_target_date_income_comparison_basis_service as rticb_service
from app.services import retirement_target_date_income_source_basis_service as crtisba_service
from app.services import retirement_target_date_income_source_admission_service as rtisa_service
from test_planning_input import choose, view
from test_recovery_migration_postgresql import postgres_url
from test_retirement_target import payload as target_payload, save as save_target
from test_retirement_monthly_income_target_postgresql import command as target_command, confirm as confirm_target
from test_retirement_target_date_income_source_basis_postgresql import (
    ROLE as CRTISBA_APPLICATION_ROLE,
    migrate as migrate_with_crtisba_role,
)


@pytest.fixture
def pg_engine(postgres_url):
    engine = create_engine(postgres_url, pool_size=5)
    with engine.begin() as connection:
        connection.execute(text(f"CREATE ROLE {CRTISBA_APPLICATION_ROLE} NOLOGIN"))
    migrate_with_crtisba_role(postgres_url, "upgrade", "c4e8a2f6b731")
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
    confirm_target(engine, target_command(engine, income_basis="GROSS"))
    with Session(engine) as db:
        collection = crtisba_service.read(db, 1)
    entry = collection["source_basis_entries"][0]
    command = TypeAdapter(CRTISBACommand).validate_python({
        "schema_version": "CRTISBA_RECURRING_CLASSIFY_COMMAND_V1",
        "operation": "CLASSIFY", "source_kind": "RECURRING_INCOME",
        "expected_decision_version": 0,
        "expected_planning_calculation_input_fingerprint": collection["planning_calculation_input_fingerprint"],
        "expected_source_version": entry["source_version"],
        "expected_source_fingerprint": entry["source_fingerprint"],
        "expected_amount_authority_fingerprint": entry["amount_authority_fingerprint"],
        "price_basis": "NOMINAL_AT_RETIREMENT_TARGET_DATE", "price_reference_date": None,
    })
    with Session(engine) as db:
        crtisba_service.write(db, 1, "income:1", command, "authenticated-professional")
    yield engine
    engine.dispose()


def _request(engine):
    planning = view(engine)
    return {
        "client_id": 1,
        "expected_planning_calculation_input_fingerprint": planning["planning_calculation_input_fingerprint"],
        "expected_retirement_target_date": planning["retirement_target"]["retirement_target_date"],
    }


def test_postgresql_exact_result_single_read_only_snapshot_and_cleanup(pg_engine, monkeypatch):
    request = _request(pg_engine)
    statements = []

    def capture(_conn, _cursor, statement, _parameters, _context, _many):
        statements.append(statement.strip().upper())

    event.listen(pg_engine, "before_cursor_execute", capture)
    monkeypatch.setattr(rticb_service, "assess", lambda *_: (_ for _ in ()).throw(AssertionError("nested RTICB owner")))
    monkeypatch.setattr(crtisba_service, "read", lambda *_: (_ for _ in ()).throw(AssertionError("nested CRTISBA owner")))
    monkeypatch.setattr(rtisa_service, "read", lambda *_: (_ for _ in ()).throw(AssertionError("nested RTISA owner")))
    monkeypatch.setattr(target_service, "assess", lambda *_: (_ for _ in ()).throw(AssertionError("nested target owner")))
    try:
        with Session(pg_engine) as db:
            result = subject.assess(db, request)
            assert not db.in_transaction()
    finally:
        event.remove(pg_engine, "before_cursor_execute", capture)
    assert statements[0] == "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"
    assert not any(statement.startswith(("INSERT ", "UPDATE ", "DELETE ", "COMMIT")) for statement in statements)
    assert result["result_state"] == "COMPLETE"
    assert result["total_monthly_equivalent"] == {
        "numerator": "1200", "denominator": "1", "currency": "ILS", "frequency": "MONTHLY",
    }
    assert result["source_count"] == 1


def test_postgresql_concurrent_writer_cannot_mix_amount_or_authority_snapshots(pg_engine):
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
    assert old["total_monthly_equivalent"]["numerator"] == "1200"
    with Session(pg_engine) as db:
        fresh = subject.assess(db, _request(pg_engine))
    assert fresh["result_state"] == "BLOCK_NO_TOTAL"
    assert fresh["observed_upstream_failure_detail_code"] == "RTICB_TARGET_AUTHORITY_NOT_READY"


def test_postgresql_technical_failure_rolls_back_and_propagates(pg_engine, monkeypatch):
    request = _request(pg_engine)
    original = planning_input_service.derive

    def fail_after_query(db, client_id):
        original(db, client_id)
        db.connection().exec_driver_sql("SELECT * FROM cmia_intentionally_missing_relation")

    monkeypatch.setattr(planning_input_service, "derive", fail_after_query)
    with Session(pg_engine) as db:
        with pytest.raises(DBAPIError, match="cmia_intentionally_missing_relation"):
            subject.assess(db, request)
        assert not db.in_transaction()


def test_postgresql_fresh_session_rejection_preserves_caller_transaction(pg_engine):
    with Session(pg_engine) as db:
        db.connection().exec_driver_sql("SELECT 1")
        transaction = db.get_transaction()
        with pytest.raises(subject.CMIAContractError) as caught:
            subject.assess(db, _request(pg_engine))
        assert caught.value.code == "CMIA_REQUIRES_FRESH_TRANSACTION"
        assert db.get_transaction() is transaction and db.in_transaction()
        db.rollback()
