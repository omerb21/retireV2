"""Read-only assembly of canonical capital and pension target-date resource state."""
from __future__ import annotations

from datetime import date
import hashlib
import re

from app.services import capital_projection_basis_service as capital_basis
from app.services import capital_projection_execution_service as capital_execution
from app.services import pension_target_date_execution_service as pension_execution
from app.services import pension_target_date_portfolio_service as pension_portfolio
from app.services import planning_input_service
from app.services.pension_monthly_basis_service import canonical_bytes


SCHEMA_VERSION = "CANONICAL_RETIREMENT_TARGET_DATE_RESOURCE_STATE_RESULT_V1"
CAPITAL_DOMAIN_CONTRACT = "CANONICAL_RETIREMENT_TARGET_DATE_RESOURCE_STATE_CAPITAL_DOMAIN_RESULT_FINGERPRINT_JSON_V1"
PENSION_DOMAIN_CONTRACT = "CANONICAL_RETIREMENT_TARGET_DATE_RESOURCE_STATE_PENSION_DOMAIN_RESULT_FINGERPRINT_JSON_V1"
EXECUTION_CONTRACT = "CANONICAL_RETIREMENT_TARGET_DATE_RESOURCE_STATE_EXECUTION_FINGERPRINT_JSON_V1"
RESULT_CONTRACT = "CANONICAL_RETIREMENT_TARGET_DATE_RESOURCE_STATE_RESULT_FINGERPRINT_JSON_V1"

SHA256 = re.compile(r"^[0-9a-f]{64}$")

CAPITAL_FIELDS = {
    "contract_version", "numeric_contract_version", "client_id",
    "planning_calculation_input_fingerprint", "projection_basis_admission_fingerprint",
    "covered_source_count", "projected_sources", "aggregate_blockers",
    "execution_ready", "execution_status", "execution_fingerprint",
}
CAPITAL_SOURCE_FIELDS = {
    "source_id", "known_value_amount", "economic_projection_start_date",
    "retirement_target_date", "annual_rate", "return_basis", "price_basis",
    "compounding_convention", "day_count_convention", "source_semantic_fingerprint",
    "projection_timing_context_fingerprint", "projection_basis_decision_fingerprint",
    "projection_basis_source_admission_fingerprint", "elapsed_days",
    "year_fraction_numerator", "year_fraction_denominator", "projection_factor",
    "projected_amount", "calculation_contract_version", "numeric_contract_version",
    "projection_result_fingerprint",
}
CAPITAL_BLOCKERS = {
    "PLANNING_OR_TARGET_NOT_READY", "SOURCE_VALUE_UNRESOLVED", "VALUATION_DATE_MISSING",
    "VALUATION_DATE_AFTER_PLANNING_BASE", "VALUATION_DATE_AFTER_RETIREMENT_TARGET",
    "RATE_MISSING", "RATE_INVALID", "RETURN_BASIS_MISSING_OR_INVALID",
    "PRICE_BASIS_MISSING_OR_INVALID", "SOURCE_STATE_CHANGED_SINCE_DECISION",
    "TIMING_CONTEXT_CHANGED_SINCE_DECISION", "PROJECTION_DECISION_STALE",
    "PROJECTION_SOURCE_NOT_READY", "PROJECTION_BASIS_NOT_READY",
}

PENSION_BASE_FIELDS = {
    "schema_version", "client_id", "result_state", "portfolio_identity_state",
    "portfolio_execution_fingerprint", "portfolio_result_fingerprint",
    "planning_calculation_input_fingerprint", "retirement_target_date", "system_currency",
    "aggregation_contract", "coverage_evidence", "failure_evidence",
    "expected_source_count", "returned_source_count", "source_results",
    "source_entry_fingerprints", "payable_current_source_ids", "future_start_source_ids",
    "unresolved_source_ids", "blocked_source_ids", "total_completeness_state",
    "partial_reason_codes", "portfolio_blockers",
}
PENSION_READY_FIELDS = PENSION_BASE_FIELDS | {
    "aggregate_unquantized_amount", "payable_current_monthly_total",
}
PENSION_COVERAGE_FIELDS = {
    "coverage_check_state", "duplicate_source_ids", "expected_source_ids",
    "missing_source_ids", "returned_source_ids", "unexpected_source_ids",
}
PENSION_FAILURE_FIELDS = {
    "current_planning_calculation_input_fingerprint", "failed_expected_source_id",
    "failure_detail_code", "failure_stage", "observed_source_id",
    "supplied_planning_calculation_input_fingerprint",
}


class CapitalDomainResultFingerprintConstructionError(RuntimeError):
    """Capital domain canonical bytes or SHA-256 construction failed."""


