"""Canonical comparison-basis authority for retirement target-date income."""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime
import hashlib
import json
import re
import unicodedata
from typing import Any, Mapping

from sqlalchemy.orm import Session

from app.services import retirement_monthly_income_target_service as target_service
from app.services import retirement_target_date_income_source_basis_service as crtisba_service


SCHEMA_VERSION = "CANONICAL_RETIREMENT_TARGET_DATE_INCOME_COMPARISON_BASIS_RESULT_V2"
INPUT_FINGERPRINT_CONTRACT = "CANONICAL_RETIREMENT_TARGET_DATE_INCOME_COMPARISON_BASIS_INPUT_JSON_V2"
ENTRY_FINGERPRINT_CONTRACT = "CANONICAL_RETIREMENT_TARGET_DATE_INCOME_COMPARISON_ENTRY_JSON_V2"
RESULT_FINGERPRINT_CONTRACT = "CANONICAL_RETIREMENT_TARGET_DATE_INCOME_COMPARISON_BASIS_RESULT_JSON_V2"
FAILURE_FINGERPRINT_CONTRACT = "CANONICAL_RETIREMENT_TARGET_DATE_INCOME_COMPARISON_BASIS_FAILURE_JSON_V2"

REQUEST_FIELDS = frozenset({
    "client_id",
    "expected_planning_calculation_input_fingerprint",
    "expected_retirement_target_date",
})
TARGET_RESULT_FIELDS = frozenset({
    "schema_version", "client_id", "planning_calculation_input_fingerprint",
    "retirement_target_date", "target", "authority", "authority_state",
    "target_readiness_state", "target_ready", "blockers",
    "target_semantic_fingerprint", "target_result_fingerprint",
})
TARGET_FIELDS = frozenset({
    "client_id", "planning_calculation_input_fingerprint", "retirement_target_date",
    "monthly_amount", "currency", "income_basis", "price_basis", "price_reference_date",
})
TARGET_AUTHORITY_FIELDS = frozenset({
    "record_version", "source_kind", "confirmation_state", "confirmation_actor",
    "confirmed_at", "lifecycle_state",
})
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z", re.ASCII)
TIMESTAMP_RE = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}Z\Z",
    re.ASCII,
)
TARGET_INCOME_BASES = frozenset({"GROSS", "NET"})
TARGET_PRICE_BASES = frozenset({"NOMINAL_AT_RETIREMENT_TARGET_DATE", "REAL_AT_REFERENCE_DATE"})
TARGET_BLOCKERS = frozenset({
    "RIT_AMOUNT_INVALID",
    "RIT_AMOUNT_MISSING",
    "RIT_AMOUNT_PRECISION_UNSUPPORTED",
    "RIT_CLIENT_ID_INVALID",
    "RIT_CONFIRMATION_INVALID",
    "RIT_CONFIRMATION_MISSING",
    "RIT_CURRENCY_INVALID",
    "RIT_INCOME_BASIS_INVALID",
    "RIT_INCOME_BASIS_MISSING",
    "RIT_NOMINAL_PRICE_REFERENCE_DATE_NOT_NULL",
    "RIT_PLANNING_CONTEXT_INVALID",
    "RIT_PLANNING_CONTEXT_UNAVAILABLE",
    "RIT_PLANNING_IDENTITY_STALE",
    "RIT_PRICE_BASIS_INVALID",
    "RIT_PRICE_BASIS_MISSING",
    "RIT_PRICE_REFERENCE_DATE_MISSING",
    "RIT_RECONFIRMATION_REQUIRED",
    "RIT_RETIREMENT_TARGET_NOT_READY",
    "RIT_RETIREMENT_TARGET_STALE",
    "RIT_STORED_FINGERPRINT_MISMATCH",
    "RIT_TARGET_CLIENT_MISMATCH",
    "RIT_TARGET_MISSING",
    "RIT_TARGET_RECORD_INVALID",
})
class RTICBFingerprintConstructionError(RuntimeError):
    """Technical failure while constructing an RTICB-owned identity."""


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise RTICBFingerprintConstructionError(str(exc)) from exc


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _is_sha(value: Any) -> bool:
    return isinstance(value, str) and SHA256_RE.fullmatch(value) is not None


def _is_date(value: Any) -> bool:
    if not isinstance(value, str) or DATE_RE.fullmatch(value) is None:
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def _positive_int(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value > 0


def _canonical_string(value: Any) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and value == value.strip(" \t\r\n")
        and not any(unicodedata.category(character) == "Cc" for character in value)
    )


def _canonical_source_id(value: Any) -> bool:
    """Validate RTISA identifiers without repairing Unicode whitespace."""
    return (
        isinstance(value, str)
        and bool(value)
        and value == value.strip()
        and not any(unicodedata.category(character) == "Cc" for character in value)
    )


def _sorted_unique_strings(value: Any, *, allow_empty: bool = True) -> bool:
    return (
        isinstance(value, list)
        and (allow_empty or bool(value))
        and all(_canonical_string(item) for item in value)
        and value == sorted(set(value))
    )


def _sorted_unique_source_ids(value: Any) -> bool:
    return (
        isinstance(value, list)
        and all(_canonical_source_id(item) for item in value)
        and value == sorted(set(value))
    )


def _field_observation(result: Any, key: str, validator) -> Any:
    if not isinstance(result, Mapping):
        return None
    value = result.get(key)
    return value if validator(value) else None


def _request_observations(request: Any) -> dict[str, Any]:
    source = request if isinstance(request, Mapping) else {}
    client_id = source.get("client_id")
    planning = source.get("expected_planning_calculation_input_fingerprint")
    target_date = source.get("expected_retirement_target_date")
    return {
        "client_id": client_id if _positive_int(client_id) else None,
        "supplied_planning_calculation_input_fingerprint": planning if _is_sha(planning) else None,
        "supplied_retirement_target_date": target_date if _is_date(target_date) else None,
    }


def _failure(request: Any, stage: str, code: str, *, target: Any = None, crtisba: Any = None) -> dict:
    supplied = _request_observations(request)
    blocked = isinstance(crtisba, Mapping) and crtisba.get("schema_version") == "CRTISBA_BLOCK_NO_RESULT_V1" and _blocked_valid(crtisba, supplied["client_id"])
    collection = isinstance(crtisba, Mapping) and not blocked
    failure = {
        "schema_version": SCHEMA_VERSION, "client_id": supplied["client_id"],
        "supplied_planning_calculation_input_fingerprint": supplied["supplied_planning_calculation_input_fingerprint"],
        "supplied_retirement_target_date": supplied["supplied_retirement_target_date"],
        "observed_target_planning_calculation_input_fingerprint": _field_observation(target, "planning_calculation_input_fingerprint", _is_sha),
        "observed_target_retirement_target_date": _field_observation(target, "retirement_target_date", _is_date),
        "observed_target_result_fingerprint": _field_observation(target, "target_result_fingerprint", _is_sha),
        "observed_crtisba_planning_calculation_input_fingerprint": _field_observation(crtisba, "observed_planning_calculation_input_fingerprint" if blocked else "planning_calculation_input_fingerprint", _is_sha),
        "observed_crtisba_retirement_target_date": _field_observation(crtisba, "retirement_target_date", _is_date) if collection else None,
        "observed_crtisba_result_fingerprint": _field_observation(crtisba, "result_fingerprint", _is_sha) if collection else None,
        "observed_crtisba_failure_fingerprint": crtisba["failure_fingerprint"] if blocked else None,
        "observed_crtisba_failure_stage": crtisba["failure_stage"] if blocked else None,
        "observed_crtisba_failure_detail_code": crtisba["failure_detail_code"] if blocked else None,
        "result_state": "block_no_result", "failure_stage": stage, "failure_detail_code": code,
    }
    failure["result_fingerprint"] = _fingerprint({"contract": FAILURE_FINGERPRINT_CONTRACT, "failure": failure})
    return failure


