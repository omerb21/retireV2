"""Opt-in isolated PostgreSQL 16 evidence for the RTDIR limiter.

Run with RTDIR_POSTGRES_TEST=1.  The fixture creates and removes its own
ephemeral Docker container and never reads the user's DATABASE_URL.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from uuid import uuid4

import psycopg2
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.security.config import AuthConfig
from app.security.rate_limit import MAX_COUNT, cleanup_batch, finalize, login_buckets, precheck


BACKEND = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def rtdir_postgres_url():
    if os.environ.get("RTDIR_POSTGRES_TEST") != "1":
        pytest.skip("isolated PostgreSQL evidence requires RTDIR_POSTGRES_TEST=1")
    name = "retire-rtdir-test-" + uuid4().hex

    def docker(*args: str) -> str:
        return subprocess.check_output(["docker", *args], text=True, timeout=120).strip()

    container = docker(
        "run", "--rm", "-d", "--name", name,
        "--label", "retire.rtdir.test=" + name,
        "--tmpfs", "/var/lib/postgresql/data",
        "-p", "127.0.0.1::5432",
        "-e", "POSTGRES_PASSWORD=isolated-test",
        "-e", "POSTGRES_DB=rtdir_test",
        "postgres:16",
    )
    try:
        info = json.loads(docker("inspect", container))[0]
        assert info["Config"]["Labels"]["retire.rtdir.test"] == name
        port = info["NetworkSettings"]["Ports"]["5432/tcp"][0]["HostPort"]
        url = f"postgresql://postgres:isolated-test@127.0.0.1:{port}/rtdir_test"
        for _ in range(100):
            try:
                with psycopg2.connect(url):
                    break
            except psycopg2.OperationalError:
                time.sleep(0.2)
        else:
            pytest.fail("isolated PostgreSQL did not become ready")
        yield url
    finally:
        info = json.loads(docker("inspect", container))[0]
        assert info["Id"] == container
        assert info["Config"]["Labels"]["retire.rtdir.test"] == name
        docker("stop", container)


def _alembic(url: str, *args: str) -> str:
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND,
        env={**os.environ, "DATABASE_URL": url, "PYTHONIOENCODING": "utf-8"},
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=180,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout.strip()


def test_postgresql_migration_schema_parent_head_and_downgrade(rtdir_postgres_url):
    _alembic(rtdir_postgres_url, "upgrade", "a2b8c5e1f309")
    _alembic(rtdir_postgres_url, "upgrade", "b3c9d6f2a410")
    assert _alembic(rtdir_postgres_url, "current").startswith("b3c9d6f2a410")
    assert _alembic(rtdir_postgres_url, "heads") == "b3c9d6f2a410 (head)"
    with psycopg2.connect(rtdir_postgres_url) as db, db.cursor() as cursor:
        assert db.server_version // 10000 == 16
        cursor.execute("""
            SELECT column_name,data_type,is_nullable
            FROM information_schema.columns
            WHERE table_name='rtdir_login_rate_limit_buckets'
            ORDER BY ordinal_position
        """)
        assert cursor.fetchall() == [
            ("bucket_key", "character", "NO"),
            ("bucket_kind", "character varying", "NO"),
            ("window_started_at", "timestamp with time zone", "NO"),
            ("failure_count", "integer", "NO"),
            ("locked_until", "timestamp with time zone", "YES"),
            ("updated_at", "timestamp with time zone", "NO"),
        ]
        cursor.execute("SELECT conname FROM pg_constraint WHERE conrelid='rtdir_login_rate_limit_buckets'::regclass")
        names = {row[0] for row in cursor.fetchall()}
        assert {
            "ck_rtdir_login_bucket_key_hex", "ck_rtdir_login_bucket_kind",
            "ck_rtdir_login_failure_count", "ck_rtdir_login_lock_window",
            "rtdir_login_rate_limit_buckets_pkey",
        } <= names
    _alembic(rtdir_postgres_url, "downgrade", "a2b8c5e1f309")
    with psycopg2.connect(rtdir_postgres_url) as db, db.cursor() as cursor:
        cursor.execute("SELECT to_regclass('rtdir_login_rate_limit_buckets')")
        assert cursor.fetchone() == (None,)
    _alembic(rtdir_postgres_url, "upgrade", "b3c9d6f2a410")


def test_postgresql_limiter_concurrent_threshold_reset_saturation_and_cleanup(rtdir_postgres_url):
    engine = create_engine(rtdir_postgres_url, pool_size=8, max_overflow=8)
    config = AuthConfig(production=True, actor_id="planner", session_secret=b"a" * 32, rate_limit_secret=b"b" * 32)
    buckets = login_buckets(config, "planner", "192.0.2.1")
    barrier = threading.Barrier(5)

    def failure() -> int:
        with Session(engine) as db:
            assert precheck(db, buckets) == 0
        barrier.wait(timeout=30)
        with Session(engine) as db:
            return finalize(db, buckets, success=False)

    with ThreadPoolExecutor(max_workers=5) as executor:
        waits = list(executor.map(lambda _: failure(), range(5)))
    assert sum(wait > 0 for wait in waits) == 1
    with engine.connect() as db:
        rows = db.execute(text("SELECT bucket_kind,failure_count,locked_until IS NOT NULL FROM rtdir_login_rate_limit_buckets ORDER BY bucket_kind")).all()
    assert rows == [("GLOBAL", 5, False), ("IP", 5, False), ("USER", 5, True)]

    with Session(engine) as db:
        assert finalize(db, buckets, success=True) > 0  # reached threshold cannot be bypassed
    with engine.begin() as db:
        user_key = next(item.key for item in buckets if item.kind == "USER")
        db.execute(text("UPDATE rtdir_login_rate_limit_buckets SET failure_count=:maximum, locked_until=window_started_at + INTERVAL '900 seconds' WHERE bucket_key=:key"), {"maximum": MAX_COUNT, "key": user_key})
    with Session(engine) as db:
        assert finalize(db, buckets, success=False) > 0
    with engine.connect() as db:
        assert db.execute(text("SELECT failure_count FROM rtdir_login_rate_limit_buckets WHERE bucket_key=:key"), {"key": user_key}).scalar_one() == MAX_COUNT

    with engine.begin() as db:
        db.execute(text("UPDATE rtdir_login_rate_limit_buckets SET updated_at=transaction_timestamp() - INTERVAL '1900 seconds'"))
    with Session(engine) as db:
        assert cleanup_batch(db) == 3
    engine.dispose()
