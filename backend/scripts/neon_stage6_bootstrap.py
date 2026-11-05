"""Safely bootstrap the dedicated, empty Neon Stage 6 validation database.

Run from a local RETIRE V2 checkout with backend dependencies installed:
    python scripts/neon_stage6_bootstrap.py           # read-only preflight
    python scripts/neon_stage6_bootstrap.py --apply   # explicit schema migration

The connection string is requested without terminal echo when DATABASE_URL is
unset. No passwords are written to files, logs, or the repository. Never point
this utility at an existing database containing user data.
"""
from __future__ import annotations

import argparse
import getpass
import os
from pathlib import Path
import subprocess
import sys

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

BACKEND_DIR = Path(__file__).resolve().parents[1]
EXPECTED_DATABASE = "retire_v2_stage6_validation"
EXPECTED_HEAD = "d6f1a9c3b704"
APPLICATION_ROLE = "retire_v2_stage6_app"


def validate_url(database_url: str) -> str:
    """Fail closed on provider, direct endpoint, database name and TLS."""
    try:
        parsed = make_url(database_url)
    except Exception as exc:
        raise RuntimeError("Invalid PostgreSQL connection string") from exc
    host = (parsed.host or "").lower()
    if parsed.drivername not in {
        "postgresql", "postgresql+psycopg2", "postgresql+psycopg",
    }:
        raise RuntimeError("Only a PostgreSQL connection is permitted")
    if not host.endswith(".neon.tech") or "-pooler" in host:
        raise RuntimeError("A direct Neon PostgreSQL endpoint is required")
    if parsed.database != EXPECTED_DATABASE:
        raise RuntimeError("Wrong database: refuse to touch anything else")
    if parsed.query.get("sslmode") not in {"require", "verify-ca", "verify-full"}:
        raise RuntimeError("An explicit TLS-verified Neon connection is required")
    if not parsed.username or not parsed.password:
        raise RuntimeError("A database owner connection with credentials is required")
    return database_url


def verify_source_revision() -> None:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    heads = ScriptDirectory.from_config(config).get_heads()
    if heads != [EXPECTED_HEAD]:
        raise RuntimeError("Checkout has unexpected Alembic head; migration blocked")


def preflight(engine) -> None:
    with engine.connect() as connection:
        database_name, server_version, app_role = connection.execute(text(
            "SELECT current_database(), current_setting('server_version_num')::integer, "
            "to_regrole(:role)::text"
        ), {"role": APPLICATION_ROLE}).one()
        count = connection.execute(text(
            "SELECT count(*) FROM pg_catalog.pg_tables WHERE schemaname = 'public'"
        )).scalar_one()
        has_migration_table = connection.execute(text(
            "SELECT to_regclass('public.alembic_version') IS NOT NULL"
        )).scalar_one()
    if database_name != EXPECTED_DATABASE or server_version // 10000 != 16:
        raise RuntimeError("Unexpected target database or PostgreSQL major version")
    if app_role != APPLICATION_ROLE:
        raise RuntimeError("Dedicated application role is missing")
    if count != 0 or has_migration_table:
        raise RuntimeError("Target is not empty; refusing schema migration")
    print("PREFLIGHT PASS: dedicated Neon PG16 is empty; application role exists.")


def verify_migration(engine) -> None:
    with engine.connect() as connection:
        versions = connection.execute(text(
            "SELECT version_num FROM alembic_version ORDER BY version_num"
        )).scalars().all()
        table_count = connection.execute(text(
            "SELECT count(*) FROM pg_catalog.pg_tables WHERE schemaname = 'public'"
        )).scalar_one()
        immutable_trigger = connection.execute(text(
            "SELECT count(*) FROM pg_trigger WHERE "
            "tgrelid = 'public.scenario_pension_factor_admissions'::regclass "
            "AND tgname = 'trg_s6_factor_admission_immutable' AND NOT tgisinternal"
        )).scalar_one()
        privileges = connection.execute(text(
            "SELECT has_table_privilege(:role, 'public.scenario_pension_factor_admissions', 'SELECT'), "
            "has_table_privilege(:role, 'public.scenario_pension_factor_admissions', 'INSERT'), "
            "has_table_privilege(:role, 'public.scenario_pension_factor_admissions', 'UPDATE'), "
            "has_table_privilege(:role, 'public.scenario_pension_factor_admissions', 'DELETE')"
        ), {"role": APPLICATION_ROLE}).one()
    if (versions != [EXPECTED_HEAD] or table_count < 2
            or immutable_trigger != 1 or tuple(privileges) != (True, True, False, False)):
        raise RuntimeError("Migration verification failed: check head, trigger or grants")
    print("MIGRATION PASS: expected Alembic head, immutable trigger and least-privilege grants.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="Run Alembic upgrade on the verified empty Neon database")
    args = parser.parse_args()
    verify_source_revision()
    url = validate_url(os.environ.get("DATABASE_URL") or getpass.getpass(
        "Paste the Neon DATABASE_URL (input hidden): "
    ).strip())
    engine = create_engine(url, pool_pre_ping=True,
                           connect_args={"connect_timeout": 15})
    try:
        preflight(engine)
        if not args.apply:
            print("No changes were made. To migrate the isolated schema, use --apply.")
            return
        env = dict(os.environ)
        env["DATABASE_URL"] = url
        env["CRTISBA_APPLICATION_DB_ROLE"] = APPLICATION_ROLE
        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=str(BACKEND_DIR),
            env=env,
            check=True,
        )
        verify_migration(engine)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
