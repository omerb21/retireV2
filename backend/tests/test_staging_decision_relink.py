from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Callable

import httpx
import pytest


SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from staging_decision_relink import (  # noqa: E402
    ACTION,
    AMOUNT,
    CLIENT_ID,
    COMPONENT_CODE,
    DECISION_ID,
    EFFECTIVE_DATE,
    EXPECTED_VERSION,
    NEW_COMPONENT_ID,
    NEW_PRODUCT_ID,
    OLD_COMPONENT_ID,
    OLD_PRODUCT_ID,
    PRODUCT_PATH,
    RelinkError,
    SCENARIO_ID,
    SCENARIO_NAME,
    SCENARIO_PATH,
    SOURCE_BALANCE,
    STAGING_ORIGIN,
    run_relink,
)
from staging_permission_preview_probe import ProbeError  # noqa: E402


ORIGIN = STAGING_ORIGIN
COOKIE = "opaque-session-cookie"
CSRF = base64.urlsafe_b64encode(b"R" * 32).decode().rstrip("=")
PASSWORD = "never-log-this-password"
SECRETS = (PASSWORD, COOKIE, CSRF)


def _scenario(*, version: int = EXPECTED_VERSION) -> dict[str, Any]:
    return {
        "scenario_id": SCENARIO_ID,
        "client_id": CLIENT_ID,
        "name": SCENARIO_NAME,
        "status": "draft",
        "version": version,
        "created_by": "planner",
        "updated_by": "planner",
        "decisions": [{
            "decision_id": DECISION_ID,
            "source_product_id": OLD_PRODUCT_ID,
            "source_component_id": OLD_COMPONENT_ID,
            "component_code": COMPONENT_CODE,
            "amount": AMOUNT,
            "action": ACTION,
            "effective_date": EFFECTIVE_DATE,
            "validation_state": "unverified",
            "product_version_at_review": 2,
            "source_fingerprint_at_review": "a" * 64,
            "ruleset_digest_at_review": None,
            "permission_preview_id_at_review": None,
        }],
        "financial_validation": "not_evaluated",
    }


def _product() -> dict[str, Any]:
    return {
        "client_id": CLIENT_ID,
        "product_id": NEW_PRODUCT_ID,
        "version": 4,
        "product_type": "קרן פנסיה",
        "source_kind": "manual",
        "source_identity": "synthetic-product-source",
        "conversion_components": [{
            "component_id": NEW_COMPONENT_ID,
            "component_code": COMPONENT_CODE,
            "balance": SOURCE_BALANCE,
            "allowed_destinations": ["pension"],
        }],
    }


SOURCE_PREIMAGE = {
    "schema": "scenario-draft-source-v1",
    "client_id": CLIENT_ID,
    "product_id": NEW_PRODUCT_ID,
    "product_version": 4,
    "product_type": "קרן פנסיה",
    "source_kind": "manual",
    "source_identity": "synthetic-product-source",
    "component_product_id": NEW_PRODUCT_ID,
    "component_id": NEW_COMPONENT_ID,
    "component_code": COMPONENT_CODE,
    "balance": SOURCE_BALANCE,
}
SOURCE_FINGERPRINT = hashlib.sha256(json.dumps(
    SOURCE_PREIMAGE,
    ensure_ascii=False,
    sort_keys=True,
    separators=(",", ":"),
    allow_nan=False,
).encode("utf-8")).hexdigest()


def _success() -> dict[str, Any]:
    body = _scenario(version=EXPECTED_VERSION + 1)
    body["decisions"][0].update({
        "source_product_id": NEW_PRODUCT_ID,
        "source_component_id": NEW_COMPONENT_ID,
        "product_version_at_review": 4,
        "source_fingerprint_at_review": SOURCE_FINGERPRINT,
    })
    return body


def _response(status: int, body: dict[str, Any]) -> Callable[[httpx.Request], httpx.Response]:
    return lambda _request: httpx.Response(status, json=body)