class PensionDomainResultFingerprintConstructionError(RuntimeError):
    """Pension domain canonical bytes or SHA-256 construction failed."""


class ResourceStateResultFingerprintConstructionError(RuntimeError):
    """Resource result canonical bytes or SHA-256 construction failed."""


def _fingerprint(payload: dict) -> str:
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


def _is_sha256(value) -> bool:
    return isinstance(value, str) and SHA256.fullmatch(value) is not None


def _is_int(value) -> bool:
    return type(value) is int


def _is_iso_date(value) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def _sorted_unique_strings(value, *, allowed=None) -> bool:
    return (
        isinstance(value, list)
        and all(isinstance(item, str) and item for item in value)
        and value == sorted(value)
        and len(value) == len(set(value))
        and (allowed is None or set(value) <= allowed)
    )


def _failure(current, supplied, target, domain, stage, detail, expected=None, observed=None):
    return {
        "current_planning_calculation_input_fingerprint": current,
        "supplied_planning_calculation_input_fingerprint": supplied,
        "current_retirement_target_date": target,
        "failed_domain": domain,
        "failure_stage": stage,
        "failure_detail_code": detail,
        "expected_identity": expected,
        "observed_identity": observed,
    }


def _domain_result_binding(domain, domain_kind):
    if domain is None:
        return {
            "domain_kind": domain_kind,
            "domain_state": None,
            "domain_result_fingerprint": None,
        }
    return {
        "domain_kind": domain["domain_name"],
        "domain_state": domain["domain_state"],
        "domain_result_fingerprint": domain["domain_result_fingerprint"],
    }


def _result_payload(result):
    return {
        "contract": RESULT_CONTRACT,
        "schema_version": result["schema_version"],
        "client_id": result["client_id"],
        "result_state": result["result_state"],
        "resource_completeness_state": result["resource_completeness_state"],
        "planning_calculation_input_fingerprint": result["planning_calculation_input_fingerprint"],
        "retirement_target_date": result["retirement_target_date"],
        "domain_results": [
            _domain_result_binding(result["capital_domain"], "capital"),
            _domain_result_binding(result["pension_domain"], "pension"),
        ],
        "resource_state_execution_fingerprint": result["resource_state_execution_fingerprint"],
        "resource_state_reason_codes": result["resource_state_reason_codes"],
        "resource_state_blockers": result["resource_state_blockers"],
        "failure_evidence": result["failure_evidence"],
    }


def _result_fingerprint(result):
    try:
        return _fingerprint(_result_payload(result))
    except Exception as exc:
        raise ResourceStateResultFingerprintConstructionError() from exc


def _fatal(
    client_id,
    current,
    supplied,
    target,
    blocker,
    stage,
    detail,
    *,
    domain=None,
    expected=None,
    observed=None,
    capital_domain=None,
    pension_domain=None,
):
    result = {
        "schema_version": SCHEMA_VERSION,
        "client_id": client_id,
        "result_state": "block_no_result",
        "resource_completeness_state": "unavailable",
        "planning_calculation_input_fingerprint": current,
        "retirement_target_date": target,
        "capital_domain": capital_domain,
        "pension_domain": pension_domain,
        "resource_state_execution_fingerprint": None,
        "resource_state_result_fingerprint": None,
        "resource_state_reason_codes": [],
        "resource_state_blockers": [blocker],
        "failure_evidence": _failure(current, supplied, target, domain, stage, detail, expected, observed),
    }
    result["resource_state_result_fingerprint"] = _result_fingerprint(result)
    return result


def _capital_source_payload(source):
    return {key: source[key] for key in capital_execution.RESULT_FIELDS}


def _capital_execution_payload(result):
    return {
        "calculation_contract_version": capital_execution.CONTRACT,
        "numeric_contract_version": capital_execution.NUMERIC_CONTRACT,
        "planning_calculation_input_fingerprint": result["planning_calculation_input_fingerprint"],
        "projection_basis_admission_fingerprint": result["projection_basis_admission_fingerprint"],
        "execution_status": result["execution_status"],
        "covered_source_count": result["covered_source_count"],
        "sources": [
            {
                "source_id": source["source_id"],
                "projection_result_fingerprint": source["projection_result_fingerprint"],
            }
            for source in result["projected_sources"]
        ],
    }


def _capital_admission_fingerprint(authority):
    return _fingerprint({
        "contract": capital_basis.CONTRACT,
        "planning_calculation_input_fingerprint": authority["planning_calculation_input_fingerprint"],
        "covered_source_count": authority["covered_source_count"],
        "sources": [
            {"source_id": source["source_id"], "admission": source["projection_basis_source_admission_fingerprint"]}
            for source in authority["covered_capital_sources"]
        ],
        "ready": authority["projection_basis_ready"],
        "blockers": authority["aggregate_blockers"],
    })


