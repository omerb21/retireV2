"""Complete the approved synthetic Case 7 Stage 6 fixture in Staging.

This is a one-shot operator tool.  It is closed to the existing Railway
Staging deployment and the exact synthetic identities approved in instruction
387.  It uses only canonical HTTP routes, signed session/CSRF, and server-side
CAS.  It never retries a write and never logs credentials, cookies, or CSRF.

The tool MUST NOT be executed before independent code review::

    RETIRE_V2_STAGING_USERNAME=<approved-user> \
    python scripts/staging_e2e_fixture_completion.py \
      --confirm-approved-fixture --evidence-json fixture-387-evidence.json
"""
from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation
import getpass
import json
import os
from pathlib import Path
import re
from typing import Any, Mapping
from urllib.parse import quote

import httpx

from app.services.scenario_stage6_single_pension_estimate_service import (
    _valid_sealed_result,
)
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
PRODUCT_ID = "96edb78aaa734d0c845ae8f6ee36da50"
COMPONENT_ID = "b5b926b9db554859ae0454e696d689a4"
COMPONENT_CODE = "תגמולי_עובד_אחרי_2000"
SCENARIO_NAME = "E2E-359-ALT-A"
INITIAL_SCENARIO_VERSION = 5
AMOUNT = "70000.00"
SOURCE_BALANCE = "100000.00"
EFFECTIVE_DATE = "2026-12-15"

BIRTH_DATE = "1959-12-15"
GENDER = "male"
PLANNING_BASE_DATE = "2026-11-26"
RETIREMENT_TARGET_DATE = "2026-12-15"
PENSION_START_DATE = "2026-12-15"
TARGET_YEAR = 2026
SURVIVORS_OPTION = "תקנוני"
SPOUSE_AGE_DIFF = 0
COEFFICIENT_SELECTION = "manual_review_required"
SYNTHETIC_COMPANY_NAME = "SYNTHETIC-E2E-STAGING-ONLY"
SYNTHETIC_OPTION_NAME = "SYNTHETIC-MANUAL-DIVISOR-200"
FACTOR_VALUE = "200"
FACTOR_EVIDENCE_TYPE = "PLANNER_ASSUMPTION"
FACTOR_EVIDENCE_REFERENCE = (
    "SYNTHETIC-E2E-STAGING-CASE7-FACTOR200-PLANNER-ASSUMPTION"
)

CLIENT_PATH = f"/api/clients/{CLIENT_ID}"
CASE_PATH = f"{CLIENT_PATH}/case"
PROFILE_PATH = f"{CLIENT_PATH}/profile"
PLANNING_PATH = f"{CLIENT_PATH}/retirement-planning-input"
SCENARIO_PATH = f"{CLIENT_PATH}/scenario-drafts/{SCENARIO_ID}"
ELECTIONS_PATH = f"{SCENARIO_PATH}/pension-elections"
FACTOR_PATH = f"{SCENARIO_PATH}/pension-decisions/{DECISION_ID}/factor-admissions"
FACTOR_CURSOR_PATH = f"{FACTOR_PATH}/revision"
GROSS_PATH = f"{SCENARIO_PATH}/pension-decisions/{DECISION_ID}/gross-estimate"
PRODUCT_PATH = f"{CLIENT_PATH}/pension-products/{PRODUCT_ID}"
TARGET_PATH = f"{CLIENT_PATH}/retirement-income-readiness/target"
TARGET_MONTH = RETIREMENT_TARGET_DATE[:7]
CASHFLOW_PATH = (
    f"{SCENARIO_PATH}/monthly-income-cashflow"
    f"?start_month={TARGET_MONTH}&end_month={TARGET_MONTH}"
)
PRICE_BASIS_PATH = f"{SCENARIO_PATH}/pension-decisions/{DECISION_ID}/price-basis"
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_MONEY = re.compile(r"(?:0|[1-9][0-9]*)\.[0-9]{2}\Z")


