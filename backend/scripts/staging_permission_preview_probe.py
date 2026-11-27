"""Authenticated, non-mutating Scenario Permission Preview probe for Staging.

The probe uses the canonical login, HttpOnly session cookie and CSRF flow. It
never prints or persists credentials, cookies or CSRF values. The operational
Staging hostname must be supplied by deployment authority in the closed JSON
allowlist ``RETIRE_V2_STAGING_ALLOWED_HOSTNAMES``. An absent, malformed or
non-matching allowlist fails before login.

Example, from ``backend``::

    RETIRE_V2_STAGING_ALLOWED_HOSTNAMES='["<approved-hostname>"]' \
    RETIRE_V2_STAGING_ORIGIN=https://<approved-hostname> \
    RETIRE_V2_STAGING_USERNAME=<approved-user> \
    AUTH_PUBLIC_ORIGIN=https://<approved-hostname> \
    RAILWAY_ENVIRONMENT_NAME=staging \
    python scripts/staging_permission_preview_probe.py --confirm-staging \
      --evidence-json permission-preview-evidence.json

The password is requested without echo unless RETIRE_V2_STAGING_PASSWORD is
provided by an authorized ephemeral execution environment.
"""
from __future__ import annotations

import argparse
import base64
from datetime import date
from decimal import Decimal, InvalidOperation
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Mapping
from urllib.parse import urlsplit

import httpx

from app.models.pension_product import COMPONENT_CODES, REWARDS_CODES, SEVERANCE_CODES
from app.main import ACTIVE_RENDER_SERVICE_HOSTNAME
from app.services import scenario_permission_preview_service as preview_contract


DEFAULT_CLIENT_ID = 7
DEFAULT_PRODUCT_ID = "96edb78aaa734d0c845ae8f6ee36da50"
DEFAULT_ACTION = "pension"
DEFAULT_EFFECTIVE_DATE = "2026-12-15"

_HOSTNAME = re.compile(
    r"(?=.{1,253}\Z)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)*"
    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z"
)
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_MONEY = re.compile(r"(?:0|[1-9][0-9]*)\.[0-9]{2}\Z")
_SIGNED_MONEY = re.compile(r"-?(?:0|[1-9][0-9]*)\.[0-9]{2}\Z")
_TOP_LEVEL_FIELDS = {
    "schema_version", "preview_id", "client_id", "product_id", "product_version",
    "canonical_product_class", "action", "effective_date", "ruleset_id",
    "ruleset_version", "ruleset_digest", "source_fingerprint", "overall_status",
    "professional_eligibility_status", "tax_status", "components", "totals",
    "reconciliation",
}
_COMPONENT_FIELDS = {
    "component_code", "component_id", "balance", "permission_status",
    "reason_code", "reason_he", "applicable_rule_id",
}
_TOTAL_FIELDS = {
    "original_classified_balance", "allowed_balance", "blocked_balance",
    "needs_source_reconciliation_balance", "unknown_balance",
}
_RECONCILIATION_FIELDS = {
    "rewards_component_sum", "severance_component_sum", "product_component_sum",
    "rewards_discrepancy", "severance_discrepancy", "product_discrepancy",
}
_PERMISSION_STATUSES = {"allowed", "blocked", "needs_source_reconciliation", "unknown"}
_OVERALL_STATUSES = _PERMISSION_STATUSES | {"mixed"}


class ProbeError(RuntimeError):
    """A sanitized technical or authentication failure."""


def _json_object(response: httpx.Response, label: str) -> dict[str, Any]:
    try:
        body = response.json()
    except ValueError as exc:
        raise ProbeError(f"{label}: NON_JSON_RESPONSE (HTTP {response.status_code})") from exc
    if type(body) is not dict:
        raise ProbeError(f"{label}: INVALID_JSON_SHAPE (HTTP {response.status_code})")
    return body


def _response_code(body: Mapping[str, Any]) -> str | None:
    code = body.get("code")
    return code if type(code) is str and code else None


def _parse_allowed_hostnames(raw: str) -> frozenset[str]:
    try:
        values = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ProbeError("STAGING_HOST_ALLOWLIST_INVALID") from exc
    if type(values) is not list or not values:
        raise ProbeError("STAGING_HOST_ALLOWLIST_INVALID")
    if any(type(value) is not str or not _HOSTNAME.fullmatch(value) for value in values):
        raise ProbeError("STAGING_HOST_ALLOWLIST_INVALID")
    allowed = frozenset(values)
    if len(allowed) != len(values):
        raise ProbeError("STAGING_HOST_ALLOWLIST_INVALID")
    return allowed


