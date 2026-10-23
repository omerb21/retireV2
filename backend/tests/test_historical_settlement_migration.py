"""Migration regression: legacy duplicate severance grants remain intact.

Tests apply the NEW migration to a representative pre-migration employment/grant
schema. No live databases or foreign services are accessed.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

MIGRATION = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "d2c4e6a8b031_historical_exempt_grant_status.py"


def test_backfill_keeps_duplicates_and_distinguishes_missing_from_none(tmp_path, monkeypatch):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with engine.begin() as connection:
        connection.execute(sa.text("""CREATE TABLE employment_records (
            employment_record_id VARCHAR(64) PRIMARY KEY, client_id INTEGER NOT NULL,
            employer_name VARCHAR(255) NOT NULL, work_start_date DATE NOT NULL,
            work_end_date DATE, is_current BOOLEAN NOT NULL, notes TEXT
        )"""))
        connection.execute(sa.text("""CREATE TABLE grants (
            grant_id VARCHAR(64) PRIMARY KEY, client_id INTEGER NOT NULL,
            employment_record_id VARCHAR(64), nominal_amount NUMERIC
        )"""))
        for ident in ("duplicate", "single", "missing", "current"):
            connection.execute(sa.text("""
                INSERT INTO employment_records (
                  employment_record_id, client_id, employer_name, work_start_date,
                  work_end_date, is_current, notes)
                VALUES (:id, 1, 'Same employer', '2000-01-01', '2010-01-01', :current, NULL)
            """), {"id": ident, "current": ident == "current"})
        for ident, period in (("a", "duplicate"), ("b", "duplicate"), ("c", "single")):
            connection.execute(sa.text("""
                INSERT INTO grants (grant_id, client_id, employment_record_id, nominal_amount)
                VALUES (:id, 1, :period, 1234)
            """), {"id": ident, "period": period})

        spec = importlib.util.spec_from_file_location("historical_status_migration", MIGRATION)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        context = MigrationContext.configure(connection)
        operations = Operations(context)
        monkeypatch.setattr(module.op, "batch_alter_table", operations.batch_alter_table)
        monkeypatch.setattr(module.op, "execute", operations.execute)
        module.upgrade()

        statuses = dict(connection.execute(sa.text(
            "SELECT employment_record_id, exempt_grant_status FROM employment_records"
        )).all())
        assert statuses == {
            "duplicate": "requires_reconciliation",
            "single": "recorded",
            "missing": "not_reviewed",
            "current": "not_reviewed",
        }
        links = connection.execute(sa.text(
            "SELECT grant_id, employment_record_id, nominal_amount FROM grants ORDER BY grant_id"
        )).all()
        assert [(row[0], row[1], int(row[2])) for row in links] == [
            ("a", "duplicate", 1234), ("b", "duplicate", 1234), ("c", "single", 1234),
        ]
        connection.execute(sa.text(
            "UPDATE employment_records SET exempt_grant_status = 'none' WHERE employment_record_id = 'missing'"
        ))
        assert connection.scalar(sa.text(
            "SELECT exempt_grant_status FROM employment_records WHERE employment_record_id = 'missing'"
        )) == "none"
