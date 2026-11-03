from __future__ import annotations

import base64
from pathlib import Path

from argon2 import PasswordHasher
from fastapi.testclient import TestClient
import pytest

from app.main import create_app
from app.security.config import AuthConfig


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
    "RENDER_SERVICE_TYPE",
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
    accepted_headers = {
        "host": "retirev2.onrender.com",
        "cf-connecting-ip": "2001:db8::9",
        "x-forwarded-proto": "https",
    }

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