class FixtureCompletionError(RuntimeError):
    """Sanitized preflight, write, validation, or cleanup failure."""

    def __init__(
        self,
        message: str,
        *,
        evidence: Mapping[str, Any] | None = None,
        cleanup_error: str | None = None,
    ) -> None:
        super().__init__(message)
        self.evidence = dict(evidence) if evidence is not None else None
        self.cleanup_error = cleanup_error


def _is_hash(value: object) -> bool:
    return type(value) is str and _HEX64.fullmatch(value) is not None


def _network(stage: str, *, write: bool = False) -> FixtureCompletionError:
    suffix = "_COMMIT_OUTCOME_UNKNOWN" if write else "_NETWORK_FAILURE"
    return FixtureCompletionError(stage + suffix)


def _error_code(body: Mapping[str, Any]) -> str:
    direct = _response_code(body)
    if direct:
        return direct
    detail = body.get("detail")
    if type(detail) is dict and type(detail.get("code")) is str:
        return detail["code"]
    return "unknown"


def _read(client: Any, path: str, stage: str) -> dict[str, Any]:
    try:
        response = client.get(path)
    except httpx.HTTPError as exc:
        raise _network(stage) from exc
    body = _json_object(response, stage)
    if response.status_code != 200:
        raise FixtureCompletionError(
            f"{stage}_REJECTED (HTTP {response.status_code}, code={_error_code(body)})"
        )
    return body


def _write(
    client: Any,
    method: str,
    path: str,
    stage: str,
    body: Mapping[str, Any],
    *,
    origin: str,
    csrf: str,
) -> dict[str, Any]:
    """Send exactly one mutation attempt.  Transport failure is always unknown."""
    try:
        response = client.request(
            method,
            path,
            json=dict(body),
            headers={"origin": origin, "x-rtdir-csrf": csrf},
        )
    except httpx.HTTPError as exc:
        raise _network(stage, write=True) from exc
    response_body = _json_object(response, stage)
    if response.status_code != 200:
        raise FixtureCompletionError(
            f"{stage}_REJECTED (HTTP {response.status_code}, "
            f"code={_error_code(response_body)})"
        )
    return response_body


def _validate_scenario(body: Mapping[str, Any], *, versions: set[int]) -> dict[str, Any]:
    if (
        body.get("client_id") != CLIENT_ID
        or body.get("scenario_id") != SCENARIO_ID
        or body.get("name") != SCENARIO_NAME
        or body.get("status") != "draft"
        or type(body.get("version")) is not int
        or body["version"] not in versions
        or type(body.get("decisions")) is not list
        or len(body["decisions"]) != 1
    ):
        raise FixtureCompletionError("SCENARIO_IDENTITY_MISMATCH")
    decision = body["decisions"][0]
    expected = {
        "decision_id": DECISION_ID,
        "source_product_id": PRODUCT_ID,
        "source_component_id": COMPONENT_ID,
        "component_code": COMPONENT_CODE,
        "amount": AMOUNT,
        "action": "pension",
        "effective_date": EFFECTIVE_DATE,
    }
    if type(decision) is not dict or any(decision.get(key) != value for key, value in expected.items()):
        raise FixtureCompletionError("DECISION_IDENTITY_MISMATCH")
    if decision.get("validation_state") != "unverified":
        raise FixtureCompletionError("DECISION_SOURCE_NOT_CURRENT")
    if not _is_hash(decision.get("source_fingerprint_at_review")):
        raise FixtureCompletionError("DECISION_SOURCE_FINGERPRINT_INVALID")
    return dict(body)