def _client(
    observed: list[dict[str, Any]],
    *,
    login: Callable[[httpx.Request], httpx.Response] | None = None,
    session: Callable[[httpx.Request], httpx.Response] | None = None,
    scenario: Callable[[httpx.Request], httpx.Response] | None = None,
    product: Callable[[httpx.Request], httpx.Response] | None = None,
    put: Callable[[httpx.Request], httpx.Response] | None = None,
    logout: Callable[[httpx.Request], httpx.Response] | None = None,
) -> httpx.Client:
    login = login or (lambda _request: httpx.Response(
        200,
        json={"authenticated": True, "csrf_token": CSRF},
        headers={"set-cookie": f"rtdir_session={COOKIE}; Path=/; Secure; HttpOnly; SameSite=Lax"},
    ))
    session = session or _response(200, {"authenticated": True, "csrf_token": CSRF})
    scenario = scenario or _response(200, _scenario())
    product = product or _response(200, _product())
    put = put or _response(200, _success())
    logout = logout or (lambda _request: httpx.Response(204))

    def handler(request: httpx.Request) -> httpx.Response:
        record = {
            "method": request.method,
            "path": request.url.path,
            "origin": request.headers.get("origin"),
            "csrf": request.headers.get("x-rtdir-csrf"),
            "cookie": request.headers.get("cookie"),
            "body": json.loads(request.content) if request.content else None,
        }
        observed.append(record)
        if request.url.path == "/api/auth/login":
            assert record["body"] == {"username": "staging-user", "password": PASSWORD}
            return login(request)
        if request.url.path == "/api/auth/session":
            return session(request)
        if request.url.path == SCENARIO_PATH and request.method == "GET":
            return scenario(request)
        if request.url.path == PRODUCT_PATH:
            return product(request)
        if request.url.path == SCENARIO_PATH and request.method == "PUT":
            return put(request)
        if request.url.path == "/api/auth/logout":
            return logout(request)
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    return httpx.Client(base_url=ORIGIN, transport=httpx.MockTransport(handler))


def _run(client: httpx.Client) -> dict[str, Any]:
    return run_relink(
        client, origin=ORIGIN, username="staging-user", password=PASSWORD,
    )


def _paths(observed: list[dict[str, Any]]) -> list[tuple[str, str]]:
    return [(row["method"], row["path"]) for row in observed]


def test_success_preserves_decision_id_and_uses_one_canonical_put() -> None:
    observed: list[dict[str, Any]] = []
    with _client(observed) as client:
        result = _run(client)
    assert result == {
        "schema_version": "STAGING_DECISION_RELINK_EVIDENCE_V1",
        "target": {
            "client_id": CLIENT_ID,
            "scenario_id": SCENARIO_ID,
            "decision_id": DECISION_ID,
            "source_product_id": NEW_PRODUCT_ID,
            "source_component_id": NEW_COMPONENT_ID,
        },
        "http_status": 200,
        "response_code": None,
        "scenario_version_before": 4,
        "scenario_version_after": 5,
        "decision_id_preserved": True,
        "put_attempts": 1,
        "commit_outcome": "confirmed",
    }
    puts = [row for row in observed if row["method"] == "PUT"]
    assert len(puts) == 1
    assert puts[0]["path"] == SCENARIO_PATH
    assert puts[0]["origin"] == ORIGIN
    assert puts[0]["csrf"] == CSRF
    assert puts[0]["body"] == {
        "expected_version": 4,
        "name": SCENARIO_NAME,
        "decisions": [{
            "decision_id": DECISION_ID,
            "source_product_id": NEW_PRODUCT_ID,
            "source_component_id": NEW_COMPONENT_ID,
            "component_code": COMPONENT_CODE,
            "amount": AMOUNT,
            "action": ACTION,
            "effective_date": EFFECTIVE_DATE,
        }],
    }
    assert _paths(observed)[-1] == ("POST", "/api/auth/logout")


@pytest.mark.parametrize("code", [
    "SCENARIO_VERSION_CONFLICT",
    "SCENARIO_DECISION_HAS_PRICE_BASIS_HISTORY",
])
def test_http_409_is_preserved_without_retry(code: str) -> None:
    observed: list[dict[str, Any]] = []
    with _client(observed, put=_response(409, {"code": code})) as client:
        result = _run(client)
    assert result["http_status"] == 409
    assert result["response_code"] == code
    assert result["commit_outcome"] == "rejected"
    assert sum(row["method"] == "PUT" for row in observed) == 1


@pytest.mark.parametrize("mutate,code", [
    (lambda body: body.update(version=5), "SCENARIO_PREFLIGHT_MISMATCH"),
    (lambda body: body["decisions"][0].update(decision_id="another"), "DECISION_PREFLIGHT_MISMATCH"),
])
def test_scenario_or_decision_mismatch_stops_before_put(
    mutate: Callable[[dict[str, Any]], None], code: str,
) -> None:
    body = _scenario()
    mutate(body)
    observed: list[dict[str, Any]] = []
    with _client(observed, scenario=_response(200, body)) as client:
        with pytest.raises(RelinkError, match=code):
            _run(client)
    assert not any(row["method"] == "PUT" for row in observed)
    assert _paths(observed)[-1] == ("POST", "/api/auth/logout")