def _request_error(request: Any) -> str | None:
    if not isinstance(request, Mapping) or set(request) != REQUEST_FIELDS:
        return "RTICB_REQUEST_SCHEMA_INVALID"
    if not _positive_int(request["client_id"]):
        return "RTICB_CLIENT_ID_INVALID"
    if not _is_sha(request["expected_planning_calculation_input_fingerprint"]):
        return "RTICB_EXPECTED_PLANNING_FINGERPRINT_INVALID"
    if not _is_date(request["expected_retirement_target_date"]):
        return "RTICB_EXPECTED_RETIREMENT_TARGET_DATE_INVALID"
    return None


def _target_object_valid(value: Any) -> bool:
    if not isinstance(value, dict) or set(value) != TARGET_FIELDS:
        return False
    reference = value["price_reference_date"]
    price_basis = value["price_basis"]
    canonical_amount, amount_error = target_service._canonical_amount(value["monthly_amount"])
    return (
        _positive_int(value["client_id"])
        and _is_sha(value["planning_calculation_input_fingerprint"])
        and _is_date(value["retirement_target_date"])
        and amount_error is None
        and canonical_amount == value["monthly_amount"]
        and value["currency"] == "ILS"
        and isinstance(value["income_basis"], str)
        and value["income_basis"] in TARGET_INCOME_BASES
        and isinstance(price_basis, str)
        and price_basis in TARGET_PRICE_BASES
        and (
            (price_basis == "NOMINAL_AT_RETIREMENT_TARGET_DATE" and reference is None)
            or (price_basis == "REAL_AT_REFERENCE_DATE" and _is_date(reference))
        )
    )


def _target_authority_valid(value: Any) -> bool:
    if not isinstance(value, dict) or set(value) != TARGET_AUTHORITY_FIELDS:
        return False
    confirmed_at = value["confirmed_at"]
    try:
        timestamp_valid = (
            isinstance(confirmed_at, str)
            and TIMESTAMP_RE.fullmatch(confirmed_at) is not None
            and datetime.strptime(confirmed_at, "%Y-%m-%dT%H:%M:%S.%fZ").strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ"
            ) == confirmed_at
        )
    except ValueError:
        timestamp_valid = False
    return (
        _positive_int(value["record_version"])
        and value["record_version"] <= target_service.MAX_VERSION
        and isinstance(value["source_kind"], str)
        and value["source_kind"] in target_service.SOURCE_KINDS
        and value["confirmation_state"] == "CONFIRMED"
        and target_service._valid_actor(value["confirmation_actor"])
        and timestamp_valid
        and isinstance(value["lifecycle_state"], str)
        and value["lifecycle_state"] in {"CONFIRMED", "STALE"}
    )


def _target_state_valid(result: dict) -> bool:
    target = result["target"]
    authority = result["authority"]
    state = result["authority_state"]
    ready = result["target_ready"]
    readiness = result["target_readiness_state"]
    blockers = result["blockers"]
    if (readiness == "READY") != ready:
        return False
    if ready != (
        state == "CURRENT"
        and target is not None
        and authority is not None
        and not blockers
    ):
        return False
    if state == "CURRENT":
        return authority is not None and authority["lifecycle_state"] == "CONFIRMED"
    if state == "STALE":
        return (
            target is not None
            and authority is not None
            and authority["lifecycle_state"] == "STALE"
            and "RIT_RECONFIRMATION_REQUIRED" in blockers
        )
    if state == "MISSING":
        return target is None and authority is None and blockers == ["RIT_TARGET_MISSING"]
    if state == "UNAVAILABLE":
        return (
            target is None
            and authority is None
            and result["planning_calculation_input_fingerprint"] is None
            and result["retirement_target_date"] is None
            and bool(blockers)
        )
    if state == "INVALID":
        return bool(blockers)
    return False


def _target_schema_valid(result: Any) -> bool:
    if not isinstance(result, dict) or set(result) != TARGET_RESULT_FIELDS:
        return False
    target = result["target"]
    authority = result["authority"]
    return (
        result["schema_version"] == target_service.SCHEMA_VERSION
        and _positive_int(result["client_id"])
        and (result["planning_calculation_input_fingerprint"] is None
             or _is_sha(result["planning_calculation_input_fingerprint"]))
        and (result["retirement_target_date"] is None or _is_date(result["retirement_target_date"]))
        and (target is None or _target_object_valid(target))
        and (authority is None or _target_authority_valid(authority))
        and (target is None or target["client_id"] == result["client_id"])
        and (
            target is None
            or result["authority_state"] != "CURRENT"
            or (
                target["planning_calculation_input_fingerprint"]
                == result["planning_calculation_input_fingerprint"]
                and target["retirement_target_date"] == result["retirement_target_date"]
            )
        )
        and isinstance(result["authority_state"], str)
        and result["authority_state"] in {"MISSING", "UNAVAILABLE", "INVALID", "STALE", "CURRENT"}
        and isinstance(result["target_readiness_state"], str)
        and result["target_readiness_state"] in {"READY", "NOT_READY"}
        and isinstance(result["target_ready"], bool)
        and _sorted_unique_strings(result["blockers"])
        and set(result["blockers"]).issubset(TARGET_BLOCKERS)
        and (result["target_semantic_fingerprint"] is None
             or isinstance(result["target_semantic_fingerprint"], str))
        and isinstance(result["target_result_fingerprint"], str)
        and _target_state_valid(result)
    )


def _target_fingerprints_valid(result: dict) -> bool:
    stored_result = result["target_result_fingerprint"]
    stored_semantic = result["target_semantic_fingerprint"]
    target = result["target"]
    if not _is_sha(stored_result):
        return False
    if target is None:
        if stored_semantic is not None:
            return False
    else:
        if not _is_sha(stored_semantic):
            return False
        if stored_semantic != _fingerprint({"contract": target_service.SEMANTIC_CONTRACT, **target}):
            return False
    payload = {key: deepcopy(value) for key, value in result.items() if key != "target_result_fingerprint"}
    return stored_result == _fingerprint({"contract": target_service.RESULT_CONTRACT, **payload})