def _validate_capital_authority(authority, result):
    try:
        sources = authority["covered_capital_sources"]
        ids = [source["source_id"] for source in sources]
        if (
            not isinstance(authority, dict)
            or not isinstance(sources, list)
            or not _is_int(authority["covered_source_count"])
            or authority["covered_source_count"] < 0
            or authority["covered_source_count"] != len(sources)
            or ids != sorted(ids)
            or len(ids) != len(set(ids))
            or not all(isinstance(item, str) and item for item in ids)
            or type(authority["projection_basis_ready"]) is not bool
            or not _sorted_unique_strings(authority["aggregate_blockers"], allowed=CAPITAL_BLOCKERS)
            or not all(_is_sha256(source["projection_basis_source_admission_fingerprint"]) for source in sources)
            or _capital_admission_fingerprint(authority) != result["projection_basis_admission_fingerprint"]
        ):
            return False
    except (KeyError, TypeError, ValueError):
        return False
    return True


def _validate_capital(result, authority):
    if not isinstance(result, dict) or set(result) != CAPITAL_FIELDS:
        return "CAPITAL_RESULT_SCHEMA_INVALID", None, None
    try:
        if (
            result["contract_version"] != capital_execution.CONTRACT
            or result["numeric_contract_version"] != capital_execution.NUMERIC_CONTRACT
            or not _is_int(result["client_id"])
            or not _is_sha256(result["planning_calculation_input_fingerprint"])
            or not _is_sha256(result["projection_basis_admission_fingerprint"])
            or not _is_int(result["covered_source_count"])
            or result["covered_source_count"] < 0
            or not isinstance(result["projected_sources"], list)
            or not _sorted_unique_strings(result["aggregate_blockers"], allowed=CAPITAL_BLOCKERS)
            or type(result["execution_ready"]) is not bool
            or result["execution_status"] not in {
                "AUTHORITATIVE_RESULT", "AUTHORITATIVE_EMPTY_RESULT", "BLOCKED_NO_RESULT",
            }
        ):
            return "CAPITAL_RESULT_SCHEMA_INVALID", None, None
    except KeyError:
        return "CAPITAL_RESULT_SCHEMA_INVALID", None, None

    sources = result["projected_sources"]
    status = result["execution_status"]
    count = result["covered_source_count"]
    ready = result["execution_ready"]
    blockers = result["aggregate_blockers"]
    execution_fp = result["execution_fingerprint"]
    if status == "AUTHORITATIVE_RESULT":
        relationship_valid = ready and count >= 1 and len(sources) == count and not blockers and _is_sha256(execution_fp)
    elif status == "AUTHORITATIVE_EMPTY_RESULT":
        relationship_valid = ready and count == 0 and sources == [] and not blockers and _is_sha256(execution_fp)
    else:
        relationship_valid = not ready and execution_fp is None and sources == [] and bool(blockers)
    if not relationship_valid or not _validate_capital_authority(authority, result):
        return "CAPITAL_RESULT_SCHEMA_INVALID", None, None

    try:
        source_ids = [source["source_id"] for source in sources]
    except (KeyError, TypeError):
        return "CAPITAL_RESULT_SCHEMA_INVALID", None, None
    if (
        not all(isinstance(source, dict) for source in sources)
        or not all(isinstance(source_id, str) and source_id for source_id in source_ids)
        or source_ids != sorted(source_ids)
        or len(source_ids) != len(set(source_ids))
    ):
        return "CAPITAL_RESULT_SCHEMA_INVALID", None, None

    for source in sources:
        if set(source) != CAPITAL_SOURCE_FIELDS:
            return "CAPITAL_RESULT_SCHEMA_INVALID", None, None
        try:
            if (
                source["calculation_contract_version"] != capital_execution.CONTRACT
                or source["numeric_contract_version"] != capital_execution.NUMERIC_CONTRACT
                or not _is_sha256(source["projection_basis_source_admission_fingerprint"])
                or not _is_sha256(source["source_semantic_fingerprint"])
                or not _is_sha256(source["projection_timing_context_fingerprint"])
                or not _is_sha256(source["projection_basis_decision_fingerprint"])
                or not _is_sha256(source["projection_result_fingerprint"])
                or not _is_iso_date(source["economic_projection_start_date"])
                or not _is_iso_date(source["retirement_target_date"])
                or not _is_int(source["elapsed_days"])
                or source["elapsed_days"] < 0
                or not _is_int(source["year_fraction_numerator"])
                or source["year_fraction_numerator"] != source["elapsed_days"] * 4
                or source["year_fraction_denominator"] != 1461
                or source["return_basis"] not in {"NET", "GROSS"}
                or source["price_basis"] not in {"NOMINAL", "REAL"}
                or source["compounding_convention"] != capital_basis.COMPOUNDING
                or source["day_count_convention"] != capital_basis.DAY_COUNT
                or not all(isinstance(source[key], str) for key in (
                    "known_value_amount", "annual_rate", "projection_factor", "projected_amount",
                ))
            ):
                return "CAPITAL_RESULT_SCHEMA_INVALID", None, None
            recomputed = _fingerprint(_capital_source_payload(source))
        except (KeyError, TypeError, ValueError):
            return "CAPITAL_RESULT_SCHEMA_INVALID", None, None
        if recomputed != source["projection_result_fingerprint"]:
            return "CAPITAL_SOURCE_RESULT_FINGERPRINT_MISMATCH", recomputed, source["projection_result_fingerprint"]

    if status != "BLOCKED_NO_RESULT":
        recomputed = _fingerprint(_capital_execution_payload(result))
        if recomputed != execution_fp:
            return "CAPITAL_EXECUTION_FINGERPRINT_MISMATCH", recomputed, execution_fp
    return None, None, None


