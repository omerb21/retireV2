from __future__ import annotations

from copy import deepcopy
import base64
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Callable

import httpx
import pytest

from app.models.pension_product import COMPONENT_CODES, REWARDS_CODES, SEVERANCE_CODES
from app.services import scenario_permission_preview_service as preview_contract


SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from staging_permission_preview_probe import (  # noqa: E402
    ProbeError,
    _authorized_staging_hostnames,
    _parse_allowed_hostnames,
    run_probe,
)


ORIGIN = "https://staging.example"
ALLOWED = frozenset({"staging.example"})
COOKIE = "opaque-session-cookie"
CSRF = base64.urlsafe_b64encode(b"C" * 32).decode().rstrip("=")
PASSWORD = "never-log-this-password"
TARGET = {
    "client_id": 7,
    "product_id": "96edb78aaa734d0c845ae8f6ee36da50",
    "action": "pension",
    "effective_date": "2026-12-15",
}
SECRETS = (PASSWORD, COOKIE, CSRF)


def _money(value: Decimal) -> str:
    return format(value, ".2f")


def _valid_permission_body() -> dict[str, Any]:
    ruleset = preview_contract.permission_ruleset()
    rules = {row["component_code"]: row for row in ruleset["component_rules"]}
    components = []
    balances = {}
    status_totals = {
        "allowed": Decimal("0.00"),
        "blocked": Decimal("0.00"),
        "needs_source_reconciliation": Decimal("0.00"),
        "unknown": Decimal("0.00"),
    }
    for position, code in enumerate(COMPONENT_CODES, start=1):
        balance = Decimal(position)
        decision = rules[code]["actions"][TARGET["action"]]
        balances[code] = balance
        status_totals[decision["permission_status"]] += balance
        components.append({
            "component_code": code,
            "component_id": f"component-{position:02d}",
            "balance": _money(balance),
            "permission_status": decision["permission_status"],
            "reason_code": decision["reason_code"],
            "reason_he": "מותר" if decision["permission_status"] == "allowed" else "חסום",
            "applicable_rule_id": rules[code]["rule_id"],
        })
    source_fingerprint = "a" * 64
    preview_id = hashlib.sha256(preview_contract.canonical_json({
        "schema": "scenario-permission-preview-id-v1",
        "client_id": TARGET["client_id"],
        "product_id": TARGET["product_id"],
        "source_fingerprint": source_fingerprint,
        "action": TARGET["action"],
        "effective_date": TARGET["effective_date"],
        "ruleset_id": ruleset["ruleset_id"],
        "ruleset_version": ruleset["ruleset_version"],
        "ruleset_digest": preview_contract.ruleset_digest(),
    }).encode("utf-8")).hexdigest()
    rewards = sum((balances[code] for code in REWARDS_CODES), Decimal("0.00"))
    severance = sum((balances[code] for code in SEVERANCE_CODES), Decimal("0.00"))
    return {
        "schema_version": "SCENARIO_PERMISSION_PREVIEW_V1",
        "preview_id": preview_id,
        **TARGET,
        "product_version": 4,
        "canonical_product_class": "pension_fund",
        "ruleset_id": ruleset["ruleset_id"],
        "ruleset_version": ruleset["ruleset_version"],
        "ruleset_digest": preview_contract.ruleset_digest(),
        "source_fingerprint": source_fingerprint,
        "overall_status": "mixed",
        "professional_eligibility_status": "not_evaluated",
        "tax_status": "not_evaluated",
        "components": components,
        "totals": {
            "original_classified_balance": _money(sum(balances.values(), Decimal("0.00"))),
            "allowed_balance": _money(status_totals["allowed"]),
            "blocked_balance": _money(status_totals["blocked"]),
            "needs_source_reconciliation_balance": "0.00",
            "unknown_balance": "0.00",
        },
        "reconciliation": {
            "rewards_component_sum": _money(rewards),
            "severance_component_sum": _money(severance),
            "product_component_sum": _money(rewards + severance),
            "rewards_discrepancy": None,
            "severance_discrepancy": None,
            "product_discrepancy": None,
        },
    }