COLLECTION_FIELDS = frozenset(("schema_version", "client_id", "planning_calculation_input_fingerprint", "retirement_target_date",
 "rtisa_admission_result_fingerprint", "source_basis_entries", "partitions", "blockers",
 "basis_readiness_state", "basis_ready", "result_fingerprint"))
ENTRY_FIELDS = frozenset(("schema_version", "source_id", "source_kind", "source_category", "admission_state",
 "rtisa_reason_codes", "source_version", "source_fingerprint", "amount_authority_fingerprint",
 "decision_version", "decision_fingerprint", "decision_state", "income_basis", "income_basis_provenance",
 "price_basis", "price_reference_date", "price_basis_provenance", "blockers"))
PARTITIONS = {"CURRENT":"current","MISSING":"missing","UNKNOWN":"unknown","STALE":"stale",
 "INVALID":"invalid","UPSTREAM_UNRESOLVED":"upstream_unresolved","NOT_APPLICABLE_DELEGATED":"not_applicable_delegated",
 "NOT_APPLICABLE_NOT_ADMITTED":"not_applicable_not_admitted","DELEGATION_UNRESOLVED":"delegation_unresolved","DELEGATION_STALE":"delegation_stale"}
BLOCKED_FIELDS = frozenset(("schema_version","result_state","client_id","source_id","operation",
 "failure_stage","failure_detail_code","field_paths","observed_planning_calculation_input_fingerprint",
 "observed_source_version","observed_source_fingerprint","observed_amount_authority_fingerprint",
 "observed_decision_version","failure_fingerprint"))
BLOCKED_CODES = {
 "planning_context":"CRTISBA_PLANNING_CONTEXT_UNAVAILABLE",
 "retirement_target":"CRTISBA_RETIREMENT_TARGET_NOT_READY",
 "source_universe":"CRTISBA_SOURCE_UNIVERSE_INVALID",
 "pension_result":"CRTISBA_PENSION_RESULT_INVALID",
}
BLOCKED_RTICB = {
 "planning_context":"RTICB_CRTISBA_BLOCKED_PLANNING_CONTEXT_UNAVAILABLE",
 "retirement_target":"RTICB_CRTISBA_BLOCKED_RETIREMENT_TARGET_NOT_READY",
 "source_universe":"RTICB_CRTISBA_BLOCKED_SOURCE_UNIVERSE_INVALID",
 "pension_result":"RTICB_CRTISBA_BLOCKED_PENSION_RESULT_INVALID",
}
NON_DELEGATION_UNRESOLVED = frozenset(crtisba_service.NON_DELEGATION_UNRESOLVED)
EXCLUDED_REASONS = frozenset({"RTISA_FUTURE_SOURCE", "RTISA_ENDED_SOURCE"})
ALL_RTISA_REASONS = frozenset(
    set(NON_DELEGATION_UNRESOLVED)
    | set(EXCLUDED_REASONS)
    | {
        "RTISA_SAME_CANONICAL_PENSION",
        "RTISA_SOURCE_IDENTITY_UNRESOLVED",
        "RTISA_SOURCE_IDENTITY_STALE",
    }
)
RECURRING_SOURCE_CATEGORIES = frozenset({
    "EMPLOYMENT", "RENTAL", "BUSINESS", "BENEFIT", "OTHER", "PENSION_REPRESENTATION",
})
BLOCKERS = {
 "MISSING":"RTICB_CRTISBA_DECISION_MISSING","UNKNOWN":"RTICB_CRTISBA_DECISION_UNKNOWN",
 "STALE":"RTICB_CRTISBA_DECISION_STALE","INVALID":"RTICB_CRTISBA_DECISION_INVALID",
 "UPSTREAM_UNRESOLVED":"RTICB_CRTISBA_UPSTREAM_UNRESOLVED",
 "DELEGATION_UNRESOLVED":"RTICB_CRTISBA_DELEGATION_UNRESOLVED",
 "DELEGATION_STALE":"RTICB_CRTISBA_DELEGATION_STALE",
}
ENTRY_FINGERPRINT_CONTRACT = "CANONICAL_RETIREMENT_TARGET_DATE_INCOME_COMPARISON_ENTRY_JSON_V2"
COLLECTION_CONTRACT = "CANONICAL_RETIREMENT_TARGET_DATE_INCOME_SOURCE_BASIS_RESULT_JSON_V1"
BLOCKED_CONTRACT = "CANONICAL_RETIREMENT_TARGET_DATE_INCOME_SOURCE_BASIS_FAILURE_JSON_V1"

def _sorted_codes(values: Any) -> bool:
    return (isinstance(values,list) and all(isinstance(v,str) and v and v==v.strip() for v in values)
            and values==sorted(set(values)))


def _json_pointer(value: Any) -> bool:
    return bool(
        _canonical_string(value)
        and re.fullmatch(r"(?:/(?:[^~]|~[01])*)+", value, re.ASCII)
    )

def _blocked_valid(obj: Any, client_id: int|None) -> bool:
    if not isinstance(obj,Mapping) or set(obj)!=BLOCKED_FIELDS:
        return False
    stage=obj.get("failure_stage")
    if not isinstance(stage,str):return False
    if (obj.get("schema_version")!="CRTISBA_BLOCK_NO_RESULT_V1" or obj.get("result_state")!="block_no_result"
        or obj.get("client_id")!=client_id or not _positive_int(obj.get("client_id"))
        or obj.get("operation")!="READ" or BLOCKED_CODES.get(stage)!=obj.get("failure_detail_code")
        or not _sorted_codes(obj.get("field_paths"))
        or not all(_json_pointer(path) for path in obj["field_paths"])):
        return False
    if obj.get("source_id") is not None and not _canonical_source_id(obj["source_id"]):
        return False
    for k in ("observed_planning_calculation_input_fingerprint","observed_source_fingerprint","observed_amount_authority_fingerprint"):
        if obj[k] is not None and not _is_sha(obj[k]):return False
    if obj["observed_source_version"] is not None and not (
        _positive_int(obj["observed_source_version"]) or _is_sha(obj["observed_source_version"])
    ):return False
    if obj["observed_decision_version"] is not None and (
        type(obj["observed_decision_version"]) is not int or not 0<=obj["observed_decision_version"]<2**63
    ):return False
    if not _is_sha(obj.get("failure_fingerprint")):return False
    pre={"contract":BLOCKED_CONTRACT,**{k:deepcopy(v) for k,v in obj.items()
        if k not in {"schema_version","result_state","failure_fingerprint"}}}
    return _fingerprint(pre)==obj["failure_fingerprint"]