def _capital_domain_payload(result, authority):
    return {
        "contract": CAPITAL_DOMAIN_CONTRACT,
        "client_id": result["client_id"],
        "planning_calculation_input_fingerprint": result["planning_calculation_input_fingerprint"],
        "retirement_target_date": authority["retirement_target_date"],
        "capital_execution_contract_version": result["contract_version"],
        "numeric_contract_version": result["numeric_contract_version"],
        "projection_basis_admission_fingerprint": result["projection_basis_admission_fingerprint"],
        "execution_status": result["execution_status"],
        "execution_ready": result["execution_ready"],
        "capital_execution_fingerprint": result["execution_fingerprint"],
        "covered_source_count": result["covered_source_count"],
        "aggregate_blockers": result["aggregate_blockers"],
        "projected_source_results": [
            {
                "source_id": source["source_id"],
                "projection_result_fingerprint": source["projection_result_fingerprint"],
            }
            for source in result["projected_sources"]
        ],
    }


def _capital_domain(result, authority):
    ready = result["execution_ready"]
    domain = {
        "domain_name": "capital",
        "domain_state": "complete" if ready else "blocked",
        "client_id": result["client_id"],
        "planning_calculation_input_fingerprint": result["planning_calculation_input_fingerprint"],
        "retirement_target_date": authority["retirement_target_date"],
        "upstream_result_state": result["execution_status"],
        "upstream_execution_fingerprint": result["execution_fingerprint"],
        "projection_basis_admission_fingerprint": result["projection_basis_admission_fingerprint"],
        "covered_source_count": result["covered_source_count"],
        "identity_kind": "execution_fingerprint" if ready else "blocked_result_fingerprint",
        "identity_fingerprint": None,
        "reason_codes": result["aggregate_blockers"],
        "domain_result_fingerprint": None,
    }
    try:
        domain["domain_result_fingerprint"] = _fingerprint(_capital_domain_payload(result, authority))
        domain["identity_fingerprint"] = (
            result["execution_fingerprint"] if ready else domain["domain_result_fingerprint"]
        )
    except Exception as exc:
        raise CapitalDomainResultFingerprintConstructionError() from exc
    return domain


def _pension_result_payload(result):
    if result["result_state"] == "result_ready":
        keys = (
            "schema_version", "client_id", "result_state", "portfolio_identity_state",
            "portfolio_execution_fingerprint", "planning_calculation_input_fingerprint",
            "retirement_target_date", "system_currency", "aggregation_contract",
            "coverage_evidence", "expected_source_count", "returned_source_count",
            "source_entry_fingerprints", "payable_current_source_ids",
            "future_start_source_ids", "unresolved_source_ids", "blocked_source_ids",
            "total_completeness_state", "partial_reason_codes", "portfolio_blockers",
            "aggregate_unquantized_amount", "payable_current_monthly_total", "failure_evidence",
        )
    else:
        keys = (
            "aggregation_contract", "blocked_source_ids", "client_id", "coverage_evidence",
            "expected_source_count", "failure_evidence", "future_start_source_ids",
            "partial_reason_codes", "payable_current_source_ids",
            "planning_calculation_input_fingerprint", "portfolio_blockers",
            "portfolio_execution_fingerprint", "portfolio_identity_state", "result_state",
            "retirement_target_date", "returned_source_count", "schema_version",
            "source_entry_fingerprints", "system_currency", "total_completeness_state",
            "unresolved_source_ids",
        )
    return {"contract": pension_portfolio.RESULT_CONTRACT, **{key: result[key] for key in keys}}


