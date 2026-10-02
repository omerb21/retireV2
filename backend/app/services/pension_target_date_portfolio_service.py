"""Read-only canonical pension target-date result set and ILS aggregation."""
from __future__ import annotations

from collections import Counter
from decimal import (
    Clamped,
    Context,
    Decimal,
    DecimalException,
    DivisionByZero,
    FloatOperation,
    Inexact,
    InvalidOperation,
    Overflow,
    ROUND_HALF_UP,
    Rounded,
    Subnormal,
    Underflow,
    localcontext,
)
import hashlib
import re

from app.services.pension_monthly_basis_service import canonical_bytes
from app.services import pension_target_date_execution_service as pte
from app.services import planning_input_service


SCHEMA_VERSION = "PENSION_TARGET_DATE_PORTFOLIO_RESULT_V1"
SOURCE_ENTRY_CONTRACT = "PENSION_TARGET_DATE_PORTFOLIO_SOURCE_ENTRY_FINGERPRINT_JSON_V1"
EXECUTION_CONTRACT = "PENSION_TARGET_DATE_PORTFOLIO_EXECUTION_FINGERPRINT_JSON_V1"
RESULT_CONTRACT = "PENSION_TARGET_DATE_PORTFOLIO_RESULT_FINGERPRINT_JSON_V1"
AGGREGATION_CONTRACT = "PENSION_TARGET_DATE_PORTFOLIO_AGGREGATION_DECIMAL_V1"
SYSTEM_CURRENCY = "ILS"

SHA256 = re.compile(r"^[0-9a-f]{64}$")
CANONICAL_POSITIVE_DECIMAL = re.compile(r"^(?:0|[1-9][0-9]*)(?:\.[0-9]*[1-9])?$")

READY_PTE_FIELDS = {
    "schema_version", "source_id", "result_state", "execution_identity_state",
    "source_execution_fingerprint", "source_result_fingerprint", "authority_kind",
    "temporal_authority_kind", "temporal_origin_date", "retirement_target_date",
    "currency", "applicability_state", "blockers", "monthly_basis_blockers",
    "temporal_blockers", "execution_identity_evidence", "elapsed_year_fraction",
    "base_amount_representation", "derived_base_monthly_amount", "annual_rate",
    "temporal_factor", "unquantized_target_monthly_amount", "final_monthly_amount",
    "decimal_execution_contract",
}
BLOCKED_PTE_FIELDS = {
    "schema_version", "source_id", "result_state", "execution_identity_state",
    "source_execution_fingerprint", "source_result_fingerprint", "authority_kind",
    "temporal_authority_kind", "temporal_origin_date", "retirement_target_date",
    "currency", "applicability_state", "blockers", "monthly_basis_blockers",
    "temporal_blockers", "execution_identity_evidence",
}


class PortfolioResultFingerprintConstructionError(RuntimeError):
    """Canonical result bytes or SHA-256 construction failed."""


def _fingerprint(payload: dict) -> str:
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


def _result_fingerprint(payload: dict) -> str:
    try:
        return _fingerprint(payload)
    except Exception as exc:  # the public boundary deliberately has no fallback hash
        raise PortfolioResultFingerprintConstructionError() from exc


def decimal_context() -> Context:
    context = Context(
        prec=100,
        rounding=ROUND_HALF_UP,
        Emin=-999999,
        Emax=999999,
        clamp=0,
        capitals=1,
    )
    for signal in context.traps:
        context.traps[signal] = signal in (
            InvalidOperation,
            DivisionByZero,
            Overflow,
            FloatOperation,
        )
    context.traps[Clamped] = False
    context.traps[Inexact] = False
    context.traps[Rounded] = False
    context.traps[Subnormal] = False
    context.traps[Underflow] = False
    context.clear_flags()
    return context


def _coverage(expected_ids, returned_ids, state=None) -> dict:
    expected = sorted(expected_ids)
    returned = sorted(returned_ids)
    expected_counts = Counter(expected)
    returned_counts = Counter(returned)
    missing = sorted(set(expected) - set(returned))
    unexpected = sorted(set(returned) - set(expected))
    duplicates = sorted(source_id for source_id, count in returned_counts.items() if count > 1)
    if state is None:
        state = "complete" if not missing and not unexpected and not duplicates else "invalid"
    return {
        "coverage_check_state": state,
        "duplicate_source_ids": duplicates,
        "expected_source_ids": expected,
        "missing_source_ids": missing,
        "returned_source_ids": returned,
        "unexpected_source_ids": unexpected,
    }


