"""Canonical target-date income-source admission, derived in one read snapshot."""
from __future__ import annotations

from datetime import date
from decimal import Decimal, DecimalException
import hashlib
import json
import re
from typing import Any

from sqlalchemy import or_, select

from app.models.planning_input_decision import PensionIncomeResolution
from app.models.retirement_facts import RecurringIncome
from app.services import pension_target_date_portfolio_service as portfolio_service
from app.services import planning_input_service
from app.services.pension_product_service import PensionProductError
from app.services.professional_source_snapshot_service import record, serialize


SCHEMA_VERSION = "CANONICAL_RETIREMENT_TARGET_DATE_INCOME_SOURCE_ADMISSION_RESULT_V1"
RESULT_CONTRACT = "CANONICAL_RETIREMENT_TARGET_DATE_INCOME_SOURCE_ADMISSION_RESULT_FINGERPRINT_JSON_V1"
SHA256 = re.compile(r"^[0-9a-f]{64}$")

SOURCE_CATEGORIES = {
    "employment": "EMPLOYMENT", "rental": "RENTAL", "business": "BUSINESS",
    "benefit": "BENEFIT", "other": "OTHER",
}
SOURCE_STATUSES = {
    "not recorded", "client stated", "planner entered", "external statement",
    "employer information", "institution information", "government or tax source", "other",
}
VERIFICATION_STATES = {
    "collected - not yet reviewed", "reviewed", "verified", "partially verified",
    "verification not applicable",
}
FREQUENCIES = {"monthly": ("MONTHLY", "1"), "quarterly": ("QUARTERLY", "3"), "annual": ("ANNUAL", "12")}
DECISIONS = {"SAME_CANONICAL_PENSION", "PENSION_NOT_YET_CANONICAL", "MISCLASSIFIED_GENERAL_INCOME"}
TECHNICAL_FATALS = {
    (("PORTFOLIO_SOURCE_EXECUTION_ERROR",), "source_execution", "PTE_EXECUTOR_EXCEPTION"),
    (("PORTFOLIO_IDENTITY_ERROR",), "portfolio_identity", "PORTFOLIO_EXECUTION_IDENTITY_ASSEMBLY_FAILED"),
}
FATAL_PORTFOLIO_BLOCKERS = {
    "PORTFOLIO_AGGREGATION_NUMERIC_ERROR", "PORTFOLIO_IDENTITY_ERROR",
    "PORTFOLIO_PLANNING_INPUT_IDENTITY_STALE", "PORTFOLIO_RETIREMENT_TARGET_NOT_READY",
    "PORTFOLIO_SOURCE_COVERAGE_DUPLICATE", "PORTFOLIO_SOURCE_COVERAGE_MISSING",
    "PORTFOLIO_SOURCE_COVERAGE_UNEXPECTED", "PORTFOLIO_SOURCE_EXECUTION_ERROR",
    "PORTFOLIO_SOURCE_RESULT_FINGERPRINT_INVALID", "PORTFOLIO_SOURCE_RESULT_SCHEMA_INVALID",
    "PORTFOLIO_SOURCE_UNIVERSE_INVALID",
}

FATAL_PORTFOLIO_SIGNATURES = {
    ("PORTFOLIO_PLANNING_INPUT_IDENTITY_STALE", "snapshot_admission", "EXPECTED_PLANNING_FINGERPRINT_MISMATCH"),
    ("PORTFOLIO_RETIREMENT_TARGET_NOT_READY", "target_admission", "RETIREMENT_TARGET_MISSING_OR_NOT_READY"),
    ("PORTFOLIO_SOURCE_UNIVERSE_INVALID", "source_universe", "SOURCE_UNIVERSE_CONTAINER_INVALID"),
    ("PORTFOLIO_SOURCE_UNIVERSE_INVALID", "source_universe", "DUPLICATE_EXPECTED_SOURCE_ID"),
    ("PORTFOLIO_SOURCE_UNIVERSE_INVALID", "source_universe", "EXPECTED_SOURCE_ID_INVALID"),
    ("PORTFOLIO_SOURCE_COVERAGE_DUPLICATE", "coverage", "DUPLICATE_SOURCE_RESULT_PRESENT"),
    ("PORTFOLIO_SOURCE_COVERAGE_MISSING", "coverage", "EXPECTED_SOURCE_RESULT_MISSING"),
    ("PORTFOLIO_SOURCE_COVERAGE_UNEXPECTED", "coverage", "UNEXPECTED_SOURCE_RESULT_PRESENT"),
    ("PORTFOLIO_SOURCE_EXECUTION_ERROR", "source_execution", "PTE_EXECUTOR_EXCEPTION"),
    ("PORTFOLIO_SOURCE_RESULT_SCHEMA_INVALID", "source_result_validation", "PTE_RESULT_NOT_OBJECT"),
    ("PORTFOLIO_SOURCE_RESULT_SCHEMA_INVALID", "source_result_validation", "PTE_SCHEMA_VERSION_INVALID"),
    ("PORTFOLIO_SOURCE_RESULT_SCHEMA_INVALID", "source_result_validation", "PTE_RESULT_SHAPE_INVALID"),
    ("PORTFOLIO_SOURCE_RESULT_SCHEMA_INVALID", "source_result_validation", "PTE_APPLICABILITY_STATE_INVALID"),
    ("PORTFOLIO_SOURCE_RESULT_SCHEMA_INVALID", "source_result_validation", "PTE_READY_EXECUTION_FINGERPRINT_INVALID"),
    ("PORTFOLIO_SOURCE_RESULT_SCHEMA_INVALID", "source_result_validation", "PTE_UNQUANTIZED_AMOUNT_INVALID"),
    ("PORTFOLIO_SOURCE_RESULT_FINGERPRINT_INVALID", "source_result_validation", "PTE_RESULT_FINGERPRINT_MISMATCH"),
    ("PORTFOLIO_AGGREGATION_NUMERIC_ERROR", "aggregation", "UNQUANTIZED_DECIMAL_OUT_OF_BOUNDS"),
    ("PORTFOLIO_IDENTITY_ERROR", "portfolio_identity", "PORTFOLIO_EXECUTION_IDENTITY_ASSEMBLY_FAILED"),
}


