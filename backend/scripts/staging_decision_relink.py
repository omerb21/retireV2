"""One-shot authenticated relink of the fixed synthetic Stage 6 decision.

This operator tool is intentionally closed to one Railway Staging deployment
and one already-approved synthetic record set. It performs read-only
preflight checks, sends exactly one canonical scenario-draft PUT, validates
the response, and logs out. It never retries the PUT because a network failure
after transmission leaves the commit outcome unknown.

Run from ``backend`` only after independent review::

    RETIRE_V2_STAGING_USERNAME=<approved-user> \
    python scripts/staging_decision_relink.py --confirm-staging \
      --evidence-json decision-relink-evidence.json

The password is requested without echo unless an authorized ephemeral
execution environment supplies ``RETIRE_V2_STAGING_PASSWORD``.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation
import getpass
import json
import os
from pathlib import Path
from typing import Any, Mapping

import httpx

from staging_permission_preview_probe import (
    ProbeError,
    STAGING_ORIGIN,
    _authorized_staging_hostnames,
    _json_object,
    _response_code,
    _validate_origin,
    _valid_csrf,
)


CLIENT_ID = 7
SCENARIO_ID = "f0dc04e3159f41948cee51edc6176550"
DECISION_ID = "cf8eaf5ea71847d7bea496db8a113f34"
EXPECTED_VERSION = 4
SCENARIO_NAME = "E2E-359-ALT-A"

OLD_PRODUCT_ID = "b5b052e5ae7b47b0b1cf1fb539d575b4"
OLD_COMPONENT_ID = "3273b20755e24ebeb6d1ad13c2ed8340"
NEW_PRODUCT_ID = "96edb78aaa734d0c845ae8f6ee36da50"
NEW_COMPONENT_ID = "b5b926b9db554859ae0454e696d689a4"
COMPONENT_CODE = "תגמולי_עובד_אחרי_2000"
SOURCE_BALANCE = "100000.00"
AMOUNT = "70000.00"
ACTION = "pension"
EFFECTIVE_DATE = "2026-12-15"

SCENARIO_PATH = f"/api/clients/{CLIENT_ID}/scenario-drafts/{SCENARIO_ID}"
PRODUCT_PATH = f"/api/clients/{CLIENT_ID}/pension-products/{NEW_PRODUCT_ID}"


class RelinkError(RuntimeError):
    """Sanitized preflight, authentication, transport, or result failure."""


def _network(stage: str) -> RelinkError:
    return RelinkError(f"{stage}_NETWORK_FAILURE")


def _valid_component_snapshot(product: Mapping[str, Any]) -> None:
    if (
        type(product.get("client_id")) is not int
        or product["client_id"] != CLIENT_ID
        or type(product.get("product_id")) is not str
        or product["product_id"] != NEW_PRODUCT_ID
        or type(product.get("conversion_components")) is not list
    ):
        raise RelinkError("SOURCE_PRODUCT_IDENTITY_MISMATCH")
    matching = [
        row for row in product["conversion_components"]
        if type(row) is dict and row.get("component_id") == NEW_COMPONENT_ID
    ]
    if len(matching) != 1:
        raise RelinkError("SOURCE_COMPONENT_IDENTITY_MISMATCH")
    component = matching[0]
    if (
        component.get("component_code") != COMPONENT_CODE
        or component.get("balance") != SOURCE_BALANCE
    ):
        raise RelinkError("SOURCE_COMPONENT_CONTRACT_MISMATCH")
    try:
        balance = Decimal(component["balance"])
        amount = Decimal(AMOUNT)
    except (InvalidOperation, TypeError) as exc:
        raise RelinkError("SOURCE_COMPONENT_CONTRACT_MISMATCH") from exc
    if not balance.is_finite() or not amount.is_finite() or amount <= 0 or amount > balance:
        raise RelinkError("SOURCE_COMPONENT_AMOUNT_EXCEEDS_BALANCE")


def _validated_scenario(body: Mapping[str, Any]) -> dict[str, Any]:
    if (
        type(body.get("client_id")) is not int
        or body["client_id"] != CLIENT_ID
        or body.get("scenario_id") != SCENARIO_ID
        or body.get("name") != SCENARIO_NAME
        or body.get("status") != "draft"
        or type(body.get("version")) is not int
        or body["version"] != EXPECTED_VERSION
        or type(body.get("decisions")) is not list
        or len(body["decisions"]) != 1
    ):
        raise RelinkError("SCENARIO_PREFLIGHT_MISMATCH")
    decision = body["decisions"][0]
    if (
        type(decision) is not dict
        or decision.get("decision_id") != DECISION_ID
        or decision.get("source_product_id") != OLD_PRODUCT_ID
        or decision.get("source_component_id") != OLD_COMPONENT_ID
        or decision.get("component_code") != COMPONENT_CODE
        or decision.get("amount") != AMOUNT
        or decision.get("action") != ACTION
        or decision.get("effective_date") != EFFECTIVE_DATE
    ):
        raise RelinkError("DECISION_PREFLIGHT_MISMATCH")
    return dict(body)


def _write_payload(scenario: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "expected_version": EXPECTED_VERSION,
        "name": scenario["name"],
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


def _validate_success(body: Mapping[str, Any]) -> dict[str, Any]:
    if (
        body.get("scenario_id") != SCENARIO_ID
        or body.get("client_id") != CLIENT_ID
        or body.get("name") != SCENARIO_NAME
        or body.get("status") != "draft"
        or body.get("version") != EXPECTED_VERSION + 1
        or type(body.get("decisions")) is not list
        or len(body["decisions"]) != 1
    ):
        raise RelinkError("RELINK_RESPONSE_SCENARIO_MISMATCH")
    decision = body["decisions"][0]
    expected = {
        "decision_id": DECISION_ID,
        "source_product_id": NEW_PRODUCT_ID,
        "source_component_id": NEW_COMPONENT_ID,
        "component_code": COMPONENT_CODE,
        "amount": AMOUNT,
        "action": ACTION,
        "effective_date": EFFECTIVE_DATE,
    }
    if type(decision) is not dict or any(decision.get(key) != value for key, value in expected.items()):
        raise RelinkError("RELINK_RESPONSE_DECISION_MISMATCH")
    if decision.get("validation_state") != "unverified":
        raise RelinkError("RELINK_RESPONSE_VALIDATION_STATE_INVALID")
    return {
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
        "scenario_version_before": EXPECTED_VERSION,
        "scenario_version_after": EXPECTED_VERSION + 1,
        "decision_id_preserved": True,
        "put_attempts": 1,
        "commit_outcome": "confirmed",
    }


def _logout(client: Any, origin: str, csrf: object) -> RelinkError | None:
    if not _valid_csrf(csrf):
        return RelinkError("LOGOUT_NOT_ATTEMPTED_NO_VALID_SESSION_CSRF")
    try:
        response = client.post(
            "/api/auth/logout",
            headers={"origin": origin, "x-rtdir-csrf": csrf},
        )
    except httpx.HTTPError:
        return RelinkError("LOGOUT_NETWORK_FAILURE")
    if response.status_code not in {204, 401}:
        return RelinkError(f"LOGOUT_UNCONFIRMED (HTTP {response.status_code})")
    return None


def run_relink(client: Any, *, origin: str, username: str, password: str) -> dict[str, Any]:
    """Preflight, one PUT, strict validation, and best-effort session cleanup."""
    origin = _validate_origin(origin)
    try:
        login = client.post(
            "/api/auth/login",
            json={"username": username, "password": password},
            headers={"origin": origin},
        )
    except httpx.HTTPError as exc:
        raise _network("LOGIN") from exc
    if login.status_code != 200:
        body = _json_object(login, "LOGIN")
        raise RelinkError(
            f"LOGIN_REJECTED (HTTP {login.status_code}, code={_response_code(body) or 'unknown'})"
        )

    cleanup_csrf: object = None
    primary: RelinkError | None = None
    evidence: dict[str, Any] | None = None
    stage = "SESSION"
    try:
        login_issue: RelinkError | None = None
        try:
            login_body = _json_object(login, "LOGIN")
        except ProbeError as exc:
            login_issue = RelinkError(str(exc))
            login_body = {}
        if login_issue is None and login_body.get("authenticated") is not True:
            login_issue = RelinkError("LOGIN_RESPONSE_INVALID")
        login_csrf = login_body.get("csrf_token")
        if _valid_csrf(login_csrf):
            cleanup_csrf = login_csrf
        elif login_issue is None:
            login_issue = RelinkError("LOGIN_CSRF_INVALID")

        # A successful login may already have created an HttpOnly session even
        # when its response is malformed. Read the canonical session so a valid
        # CSRF can still be used exclusively for mandatory logout.
        session = client.get("/api/auth/session")
        session_body = _json_object(session, "SESSION")
        session_csrf = session_body.get("csrf_token")
        if session.status_code != 200 or session_body.get("authenticated") is not True:
            raise RelinkError(
                f"SESSION_UNAVAILABLE (HTTP {session.status_code}, "
                f"code={_response_code(session_body) or 'unknown'})"
            )
        if _valid_csrf(session_csrf) and cleanup_csrf is None:
            cleanup_csrf = session_csrf
        if login_issue is not None:
            raise login_issue
        if not _valid_csrf(session_csrf) or session_csrf != login_csrf:
            raise RelinkError("SESSION_CSRF_INVALID")

        stage = "SCENARIO_PREFLIGHT"
        scenario_response = client.get(SCENARIO_PATH)
        scenario_body = _json_object(scenario_response, "SCENARIO_PREFLIGHT")
        if scenario_response.status_code != 200:
            raise RelinkError(
                f"SCENARIO_PREFLIGHT_FAILED (HTTP {scenario_response.status_code}, "
                f"code={_response_code(scenario_body) or 'unknown'})"
            )
        scenario = _validated_scenario(scenario_body)

        stage = "SOURCE_PREFLIGHT"
        product_response = client.get(PRODUCT_PATH)
        product_body = _json_object(product_response, "SOURCE_PREFLIGHT")
        if product_response.status_code != 200:
            raise RelinkError(
                f"SOURCE_PREFLIGHT_FAILED (HTTP {product_response.status_code}, "
                f"code={_response_code(product_body) or 'unknown'})"
            )
        _valid_component_snapshot(product_body)

        stage = "RELINK_PUT"
        response = client.put(
            SCENARIO_PATH,
            json=_write_payload(scenario),
            headers={"origin": origin, "x-rtdir-csrf": login_csrf},
        )
        body = _json_object(response, "RELINK_PUT")
        if response.status_code == 200:
            evidence = _validate_success(body)
        elif response.status_code == 409:
            code = _response_code(body) or "unknown"
            evidence = {
                "schema_version": "STAGING_DECISION_RELINK_EVIDENCE_V1",
                "target": {
                    "client_id": CLIENT_ID,
                    "scenario_id": SCENARIO_ID,
                    "decision_id": DECISION_ID,
                    "source_product_id": NEW_PRODUCT_ID,
                    "source_component_id": NEW_COMPONENT_ID,
                },
                "http_status": 409,
                "response_code": code,
                "scenario_version_before": EXPECTED_VERSION,
                "scenario_version_after": None,
                "decision_id_preserved": None,
                "put_attempts": 1,
                "commit_outcome": "rejected",
            }
        else:
            raise RelinkError(
                f"RELINK_REJECTED (HTTP {response.status_code}, "
                f"code={_response_code(body) or 'unknown'})"
            )
    except ProbeError as exc:
        primary = RelinkError(str(exc))
    except RelinkError as exc:
        primary = exc
    except httpx.HTTPError as exc:
        primary = _network(stage)
    finally:
        logout_failure = _logout(client, origin, cleanup_csrf)

    if primary is not None:
        if logout_failure is not None:
            raise RelinkError(f"{primary}; {logout_failure}") from primary
        raise primary
    if logout_failure is not None:
        raise logout_failure
    if evidence is None:
        raise RelinkError("RELINK_RESULT_MISSING")
    return evidence


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-staging", action="store_true")
    parser.add_argument("--origin", default=STAGING_ORIGIN)
    parser.add_argument("--username", default=os.getenv("RETIRE_V2_STAGING_USERNAME", ""))
    parser.add_argument("--evidence-json", type=Path)
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    if not args.confirm_staging:
        print("BLOCKED: --confirm-staging is required")
        return 2
    password = os.getenv("RETIRE_V2_STAGING_PASSWORD") or getpass.getpass(
        "Staging password (hidden): "
    )
    if not args.username or not password:
        print("BLOCKED: staging username and password are required")
        return 2
    try:
        _authorized_staging_hostnames(os.environ)
        origin = _validate_origin(args.origin)
        with httpx.Client(
            base_url=origin,
            timeout=75,
            follow_redirects=False,
            headers={"user-agent": "retire-v2-decision-relink/1"},
        ) as client:
            evidence = run_relink(
                client, origin=origin, username=args.username, password=password,
            )
        serialized = json.dumps(evidence, ensure_ascii=False, sort_keys=True, indent=2)
        if args.evidence_json:
            args.evidence_json.write_text(serialized + "\n", encoding="utf-8")
        print(serialized)
        return 0 if evidence["http_status"] == 200 else 3
    except (httpx.HTTPError, ProbeError, RelinkError) as exc:
        print("DECISION_RELINK_FAILED: " + str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