@pytest.mark.parametrize("mutate,code", [
    (lambda body: body.update(product_id="another"), "SOURCE_PRODUCT_IDENTITY_MISMATCH"),
    (lambda body: body["conversion_components"][0].update(component_id="another"), "SOURCE_COMPONENT_IDENTITY_MISMATCH"),
    (lambda body: body["conversion_components"][0].update(balance="99999.99"), "SOURCE_COMPONENT_CONTRACT_MISMATCH"),
])
def test_product_or_component_mismatch_stops_before_put(
    mutate: Callable[[dict[str, Any]], None], code: str,
) -> None:
    body = _product()
    mutate(body)
    observed: list[dict[str, Any]] = []
    with _client(observed, product=_response(200, body)) as client:
        with pytest.raises(RelinkError, match=code):
            _run(client)
    assert not any(row["method"] == "PUT" for row in observed)


def test_login_failure_stops_without_session_or_put() -> None:
    observed: list[dict[str, Any]] = []
    with _client(observed, login=_response(401, {"code": "AUTHENTICATION_FAILED"})) as client:
        with pytest.raises(RelinkError, match="LOGIN_REJECTED"):
            _run(client)
    assert _paths(observed) == [("POST", "/api/auth/login")]


def test_non_staging_origin_is_rejected_before_login() -> None:
    observed: list[dict[str, Any]] = []
    with _client(observed) as client:
        with pytest.raises(ProbeError, match="STAGING_ORIGIN_NOT_ALLOWED"):
            run_relink(
                client,
                origin="https://retire-v2-app-production.up.railway.app",
                username="staging-user",
                password=PASSWORD,
            )
    assert observed == []


def test_missing_login_csrf_recovers_session_csrf_for_logout() -> None:
    observed: list[dict[str, Any]] = []
    login = lambda _request: httpx.Response(  # noqa: E731
        200,
        json={"authenticated": True},
        headers={"set-cookie": f"rtdir_session={COOKIE}; Path=/; Secure; HttpOnly; SameSite=Lax"},
    )
    with _client(observed, login=login) as client:
        with pytest.raises(RelinkError, match="LOGIN_CSRF_INVALID"):
            _run(client)
    assert _paths(observed) == [
        ("POST", "/api/auth/login"),
        ("GET", "/api/auth/session"),
        ("POST", "/api/auth/logout"),
    ]


def test_server_csrf_rejection_is_not_treated_as_success() -> None:
    observed: list[dict[str, Any]] = []
    with _client(observed, put=_response(403, {"code": "CSRF_INVALID"})) as client:
        with pytest.raises(RelinkError, match=r"HTTP 403.*CSRF_INVALID"):
            _run(client)
    assert sum(row["method"] == "PUT" for row in observed) == 1
    assert _paths(observed)[-1] == ("POST", "/api/auth/logout")


