from __future__ import annotations

import asyncio
import base64
from pathlib import Path
from types import SimpleNamespace

from argon2 import PasswordHasher
from fastapi.testclient import TestClient
import pytest
from sqlalchemy.exc import OperationalError

from app import main as app_main
from app.main import create_app
from app.security.config import AuthConfig
from app.security.rate_limit import RateLimitUnavailable


ROOT = Path(__file__).resolve().parents[2]
PLATFORM_ENV = {
    "APP_ENV",
    "AUTH_ACTOR_ID",
    "AUTH_DUMMY_PASSWORD_HASH",
    "AUTH_INGRESS_MODE",
    "AUTH_PASSWORD_HASH",
    "AUTH_PUBLIC_ORIGIN",
    "AUTH_RATE_LIMIT_SECRET_B64",
    "AUTH_SESSION_SECRET_B64",
    "AUTH_USERNAME",
    "DATABASE_URL",
    "RAILWAY_DEPLOYMENT_OVERLAP_SECONDS",
    "RAILWAY_ENVIRONMENT",
    "RAILWAY_ENVIRONMENT_NAME",
    "RAILWAY_PROJECT_ID",
    "RAILWAY_SERVICE_ID",
    "RENDER",
    "RENDER_EXTERNAL_HOSTNAME",
    "RENDER_SERVICE_ID",
    "RENDER_SERVICE_TYPE",
    "STAGE6_APPROVED_DATABASE_HOST",
    "STAGE6_APPROVED_RENDER_HOSTNAME",
    "STAGE6_APPROVED_RENDER_SERVICE_ID",
    "STAGE6_PREVIEW_ENABLED",
    "WEB_CONCURRENCY",
}


@pytest.fixture
def clean_platform_env(monkeypatch):
    for name in PLATFORM_ENV:
        monkeypatch.delenv(name, raising=False)


