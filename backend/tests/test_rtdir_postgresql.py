"""Opt-in isolated PostgreSQL 16 evidence for the RTDIR limiter.

Run with RTDIR_POSTGRES_TEST=1.  The fixture creates and removes its own
ephemeral Docker container and never reads the user's DATABASE_URL.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
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
from argon2 import PasswordHasher
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.api import auth_routes
from app.security import rate_limit as rate_limit_module
from app.security.config import AuthConfig
from app.security.rate_limit import MAX_COUNT, RateLimitUnavailable, cleanup_batch, finalize, login_buckets, precheck
from app import main as app_main
from app.main import create_app


BACKEND = Path(__file__).resolve().parents[1]


def _config(secret: bytes = b"z" * 32) -> AuthConfig:
    hasher = PasswordHasher(time_cost=1, memory_cost=8192, parallelism=1, hash_len=16, salt_len=16)
    return AuthConfig(
        production=True, public_origin="https://retire.example", public_authority="retire.example",
        username="planner", password_hash=hasher.hash("correct"), dummy_password_hash=hasher.hash("dummy"),
        actor_id="planner", session_secret=b"s" * 32, rate_limit_secret=secret,
    )


def _headers(ip: str = "192.0.2.10") -> dict[str, str]:
    return {
        "host": "retire.example", "x-real-ip": ip, "x-forwarded-proto": "https",
        "x-forwarded-host": "retire.example", "origin": "https://retire.example",
    }


def _postgres_client(engine, monkeypatch, config: AuthConfig):
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(auth_routes, "get_session_factory", lambda: sessions)
    application = create_app(config)
    application.state.rate_limiter_ready = True
    return TestClient(application), application


def _clear(engine):
    with engine.begin() as db:
        db.execute(text("DELETE FROM rtdir_login_rate_limit_buckets"))


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
        # No lock is present, so finalize must reach the actual saturating UPDATE
        # branch rather than returning from the lock precheck.
        db.execute(text("UPDATE rtdir_login_rate_limit_buckets SET failure_count=:maximum, locked_until=NULL WHERE bucket_key=:key"), {"maximum": MAX_COUNT, "key": user_key})
    with Session(engine) as db:
        finalize(db, buckets, success=False)
    with engine.connect() as db:
        assert db.execute(text("SELECT failure_count FROM rtdir_login_rate_limit_buckets WHERE bucket_key=:key"), {"key": user_key}).scalar_one() == MAX_COUNT

    with engine.begin() as db:
        db.execute(text("UPDATE rtdir_login_rate_limit_buckets SET updated_at=transaction_timestamp() - INTERVAL '1900 seconds'"))
    with Session(engine) as db:
        assert cleanup_batch(db) == 3
    engine.dispose()


def test_postgresql_zero_placeholder_anchor_and_restart_persistence(rtdir_postgres_url):
    engine = create_engine(rtdir_postgres_url)
    config = AuthConfig(production=True, actor_id="planner", session_secret=b"a" * 32, rate_limit_secret=b"c" * 32)
    buckets = login_buckets(config, "new-user", "192.0.2.22")
    with Session(engine) as db:
        assert precheck(db, buckets) == 0
    with engine.connect() as db:
        placeholders = db.execute(text("""
            SELECT failure_count, locked_until, window_started_at = updated_at
            FROM rtdir_login_rate_limit_buckets
            WHERE bucket_key = ANY(:keys)
            ORDER BY bucket_key
        """), {"keys": [item.key for item in buckets]}).all()
    assert placeholders == [(0, None, True)] * 3
    with Session(engine) as db:
        assert finalize(db, buckets, success=False) == 0
    with engine.connect() as db:
        anchored = db.execute(text("""
            SELECT failure_count, locked_until, window_started_at <= updated_at
            FROM rtdir_login_rate_limit_buckets
            WHERE bucket_key = ANY(:keys)
            ORDER BY bucket_key
        """), {"keys": [item.key for item in buckets]}).all()
    assert anchored == [(1, None, True)] * 3
    engine.dispose()
    restarted = create_engine(rtdir_postgres_url)
    with restarted.connect() as db:
        assert db.execute(text("SELECT count(*) FROM rtdir_login_rate_limit_buckets WHERE bucket_key = ANY(:keys)"), {"keys": [item.key for item in buckets]}).scalar_one() == 3
    restarted.dispose()


def test_postgresql_readiness_requires_exact_migration_head(rtdir_postgres_url, monkeypatch):
    engine = create_engine(rtdir_postgres_url)
    monkeypatch.setattr(app_main, "get_session_factory", lambda: lambda: Session(engine))
    application = create_app(AuthConfig(production=True, actor_id="planner", session_secret=b"a" * 32, rate_limit_secret=b"b" * 32))
    assert app_main._cleanup_once(application) is True
    assert application.state.rate_limiter_ready is True
    with engine.begin() as db:
        db.execute(text("UPDATE alembic_version SET version_num='a2b8c5e1f309'"))
    assert app_main._cleanup_once(application) is False
    assert application.state.rate_limiter_ready is False
    with engine.begin() as db:
        db.execute(text("UPDATE alembic_version SET version_num='b3c9d6f2a410'"))
    assert app_main._cleanup_once(application) is True
    engine.dispose()


def test_postgresql_placeholder_delay_final_anchor_and_success_deletion_rules(rtdir_postgres_url):
    engine = create_engine(rtdir_postgres_url)
    _clear(engine)
    buckets = login_buckets(_config(b"1" * 32), "planner", "192.0.2.31")
    keys = {item.kind: item.key for item in buckets}
    with Session(engine) as db:
        assert precheck(db, buckets) == 0
    with engine.connect() as db:
        placeholder_time = db.execute(text(
            "SELECT min(window_started_at) FROM rtdir_login_rate_limit_buckets WHERE bucket_key = ANY(:keys)"
        ), {"keys": list(keys.values())}).scalar_one()
    time.sleep(0.08)
    before_final = datetime.now(timezone.utc)
    with Session(engine) as db:
        assert finalize(db, buckets, success=False) == 0
    with engine.connect() as db:
        anchors = db.execute(text(
            "SELECT bucket_kind,window_started_at,updated_at,failure_count FROM rtdir_login_rate_limit_buckets "
            "WHERE bucket_key = ANY(:keys) ORDER BY bucket_kind"
        ), {"keys": list(keys.values())}).all()
    assert all(row.window_started_at > placeholder_time for row in anchors)
    assert all(row.window_started_at >= before_final and row.window_started_at == row.updated_at and row.failure_count == 1 for row in anchors)

    with engine.begin() as db:
        db.execute(text("UPDATE rtdir_login_rate_limit_buckets SET failure_count=0,locked_until=NULL"))
    with Session(engine) as db:
        assert finalize(db, buckets, success=True) == 0
    with engine.connect() as db:
        assert db.execute(text("SELECT count(*) FROM rtdir_login_rate_limit_buckets")).scalar_one() == 0

    with Session(engine) as db:
        assert precheck(db, buckets) == 0
    with engine.begin() as db:
        db.execute(text("UPDATE rtdir_login_rate_limit_buckets SET failure_count=3 WHERE bucket_kind='GLOBAL'"))
    with Session(engine) as db:
        assert finalize(db, buckets, success=True) == 0
    with engine.connect() as db:
        remaining = db.execute(text("SELECT bucket_kind,failure_count FROM rtdir_login_rate_limit_buckets ORDER BY bucket_kind")).all()
    assert remaining == [("GLOBAL", 3)]
    engine.dispose()


def test_postgresql_expired_zero_and_positive_buckets_precheck_and_final_paths(rtdir_postgres_url):
    engine = create_engine(rtdir_postgres_url)
    _clear(engine)
    buckets = login_buckets(_config(b"2" * 32), "planner", "192.0.2.32")
    keys = {item.kind: item.key for item in buckets}
    with Session(engine) as db:
        assert precheck(db, buckets) == 0
    with engine.begin() as db:
        db.execute(text("""
            UPDATE rtdir_login_rate_limit_buckets
            SET failure_count=CASE WHEN bucket_kind='USER' THEN 4 ELSE 0 END,
                window_started_at=transaction_timestamp()-INTERVAL '901 seconds',
                updated_at=transaction_timestamp()-INTERVAL '901 seconds'
        """))
    precheck_start = datetime.now(timezone.utc)
    with Session(engine) as db:
        assert precheck(db, buckets) == 0
    with engine.connect() as db:
        user = db.execute(text(
            "SELECT failure_count,window_started_at,updated_at FROM rtdir_login_rate_limit_buckets WHERE bucket_key=:key"
        ), {"key": keys["USER"]}).one()
        zeros = db.execute(text(
            "SELECT failure_count,window_started_at FROM rtdir_login_rate_limit_buckets WHERE bucket_kind IN ('GLOBAL','IP') ORDER BY bucket_kind"
        )).all()
    assert user.failure_count == 0 and user.window_started_at >= precheck_start and user.updated_at == user.window_started_at
    assert [row.failure_count for row in zeros] == [0, 0]

    with engine.begin() as db:
        db.execute(text("""
            UPDATE rtdir_login_rate_limit_buckets
            SET failure_count=CASE WHEN bucket_kind='USER' THEN 4 ELSE 0 END,
                window_started_at=transaction_timestamp()-INTERVAL '901 seconds',
                updated_at=transaction_timestamp()-INTERVAL '901 seconds'
        """))
    final_start = datetime.now(timezone.utc)
    with Session(engine) as db:
        assert finalize(db, buckets, success=False) == 0
    with engine.connect() as db:
        rows = db.execute(text(
            "SELECT bucket_kind,failure_count,window_started_at,updated_at FROM rtdir_login_rate_limit_buckets ORDER BY bucket_kind"
        )).all()
    assert all(row.failure_count == 1 and row.window_started_at == row.updated_at and row.window_started_at >= final_start for row in rows)
    engine.dispose()


def test_postgresql_cleanup_skip_locked_current_active_bounded_and_continues(rtdir_postgres_url):
    engine = create_engine(rtdir_postgres_url, pool_size=4)
    _clear(engine)
    now = datetime.now(timezone.utc)
    rows = []
    for index in range(67):
        rows.append({
            "key": f"{index:064x}", "kind": "USER", "started": now - timedelta(hours=2),
            "count": 1 if index % 2 else 0, "updated": now - timedelta(hours=1),
        })
    rows.extend([
        {"key": "e" * 64, "kind": "USER", "started": now, "count": 0, "updated": now},
        {"key": "f" * 64, "kind": "IP", "started": now, "count": 19, "updated": now},
    ])
    with engine.begin() as db:
        db.execute(text("""
            INSERT INTO rtdir_login_rate_limit_buckets
              (bucket_key,bucket_kind,window_started_at,failure_count,locked_until,updated_at)
            VALUES (:key,:kind,:started,:count,NULL,:updated)
        """), rows)
    locked_key = rows[0]["key"]
    locker = Session(engine)
    try:
        locker.execute(text(
            "SELECT bucket_key FROM rtdir_login_rate_limit_buckets WHERE bucket_key=:key FOR UPDATE"
        ), {"key": locked_key}).one()
        with Session(engine) as db:
            assert cleanup_batch(db) == 64
        with engine.connect() as db:
            assert db.execute(text(
                "SELECT count(*) FROM rtdir_login_rate_limit_buckets WHERE bucket_key=:key"
            ), {"key": locked_key}).scalar_one() == 1
            assert db.execute(text(
                "SELECT count(*) FROM rtdir_login_rate_limit_buckets WHERE bucket_key IN (:current,:active)"
            ), {"current": "e" * 64, "active": "f" * 64}).scalar_one() == 2
    finally:
        locker.rollback(); locker.close()
    with Session(engine) as db:
        assert cleanup_batch(db) == 3
        assert cleanup_batch(db) == 0
    with engine.connect() as db:
        assert db.execute(text("SELECT count(*) FROM rtdir_login_rate_limit_buckets")).scalar_one() == 2
    engine.dispose()


def test_postgresql_cleanup_failure_blocks_argon_and_recovery_restores_readiness(rtdir_postgres_url, monkeypatch):
    engine = create_engine(rtdir_postgres_url)
    _clear(engine)
    config = _config(b"3" * 32)
    client, application = _postgres_client(engine, monkeypatch, config)
    argon_calls = []
    original_verify = PasswordHasher.verify
    monkeypatch.setattr(PasswordHasher, "verify", lambda self, encoded, password: argon_calls.append(password) or original_verify(self, encoded, password))

    monkeypatch.setattr(app_main, "get_session_factory", lambda: sessionmaker(bind=engine))
    with monkeypatch.context() as failure:
        failure.setattr(app_main, "cleanup_batch", lambda db: (_ for _ in ()).throw(RateLimitUnavailable("injected cleanup")))
        assert app_main._cleanup_once(application) is False
    unavailable = client.post("/api/auth/login", headers=_headers(), json={"username": "planner", "password": "correct"})
    assert (unavailable.status_code, unavailable.json()["code"]) == (503, "AUTH_RATE_LIMIT_UNAVAILABLE")
    assert argon_calls == []
    assert app_main._cleanup_once(application) is True
    recovered = client.post("/api/auth/login", headers=_headers(), json={"username": "planner", "password": "correct"})
    assert recovered.status_code == 200 and argon_calls == ["correct"]
    engine.dispose()


def test_postgresql_injected_database_failures_never_fail_open(rtdir_postgres_url, monkeypatch):
    engine = create_engine(rtdir_postgres_url)
    config = _config(b"4" * 32)
    client, application = _postgres_client(engine, monkeypatch, config)
    argon_calls = []
    monkeypatch.setattr(PasswordHasher, "verify", lambda *args: argon_calls.append(True) or True)
    with monkeypatch.context() as failure:
        failure.setattr(auth_routes, "cleanup_batch", lambda db: (_ for _ in ()).throw(RateLimitUnavailable("db unavailable")))
        response = client.post("/api/auth/login", headers=_headers(), json={"username": "planner", "password": "correct"})
    assert (response.status_code, response.json()["code"]) == (503, "AUTH_RATE_LIMIT_UNAVAILABLE")
    assert "set-cookie" not in response.headers and argon_calls == []
    assert application.state.rate_limiter_ready is False
    engine.dispose()


def _run_login_threshold_race(engine, monkeypatch, *, mutant: bool):
    _clear(engine)
    config = _config(b"5" * 32)
    client, _ = _postgres_client(engine, monkeypatch, config)
    entered = threading.Event(); release = threading.Event()
    original_verify = PasswordHasher.verify

    def delayed_verify(hasher, encoded, password):
        if password == "correct":
            entered.set()
            assert release.wait(30)
        return original_verify(hasher, encoded, password)

    monkeypatch.setattr(PasswordHasher, "verify", delayed_verify)
    original_finalize = auth_routes.finalize
    if mutant:
        monkeypatch.setattr(auth_routes, "finalize", lambda db, buckets, success: 0 if success else original_finalize(db, buckets, success=success))

    with ThreadPoolExecutor(max_workers=2) as executor:
        pending = executor.submit(lambda: client.post(
            "/api/auth/login", headers=_headers(), json={"username": "planner", "password": "correct"}
        ))
        assert entered.wait(30)
        with engine.connect() as db:
            held = db.execute(text("""
                SELECT count(*) FROM pg_locks locks
                LEFT JOIN pg_class relation ON relation.oid=locks.relation
                WHERE locks.pid <> pg_backend_pid() AND locks.granted
                  AND (relation.relname='rtdir_login_rate_limit_buckets' OR locks.locktype='advisory')
            """)).scalar_one()
        assert held == 0
        failures = [client.post(
            "/api/auth/login", headers=_headers(), json={"username": "planner", "password": "wrong"}
        ) for _ in range(5)]
        release.set()
        success = pending.result(timeout=30)
    return failures, success


def test_postgresql_real_login_race_final_recheck_mutation_and_restoration(rtdir_postgres_url, monkeypatch):
    engine = create_engine(rtdir_postgres_url, pool_size=8, max_overflow=8)
    failures, ordinary = _run_login_threshold_race(engine, monkeypatch, mutant=False)
    assert [response.status_code for response in failures] == [401, 401, 401, 401, 429]
    assert (ordinary.status_code, ordinary.json()["code"]) == (429, "LOGIN_RATE_LIMITED")
    assert "set-cookie" not in ordinary.headers

    monkeypatch.undo()
    failures, changed = _run_login_threshold_race(engine, monkeypatch, mutant=True)
    assert [response.status_code for response in failures] == [401, 401, 401, 401, 429]
    assert changed.status_code == 200 and "set-cookie" in changed.headers

    monkeypatch.undo()
    failures, restored = _run_login_threshold_race(engine, monkeypatch, mutant=False)
    assert [response.status_code for response in failures] == [401, 401, 401, 401, 429]
    assert (restored.status_code, restored.json()["code"]) == (429, "LOGIN_RATE_LIMITED")
    assert "set-cookie" not in restored.headers
    engine.dispose()


def test_postgresql_actual_failed_login_saturation_and_overflow_mutation(rtdir_postgres_url, monkeypatch):
    engine = create_engine(rtdir_postgres_url)
    _clear(engine)
    config = _config(b"6" * 32)
    client, application = _postgres_client(engine, monkeypatch, config)
    buckets = login_buckets(config, "planner", "192.0.2.10")
    user_key = next(item.key for item in buckets if item.kind == "USER")
    with engine.begin() as db:
        now = db.execute(text("SELECT transaction_timestamp()")) .scalar_one()
        db.execute(text("""
            INSERT INTO rtdir_login_rate_limit_buckets
              (bucket_key,bucket_kind,window_started_at,failure_count,locked_until,updated_at)
            VALUES (:key,'USER',:now,:maximum,NULL,:now)
        """), {"key": user_key, "now": now, "maximum": MAX_COUNT})
    ordinary = client.post("/api/auth/login", headers=_headers(), json={"username": "planner", "password": "wrong"})
    assert (ordinary.status_code, ordinary.json()["code"]) == (429, "LOGIN_RATE_LIMITED")
    with engine.connect() as db:
        assert db.execute(text(
            "SELECT failure_count FROM rtdir_login_rate_limit_buckets WHERE bucket_key=:key"
        ), {"key": user_key}).scalar_one() == MAX_COUNT

    with engine.begin() as db:
        db.execute(text("UPDATE rtdir_login_rate_limit_buckets SET locked_until=NULL WHERE bucket_key=:key"), {"key": user_key})
    original_finalize = auth_routes.finalize

    def overflow_mutant(db, actual_buckets, *, success):
        if success:
            return original_finalize(db, actual_buckets, success=True)
        try:
            db.execute(text(
                "UPDATE rtdir_login_rate_limit_buckets SET failure_count=failure_count+1 WHERE bucket_key=:key"
            ), {"key": user_key})
            db.commit()
            return 0
        except Exception as exc:
            db.rollback()
            raise RateLimitUnavailable("overflow-sensitive mutant failed") from exc

    with monkeypatch.context() as mutation:
        mutation.setattr(auth_routes, "finalize", overflow_mutant)
        changed = client.post("/api/auth/login", headers=_headers(), json={"username": "planner", "password": "wrong"})
    assert (changed.status_code, changed.json()["code"]) == (503, "AUTH_RATE_LIMIT_UNAVAILABLE")
    assert application.state.rate_limiter_ready is False
    with engine.connect() as db:
        assert db.execute(text(
            "SELECT failure_count FROM rtdir_login_rate_limit_buckets WHERE bucket_key=:key"
        ), {"key": user_key}).scalar_one() == MAX_COUNT
    application.state.rate_limiter_ready = True
    with engine.begin() as db:
        db.execute(text("UPDATE rtdir_login_rate_limit_buckets SET locked_until=NULL WHERE bucket_key=:key"), {"key": user_key})
    restored = client.post("/api/auth/login", headers=_headers(), json={"username": "planner", "password": "wrong"})
    assert (restored.status_code, restored.json()["code"]) == (429, "LOGIN_RATE_LIMITED")
    with engine.connect() as db:
        assert db.execute(text(
            "SELECT failure_count FROM rtdir_login_rate_limit_buckets WHERE bucket_key=:key"
        ), {"key": user_key}).scalar_one() == MAX_COUNT
    engine.dispose()


def test_postgresql_threshold_and_each_bucket_mutation_kill_and_restore_login_oracle(rtdir_postgres_url, monkeypatch):
    _alembic(rtdir_postgres_url, "upgrade", "b3c9d6f2a410")
    engine = create_engine(rtdir_postgres_url)
    config = _config(b"7" * 32)
    original_login_buckets = auth_routes.login_buckets

    def ordinary():
        _clear(engine)
        client, application = _postgres_client(engine, monkeypatch, config)
        application.state.rate_limiter_ready = True
        statuses = [client.post("/api/auth/login", headers=_headers(), json={"username": "planner", "password": "wrong"}).status_code for _ in range(5)]
        with engine.connect() as db:
            rows = db.execute(text(
                "SELECT bucket_kind,failure_count FROM rtdir_login_rate_limit_buckets ORDER BY bucket_kind"
            )).all()
        assert statuses == [401, 401, 401, 401, 429]
        assert rows == [("GLOBAL", 5), ("IP", 5), ("USER", 5)]

    ordinary()
    rate_limit_module.THRESHOLDS["USER"] = 6
    try:
        with pytest.raises(AssertionError):
            ordinary()
    finally:
        rate_limit_module.THRESHOLDS["USER"] = 5
    ordinary()

    for omitted in ("GLOBAL", "USER", "IP"):
        monkeypatch.setattr(auth_routes, "login_buckets", lambda actual_config, username, ip, omitted=omitted: [
            item for item in original_login_buckets(actual_config, username, ip) if item.kind != omitted
        ])
        with pytest.raises(AssertionError):
            ordinary()
        monkeypatch.setattr(auth_routes, "login_buckets", original_login_buckets)
        ordinary()
    engine.dispose()


def test_postgresql_storage_failure_and_process_local_mutations_fail_ordinary_login_oracles(rtdir_postgres_url, monkeypatch):
    _alembic(rtdir_postgres_url, "upgrade", "b3c9d6f2a410")
    engine = create_engine(rtdir_postgres_url)
    config = _config(b"8" * 32)
    original_cleanup = auth_routes.cleanup_batch
    original_precheck = auth_routes.precheck
    original_finalize = auth_routes.finalize
    argon_calls: list[str] = []
    monkeypatch.setattr(PasswordHasher, "verify", lambda self, encoded, password: argon_calls.append(password) or True)

    def unavailable():
        _clear(engine)
        client, application = _postgres_client(engine, monkeypatch, config)
        application.state.rate_limiter_ready = True
        argon_calls.clear()
        response = client.post("/api/auth/login", headers=_headers(), json={"username": "planner", "password": "correct"})
        assert (response.status_code, response.json()["code"]) == (503, "AUTH_RATE_LIMIT_UNAVAILABLE")
        assert "set-cookie" not in response.headers and argon_calls == []

    def storage_failure(db):
        raise RateLimitUnavailable("injected durable store failure")

    monkeypatch.setattr(auth_routes, "cleanup_batch", storage_failure)
    unavailable()

    def fail_open(db):
        try:
            return storage_failure(db)
        except RateLimitUnavailable:
            return 0

    monkeypatch.setattr(auth_routes, "cleanup_batch", fail_open)
    with pytest.raises((AssertionError, KeyError)):
        unavailable()
    monkeypatch.setattr(auth_routes, "cleanup_batch", storage_failure)
    unavailable()
    monkeypatch.setattr(auth_routes, "cleanup_batch", original_cleanup)

    buckets = login_buckets(config, "planner", "192.0.2.10")

    def durable_oracle():
        client, application = _postgres_client(engine, monkeypatch, config)
        application.state.rate_limiter_ready = True
        response = client.post("/api/auth/login", headers=_headers(), json={"username": "planner", "password": "correct"})
        assert (response.status_code, response.json()["code"]) == (429, "LOGIN_RATE_LIMITED")
        assert "set-cookie" not in response.headers

    _clear(engine)
    with Session(engine) as db:
        for _ in range(5):
            finalize(db, buckets, success=False)
    durable_oracle()
    monkeypatch.setattr(auth_routes, "precheck", lambda db, actual: 0)
    monkeypatch.setattr(auth_routes, "finalize", lambda db, actual, success: 0)
    with pytest.raises((AssertionError, KeyError)):
        durable_oracle()
    monkeypatch.setattr(auth_routes, "precheck", original_precheck)
    monkeypatch.setattr(auth_routes, "finalize", original_finalize)
    durable_oracle()
    engine.dispose()


def test_postgresql_cleanup_bound_active_protection_and_failure_mutations_are_detected(rtdir_postgres_url, monkeypatch):
    _alembic(rtdir_postgres_url, "upgrade", "b3c9d6f2a410")
    engine = create_engine(rtdir_postgres_url)
    original_text = rate_limit_module.text

    def seed(stale_count: int):
        _clear(engine)
        now = datetime.now(timezone.utc)
        rows = [{
            "key": f"{index:064x}", "kind": "USER", "started": now - timedelta(hours=2),
            "count": 1, "updated": now - timedelta(hours=1),
        } for index in range(stale_count)]
        rows.append({"key": "f" * 64, "kind": "IP", "started": now, "count": 19, "updated": now})
        with engine.begin() as db:
            db.execute(text("""
                INSERT INTO rtdir_login_rate_limit_buckets
                  (bucket_key,bucket_kind,window_started_at,failure_count,locked_until,updated_at)
                VALUES (:key,:kind,:started,:count,NULL,:updated)
            """), rows)

    def bounded_oracle():
        seed(65)
        with Session(engine) as db:
            assert cleanup_batch(db) == 64
            assert cleanup_batch(db) == 1
        with engine.connect() as db:
            assert db.execute(text("SELECT count(*) FROM rtdir_login_rate_limit_buckets WHERE bucket_key=:key"), {"key": "f" * 64}).scalar_one() == 1

    bounded_oracle()

    def limit_mutant(statement):
        raw = str(statement)
        if "FOR UPDATE SKIP LOCKED LIMIT 64" in raw:
            raw = raw.replace("LIMIT 64", "LIMIT 65")
        return original_text(raw)

    monkeypatch.setattr(rate_limit_module, "text", limit_mutant)
    with pytest.raises(AssertionError):
        bounded_oracle()
    monkeypatch.setattr(rate_limit_module, "text", original_text)
    bounded_oracle()

    def active_oracle():
        seed(1)
        with Session(engine) as db:
            assert cleanup_batch(db) == 1
        with engine.connect() as db:
            assert db.execute(text("SELECT count(*) FROM rtdir_login_rate_limit_buckets WHERE bucket_key=:key"), {"key": "f" * 64}).scalar_one() == 1

    active_oracle()

    def active_mutant(statement):
        raw = str(statement)
        if "SELECT bucket_key FROM rtdir_login_rate_limit_buckets" in raw and "updated_at <" in raw:
            raw = raw.replace("WHERE updated_at < transaction_timestamp() - INTERVAL '1800 seconds'", "")
        return original_text(raw)

    monkeypatch.setattr(rate_limit_module, "text", active_mutant)
    with pytest.raises(AssertionError):
        active_oracle()
    monkeypatch.setattr(rate_limit_module, "text", original_text)
    active_oracle()

    application = create_app(_config(b"9" * 32))
    monkeypatch.setattr(app_main, "get_session_factory", lambda: sessionmaker(bind=engine))
    original_cleanup = app_main.cleanup_batch

    def readiness_oracle():
        assert app_main._cleanup_once(application) is False
        assert application.state.rate_limiter_ready is False

    monkeypatch.setattr(app_main, "cleanup_batch", lambda db: (_ for _ in ()).throw(RateLimitUnavailable("cleanup failed")))
    readiness_oracle()
    monkeypatch.setattr(app_main, "cleanup_batch", lambda db: 0)
    with pytest.raises(AssertionError):
        readiness_oracle()
    monkeypatch.setattr(app_main, "cleanup_batch", lambda db: (_ for _ in ()).throw(RateLimitUnavailable("cleanup failed")))
    readiness_oracle()
    monkeypatch.setattr(app_main, "cleanup_batch", original_cleanup)
    engine.dispose()