def _entry_authority_valid(e: Any) -> bool:
    if not isinstance(e,Mapping) or set(e)!=ENTRY_FIELDS:return False
    if e["schema_version"]!="CRTISBA_SOURCE_BASIS_ENTRY_V1" or not _canonical_source_id(e["source_id"]):return False
    if not isinstance(e["source_kind"],str) or e["source_kind"] not in {"PENSION","RECURRING_INCOME"} or not _canonical_string(e["source_category"]):return False
    if e["source_kind"] == "PENSION" and e["source_category"] != "PENSION":return False
    if e["source_kind"] == "RECURRING_INCOME" and e["source_category"] not in RECURRING_SOURCE_CATEGORIES:return False
    if not isinstance(e["decision_state"],str) or e["decision_state"] not in PARTITIONS or not isinstance(e["admission_state"],str) or e["admission_state"] not in {"INCLUDED","EXCLUDED","UNRESOLVED"}:return False
    if not _sorted_codes(e["rtisa_reason_codes"]) or not _sorted_codes(e["blockers"]):return False
    if not set(e["rtisa_reason_codes"]).issubset(ALL_RTISA_REASONS):return False
    if not _is_sha(e["source_fingerprint"]):return False
    if e["source_kind"]=="PENSION":
        if not _positive_int(e["source_version"]):return False
        if not e["source_id"].startswith(("manual:","conversion:")):return False
    else:
        if e["source_version"]!=e["source_fingerprint"] or not e["source_id"].startswith("income:"):return False
    if e["amount_authority_fingerprint"] is not None and not _is_sha(e["amount_authority_fingerprint"]):return False
    if (e["decision_version"] is None)!=(e["decision_fingerprint"] is None):return False
    if e["decision_version"] is not None and (not _positive_int(e["decision_version"])
        or e["decision_version"]>crtisba_service.MAX_VERSION or not _is_sha(e["decision_fingerprint"])):return False
    for k,v in (("income_basis",{"GROSS","NET","UNKNOWN"}),("price_basis",{"NOMINAL_AT_RETIREMENT_TARGET_DATE","REAL_AT_REFERENCE_DATE","UNKNOWN"})):
        if e[k] is not None and (not isinstance(e[k],str) or e[k] not in v):return False
    for k,v in (("income_basis_provenance",{"EXPLICIT_PROFESSIONAL","UPSTREAM_RECURRING_AMOUNT_BASIS","MISSING"}),
                ("price_basis_provenance",{"OWNER_DECISION_OD2","EXPLICIT_PROFESSIONAL","MISSING"})):
        if e[k] is not None and e[k] not in v:return False
    if e["price_reference_date"] is not None and not _is_date(e["price_reference_date"]):return False
    return True


def _recurring_safe_basis(e: Mapping[str, Any]) -> bool:
    return (
        (
            e["income_basis"] in {"GROSS", "NET"}
            and e["income_basis_provenance"] == "UPSTREAM_RECURRING_AMOUNT_BASIS"
        )
        or (
            e["income_basis"] == "UNKNOWN"
            and e["income_basis_provenance"] == "MISSING"
        )
    ) and (
        e["price_basis"] == "UNKNOWN"
        and e["price_reference_date"] is None
        and e["price_basis_provenance"] == "MISSING"
    )


def _entry_state_valid(e: Mapping[str, Any]) -> bool:
    state=e["decision_state"]
    if state in {"CURRENT","MISSING","UNKNOWN","STALE","INVALID"} and e["admission_state"]!="INCLUDED":return False
    if state in {"UPSTREAM_UNRESOLVED","DELEGATION_UNRESOLVED","DELEGATION_STALE"} and e["admission_state"]!="UNRESOLVED":return False
    if state in {"NOT_APPLICABLE_DELEGATED","NOT_APPLICABLE_NOT_ADMITTED"} and e["admission_state"]!="EXCLUDED":return False
    if state in {"NOT_APPLICABLE_DELEGATED","NOT_APPLICABLE_NOT_ADMITTED","DELEGATION_UNRESOLVED","DELEGATION_STALE"}:
        if any(e[x] is not None for x in ("income_basis","income_basis_provenance","price_basis",
                                            "price_reference_date","price_basis_provenance")):return False
    safe_missing = (
        (e["income_basis"] == "UNKNOWN" and e["income_basis_provenance"] == "MISSING"
         and e["price_basis"] == "NOMINAL_AT_RETIREMENT_TARGET_DATE"
         and e["price_reference_date"] is None and e["price_basis_provenance"] == "OWNER_DECISION_OD2")
        if e["source_kind"] == "PENSION" else
        _recurring_safe_basis(e)
    )
    if state in {"CURRENT","MISSING","UNKNOWN","STALE","INVALID"}:
        if (e["source_version"] is None or e["amount_authority_fingerprint"] is None):return False
        if e["rtisa_reason_codes"] != []:return False
        expected_blockers = [] if state=="CURRENT" else ["CRTISBA_DECISION_"+state]
        if e["blockers"] != expected_blockers:return False
        if state in {"CURRENT","UNKNOWN","STALE"} and e["decision_version"] is None:return False
        if state in {"MISSING","INVALID"} and e["decision_version"] is not None:return False
        if state in {"MISSING","UNKNOWN","STALE","INVALID"} and not safe_missing:return False
        if state=="CURRENT":
            if e["source_kind"]=="PENSION":
                if (e["income_basis"] not in {"GROSS","NET"}
                    or e["income_basis_provenance"]!="EXPLICIT_PROFESSIONAL"
                    or e["price_basis"]!="NOMINAL_AT_RETIREMENT_TARGET_DATE"
                    or e["price_reference_date"] is not None
                    or e["price_basis_provenance"]!="OWNER_DECISION_OD2"):return False
            else:
                if (e["income_basis"] not in {"GROSS","NET","UNKNOWN"}
                    or e["income_basis_provenance"] != ("MISSING" if e["income_basis"]=="UNKNOWN" else "UPSTREAM_RECURRING_AMOUNT_BASIS")
                    or e["price_basis"] not in {"NOMINAL_AT_RETIREMENT_TARGET_DATE","REAL_AT_REFERENCE_DATE"}
                    or e["price_basis_provenance"]!="EXPLICIT_PROFESSIONAL"
                    or (e["price_basis"]=="REAL_AT_REFERENCE_DATE")!=(e["price_reference_date"] is not None)):return False
    elif state in {"NOT_APPLICABLE_DELEGATED","NOT_APPLICABLE_NOT_ADMITTED","DELEGATION_UNRESOLVED","DELEGATION_STALE"}:
        if e["amount_authority_fingerprint"] is not None or e["decision_version"] is not None:return False
        if state!="NOT_APPLICABLE_NOT_ADMITTED" and (
            e["source_kind"]!="RECURRING_INCOME" or e["source_category"]!="PENSION_REPRESENTATION"
        ):return False
        expected_reasons = {
            "NOT_APPLICABLE_DELEGATED":["RTISA_SAME_CANONICAL_PENSION"],
            "NOT_APPLICABLE_NOT_ADMITTED":None,
            "DELEGATION_UNRESOLVED":["RTISA_SOURCE_IDENTITY_UNRESOLVED"],
            "DELEGATION_STALE":["RTISA_SOURCE_IDENTITY_STALE"],
        }[state]
        if expected_reasons is None:
            if len(e["rtisa_reason_codes"]) != 1 or e["rtisa_reason_codes"][0] not in EXCLUDED_REASONS:return False
        elif e["rtisa_reason_codes"] != expected_reasons:return False
        expected = {
            "NOT_APPLICABLE_DELEGATED":[],
            "NOT_APPLICABLE_NOT_ADMITTED":[],
            "DELEGATION_UNRESOLVED":["RTISA_SOURCE_IDENTITY_UNRESOLVED"],
            "DELEGATION_STALE":["RTISA_SOURCE_IDENTITY_STALE"],
        }[state]
        if e["blockers"]!=expected:return False
    elif state=="UPSTREAM_UNRESOLVED":
        if not e["rtisa_reason_codes"] or e["blockers"]!=e["rtisa_reason_codes"]:return False
        freq = e["rtisa_reason_codes"]==["RTISA_SOURCE_FREQUENCY_UNSUPPORTED"]
        if freq:
            if (e["source_kind"]!="RECURRING_INCOME" or e["amount_authority_fingerprint"] is None
                or e["source_version"] is None):return False
            if e["decision_version"] is not None:
                if (not _recurring_current_income(e)
                    or e["price_basis"] not in {"NOMINAL_AT_RETIREMENT_TARGET_DATE","REAL_AT_REFERENCE_DATE"}
                    or e["price_basis_provenance"]!="EXPLICIT_PROFESSIONAL"
                    or (e["price_basis"]=="REAL_AT_REFERENCE_DATE")!=(e["price_reference_date"] is not None)):return False
            elif not safe_missing:return False
        else:
            if not set(e["rtisa_reason_codes"]).issubset(NON_DELEGATION_UNRESOLVED):return False
            if e["amount_authority_fingerprint"] is not None or e["decision_version"] is not None:return False
            if any(e[k] is not None for k in ("income_basis","income_basis_provenance","price_basis",
                                               "price_reference_date","price_basis_provenance")):return False
    return True