def _validate_product(body: Mapping[str, Any]) -> None:
    if (
        body.get("client_id") != CLIENT_ID
        or body.get("product_id") != PRODUCT_ID
        or type(body.get("version")) is not int
        or body["version"] < 1
        or body.get("statement_date") != PLANNING_BASE_DATE
        or type(body.get("conversion_components")) is not list
    ):
        raise FixtureCompletionError("SOURCE_PRODUCT_PREFLIGHT_MISMATCH")
    rows = [
        row for row in body["conversion_components"]
        if type(row) is dict and row.get("component_id") == COMPONENT_ID
    ]
    if len(rows) != 1 or rows[0].get("component_code") != COMPONENT_CODE:
        raise FixtureCompletionError("SOURCE_COMPONENT_PREFLIGHT_MISMATCH")
    if rows[0].get("balance") != SOURCE_BALANCE:
        raise FixtureCompletionError("SOURCE_COMPONENT_BALANCE_MISMATCH")
    try:
        if Decimal(AMOUNT) > Decimal(rows[0]["balance"]):
            raise FixtureCompletionError("SOURCE_COMPONENT_OVERALLOCATED")
    except (InvalidOperation, TypeError, KeyError) as exc:
        raise FixtureCompletionError("SOURCE_COMPONENT_BALANCE_INVALID") from exc


def _desired_case(current: Mapping[str, Any]) -> dict[str, Any]:
    m01 = current.get("m01_case")
    if current.get("client_id") != CLIENT_ID or type(m01) is not dict:
        raise FixtureCompletionError("CLIENT_PREFLIGHT_MISMATCH")
    if m01.get("birth_date") not in {None, BIRTH_DATE}:
        raise FixtureCompletionError("CLIENT_BIRTH_DATE_CONFLICT")
    if m01.get("gender") not in {None, GENDER}:
        raise FixtureCompletionError("CLIENT_GENDER_CONFLICT")
    if m01.get("planned_retirement_date") not in {None, RETIREMENT_TARGET_DATE}:
        raise FixtureCompletionError("CLIENT_RETIREMENT_DATE_CONFLICT")
    if m01.get("planned_retirement_age") is not None:
        raise FixtureCompletionError("CLIENT_RETIREMENT_AGE_CONFLICT")
    display_name = m01.get("display_name")
    id_number = m01.get("id_number")
    if type(display_name) is not str or not display_name or type(id_number) is not str or not id_number:
        raise FixtureCompletionError("CLIENT_IDENTITY_FIELDS_INVALID")
    return {
        "display_name": display_name,
        "id_number": id_number,
        "birth_date": BIRTH_DATE,
        "gender": GENDER,
        "employment_status": m01.get("employment_status"),
        "planned_retirement_date": RETIREMENT_TARGET_DATE,
        "planned_retirement_age": None,
    }


def _case_is_desired(body: Mapping[str, Any]) -> bool:
    return (
        body.get("client_id") == CLIENT_ID
        and body.get("birth_date") == BIRTH_DATE
        and body.get("gender") == GENDER
        and body.get("planned_retirement_date") == RETIREMENT_TARGET_DATE
        and body.get("planned_retirement_age") is None
    )


def _planning(body: Mapping[str, Any]) -> dict[str, Any]:
    target = body.get("retirement_target")
    if (
        body.get("client_id") != CLIENT_ID
        or type(body.get("decision_version")) is not int
        or body["decision_version"] < 0
        or type(target) is not dict
        or not _is_hash(target.get("current_reference_fingerprint"))
    ):
        raise FixtureCompletionError("PLANNING_CONTEXT_INVALID")
    return dict(body)


def _election() -> dict[str, Any]:
    return {
        "decision_id": DECISION_ID,
        "pension_start_date": PENSION_START_DATE,
        "target_year": TARGET_YEAR,
        "survivors_option": SURVIVORS_OPTION,
        "spouse_age_diff": SPOUSE_AGE_DIFF,
        "coefficient_selection": COEFFICIENT_SELECTION,
        "company_name": SYNTHETIC_COMPANY_NAME,
        "option_name": SYNTHETIC_OPTION_NAME,
    }


def _elections_are_desired(body: Mapping[str, Any]) -> bool:
    rows = body.get("elections")
    if type(rows) is not list:
        raise FixtureCompletionError("ELECTION_RESPONSE_INVALID")
    if not rows:
        return False
    if len(rows) != 1 or type(rows[0]) is not dict:
        raise FixtureCompletionError("ELECTION_STATE_CONFLICT")
    return all(rows[0].get(key) == value for key, value in _election().items())


