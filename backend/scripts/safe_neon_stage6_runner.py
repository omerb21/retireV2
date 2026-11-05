"""Run the isolated Neon Stage 6 bootstrap without logging connection secrets."""
from __future__ import annotations

import argparse
import getpass
import os
from pathlib import Path
import subprocess
import sys

from sqlalchemy.engine import make_url

EXPECTED_HOST = "ep-raspy-mouse-b90m3k25.c-7.eu-central-1.aws.neon.tech"
EXPECTED_DB = "retire_v2_stage6_validation"
EXPECTED_USER = "retire_v2_stage6_validation_owner"


def validate_connection_string(value: str) -> None:
    if not value or value.count("://") != 1 or any(ch.isspace() for ch in value):
        raise ValueError("Paste exactly one URL, without commands or extra text")
    if any(ch in value for ch in ("'", '"', "<", ">")):
        raise ValueError("Do not include quotes or markup")
    try:
        parsed = make_url(value)
    except Exception:
        raise ValueError("Malformed PostgreSQL URL") from None
    if parsed.drivername not in {"postgresql", "postgresql+psycopg2"}:
        raise ValueError("Expected a PostgreSQL URL")
    if (parsed.host or "").lower() != EXPECTED_HOST or parsed.database != EXPECTED_DB:
        raise ValueError("Wrong Neon project or database")
    if parsed.username != EXPECTED_USER or not parsed.password:
        raise ValueError("Expected the Neon migration-owner role")
    if parsed.port not in (None, 5432):
        raise ValueError("Unexpected PostgreSQL port")
    if set(parsed.query) - {"sslmode", "channel_binding"}:
        raise ValueError("Unexpected query parameters")
    if parsed.query.get("sslmode") not in {"require", "verify-ca", "verify-full"}:
        raise ValueError("TLS is required")
    if parsed.query.get("channel_binding", "require") != "require":
        raise ValueError("Duplicated or invalid channel_binding")


def main() -> int:
    parser = argparse.ArgumentParser(description="Safe, isolated Neon Stage 6 bootstrap")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    backend_dir = Path(__file__).resolve().parents[1]
    target = backend_dir / "scripts" / "neon_stage6_bootstrap.py"
    if not target.is_file():
        print("STOP: original bootstrap script missing")
        return 2

    url = getpass.getpass("Paste a single Neon Direct URL (hidden): ").strip()
    try:
        validate_connection_string(url)
    except ValueError as exc:
        print("STOP: " + str(exc))
        return 2

    env = dict(os.environ)
    env["DATABASE_URL"] = url
    command = [sys.executable, str(target)]
    if args.apply:
        command.append("--apply")
    try:
        result = subprocess.run(
            command, cwd=backend_dir, env=env,
            capture_output=True, text=True, timeout=300, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        print("STOP: bootstrap did not complete; inspect DB state before retrying")
        return 1
    finally:
        env.pop("DATABASE_URL", None)
        url = ""

    preflight_ok = "PREFLIGHT PASS:" in result.stdout
    migration_ok = "MIGRATION PASS:" in result.stdout
    if preflight_ok:
        print("PREFLIGHT PASS")
    if result.returncode == 0 and (migration_ok if args.apply else preflight_ok):
        print("MIGRATION PASS" if args.apply else "PREFLIGHT COMPLETE")
        return 0
    print("STOP: bootstrap failed. Check database state before retrying --apply.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