def _failure(current, supplied, stage, detail, failed=None, observed=None) -> dict:
    return {
        "current_planning_calculation_input_fingerprint": current,
        "failed_expected_source_id": failed,
        "failure_detail_code": detail,
        "failure_stage": stage,
        "observed_source_id": observed,
        "supplied_planning_calculation_input_fingerprint": supplied,
    }


def _fatal_result(
    *,
    client_id: int,
    planning_fingerprint,
    supplied_fingerprint,
    retirement_target_date,
    coverage,
    failure,
    blockers,
    expected_count=None,
    returned_count=None,
) -> dict:
    result = {
        "schema_version": SCHEMA_VERSION,
        "client_id": client_id,
        "result_state": "block_no_result",
        "portfolio_identity_state": "incomplete",
        "portfolio_execution_fingerprint": None,
        "portfolio_result_fingerprint": None,
        "planning_calculation_input_fingerprint": planning_fingerprint,
        "retirement_target_date": retirement_target_date,
        "system_currency": SYSTEM_CURRENCY,
        "aggregation_contract": AGGREGATION_CONTRACT,
        "coverage_evidence": coverage,
        "failure_evidence": failure,
        "expected_source_count": len(coverage["expected_source_ids"]) if expected_count is None else expected_count,
        "returned_source_count": len(coverage["returned_source_ids"]) if returned_count is None else returned_count,
        "source_results": [],
        "source_entry_fingerprints": [],
        "payable_current_source_ids": [],
        "future_start_source_ids": [],
        "unresolved_source_ids": [],
        "blocked_source_ids": [],
        "total_completeness_state": "unavailable",
        "partial_reason_codes": [],
        "portfolio_blockers": sorted(set(blockers)),
    }
    result["portfolio_result_fingerprint"] = _result_fingerprint(_fatal_result_payload(result))
    return result


def _fatal_result_payload(result: dict) -> dict:
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
    return {"contract": RESULT_CONTRACT, **{key: result[key] for key in keys}}


def _pte_result_payload(result: dict) -> dict:
    common = {
        "applicability_state", "authority_kind", "blockers", "currency",
        "execution_identity_state", "monthly_basis_blockers", "result_state",
        "retirement_target_date", "schema_version", "source_execution_fingerprint",
        "source_id", "temporal_authority_kind", "temporal_blockers", "temporal_origin_date",
    }
    keys = common | ({"elapsed_year_fraction", "final_monthly_amount"}
                     if result.get("result_state") == "result_ready"
                     else {"execution_identity_evidence"})
    return {"contract": pte.RESULT_CONTRACT, **{key: result[key] for key in keys}}


def _validate_pte_result(result, expected_id):
    if not isinstance(result, dict):
        return "PORTFOLIO_SOURCE_RESULT_SCHEMA_INVALID", "PTE_RESULT_NOT_OBJECT"
    observed = result.get("source_id")
    if observed != expected_id:
        return None, None
    state = result.get("result_state")
    expected_fields = READY_PTE_FIELDS if state == "result_ready" else BLOCKED_PTE_FIELDS if state == "block_no_result" else None
    if result.get("schema_version") != pte.SCHEMA_VERSION or expected_fields is None or set(result) != expected_fields:
        return "PORTFOLIO_SOURCE_RESULT_SCHEMA_INVALID", "PTE_SCHEMA_VERSION_INVALID"
    result_fp = result.get("source_result_fingerprint")
    if not isinstance(result_fp, str) or not SHA256.fullmatch(result_fp):
        return "PORTFOLIO_SOURCE_RESULT_FINGERPRINT_INVALID", "PTE_RESULT_FINGERPRINT_MISMATCH"
    try:
        recomputed = _fingerprint(_pte_result_payload(result))
    except (KeyError, TypeError, ValueError):
        return "PORTFOLIO_SOURCE_RESULT_SCHEMA_INVALID", "PTE_RESULT_SHAPE_INVALID"
    if recomputed != result_fp:
        return "PORTFOLIO_SOURCE_RESULT_FINGERPRINT_INVALID", "PTE_RESULT_FINGERPRINT_MISMATCH"
    if state == "result_ready":
        execution_fp = result.get("source_execution_fingerprint")
        if not isinstance(execution_fp, str) or not SHA256.fullmatch(execution_fp):
            return "PORTFOLIO_SOURCE_RESULT_SCHEMA_INVALID", "PTE_READY_EXECUTION_FINGERPRINT_INVALID"
        if not isinstance(result.get("unquantized_target_monthly_amount"), str):
            return "PORTFOLIO_SOURCE_RESULT_SCHEMA_INVALID", "PTE_UNQUANTIZED_AMOUNT_INVALID"
    return None, None


