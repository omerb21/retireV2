from concurrent.futures import ThreadPoolExecutor
from datetime import date
import os
from pathlib import Path
import subprocess
import sys

import pytest
from pydantic import TypeAdapter
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from app.schemas.retirement_income_source_basis import CRTISBACommand
from app.services import retirement_target_date_income_source_basis_service as subject
from test_planning_input import choose, income, view
from test_recovery_migration_postgresql import postgres_url
from test_retirement_target import payload as target_payload, save as save_target

BACKEND = Path(__file__).resolve().parents[1]
ROLE = "crtisba_test_app"


def migrate(url, *args):
    result = subprocess.run([sys.executable, "-m", "alembic", *args], cwd=BACKEND,
        env={**os.environ, "DATABASE_URL": url, "CRTISBA_APPLICATION_DB_ROLE": ROLE,
             "PYTHONIOENCODING": "utf-8"}, capture_output=True, text=True, encoding="utf-8", timeout=180)
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


def _prepare(url):
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("CREATE ROLE crtisba_test_app NOLOGIN"))
    migrate(url, "upgrade", "b3c9d6f2a410")
    old = set(inspect(engine).get_table_names())
    migrate(url, "upgrade", "c4e8a2f6b731")
    assert set(inspect(engine).get_table_names()) - old == {subject.Decision.__tablename__}
    return engine


def _source(engine):
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO clients(client_id,display_name,id_number) VALUES(1,'test','123')"))
    choose(engine)
    save_target(engine, target_payload(engine))
    source_id = income(engine, amount_basis="gross", frequency="monthly",
                       source_status="planner entered", verification_state="reviewed")
    return f"income:{source_id}"


def _current(engine, source_id):
    with Session(engine) as db:
        result = subject.read(db, 1)
    return result, next(item for item in result["source_basis_entries"] if item["source_id"] == source_id)


def _command(result, entry):
    return TypeAdapter(CRTISBACommand).validate_python({
        "schema_version": "CRTISBA_RECURRING_CLASSIFY_COMMAND_V1", "operation": "CLASSIFY",
        "source_kind": "RECURRING_INCOME", "expected_decision_version": entry["decision_version"] or 0,
        "expected_planning_calculation_input_fingerprint": result["planning_calculation_input_fingerprint"],
        "expected_source_version": entry["source_version"], "expected_source_fingerprint": entry["source_fingerprint"],
        "expected_amount_authority_fingerprint": entry["amount_authority_fingerprint"],
        "price_basis": "REAL_AT_REFERENCE_DATE", "price_reference_date": "2026-01-01",
    })


def test_postgresql_migration_trigger_privileges_transactions_and_concurrency(postgres_url):
    engine = _prepare(postgres_url)
    try:
        assert migrate(postgres_url, "heads").strip() == "c4e8a2f6b731 (head)"
        columns = {item["name"]: item for item in inspect(engine).get_columns(subject.Decision.__tablename__)}
        assert set(columns) == {
            "decision_id", "client_id", "source_id", "source_kind", "decision_version",
            "planning_calculation_input_fingerprint", "pension_source_version",
            "recurring_source_version_fingerprint", "source_fingerprint", "amount_authority_fingerprint",
            "pension_source_execution_fingerprint", "pension_source_result_fingerprint",
            "portfolio_source_entry_fingerprint", "retirement_target_date", "income_basis",
            "income_basis_provenance", "price_basis", "price_reference_date", "price_basis_provenance",
            "decision_actor", "decided_at", "decision_fingerprint",
        }
        with engine.connect() as connection:
            trigger = connection.execute(text("""SELECT action_timing,event_manipulation,action_orientation
                FROM information_schema.triggers WHERE trigger_name='trg_crtisba_decision_immutable'
                ORDER BY event_manipulation""")).all()
            assert trigger == [("BEFORE", "DELETE", "ROW"), ("BEFORE", "UPDATE", "ROW")]
            grants = set(connection.execute(text("""SELECT privilege_type FROM information_schema.role_table_grants
                WHERE grantee=:role AND table_name=:table"""), {"role": ROLE, "table": subject.Decision.__tablename__}).scalars())
            assert grants == {"SELECT", "INSERT"}
            sequence = connection.scalar(text("SELECT pg_get_serial_sequence(:table_name, 'decision_id')"), {"table_name": subject.Decision.__tablename__})
            assert connection.scalar(text("SELECT has_sequence_privilege(:role, :sequence, 'USAGE')"), {"role": ROLE, "sequence": sequence})
        migrate(postgres_url, "downgrade", "b3c9d6f2a410")
        assert subject.Decision.__tablename__ not in inspect(engine).get_table_names()
        migrate(postgres_url, "upgrade", "c4e8a2f6b731")
        source_id = _source(engine)
        before, entry = _current(engine, source_id)
        statements = []
        from sqlalchemy import event
        def capture(conn, cursor, statement, *args): statements.append(statement.upper())
        event.listen(engine, "before_cursor_execute", capture)
        try:
            with Session(engine) as db:
                written = subject.write(db, 1, source_id, _command(before, entry), "trusted:professional")
        finally:
            event.remove(engine, "before_cursor_execute", capture)
        assert written["decision_version"] == 1
        assert any("FOR UPDATE" in item and "RECURRING_INCOME" in item for item in statements)
        assert any("FOR UPDATE" in item and subject.Decision.__tablename__.upper() in item for item in statements)
        with engine.connect() as connection:
            row = connection.execute(text(f"SELECT decision_actor, decided_at FROM {subject.Decision.__tablename__}" )).one()
            assert row.decision_actor == "trusted:professional" and row.decided_at is not None
            connection.rollback()
            for verb in ("UPDATE", "DELETE"):
                transaction = connection.begin()
                try:
                    statement = (f"UPDATE {subject.Decision.__tablename__} SET decision_actor='x'" if verb == "UPDATE"
                                 else f"DELETE FROM {subject.Decision.__tablename__}")
                    with pytest.raises(Exception) as caught:
                        connection.execute(text(statement))
                    orig = caught.value.orig
                    assert (getattr(orig, "pgcode", None) or getattr(orig, "sqlstate", None)) == "P7501"
                    assert orig.diag.constraint_name == "trg_crtisba_decision_immutable"
                finally:
                    transaction.rollback()
            transaction = connection.begin()
            try:
                connection.execute(text(f"SET LOCAL ROLE {ROLE}"))
                assert connection.scalar(text(f"SELECT count(*) FROM {subject.Decision.__tablename__}")) == 1
                with pytest.raises(Exception):
                    connection.execute(text(f"UPDATE {subject.Decision.__tablename__} SET decision_actor='forbidden'"))
            finally:
                transaction.rollback()
        current_result, current_entry = _current(engine, source_id)
        command = _command(current_result, current_entry)
        assert current_entry["decision_state"] == "CURRENT" and command.expected_decision_version == 1, current_entry
        def append(actor):
            try:
                with Session(engine) as db:
                    return subject.write(db, 1, source_id, command, actor)["decision_version"]
            except subject.CRTISBAError as exc:
                return exc.code
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(append, ["actor:a", "actor:b"]))
        assert 2 in outcomes
        assert any(item in {"CRTISBA_DECISION_VERSION_CONFLICT", "CRTISBA_SERIALIZATION_FAILURE"} for item in outcomes), outcomes
        with engine.connect() as connection:
            assert connection.scalar(text(f"SELECT count(*) FROM {subject.Decision.__tablename__}")) == 2
    finally:
        engine.dispose()