def _validate_factor_receipt(body: Mapping[str, Any], expected_revision: int) -> None:
    if (
        body.get("admission_revision") != expected_revision + 1
        or not _is_hash(body.get("professional_admission_fingerprint"))
        or body.get("execution_allowed") is not False
    ):
        raise FixtureCompletionError("FACTOR_ADMISSION_RESPONSE_INVALID")


def _validate_ready_result(body: Mapping[str, Any], scenario_version: int) -> dict[str, Any]:
    if not _valid_sealed_result(
        body, client_id=CLIENT_ID, scenario_id=SCENARIO_ID, decision_id=DECISION_ID,
    ):
        raise FixtureCompletionError("GROSS_RESULT_CONTRACT_INVALID")
    if body.get("result_state") != "RESULT_READY" or body.get("execution_allowed") is not True:
        blockers = body.get("blockers")
        code = blockers[0] if type(blockers) is list and blockers else "unknown"
        raise FixtureCompletionError(f"GROSS_RESULT_BLOCKED (code={code})")
    if body.get("scenario_version") != scenario_version:
        raise FixtureCompletionError("GROSS_RESULT_SCENARIO_VERSION_MISMATCH")
    provenance = body.get("coefficient_provenance")
    if (
        type(provenance) is not dict
        or provenance.get("factor_value") != FACTOR_VALUE
        or provenance.get("factor_evidence_type") != FACTOR_EVIDENCE_TYPE
        or provenance.get("factor_evidence_reference") != FACTOR_EVIDENCE_REFERENCE
        or provenance.get("payout_option_name") != SYNTHETIC_OPTION_NAME
    ):
        raise FixtureCompletionError("GROSS_RESULT_FACTOR_PROVENANCE_MISMATCH")
    amount = body.get("monthly_estimate_gross_ils")
    if type(amount) is not str or _MONEY.fullmatch(amount) is None or Decimal(amount) <= 0:
        raise FixtureCompletionError("GROSS_RESULT_AMOUNT_INVALID")
    return dict(body)


def _price_basis_inputs(
    client: Any, gross: Mapping[str, Any], scenario_version: int,
) -> dict[str, Any] | None:
    target = _read(client, TARGET_PATH, "RETIREMENT_INCOME_TARGET")
    if target.get("target_ready") is not True:
        return None
    if (
        target.get("retirement_target_date") != RETIREMENT_TARGET_DATE
        or not _is_hash(target.get("target_result_fingerprint"))
    ):
        raise FixtureCompletionError("RETIREMENT_INCOME_TARGET_MISMATCH")
    cashflow = _read(client, CASHFLOW_PATH, "MONTHLY_CASHFLOW")
    sources = cashflow.get("sources")
    source_id = (
        "scenario-decision:" + quote(SCENARIO_ID, safe="") + ":"
        + quote(DECISION_ID, safe="")
    )
    matches = [
        row for row in sources if type(row) is dict and row.get("source_id") == source_id
    ] if type(sources) is list else []
    if len(matches) != 1:
        raise FixtureCompletionError("PRICE_BASIS_SOURCE_MISSING")
    source = matches[0]
    if (
        source.get("source_kind") != "CALCULATED_PENSION"
        or source.get("source_state") != "READY"
        or not _is_hash(source.get("authority_fingerprint"))
        or gross.get("result_fingerprint") is None
    ):
        raise FixtureCompletionError("PRICE_BASIS_SOURCE_NOT_READY")
    return {
        "expected_scenario_version": scenario_version,
        "expected_source_fingerprint": source["authority_fingerprint"],
        "expected_target_fingerprint": target["target_result_fingerprint"],
        "expected_target_date": RETIREMENT_TARGET_DATE,
        "expected_revision": 0,
        "price_basis": "NOMINAL_AT_RETIREMENT_TARGET_DATE",
    }