def _secret(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _production_env(monkeypatch, ingress_mode: str) -> None:
    hasher = PasswordHasher(
        time_cost=3,
        memory_cost=65536,
        parallelism=4,
        hash_len=32,
        salt_len=16,
    )
    values = {
        "APP_ENV": "production",
        "AUTH_ACTOR_ID": "planner:render",
        "AUTH_DUMMY_PASSWORD_HASH": hasher.hash("dummy-password"),
        "AUTH_INGRESS_MODE": ingress_mode,
        "AUTH_PASSWORD_HASH": hasher.hash("operator-password"),
        "AUTH_PUBLIC_ORIGIN": "https://retirev2.onrender.com",
        "AUTH_RATE_LIMIT_SECRET_B64": _secret(b"r" * 32),
        "AUTH_SESSION_SECRET_B64": _secret(b"s" * 32),
        "AUTH_USERNAME": "planner",
        "DATABASE_URL": "postgresql+psycopg2://user:password@db.internal/retire_v2",
        "WEB_CONCURRENCY": "1",
    }
    if ingress_mode == "render_public_edge":
        values.update({
            "RENDER": "true",
            "RENDER_EXTERNAL_HOSTNAME": "retirev2.onrender.com",
            "RENDER_SERVICE_TYPE": "web",
        })
    else:
        values.update({
            "RAILWAY_DEPLOYMENT_OVERLAP_SECONDS": "0",
            "RAILWAY_ENVIRONMENT": "production",
        })
    for name, value in values.items():
        monkeypatch.setenv(name, value)


def _render_config() -> AuthConfig:
    return AuthConfig(
        production=True,
        ingress_mode="render_public_edge",
        public_origin="https://retirev2.onrender.com",
        public_authority="retirev2.onrender.com",
        username="planner",
        password_hash="unused-by-this-test",
        dummy_password_hash="unused-by-this-test-too",
        actor_id="planner:render",
        session_secret=b"s" * 32,
        rate_limit_secret=b"r" * 32,
    )


def _isolated_render_config() -> AuthConfig:
    return AuthConfig(
        production=True,
        ingress_mode="render_public_edge",
        public_origin="https://retirev2-stage6-review.onrender.com",
        public_authority="retirev2-stage6-review.onrender.com",
        username="planner",
        password_hash="unused-by-this-test",
        dummy_password_hash="unused-by-this-test-too",
        actor_id="planner:render",
        session_secret=b"s" * 32,
        rate_limit_secret=b"r" * 32,
    )


def _render_headers() -> dict[str, str]:
    return {
        "host": "retirev2.onrender.com",
        "cf-connecting-ip": "2001:db8::9",
        "x-forwarded-proto": "https",
    }


def _database_error(message: str) -> OperationalError:
    return OperationalError("SELECT 1", {}, RuntimeError(message))


class _ReadinessSession:
    def __init__(
        self,
        versions: list[str] | None = None,
        *,
        execute_error: OperationalError | None = None,
        close_error: OperationalError | None = None,
    ):
        self.versions = versions or []
        self.execute_error = execute_error
        self.close_error = close_error
        self.rollback_calls = 0
        self.close_calls = 0
        self.invalidate_calls = 0

    def execute(self, _statement):
        if self.execute_error is not None:
            raise self.execute_error
        return SimpleNamespace(
            scalars=lambda: SimpleNamespace(all=lambda: self.versions)
        )

    def rollback(self):
        self.rollback_calls += 1

    def close(self):
        self.close_calls += 1
        if self.close_error is not None:
            raise self.close_error

    def invalidate(self):
        self.invalidate_calls += 1


def test_docker_runtime_starts_original_application_without_test_runner() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "exec python -m uvicorn app.main:app" in dockerfile
    assert "--host 0.0.0.0" in dockerfile
    assert "${PORT:?PORT is required}" in dockerfile
    assert "--workers 1 --no-proxy-headers" in dockerfile
    assert "run_stage6_render_pg_tests.sh" not in dockerfile
    assert "apt-get install -y --no-install-recommends postgresql" not in dockerfile
    assert "npm run test" not in dockerfile
    assert "RUN npm run build" in dockerfile


def test_render_production_environment_is_explicit_and_fail_closed(clean_platform_env, monkeypatch) -> None:
    _production_env(monkeypatch, "render_public_edge")
    config = AuthConfig.from_env()

    assert config.production is True
    assert config.ingress_mode == "render_public_edge"
    assert config.public_authority == "retirev2.onrender.com"

    monkeypatch.setenv("RENDER_EXTERNAL_HOSTNAME", "other-service.onrender.com")
    with pytest.raises(RuntimeError, match="RENDER_EXTERNAL_HOSTNAME"):
        AuthConfig.from_env()


def test_railway_production_environment_contract_remains_unchanged(clean_platform_env, monkeypatch) -> None:
    _production_env(monkeypatch, "railway_public_edge")
    config = AuthConfig.from_env()

    assert config.production is True
    assert config.ingress_mode == "railway_public_edge"


def test_render_edge_uses_cloudflare_identity_and_rejects_spoofed_or_wrong_host() -> None:
    client = TestClient(create_app(_render_config()))
    accepted_headers = _render_headers()

    accepted = client.get("/healthz/live", headers=accepted_headers)
    spoofed = client.get(
        "/healthz/live",
        headers={
            "host": "retirev2.onrender.com",
            "x-real-ip": "127.0.0.1",
            "x-forwarded-for": "127.0.0.1",
            "x-forwarded-proto": "https",
        },
    )
    wrong_host = client.get(
        "/healthz/live",
        headers={**accepted_headers, "x-forwarded-host": "evil.example"},
    )
    railway_health_bypass = client.get(
        "/healthz/ready",
        headers={"host": "healthcheck.railway.app"},
    )

    assert accepted.status_code == 200
    assert accepted.json() == {"status": "ok"}
    assert (spoofed.status_code, spoofed.json()["code"]) == (400, "EDGE_REQUEST_INVALID")
    assert (wrong_host.status_code, wrong_host.json()["code"]) == (400, "EDGE_REQUEST_INVALID")
    assert (railway_health_bypass.status_code, railway_health_bypass.json()["code"]) == (400, "EDGE_REQUEST_INVALID")


def test_render_cannot_enable_railway_only_stage6_routes(monkeypatch) -> None:
    monkeypatch.setenv("STAGE6_PREVIEW_ENABLED", "1")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", "staging")

    application = create_app(_render_config())

    assert application.state.stage6_preview_enabled is False
    assert not any(
        getattr(getattr(route, "endpoint", None), "__module__", "").startswith(
            "app.api.scenario_stage6_"
        )
        for route in application.routes
    )


def test_active_render_service_stays_blocked_even_with_explicit_stage6_values(monkeypatch) -> None:
    monkeypatch.setenv("STAGE6_PREVIEW_ENABLED", "1")
    monkeypatch.setenv("RENDER_SERVICE_ID", "srv-active")
    monkeypatch.setenv("RENDER_EXTERNAL_HOSTNAME", "retirev2.onrender.com")
    monkeypatch.setenv("STAGE6_APPROVED_RENDER_SERVICE_ID", "srv-active")
    monkeypatch.setenv("STAGE6_APPROVED_RENDER_HOSTNAME", "retirev2.onrender.com")
    monkeypatch.setenv("STAGE6_APPROVED_DATABASE_HOST", "db.internal")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://u:p@db.internal/retire_v2")

    application = create_app(_render_config())

    assert application.state.stage6_preview_enabled is False


def test_isolated_render_stage6_requires_exact_service_host_and_database_identity(monkeypatch) -> None:
    monkeypatch.setenv("STAGE6_PREVIEW_ENABLED", "1")
    monkeypatch.setenv("RENDER_SERVICE_ID", "srv-stage6-review")
    monkeypatch.setenv("RENDER_EXTERNAL_HOSTNAME", "retirev2-stage6-review.onrender.com")
    monkeypatch.setenv("STAGE6_APPROVED_RENDER_SERVICE_ID", "srv-stage6-review")
    monkeypatch.setenv("STAGE6_APPROVED_RENDER_HOSTNAME", "retirev2-stage6-review.onrender.com")
    monkeypatch.setenv("STAGE6_APPROVED_DATABASE_HOST", "stage6-db.internal")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://u:p@stage6-db.internal/retire_v2")

    assert create_app(_isolated_render_config()).state.stage6_preview_enabled is True

    monkeypatch.setenv("RENDER_SERVICE_ID", "srv-other")
    assert create_app(_isolated_render_config()).state.stage6_preview_enabled is False
    monkeypatch.setenv("RENDER_SERVICE_ID", "srv-stage6-review")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://u:p@other-db.internal/retire_v2")
    assert create_app(_isolated_render_config()).state.stage6_preview_enabled is False


def test_readiness_turns_red_on_database_loss_and_recovers_without_restart(monkeypatch) -> None:
    healthy_before = _ReadinessSession([app_main.EXPECTED_ALEMBIC_HEAD])
    disconnected = _ReadinessSession(
        execute_error=_database_error("database disconnected")
    )
    healthy_after = _ReadinessSession([app_main.EXPECTED_ALEMBIC_HEAD])
    sessions = iter([healthy_before, disconnected, healthy_after])
    monkeypatch.setattr(
        app_main, "get_session_factory", lambda: lambda: next(sessions)
    )
    monkeypatch.setattr(app_main, "cleanup_batch", lambda _db: 0)
    application = create_app(_render_config())
    client = TestClient(application)

    assert app_main._cleanup_once(application) is True
    assert client.get("/healthz/ready", headers=_render_headers()).status_code == 200

    assert app_main._cleanup_once(application) is False
    unavailable = client.get("/healthz/ready", headers=_render_headers())
    assert (unavailable.status_code, unavailable.json()) == (
        503,
        {"status": "unavailable"},
    )
    assert disconnected.rollback_calls == 1
    assert disconnected.close_calls == 1

    assert app_main._cleanup_once(application) is True
    recovered = client.get("/healthz/ready", headers=_render_headers())
    assert (recovered.status_code, recovered.json()) == (200, {"status": "ready"})
    assert healthy_before.close_calls == healthy_after.close_calls == 1


@pytest.mark.parametrize("versions", [[], ["wrong-head"]])
def test_readiness_rejects_missing_or_wrong_migration_head(
    monkeypatch, versions
) -> None:
    database = _ReadinessSession(versions)
    monkeypatch.setattr(app_main, "get_session_factory", lambda: lambda: database)
    monkeypatch.setattr(app_main, "cleanup_batch", lambda _db: 0)
    application = create_app(_render_config())

    assert app_main._cleanup_once(application) is False
    response = TestClient(application).get(
        "/healthz/ready", headers=_render_headers()
    )
    assert response.status_code == 503
    assert database.rollback_calls == 1
    assert database.close_calls == 1


def test_cleanup_failure_rolls_back_and_never_leaves_readiness_green(monkeypatch) -> None:
    database = _ReadinessSession([app_main.EXPECTED_ALEMBIC_HEAD])
    monkeypatch.setattr(app_main, "get_session_factory", lambda: lambda: database)
    monkeypatch.setattr(
        app_main,
        "cleanup_batch",
        lambda _db: (_ for _ in ()).throw(
            RateLimitUnavailable("injected cleanup failure")
        ),
    )
    application = create_app(_render_config())
    application.state.rate_limiter_ready = True

    assert app_main._cleanup_once(application) is False
    assert application.state.rate_limiter_ready is False
    assert database.rollback_calls == 1
    assert database.close_calls == 1


def test_session_open_and_close_database_failures_are_fail_closed(monkeypatch) -> None:
    application = create_app(_render_config())
    application.state.rate_limiter_ready = True
    monkeypatch.setattr(
        app_main,
        "get_session_factory",
        lambda: lambda: (_ for _ in ()).throw(
            _database_error("session acquisition failed")
        ),
    )

    assert app_main._cleanup_once(application) is False
    assert application.state.rate_limiter_ready is False

    close_failure = _ReadinessSession(
        [app_main.EXPECTED_ALEMBIC_HEAD],
        close_error=_database_error("session close failed"),
    )
    monkeypatch.setattr(
        app_main, "get_session_factory", lambda: lambda: close_failure
    )
    monkeypatch.setattr(app_main, "cleanup_batch", lambda _db: 0)

    assert app_main._cleanup_once(application) is False
    assert application.state.rate_limiter_ready is False
    assert close_failure.close_calls == 1
    assert close_failure.invalidate_calls == 1


def test_periodic_cleanup_survives_transient_failure_and_runs_again(monkeypatch) -> None:
    application = create_app(_render_config())
    cleanup_calls = 0
    sleep_calls = 0

    def transient_cleanup(app):
        nonlocal cleanup_calls
        cleanup_calls += 1
        if cleanup_calls == 1:
            raise _database_error("temporary database failure")
        app.state.rate_limiter_ready = True
        return True

    async def immediate_to_thread(function, *args):
        return function(*args)

    async def two_cycles_then_cancel(_interval):
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls > 2:
            raise asyncio.CancelledError

    monkeypatch.setattr(app_main, "_cleanup_once", transient_cleanup)
    monkeypatch.setattr(app_main.asyncio, "to_thread", immediate_to_thread)
    monkeypatch.setattr(app_main.asyncio, "sleep", two_cycles_then_cancel)

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(app_main._scheduled_cleanup(application, interval_seconds=0))

    assert cleanup_calls == 2
    assert application.state.rate_limiter_ready is True