def _authorized_staging_hostnames(environment: Mapping[str, str]) -> frozenset[str]:
    allowed = _parse_allowed_hostnames(
        environment.get("RETIRE_V2_STAGING_ALLOWED_HOSTNAMES", "")
    )
    public_origin = environment.get("AUTH_PUBLIC_ORIGIN", "")
    parsed = urlsplit(public_origin)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.netloc != parsed.hostname
        or parsed.path
        or parsed.query
        or parsed.fragment
        or parsed.hostname not in allowed
        or parsed.hostname == ACTIVE_RENDER_SERVICE_HOSTNAME
    ):
        raise ProbeError("STAGING_AUTHORITY_CONFIGURATION_INVALID")
    railway_staging = environment.get("RAILWAY_ENVIRONMENT_NAME") == "staging"
    render_staging = (
        environment.get("STAGE6_APPROVED_RENDER_HOSTNAME") == parsed.hostname
        and environment.get("RENDER_EXTERNAL_HOSTNAME") == parsed.hostname
    )
    if not (railway_staging or render_staging):
        raise ProbeError("STAGING_AUTHORITY_CONFIGURATION_INVALID")
    return allowed


def _validate_origin(origin: str, allowed_hostnames: frozenset[str]) -> str:
    if not allowed_hostnames:
        raise ProbeError("STAGING_HOST_ALLOWLIST_INVALID")
    parsed = urlsplit(origin)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port is not None
        or parsed.netloc != parsed.hostname
        or parsed.path
        or parsed.query
        or parsed.fragment
        or parsed.hostname not in allowed_hostnames
        or parsed.hostname == ACTIVE_RENDER_SERVICE_HOSTNAME
    ):
        raise ProbeError("STAGING_ORIGIN_NOT_ALLOWED")
    return origin


def _valid_csrf(value: object) -> bool:
    if type(value) is not str or len(value) != 43 or "=" in value:
        return False
    try:
        decoded = base64.urlsafe_b64decode(value + "=")
    except Exception:
        return False
    return len(decoded) == 32 and base64.urlsafe_b64encode(decoded).decode().rstrip("=") == value


def _canonical_text(value: object) -> bool:
    return (
        type(value) is str
        and bool(value)
        and value == value.strip(" \t\r\n")
        and not any(ord(character) < 32 for character in value)
    )


def _decimal(value: object, *, signed: bool = False) -> Decimal:
    pattern = _SIGNED_MONEY if signed else _MONEY
    if type(value) is not str or not pattern.fullmatch(value):
        raise ProbeError("PERMISSION_RESPONSE_INVALID_MONEY")
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise ProbeError("PERMISSION_RESPONSE_INVALID_MONEY") from exc
    if not result.is_finite() or (not signed and result < 0):
        raise ProbeError("PERMISSION_RESPONSE_INVALID_MONEY")
    return result