def _logout(client: Any, origin: str, csrf: object) -> FixtureCompletionError | None:
    if not _valid_csrf(csrf):
        return FixtureCompletionError("LOGOUT_NOT_ATTEMPTED_NO_VALID_SESSION_CSRF")
    try:
        response = client.post(
            "/api/auth/logout",
            headers={"origin": origin, "x-rtdir-csrf": csrf},
        )
    except httpx.HTTPError:
        return FixtureCompletionError("LOGOUT_NETWORK_FAILURE")
    if response.status_code != 204:
        return FixtureCompletionError(f"LOGOUT_UNCONFIRMED (HTTP {response.status_code})")
    return None


def run_completion(client: Any, *, origin: str, username: str, password: str) -> dict[str, Any]:
    """Execute the approved sequence once, preserving every server CAS boundary."""
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
        raise FixtureCompletionError(
            f"LOGIN_REJECTED (HTTP {login.status_code}, code={_error_code(body)})"
        )

    cleanup_csrf: object = None
    primary: FixtureCompletionError | None = None
    evidence: dict[str, Any] = {
        "schema_version": "STAGING_E2E_FIXTURE_COMPLETION_EVIDENCE_V1",
        "target": {
            "client_id": CLIENT_ID,
            "scenario_id": SCENARIO_ID,
            "decision_id": DECISION_ID,
            "product_id": PRODUCT_ID,
            "component_id": COMPONENT_ID,
        },
        "confirmed_steps": [],
        "price_basis": {"status": "not_evaluated"},
    }
    try:
        login_body = _json_object(login, "LOGIN")
        login_csrf = login_body.get("csrf_token")
        if login_body.get("authenticated") is not True or not _valid_csrf(login_csrf):
            raise FixtureCompletionError("LOGIN_RESPONSE_INVALID")
        cleanup_csrf = login_csrf
        session = _read(client, "/api/auth/session", "SESSION")
        if (
            session.get("authenticated") is not True
            or not _valid_csrf(session.get("csrf_token"))
            or session["csrf_token"] != login_csrf
        ):
            raise FixtureCompletionError("SESSION_CSRF_INVALID")

        scenario = _validate_scenario(
            _read(client, SCENARIO_PATH, "SCENARIO_PREFLIGHT"),
            versions={INITIAL_SCENARIO_VERSION},
        )
        _validate_product(_read(client, PRODUCT_PATH, "PRODUCT_PREFLIGHT"))
        evidence["confirmed_steps"].append("source_and_scenario_preflight")

        client_state = _read(client, CLIENT_PATH, "CLIENT_PREFLIGHT")
        desired_case = _desired_case(client_state)
        if not _case_is_desired(client_state["m01_case"]):
            case = _write(
                client, "PUT", CASE_PATH, "CLIENT_CASE_WRITE", desired_case,
                origin=origin, csrf=login_csrf,
            )
            if not _case_is_desired(case):
                raise FixtureCompletionError("CLIENT_CASE_RESPONSE_INVALID")
        evidence["confirmed_steps"].append("client_profile_and_retirement_facts")

        planning = _planning(_read(client, PLANNING_PATH, "PLANNING_PREFLIGHT"))
        if planning.get("planning_base_date") not in {None, PLANNING_BASE_DATE}:
            raise FixtureCompletionError("PLANNING_BASE_DATE_CONFLICT")
        if planning.get("planning_base_date") is None:
            _write(
                client, "PUT", PLANNING_PATH + "/base-date", "PLANNING_BASE_WRITE",
                {"expected_version": planning["decision_version"],
                 "planning_base_date": PLANNING_BASE_DATE},
                origin=origin, csrf=login_csrf,
            )
            planning = _planning(_read(client, PLANNING_PATH, "PLANNING_AFTER_BASE"))
        if planning.get("planning_base_date") != PLANNING_BASE_DATE:
            raise FixtureCompletionError("PLANNING_BASE_DATE_NOT_PERSISTED")
        target = planning["retirement_target"]
        if target.get("retirement_target_date") not in {None, RETIREMENT_TARGET_DATE}:
            raise FixtureCompletionError("RETIREMENT_TARGET_DATE_CONFLICT")
        if target.get("retirement_target_date") is None:
            _write(
                client, "PUT", PLANNING_PATH + "/target-date", "RETIREMENT_TARGET_WRITE",
                {
                    "expected_version": planning["decision_version"],
                    "expected_target_reference_fingerprint": target["current_reference_fingerprint"],
                    "retirement_target_date": RETIREMENT_TARGET_DATE,
                },
                origin=origin, csrf=login_csrf,
            )
            planning = _planning(_read(client, PLANNING_PATH, "PLANNING_AFTER_TARGET"))
        if (
            planning.get("planning_base_date") != PLANNING_BASE_DATE
            or planning["retirement_target"].get("retirement_target_date")
            != RETIREMENT_TARGET_DATE
            or planning["retirement_target"].get("retirement_target_ready") is not True
        ):
            raise FixtureCompletionError("PLANNING_DATES_NOT_READY")
        evidence["planning_decision_version"] = planning["decision_version"]
        evidence["confirmed_steps"].append("planning_base_and_retirement_target")

        election_state = _read(client, ELECTIONS_PATH, "ELECTION_PREFLIGHT")
        if election_state.get("elections") and not _elections_are_desired(election_state):
            raise FixtureCompletionError("ELECTION_STATE_CONFLICT")
        if not election_state.get("elections"):
            scenario_version = scenario["version"]
            election_write = _write(
                client, "PUT", ELECTIONS_PATH, "ELECTION_WRITE",
                {"expected_scenario_version": scenario_version, "elections": [_election()]},
                origin=origin, csrf=login_csrf,
            )
            scenario = _validate_scenario(election_write, versions={scenario_version + 1})
        else:
            scenario = _validate_scenario(
                _read(client, SCENARIO_PATH, "SCENARIO_AFTER_ELECTION"),
                versions={INITIAL_SCENARIO_VERSION + 1},
            )
        election_state = _read(client, ELECTIONS_PATH, "ELECTION_CONFIRMATION")
        if not _elections_are_desired(election_state):
            raise FixtureCompletionError("ELECTION_NOT_PERSISTED")
        scenario_version = scenario["version"]
        evidence["scenario_version_after_election"] = scenario_version
        evidence["confirmed_steps"].append("pension_election")

        cursor = _read(client, FACTOR_CURSOR_PATH, "FACTOR_CURSOR")
        if (
            cursor.get("scenario_version") != scenario_version
            or type(cursor.get("latest_admission_revision")) is not int
            or cursor["latest_admission_revision"] != 0
        ):
            raise FixtureCompletionError("FACTOR_ADMISSION_CURSOR_CONFLICT")
        receipt = _write(
            client, "POST", FACTOR_PATH, "FACTOR_ADMISSION_WRITE",
            {
                "expected_scenario_version": scenario_version,
                "expected_admission_revision": 0,
                "factor_value": FACTOR_VALUE,
                "factor_evidence_type": FACTOR_EVIDENCE_TYPE,
                "factor_evidence_reference": FACTOR_EVIDENCE_REFERENCE,
            },
            origin=origin, csrf=login_csrf,
        )
        _validate_factor_receipt(receipt, 0)
        evidence["factor_admission_revision"] = receipt["admission_revision"]
        evidence["confirmed_steps"].append("professional_factor_admission")

        gross = _validate_ready_result(
            _read(client, GROSS_PATH, "GROSS_ESTIMATE"), scenario_version,
        )
        evidence["gross_result"] = {
            "result_state": gross["result_state"],
            "monthly_estimate_gross_ils": gross["monthly_estimate_gross_ils"],
            "result_fingerprint": gross["result_fingerprint"],
        }
        evidence["confirmed_steps"].append("gross_estimate_result_ready")

        price_inputs = _price_basis_inputs(client, gross, scenario_version)
        if price_inputs is None:
            evidence["price_basis"] = {
                "status": "skipped",
                "reason": "RETIREMENT_MONTHLY_INCOME_TARGET_NOT_READY",
            }
        else:
            price = _write(
                client, "POST", PRICE_BASIS_PATH, "PRICE_BASIS_WRITE", price_inputs,
                origin=origin, csrf=login_csrf,
            )
            if (
                price.get("scenario_id") != SCENARIO_ID
                or price.get("decision_id") != DECISION_ID
                or price.get("scenario_version") != scenario_version
                or price.get("revision") != 1
                or price.get("price_basis") != "NOMINAL_AT_RETIREMENT_TARGET_DATE"
                or not _is_hash(price.get("record_fingerprint"))
            ):
                raise FixtureCompletionError("PRICE_BASIS_RESPONSE_INVALID")
            evidence["price_basis"] = {
                "status": "confirmed", "revision": 1,
                "record_fingerprint": price["record_fingerprint"],
            }
            evidence["confirmed_steps"].append("price_basis")

        reloaded = _validate_ready_result(
            _read(client, GROSS_PATH, "GROSS_ESTIMATE_RELOAD"), scenario_version,
        )
        if reloaded["result_fingerprint"] != gross["result_fingerprint"]:
            raise FixtureCompletionError("GROSS_RESULT_FINGERPRINT_CHANGED")
        evidence["gross_result_reloaded"] = True
        evidence["run_status"] = "completed"
    except ProbeError as exc:
        primary = FixtureCompletionError(str(exc), evidence=evidence)
    except FixtureCompletionError as exc:
        primary = FixtureCompletionError(str(exc), evidence=evidence)
    except httpx.HTTPError as exc:
        primary = FixtureCompletionError("UNEXPECTED_NETWORK_FAILURE", evidence=evidence)
    finally:
        cleanup = _logout(client, origin, cleanup_csrf)

    if primary is not None:
        if cleanup is not None:
            raise FixtureCompletionError(
                str(primary), evidence=primary.evidence, cleanup_error=str(cleanup),
            ) from primary
        raise primary
    if cleanup is not None:
        raise FixtureCompletionError(
            "FIXTURE_COMPLETION_CLEANUP_FAILED", evidence=evidence,
            cleanup_error=str(cleanup),
        ) from cleanup
    return evidence


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-approved-fixture", action="store_true")
    parser.add_argument("--origin", default=STAGING_ORIGIN)
    parser.add_argument("--username", default=os.getenv("RETIRE_V2_STAGING_USERNAME", ""))
    parser.add_argument("--evidence-json", type=Path)
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    if not args.confirm_approved_fixture:
        print("BLOCKED: --confirm-approved-fixture is required")
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
            headers={"user-agent": "retire-v2-e2e-fixture-completion/1"},
        ) as client:
            evidence = run_completion(
                client, origin=origin, username=args.username, password=password,
            )
        serialized = json.dumps(evidence, ensure_ascii=False, sort_keys=True, indent=2)
        if args.evidence_json:
            args.evidence_json.write_text(serialized + "\n", encoding="utf-8")
        print(serialized)
        return 0
    except (httpx.HTTPError, ProbeError, FixtureCompletionError) as exc:
        failure = {
            "schema_version": "STAGING_E2E_FIXTURE_COMPLETION_FAILURE_V1",
            "run_status": "failed",
            "primary_error": str(exc),
            "confirmed_evidence": exc.evidence if isinstance(exc, FixtureCompletionError) else None,
            "cleanup_error": exc.cleanup_error if isinstance(exc, FixtureCompletionError) else None,
        }
        serialized = json.dumps(failure, ensure_ascii=False, sort_keys=True, indent=2)
        if args.evidence_json:
            args.evidence_json.write_text(serialized + "\n", encoding="utf-8")
        print(serialized)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
