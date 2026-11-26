from __future__ import annotations

import json
from pathlib import Path
import sys

import httpx
import pytest


SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from staging_permission_preview_probe import ProbeError, run_probe  # noqa: E402


ORIGIN = "https://staging.example"
COOKIE = "opaque-session-cookie"
CSRF = "C" * 43
PASSWORD = "never-log-this-password"
TARGET = {
    "client_id": 7,
    "product_id": "96edb78aaa734d0c845ae8f6ee36da50",
    "action": "pension",
    "effective_date": "2026-12-15",
}


def _client(permission_response: httpx.Response, observed: list[dict[str, object]]) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        record = {
            "path": request.url.path,
            "origin": request.headers.get("origin"),
            "csrf": request.headers.get("x-rtdir-csrf"),
            "cookie": request.headers.get("cookie"),
        }
        if request.content:
            record["body"] = json.loads(request.content)
        observed.append(record)
        if request.url.path == "/api/auth/login":
            assert record["body"] == {"username": "staging-user", "password": PASSWORD}
            return httpx.Response(
                200,
                json={"authenticated": True},
                headers={"set-cookie": f"rtdir_session={COOKIE}; Path=/; Secure; HttpOnly; SameSite=Lax"},
            )
        if request.url.path == "/api/auth/session":
            assert request.headers.get("cookie") == f"rtdir_session={COOKIE}"
            return httpx.Response(200, json={"authenticated": True, "csrf_token": CSRF})
        if request.url.path.endswith("/permission-preview"):
            assert request.headers.get("cookie") == f"rtdir_session={COOKIE}"
            assert request.headers.get("origin") == ORIGIN
            assert request.headers.get("x-rtdir-csrf") == CSRF
            assert record["body"] == {
                "product_id": TARGET["product_id"],
                "action": TARGET["action"],
                "effective_date": TARGET["effective_date"],
            }
            return permission_response
        if request.url.path == "/api/auth/logout":
            assert request.headers.get("cookie") == f"rtdir_session={COOKIE}"
            assert request.headers.get("x-rtdir-csrf") == CSRF
            return httpx.Response(204)
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    return httpx.Client(base_url=ORIGIN, transport=httpx.MockTransport(handler))


def test_authenticated_probe_records_allowed_and_blocked_components_without_secrets():
    observed: list[dict[str, object]] = []
    body = {
        "schema_version": "SCENARIO_PERMISSION_PREVIEW_V1",
        **TARGET,
        "overall_status": "mixed",
        "components": [
            {"component_code": "allowed-component", "permission_status": "allowed",
             "reason_code": "BASE_PERMISSION_ALLOWED", "reason_he": "מותר"},
            {"component_code": "blocked-component", "permission_status": "blocked",
             "reason_code": "BASE_PERMISSION_BLOCKED", "reason_he": "חסום"},
        ],
    }
    with _client(httpx.Response(200, json=body), observed) as client:
        evidence = run_probe(
            client, origin=ORIGIN, username="staging-user", password=PASSWORD, **TARGET,
        )

    assert [row["path"] for row in observed] == [
        "/api/auth/login", "/api/auth/session",
        "/api/clients/7/scenario-conversions/permission-preview", "/api/auth/logout",
    ]
    assert evidence["authenticated_session"] is True
    assert evidence["http_status"] == 200
    assert evidence["overall_status"] == "mixed"
    assert [row["permission_status"] for row in evidence["permissions"]] == ["allowed", "blocked"]
    serialized = json.dumps(evidence)
    assert PASSWORD not in serialized
    assert COOKIE not in serialized
    assert CSRF not in serialized


def test_authenticated_probe_preserves_domain_block_code_without_claiming_allowed():
    observed: list[dict[str, object]] = []
    response = httpx.Response(
        422,
        json={"code": "UNKNOWN_PRODUCT_TYPE", "field_paths": ["/product_id"]},
    )
    with _client(response, observed) as client:
        evidence = run_probe(
            client, origin=ORIGIN, username="staging-user", password=PASSWORD, **TARGET,
        )

    assert evidence == {
        "schema_version": "STAGING_PERMISSION_PREVIEW_PROBE_EVIDENCE_V1",
        "target": TARGET,
        "authenticated_session": True,
        "http_status": 422,
        "response_code": "UNKNOWN_PRODUCT_TYPE",
        "overall_status": None,
        "permissions": [],
        "field_paths": ["/product_id"],
    }
    assert observed[-1]["path"] == "/api/auth/logout"


@pytest.mark.parametrize("status,code", [(401, "SESSION_MISSING"), (403, "CSRF_INVALID"), (503, "INTERNAL_ERROR")])
def test_probe_fails_on_authentication_or_technical_permission_failure(status: int, code: str):
    observed: list[dict[str, object]] = []
    with _client(httpx.Response(status, json={"code": code}), observed) as client:
        with pytest.raises(ProbeError, match="PERMISSION_PREVIEW_TECHNICAL_FAILURE"):
            run_probe(client, origin=ORIGIN, username="staging-user", password=PASSWORD, **TARGET)
    assert observed[-1]["path"] == "/api/auth/logout"


def test_probe_rejects_non_https_or_credential_bearing_origin_before_login():
    for origin in ("http://staging.example", "https://user:pass@staging.example", "https://staging.example/path"):
        with pytest.raises(ProbeError, match="STAGING_ORIGIN_INVALID"):
            run_probe(object(), origin=origin, username="u", password="p", **TARGET)
