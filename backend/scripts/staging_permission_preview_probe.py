"""Authenticated, non-mutating Scenario Permission Preview probe for Staging.

The probe uses the canonical login, HttpOnly session cookie and CSRF flow. It
never prints or persists credentials, cookies or CSRF values. Its only network
target is the immutable Railway Staging deployment identity below. Operator
arguments and environment variables cannot authorize another hostname.

Example, from ``backend``::

    RETIRE_V2_STAGING_USERNAME=<approved-user> \
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
from app.services import scenario_permission_preview_service as preview_contract


DEFAULT_CLIENT_ID = 7
DEFAULT_PRODUCT_ID = "96edb78aaa734d0c845ae8f6ee36da50"
DEFAULT_ACTION = "pension"
DEFAULT_EFFECTIVE_DATE = "2026-12-15"

# Closed deployment authority. These values are the existing Railway Staging
# project, environment, application service and generated service domain. They
# are deliberately not configurable by command line or environment variables.
STAGING_PROJECT_ID = "7e49d0ff-a760-4a03-be57-4ee88a4b892c"
STAGING_ENVIRONMENT_ID = "025871e4-2c84-427b-b37c-1d5b2c7b4d3c"
STAGING_ENVIRONMENT_NAME = "staging"
STAGING_SERVICE_ID = "328ec58c-da05-48e7-b959-bd5d3cd2bba3"
STAGING_HOSTNAME = "retire-v2-app-staging.up.railway.app"
STAGING_ORIGIN = f"https://{STAGING_HOSTNAME}"

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
_SOURCE_COMPONENT_FIELDS = {
    "component_code", "component_id", "balance", "allowed_destinations",
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


def _authorized_staging_hostnames(environment: Mapping[str, str]) -> frozenset[str]:
    expected = {
        "RAILWAY_PROJECT_ID": STAGING_PROJECT_ID,
        "RAILWAY_ENVIRONMENT_ID": STAGING_ENVIRONMENT_ID,
        "RAILWAY_ENVIRONMENT_NAME": STAGING_ENVIRONMENT_NAME,
        "RAILWAY_SERVICE_ID": STAGING_SERVICE_ID,
        "APP_ENV": "production",
        "AUTH_INGRESS_MODE": "railway_public_edge",
        "AUTH_PUBLIC_ORIGIN": STAGING_ORIGIN,
    }
    if any(environment.get(name) != value for name, value in expected.items()):
        raise ProbeError("STAGING_AUTHORITY_CONFIGURATION_INVALID")
    return frozenset({STAGING_HOSTNAME})


def _validate_origin(origin: str) -> str:
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
        or parsed.hostname != STAGING_HOSTNAME
        or origin != STAGING_ORIGIN
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


def _validate_source_snapshot(
    source: dict[str, Any], *, client_id: int, product_id: str,
) -> tuple[str, dict[str, dict[str, str]], str]:
    required = {
        "client_id", "product_id", "version", "source_kind", "product_type",
        "conversion_components",
    }
    if not required <= set(source):
        raise ProbeError("SOURCE_SNAPSHOT_FIELDS_INVALID")
    if type(source["client_id"]) is not int or source["client_id"] != client_id:
        raise ProbeError("SOURCE_SNAPSHOT_IDENTITY_MISMATCH")
    if type(source["product_id"]) is not str or source["product_id"] != product_id:
        raise ProbeError("SOURCE_SNAPSHOT_IDENTITY_MISMATCH")
    if type(source["version"]) is not int or source["version"] < 1:
        raise ProbeError("SOURCE_SNAPSHOT_VERSION_INVALID")
    if type(source["source_kind"]) is not str or not _canonical_text(source["source_kind"]):
        raise ProbeError("SOURCE_SNAPSHOT_SOURCE_KIND_INVALID")
    if type(source["product_type"]) is not str or not _canonical_text(source["product_type"]):
        raise ProbeError("SOURCE_SNAPSHOT_PRODUCT_TYPE_INVALID")

    raw_components = source["conversion_components"]
    if type(raw_components) is not list or len(raw_components) != len(COMPONENT_CODES):
        raise ProbeError("SOURCE_SNAPSHOT_COMPONENT_MATRIX_INVALID")
    by_code: dict[str, dict[str, str]] = {}
    component_ids: set[str] = set()
    for raw_component in raw_components:
        component = _exact_fields(raw_component, _SOURCE_COMPONENT_FIELDS, "SOURCE_COMPONENT")
        code = component["component_code"]
        component_id = component["component_id"]
        if type(code) is not str or code not in COMPONENT_CODES or code in by_code:
            raise ProbeError("SOURCE_SNAPSHOT_COMPONENT_MATRIX_INVALID")
        if not _canonical_text(component_id) or component_id in component_ids:
            raise ProbeError("SOURCE_SNAPSHOT_COMPONENT_ID_INVALID")
        _decimal(component["balance"])
        if type(component["allowed_destinations"]) is not list:
            raise ProbeError("SOURCE_SNAPSHOT_COMPONENT_DESTINATIONS_INVALID")
        by_code[code] = {
            "component_code": code,
            "component_id": component_id,
            "balance": component["balance"],
        }
        component_ids.add(component_id)
    if set(by_code) != set(COMPONENT_CODES):
        raise ProbeError("SOURCE_SNAPSHOT_COMPONENT_MATRIX_INVALID")

    source_fingerprint = _sha256({
        "schema": "scenario-source-fingerprint-v1",
        "client_id": client_id,
        "product_id": product_id,
        "product_version": source["version"],
        "source_kind": source["source_kind"],
        "product_type": source["product_type"],
        "components": [by_code[code] for code in COMPONENT_CODES],
    })
    ruleset = preview_contract.permission_ruleset()
    product_classes = [
        mapping["canonical_product_class"]
        for mapping in ruleset["product_mappings"]
        if mapping["source_kind"] == source["source_kind"]
        and mapping["product_type"] == source["product_type"]
    ]
    if len(product_classes) != 1:
        raise ProbeError("SOURCE_SNAPSHOT_PRODUCT_CLASS_INVALID")
    return source_fingerprint, by_code, product_classes[0]


def _validate_permission_response(
    body: dict[str, Any], *, client_id: int, product_id: str,
    action: str, effective_date: str, source_snapshot: dict[str, Any],
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
    expected_source_fingerprint, source_by_code, expected_product_class = (
        _validate_source_snapshot(
            source_snapshot, client_id=client_id, product_id=product_id,
        )
    )
    if body["product_version"] != source_snapshot["version"]:
        raise ProbeError("PERMISSION_RESPONSE_PRODUCT_VERSION_MISMATCH")
    if (
        type(body["canonical_product_class"]) is not str
        or body["canonical_product_class"] != expected_product_class
    ):
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
    if body["source_fingerprint"] != expected_source_fingerprint:
        raise ProbeError("PERMISSION_RESPONSE_SOURCE_FINGERPRINT_INVALID")
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
    component_ids: set[str] = set()
    for position, component_code in enumerate(COMPONENT_CODES):
        component = _exact_fields(raw_components[position], _COMPONENT_FIELDS, "COMPONENT")
        if type(component["component_code"]) is not str or component["component_code"] != component_code:
            raise ProbeError("PERMISSION_RESPONSE_COMPONENT_MATRIX_INVALID")
        if (
            not _canonical_text(component["component_id"])
            or component["component_id"] in component_ids
        ):
            raise ProbeError("PERMISSION_RESPONSE_COMPONENT_ID_INVALID")
        balance = _decimal(component["balance"])
        source_component = source_by_code[component_code]
        if (
            component["component_id"] != source_component["component_id"]
            or component["balance"] != source_component["balance"]
        ):
            raise ProbeError("PERMISSION_RESPONSE_SOURCE_COMPONENT_MISMATCH")
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
            or component["reason_he"] != preview_contract._REASON_HE[decision["reason_code"]]
        ):
            raise ProbeError("PERMISSION_RESPONSE_COMPONENT_RULE_INVALID")
        component_ids.add(component["component_id"])
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
    reported_fields = {
        "rewards_discrepancy": ("reported_rewards_total", rewards),
        "severance_discrepancy": ("reported_severance_total", severance),
        "product_discrepancy": ("reported_product_total", rewards + severance),
    }
    expected_reconciliation: dict[str, Decimal | None] = dict(expected_sums)
    for discrepancy_field, (source_field, component_sum) in reported_fields.items():
        if source_field not in source_snapshot:
            raise ProbeError("SOURCE_SNAPSHOT_RECONCILIATION_INVALID")
        reported = source_snapshot[source_field]
        expected_reconciliation[discrepancy_field] = (
            None if reported is None else _decimal(reported) - component_sum
        )
    source_reconciliation = _exact_fields(
        source_snapshot.get("reconciliation"), _RECONCILIATION_FIELDS,
        "SOURCE_RECONCILIATION",
    )
    for field, expected in expected_reconciliation.items():
        for actual, label in (
            (source_reconciliation[field], "SOURCE_SNAPSHOT_RECONCILIATION_INVALID"),
            (reconciliation[field], "PERMISSION_RESPONSE_RECONCILIATION_INVALID"),
        ):
            if expected is None:
                if actual is not None:
                    raise ProbeError(label)
            elif actual is None or _decimal(actual, signed=field.endswith("_discrepancy")) != expected:
                raise ProbeError(label)
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
    username: str,
    password: str,
    client_id: int = DEFAULT_CLIENT_ID,
    product_id: str = DEFAULT_PRODUCT_ID,
    action: str = DEFAULT_ACTION,
    effective_date: str = DEFAULT_EFFECTIVE_DATE,
) -> dict[str, Any]:
    """Run one authenticated probe and return only sanitized evidence."""
    origin = _validate_origin(origin)
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
    cleanup_csrf: object = None
    login_issue: ProbeError | None = None
    primary: ProbeError | None = None
    logout_failure: ProbeError | None = None
    evidence: dict[str, Any] | None = None
    stage = "SESSION"
    try:
        try:
            login_body = _json_object(login, "LOGIN")
        except ProbeError as exc:
            login_issue = exc
            login_body = {}
        if login_issue is None and login_body.get("authenticated") is not True:
            login_issue = ProbeError("LOGIN_RESPONSE_INVALID")
        login_csrf = login_body.get("csrf_token")
        if _valid_csrf(login_csrf):
            cleanup_csrf = login_csrf
        elif login_issue is None:
            login_issue = ProbeError("LOGIN_CSRF_INVALID")

        # A HTTP 200 login can already have created a cookie session. Fetch the
        # canonical session even when the login CSRF is absent or malformed so
        # its valid CSRF can be used solely to revoke that session.
        session = client.get("/api/auth/session")
        session_body = _json_object(session, "SESSION")
        if session.status_code != 200 or session_body.get("authenticated") is not True:
            session_issue = ProbeError(
                f"SESSION_UNAVAILABLE (HTTP {session.status_code}, "
                f"code={_response_code(session_body) or 'unknown'})"
            )
            if login_issue is not None:
                raise ProbeError(f"{login_issue}; {session_issue}") from login_issue
            raise session_issue
        session_csrf = session_body.get("csrf_token")
        if _valid_csrf(session_csrf) and cleanup_csrf is None:
            cleanup_csrf = session_csrf
        if login_issue is not None:
            raise login_issue
        if not _valid_csrf(session_csrf) or session_csrf != login_csrf:
            raise ProbeError("SESSION_CSRF_INVALID")

        stage = "SOURCE"
        source_response = client.get(
            f"/api/clients/{client_id}/pension-products/{product_id}"
        )
        source_snapshot = _json_object(source_response, "PENSION_PRODUCT_SOURCE")
        if source_response.status_code != 200:
            raise ProbeError(
                f"SOURCE_SNAPSHOT_UNAVAILABLE (HTTP {source_response.status_code}, "
                f"code={_response_code(source_snapshot) or 'unknown'})"
            )
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
                source_snapshot=source_snapshot,
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
        network_issue = _network_failure(stage)
        primary = (
            ProbeError(f"{login_issue}; {network_issue}")
            if login_issue is not None else network_issue
        )
    finally:
        if _valid_csrf(cleanup_csrf):
            try:
                logout = client.post(
                    "/api/auth/logout",
                    headers={"origin": origin, "x-rtdir-csrf": cleanup_csrf},
                )
                if logout.status_code != 204:
                    logout_failure = ProbeError(f"LOGOUT_UNCONFIRMED (HTTP {logout.status_code})")
            except httpx.HTTPError:
                logout_failure = ProbeError("LOGOUT_NETWORK_FAILURE")
        else:
            logout_failure = ProbeError("LOGOUT_NOT_ATTEMPTED_NO_VALID_SESSION_CSRF")

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
    parser.add_argument("--origin", default=STAGING_ORIGIN)
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
        _authorized_staging_hostnames(os.environ)
        origin = _validate_origin(args.origin)
        with httpx.Client(
            base_url=origin,
            timeout=75,
            follow_redirects=False,
            headers={"user-agent": "retire-v2-permission-probe/2"},
        ) as client:
            evidence = run_probe(
                client,
                origin=origin,
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