def _pension_source_payload(source):
    common = {
        "applicability_state", "authority_kind", "blockers", "currency",
        "execution_identity_state", "monthly_basis_blockers", "result_state",
        "retirement_target_date", "schema_version", "source_execution_fingerprint",
        "source_id", "temporal_authority_kind", "temporal_blockers", "temporal_origin_date",
    }
    keys = common | ({"elapsed_year_fraction", "final_monthly_amount"}
                     if source.get("result_state") == "result_ready"
                     else {"execution_identity_evidence"})
    return {"contract": pension_execution.RESULT_CONTRACT, **{key: source[key] for key in keys}}


def _pension_execution_payload(result):
    identities = []
    for source in result["source_results"]:
        ready = source["result_state"] == "result_ready"
        identities.append({
            "source_id": source["source_id"],
            "source_identity_fingerprint": (
                source["source_execution_fingerprint"] if ready else source["source_result_fingerprint"]
            ),
            "source_identity_kind": "execution_fingerprint" if ready else "blocked_result_fingerprint",
            "source_result_state": source["result_state"],
        })
    return {
        "aggregation_contract": pension_portfolio.AGGREGATION_CONTRACT,
        "client_id": result["client_id"],
        "contract": pension_portfolio.EXECUTION_CONTRACT,
        "planning_calculation_input_fingerprint": result["planning_calculation_input_fingerprint"],
        "retirement_target_date": result["retirement_target_date"],
        "source_identities": identities,
        "system_currency": pension_portfolio.SYSTEM_CURRENCY,
        "total_completeness_state": result["total_completeness_state"],
    }


def _validate_pension_source(source):
    if not isinstance(source, dict):
        return False
    state = source.get("result_state")
    expected = (
        pension_portfolio.READY_PTE_FIELDS if state == "result_ready"
        else pension_portfolio.BLOCKED_PTE_FIELDS if state == "block_no_result"
        else None
    )
    if expected is None or set(source) != expected or source.get("schema_version") != pension_execution.SCHEMA_VERSION:
        return False
    if not isinstance(source.get("source_id"), str) or not source["source_id"] or not _is_sha256(source.get("source_result_fingerprint")):
        return False
    try:
        if _fingerprint(_pension_source_payload(source)) != source["source_result_fingerprint"]:
            return False
    except (KeyError, TypeError, ValueError):
        return False
    if state == "result_ready":
        return (
            _is_sha256(source.get("source_execution_fingerprint"))
            and source.get("applicability_state") in {"payable_current", "future_start", "unresolved"}
            and isinstance(source.get("unquantized_target_monthly_amount"), str)
        )
    return True


