"""Targeted Supervisor 108 PostgreSQL migration acceptance.

Runs only on the existing isolated localhost PG16 schema fixture, never on
production databases or the shared public schema.
"""
import importlib.util
from pathlib import Path

from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from sqlalchemy import text

# Re-export the original base fixture for this narrowly collected pytest module.
from tests.test_scenario_unified_result_real_postgresql import pg16 as pg16_base
from tests.test_scenario_unified_engine_binding_postgresql import (
    pg16, _prepared_fixation_sources, _prepared_review,
)


def _constraint(conn, schema, table, name):
    return conn.execute(text("""
        SELECT pg_get_constraintdef(c.oid)
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        WHERE n.nspname = :schema AND t.relname = :table AND c.conname = :name
    """), {"schema": schema, "table": table, "name": name}).scalar_one()


def _status_length(conn, schema, table):
    return conn.execute(text("""
        SELECT character_maximum_length
        FROM information_schema.columns
        WHERE table_schema = :schema AND table_name = :table
          AND column_name = 'status'
    """), {"schema": schema, "table": table}).scalar_one()


def test_existing_draft_preserved_by_internal_approval_status_migration(pg16):
    factory, scoped = pg16
    _prepared_fixation_sources(factory)
    _prepared_review(factory)
    schema = scoped.get_execution_options()["schema_translate_map"][None]
    file = (Path(__file__).resolve().parents[1] / "alembic" / "versions"
            / "a108c7e5d2b9_internal_fixation_approval.py")
    spec = importlib.util.spec_from_file_location("internal_approval_migration", file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.revision == "a108c7e5d2b9"
    assert module.down_revision == "e53f1c0a7d23"
    names = [
        ("scenario_fixation_approval_heads", "ck_fixation_approval_head_status"),
        ("scenario_fixation_approval_revisions", "ck_fixation_approval_revision_status"),
    ]
    with scoped.begin() as conn:
        conn.execute(text(f'SET LOCAL search_path TO "{schema}", public'))
        # Simulate the existing DRAFT/BLOCKED constraint before running the
        # new migration against preexisting revision rows, including the
        # original VARCHAR(16) status columns.
        for table, name in names:
            conn.execute(text(f'ALTER TABLE "{schema}".{table} DROP CONSTRAINT {name}'))
            conn.execute(text(
                f'ALTER TABLE "{schema}".{table} '
                'ALTER COLUMN status TYPE VARCHAR(16)'
            ))
            conn.execute(text(
                f'ALTER TABLE "{schema}".{table} ADD CONSTRAINT {name} '
                "CHECK (status IN ('DRAFT','BLOCKED'))"
            ))
        old_op = module.op
        try:
            module.op = Operations(MigrationContext.configure(conn))
            module.upgrade()
        finally:
            module.op = old_op
        for table, name in names:
            definition = _constraint(conn, schema, table, name)
            assert "APPROVED_INTERNAL" in definition
            assert "DRAFT" in definition
            assert _status_length(conn, schema, table) == 32
        row = conn.execute(text(
            f'SELECT status, approval_version FROM "{schema}".scenario_fixation_approval_revisions '
            "WHERE scenario_id = 'a1'"
        )).one()
        assert row == ("DRAFT", 1)
    with factory() as db:
        from app.services.scenario_fixation_approval_service import history
        rows = history(db, 7, "a1")
        assert rows[0]["status"] == "DRAFT"