def _recurring_current_income(e: Mapping[str, Any]) -> bool:
    return (
        e["income_basis"] in {"GROSS", "NET"}
        and e["income_basis_provenance"] == "UPSTREAM_RECURRING_AMOUNT_BASIS"
    ) or (
        e["income_basis"] == "UNKNOWN"
        and e["income_basis_provenance"] == "MISSING"
    )


def _entry_valid(e: Any) -> bool:
    return _entry_authority_valid(e) and _entry_state_valid(e)

def _collection_shape(value: Any) -> bool:
    if not isinstance(value,Mapping) or set(value)!=COLLECTION_FIELDS:return False
    if value["schema_version"]!="CRTISBA_COLLECTION_RESULT_V1" or not _positive_int(value["client_id"]):return False
    if not _is_sha(value["planning_calculation_input_fingerprint"]):return False
    if value["retirement_target_date"] is not None and not _is_date(value["retirement_target_date"]):return False
    if not _is_sha(value["rtisa_admission_result_fingerprint"]):return False
    if not isinstance(value["source_basis_entries"],list) or not isinstance(value["partitions"],dict):return False
    if set(value["partitions"])!=set(PARTITIONS.values()):return False
    if not all(_sorted_codes(x) for x in value["partitions"].values()):return False
    if not _sorted_codes(value["blockers"]):return False
    if value["basis_readiness_state"] not in {"READY","NOT_READY"} or type(value["basis_ready"]) is not bool:return False
    return _is_sha(value["result_fingerprint"])

def _collection_fingerprint_valid(value: dict) -> bool:
    return value["result_fingerprint"]==_fingerprint({
        "contract":COLLECTION_CONTRACT,
        "result":{k:deepcopy(v) for k,v in value.items() if k!="result_fingerprint"},
    })

def _universe_valid(value: dict) -> bool:
    entries=value["source_basis_entries"]
    ids=[e.get("source_id") if isinstance(e,Mapping) else None for e in entries]
    if any(not _canonical_source_id(x) for x in ids) or ids!=sorted(set(ids)):return False
    seen=[]
    for state,part in PARTITIONS.items():
        expected=[e["source_id"] for e in entries if e.get("decision_state")==state]
        if value["partitions"][part]!=expected:return False
        seen+=value["partitions"][part]
    return sorted(seen)==ids

def _consistent(value: dict) -> bool:
    entries=value["source_basis_entries"]
    if not all(isinstance(x,Mapping) and _sorted_codes(x.get("blockers")) for x in entries):return False
    blockers=sorted({x for e in entries for x in e["blockers"]})
    return (value["blockers"]==blockers and value["basis_readiness_state"]==("READY" if not blockers else "NOT_READY")
            and value["basis_ready"] is (not blockers))

def _basis_reasons(e: dict,target_basis:dict) -> list[str]:
    reasons=[]
    if e["income_basis"]=="UNKNOWN":reasons.append("RTICB_INCOME_BASIS_UNKNOWN")
    elif e["income_basis"] not in (None,target_basis["income_basis"]):reasons.append("RTICB_INCOME_BASIS_MISMATCH")
    if e["price_basis"]=="UNKNOWN":reasons.append("RTICB_PRICE_BASIS_UNKNOWN")
    elif e["price_basis"] is not None:
        if e["price_basis"]!=target_basis["price_basis"]:reasons.append("RTICB_PRICE_BASIS_MISMATCH")
        if e["price_basis"]=="REAL_AT_REFERENCE_DATE":
            if e["price_reference_date"] is None:reasons.append("RTICB_REAL_PRICE_REFERENCE_DATE_MISSING")
            elif target_basis["price_basis"]=="REAL_AT_REFERENCE_DATE" and e["price_reference_date"]!=target_basis["price_reference_date"]:
                reasons.append("RTICB_REAL_PRICE_REFERENCE_DATE_MISMATCH")
    return reasons

def _entry_comparison(e: dict,target_basis:dict,input_fp:str)->dict:
    state=e["decision_state"]
    reasons=[]
    if e["admission_state"]=="EXCLUDED":
        classification="NOT_ADMITTED"
        reasons=["RTICB_SOURCE_NOT_ADMITTED"]
    elif state=="CURRENT":
        reasons=_basis_reasons(e,target_basis)
        classification=("BASIS_UNRESOLVED" if any(x.endswith(("_UNKNOWN","_MISSING")) for x in reasons) else
                        "NORMALIZATION_REQUIRED" if reasons else "DIRECTLY_COMPARABLE")
    else:
        reasons=[BLOCKERS[state]]
        if state in {"MISSING","UNKNOWN"}:
            reasons += [x for x in _basis_reasons(e,target_basis) if x.endswith("_MISMATCH")]
        classification="BASIS_UNRESOLVED"
    out={k:deepcopy(e[k]) for k in ENTRY_FIELDS if k not in {"schema_version","blockers"}}
    out.update({"target_income_basis":target_basis["income_basis"],"target_price_basis":target_basis["price_basis"],
                "target_price_reference_date":target_basis["price_reference_date"],
                "comparison_state":classification,"reason_codes":sorted(set(reasons))})
    out["source_comparison_fingerprint"]=_fingerprint({
        "contract":ENTRY_FINGERPRINT_CONTRACT,"comparison_input_fingerprint":input_fp,
        "entry":deepcopy(out)})
    return out

