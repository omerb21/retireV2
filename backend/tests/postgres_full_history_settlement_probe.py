"""Run real Alembic history through the settlement migration on disposable Postgres.

TEST_DATABASE_URL must contain the dedicated probe database name. No changes to
the developer's active workspace database or to Railway.
"""
import os
from decimal import Decimal
from sqlalchemy import create_engine, text
from alembic import command
from alembic.config import Config

BASE = "c4e8a2f6b731"
TARGET = "d2c4e6a8b031"


def run():
    url = os.environ["TEST_DATABASE_URL"]
    if not url.endswith("/settlement_migration_probe"):
        raise RuntimeError("Refusing to run outside settlement_migration_probe")
    os.environ["DATABASE_URL"] = url
    config = Config("alembic.ini")
    engine = create_engine(url)
    with engine.connect() as conn:
        assert conn.dialect.name == "postgresql"
        assert conn.scalar(text("SELECT COUNT(*) FROM pg_tables WHERE schemaname='public'")) == 0, "Probe database must be empty"

    command.upgrade(config, BASE)
    with engine.begin() as conn:
        assert conn.scalar(text("SELECT version_num FROM alembic_version")) == BASE
        cid = conn.scalar(text("""
            INSERT INTO clients (display_name, id_number)
            VALUES ('Synthetic Test', '987654321')
            RETURNING client_id
        """))
        for name in ("duplicate", "single", "missing", "current"):
            conn.execute(text("""
                INSERT INTO employment_records
                    (employment_record_id, client_id, employer_name,
                     work_start_date, work_end_date, is_current)
                VALUES (:name, :cid, 'Test historical employer', '2000-01-01',
                        :end, :current)
            """), {"name": name, "cid": cid, "end": None if name == "current" else "2010-01-01",
                   "current": name == "current"})
        for gid, period, amount in (("g1","duplicate",Decimal("123456.00")),
                                     ("g2","duplicate",Decimal("2500.00")),
                                     ("g3","single",Decimal("1000.00"))):
            conn.execute(text("""
                INSERT INTO grants (grant_id, client_id, employment_record_id,
                                    employer_name, employer_withholding_file_number,
                                    nominal_amount, grant_date, work_start_date, work_end_date)
                VALUES (:gid, :cid, :period, 'Test historical employer',
                        '123456789', :amount, '2010-02-01', '2000-01-01', '2010-01-01')
            """), {"gid": gid, "cid": cid, "period": period, "amount": amount})

    command.upgrade(config, TARGET)
    with engine.begin() as conn:
        assert conn.scalar(text("SELECT version_num FROM alembic_version")) == TARGET
        states = dict(conn.execute(text(
            "SELECT employment_record_id, exempt_grant_status FROM employment_records"
        )).all())
        assert states == {"duplicate":"requires_reconciliation", "single":"recorded",
                          "missing":"not_reviewed", "current":"not_reviewed"}, states
        amounts = list(conn.execute(text("""
            SELECT grant_id, employment_record_id, nominal_amount FROM grants ORDER BY grant_id
        """)).all())
        assert [(r[0], r[1], Decimal(str(r[2]))) for r in amounts] == [
            ("g1","duplicate",Decimal("123456.00")),
            ("g2","duplicate",Decimal("2500.00")),
            ("g3","single",Decimal("1000.00"))], amounts
        conn.execute(text("UPDATE employment_records SET exempt_grant_status='none' WHERE employment_record_id='missing'"))
        assert conn.scalar(text("SELECT exempt_grant_status FROM employment_records WHERE employment_record_id='missing'")) == "none"
    engine.dispose()
    print("PASS: complete Alembic chain, duplicate grant preservation, and durable statuses on isolated PostgreSQL")


if __name__ == "__main__":
    run()