def _validate_pension(result):
    if not isinstance(result, dict):
        return "PENSION_RESULT_SCHEMA_INVALID", None, None
    state = result.get("result_state")
    expected_fields = PENSION_READY_FIELDS if state == "result_ready" else PENSION_BASE_FIELDS if state == "block_no_result" else None
    if expected_fields is None or set(result) != expected_fields:
        return "PENSION_RESULT_SCHEMA_INVALID", None, None
    try:
        coverage = result["coverage_evidence"]
        groups = (
            result["payable_current_source_ids"], result["future_start_source_ids"],
            result["unresolved_source_ids"], result["blocked_source_ids"],
        )
        if (
            result["schema_version"] != pension_portfolio.SCHEMA_VERSION
            or not _is_int(result["client_id"])
            or not _is_sha256(result["planning_calculation_input_fingerprint"])
            or not _is_iso_date(result["retirement_target_date"])
            or result["system_currency"] != pension_portfolio.SYSTEM_CURRENCY
            or result["aggregation_contract"] != pension_portfolio.AGGREGATION_CONTRACT
            or not isinstance(coverage, dict)
            or set(coverage) != PENSION_COVERAGE_FIELDS
            or coverage["coverage_check_state"] not in {"complete", "invalid", "incomplete", "not_evaluated"}
            or not all(_sorted_unique_strings(coverage[key]) for key in PENSION_COVERAGE_FIELDS - {"coverage_check_state"})
            or not _is_int(result["expected_source_count"])
            or not _is_int(result["returned_source_count"])
            or result["expected_source_count"] < 0
            or result["returned_source_count"] < 0
            or not isinstance(result["source_results"], list)
            or not isinstance(result["source_entry_fingerprints"], list)
            or not all(_sorted_unique_strings(group) for group in groups)
            or not _sorted_unique_strings(result["partial_reason_codes"])
            or not _sorted_unique_strings(result["portfolio_blockers"])
            or not _is_sha256(result["portfolio_result_fingerprint"])
        ):
            return "PENSION_RESULT_SCHEMA_INVALID", None, None
    except (KeyError, TypeError):
        return "PENSION_RESULT_SCHEMA_INVALID", None, None

    source_ids = [source.get("source_id") if isinstance(source, dict) else None for source in result["source_results"]]
    if (
        not all(isinstance(source_id, str) and source_id for source_id in source_ids)
        or source_ids != sorted(source_ids)
        or len(source_ids) != len(set(source_ids))
        or not all(_validate_pension_source(source) for source in result["source_results"])
    ):
        return "PENSION_RESULT_SCHEMA_INVALID", None, None
    entry_ids = []
    for entry in result["source_entry_fingerprints"]:
        if not isinstance(entry, dict) or set(entry) != {"source_id", "source_entry_fingerprint"} or not isinstance(entry["source_id"], str) or not _is_sha256(entry["source_entry_fingerprint"]):
            return "PENSION_RESULT_SCHEMA_INVALID", None, None
        entry_ids.append(entry["source_id"])
    if entry_ids != sorted(entry_ids) or len(entry_ids) != len(set(entry_ids)):
        return "PENSION_RESULT_SCHEMA_INVALID", None, None

    if state == "result_ready":
        valid_relationship = (
            result["portfolio_identity_state"] == "complete"
            and _is_sha256(result["portfolio_execution_fingerprint"])
            and result["failure_evidence"] is None
            and result["portfolio_blockers"] == []
            and result["coverage_evidence"]["coverage_check_state"] == "complete"
            and result["expected_source_count"] == len(result["source_results"])
            and result["returned_source_count"] == len(result["source_results"])
            and len(result["source_entry_fingerprints"]) == len(result["source_results"])
            and result["total_completeness_state"] in {"complete", "partial"}
            and isinstance(result["aggregate_unquantized_amount"], str)
            and isinstance(result["payable_current_monthly_total"], str)
        )
    else:
        valid_relationship = (
            result["portfolio_identity_state"] == "incomplete"
            and result["portfolio_execution_fingerprint"] is None
            and isinstance(result["failure_evidence"], dict)
            and set(result["failure_evidence"]) == PENSION_FAILURE_FIELDS
            and bool(result["portfolio_blockers"])
            and result["source_results"] == []
            and result["source_entry_fingerprints"] == []
            and all(group == [] for group in groups)
            and result["total_completeness_state"] == "unavailable"
        )
    if not valid_relationship:
        return "PENSION_RESULT_SCHEMA_INVALID", None, None

    recomputed_result = _fingerprint(_pension_result_payload(result))
    if recomputed_result != result["portfolio_result_fingerprint"]:
        return "PENSION_RESULT_FINGERPRINT_MISMATCH", recomputed_result, result["portfolio_result_fingerprint"]
    if state == "result_ready":
        recomputed_execution = _fingerprint(_pension_execution_payload(result))
        if recomputed_execution != result["portfolio_execution_fingerprint"]:
            return "PENSION_RESULT_FINGERPRINT_MISMATCH", recomputed_execution, result["portfolio_execution_fingerprint"]
    return None, None, None


def _pension_domain_payload(domain):
    return {
        "contract": PENSION_DOMAIN_CONTRACT,
        "domain_kind": domain["domain_name"],
        "domain_state": domain["domain_state"],
        "client_id": domain["client_id"],
        "planning_calculation_input_fingerprint": domain["planning_calculation_input_fingerprint"],
        "retirement_target_date": domain["retirement_target_date"],
        "upstream_result_state": domain["upstream_result_state"],
        "upstream_execution_fingerprint": domain["upstream_execution_fingerprint"],
        "upstream_result_fingerprint": domain["upstream_result_fingerprint"],
        "reason_codes": domain["reason_codes"],
    }


def _pension_domain(result):
    ready = result["result_state"] == "result_ready"
    if not ready:
        state = "blocked"
    elif result["total_completeness_state"] == "partial":
        state = "partial"
    else:
        state = "complete"
    domain = {
        "domain_name": "pension",
        "domain_state": state,
        "client_id": result["client_id"],
        "planning_calculation_input_fingerprint": result["planning_calculation_input_fingerprint"],
        "retirement_target_date": result["retirement_target_date"],
        "upstream_result_state": result["result_state"],
        "upstream_execution_fingerprint": result["portfolio_execution_fingerprint"],
        "upstream_result_fingerprint": result["portfolio_result_fingerprint"],
        "identity_kind": "execution_fingerprint" if ready else "blocked_result_fingerprint",
        "identity_fingerprint": (
            result["portfolio_execution_fingerprint"] if ready else result["portfolio_result_fingerprint"]
        ),
        "reason_codes": (
            result["partial_reason_codes"] if ready else result["portfolio_blockers"]
        ),
        "domain_result_fingerprint": None,
    }
    domain["domain_result_fingerprint"] = result["portfolio_result_fingerprint"]
    return domain


