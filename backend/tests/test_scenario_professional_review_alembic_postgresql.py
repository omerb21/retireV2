"""SC-05E: run only the new Alembic revision in a disposable local PostgreSQL schema.

Do not touch the database's alembic_version or apply a global migration.
"""
import importlib.util
import os
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

import pytest
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text

from app.db.base import Base, load_all_models
from app.models.client import Client
from app.models.scenario_draft import ScenarioDraft

load_all_models()


def _local_url():
    value = os.getenv("SCENARIO_TEST_POSTGRES_URL")
    if not value:
        pytest.skip("dedicated PostgreSQL test URL absent")
    parsed = urlsplit(value)
    if parsed.hostname not in {"localhost", "127.0.0.1", "::1"} or parsed.path != "/retire_v2_scenario_test":
        pytest.fail("Only local retire_v2_scenario_test is permitted")
    return value


def _dependency_closure(*tables):
    result = set(tables)
    pending = list(tables)
    while pending:
        table = pending.pop()
        for fk in table.foreign_keys:
            parent = fk.column.table
            if parent not in result:
                result.add(parent)
                pending.append(parent)
    return list(result)


def test_upgrade_downgrade_on_disposable_postgresql_schema(monkeypatch):
    engine = create_engine(_local_url())
    if engine.dialect.name != "postgresql":
        pytest.fail("PostgreSQL required")
    schema = "sc05e_migration_" + uuid4().hex[:12]
    scoped = engine.execution_options(schema_translate_map={None: schema})
    file = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "c5e019a47d62_professional_coefficient_reviews.py"
    spec = importlib.util.spec_from_file_location("sc05e_election_migration", file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.revision == "c5e019a47d62"
    assert module.down_revision == "b7c5e1a90342"
    try:
        with engine.begin() as conn:
            conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        with scoped.begin() as conn:
            monkeypatch.setenv("CRTISBA_APPLICATION_DB_ROLE", conn.execute(text("SELECT current_user")).scalar_one())
            conn.execute(text(f'SET LOCAL search_path TO "{schema}", public'))
            Base.metadata.create_all(conn, tables=_dependency_closure(Client.__table__, ScenarioDraft.__table__))
            original_op = module.op
            try:
                module.op = Operations(MigrationContext.configure(conn))
                module.upgrade()
                columns = {c["name"] for c in inspect(conn).get_columns("scenario_coefficient_professional_reviews", schema=schema)}
                assert columns == {
                    "review_id", "scenario_id", "client_id", "scenario_version",
                    "decision_id", "product_id", "component_id", "product_version",
                    "manifest_fingerprint", "inventory_fingerprint", "election_fingerprint",
                    "source_fingerprint", "professional_actor_id", "reviewed_at",
                    "review_reference", "decision", "record_fingerprint", "created_at",
                }
                assert "scenario_coefficient_professional_reviews" in inspect(conn).get_table_names(schema=schema)
                module.downgrade()
                assert "scenario_coefficient_professional_reviews" not in inspect(conn).get_table_names(schema=schema)
                module.upgrade()
                assert "scenario_coefficient_professional_reviews" in inspect(conn).get_table_names(schema=schema)
            finally:
                module.op = original_op
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        scoped.dispose()
        engine.dispose()