def test_network_failure_after_put_is_unknown_and_never_retried() -> None:
    observed: list[dict[str, Any]] = []

    def failed_put(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("response lost after send", request=request)

    with _client(observed, put=failed_put) as client:
        with pytest.raises(RelinkError, match="RELINK_PUT_NETWORK_FAILURE"):
            _run(client)
    assert sum(row["method"] == "PUT" for row in observed) == 1
    assert _paths(observed)[-1] == ("POST", "/api/auth/logout")


def test_logout_204_confirms_cleanup_after_success() -> None:
    observed: list[dict[str, Any]] = []
    with _client(observed, logout=lambda _request: httpx.Response(204)) as client:
        result = _run(client)
    assert result["http_status"] == 200
    assert result["commit_outcome"] == "confirmed"
    assert _paths(observed)[-1] == ("POST", "/api/auth/logout")


def test_logout_401_after_success_preserves_put_and_fails_cleanup() -> None:
    observed: list[dict[str, Any]] = []
    with _client(observed, logout=_response(401, {"code": "AUTHENTICATION_REQUIRED"})) as client:
        with pytest.raises(RelinkError, match="RELINK_CLEANUP_FAILED") as captured:
            _run(client)
    assert captured.value.put_evidence is not None
    assert captured.value.put_evidence["http_status"] == 200
    assert captured.value.put_evidence["commit_outcome"] == "confirmed"
    assert captured.value.cleanup_error == "LOGOUT_UNCONFIRMED (HTTP 401)"


def test_logout_failure_is_reported_after_success() -> None:
    observed: list[dict[str, Any]] = []
    with _client(observed, logout=_response(500, {"code": "LOGOUT_FAILED"})) as client:
        with pytest.raises(RelinkError, match="RELINK_CLEANUP_FAILED") as captured:
            _run(client)
    assert captured.value.put_evidence is not None
    assert captured.value.cleanup_error == "LOGOUT_UNCONFIRMED (HTTP 500)"
    assert sum(row["method"] == "PUT" for row in observed) == 1


def test_prior_failure_and_logout_failure_are_reported_separately() -> None:
    observed: list[dict[str, Any]] = []
    with _client(
        observed,
        put=_response(403, {"code": "CSRF_INVALID"}),
        logout=_response(500, {"code": "LOGOUT_FAILED"}),
    ) as client:
        with pytest.raises(RelinkError, match=r"HTTP 403.*CSRF_INVALID") as captured:
            _run(client)
    assert captured.value.put_evidence is None
    assert captured.value.cleanup_error == "LOGOUT_UNCONFIRMED (HTTP 500)"


def test_failure_messages_never_expose_credentials_cookie_or_csrf() -> None:
    observed: list[dict[str, Any]] = []
    with _client(observed, put=_response(503, {"code": "DATABASE_UNAVAILABLE"})) as client:
        with pytest.raises(RelinkError) as captured:
            _run(client)
    rendered = str(captured.value)
    assert "HTTP 503" in rendered
    assert "DATABASE_UNAVAILABLE" in rendered
    assert all(secret not in rendered for secret in SECRETS)


def test_success_response_with_changed_decision_id_is_rejected() -> None:
    body = _success()
    body["decisions"][0]["decision_id"] = "changed"
    observed: list[dict[str, Any]] = []
    with _client(observed, put=_response(200, body)) as client:
        with pytest.raises(RelinkError, match="RELINK_RESPONSE_DECISION_MISMATCH"):
            _run(client)
    assert sum(row["method"] == "PUT" for row in observed) == 1


@pytest.mark.parametrize("version", [999, "4", True])
def test_success_response_with_wrong_product_version_is_rejected(
    version: object,
) -> None:
    body = _success()
    body["decisions"][0]["product_version_at_review"] = version
    observed: list[dict[str, Any]] = []
    with _client(observed, put=_response(200, body)) as client:
        with pytest.raises(RelinkError, match="RELINK_RESPONSE_PRODUCT_VERSION_MISMATCH"):
            _run(client)


@pytest.mark.parametrize("fingerprint", ["not-a-sha", "A" * 64, 123, None])
def test_success_response_with_malformed_fingerprint_is_rejected(
    fingerprint: object,
) -> None:
    body = _success()
    body["decisions"][0]["source_fingerprint_at_review"] = fingerprint
    observed: list[dict[str, Any]] = []
    with _client(observed, put=_response(200, body)) as client:
        with pytest.raises(RelinkError, match="RELINK_RESPONSE_SOURCE_FINGERPRINT_INVALID"):
            _run(client)


def test_success_response_fingerprint_matches_canonical_preimage() -> None:
    observed: list[dict[str, Any]] = []
    with _client(observed) as client:
        result = _run(client)
    assert SOURCE_FINGERPRINT == "04f3999049577f43cc5891d92365875186ca537e555997420463a11e72d2ab91"
    assert result["http_status"] == 200


def test_success_response_with_well_formed_wrong_fingerprint_is_rejected() -> None:
    body = _success()
    body["decisions"][0]["source_fingerprint_at_review"] = "f" * 64
    observed: list[dict[str, Any]] = []
    with _client(observed, put=_response(200, body)) as client:
        with pytest.raises(RelinkError, match="RELINK_RESPONSE_SOURCE_FINGERPRINT_MISMATCH"):
            _run(client)


@pytest.mark.parametrize("field", [
    "product_version_at_review",
    "source_fingerprint_at_review",
])
def test_success_response_missing_source_evidence_is_rejected(field: str) -> None:
    body = _success()
    del body["decisions"][0][field]
    observed: list[dict[str, Any]] = []
    with _client(observed, put=_response(200, body)) as client:
        expected = (
            "RELINK_RESPONSE_PRODUCT_VERSION_MISMATCH"
            if field == "product_version_at_review"
            else "RELINK_RESPONSE_SOURCE_FINGERPRINT_INVALID"
        )
        with pytest.raises(RelinkError, match=expected):
            _run(client)