def _parse_amount(text: str) -> tuple[int, int]:
    if not isinstance(text, str) or not CANONICAL_POSITIVE_DECIMAL.fullmatch(text):
        raise ValueError("canonical positive decimal required")
    integer, dot, fraction = text.partition(".")
    scale = len(fraction) if dot else 0
    coefficient_text = (integer + fraction).lstrip("0") or "0"
    if len(coefficient_text) > 100 or scale > 100:
        raise ValueError("decimal out of bounds")
    coefficient = int(integer + fraction)
    if coefficient <= 0:
        raise ValueError("positive decimal required")
    return coefficient, scale


def _canonical_sum(parts: list[tuple[int, int]]) -> str:
    if not parts:
        return "0"
    max_scale = max(scale for _, scale in parts)
    coefficient = sum(value * 10 ** (max_scale - scale) for value, scale in parts)
    digits = str(coefficient)
    integer_digits = len(digits) - max_scale
    if integer_digits > 97:
        raise ValueError("aggregate integer digits out of bounds")
    if max_scale == 0:
        return digits
    if len(digits) <= max_scale:
        digits = "0" * (max_scale - len(digits) + 1) + digits
    text = digits[:-max_scale] + "." + digits[-max_scale:]
    return text.rstrip("0").rstrip(".")


def _quantize(exact: str) -> str:
    try:
        with localcontext(decimal_context()) as context:
            context.clear_flags()
            return format(Decimal(exact).quantize(Decimal("0.01")), ".2f")
    except (DecimalException, ArithmeticError, ValueError, TypeError) as exc:
        raise ValueError("quantization failed") from exc


def _source_entry(result: dict) -> tuple[dict, tuple[int, int] | None]:
    state = result["result_state"]
    currency = result.get("currency")
    applicability = result.get("applicability_state")
    amount = result.get("unquantized_target_monthly_amount") if state == "result_ready" else None
    aggregation_currency = (SYSTEM_CURRENCY if state == "result_ready" and currency in (None, SYSTEM_CURRENCY)
                            else None)
    aggregation_blockers = (["PENSION_SOURCE_CURRENCY_NOT_ILS"]
                            if state == "result_ready" and currency not in (None, SYSTEM_CURRENCY) else [])
    if state == "block_no_result" or aggregation_blockers:
        group = "blocked"
    elif applicability in ("payable_current", "future_start", "unresolved"):
        group = applicability
    else:
        raise KeyError("unknown applicability")
    contributes = state == "result_ready" and group == "payable_current" and not aggregation_blockers
    parsed = _parse_amount(amount) if contributes else None
    payload = {
        "contract": SOURCE_ENTRY_CONTRACT,
        "source_id": result["source_id"],
        "source_result_state": state,
        "source_execution_fingerprint": result.get("source_execution_fingerprint"),
        "source_result_fingerprint": result["source_result_fingerprint"],
        "source_unquantized_target_monthly_amount": amount,
        "portfolio_group": group,
        "aggregation_currency": aggregation_currency,
        "aggregation_blockers": aggregation_blockers,
        "contributes_to_payable_current_total": contributes,
        "contribution_unquantized_amount": amount if contributes else None,
    }
    return {**payload, "source_entry_fingerprint": _fingerprint(payload)}, parsed


