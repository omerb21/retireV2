"""Run historical grant status migration on a disposable PostgreSQL database.

Requires TEST_DATABASE_URL pointing ONLY to a dedicated throwaway database.
Deliberately does not touch the active workspace database.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import os

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def main():
    url = os.environ["TEST_DATABASE_URL"]
    if "settlement_migration_probe" not in url:
        raise RuntimeError("Refusing non-probe database name")
    engine = sa.create_engine(url)
    assert engine.dialect.name == "postgresql"
    with engine.begin() as conn:
        conn.execute(sa.text("""CREATE TABLE employment_records (
            employment_record_id VARCHAR(64) PRIMARY KEY, client_id INTEGER NOT NULL,
            employer_name VARCHAR(255) NOT NULL, work_start_date DATE NOT NULL,
            work_end_date DATE, is_current BOOLEAN NOT NULL, notes TEXT
        )"""))
        conn.execute(sa.text("""CREATE TABLE grants (
            grant_id VARCHAR(64) PRIMARY KEY, client_id INTEGER NOT NULL,
            employment_record_id VARCHAR(64), nominal_amount NUMERIC
        )"""))
        for ident in ("duplicate", "single", "missing", "current"):
            conn.execute(sa.text("""INSERT INTO employment_records
                (employment_record_id, client_id, employer_name, work_start_date,
                 work_end_date, is_current, notes)
                VALUES (:id, 1, 'Employer', '2000-01-01', '2010-01-01', :current, NULL)
            """), {"id": ident, "current": ident == "current"})
        for ident, period in (("a", "duplicate"), ("b", "duplicate"), ("c", "single")):
            conn.execute(sa.text("""INSERT INTO grants
                (grant_id, client_id, employment_record_id, nominal_amount)
                VALUES (:id, 1, :period, 1234)
            """), {"id": ident, "period": period})
        path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "d2c4e6a8b031_historical_exempt_grant_status.py"
        spec = importlib.util.spec_from_file_location("probe_migration", path)
        assert spec and spec.loader
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        operations = Operations(MigrationContext.configure(conn))
        migration.op.batch_alter_table = operations.batch_alter_table
        migration.op.execute = operations.execute
        migration.upgrade()
        actual = dict(conn.execute(sa.text(
            "SELECT employment_record_id, exempt_grant_status FROM employment_records"
        )).all())
        expected = {"duplicate": "requires_reconciliation", "single": "recorded",
                    "missing": "not_reviewed", "current": "not_reviewed"}
        assert actual == expected, (actual, expected)
        grants = conn.execute(sa.text(
            "SELECT grant_id, employment_record_id, nominal_amount FROM grants ORDER BY grant_id"
        )).all()
        assert [(row[0], row[1], int(row[2])) for row in grants] == [
            ("a", "duplicate", 1234), ("b", "duplicate", 1234), ("c", "single", 1234)
        ], grants
        conn.execute(sa.text(
            "UPDATE employment_records SET exempt_grant_status='none' WHERE employment_record_id='missing'"
        ))
        assert conn.scalar(sa.text(
            "SELECT exempt_grant_status FROM employment_records WHERE employment_record_id='missing'"
        )) == "none"
        try:
            with conn.begin_nested():
                conn.execute(sa.text(
                    "UPDATE employment_records SET exempt_grant_status='invalid' WHERE employment_record_id='missing'"
                ))
        except sa.exc.IntegrityError:
            pass
        else:
            raise AssertionError("PostgreSQL must reject invalid status")
        migration.op.batch_alter_table = operations.batch_alter_table
        migration.downgrade()
        cols = sa.inspect(conn).get_columns("employment_records")
        assert not any(col["name"] == "exempt_grant_status" for col in cols)
    engine.dispose()
    print("PASS: isolated PostgreSQL upgrade/backfill/constraint/downgrade; grant rows preserved")


if __name__ == "__main__":
    main()
