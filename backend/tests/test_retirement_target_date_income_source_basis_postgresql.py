from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
import os
from pathlib import Path
import subprocess
import sys

import pytest
from pydantic import TypeAdapter
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.schemas.retirement_income_source_basis import CRTISBACommand
from app.models.canonical_manual_pension_source import CanonicalManualPensionSource
from app.services import retirement_target_date_income_source_basis_service as subject
from app.services.canonical_component_conversion_service import execute as execute_conversion
from test_canonical_component_conversion import seeded as seeded_product, request as conversion_request
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
        with engine.connect() as connection:
            assert 160000 <= int(connection.scalar(text("SHOW server_version_num"))) < 170000
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
        # The public owners establish the accepted isolation before any
        # authoritative service query.  Read cleanup ends the snapshot by
        # rollback; write setup is SERIALIZABLE.
        with Session(engine) as db:
            subject._pristine(db)
            subject._begin(db, write=False)
            assert db.scalar(text("SHOW transaction_isolation")) == "repeatable read"
            assert db.scalar(text("SHOW transaction_read_only")) == "on"
            subject._rollback(db)
            assert not db.in_transaction()
        with Session(engine) as db:
            subject._pristine(db)
            subject._begin(db, write=True)
            assert db.scalar(text("SHOW transaction_isolation")) == "serializable"
            subject._rollback(db)
            assert not db.in_transaction()
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
            # Ordinary trigger oracle -> actual trigger-target mutation -> same
            # oracle fails -> transactional restoration -> ordinary oracle.
            transaction = connection.begin()
            try:
                connection.execute(text("CREATE TEMP TABLE crtisba_wrong_trigger_target(id integer)"))
                connection.execute(text(
                    f"DROP TRIGGER trg_crtisba_decision_immutable ON {subject.Decision.__tablename__}"
                ))
                connection.execute(text(
                    "CREATE TRIGGER trg_crtisba_decision_immutable BEFORE UPDATE OR DELETE "
                    "ON crtisba_wrong_trigger_target FOR EACH ROW EXECUTE FUNCTION "
                    "reject_crtisba_decision_mutation()"
                ))
                # The unchanged immutability oracle is now killed by the mutation:
                # UPDATE succeeds instead of producing P7501.
                connection.execute(text(
                    f"UPDATE {subject.Decision.__tablename__} SET decision_actor=decision_actor"
                ))
            finally:
                transaction.rollback()
            transaction = connection.begin()
            try:
                with pytest.raises(Exception) as restored:
                    connection.execute(text(
                        f"UPDATE {subject.Decision.__tablename__} SET decision_actor=decision_actor"
                    ))
                assert (restored.value.orig.pgcode or restored.value.orig.sqlstate) == "P7501"
                assert restored.value.orig.diag.constraint_name == "trg_crtisba_decision_immutable"
            finally:
                transaction.rollback()

            # A real check violation remains distinct from trigger immutability.
            transaction = connection.begin()
            try:
                with pytest.raises(Exception) as checked:
                    connection.execute(text(f"""
                        INSERT INTO {subject.Decision.__tablename__} (
                          client_id,source_id,source_kind,decision_version,
                          planning_calculation_input_fingerprint,recurring_source_version_fingerprint,
                          source_fingerprint,amount_authority_fingerprint,income_basis,
                          income_basis_provenance,price_basis,price_basis_provenance,
                          decision_actor,decision_fingerprint
                        ) SELECT client_id,source_id,source_kind,0,
                          planning_calculation_input_fingerprint,recurring_source_version_fingerprint,
                          source_fingerprint,amount_authority_fingerprint,income_basis,
                          income_basis_provenance,price_basis,price_basis_provenance,
                          decision_actor,decision_fingerprint
                        FROM {subject.Decision.__tablename__} LIMIT 1
                    """))
                assert (checked.value.orig.pgcode or checked.value.orig.sqlstate) == "23514"
                assert checked.value.orig.diag.constraint_name == "ck_crtisba_decision_version_positive"
            finally:
                transaction.rollback()
            transaction = connection.begin()
            try:
                connection.execute(text(f"SET LOCAL ROLE {ROLE}"))
                assert connection.scalar(text(f"SELECT count(*) FROM {subject.Decision.__tablename__}")) == 1
                for forbidden in (
                    f"UPDATE {subject.Decision.__tablename__} SET decision_actor='forbidden'",
                    f"DELETE FROM {subject.Decision.__tablename__}",
                    f"TRUNCATE TABLE {subject.Decision.__tablename__}",
                ):
                    with pytest.raises(Exception):
                        connection.execute(text(forbidden))
                    transaction.rollback()
                    transaction = connection.begin()
                    connection.execute(text(f"SET LOCAL ROLE {ROLE}"))
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

        # All three polymorphic source-lock targets are exercised against real
        # PostgreSQL and must emit FOR UPDATE on the addressed table.
        with Session(engine) as db, db.begin():
            db.add(CanonicalManualPensionSource(
                manual_pension_source_id="manual-lock", client_id=1,
                input_mode="entered", payer_name="payer", description="lock",
                source_reference="test", monthly_amount=Decimal("10.00"),
                balance=None, annuity_factor=None, pension_start_date=date(2030, 1, 1),
                base_amount_effective_date=date(2026, 1, 1), tax_treatment="taxable",
                indexation_method="none", fixed_indexation_rate=None,
                temporal_authority_explicit=True, source_note=None,
                lifecycle_status="current", version=1,
            ))
        product = seeded_product(engine)
        with Session(engine) as db, db.begin():
            converted = execute_conversion(
                db, 1, conversion_request(product, destination="pension"), "trusted:professional"
            )
        destination_id = converted["conversions"][0]["destination_id"]
        expected_targets = {
            source_id: table for source_id, table in (
                (source_id, "recurring_income"),
                ("manual:manual-lock", "canonical_manual_pension_sources"),
                (f"conversion:{destination_id}", "canonical_pension_destinations"),
            )
        }
        from sqlalchemy import event
        for addressed, table in expected_targets.items():
            observed = []
            def capture_lock(conn, cursor, statement, *args):
                observed.append(statement.lower())
            event.listen(engine, "before_cursor_execute", capture_lock)
            try:
                with Session(engine) as db, db.begin():
                    subject._lock_source(
                        db, 1, addressed,
                        "RECURRING_INCOME" if addressed.startswith("income:") else "PENSION",
                    )
            finally:
                event.remove(engine, "before_cursor_execute", capture_lock)
            assert any(table in statement and "for update" in statement for statement in observed), (addressed, observed)

        # The database, rather than a fabricated exception object, emits both
        # retry-class SQLSTATEs consumed by the closed CRTISBA classifier.
        for sqlstate in ("40001", "40P01"):
            with Session(engine) as db:
                subject._begin(db, write=True)
                with pytest.raises(DBAPIError) as aborted:
                    db.execute(text(
                        "DO $$ BEGIN RAISE EXCEPTION 'controlled abort' "
                        f"USING ERRCODE='{sqlstate}'; END $$"
                    ))
                observed_state = aborted.value.orig.pgcode or aborted.value.orig.sqlstate
                assert observed_state == sqlstate
                assert subject._classify_integrity(aborted.value, "COMMIT_DISPATCHED").code == "CRTISBA_SERIALIZATION_FAILURE"
                db.rollback()

        # Real connection loss before dispatch is known-not-committed.  Once
        # the owner has entered COMMIT_DISPATCHED, the same observable driver
        # evidence is uncertain and must be reconciled by a fresh explicit GET.
        for phase, expected in (
            ("IN_TRANSACTION", "CRTISBA_DATABASE_FAILURE"),
            ("COMMIT_DISPATCHED", "CRTISBA_COMMIT_OUTCOME_UNKNOWN"),
        ):
            db = Session(engine)
            try:
                subject._begin(db, write=True)
                backend_pid = db.scalar(text("SELECT pg_backend_pid()"))
                with engine.begin() as killer:
                    assert killer.scalar(text("SELECT pg_terminate_backend(:pid)"), {"pid": backend_pid}) is True
                with pytest.raises(DBAPIError) as disconnected:
                    if phase == "COMMIT_DISPATCHED":
                        db.commit()
                    else:
                        db.execute(text("SELECT 1"))
                assert disconnected.value.connection_invalidated or str(
                    disconnected.value.orig.pgcode or disconnected.value.orig.sqlstate or ""
                ).startswith("08")
                assert subject._classify_integrity(disconnected.value, phase).code == expected
            finally:
                db.close()
            reconciled, reconciled_entry = _current(engine, source_id)
            assert reconciled_entry["decision_version"] == 2
            assert reconciled["schema_version"] == "CRTISBA_COLLECTION_RESULT_V1"
    finally:
        engine.dispose()