def _ready_result_payload(result: dict) -> dict:
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
    return {"contract": RESULT_CONTRACT, **{key: result[key] for key in keys}}


def _assemble_ready(client_id, planning_fingerprint, supplied_fingerprint, target, expected_ids, raw_results):
    returned_ids = [item.get("source_id") if isinstance(item, dict) else None for item in raw_results]
    coverage = _coverage(expected_ids, [item for item in returned_ids if isinstance(item, str)])
    positional_mismatches = [
        (expected_id, observed_id)
        for expected_id, observed_id in zip(expected_ids, returned_ids)
        if observed_id != expected_id
    ]
    if positional_mismatches and coverage["coverage_check_state"] == "complete":
        coverage["coverage_check_state"] = "invalid"
        coverage["missing_source_ids"] = sorted(expected_id for expected_id, _ in positional_mismatches)
        coverage["unexpected_source_ids"] = sorted(
            observed_id for _, observed_id in positional_mismatches if isinstance(observed_id, str)
        )
    if coverage["coverage_check_state"] != "complete":
        if coverage["duplicate_source_ids"]:
            blocker, detail = "PORTFOLIO_SOURCE_COVERAGE_DUPLICATE", "DUPLICATE_SOURCE_RESULT_PRESENT"
            failed = observed = coverage["duplicate_source_ids"][0]
        elif coverage["missing_source_ids"]:
            blocker, detail = "PORTFOLIO_SOURCE_COVERAGE_MISSING", "EXPECTED_SOURCE_RESULT_MISSING"
            failed = coverage["missing_source_ids"][0]
            observed = coverage["unexpected_source_ids"][0] if positional_mismatches and coverage["unexpected_source_ids"] else None
        else:
            blocker, detail = "PORTFOLIO_SOURCE_COVERAGE_UNEXPECTED", "UNEXPECTED_SOURCE_RESULT_PRESENT"
            failed, observed = None, coverage["unexpected_source_ids"][0]
        return _fatal_result(
            client_id=client_id, planning_fingerprint=planning_fingerprint,
            supplied_fingerprint=supplied_fingerprint, retirement_target_date=target,
            coverage=coverage,
            failure=_failure(planning_fingerprint, supplied_fingerprint, "coverage", detail, failed, observed),
            blockers=[blocker], expected_count=len(expected_ids), returned_count=len(raw_results),
        )

    validated = []
    for expected_id, result in zip(expected_ids, raw_results):
        blocker, detail = _validate_pte_result(result, expected_id)
        if blocker:
            return _fatal_result(
                client_id=client_id, planning_fingerprint=planning_fingerprint,
                supplied_fingerprint=supplied_fingerprint, retirement_target_date=target,
                coverage=coverage,
                failure=_failure(planning_fingerprint, supplied_fingerprint, "source_result_validation", detail,
                                 expected_id, result.get("source_id") if isinstance(result, dict) else None),
                blockers=[blocker],
            )
        validated.append(result)

    entries = []
    parts = []
    try:
        for result in validated:
            entry, parsed = _source_entry(result)
            entries.append(entry)
            if parsed is not None:
                parts.append(parsed)
        exact = _canonical_sum(parts)
        total = _quantize(exact)
    except (KeyError, ValueError, DecimalException):
        source_id = result.get("source_id") if isinstance(result, dict) else None
        return _fatal_result(
            client_id=client_id, planning_fingerprint=planning_fingerprint,
            supplied_fingerprint=supplied_fingerprint, retirement_target_date=target,
            coverage=coverage,
            failure=_failure(planning_fingerprint, supplied_fingerprint, "aggregation",
                             "UNQUANTIZED_DECIMAL_OUT_OF_BOUNDS", source_id, source_id),
            blockers=["PORTFOLIO_AGGREGATION_NUMERIC_ERROR"],
        )

    groups = {name: [] for name in ("payable_current", "future_start", "unresolved", "blocked")}
    partial_reasons = set()
    for entry in entries:
        groups[entry["portfolio_group"]].append(entry["source_id"])
        if entry["portfolio_group"] == "unresolved":
            partial_reasons.add("UNRESOLVED_APPLICABILITY_PRESENT")
        if entry["portfolio_group"] == "blocked":
            partial_reasons.add("BLOCKED_SOURCE_PRESENT")
        if entry["aggregation_blockers"]:
            partial_reasons.add("EXPLICIT_NON_ILS_SOURCE_PRESENT")
    completeness = "partial" if partial_reasons else "complete"
    source_identities = []
    for result in validated:
        ready = result["result_state"] == "result_ready"
        source_identities.append({
            "source_id": result["source_id"],
            "source_identity_fingerprint": result["source_execution_fingerprint"] if ready else result["source_result_fingerprint"],
            "source_identity_kind": "execution_fingerprint" if ready else "blocked_result_fingerprint",
            "source_result_state": result["result_state"],
        })
    execution_payload = {
        "aggregation_contract": AGGREGATION_CONTRACT,
        "client_id": client_id,
        "contract": EXECUTION_CONTRACT,
        "planning_calculation_input_fingerprint": planning_fingerprint,
        "retirement_target_date": target,
        "source_identities": source_identities,
        "system_currency": SYSTEM_CURRENCY,
        "total_completeness_state": completeness,
    }
    try:
        execution_fp = _fingerprint(execution_payload)
    except Exception:
        return _fatal_result(
            client_id=client_id, planning_fingerprint=planning_fingerprint,
            supplied_fingerprint=supplied_fingerprint, retirement_target_date=target,
            coverage=coverage,
            failure=_failure(planning_fingerprint, supplied_fingerprint, "portfolio_identity",
                             "PORTFOLIO_EXECUTION_IDENTITY_ASSEMBLY_FAILED"),
            blockers=["PORTFOLIO_IDENTITY_ERROR"],
        )
    result = {
        "schema_version": SCHEMA_VERSION,
        "client_id": client_id,
        "result_state": "result_ready",
        "portfolio_identity_state": "complete",
        "portfolio_execution_fingerprint": execution_fp,
        "portfolio_result_fingerprint": None,
        "planning_calculation_input_fingerprint": planning_fingerprint,
        "retirement_target_date": target,
        "system_currency": SYSTEM_CURRENCY,
        "aggregation_contract": AGGREGATION_CONTRACT,
        "coverage_evidence": coverage,
        "failure_evidence": None,
        "expected_source_count": len(expected_ids),
        "returned_source_count": len(raw_results),
        "source_results": validated,
        "source_entry_fingerprints": [
            {"source_id": entry["source_id"], "source_entry_fingerprint": entry["source_entry_fingerprint"]}
            for entry in entries
        ],
        "payable_current_source_ids": sorted(groups["payable_current"]),
        "future_start_source_ids": sorted(groups["future_start"]),
        "unresolved_source_ids": sorted(groups["unresolved"]),
        "blocked_source_ids": sorted(groups["blocked"]),
        "total_completeness_state": completeness,
        "partial_reason_codes": sorted(partial_reasons),
        "portfolio_blockers": [],
        "aggregate_unquantized_amount": exact,
        "payable_current_monthly_total": total,
    }
    result["portfolio_result_fingerprint"] = _result_fingerprint(_ready_result_payload(result))
    return result