def _execution_payload(
    client_id,
    planning_fingerprint,
    target,
    resource_completeness_state,
    capital_domain,
    pension_domain,
):
    return {
        "contract": EXECUTION_CONTRACT,
        "client_id": client_id,
        "planning_calculation_input_fingerprint": planning_fingerprint,
        "retirement_target_date": target,
        "resource_completeness_state": resource_completeness_state,
        "domains": [
            {
                "domain_kind": capital_domain["domain_name"],
                "domain_state": capital_domain["domain_state"],
                "identity_kind": capital_domain["identity_kind"],
                "identity_fingerprint": capital_domain["identity_fingerprint"],
                "domain_result_fingerprint": capital_domain["domain_result_fingerprint"],
            },
            {
                "domain_kind": pension_domain["domain_name"],
                "domain_state": pension_domain["domain_state"],
                "identity_kind": pension_domain["identity_kind"],
                "identity_fingerprint": pension_domain["identity_fingerprint"],
                "domain_result_fingerprint": pension_domain["domain_result_fingerprint"],
            },
        ],
    }


def _ready(client_id, current, target, capital_domain, pension_domain):
    domain_states = {capital_domain["domain_state"], pension_domain["domain_state"]}
    if "blocked" in domain_states:
        completeness = "blocked"
    elif "partial" in domain_states:
        completeness = "partial"
    else:
        completeness = "complete"
    try:
        execution_fp = _fingerprint(
            _execution_payload(
                client_id,
                current,
                target,
                completeness,
                capital_domain,
                pension_domain,
            )
        )
    except Exception:
        return _fatal(
            client_id, current, current, target, "RESOURCE_STATE_IDENTITY_ERROR",
            "resource_identity", "RESOURCE_EXECUTION_IDENTITY_ASSEMBLY_FAILED",
            capital_domain=capital_domain, pension_domain=pension_domain,
        )
    reasons = []
    for domain in (capital_domain, pension_domain):
        if domain["domain_state"] != "complete":
            reasons.append(
                f"{domain['domain_name'].upper()}_DOMAIN_{domain['domain_state'].upper()}"
            )
    result = {
        "schema_version": SCHEMA_VERSION,
        "client_id": client_id,
        "result_state": "result_ready",
        "resource_completeness_state": completeness,
        "planning_calculation_input_fingerprint": current,
        "retirement_target_date": target,
        "capital_domain": capital_domain,
        "pension_domain": pension_domain,
        "resource_state_execution_fingerprint": execution_fp,
        "resource_state_result_fingerprint": None,
        "resource_state_reason_codes": reasons,
        "resource_state_blockers": [],
        "failure_evidence": None,
    }
    result["resource_state_result_fingerprint"] = _result_fingerprint(result)
    return result


def _supplied_identity(value):
    return value if _is_sha256(value) else None


def _snapshot_identity(snapshot, client_id):
    if not isinstance(snapshot, dict):
        return None
    required = {"contract_version", "client_id", "planning_calculation_input_fingerprint", "retirement_target"}
    if not required <= set(snapshot):
        return None
    if snapshot.get("contract_version") != planning_input_service.CONTRACT:
        return None
    if not _is_int(snapshot.get("client_id")) or snapshot["client_id"] != client_id:
        return None
    current = snapshot.get("planning_calculation_input_fingerprint")
    return current if _is_sha256(current) else None