def _result(request:Mapping[str,Any],target:dict,collection:dict)->dict:
    input_fp=_fingerprint({"contract":INPUT_FINGERPRINT_CONTRACT,"client_id":request["client_id"],
        "planning_calculation_input_fingerprint":request["expected_planning_calculation_input_fingerprint"],
        "retirement_target_date":request["expected_retirement_target_date"],
        "target_result_fingerprint":target["target_result_fingerprint"],
        "target_semantic_fingerprint":target["target_semantic_fingerprint"],
        "crtisba_result_fingerprint":collection["result_fingerprint"]})
    entries=[_entry_comparison(x,target["target"],input_fp) for x in collection["source_basis_entries"]]
    direct=all(x["comparison_state"] in {"DIRECTLY_COMPARABLE","NOT_ADMITTED"} for x in entries)
    blockers=sorted(set(
        (["RTICB_NORMALIZATION_REQUIRED"] if any(e["comparison_state"]=="NORMALIZATION_REQUIRED" for e in entries) else [])
        +(["RTICB_BASIS_UNRESOLVED"] if any(e["comparison_state"]=="BASIS_UNRESOLVED" for e in entries) else [])
    ))
    out={"schema_version":SCHEMA_VERSION,"client_id":request["client_id"],
         "planning_calculation_input_fingerprint":request["expected_planning_calculation_input_fingerprint"],
         "retirement_target_date":request["expected_retirement_target_date"],
         "target_result_fingerprint":target["target_result_fingerprint"],
         "target_semantic_fingerprint":target["target_semantic_fingerprint"],
         "crtisba_result_fingerprint":collection["result_fingerprint"],
         "comparison_input_fingerprint":input_fp,"source_comparisons":entries,
         "classification_state":"COMPLETE","classification_complete":True,
         "direct_comparison_state":"READY" if direct else "NOT_READY",
         "direct_comparison_ready":direct,"blockers":blockers}
    out["comparison_result_fingerprint"]=_fingerprint({"contract":RESULT_FINGERPRINT_CONTRACT,"result":deepcopy(out)})
    return out


SUCCESS_FIELDS = frozenset({
    "schema_version", "client_id", "planning_calculation_input_fingerprint",
    "retirement_target_date", "target_result_fingerprint", "target_semantic_fingerprint",
    "crtisba_result_fingerprint", "comparison_input_fingerprint", "source_comparisons",
    "classification_state", "classification_complete", "direct_comparison_state",
    "direct_comparison_ready", "blockers", "comparison_result_fingerprint",
})
COMPARISON_ENTRY_FIELDS = frozenset({
    "source_id", "source_kind", "source_category", "admission_state", "rtisa_reason_codes",
    "decision_state", "source_version", "source_fingerprint", "amount_authority_fingerprint",
    "decision_version", "decision_fingerprint", "income_basis", "income_basis_provenance",
    "price_basis", "price_reference_date", "price_basis_provenance", "target_income_basis",
    "target_price_basis", "target_price_reference_date", "comparison_state", "reason_codes",
    "source_comparison_fingerprint",
})
FAILURE_FIELDS = frozenset({
    "schema_version", "client_id", "supplied_planning_calculation_input_fingerprint",
    "supplied_retirement_target_date", "observed_target_planning_calculation_input_fingerprint",
    "observed_target_retirement_target_date", "observed_target_result_fingerprint",
    "observed_crtisba_planning_calculation_input_fingerprint",
    "observed_crtisba_retirement_target_date", "observed_crtisba_result_fingerprint",
    "observed_crtisba_failure_fingerprint", "observed_crtisba_failure_stage",
    "observed_crtisba_failure_detail_code", "result_state", "failure_stage",
    "failure_detail_code", "result_fingerprint",
})
FAILURE_CODES = {
    "request_validation": frozenset({
        "RTICB_REQUEST_SCHEMA_INVALID", "RTICB_CLIENT_ID_INVALID",
        "RTICB_EXPECTED_PLANNING_FINGERPRINT_INVALID",
        "RTICB_EXPECTED_RETIREMENT_TARGET_DATE_INVALID",
    }),
    "snapshot_admission": frozenset({
        "RTICB_REQUIRES_FRESH_TRANSACTION", "RTICB_UNSUPPORTED_DATABASE",
    }),
    "target_authority": frozenset({
        "RTICB_TARGET_AUTHORITY_SCHEMA_INVALID", "RTICB_TARGET_AUTHORITY_FINGERPRINT_INVALID",
        "RTICB_TARGET_AUTHORITY_UNAVAILABLE", "RTICB_TARGET_AUTHORITY_NOT_READY",
    }),
    "crtisba_authority": frozenset(set(BLOCKED_RTICB.values()) | {
        "RTICB_CRTISBA_COLLECTION_SCHEMA_INVALID",
        "RTICB_CRTISBA_RESULT_FINGERPRINT_MISMATCH",
    }),
    "cross_authority_identity": frozenset({
        "RTICB_CLIENT_ID_MISMATCH", "RTICB_PLANNING_IDENTITY_MISMATCH",
        "RTICB_RETIREMENT_TARGET_DATE_MISMATCH",
    }),
    "source_universe": frozenset({
        "RTICB_CRTISBA_SOURCE_UNIVERSE_MISMATCH",
        "RTICB_CRTISBA_COLLECTION_CONSISTENCY_INVALID",
        "RTICB_CRTISBA_ENTRY_AUTHORITY_INVALID",
    }),
    "classification": frozenset({"RTICB_CRTISBA_STATE_BASIS_INVALID"}),
}


def _source_entry_from_comparison(entry: Mapping[str, Any]) -> dict[str, Any]:
    state = entry["decision_state"]
    if not isinstance(state, str):
        blockers = ["CRTISBA_DECISION_INVALID"]
    elif state == "CURRENT" or state.startswith("NOT_APPLICABLE"):
        blockers: list[str] = []
    elif state == "UPSTREAM_UNRESOLVED":
        blockers = deepcopy(entry["rtisa_reason_codes"])
    elif state == "DELEGATION_UNRESOLVED":
        blockers = ["RTISA_SOURCE_IDENTITY_UNRESOLVED"]
    elif state == "DELEGATION_STALE":
        blockers = ["RTISA_SOURCE_IDENTITY_STALE"]
    else:
        blockers = [f"CRTISBA_DECISION_{state}"]
    return {
        "schema_version": "CRTISBA_SOURCE_BASIS_ENTRY_V1",
        **{key: deepcopy(entry[key]) for key in ENTRY_FIELDS if key not in {"schema_version", "blockers"}},
        "blockers": blockers,
    }