def read(db, client_id: int, expected_planning_calculation_input_fingerprint: str) -> dict:
    """Read one planning snapshot and execute its complete pension source universe."""
    planning = planning_input_service.read(db, client_id)
    current = planning.get("planning_calculation_input_fingerprint")
    target_record = planning.get("retirement_target") or {}
    target = target_record.get("retirement_target_date")
    empty_coverage = _coverage([], [], "not_evaluated")
    if not isinstance(expected_planning_calculation_input_fingerprint, str) \
            or not SHA256.fullmatch(expected_planning_calculation_input_fingerprint) \
            or not isinstance(current, str) or not SHA256.fullmatch(current) \
            or expected_planning_calculation_input_fingerprint != current:
        return _fatal_result(
            client_id=client_id, planning_fingerprint=current if isinstance(current, str) and SHA256.fullmatch(current) else None,
            supplied_fingerprint=(expected_planning_calculation_input_fingerprint
                                  if isinstance(expected_planning_calculation_input_fingerprint, str)
                                  and SHA256.fullmatch(expected_planning_calculation_input_fingerprint) else None),
            retirement_target_date=target,
            coverage=empty_coverage,
            failure=_failure(current if isinstance(current, str) and SHA256.fullmatch(current) else None,
                             expected_planning_calculation_input_fingerprint
                             if isinstance(expected_planning_calculation_input_fingerprint, str)
                             and SHA256.fullmatch(expected_planning_calculation_input_fingerprint) else None,
                             "snapshot_admission", "EXPECTED_PLANNING_FINGERPRINT_MISMATCH"),
            blockers=["PORTFOLIO_PLANNING_INPUT_IDENTITY_STALE"],
        )
    if target_record.get("retirement_target_ready") is not True or not isinstance(target, str):
        return _fatal_result(
            client_id=client_id, planning_fingerprint=current,
            supplied_fingerprint=expected_planning_calculation_input_fingerprint,
            retirement_target_date=target if isinstance(target, str) else None,
            coverage=empty_coverage,
            failure=_failure(current, expected_planning_calculation_input_fingerprint,
                             "target_admission", "RETIREMENT_TARGET_MISSING_OR_NOT_READY"),
            blockers=["PORTFOLIO_RETIREMENT_TARGET_NOT_READY"],
        )
    sources = planning.get("pension_inputs")
    if not isinstance(sources, list):
        sources = []
    ids = [source.get("source_id") if isinstance(source, dict) else None for source in sources]
    valid_ids = [source_id for source_id in ids if isinstance(source_id, str) and source_id]
    duplicate_ids = sorted(source_id for source_id, count in Counter(valid_ids).items() if count > 1)
    if len(valid_ids) != len(ids) or duplicate_ids:
        failed = duplicate_ids[0] if duplicate_ids else None
        coverage = _coverage(valid_ids, [], "invalid")
        if duplicate_ids:
            coverage["duplicate_source_ids"] = duplicate_ids
            coverage["missing_source_ids"] = []
        return _fatal_result(
            client_id=client_id, planning_fingerprint=current,
            supplied_fingerprint=expected_planning_calculation_input_fingerprint,
            retirement_target_date=target, coverage=coverage,
            failure=_failure(current, expected_planning_calculation_input_fingerprint,
                             "source_universe", "DUPLICATE_EXPECTED_SOURCE_ID" if failed else "EXPECTED_SOURCE_ID_INVALID",
                             failed),
            blockers=["PORTFOLIO_SOURCE_UNIVERSE_INVALID"], expected_count=len(ids), returned_count=0,
        )
    source_by_id = {source["source_id"]: source for source in sources}
    expected_ids = sorted(valid_ids)
    raw_results = []
    for source_id in expected_ids:
        source = source_by_id[source_id]
        monthly = source.get("monthly_amount_basis") or {}
        temporal = source.get("temporal_authority") or {}
        try:
            returned = pte.execute_from_planning_result(
                planning,
                source_id,
                supplied_planning_calculation_input_fingerprint=current,
                supplied_monthly_basis_semantic_fingerprint=monthly.get("base_amount_semantic_fingerprint"),
                supplied_monthly_basis_source_fingerprint=monthly.get("base_amount_source_fingerprint"),
                supplied_temporal_semantic_fingerprint=temporal.get("temporal_semantic_fingerprint"),
                supplied_temporal_source_fingerprint=temporal.get("temporal_source_fingerprint"),
            )
        except Exception:
            returned_ids = [item.get("source_id") for item in raw_results if isinstance(item, dict)]
            coverage = _coverage(expected_ids, returned_ids, "incomplete")
            return _fatal_result(
                client_id=client_id, planning_fingerprint=current,
                supplied_fingerprint=expected_planning_calculation_input_fingerprint,
                retirement_target_date=target, coverage=coverage,
                failure=_failure(current, expected_planning_calculation_input_fingerprint,
                                 "source_execution", "PTE_EXECUTOR_EXCEPTION", source_id),
                blockers=["PORTFOLIO_SOURCE_EXECUTION_ERROR"],
                expected_count=len(expected_ids), returned_count=len(raw_results),
            )
        if returned is not None:
            raw_results.append(returned)
    return _assemble_ready(
        client_id, current, expected_planning_calculation_input_fingerprint,
        target, expected_ids, raw_results,
    )