class RetirementTargetIncomeSourceAdmissionError(ValueError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class RetirementTargetIncomeSourceAdmissionTechnicalError(RuntimeError):
    def __init__(self, blocker: str, stage: str, detail: str):
        super().__init__(blocker, stage, detail)
        self.blocker = blocker
        self.stage = stage
        self.detail = detail


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _fingerprint(value: dict) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _result_fingerprint(result: dict) -> str:
    return _fingerprint({"contract": RESULT_CONTRACT, **result})


def _empty_result(client_id: int, planning_fp, target, blocker: str) -> dict:
    result = {
        "schema_version": SCHEMA_VERSION,
        "client_id": client_id,
        "planning_calculation_input_fingerprint": planning_fp,
        "retirement_target_date": target,
        "pension_portfolio_result_fingerprint": None,
        "source_entries": [],
        "included_source_ids": [],
        "excluded_source_ids": [],
        "unresolved_source_ids": [],
        "universe_completeness_state": "UNAVAILABLE",
        "admission_readiness_state": "NOT_READY",
        "admission_ready": False,
        "blockers": [blocker],
    }
    return {**result, "admission_result_fingerprint": _result_fingerprint(result)}


def _begin_read(db) -> None:
    if db.in_transaction() or db.new or db.dirty or db.deleted:
        raise RetirementTargetIncomeSourceAdmissionError("RTISA_REQUIRES_FRESH_TRANSACTION")
    dialect = db.get_bind().dialect.name
    connection = db.connection()
    if dialect == "postgresql":
        connection.exec_driver_sql("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
    elif dialect == "sqlite":
        connection.exec_driver_sql("BEGIN")
    else:
        db.rollback()
        raise RetirementTargetIncomeSourceAdmissionError("RTISA_UNSUPPORTED_DATABASE")
    db.expire_all()


def _money(value) -> str | None:
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        return None
    text = format(value, "f")
    integer, _, fraction = text.partition(".")
    if len(integer.lstrip("0")) > 12 or len(fraction) > 2:
        return None
    return format(value, ".2f")


def _date_value(value) -> str | None:
    return value.isoformat() if isinstance(value, date) else None


def _is_iso_date(value) -> bool:
    try:
        return isinstance(value, str) and date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def _resolution_value(row: PensionIncomeResolution | None) -> dict | None:
    if row is None or row.decision_kind not in DECISIONS or not isinstance(row.version, int) or row.version <= 0:
        return None
    if not isinstance(row.income_fingerprint, str) or not SHA256.fullmatch(row.income_fingerprint):
        return None
    if (row.canonical_source_id is None) != (row.canonical_fingerprint is None):
        return None
    if row.canonical_source_id is not None and (
        not isinstance(row.canonical_source_id, str) or not row.canonical_source_id
        or not isinstance(row.canonical_fingerprint, str) or not SHA256.fullmatch(row.canonical_fingerprint)
    ):
        return None
    return {
        "decision_kind": row.decision_kind,
        "record_version": row.version,
        "income_fingerprint": row.income_fingerprint,
        "canonical_source_id": row.canonical_source_id,
        "canonical_fingerprint": row.canonical_fingerprint,
    }


def _base_entry(*, source_id: str, category, authority: str, origin: str, source_fp: str,
                source_status=None, verification_state=None, resolution=None) -> dict:
    return {
        "source_id": source_id,
        "source_category": category,
        "source_authority": authority,
        "admission_state": "UNRESOLVED",
        "native_amount": None,
        "monthly_equivalent": None,
        "native_income_basis": "UNKNOWN",
        "native_tax_characterization": {"kind": "UNKNOWN", "value": None},
        "native_price_evidence": {
            "price_basis": "UNKNOWN", "price_reference_date": None,
            "temporal_authority_kind": None, "temporal_origin_date": None,
            "annual_rate": None, "rate_basis": None,
        },
        "applicability": {"start_date": None, "end_date": None, "continuation_status": None, "at_target": "UNRESOLVED"},
        "provenance": {"origin_kind": origin, "source_status": source_status, "verification_state": verification_state},
        "upstream_identity": {
            "source_fingerprint": source_fp,
            "pension_source_result_fingerprint": None,
            "resolution": resolution,
        },
        "reason_codes": [],
    }


READY_PORTFOLIO_FIELDS = {
    "schema_version", "client_id", "result_state", "portfolio_identity_state",
    "portfolio_execution_fingerprint", "portfolio_result_fingerprint",
    "planning_calculation_input_fingerprint", "retirement_target_date", "system_currency",
    "aggregation_contract", "coverage_evidence", "failure_evidence", "expected_source_count",
    "returned_source_count", "source_results", "source_entry_fingerprints",
    "payable_current_source_ids", "future_start_source_ids", "unresolved_source_ids",
    "blocked_source_ids", "total_completeness_state", "partial_reason_codes",
    "portfolio_blockers", "aggregate_unquantized_amount", "payable_current_monthly_total",
}
FATAL_PORTFOLIO_FIELDS = READY_PORTFOLIO_FIELDS - {"aggregate_unquantized_amount", "payable_current_monthly_total"}


def _portfolio_is_valid(result: Any, client_id: int, planning: dict, target: str) -> bool:
    planning_fp = planning["planning_calculation_input_fingerprint"]
    pension_inputs = planning.get("pension_inputs")
    raw_expected_ids = ([source.get("source_id") if isinstance(source, dict) else None
                         for source in pension_inputs]
                        if isinstance(pension_inputs, list) else [])
    expected_ids = [source_id for source_id in raw_expected_ids
                    if isinstance(source_id, str) and source_id]
    if not isinstance(result, dict) or result.get("schema_version") != portfolio_service.SCHEMA_VERSION:
        return False
    if isinstance(result.get("client_id"), bool) or not isinstance(result.get("client_id"), int) \
            or result.get("client_id") != client_id \
            or result.get("planning_calculation_input_fingerprint") != planning_fp \
            or result.get("retirement_target_date") != target:
        return False
    value = result.get("portfolio_result_fingerprint")
    if not isinstance(value, str) or not portfolio_service.SHA256.fullmatch(value):
        return False
    try:
        state = result.get("result_state")
        if state == "result_ready":
            if set(result) != READY_PORTFOLIO_FIELDS or result.get("failure_evidence") is not None:
                return False
            rebuilt = portfolio_service._assemble_ready(
                client_id, planning_fp, planning_fp, target, expected_ids, result.get("source_results")
            )
            return rebuilt == result
        if state != "block_no_result" or set(result) != FATAL_PORTFOLIO_FIELDS:
            return False
        coverage = result.get("coverage_evidence")
        coverage_fields = {
            "coverage_check_state", "duplicate_source_ids", "expected_source_ids", "missing_source_ids",
            "returned_source_ids", "unexpected_source_ids",
        }
        failure = result.get("failure_evidence")
        failure_fields = {
            "current_planning_calculation_input_fingerprint", "failed_expected_source_id",
            "failure_detail_code", "failure_stage", "observed_source_id",
            "supplied_planning_calculation_input_fingerprint",
        }
        if not isinstance(coverage, dict) or set(coverage) != coverage_fields \
                or coverage.get("expected_source_ids") != sorted(expected_ids):
            return False
        expected_count = result.get("expected_source_count")
        returned_count = result.get("returned_source_count")
        if isinstance(expected_count, bool) or not isinstance(expected_count, int) \
                or isinstance(returned_count, bool) or not isinstance(returned_count, int) \
                or expected_count < 0 or returned_count < 0:
            return False
        list_keys = (
            "duplicate_source_ids", "expected_source_ids", "missing_source_ids",
            "returned_source_ids", "unexpected_source_ids",
        )
        if any(not isinstance(coverage.get(key), list) for key in list_keys) \
                or any(any(not isinstance(item, str) or not item for item in coverage[key]) for key in list_keys):
            return False
        expected = coverage["expected_source_ids"]
        returned = coverage["returned_source_ids"]
        missing = coverage["missing_source_ids"]
        unexpected = coverage["unexpected_source_ids"]
        duplicates = coverage["duplicate_source_ids"]
        if expected != sorted(expected) or returned != sorted(returned) \
                or missing != sorted(set(missing)) or unexpected != sorted(set(unexpected)) \
                or duplicates != sorted(set(duplicates)):
            return False
        returned_counts = {source_id: returned.count(source_id) for source_id in set(returned)}
        set_missing = sorted(set(expected) - set(returned))
        set_unexpected = sorted(set(returned) - set(expected))
        derived_duplicates = sorted(source_id for source_id, count in returned_counts.items() if count > 1)
        positional_permutation = (
            coverage.get("coverage_check_state") == "invalid"
            and returned_count == len(returned) == len(expected)
            and returned == expected
            and not duplicates
            and len(missing) >= 2
            and missing == unexpected
            and set(missing).issubset(set(expected))
        )
        ordinary_coverage = (
            missing == set_missing
            and unexpected == set_unexpected
            and duplicates == derived_duplicates
        )
        source_universe_exception = (
            isinstance(failure, dict)
            and failure.get("failure_stage") == "source_universe"
            and failure.get("failure_detail_code") in {
                "DUPLICATE_EXPECTED_SOURCE_ID", "EXPECTED_SOURCE_ID_INVALID",
            }
        )
        if not ordinary_coverage and not positional_permutation and not source_universe_exception:
            return False
        coverage_state = coverage.get("coverage_check_state")
        if coverage_state not in {"complete", "incomplete", "invalid", "not_evaluated"}:
            return False
        discrepancies = bool(missing or unexpected or duplicates)
        if coverage_state == "complete" and (discrepancies or expected != returned):
            return False
        if coverage_state == "incomplete" and not missing:
            return False
        if coverage_state == "invalid" and not discrepancies:
            return False
        if coverage_state == "not_evaluated" and any((expected, returned, missing, unexpected, duplicates)):
            return False
        blockers = result.get("portfolio_blockers")
        if not isinstance(blockers, list) or len(blockers) != 1 or blockers != sorted(set(blockers)) \
                or blockers[0] not in FATAL_PORTFOLIO_BLOCKERS:
            return False
        if not isinstance(failure, dict) or set(failure) != failure_fields \
                or failure.get("current_planning_calculation_input_fingerprint") != planning_fp \
                or failure.get("supplied_planning_calculation_input_fingerprint") != planning_fp \
                or not isinstance(failure.get("failure_stage"), str) or not failure["failure_stage"] \
                or not isinstance(failure.get("failure_detail_code"), str) or not failure["failure_detail_code"]:
            return False
        failed = failure.get("failed_expected_source_id")
        observed = failure.get("observed_source_id")
        if (failed is not None and (not isinstance(failed, str) or not failed or failed not in expected)) \
                or (observed is not None and (not isinstance(observed, str) or not observed or observed not in returned)):
            return False
        signature = (blockers[0], failure["failure_stage"], failure["failure_detail_code"])
        if signature not in FATAL_PORTFOLIO_SIGNATURES:
            return False
        stage = failure["failure_stage"]
        detail = failure["failure_detail_code"]
        blocker = blockers[0]
        if stage != "source_universe" and len(expected) != len(set(expected)):
            return False
        if stage == "snapshot_admission":
            if expected_count != 0 or returned_count != 0 or coverage_state != "not_evaluated" \
                    or any((expected, returned, missing, unexpected, duplicates)) \
                    or failed is not None or observed is not None:
                return False
        elif stage == "target_admission":
            if expected_count != 0 or returned_count != 0 or coverage_state != "not_evaluated" \
                    or any((expected, returned, missing, unexpected, duplicates)) \
                    or failed is not None or observed is not None:
                return False
        elif stage == "source_universe":
            if returned_count != 0 or returned or observed is not None or coverage_state != "invalid":
                return False
            if detail == "SOURCE_UNIVERSE_CONTAINER_INVALID":
                if expected_count != 0 or any((expected, missing, unexpected, duplicates)) or failed is not None:
                    return False
            elif detail == "DUPLICATE_EXPECTED_SOURCE_ID":
                if expected_count < 2 or not duplicates or failed != duplicates[0] \
                        or missing or unexpected or expected != sorted(expected):
                    return False
            elif detail == "EXPECTED_SOURCE_ID_INVALID":
                if expected_count <= len(expected) or failed is not None or duplicates or unexpected:
                    return False
        elif stage == "coverage":
            if expected_count != len(expected_ids) or returned_count < len(returned):
                return False
            if blockers[0] == "PORTFOLIO_SOURCE_COVERAGE_DUPLICATE":
                if not duplicates or failed != duplicates[0] or observed != duplicates[0]:
                    return False
            elif blockers[0] == "PORTFOLIO_SOURCE_COVERAGE_MISSING":
                expected_observed = unexpected[0] if unexpected else None
                if not missing or failed != missing[0] or observed != expected_observed:
                    return False
            elif not unexpected or missing or duplicates or failed is not None or observed != unexpected[0]:
                return False
        elif stage == "source_execution":
            if expected_count != len(expected_ids) or returned_count != len(returned) \
                    or coverage_state != "incomplete" or not ordinary_coverage \
                    or not missing or failed not in missing \
                    or returned_count > expected.index(failed) or observed is not None:
                return False
        elif stage in {"source_result_validation", "aggregation"}:
            if expected_count != len(expected_ids) or returned_count != len(returned) \
                    or coverage_state != "complete" or not ordinary_coverage \
                    or failed not in expected or observed != failed:
                return False
        elif stage == "portfolio_identity":
            if expected_count != len(expected_ids) or returned_count != len(returned) \
                    or coverage_state != "complete" or not ordinary_coverage \
                    or failed is not None or observed is not None:
                return False
        if result.get("portfolio_identity_state") != "incomplete" \
                or result.get("portfolio_execution_fingerprint") is not None \
                or result.get("system_currency") != portfolio_service.SYSTEM_CURRENCY \
                or result.get("aggregation_contract") != portfolio_service.AGGREGATION_CONTRACT \
                or result.get("source_results") != [] or result.get("source_entry_fingerprints") != [] \
                or result.get("payable_current_source_ids") != [] or result.get("future_start_source_ids") != [] \
                or result.get("unresolved_source_ids") != [] or result.get("blocked_source_ids") != [] \
                or result.get("total_completeness_state") != "unavailable" \
                or result.get("partial_reason_codes") != []:
            return False
        payload = portfolio_service._fatal_result_payload(result)
        return portfolio_service._result_fingerprint(payload) == value
    except (KeyError, TypeError, ValueError):
        return False


def _discard_failed_attempt(db) -> None:
    """Rollback, and invalidate the guarded connection if rollback itself fails."""
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


def _is_technical_fatal(result: dict) -> tuple[str, str, str] | None:
    if result.get("result_state") != "block_no_result":
        return None
    failure = result.get("failure_evidence")
    blockers = result.get("portfolio_blockers")
    if not isinstance(failure, dict) or not isinstance(blockers, list):
        return None
    signature = (tuple(blockers), failure.get("failure_stage"), failure.get("failure_detail_code"))
    if signature in TECHNICAL_FATALS:
        return blockers[0], signature[1], signature[2]
    return None


def _pension_entry(source: dict, pte: dict | None, group: str | None) -> dict:
    source_id = source["source_id"]
    entry = _base_entry(
        source_id=source_id, category="PENSION", authority="CANONICAL_PENSION_TARGET_DATE",
        origin="conversion" if source_id.startswith("conversion:") else "manual",
        source_fp=source["source_fingerprint"],
    )
    start = source.get("pension_start_date")
    entry["applicability"]["start_date"] = start if isinstance(start, str) else None
    tax = source.get("tax_treatment")
    if isinstance(tax, str) and tax:
        entry["native_tax_characterization"] = {"kind": "SOURCE_LABEL", "value": tax}
    if pte is None:
        entry["reason_codes"] = ["RTISA_PENSION_AUTHORITY_UNAVAILABLE"]
        return entry
    entry["upstream_identity"]["pension_source_result_fingerprint"] = pte.get("source_result_fingerprint")
    entry["native_price_evidence"].update({
        "temporal_authority_kind": pte.get("temporal_authority_kind"),
        "temporal_origin_date": pte.get("temporal_origin_date"),
        "annual_rate": pte.get("annual_rate"),
        "rate_basis": "ANNUAL_EFFECTIVE" if pte.get("temporal_authority_kind") == "fixed_manual" else None,
    })
    if pte.get("result_state") == "result_ready":
        final = pte.get("final_monthly_amount")
        exact = pte.get("unquantized_target_monthly_amount")
        entry["native_amount"] = {"amount": final, "currency": pte.get("currency") or "ILS", "frequency": "MONTHLY"}
        entry["monthly_equivalent"] = {"numerator": exact, "denominator": "1"}
    if group == "payable_current" and pte.get("currency") in (None, "ILS") and pte.get("result_state") == "result_ready":
        entry["admission_state"] = "INCLUDED"
        entry["applicability"]["at_target"] = "ACTIVE"
    elif group == "future_start" and pte.get("result_state") == "result_ready":
        entry["admission_state"] = "EXCLUDED"
        entry["applicability"]["at_target"] = "FUTURE"
        entry["reason_codes"] = ["RTISA_FUTURE_SOURCE"]
    else:
        entry["reason_codes"] = ["RTISA_PENSION_SOURCE_NOT_READY"]
        entry["applicability"]["at_target"] = "UNRESOLVED"
    if pte.get("result_state") == "result_ready" and pte.get("currency") not in (None, "ILS"):
        entry["admission_state"] = "UNRESOLVED"
        entry["reason_codes"] = ["RTISA_SOURCE_CURRENCY_UNSUPPORTED"]
    if group == "unresolved":
        entry["reason_codes"] = sorted(set(entry["reason_codes"] + ["RTISA_PENSION_APPLICABILITY_UNRESOLVED"]))
    return entry


def _recurring_entry(row: RecurringIncome, resolution: PensionIncomeResolution | None, pension_map: dict[str, dict], target: date) -> dict:
    source_id = f"income:{row.id}"
    row_record = record(row)
    source_fp = planning_input_service.fingerprint(row_record)
    resolution_data = _resolution_value(resolution)
    pension_alias = row.income_category == "pension" or resolution is not None and resolution.decision_kind != "MISCLASSIFIED_GENERAL_INCOME"
    category = ("PENSION_REPRESENTATION" if pension_alias else
                SOURCE_CATEGORIES.get(row.income_category) if isinstance(row.income_category, str) else None)
    entry = _base_entry(
        source_id=source_id, category=category, authority="CANONICAL_PLANNING_RECURRING_INCOME",
        origin="recurring_income", source_fp=source_fp, source_status=row.source_status,
        verification_state=row.verification_state, resolution=resolution_data,
    )
    reasons: list[str] = []
    start, end = row.start_date, row.end_date
    entry["applicability"].update({
        "start_date": _date_value(start), "end_date": _date_value(end),
        "continuation_status": (row.continuation_status if isinstance(row.continuation_status, str)
                                and row.continuation_status in {"ongoing", "known end date", "unknown"} else None),
    })

    if pension_alias:
        valid = bool(
            resolution_data and resolution.client_id == row.client_id and resolution.income_fingerprint == source_fp
            and resolution.decision_kind in {"SAME_CANONICAL_PENSION", "PENSION_NOT_YET_CANONICAL"}
            and resolution.canonical_source_id in pension_map
            and resolution.canonical_fingerprint == pension_map[resolution.canonical_source_id].get("source_fingerprint")
            and (resolution.decision_kind != "PENSION_NOT_YET_CANONICAL" or resolution.canonical_source_id.startswith("manual:"))
        )
        if valid:
            entry["admission_state"] = "EXCLUDED"
            entry["applicability"]["at_target"] = "DELEGATED_TO_CANONICAL"
            entry["reason_codes"] = ["RTISA_SAME_CANONICAL_PENSION"]
        else:
            entry["reason_codes"] = ["RTISA_SOURCE_IDENTITY_STALE" if resolution else "RTISA_SOURCE_IDENTITY_UNRESOLVED"]
        return entry

    if resolution is not None:
        valid_misclassified = (
            resolution_data is not None and resolution.client_id == row.client_id
            and resolution.decision_kind == "MISCLASSIFIED_GENERAL_INCOME"
            and resolution.income_fingerprint == source_fp and resolution.canonical_source_id is None
            and resolution.canonical_fingerprint is None and row.income_category != "pension"
        )
        if not valid_misclassified:
            reasons.append("RTISA_SOURCE_IDENTITY_STALE")

    if category is None or not isinstance(row.description, str):
        reasons.append("RTISA_SOURCE_RECORD_INVALID")
    if not isinstance(row.source_status, str) or row.source_status not in SOURCE_STATUSES \
            or not isinstance(row.verification_state, str) or row.verification_state not in VERIFICATION_STATES:
        reasons.append("RTISA_SOURCE_RECORD_INVALID")
    else:
        if row.source_status == "not recorded": reasons.append("RTISA_SOURCE_AUTHORITY_NOT_RECORDED")
        if row.verification_state == "collected - not yet reviewed": reasons.append("RTISA_SOURCE_REVIEW_INCOMPLETE")

    amount = _money(row.amount)
    frequency = FREQUENCIES.get(row.frequency) if isinstance(row.frequency, str) else None
    if amount is None:
        reasons.append("RTISA_SOURCE_AMOUNT_INVALID")
    if frequency is None:
        reasons.append("RTISA_SOURCE_FREQUENCY_UNSUPPORTED")
    if amount is not None and frequency is not None:
        entry["native_amount"] = {"amount": amount, "currency": "ILS", "frequency": frequency[0]}
        entry["monthly_equivalent"] = {"numerator": amount, "denominator": frequency[1]}
    if row.amount_basis == "gross": entry["native_income_basis"] = "GROSS"
    elif row.amount_basis == "net": entry["native_income_basis"] = "NET"
    elif row.amount_basis == "unknown": reasons.append("RTISA_NATIVE_INCOME_BASIS_UNKNOWN")
    else: reasons.append("RTISA_SOURCE_RECORD_INVALID")

    if not isinstance(start, date): reasons.append("RTISA_SOURCE_START_DATE_MISSING")
    continuation_valid = isinstance(row.continuation_status, str) \
        and row.continuation_status in {"ongoing", "known end date", "unknown"}
    if not continuation_valid: reasons.append("RTISA_SOURCE_RECORD_INVALID")
    elif row.continuation_status == "unknown": reasons.append("RTISA_SOURCE_CONTINUATION_UNRESOLVED")
    elif row.continuation_status == "known end date" and not isinstance(end, date): reasons.append("RTISA_SOURCE_END_DATE_MISSING")
    if isinstance(start, date) and isinstance(end, date) and end < start:
        reasons.append("RTISA_SOURCE_DATE_RANGE_INVALID")

    if reasons:
        entry["reason_codes"] = sorted(set(reasons))
        return entry
    if start > target:
        entry["admission_state"] = "EXCLUDED"; entry["applicability"]["at_target"] = "FUTURE"
        entry["reason_codes"] = ["RTISA_FUTURE_SOURCE"]
    elif isinstance(end, date) and end < target:
        entry["admission_state"] = "EXCLUDED"; entry["applicability"]["at_target"] = "ENDED"
        entry["reason_codes"] = ["RTISA_ENDED_SOURCE"]
    else:
        entry["admission_state"] = "INCLUDED"; entry["applicability"]["at_target"] = "ACTIVE"
    return entry


def _apply_collisions(entries: list[dict], rows: list[RecurringIncome], planning: dict) -> None:
    groups: list[list[str]] = []
    for warning in planning.get("warnings", []):
        if isinstance(warning, dict) and warning.get("code") == "potential_duplicate_warning" and isinstance(warning.get("source_ids"), list):
            groups.append(warning["source_ids"])
    economic: dict[tuple, list[str]] = {}
    for row in rows:
        if row.frequency == "monthly" and row.amount_basis == "gross" and _money(row.amount) is not None \
                and isinstance(row.description, str):
            key = (row.income_category, row.description.strip().casefold(), _money(row.amount), row.start_date, row.end_date)
            economic.setdefault(key, []).append(f"income:{row.id}")
    groups.extend(ids for ids in economic.values() if len(ids) > 1)
    by_id = {entry["source_id"]: entry for entry in entries}
    for group in groups:
        participating = [by_id[source_id] for source_id in sorted(set(group))
                         if source_id in by_id and by_id[source_id]["admission_state"] == "INCLUDED"]
        if len(participating) > 1:
            for entry in participating:
                entry["admission_state"] = "UNRESOLVED"
                entry["reason_codes"] = sorted(set(entry["reason_codes"] + [
                    "RTISA_SOURCE_IDENTITY_AMBIGUOUS", "RTISA_DUPLICATE_COLLISION_UNRESOLVED",
                ]))


def _assemble(client_id: int, planning: dict, portfolio: dict, rows: list[RecurringIncome], resolutions: list[PensionIncomeResolution]) -> dict:
    planning_fp = planning["planning_calculation_input_fingerprint"]
    target_text = planning["retirement_target"]["retirement_target_date"]
    target = date.fromisoformat(target_text)
    pension_map = {source["source_id"]: source for source in planning["pension_inputs"]}
    resolution_map = {row.income_id: row for row in resolutions}
    entries: list[dict] = []
    portfolio_fp = portfolio["portfolio_result_fingerprint"]
    partial = portfolio.get("result_state") != "result_ready" or portfolio.get("total_completeness_state") != "complete"

    if portfolio.get("result_state") == "result_ready":
        source_results = {item["source_id"]: item for item in portfolio["source_results"]}
        group_map = {}
        for group, key in (("payable_current", "payable_current_source_ids"), ("future_start", "future_start_source_ids"),
                           ("unresolved", "unresolved_source_ids"), ("blocked", "blocked_source_ids")):
            group_map.update({source_id: group for source_id in portfolio[key]})
        for source_id in sorted(pension_map):
            entries.append(_pension_entry(pension_map[source_id], source_results.get(source_id), group_map.get(source_id)))
    else:
        for source_id in sorted(pension_map):
            entries.append(_pension_entry(pension_map[source_id], None, None))

    for row in rows:
        entries.append(_recurring_entry(row, resolution_map.get(row.id), pension_map, target))
    _apply_collisions(entries, rows, planning)
    entries.sort(key=lambda item: item["source_id"])
    if len({entry["source_id"] for entry in entries}) != len(entries):
        return _empty_result(client_id, planning_fp, target_text, "RTISA_SOURCE_UNIVERSE_INVALID")
    unresolved = [entry for entry in entries if entry["admission_state"] == "UNRESOLVED"]
    partial = partial or bool(unresolved)
    blockers = sorted(set(code for entry in unresolved for code in entry["reason_codes"])
                      | ({"RTISA_SOURCE_UNIVERSE_INCOMPLETE"} if partial else set()))
    result = {
        "schema_version": SCHEMA_VERSION,
        "client_id": client_id,
        "planning_calculation_input_fingerprint": planning_fp,
        "retirement_target_date": target_text,
        "pension_portfolio_result_fingerprint": portfolio_fp,
        "source_entries": entries,
        "included_source_ids": sorted(entry["source_id"] for entry in entries if entry["admission_state"] == "INCLUDED"),
        "excluded_source_ids": sorted(entry["source_id"] for entry in entries if entry["admission_state"] == "EXCLUDED"),
        "unresolved_source_ids": sorted(entry["source_id"] for entry in entries if entry["admission_state"] == "UNRESOLVED"),
        "universe_completeness_state": "PARTIAL" if partial else "COMPLETE_EVIDENCED",
        "admission_readiness_state": "NOT_READY" if partial else "READY",
        "admission_ready": not partial,
        "blockers": blockers,
    }
    return {**result, "admission_result_fingerprint": _result_fingerprint(result)}


def read(db, client_id: int, expected_planning_calculation_input_fingerprint: str) -> dict:
    """Derive the closed candidate universe under one fresh guarded snapshot."""
    if isinstance(client_id, bool) or not isinstance(client_id, int) or client_id <= 0:
        raise RetirementTargetIncomeSourceAdmissionError("RTISA_CLIENT_ID_INVALID")
    if not isinstance(expected_planning_calculation_input_fingerprint, str) \
            or not SHA256.fullmatch(expected_planning_calculation_input_fingerprint):
        raise RetirementTargetIncomeSourceAdmissionError("RTISA_EXPECTED_PLANNING_FINGERPRINT_INVALID")
    try:
        _begin_read(db)
        with db.no_autoflush:
            try:
                planning = planning_input_service.derive(db, client_id)
            except PensionProductError:
                result = _empty_result(client_id, None, None, "RTISA_PLANNING_CONTEXT_UNAVAILABLE")
                db.commit()
                return result
            planning_fp = planning.get("planning_calculation_input_fingerprint")
            target_record = planning.get("retirement_target")
            target = target_record.get("retirement_target_date") if isinstance(target_record, dict) else None
            if planning.get("client_id") != client_id or not isinstance(planning_fp, str) or not SHA256.fullmatch(planning_fp):
                result = _empty_result(client_id, None, None, "RTISA_PLANNING_CONTEXT_INVALID")
            elif planning_fp != expected_planning_calculation_input_fingerprint:
                result = _empty_result(client_id, planning_fp, target if isinstance(target, str) else None, "RTISA_PLANNING_IDENTITY_STALE")
            elif not isinstance(target_record, dict) or target_record.get("retirement_target_ready") is not True \
                    or not _is_iso_date(target):
                result = _empty_result(client_id, planning_fp, target if isinstance(target, str) else None, "RTISA_RETIREMENT_TARGET_NOT_READY")
            elif not isinstance(planning.get("pension_inputs"), list) \
                    or any(not isinstance(source, dict) or not isinstance(source.get("source_id"), str) or not source["source_id"]
                           or not isinstance(source.get("source_fingerprint"), str) or not SHA256.fullmatch(source["source_fingerprint"])
                           for source in planning["pension_inputs"]) \
                    or len({source["source_id"] for source in planning["pension_inputs"]}) != len(planning["pension_inputs"]):
                result = _empty_result(client_id, planning_fp, target, "RTISA_SOURCE_UNIVERSE_INVALID")
            else:
                portfolio = portfolio_service.execute_from_planning_result(
                    planning, client_id, expected_planning_calculation_input_fingerprint
                )
                if not _portfolio_is_valid(portfolio, client_id, planning, target):
                    result = _empty_result(client_id, planning_fp, target, "RTISA_PENSION_RESULT_INVALID")
                else:
                    technical = _is_technical_fatal(portfolio)
                    if technical:
                        raise RetirementTargetIncomeSourceAdmissionTechnicalError(*technical)
                    rows = list(db.scalars(select(RecurringIncome).where(
                        RecurringIncome.client_id == client_id, RecurringIncome.lifecycle_status == "current"
                    ).order_by(RecurringIncome.id)))
                    if any(isinstance(row.id, bool) or not isinstance(row.id, int) or row.id <= 0 for row in rows):
                        result = _empty_result(client_id, planning_fp, target, "RTISA_SOURCE_UNIVERSE_INVALID")
                        db.commit()
                        return serialize(result)
                    ids = [row.id for row in rows]
                    resolutions = list(db.scalars(select(PensionIncomeResolution).where(or_(
                        PensionIncomeResolution.client_id == client_id,
                        PensionIncomeResolution.income_id.in_(ids) if ids else False,
                    )).order_by(PensionIncomeResolution.income_id)))
                    if any(item.client_id != client_id or item.income_id not in ids for item in resolutions):
                        result = _empty_result(client_id, planning_fp, target, "RTISA_SOURCE_UNIVERSE_INVALID")
                    else:
                        result = _assemble(client_id, planning, portfolio, rows, resolutions)
        db.commit()
        return serialize(result)
    except RetirementTargetIncomeSourceAdmissionError:
        raise
    except Exception:
        _discard_failed_attempt(db)
        raise