def _success_result_valid(
    value: Any,
    client_id: int,
    expected_planning_fingerprint: str | None = None,
    expected_retirement_target_date: str | None = None,
) -> bool:
    if not isinstance(value, Mapping) or set(value) != SUCCESS_FIELDS:
        return False
    if (
        value["schema_version"] != SCHEMA_VERSION
        or value["client_id"] != client_id
        or not _positive_int(value["client_id"])
        or not _is_sha(value["planning_calculation_input_fingerprint"])
        or not _is_date(value["retirement_target_date"])
        or any(not _is_sha(value[key]) for key in (
            "target_result_fingerprint", "target_semantic_fingerprint", "crtisba_result_fingerprint",
            "comparison_input_fingerprint", "comparison_result_fingerprint",
        ))
        or value["classification_state"] != "COMPLETE"
        or value["classification_complete"] is not True
        or value["direct_comparison_state"] not in {"READY", "NOT_READY"}
        or type(value["direct_comparison_ready"]) is not bool
        or not _sorted_codes(value["blockers"])
    ):
        return False
    if expected_planning_fingerprint is not None and value["planning_calculation_input_fingerprint"] != expected_planning_fingerprint:
        return False
    if expected_retirement_target_date is not None and value["retirement_target_date"] != expected_retirement_target_date:
        return False
    input_preimage = {
        "contract": INPUT_FINGERPRINT_CONTRACT,
        "client_id": value["client_id"],
        "planning_calculation_input_fingerprint": value["planning_calculation_input_fingerprint"],
        "retirement_target_date": value["retirement_target_date"],
        "target_result_fingerprint": value["target_result_fingerprint"],
        "target_semantic_fingerprint": value["target_semantic_fingerprint"],
        "crtisba_result_fingerprint": value["crtisba_result_fingerprint"],
    }
    if value["comparison_input_fingerprint"] != _fingerprint(input_preimage):
        return False
    comparisons = value["source_comparisons"]
    if not isinstance(comparisons, list):
        return False
    ids: list[str] = []
    common_target_basis: dict[str, Any] | None = None
    for comparison in comparisons:
        if not isinstance(comparison, Mapping) or set(comparison) != COMPARISON_ENTRY_FIELDS:
            return False
        ids.append(comparison.get("source_id"))
        source_entry = _source_entry_from_comparison(comparison)
        if not _entry_valid(source_entry):
            return False
        target_basis = {
            "income_basis": comparison["target_income_basis"],
            "price_basis": comparison["target_price_basis"],
            "price_reference_date": comparison["target_price_reference_date"],
        }
        if (
            target_basis["income_basis"] not in TARGET_INCOME_BASES
            or target_basis["price_basis"] not in TARGET_PRICE_BASES
            or (
                target_basis["price_basis"] == "NOMINAL_AT_RETIREMENT_TARGET_DATE"
                and target_basis["price_reference_date"] is not None
            )
            or (
                target_basis["price_basis"] == "REAL_AT_REFERENCE_DATE"
                and not _is_date(target_basis["price_reference_date"])
            )
        ):
            return False
        if common_target_basis is None:
            common_target_basis = target_basis
        elif target_basis != common_target_basis:
            return False
        if _entry_comparison(source_entry, target_basis, value["comparison_input_fingerprint"]) != comparison:
            return False
    if ids != sorted(set(ids)):
        return False
    direct = all(item["comparison_state"] in {"DIRECTLY_COMPARABLE", "NOT_ADMITTED"} for item in comparisons)
    blockers = sorted(set(
        (["RTICB_NORMALIZATION_REQUIRED"] if any(item["comparison_state"] == "NORMALIZATION_REQUIRED" for item in comparisons) else [])
        + (["RTICB_BASIS_UNRESOLVED"] if any(item["comparison_state"] == "BASIS_UNRESOLVED" for item in comparisons) else [])
    ))
    if (
        value["direct_comparison_ready"] is not direct
        or value["direct_comparison_state"] != ("READY" if direct else "NOT_READY")
        or value["blockers"] != blockers
    ):
        return False
    payload = {key: deepcopy(item) for key, item in value.items() if key != "comparison_result_fingerprint"}
    return value["comparison_result_fingerprint"] == _fingerprint({
        "contract": RESULT_FINGERPRINT_CONTRACT, "result": payload,
    })


def _failure_result_valid(
    value: Any,
    client_id: int,
    expected_planning_fingerprint: str | None = None,
    expected_retirement_target_date: str | None = None,
) -> bool:
    if not isinstance(value, Mapping) or set(value) != FAILURE_FIELDS:
        return False
    stage = value.get("failure_stage")
    code = value.get("failure_detail_code")
    if (
        value.get("schema_version") != SCHEMA_VERSION
        or value.get("result_state") != "block_no_result"
        or value.get("client_id") != client_id
        or not _positive_int(value.get("client_id"))
        or not isinstance(stage, str)
        or not isinstance(code, str)
        or stage not in FAILURE_CODES
        or code not in FAILURE_CODES[stage]
    ):
        return False
    sha_fields = (
        "supplied_planning_calculation_input_fingerprint",
        "observed_target_planning_calculation_input_fingerprint",
        "observed_target_result_fingerprint",
        "observed_crtisba_planning_calculation_input_fingerprint",
        "observed_crtisba_result_fingerprint",
        "observed_crtisba_failure_fingerprint",
    )
    date_fields = (
        "supplied_retirement_target_date", "observed_target_retirement_target_date",
        "observed_crtisba_retirement_target_date",
    )
    if any(value[field] is not None and not _is_sha(value[field]) for field in sha_fields):
        return False
    if any(value[field] is not None and not _is_date(value[field]) for field in date_fields):
        return False
    if expected_planning_fingerprint is not None and value["supplied_planning_calculation_input_fingerprint"] != expected_planning_fingerprint:
        return False
    if expected_retirement_target_date is not None and value["supplied_retirement_target_date"] != expected_retirement_target_date:
        return False
    target_observations = (
        value["observed_target_planning_calculation_input_fingerprint"],
        value["observed_target_retirement_target_date"],
        value["observed_target_result_fingerprint"],
    )
    crtisba_observations = (
        value["observed_crtisba_planning_calculation_input_fingerprint"],
        value["observed_crtisba_retirement_target_date"],
        value["observed_crtisba_result_fingerprint"],
        value["observed_crtisba_failure_fingerprint"],
        value["observed_crtisba_failure_stage"],
        value["observed_crtisba_failure_detail_code"],
    )
    if stage in {"request_validation", "snapshot_admission"} and any(
        item is not None for item in target_observations + crtisba_observations
    ):
        return False
    if stage == "target_authority" and any(item is not None for item in crtisba_observations):
        return False
    if stage in {
        "crtisba_authority", "cross_authority_identity", "source_universe", "classification",
    } and not all(item is not None for item in target_observations):
        return False
    if stage in {"cross_authority_identity", "source_universe", "classification"} and (
        value["observed_crtisba_planning_calculation_input_fingerprint"] is None
        or value["observed_crtisba_result_fingerprint"] is None
    ):
        return False
    if stage in {"source_universe", "classification"} and (
        value["observed_crtisba_retirement_target_date"] is None
    ):
        return False
    blocked_values = (
        value["observed_crtisba_failure_fingerprint"],
        value["observed_crtisba_failure_stage"],
        value["observed_crtisba_failure_detail_code"],
    )
    if any(item is not None for item in blocked_values):
        upstream_stage = value["observed_crtisba_failure_stage"]
        if (
            stage != "crtisba_authority"
            or not _is_sha(value["observed_crtisba_failure_fingerprint"])
            or upstream_stage not in BLOCKED_CODES
            or value["observed_crtisba_failure_detail_code"] != BLOCKED_CODES[upstream_stage]
            or code != BLOCKED_RTICB[upstream_stage]
            or value["observed_crtisba_result_fingerprint"] is not None
            or value["observed_crtisba_retirement_target_date"] is not None
        ):
            return False
    elif value["observed_crtisba_failure_stage"] is not None or value["observed_crtisba_failure_detail_code"] is not None:
        return False
    if not _is_sha(value.get("result_fingerprint")):
        return False
    payload = {key: deepcopy(item) for key, item in value.items() if key != "result_fingerprint"}
    return value["result_fingerprint"] == _fingerprint({
        "contract": FAILURE_FINGERPRINT_CONTRACT, "failure": payload,
    })