def read(db, client_id: int, expected_planning_calculation_input_fingerprint: str) -> dict:
    """Assemble one resource state from exactly one current planning snapshot."""
    supplied = _supplied_identity(expected_planning_calculation_input_fingerprint)
    try:
        planning = planning_input_service.read(db, client_id)
    except Exception:
        return _fatal(
            client_id, None, supplied, None, "RESOURCE_STATE_PLANNING_SNAPSHOT_UNAVAILABLE",
            "snapshot_admission", "PLANNING_SNAPSHOT_READ_EXCEPTION",
        )

    current = _snapshot_identity(planning, client_id)
    if current is None:
        return _fatal(
            client_id, None, supplied, None, "RESOURCE_STATE_PLANNING_SNAPSHOT_UNAVAILABLE",
            "snapshot_admission", "PLANNING_SNAPSHOT_SCHEMA_INVALID",
        )
    target_record = planning.get("retirement_target")
    target = target_record.get("retirement_target_date") if isinstance(target_record, dict) else None
    canonical_target = target if _is_iso_date(target) else None
    if supplied != current:
        return _fatal(
            client_id, current, supplied, canonical_target, "RESOURCE_STATE_PLANNING_INPUT_IDENTITY_STALE",
            "snapshot_admission", "EXPECTED_PLANNING_FINGERPRINT_MISMATCH",
            expected=supplied, observed=current,
        )

    if not isinstance(target_record, dict) or target_record.get("retirement_target_ready") is not True or not _is_iso_date(target):
        return _fatal(
            client_id, current, supplied, target if _is_iso_date(target) else None,
            "RESOURCE_STATE_RETIREMENT_TARGET_NOT_READY", "target_admission",
            "RETIREMENT_TARGET_MISSING_OR_NOT_READY",
        )

    try:
        authority = capital_basis.derive(db, client_id, planning)
        capital_result = capital_execution.execute(client_id, planning, authority)
    except Exception:
        return _fatal(
            client_id, current, supplied, target, "RESOURCE_STATE_CAPITAL_EXECUTION_ERROR",
            "capital_execution", "CAPITAL_EXECUTOR_EXCEPTION", domain="capital",
        )

    detail, expected, observed = _validate_capital(capital_result, authority)
    if detail:
        return _fatal(
            client_id, current, supplied, target, "RESOURCE_STATE_CAPITAL_RESULT_INVALID",
            "capital_validation", detail, domain="capital", expected=expected, observed=observed,
        )
    capital_domain = _capital_domain(capital_result, authority)

    capital_checks = (
        (
            "RESOURCE_STATE_CROSS_DOMAIN_CLIENT_ID_MISMATCH",
            "CROSS_DOMAIN_CLIENT_ID_MISMATCH",
            str(client_id),
            str(capital_result["client_id"]),
        ),
        (
            "RESOURCE_STATE_CAPITAL_RESULT_INVALID",
            "CAPITAL_PLANNING_FINGERPRINT_MISMATCH",
            current,
            capital_result["planning_calculation_input_fingerprint"],
        ),
        (
            "RESOURCE_STATE_CAPITAL_RESULT_INVALID",
            "CAPITAL_RETIREMENT_TARGET_DATE_MISMATCH",
            target,
            capital_domain["retirement_target_date"],
        ),
    )
    for mismatch_blocker, mismatch_detail, expected, observed in capital_checks:
        if observed != expected:
            return _fatal(
                client_id, current, supplied, target, mismatch_blocker,
                "cross_domain_validation", mismatch_detail,
                domain="capital", expected=expected, observed=observed, capital_domain=capital_domain,
            )

    try:
        pension_result = pension_portfolio.execute_from_planning_result(planning, client_id, current)
    except Exception:
        return _fatal(
            client_id, current, supplied, target, "RESOURCE_STATE_PENSION_EXECUTION_ERROR",
            "pension_execution", "PENSION_EXECUTOR_EXCEPTION", domain="pension",
            capital_domain=capital_domain,
        )

    detail, expected, observed = _validate_pension(pension_result)
    if detail:
        return _fatal(
            client_id, current, supplied, target, "RESOURCE_STATE_PENSION_RESULT_INVALID",
            "pension_validation", detail, domain="pension", expected=expected, observed=observed,
            capital_domain=capital_domain,
        )
    pension_domain = _pension_domain(pension_result)

    pension_checks = (
        (
            "RESOURCE_STATE_CROSS_DOMAIN_CLIENT_ID_MISMATCH",
            "CROSS_DOMAIN_CLIENT_ID_MISMATCH",
            str(client_id),
            str(pension_result["client_id"]),
        ),
        (
            "RESOURCE_STATE_CROSS_DOMAIN_PLANNING_IDENTITY_MISMATCH",
            "CROSS_DOMAIN_PLANNING_FINGERPRINT_MISMATCH",
            current,
            pension_result["planning_calculation_input_fingerprint"],
        ),
        (
            "RESOURCE_STATE_CROSS_DOMAIN_TARGET_DATE_MISMATCH",
            "CROSS_DOMAIN_RETIREMENT_TARGET_DATE_MISMATCH",
            target,
            pension_result["retirement_target_date"],
        ),
    )
    for mismatch_blocker, mismatch_detail, expected, observed in pension_checks:
        if observed != expected:
            return _fatal(
                client_id, current, supplied, target, mismatch_blocker,
                "cross_domain_validation", mismatch_detail,
                domain="pension", expected=expected, observed=observed,
                capital_domain=capital_domain, pension_domain=pension_domain,
            )

    return _ready(client_id, current, target, capital_domain, pension_domain)