def _exact_fields(value: object, expected: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != expected:
        raise ProbeError(f"PERMISSION_RESPONSE_INVALID_{label}_FIELDS")
    return value


def _expected_overall(statuses: set[str]) -> str:
    if "needs_source_reconciliation" in statuses:
        return "needs_source_reconciliation"
    if "unknown" in statuses:
        return "unknown"
    if {"allowed", "blocked"} <= statuses:
        return "mixed"
    if "allowed" in statuses:
        return "allowed"
    return "blocked"


def _sha256(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        preview_contract.canonical_json(value).encode("utf-8")
    ).hexdigest()


def _validate_permission_response(
    body: dict[str, Any], *, client_id: int, product_id: str,
    action: str, effective_date: str,
) -> list[dict[str, str]]:
    _exact_fields(body, _TOP_LEVEL_FIELDS, "TOP_LEVEL")
    if body["schema_version"] != "SCENARIO_PERMISSION_PREVIEW_V1":
        raise ProbeError("PERMISSION_RESPONSE_SCHEMA_MISMATCH")
    if type(body["client_id"]) is not int or body["client_id"] != client_id:
        raise ProbeError("PERMISSION_RESPONSE_IDENTITY_MISMATCH")
    if type(body["product_id"]) is not str or body["product_id"] != product_id:
        raise ProbeError("PERMISSION_RESPONSE_IDENTITY_MISMATCH")
    if type(body["product_version"]) is not int or body["product_version"] < 1:
        raise ProbeError("PERMISSION_RESPONSE_PRODUCT_VERSION_INVALID")
    if type(body["action"]) is not str or body["action"] != action:
        raise ProbeError("PERMISSION_RESPONSE_IDENTITY_MISMATCH")
    try:
        parsed_date = date.fromisoformat(body["effective_date"])
    except (TypeError, ValueError) as exc:
        raise ProbeError("PERMISSION_RESPONSE_EFFECTIVE_DATE_INVALID") from exc
    if parsed_date.isoformat() != body["effective_date"] or body["effective_date"] != effective_date:
        raise ProbeError("PERMISSION_RESPONSE_IDENTITY_MISMATCH")

    ruleset = preview_contract.permission_ruleset()
    product_classes = {
        mapping["canonical_product_class"] for mapping in ruleset["product_mappings"]
    }
    if type(body["canonical_product_class"]) is not str or body["canonical_product_class"] not in product_classes:
        raise ProbeError("PERMISSION_RESPONSE_PRODUCT_CLASS_INVALID")
    if (
        type(body["ruleset_id"]) is not str
        or body["ruleset_id"] != ruleset["ruleset_id"]
        or type(body["ruleset_version"]) is not int
        or body["ruleset_version"] != ruleset["ruleset_version"]
        or type(body["ruleset_digest"]) is not str
        or body["ruleset_digest"] != preview_contract.ruleset_digest()
    ):
        raise ProbeError("PERMISSION_RESPONSE_RULESET_INVALID")
    for field in ("preview_id", "source_fingerprint"):
        if type(body[field]) is not str or not _HEX64.fullmatch(body[field]):
            raise ProbeError("PERMISSION_RESPONSE_FINGERPRINT_INVALID")
    expected_preview_id = _sha256({
        "schema": "scenario-permission-preview-id-v1",
        "client_id": client_id,
        "product_id": product_id,
        "source_fingerprint": body["source_fingerprint"],
        "action": action,
        "effective_date": effective_date,
        "ruleset_id": ruleset["ruleset_id"],
        "ruleset_version": ruleset["ruleset_version"],
        "ruleset_digest": preview_contract.ruleset_digest(),
    })
    if body["preview_id"] != expected_preview_id:
        raise ProbeError("PERMISSION_RESPONSE_PREVIEW_FINGERPRINT_INVALID")
    if body["professional_eligibility_status"] != "not_evaluated" or body["tax_status"] != "not_evaluated":
        raise ProbeError("PERMISSION_RESPONSE_AUTHORITY_STATUS_INVALID")

    raw_components = body["components"]
    if type(raw_components) is not list or len(raw_components) != len(COMPONENT_CODES):
        raise ProbeError("PERMISSION_RESPONSE_COMPONENT_MATRIX_INVALID")
    rules_by_code = {row["component_code"]: row for row in ruleset["component_rules"]}
    balances: dict[str, Decimal] = {}
    status_totals = {status: Decimal("0.00") for status in _PERMISSION_STATUSES}
    evidence_rows: list[dict[str, str]] = []
    for position, component_code in enumerate(COMPONENT_CODES):
        component = _exact_fields(raw_components[position], _COMPONENT_FIELDS, "COMPONENT")
        if type(component["component_code"]) is not str or component["component_code"] != component_code:
            raise ProbeError("PERMISSION_RESPONSE_COMPONENT_MATRIX_INVALID")
        if not _canonical_text(component["component_id"]):
            raise ProbeError("PERMISSION_RESPONSE_COMPONENT_ID_INVALID")
        balance = _decimal(component["balance"])
        rule = rules_by_code[component_code]
        decision = rule["actions"][action]
        if body["canonical_product_class"] not in rule["applicable_product_classes"]:
            raise ProbeError("PERMISSION_RESPONSE_PRODUCT_CLASS_INVALID")
        if (
            type(component["permission_status"]) is not str
            or component["permission_status"] not in _PERMISSION_STATUSES
            or component["permission_status"] != decision["permission_status"]
            or type(component["reason_code"]) is not str
            or component["reason_code"] != decision["reason_code"]
            or type(component["applicable_rule_id"]) is not str
            or component["applicable_rule_id"] != rule["rule_id"]
            or not _canonical_text(component["reason_he"])
        ):
            raise ProbeError("PERMISSION_RESPONSE_COMPONENT_RULE_INVALID")
        balances[component_code] = balance
        status_totals[component["permission_status"]] += balance
        evidence_rows.append({
            "component_code": component["component_code"],
            "permission_status": component["permission_status"],
            "reason_code": component["reason_code"],
            "reason_he": component["reason_he"],
        })

    statuses = {row["permission_status"] for row in evidence_rows}
    if type(body["overall_status"]) is not str or body["overall_status"] not in _OVERALL_STATUSES:
        raise ProbeError("PERMISSION_RESPONSE_OVERALL_STATUS_INVALID")
    if body["overall_status"] != _expected_overall(statuses):
        raise ProbeError("PERMISSION_RESPONSE_OVERALL_STATUS_INVALID")

    totals = _exact_fields(body["totals"], _TOTAL_FIELDS, "TOTALS")
    expected_totals = {
        "original_classified_balance": sum(balances.values(), Decimal("0.00")),
        "allowed_balance": status_totals["allowed"],
        "blocked_balance": status_totals["blocked"],
        "needs_source_reconciliation_balance": status_totals["needs_source_reconciliation"],
        "unknown_balance": status_totals["unknown"],
    }
    if any(_decimal(totals[key]) != value for key, value in expected_totals.items()):
        raise ProbeError("PERMISSION_RESPONSE_TOTALS_INVALID")

    reconciliation = _exact_fields(body["reconciliation"], _RECONCILIATION_FIELDS, "RECONCILIATION")
    rewards = sum((balances[code] for code in REWARDS_CODES), Decimal("0.00"))
    severance = sum((balances[code] for code in SEVERANCE_CODES), Decimal("0.00"))
    expected_sums = {
        "rewards_component_sum": rewards,
        "severance_component_sum": severance,
        "product_component_sum": rewards + severance,
    }
    if any(_decimal(reconciliation[key]) != value for key, value in expected_sums.items()):
        raise ProbeError("PERMISSION_RESPONSE_RECONCILIATION_INVALID")
    for key in ("rewards_discrepancy", "severance_discrepancy", "product_discrepancy"):
        if reconciliation[key] is not None:
            _decimal(reconciliation[key], signed=True)
    return evidence_rows


def _domain_error_evidence(body: dict[str, Any]) -> tuple[str | None, list[str]]:
    code = _response_code(body)
    field_paths = body.get("field_paths")
    if type(field_paths) is not list or any(type(path) is not str for path in field_paths):
        field_paths = []
    return code, field_paths


def _network_failure(stage: str) -> ProbeError:
    return ProbeError(f"{stage}_NETWORK_FAILURE")


def run_probe(
    client: Any,
    *,
    origin: str,
    allowed_hostnames: frozenset[str],
    username: str,
    password: str,
    client_id: int = DEFAULT_CLIENT_ID,
    product_id: str = DEFAULT_PRODUCT_ID,
    action: str = DEFAULT_ACTION,
    effective_date: str = DEFAULT_EFFECTIVE_DATE,
) -> dict[str, Any]:
    """Run one authenticated probe and return only sanitized evidence."""
    origin = _validate_origin(origin, allowed_hostnames)
    try:
        login = client.post(
            "/api/auth/login",
            json={"username": username, "password": password},
            headers={"origin": origin},
        )
    except httpx.HTTPError as exc:
        raise _network_failure("LOGIN") from exc
    if login.status_code != 200:
        login_body = _json_object(login, "LOGIN")
        raise ProbeError(
            f"LOGIN_REJECTED (HTTP {login.status_code}, code={_response_code(login_body) or 'unknown'})"
        )

    login_csrf: object = None
    primary: ProbeError | None = None
    logout_failure: ProbeError | None = None
    evidence: dict[str, Any] | None = None
    stage = "SESSION"
    try:
        login_body = _json_object(login, "LOGIN")
        if login_body.get("authenticated") is not True:
            raise ProbeError("LOGIN_RESPONSE_INVALID")
        login_csrf = login_body.get("csrf_token")
        if not _valid_csrf(login_csrf):
            raise ProbeError("LOGIN_CSRF_INVALID")
        session = client.get("/api/auth/session")
        session_body = _json_object(session, "SESSION")
        if session.status_code != 200 or session_body.get("authenticated") is not True:
            raise ProbeError(
                f"SESSION_UNAVAILABLE (HTTP {session.status_code}, "
                f"code={_response_code(session_body) or 'unknown'})"
            )
        session_csrf = session_body.get("csrf_token")
        if not _valid_csrf(session_csrf) or session_csrf != login_csrf:
            raise ProbeError("SESSION_CSRF_INVALID")
        stage = "PERMISSION"
        response = client.post(
            f"/api/clients/{client_id}/scenario-conversions/permission-preview",
            json={
                "product_id": product_id,
                "action": action,
                "effective_date": effective_date,
            },
            headers={"origin": origin, "x-rtdir-csrf": login_csrf},
        )
        body = _json_object(response, "PERMISSION_PREVIEW")
        if response.status_code in {401, 403} or response.status_code >= 500:
            raise ProbeError(
                f"PERMISSION_PREVIEW_TECHNICAL_FAILURE (HTTP {response.status_code}, "
                f"code={_response_code(body) or 'unknown'})"
            )
        permission_rows: list[dict[str, str]] = []
        if response.status_code == 200:
            permission_rows = _validate_permission_response(
                body,
                client_id=client_id,
                product_id=product_id,
                action=action,
                effective_date=effective_date,
            )
            response_code, field_paths = None, []
        else:
            response_code, field_paths = _domain_error_evidence(body)
        evidence = {
            "schema_version": "STAGING_PERMISSION_PREVIEW_PROBE_EVIDENCE_V1",
            "target": {
                "client_id": client_id,
                "product_id": product_id,
                "action": action,
                "effective_date": effective_date,
            },
            "authenticated_session": True,
            "http_status": response.status_code,
            "response_code": response_code,
            "overall_status": body["overall_status"] if response.status_code == 200 else None,
            "permissions": permission_rows,
            "field_paths": field_paths,
        }
    except ProbeError as exc:
        primary = exc
    except httpx.HTTPError as exc:
        primary = _network_failure(stage)
    finally:
        if _valid_csrf(login_csrf):
            try:
                logout = client.post(
                    "/api/auth/logout",
                    headers={"origin": origin, "x-rtdir-csrf": login_csrf},
                )
                if logout.status_code not in {204, 401}:
                    logout_failure = ProbeError(f"LOGOUT_UNCONFIRMED (HTTP {logout.status_code})")
            except httpx.HTTPError:
                logout_failure = ProbeError("LOGOUT_NETWORK_FAILURE")
        else:
            logout_failure = ProbeError("LOGOUT_NOT_ATTEMPTED_INVALID_LOGIN_CSRF")

    if primary is not None:
        if logout_failure is not None:
            raise ProbeError(f"{primary}; {logout_failure}") from primary
        raise primary
    if logout_failure is not None:
        raise logout_failure
    if evidence is None:
        raise ProbeError("PERMISSION_PREVIEW_RESULT_MISSING")
    return evidence


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-staging", action="store_true")
    parser.add_argument("--origin", default=os.getenv("RETIRE_V2_STAGING_ORIGIN", ""))
    parser.add_argument("--username", default=os.getenv("RETIRE_V2_STAGING_USERNAME", ""))
    parser.add_argument("--client-id", type=int, default=DEFAULT_CLIENT_ID)
    parser.add_argument("--product-id", default=DEFAULT_PRODUCT_ID)
    parser.add_argument("--action", choices=("pension", "capital_asset"), default=DEFAULT_ACTION)
    parser.add_argument("--effective-date", default=DEFAULT_EFFECTIVE_DATE)
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
        allowed_hostnames = _authorized_staging_hostnames(os.environ)
        origin = _validate_origin(args.origin, allowed_hostnames)
        with httpx.Client(
            base_url=origin,
            timeout=75,
            follow_redirects=False,
            headers={"user-agent": "retire-v2-permission-probe/2"},
        ) as client:
            evidence = run_probe(
                client,
                origin=origin,
                allowed_hostnames=allowed_hostnames,
                username=args.username,
                password=password,
                client_id=args.client_id,
                product_id=args.product_id,
                action=args.action,
                effective_date=args.effective_date,
            )
        serialized = json.dumps(evidence, ensure_ascii=False, sort_keys=True, indent=2)
        if args.evidence_json:
            args.evidence_json.write_text(serialized + "\n", encoding="utf-8")
        print(serialized)
        return 0
    except (httpx.HTTPError, ProbeError) as exc:
        print("PERMISSION_PREVIEW_PROBE_FAILED: " + str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
