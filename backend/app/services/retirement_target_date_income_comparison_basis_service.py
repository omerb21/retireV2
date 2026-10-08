"""Canonical comparison-basis authority for retirement target-date income."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import hashlib
import json
import re
import unicodedata
from typing import Any, Mapping

from sqlalchemy.orm import Session

from app.services import retirement_monthly_income_target_service as target_service
from app.services import retirement_target_date_income_source_admission_service as rtisa_service


SCHEMA_VERSION = "CANONICAL_RETIREMENT_TARGET_DATE_INCOME_COMPARISON_BASIS_RESULT_V1"
INPUT_FINGERPRINT_CONTRACT = "CANONICAL_RETIREMENT_TARGET_DATE_INCOME_COMPARISON_BASIS_INPUT_JSON_V1"
ENTRY_FINGERPRINT_CONTRACT = "CANONICAL_RETIREMENT_TARGET_DATE_INCOME_COMPARISON_ENTRY_JSON_V1"
RESULT_FINGERPRINT_CONTRACT = "CANONICAL_RETIREMENT_TARGET_DATE_INCOME_COMPARISON_BASIS_RESULT_JSON_V1"
FAILURE_FINGERPRINT_CONTRACT = "CANONICAL_RETIREMENT_TARGET_DATE_INCOME_COMPARISON_BASIS_FAILURE_JSON_V1"

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
RTISA_RESULT_FIELDS = frozenset({
    "schema_version", "client_id", "planning_calculation_input_fingerprint",
    "retirement_target_date", "pension_portfolio_result_fingerprint", "source_entries",
    "included_source_ids", "excluded_source_ids", "unresolved_source_ids",
    "universe_completeness_state", "admission_readiness_state", "admission_ready",
    "blockers", "admission_result_fingerprint",
})
RTISA_ENTRY_FIELDS = frozenset({
    "source_id", "source_category", "source_authority", "admission_state",
    "native_amount", "monthly_equivalent", "native_income_basis",
    "native_tax_characterization", "native_price_evidence", "applicability",
    "provenance", "upstream_identity", "reason_codes",
})
PRICE_EVIDENCE_FIELDS = frozenset({
    "price_basis", "price_reference_date", "temporal_authority_kind",
    "temporal_origin_date", "annual_rate", "rate_basis",
})
UPSTREAM_IDENTITY_FIELDS = frozenset({
    "source_fingerprint", "pension_source_result_fingerprint", "resolution",
})
RESOLUTION_FIELDS = frozenset({
    "decision_kind", "record_version", "income_fingerprint",
    "canonical_source_id", "canonical_fingerprint",
})

SHA256_RE = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z", re.ASCII)
TIMESTAMP_RE = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}Z\Z",
    re.ASCII,
)
INCOME_BASES = frozenset({"GROSS", "NET", "UNKNOWN"})
TARGET_INCOME_BASES = frozenset({"GROSS", "NET"})
PRICE_BASES = frozenset({
    "NOMINAL_AT_RETIREMENT_TARGET_DATE", "REAL_AT_REFERENCE_DATE", "UNKNOWN",
})
TARGET_PRICE_BASES = frozenset({"NOMINAL_AT_RETIREMENT_TARGET_DATE", "REAL_AT_REFERENCE_DATE"})
ADMISSION_STATES = frozenset({"INCLUDED", "EXCLUDED", "UNRESOLVED"})
RESOLUTION_DECISIONS = frozenset({
    "SAME_CANONICAL_PENSION", "PENSION_NOT_YET_CANONICAL", "MISCLASSIFIED_GENERAL_INCOME",
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


def _sorted_unique_strings(value: Any, *, allow_empty: bool = True) -> bool:
    return (
        isinstance(value, list)
        and (allow_empty or bool(value))
        and all(_canonical_string(item) for item in value)
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


def _failure(
    request: Any,
    stage: str,
    code: str,
    *,
    target: Any = None,
    rtisa: Any = None,
) -> dict:
    supplied = _request_observations(request)
    failure = {
        "schema_version": SCHEMA_VERSION,
        "client_id": supplied["client_id"],
        "supplied_planning_calculation_input_fingerprint": supplied[
            "supplied_planning_calculation_input_fingerprint"
        ],
        "observed_target_planning_calculation_input_fingerprint": _field_observation(
            target, "planning_calculation_input_fingerprint", _is_sha
        ),
        "observed_rtisa_planning_calculation_input_fingerprint": _field_observation(
            rtisa, "planning_calculation_input_fingerprint", _is_sha
        ),
        "supplied_retirement_target_date": supplied["supplied_retirement_target_date"],
        "observed_target_retirement_target_date": _field_observation(
            target, "retirement_target_date", _is_date
        ),
        "observed_rtisa_retirement_target_date": _field_observation(
            rtisa, "retirement_target_date", _is_date
        ),
        "observed_target_result_fingerprint": _field_observation(
            target, "target_result_fingerprint", _is_sha
        ),
        "observed_rtisa_admission_result_fingerprint": _field_observation(
            rtisa, "admission_result_fingerprint", _is_sha
        ),
        "result_state": "block_no_result",
        "failure_stage": stage,
        "failure_detail_code": code,
    }
    return {
        **failure,
        "result_fingerprint": _fingerprint({
            "contract": FAILURE_FINGERPRINT_CONTRACT,
            "failure": failure,
        }),
    }


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


def _nullable_canonical_string(value: Any) -> bool:
    return value is None or _canonical_string(value)


def _target_object_valid(value: Any) -> bool:
    if not isinstance(value, dict) or set(value) != TARGET_FIELDS:
        return False
    reference = value["price_reference_date"]
    price_basis = value["price_basis"]
    return (
        _positive_int(value["client_id"])
        and _is_sha(value["planning_calculation_input_fingerprint"])
        and _is_date(value["retirement_target_date"])
        and _canonical_string(value["monthly_amount"])
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
    return (
        _positive_int(value["record_version"])
        and isinstance(value["source_kind"], str)
        and value["source_kind"] in target_service.SOURCE_KINDS
        and value["confirmation_state"] == "CONFIRMED"
        and _canonical_string(value["confirmation_actor"])
        and isinstance(value["confirmed_at"], str)
        and TIMESTAMP_RE.fullmatch(value["confirmed_at"]) is not None
        and isinstance(value["lifecycle_state"], str)
        and value["lifecycle_state"] in {"CONFIRMED", "STALE"}
    )


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
        and (result["target_semantic_fingerprint"] is None
             or isinstance(result["target_semantic_fingerprint"], str))
        and isinstance(result["target_result_fingerprint"], str)
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


def _rtisa_schema_valid(result: Any) -> bool:
    return (
        isinstance(result, dict)
        and set(result) == RTISA_RESULT_FIELDS
        and result["schema_version"] == rtisa_service.SCHEMA_VERSION
        and _positive_int(result["client_id"])
        and (result["planning_calculation_input_fingerprint"] is None
             or _is_sha(result["planning_calculation_input_fingerprint"]))
        and (result["retirement_target_date"] is None or _is_date(result["retirement_target_date"]))
        and (result["pension_portfolio_result_fingerprint"] is None
             or _is_sha(result["pension_portfolio_result_fingerprint"]))
        and isinstance(result["source_entries"], list)
        and isinstance(result["included_source_ids"], list)
        and isinstance(result["excluded_source_ids"], list)
        and isinstance(result["unresolved_source_ids"], list)
        and isinstance(result["universe_completeness_state"], str)
        and result["universe_completeness_state"] in {"UNAVAILABLE", "PARTIAL", "COMPLETE_EVIDENCED"}
        and isinstance(result["admission_readiness_state"], str)
        and result["admission_readiness_state"] in {"READY", "NOT_READY"}
        and isinstance(result["admission_ready"], bool)
        and _sorted_unique_strings(result["blockers"])
        and isinstance(result["admission_result_fingerprint"], str)
    )


def _rtisa_fingerprint_valid(result: dict) -> bool:
    stored = result["admission_result_fingerprint"]
    if not _is_sha(stored):
        return False
    payload = {key: deepcopy(value) for key, value in result.items() if key != "admission_result_fingerprint"}
    return stored == _fingerprint({"contract": rtisa_service.RESULT_CONTRACT, **payload})


def _resolution_valid(value: Any) -> bool:
    if value is None:
        return True
    if not isinstance(value, dict) or set(value) != RESOLUTION_FIELDS:
        return False
    canonical_id = value["canonical_source_id"]
    canonical_fingerprint = value["canonical_fingerprint"]
    decision = value["decision_kind"]
    if not isinstance(decision, str) or decision not in RESOLUTION_DECISIONS:
        return False
    canonical_pair_valid = (
        canonical_id is None and canonical_fingerprint is None
        if decision == "MISCLASSIFIED_GENERAL_INCOME"
        else _canonical_string(canonical_id) and _is_sha(canonical_fingerprint)
    )
    return (
        _positive_int(value["record_version"])
        and _is_sha(value["income_fingerprint"])
        and canonical_pair_valid
    )


def _upstream_identity_valid(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == UPSTREAM_IDENTITY_FIELDS
        and _is_sha(value["source_fingerprint"])
        and (value["pension_source_result_fingerprint"] is None
             or _is_sha(value["pension_source_result_fingerprint"]))
        and _resolution_valid(value["resolution"])
    )


def _exact_nullable_string_object(value: Any, fields: frozenset[str]) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == fields
        and all(_nullable_canonical_string(item) for item in value.values())
    )


def _exact_string_object(value: Any, fields: frozenset[str]) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == fields
        and all(_canonical_string(item) for item in value.values())
    )


def _entry_non_basis_valid(entry: Any) -> bool:
    if not isinstance(entry, dict) or set(entry) != RTISA_ENTRY_FIELDS:
        return False
    amount = entry["native_amount"]
    monthly = entry["monthly_equivalent"]
    tax = entry["native_tax_characterization"]
    return (
        _canonical_string(entry["source_id"])
        and _canonical_string(entry["source_category"])
        and _canonical_string(entry["source_authority"])
        and isinstance(entry["admission_state"], str)
        and entry["admission_state"] in ADMISSION_STATES
        and (
            amount is None
            or _exact_string_object(amount, frozenset({"amount", "currency", "frequency"}))
        )
        and (
            monthly is None
            or _exact_string_object(monthly, frozenset({"numerator", "denominator"}))
        )
        and isinstance(tax, dict)
        and set(tax) == {"kind", "value"}
        and _canonical_string(tax["kind"])
        and _nullable_canonical_string(tax["value"])
        and isinstance(entry["applicability"], dict)
        and set(entry["applicability"]) == {"start_date", "end_date", "continuation_status", "at_target"}
        and _nullable_canonical_string(entry["applicability"]["start_date"])
        and _nullable_canonical_string(entry["applicability"]["end_date"])
        and _nullable_canonical_string(entry["applicability"]["continuation_status"])
        and _canonical_string(entry["applicability"]["at_target"])
        and isinstance(entry["provenance"], dict)
        and set(entry["provenance"]) == {"origin_kind", "source_status", "verification_state"}
        and _canonical_string(entry["provenance"]["origin_kind"])
        and _nullable_canonical_string(entry["provenance"]["source_status"])
        and _nullable_canonical_string(entry["provenance"]["verification_state"])
        and _upstream_identity_valid(entry["upstream_identity"])
        and _sorted_unique_strings(entry["reason_codes"])
    )


def _source_universe_valid(entries: list[Any]) -> bool:
    if not all(_entry_non_basis_valid(entry) for entry in entries):
        return False
    ids = [entry["source_id"] for entry in entries]
    return ids == sorted(ids) and len(ids) == len(set(ids))


def _coverage_valid(result: dict) -> bool:
    partitions = {
        "INCLUDED": result["included_source_ids"],
        "EXCLUDED": result["excluded_source_ids"],
        "UNRESOLVED": result["unresolved_source_ids"],
    }
    if not all(_sorted_unique_strings(values) for values in partitions.values()):
        return False
    actual = {state: [] for state in partitions}
    for entry in result["source_entries"]:
        actual[entry["admission_state"]].append(entry["source_id"])
    if any(partitions[state] != actual[state] for state in partitions):
        return False
    all_partition_ids = [source_id for values in partitions.values() for source_id in values]
    entry_ids = [entry["source_id"] for entry in result["source_entries"]]
    return (
        len(all_partition_ids) == len(set(all_partition_ids))
        and sorted(all_partition_ids) == entry_ids
        and not partitions["UNRESOLVED"]
    )


def _basis_valid(entry: dict) -> bool:
    income = entry["native_income_basis"]
    price = entry["native_price_evidence"]
    if not isinstance(price, dict) or set(price) != PRICE_EVIDENCE_FIELDS:
        return False
    if not all(_nullable_canonical_string(price[key]) for key in (
        "temporal_authority_kind", "temporal_origin_date", "annual_rate", "rate_basis"
    )):
        return False
    price_basis = price["price_basis"]
    reference = price["price_reference_date"]
    if not isinstance(income, str) or income not in INCOME_BASES:
        return False
    if not isinstance(price_basis, str) or price_basis not in PRICE_BASES:
        return False
    if price_basis in {"NOMINAL_AT_RETIREMENT_TARGET_DATE", "UNKNOWN"}:
        return reference is None
    return reference is None or _is_date(reference)


def _input_fingerprint(request: Mapping[str, Any], target: dict, rtisa: dict) -> str:
    return _fingerprint({
        "contract": INPUT_FINGERPRINT_CONTRACT,
        "client_id": request["client_id"],
        "planning_calculation_input_fingerprint": request[
            "expected_planning_calculation_input_fingerprint"
        ],
        "retirement_target_date": request["expected_retirement_target_date"],
        "target_result_fingerprint": target["target_result_fingerprint"],
        "target_semantic_fingerprint": target["target_semantic_fingerprint"],
        "rtisa_admission_result_fingerprint": rtisa["admission_result_fingerprint"],
    })


def _comparison_entry(entry: dict, target_basis: dict, input_fingerprint: str) -> dict:
    income = entry["native_income_basis"]
    price = entry["native_price_evidence"]["price_basis"]
    reference = entry["native_price_evidence"]["price_reference_date"]
    reasons: list[str] = []
    if entry["admission_state"] == "EXCLUDED":
        state = "NOT_ADMITTED"
        reasons = ["RTICB_SOURCE_NOT_ADMITTED"]
    else:
        if income == "UNKNOWN":
            reasons.append("RTICB_INCOME_BASIS_UNKNOWN")
        elif income != target_basis["income_basis"]:
            reasons.append("RTICB_INCOME_BASIS_MISMATCH")
        if price == "UNKNOWN":
            reasons.append("RTICB_PRICE_BASIS_UNKNOWN")
        elif price == "REAL_AT_REFERENCE_DATE" and reference is None:
            reasons.append("RTICB_REAL_PRICE_REFERENCE_DATE_MISSING")
        if price != "UNKNOWN" and price != target_basis["price_basis"]:
            reasons.append("RTICB_PRICE_BASIS_MISMATCH")
        if (
            price == target_basis["price_basis"] == "REAL_AT_REFERENCE_DATE"
            and reference is not None
            and reference != target_basis["price_reference_date"]
        ):
            reasons.append("RTICB_REAL_PRICE_REFERENCE_DATE_MISMATCH")
        reasons = sorted(set(reasons))
        unresolved = {
            "RTICB_INCOME_BASIS_UNKNOWN",
            "RTICB_PRICE_BASIS_UNKNOWN",
            "RTICB_REAL_PRICE_REFERENCE_DATE_MISSING",
        }
        mismatch = {
            "RTICB_INCOME_BASIS_MISMATCH",
            "RTICB_PRICE_BASIS_MISMATCH",
            "RTICB_REAL_PRICE_REFERENCE_DATE_MISMATCH",
        }
        if unresolved.intersection(reasons):
            state = "BASIS_UNRESOLVED"
        elif mismatch.intersection(reasons):
            state = "NORMALIZATION_REQUIRED"
        else:
            state = "DIRECTLY_COMPARABLE"
    comparison = {
        "source_id": entry["source_id"],
        "rtisa_admission_state": entry["admission_state"],
        "source_upstream_identity": deepcopy(entry["upstream_identity"]),
        "source_income_basis": income,
        "source_price_basis": price,
        "source_price_reference_date": reference,
        "comparison_state": state,
        "reason_codes": reasons,
    }
    comparison["source_comparison_fingerprint"] = _fingerprint({
        "contract": ENTRY_FINGERPRINT_CONTRACT,
        "comparison_input_fingerprint": input_fingerprint,
        "source_comparison": comparison,
    })
    return comparison


def _success(request: Mapping[str, Any], target: dict, rtisa: dict) -> dict:
    input_fingerprint = _input_fingerprint(request, target, rtisa)
    target_basis = {
        "income_basis": target["target"]["income_basis"],
        "price_basis": target["target"]["price_basis"],
        "price_reference_date": target["target"]["price_reference_date"],
    }
    comparisons = [
        _comparison_entry(entry, target_basis, input_fingerprint)
        for entry in rtisa["source_entries"]
    ]
    partitions = {
        "DIRECTLY_COMPARABLE": [],
        "NORMALIZATION_REQUIRED": [],
        "BASIS_UNRESOLVED": [],
        "NOT_ADMITTED": [],
    }
    for comparison in comparisons:
        partitions[comparison["comparison_state"]].append(comparison["source_id"])
    blockers = []
    if partitions["NORMALIZATION_REQUIRED"]:
        blockers.append("RTICB_NORMALIZATION_REQUIRED")
    if partitions["BASIS_UNRESOLVED"]:
        blockers.append("RTICB_BASIS_UNRESOLVED")
    ready = not blockers
    result = {
        "schema_version": SCHEMA_VERSION,
        "client_id": request["client_id"],
        "planning_calculation_input_fingerprint": request[
            "expected_planning_calculation_input_fingerprint"
        ],
        "retirement_target_date": request["expected_retirement_target_date"],
        "target_result_fingerprint": target["target_result_fingerprint"],
        "target_semantic_fingerprint": target["target_semantic_fingerprint"],
        "rtisa_admission_result_fingerprint": rtisa["admission_result_fingerprint"],
        "comparison_input_fingerprint": input_fingerprint,
        "target_basis": target_basis,
        "source_comparisons": comparisons,
        "directly_comparable_source_ids": partitions["DIRECTLY_COMPARABLE"],
        "normalization_required_source_ids": partitions["NORMALIZATION_REQUIRED"],
        "basis_unresolved_source_ids": partitions["BASIS_UNRESOLVED"],
        "not_admitted_source_ids": partitions["NOT_ADMITTED"],
        "classification_state": "COMPLETE",
        "classification_complete": True,
        "direct_comparison_state": "READY" if ready else "NOT_READY",
        "direct_comparison_ready": ready,
        "blockers": sorted(blockers),
    }
    result["comparison_result_fingerprint"] = _fingerprint({
        "contract": RESULT_FINGERPRINT_CONTRACT,
        "result": result,
    })
    return result


def _rollback_owned_transaction(db: Session) -> None:
    connection = None
    try:
        if db.in_transaction():
            connection = db.connection()
    except Exception:
        connection = None
    try:
        db.rollback()
    except BaseException:
        try:
            if connection is not None:
                connection.invalidate()
        except BaseException:
            pass
        try:
            db.close()
        except BaseException:
            pass
        raise


def _begin_snapshot(db: Session) -> None:
    connection = db.connection()
    dialect = connection.dialect.name
    if dialect == "postgresql":
        connection.exec_driver_sql("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
    elif dialect == "sqlite":
        connection.exec_driver_sql("BEGIN")
    else:  # guarded before connection acquisition
        raise AssertionError("unsupported dialect passed snapshot admission")
    db.expire_all()


def assess(db: Session, request: Any) -> dict:
    """Assess direct basis comparability in one caller-supplied read snapshot."""
    request_error = _request_error(request)
    if request_error is not None:
        return _failure(request, "request_validation", request_error)
    if db.in_transaction() or db.new or db.dirty or db.deleted:
        return _failure(request, "snapshot_admission", "RTICB_REQUIRES_FRESH_TRANSACTION")
    dialect = db.get_bind().dialect.name
    if dialect not in {"postgresql", "sqlite"}:
        return _failure(request, "snapshot_admission", "RTICB_UNSUPPORTED_DATABASE")

    target = rtisa = None
    try:
        _begin_snapshot(db)
        with db.no_autoflush:
            target = target_service.assess_in_snapshot(db, request["client_id"])
            if not _target_schema_valid(target):
                result = _failure(
                    request, "target_authority", "RTICB_TARGET_AUTHORITY_SCHEMA_INVALID", target=target
                )
            elif not _target_fingerprints_valid(target):
                result = _failure(
                    request, "target_authority", "RTICB_TARGET_AUTHORITY_FINGERPRINT_INVALID", target=target
                )
            elif target["authority_state"] == "UNAVAILABLE":
                result = _failure(
                    request, "target_authority", "RTICB_TARGET_AUTHORITY_UNAVAILABLE", target=target
                )
            elif not (
                target["authority_state"] == "CURRENT"
                and target["target_readiness_state"] == "READY"
                and target["target_ready"] is True
                and target["target"] is not None
                and target["authority"] is not None
                and target["authority"]["confirmation_state"] == "CONFIRMED"
                and not target["blockers"]
            ):
                result = _failure(
                    request, "target_authority", "RTICB_TARGET_AUTHORITY_NOT_READY", target=target
                )
            else:
                rtisa = rtisa_service.read_in_snapshot(
                    db,
                    request["client_id"],
                    request["expected_planning_calculation_input_fingerprint"],
                )
                if not _rtisa_schema_valid(rtisa):
                    result = _failure(
                        request, "rtisa_authority", "RTICB_RTISA_AUTHORITY_SCHEMA_INVALID",
                        target=target, rtisa=rtisa,
                    )
                elif not _rtisa_fingerprint_valid(rtisa):
                    result = _failure(
                        request, "rtisa_authority", "RTICB_RTISA_AUTHORITY_FINGERPRINT_INVALID",
                        target=target, rtisa=rtisa,
                    )
                elif rtisa["universe_completeness_state"] == "UNAVAILABLE":
                    result = _failure(
                        request, "rtisa_authority", "RTICB_RTISA_AUTHORITY_UNAVAILABLE",
                        target=target, rtisa=rtisa,
                    )
                elif not (
                    rtisa["universe_completeness_state"] == "COMPLETE_EVIDENCED"
                    and rtisa["admission_readiness_state"] == "READY"
                    and rtisa["admission_ready"] is True
                ):
                    result = _failure(
                        request, "rtisa_authority", "RTICB_RTISA_AUTHORITY_NOT_READY",
                        target=target, rtisa=rtisa,
                    )
                elif target["client_id"] != request["client_id"] or rtisa["client_id"] != request["client_id"]:
                    result = _failure(
                        request, "cross_authority_identity", "RTICB_CLIENT_ID_MISMATCH",
                        target=target, rtisa=rtisa,
                    )
                elif not (
                    target["planning_calculation_input_fingerprint"]
                    == rtisa["planning_calculation_input_fingerprint"]
                    == request["expected_planning_calculation_input_fingerprint"]
                ):
                    result = _failure(
                        request, "cross_authority_identity", "RTICB_PLANNING_IDENTITY_MISMATCH",
                        target=target, rtisa=rtisa,
                    )
                elif not (
                    target["retirement_target_date"]
                    == rtisa["retirement_target_date"]
                    == request["expected_retirement_target_date"]
                ):
                    result = _failure(
                        request, "cross_authority_identity", "RTICB_RETIREMENT_TARGET_DATE_MISMATCH",
                        target=target, rtisa=rtisa,
                    )
                elif not _source_universe_valid(rtisa["source_entries"]):
                    result = _failure(
                        request, "source_universe", "RTICB_SOURCE_UNIVERSE_INVALID",
                        target=target, rtisa=rtisa,
                    )
                elif not _coverage_valid(rtisa):
                    result = _failure(
                        request, "source_universe", "RTICB_SOURCE_COVERAGE_MISMATCH",
                        target=target, rtisa=rtisa,
                    )
                elif not all(_basis_valid(entry) for entry in rtisa["source_entries"]):
                    result = _failure(
                        request, "classification", "RTICB_SOURCE_BASIS_EVIDENCE_INVALID",
                        target=target, rtisa=rtisa,
                    )
                else:
                    result = _success(request, target, rtisa)
    except BaseException:
        if db.in_transaction():
            _rollback_owned_transaction(db)
        raise
    _rollback_owned_transaction(db)
    return result