def public_result_valid(
    value: Any,
    client_id: int,
    expected_planning_fingerprint: str | None = None,
    expected_retirement_target_date: str | None = None,
) -> bool:
    """Validate the complete RTICB-owned V2 result without inventing consumer semantics."""
    try:
        if isinstance(value, Mapping) and value.get("result_state") == "block_no_result":
            return _failure_result_valid(
                value, client_id, expected_planning_fingerprint, expected_retirement_target_date,
            )
        return _success_result_valid(
            value, client_id, expected_planning_fingerprint, expected_retirement_target_date,
        )
    except RTICBFingerprintConstructionError:
        raise
    except (AttributeError, KeyError, TypeError, ValueError):
        return False

def _rollback_owned_transaction(db:Session)->None:
    connection=None
    try:
        if db.in_transaction():connection=db.connection()
    except Exception:pass
    try:db.rollback()
    except BaseException:
        try:
            if connection is not None:connection.invalidate()
        except BaseException:pass
        try:db.close()
        except BaseException:pass
        raise

def _begin_snapshot(db:Session)->None:
    connection=db.connection()
    dialect=connection.dialect.name
    if dialect=="postgresql":connection.exec_driver_sql("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
    elif dialect=="sqlite":connection.exec_driver_sql("BEGIN")
    else:raise AssertionError("unsupported dialect")
    db.expire_all()

def assess(db:Session,request:Any)->dict:
    error=_request_error(request)
    if error is not None:return _failure(request,"request_validation",error)
    if db.in_transaction() or db.new or db.dirty or db.deleted:
        return _failure(request,"snapshot_admission","RTICB_REQUIRES_FRESH_TRANSACTION")
    if db.get_bind().dialect.name not in {"postgresql","sqlite"}:
        return _failure(request,"snapshot_admission","RTICB_UNSUPPORTED_DATABASE")
    target=collection=None
    owns_transaction=False
    try:
        owns_transaction=True
        _begin_snapshot(db)
        with db.no_autoflush:
            target=target_service.assess_in_snapshot(db,request["client_id"])
            if not _target_schema_valid(target):
                result=_failure(request,"target_authority","RTICB_TARGET_AUTHORITY_SCHEMA_INVALID",target=target)
            elif not _target_fingerprints_valid(target):
                result=_failure(request,"target_authority","RTICB_TARGET_AUTHORITY_FINGERPRINT_INVALID",target=target)
            elif target["authority_state"]=="UNAVAILABLE":
                result=_failure(request,"target_authority","RTICB_TARGET_AUTHORITY_UNAVAILABLE",target=target)
            elif not (target["authority_state"]=="CURRENT" and target["target_readiness_state"]=="READY"
                      and target["target_ready"] is True and target["target"] is not None
                      and target["authority"] is not None
                      and target["authority"]["confirmation_state"]=="CONFIRMED"
                      and not target["blockers"]):
                result=_failure(request,"target_authority","RTICB_TARGET_AUTHORITY_NOT_READY",target=target)
            else:
                collection=crtisba_service.derive_in_snapshot(db,request["client_id"],operation="READ")
                if isinstance(collection,Mapping) and collection.get("schema_version")=="CRTISBA_BLOCK_NO_RESULT_V1":
                    if _blocked_valid(collection,request["client_id"]):
                        result=_failure(request,"crtisba_authority",BLOCKED_RTICB[collection["failure_stage"]],
                                        target=target,crtisba=collection)
                    else:
                        result=_failure(request,"crtisba_authority","RTICB_CRTISBA_COLLECTION_SCHEMA_INVALID",
                                        target=target,crtisba=collection)
                elif not _collection_shape(collection):
                    result=_failure(request,"crtisba_authority","RTICB_CRTISBA_COLLECTION_SCHEMA_INVALID",
                                    target=target,crtisba=collection)
                elif not _collection_fingerprint_valid(collection):
                    result=_failure(request,"crtisba_authority","RTICB_CRTISBA_RESULT_FINGERPRINT_MISMATCH",
                                    target=target,crtisba=collection)
                elif target["client_id"]!=request["client_id"] or collection["client_id"]!=request["client_id"]:
                    result=_failure(request,"cross_authority_identity","RTICB_CLIENT_ID_MISMATCH",target=target,crtisba=collection)
                elif not (target["planning_calculation_input_fingerprint"]==
                          collection["planning_calculation_input_fingerprint"]==
                          request["expected_planning_calculation_input_fingerprint"]):
                    result=_failure(request,"cross_authority_identity","RTICB_PLANNING_IDENTITY_MISMATCH",target=target,crtisba=collection)
                elif not (target["retirement_target_date"]==collection["retirement_target_date"]==
                          request["expected_retirement_target_date"]):
                    result=_failure(request,"cross_authority_identity","RTICB_RETIREMENT_TARGET_DATE_MISMATCH",target=target,crtisba=collection)
                elif not _universe_valid(collection):
                    result=_failure(request,"source_universe","RTICB_CRTISBA_SOURCE_UNIVERSE_MISMATCH",target=target,crtisba=collection)
                elif not _consistent(collection):
                    result=_failure(request,"source_universe","RTICB_CRTISBA_COLLECTION_CONSISTENCY_INVALID",target=target,crtisba=collection)
                elif not all(_entry_authority_valid(e) for e in collection["source_basis_entries"]):
                    result=_failure(request,"source_universe","RTICB_CRTISBA_ENTRY_AUTHORITY_INVALID",target=target,crtisba=collection)
                elif not all(_entry_state_valid(e) for e in collection["source_basis_entries"]):
                    result=_failure(request,"classification","RTICB_CRTISBA_STATE_BASIS_INVALID",target=target,crtisba=collection)
                else:
                    result=_result(request,target,collection)
    except BaseException:
        if owns_transaction:_rollback_owned_transaction(db)
        raise
    _rollback_owned_transaction(db)
    return result
