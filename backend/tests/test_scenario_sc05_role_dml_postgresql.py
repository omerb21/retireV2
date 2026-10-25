"""PostgreSQL role DML acceptance for both SC-05 migrations.

Requires dedicated local test DB with CREATEDB/CREATEROLE-capable test user.
Creates isolated disposable schema and temporary NOLOGIN role, both rolled back.
"""
import importlib.util
import os
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

import pytest
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from app.db.base import Base, load_all_models
from app.models.client import Client
from app.models.scenario_draft import ScenarioDraft

load_all_models()


def _closure(*tables):
    found = set(tables)
    pending = list(tables)
    while pending:
        for fk in pending.pop().foreign_keys:
            parent = fk.column.table
            if parent not in found:
                found.add(parent)
                pending.append(parent)
    return list(found)


def _revision(filename):
    source = Path(__file__).resolve().parents[1] / "alembic" / "versions" / filename
    spec = importlib.util.spec_from_file_location(filename.removesuffix(".py"), source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sc05_application_role_can_only_perform_allowed_dml(monkeypatch):
    url = os.getenv("SCENARIO_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("dedicated local PostgreSQL URL not configured")
    parsed = urlsplit(url)
    if parsed.hostname not in {"localhost", "127.0.0.1", "::1"} or parsed.path != "/retire_v2_scenario_test":
        pytest.fail("only retire_v2_scenario_test is allowed")
    engine = create_engine(url)
    schema = "sc05_acl_" + uuid4().hex[:10]
    role = "sc05_role_" + uuid4().hex[:10]
    try:
        # One rolled-back transaction: no persistent tables, grants or roles.
        with engine.connect() as raw:
            tx = raw.begin()
            try:
                try:
                    raw.execute(text(f'CREATE ROLE "{role}" NOLOGIN'))
                except DBAPIError as exc:
                    tx.rollback()
                    pytest.skip("test database user lacks CREATEROLE: " + str(exc.orig).splitlines()[0])
                raw.execute(text(f'CREATE SCHEMA "{schema}"'))
                raw.execute(text(f'GRANT USAGE ON SCHEMA "{schema}" TO "{role}"'))
                raw.execute(text(f'SET LOCAL search_path TO "{schema}", public'))
                Base.metadata.create_all(raw, tables=_closure(Client.__table__, ScenarioDraft.__table__))
                monkeypatch.setenv("CRTISBA_APPLICATION_DB_ROLE", role)
                for name in (
                    "b7c5e1a90342_scenario_pension_elections.py",
                    "c5e019a47d62_professional_coefficient_reviews.py",
                ):
                    module = _revision(name)
                    old_op = module.op
                    try:
                        module.op = Operations(MigrationContext.configure(raw))
                        module.upgrade()
                    finally:
                        module.op = old_op
                checks = (
                    ("scenario_draft_pension_elections", {"SELECT", "INSERT", "DELETE"}, {"UPDATE"}),
                    ("scenario_coefficient_professional_reviews", {"SELECT", "INSERT"}, {"UPDATE", "DELETE"}),
                )
                for table, allowed, forbidden in checks:
                    qualified = f'"{schema}"."{table}"'
                    for command in sorted(allowed | forbidden):
                        if command == "SELECT":
                            sql = f"SELECT * FROM {qualified} WHERE FALSE"
                        elif command == "INSERT":
                            sql = f"INSERT INTO {qualified} DEFAULT VALUES"
                        elif command == "UPDATE":
                            sql = f"UPDATE {qualified} SET review_id = review_id WHERE FALSE" if "reviews" in table else f"UPDATE {qualified} SET election_id = election_id WHERE FALSE"
                        else:
                            sql = f"DELETE FROM {qualified} WHERE FALSE"
                        raw.execute(text("SAVEPOINT sc05_dml"))
                        try:
                            raw.execute(text(f'SET LOCAL ROLE "{role}"'))
                            try:
                                raw.execute(text(sql))
                                outcome = "success"
                            except DBAPIError as err:
                                code = getattr(err.orig, "sqlstate", None) or getattr(err.orig, "pgcode", None)
                                outcome = "permission_denied" if code == "42501" else "other_error"
                            finally:
                                raw.execute(text("ROLLBACK TO SAVEPOINT sc05_dml"))
                        except DBAPIError:
                            raw.execute(text("ROLLBACK TO SAVEPOINT sc05_dml"))
                            raise
                        if command in forbidden:
                            assert outcome == "permission_denied", (table, command, outcome)
                        else:
                            assert outcome != "permission_denied", (table, command, outcome)
            finally:
                if tx.is_active:
                    tx.rollback()
    finally:
        engine.dispose()