def _response(status: int, body: dict[str, Any]) -> Callable[[httpx.Request], httpx.Response]:
    return lambda _request: httpx.Response(status, json=body)


def _network(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("transport unavailable", request=request)


def _client(
    permission: Callable[[httpx.Request], httpx.Response],
    observed: list[dict[str, object]],
    *,
    login: Callable[[httpx.Request], httpx.Response] | None = None,
    session: Callable[[httpx.Request], httpx.Response] | None = None,
    logout: Callable[[httpx.Request], httpx.Response] | None = None,
) -> httpx.Client:
    login = login or (lambda _request: httpx.Response(
        200,
        json={"authenticated": True, "csrf_token": CSRF},
        headers={"set-cookie": f"rtdir_session={COOKIE}; Path=/; Secure; HttpOnly; SameSite=Lax"},
    ))
    session = session or _response(200, {"authenticated": True, "csrf_token": CSRF})
    logout = logout or (lambda _request: httpx.Response(204))

    def handler(request: httpx.Request) -> httpx.Response:
        record: dict[str, object] = {
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
            return login(request)
        if request.url.path == "/api/auth/session":
            assert request.headers.get("cookie") == f"rtdir_session={COOKIE}"
            return session(request)
        if request.url.path.endswith("/permission-preview"):
            assert request.headers.get("cookie") == f"rtdir_session={COOKIE}"
            assert request.headers.get("origin") == ORIGIN
            assert request.headers.get("x-rtdir-csrf") == CSRF
            assert record["body"] == {
                "product_id": TARGET["product_id"],
                "action": TARGET["action"],
                "effective_date": TARGET["effective_date"],
            }
            return permission(request)
        if request.url.path == "/api/auth/logout":
            assert request.headers.get("cookie") == f"rtdir_session={COOKIE}"
            assert request.headers.get("x-rtdir-csrf") == CSRF
            return logout(request)
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    return httpx.Client(base_url=ORIGIN, transport=httpx.MockTransport(handler))


def _run(client: httpx.Client) -> dict[str, Any]:
    return run_probe(
        client,
        origin=ORIGIN,
        allowed_hostnames=ALLOWED,
        username="staging-user",
        password=PASSWORD,
        **TARGET,
    )


def _assert_no_secret(value: object) -> None:
    rendered = str(value)
    assert all(secret not in rendered for secret in SECRETS)


def test_closed_environment_allowlist_and_exact_staging_origin_are_required_before_login():
    assert _parse_allowed_hostnames('["staging.example"]') == ALLOWED
    for raw in ("", "[]", '"staging.example"', '["*.example"]', '["Staging.example"]'):
        with pytest.raises(ProbeError, match="STAGING_HOST_ALLOWLIST_INVALID"):
            _parse_allowed_hostnames(raw)

    class NoNetwork:
        def post(self, *_args, **_kwargs):
            raise AssertionError("login must not be attempted")

    for origin in (
        "https://retirev2.onrender.com",
        "https://arbitrary.example",
        "http://staging.example",
        "https://staging.example/path",
        "https://user:pass@staging.example",
    ):
        with pytest.raises(ProbeError, match="STAGING_ORIGIN_NOT_ALLOWED"):
            run_probe(
                NoNetwork(), origin=origin, allowed_hostnames=ALLOWED,
                username="u", password="p", **TARGET,
            )

    production = "retirev2.onrender.com"
    with pytest.raises(ProbeError, match="STAGING_ORIGIN_NOT_ALLOWED"):
        run_probe(
            NoNetwork(), origin=f"https://{production}", allowed_hostnames=frozenset({production}),
            username="u", password="p", **TARGET,
        )


def test_authoritative_environment_identity_must_bind_the_exact_allowlisted_host():
    railway = {
        "RETIRE_V2_STAGING_ALLOWED_HOSTNAMES": '["staging.example"]',
        "AUTH_PUBLIC_ORIGIN": ORIGIN,
        "RAILWAY_ENVIRONMENT_NAME": "staging",
    }
    assert _authorized_staging_hostnames(railway) == ALLOWED
    render = {
        "RETIRE_V2_STAGING_ALLOWED_HOSTNAMES": '["staging.example"]',
        "AUTH_PUBLIC_ORIGIN": ORIGIN,
        "STAGE6_APPROVED_RENDER_HOSTNAME": "staging.example",
        "RENDER_EXTERNAL_HOSTNAME": "staging.example",
    }
    assert _authorized_staging_hostnames(render) == ALLOWED
    for changed in (
        {**railway, "RAILWAY_ENVIRONMENT_NAME": "production"},
        {**railway, "AUTH_PUBLIC_ORIGIN": "https://other.example"},
        {**render, "RENDER_EXTERNAL_HOSTNAME": "other.example"},
        {},
    ):
        with pytest.raises(ProbeError, match="STAGING_"):
            _authorized_staging_hostnames(changed)


def test_complete_valid_http_200_contract_is_accepted_and_sanitized():
    observed: list[dict[str, object]] = []
    with _client(_response(200, _valid_permission_body()), observed) as client:
        evidence = _run(client)
    assert [row["path"] for row in observed] == [
        "/api/auth/login", "/api/auth/session",
        "/api/clients/7/scenario-conversions/permission-preview", "/api/auth/logout",
    ]
    assert evidence["authenticated_session"] is True
    assert evidence["http_status"] == 200
    assert evidence["overall_status"] == "mixed"
    assert len(evidence["permissions"]) == 11
    assert {row["permission_status"] for row in evidence["permissions"]} == {"allowed", "blocked"}
    _assert_no_secret(json.dumps(evidence))


def _drop_totals(body: dict[str, Any]) -> None:
    body.pop("totals")


def _extra_top_level(body: dict[str, Any]) -> None:
    body["unexpected"] = True


def _bad_source_fingerprint(body: dict[str, Any]) -> None:
    body["source_fingerprint"] = "not-a-fingerprint"


def _bad_ruleset(body: dict[str, Any]) -> None:
    body["ruleset_digest"] = "0" * 64


def _missing_component(body: dict[str, Any]) -> None:
    body["components"].pop()


def _silent_type_coercion(body: dict[str, Any]) -> None:
    body["components"][0]["balance"] = 1


def _bad_totals(body: dict[str, Any]) -> None:
    body["totals"]["allowed_balance"] = "999.00"


def _bad_reconciliation(body: dict[str, Any]) -> None:
    body["reconciliation"]["product_component_sum"] = "999.00"


def _extra_component_field(body: dict[str, Any]) -> None:
    body["components"][0]["unexpected"] = "value"


@pytest.mark.parametrize("mutate", [
    _drop_totals,
    _extra_top_level,
    _bad_source_fingerprint,
    _bad_ruleset,
    _missing_component,
    _silent_type_coercion,
    _bad_totals,
    _bad_reconciliation,
    _extra_component_field,
])
def test_missing_malformed_or_extra_http_200_contract_is_rejected(mutate):
    body = deepcopy(_valid_permission_body())
    mutate(body)
    observed: list[dict[str, object]] = []
    with _client(_response(200, body), observed) as client:
        with pytest.raises(ProbeError, match="PERMISSION_RESPONSE_") as error:
            _run(client)
    assert observed[-1]["path"] == "/api/auth/logout"
    _assert_no_secret(error.value)


def test_http_409_is_preserved_as_block_and_never_becomes_permission():
    observed: list[dict[str, object]] = []
    blocked = {
        "schema_version": "RTDIR_TRANSPORT_ERROR_V1",
        "code": "MISSING_CANONICAL_SOURCE",
        "message": "לא ניתן להשלים את הבקשה",
        "field_paths": ["/product_id"],
        "request_id": "request-1",
    }
    with _client(_response(409, blocked), observed) as client:
        evidence = _run(client)
    assert evidence["http_status"] == 409
    assert evidence["response_code"] == "MISSING_CANONICAL_SOURCE"
    assert evidence["overall_status"] is None
    assert evidence["permissions"] == []


def test_login_failure_is_sanitized_and_does_not_claim_a_session():
    observed: list[dict[str, object]] = []
    failed_login = _response(401, {"code": "AUTHENTICATION_FAILED"})
    with _client(_response(200, _valid_permission_body()), observed, login=failed_login) as client:
        with pytest.raises(ProbeError, match="LOGIN_REJECTED") as error:
            _run(client)
    assert [row["path"] for row in observed] == ["/api/auth/login"]
    _assert_no_secret(error.value)


def test_successful_http_login_with_missing_csrf_fails_closed_and_reports_logout_limit():
    observed: list[dict[str, object]] = []
    login_without_csrf = _response(200, {"authenticated": True})
    with _client(
        _response(200, _valid_permission_body()), observed, login=login_without_csrf,
    ) as client:
        with pytest.raises(ProbeError) as error:
            _run(client)
    assert "LOGIN_CSRF_INVALID" in str(error.value)
    assert "LOGOUT_NOT_ATTEMPTED_INVALID_LOGIN_CSRF" in str(error.value)
    assert [row["path"] for row in observed] == ["/api/auth/login"]
    _assert_no_secret(error.value)


def test_successful_login_then_session_failure_still_logs_out_with_login_csrf():
    observed: list[dict[str, object]] = []
    failed_session = _response(503, {"code": "SESSION_UNAVAILABLE"})
    with _client(_response(200, _valid_permission_body()), observed, session=failed_session) as client:
        with pytest.raises(ProbeError, match="SESSION_UNAVAILABLE") as error:
            _run(client)
    assert [row["path"] for row in observed] == [
        "/api/auth/login", "/api/auth/session", "/api/auth/logout",
    ]
    _assert_no_secret(error.value)


def test_missing_or_mismatched_session_csrf_fails_and_still_logs_out():
    mismatched = base64.urlsafe_b64encode(b"D" * 32).decode().rstrip("=")
    for session_body in ({"authenticated": True}, {"authenticated": True, "csrf_token": mismatched}):
        observed: list[dict[str, object]] = []
        with _client(
            _response(200, _valid_permission_body()), observed,
            session=_response(200, session_body),
        ) as client:
            with pytest.raises(ProbeError, match="SESSION_CSRF_INVALID") as error:
                _run(client)
        assert observed[-1]["path"] == "/api/auth/logout"
        _assert_no_secret(error.value)


@pytest.mark.parametrize("stage", ["login", "session", "permission"])
def test_network_failure_is_sanitized_and_post_login_failures_attempt_logout(stage: str):
    observed: list[dict[str, object]] = []
    kwargs: dict[str, Any] = {}
    permission = _response(200, _valid_permission_body())
    if stage == "login":
        kwargs["login"] = _network
    elif stage == "session":
        kwargs["session"] = _network
    else:
        permission = _network
    with _client(permission, observed, **kwargs) as client:
        with pytest.raises(ProbeError, match=f"{stage.upper()}_NETWORK_FAILURE") as error:
            _run(client)
    if stage == "login":
        assert [row["path"] for row in observed] == ["/api/auth/login"]
    else:
        assert observed[-1]["path"] == "/api/auth/logout"
    _assert_no_secret(error.value)


def test_logout_failure_is_reported_without_exposing_secrets():
    for logout in (_response(500, {"code": "INTERNAL_ERROR"}), _network):
        observed: list[dict[str, object]] = []
        with _client(_response(200, _valid_permission_body()), observed, logout=logout) as client:
            with pytest.raises(ProbeError, match="LOGOUT_") as error:
                _run(client)
        assert observed[-1]["path"] == "/api/auth/logout"
        _assert_no_secret(error.value)


def test_logout_failure_does_not_hide_the_original_session_failure():
    observed: list[dict[str, object]] = []
    with _client(
        _response(200, _valid_permission_body()),
        observed,
        session=_response(503, {"code": "SESSION_UNAVAILABLE"}),
        logout=_network,
    ) as client:
        with pytest.raises(ProbeError) as error:
            _run(client)
    message = str(error.value)
    assert "SESSION_UNAVAILABLE" in message
    assert "LOGOUT_NETWORK_FAILURE" in message
    _assert_no_secret(message)
