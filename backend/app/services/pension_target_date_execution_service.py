"""Deterministic per-source pension execution at an explicit retirement target.

This module is deliberately read-only.  It consumes the already-derived
planning-input source view and never persists, aggregates, or infers authority.
"""
from __future__ import annotations

from calendar import isleap
from datetime import date
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
    ROUND_HALF_EVEN,
    ROUND_HALF_UP,
    Rounded,
    Subnormal,
    Underflow,
    localcontext,
)
from fractions import Fraction
import hashlib
import re

from app.services.pension_monthly_basis_service import canonical_bytes

SCHEMA_VERSION = "PENSION_TARGET_DATE_SOURCE_RESULT_V1"
EXECUTION_CONTRACT = "PENSION_TARGET_DATE_SOURCE_EXECUTION_FINGERPRINT_JSON_V1"
RESULT_CONTRACT = "PENSION_TARGET_DATE_SOURCE_RESULT_FINGERPRINT_JSON_V1"
DECIMAL_CONTRACT = "PENSION_TARGET_DATE_DECIMAL_EXECUTION_V1"
DATE_CONVENTION = "ACTUAL_ACTUAL_CALENDAR_YEAR_SEGMENTED_V1"
SHA256 = re.compile(r"^[0-9a-f]{64}$")

NUMERICAL_FIELDS = {
    "elapsed_year_fraction",
    "derived_base_monthly_amount",
    "temporal_factor",
    "unquantized_target_monthly_amount",
    "final_monthly_amount",
}


def fingerprint(payload: dict) -> str:
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


def _iso(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        return date.fromisoformat(value).isoformat()
    raise ValueError("Canonical date required")


def _decimal(value) -> Decimal:
    if not isinstance(value, str):
        raise ValueError("Exact decimal string required")
    result = Decimal(value)
    if not result.is_finite():
        raise ValueError("Finite decimal required")
    return result


def _canonical_decimal(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text


def _money(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), ".2f")


def decimal_context() -> Context:
    context = Context(prec=100, rounding=ROUND_HALF_EVEN, Emin=-999999, Emax=999999, clamp=0)
    for signal in context.traps:
        context.traps[signal] = signal in (InvalidOperation, DivisionByZero, Overflow, FloatOperation)
    # State is never shared between sources, and flags are diagnostic only.
    context.clear_flags()
    return context


def elapsed_year_fraction(origin, target) -> Fraction:
    """Exact segmented Actual/Actual over the half-open interval [origin,target)."""
    origin_date, target_date = date.fromisoformat(_iso(origin)), date.fromisoformat(_iso(target))
    if target_date < origin_date:
        raise ValueError("RETIREMENT_TARGET_BEFORE_TEMPORAL_ORIGIN")
    result = Fraction(0, 1)
    cursor = origin_date
    while cursor < target_date:
        boundary = date(cursor.year + 1, 1, 1)
        segment_end = min(target_date, boundary)
        result += Fraction((segment_end - cursor).days, 366 if isleap(cursor.year) else 365)
        cursor = segment_end
    return result


def _fraction(value: Fraction) -> dict[str, str]:
    return {"numerator": str(value.numerator), "denominator": str(value.denominator)}


def _base_amount(representation: dict) -> Decimal:
    if not isinstance(representation, dict):
        raise ValueError("Monthly representation required")
    kind = representation.get("representation_kind")
    if kind == "exact_money" and set(representation) == {"representation_kind", "amount"}:
        return _decimal(representation["amount"])
    if kind == "exact_ratio" and set(representation) == {"representation_kind", "numerator", "denominator"}:
        denominator = _decimal(representation["denominator"])
        if denominator <= 0:
            raise ValueError("Positive denominator required")
        return _decimal(representation["numerator"]) / denominator
    raise ValueError("Accepted monthly representation required")


def _accepted_representation(representation) -> bool:
    if not isinstance(representation, dict):
        return False
    kind = representation.get("representation_kind")
    required = ({"representation_kind", "amount"} if kind == "exact_money"
                else {"representation_kind", "numerator", "denominator"} if kind == "exact_ratio"
                else None)
    if required is None or set(representation) != required:
        return False
    values = [representation[key] for key in required - {"representation_kind"}]
    return all(isinstance(value, str) for value in values)


def _sha(value) -> str | None:
    return value if isinstance(value, str) and SHA256.fullmatch(value) else None


def _applicability(target: str | None, start: str | None) -> str:
    if target is None or start is None:
        return "unresolved"
    return "payable_current" if date.fromisoformat(start) <= date.fromisoformat(target) else "future_start"


def _result_payload(result: dict) -> dict:
    common = {
        "applicability_state", "authority_kind", "blockers", "currency",
        "execution_identity_state", "monthly_basis_blockers", "result_state",
        "retirement_target_date", "schema_version", "source_execution_fingerprint",
        "source_id", "temporal_authority_kind", "temporal_blockers", "temporal_origin_date",
    }
    keys = common | ({"elapsed_year_fraction", "final_monthly_amount"}
                     if result["result_state"] == "result_ready" else {"execution_identity_evidence"})
    return {"contract": RESULT_CONTRACT, **{key: result[key] for key in keys}}


def execute_source(
    *,
    source_id: str,
    source_current_state: str,
    monthly_basis: dict | None,
    temporal_authority: dict | None,
    retirement_target: dict | None,
    current_planning_calculation_input_fingerprint: str | None,
    supplied_planning_calculation_input_fingerprint: str | None,
    supplied_monthly_basis_semantic_fingerprint: str | None,
    supplied_monthly_basis_source_fingerprint: str | None,
    supplied_temporal_semantic_fingerprint: str | None,
    supplied_temporal_source_fingerprint: str | None,
    pension_start_date=None,
    currency: str | None = None,
) -> dict:
    """Execute one source from current recomputed evidence and bound identities."""
    monthly_basis = monthly_basis or {}
    temporal_authority = temporal_authority or {}
    retirement_target = retirement_target or {}

    monthly_kind = monthly_basis.get("authority_kind")
    representation = monthly_basis.get("base_amount_representation")
    representation_ready = _accepted_representation(representation)
    if not representation_ready:
        representation = None
    current_monthly_semantic = _sha(monthly_basis.get("base_amount_semantic_fingerprint"))
    current_monthly_source = _sha(monthly_basis.get("base_amount_source_fingerprint"))
    temporal_kind = temporal_authority.get("temporal_authority_kind")
    temporal_origin = temporal_authority.get("temporal_origin_date")
    annual_rate = temporal_authority.get("annual_rate")
    annual_rate_ready = ((temporal_kind == "none" and annual_rate is None)
                         or (temporal_kind == "fixed_manual" and isinstance(annual_rate, str)))
    if not annual_rate_ready:
        annual_rate = None
    if not isinstance(currency, str):
        currency = None
    current_temporal_semantic = _sha(temporal_authority.get("temporal_semantic_fingerprint"))
    current_temporal_source = _sha(temporal_authority.get("temporal_source_fingerprint"))
    current_planning_calculation_input_fingerprint = _sha(current_planning_calculation_input_fingerprint)
    supplied_planning_calculation_input_fingerprint = _sha(supplied_planning_calculation_input_fingerprint)
    supplied_monthly_basis_semantic_fingerprint = _sha(supplied_monthly_basis_semantic_fingerprint)
    supplied_monthly_basis_source_fingerprint = _sha(supplied_monthly_basis_source_fingerprint)
    supplied_temporal_semantic_fingerprint = _sha(supplied_temporal_semantic_fingerprint)
    supplied_temporal_source_fingerprint = _sha(supplied_temporal_source_fingerprint)
    target = retirement_target.get("retirement_target_date")
    target_ready = retirement_target.get("retirement_target_ready") is True

    try:
        target = _iso(target)
    except (TypeError, ValueError):
        target = None
        target_ready = False
    try:
        temporal_origin = _iso(temporal_origin)
    except (TypeError, ValueError):
        temporal_origin = None
    try:
        pension_start_date = _iso(pension_start_date)
    except (TypeError, ValueError):
        pension_start_date = None

    evidence = {
        "annual_rate": annual_rate,
        "base_amount_representation": representation,
        "currency": currency,
        "current_monthly_basis_semantic_fingerprint": current_monthly_semantic,
        "current_monthly_basis_source_fingerprint": current_monthly_source,
        "current_planning_calculation_input_fingerprint": current_planning_calculation_input_fingerprint,
        "current_temporal_semantic_fingerprint": current_temporal_semantic,
        "current_temporal_source_fingerprint": current_temporal_source,
        "monthly_basis_authority_kind": monthly_kind,
        "pension_start_date": pension_start_date,
        "retirement_target_date": target,
        "source_current_state": source_current_state,
        "supplied_monthly_basis_semantic_fingerprint": supplied_monthly_basis_semantic_fingerprint,
        "supplied_monthly_basis_source_fingerprint": supplied_monthly_basis_source_fingerprint,
        "supplied_planning_calculation_input_fingerprint": supplied_planning_calculation_input_fingerprint,
        "supplied_temporal_semantic_fingerprint": supplied_temporal_semantic_fingerprint,
        "supplied_temporal_source_fingerprint": supplied_temporal_source_fingerprint,
        "temporal_authority_kind": temporal_kind,
        "temporal_origin_date": temporal_origin,
    }

    blockers = []
    monthly_blockers = sorted(set(monthly_basis.get("basis_blockers") or []))
    temporal_blockers = sorted(set(temporal_authority.get("temporal_blockers") or []))
    if source_current_state not in ("current", "not_current", "unresolved"):
        source_current_state = "unresolved"
        evidence["source_current_state"] = source_current_state
    if source_current_state != "current":
        blockers.append("SOURCE_NOT_CURRENT")
    if not target_ready or target is None:
        blockers.append("RETIREMENT_TARGET_NOT_READY")
    monthly_required = (
        monthly_kind not in ("entered_monthly_amount", "manual_balance_ratio", "persisted_conversion_ratio")
        or not representation_ready
        or (monthly_kind == "entered_monthly_amount" and representation and representation.get("representation_kind") != "exact_money")
        or (monthly_kind in ("manual_balance_ratio", "persisted_conversion_ratio")
            and representation and representation.get("representation_kind") != "exact_ratio")
        or current_monthly_semantic is None or current_monthly_source is None
        or supplied_monthly_basis_semantic_fingerprint is None or supplied_monthly_basis_source_fingerprint is None
        or monthly_basis.get("basis_authority_ready") is not True or bool(monthly_blockers)
    )
    if monthly_required:
        blockers.append("MONTHLY_BASIS_NOT_READY")
    if current_monthly_semantic is not None and supplied_monthly_basis_semantic_fingerprint is not None \
            and current_monthly_semantic != supplied_monthly_basis_semantic_fingerprint:
        blockers.append("MONTHLY_BASIS_IDENTITY_STALE")
    if current_monthly_source is not None and supplied_monthly_basis_source_fingerprint is not None \
            and current_monthly_source != supplied_monthly_basis_source_fingerprint:
        blockers.append("MONTHLY_BASIS_IDENTITY_STALE")
    temporal_required = (
        temporal_kind not in ("none", "fixed_manual")
        or not annual_rate_ready
        or current_temporal_semantic is None or current_temporal_source is None
        or supplied_temporal_semantic_fingerprint is None or supplied_temporal_source_fingerprint is None
        or temporal_authority.get("temporal_authority_ready") is not True or bool(temporal_blockers)
    )
    if temporal_required:
        blockers.append("TEMPORAL_AUTHORITY_NOT_READY")
    if current_temporal_semantic is not None and supplied_temporal_semantic_fingerprint is not None \
            and current_temporal_semantic != supplied_temporal_semantic_fingerprint:
        blockers.append("TEMPORAL_AUTHORITY_IDENTITY_STALE")
    if current_temporal_source is not None and supplied_temporal_source_fingerprint is not None \
            and current_temporal_source != supplied_temporal_source_fingerprint:
        blockers.append("TEMPORAL_AUTHORITY_IDENTITY_STALE")
    if temporal_origin is None:
        blockers.append("TEMPORAL_ORIGIN_MISSING")
    if current_planning_calculation_input_fingerprint is None \
            or supplied_planning_calculation_input_fingerprint is None \
            or current_planning_calculation_input_fingerprint != supplied_planning_calculation_input_fingerprint:
        blockers.append("PLANNING_INPUT_IDENTITY_STALE")
    if target is not None and temporal_origin is not None \
            and date.fromisoformat(target) < date.fromisoformat(temporal_origin):
        blockers.append("RETIREMENT_TARGET_BEFORE_TEMPORAL_ORIGIN")
    blockers = sorted(set(blockers))

    incomplete_causes = set(blockers) - {"RETIREMENT_TARGET_BEFORE_TEMPORAL_ORIGIN"}
    identity_state = "incomplete" if incomplete_causes else "complete"
    execution_payload = None
    execution_fingerprint = None
    if identity_state == "complete":
        execution_payload = {
            "annual_rate": annual_rate,
            "base_amount_representation": representation,
            "contract": EXECUTION_CONTRACT,
            "currency": currency,
            "monthly_basis_authority_kind": monthly_kind,
            "monthly_basis_semantic_fingerprint": current_monthly_semantic,
            "monthly_basis_source_fingerprint": current_monthly_source,
            "pension_start_date": pension_start_date,
            "planning_calculation_input_fingerprint": current_planning_calculation_input_fingerprint,
            "retirement_target_date": target,
            "source_current_state": "current",
            "source_id": source_id,
            "temporal_authority_kind": temporal_kind,
            "temporal_origin_date": temporal_origin,
            "temporal_semantic_fingerprint": current_temporal_semantic,
            "temporal_source_fingerprint": current_temporal_source,
        }
        execution_fingerprint = fingerprint(execution_payload)

    result = {
        "schema_version": SCHEMA_VERSION,
        "source_id": source_id,
        "result_state": "block_no_result" if blockers else "result_ready",
        "execution_identity_state": identity_state,
        "source_execution_fingerprint": execution_fingerprint,
        "source_result_fingerprint": None,
        "authority_kind": monthly_kind,
        "temporal_authority_kind": temporal_kind,
        "temporal_origin_date": temporal_origin,
        "retirement_target_date": target,
        "currency": currency,
        "applicability_state": _applicability(target, pension_start_date),
        "blockers": blockers,
        "monthly_basis_blockers": monthly_blockers,
        "temporal_blockers": temporal_blockers,
        "execution_identity_evidence": evidence,
    }
    if blockers:
        result["source_result_fingerprint"] = fingerprint(_result_payload(result))
        return result

    try:
        with localcontext(decimal_context()) as context:
            context.clear_flags()
            elapsed = elapsed_year_fraction(temporal_origin, target)
            base_amount = _base_amount(representation)
            if temporal_kind == "none":
                factor = Decimal("1")
            else:
                rate = _decimal(annual_rate)
                if rate <= 0:
                    raise InvalidOperation("Positive annual rate required")
                year_value = Decimal(elapsed.numerator) / Decimal(elapsed.denominator)
                factor = (year_value * (Decimal("1") + rate).ln()).exp()
            unquantized = base_amount * factor
            final = _money(unquantized)
            result.update(
                elapsed_year_fraction=_fraction(elapsed),
                base_amount_representation=representation,
                derived_base_monthly_amount=_canonical_decimal(base_amount),
                annual_rate=annual_rate,
                temporal_factor=_canonical_decimal(factor),
                unquantized_target_monthly_amount=_canonical_decimal(unquantized),
                final_monthly_amount=final,
                decimal_execution_contract=DECIMAL_CONTRACT,
            )
    except (DecimalException, ArithmeticError, ValueError, TypeError):
        result["result_state"] = "block_no_result"
        result["blockers"] = ["NUMERIC_EXECUTION_ERROR"]
        for key in NUMERICAL_FIELDS:
            result.pop(key, None)
    result["source_result_fingerprint"] = fingerprint(_result_payload(result))
    return result


def execute_from_planning_result(
    planning_result: dict,
    source_id: str,
    *,
    supplied_planning_calculation_input_fingerprint: str | None,
    supplied_monthly_basis_semantic_fingerprint: str | None,
    supplied_monthly_basis_source_fingerprint: str | None,
    supplied_temporal_semantic_fingerprint: str | None,
    supplied_temporal_source_fingerprint: str | None,
) -> dict:
    """Bind execution to one unique source in a freshly recomputed planning result."""
    matches = [source for source in planning_result.get("pension_inputs", [])
               if source.get("source_id") == source_id]
    current_state = "current" if len(matches) == 1 else "not_current"
    source = matches[0] if len(matches) == 1 else {}
    return execute_source(
        source_id=source_id,
        source_current_state=current_state,
        monthly_basis=source.get("monthly_amount_basis"),
        temporal_authority=source.get("temporal_authority"),
        retirement_target=planning_result.get("retirement_target"),
        current_planning_calculation_input_fingerprint=planning_result.get("planning_calculation_input_fingerprint"),
        supplied_planning_calculation_input_fingerprint=supplied_planning_calculation_input_fingerprint,
        supplied_monthly_basis_semantic_fingerprint=supplied_monthly_basis_semantic_fingerprint,
        supplied_monthly_basis_source_fingerprint=supplied_monthly_basis_source_fingerprint,
        supplied_temporal_semantic_fingerprint=supplied_temporal_semantic_fingerprint,
        supplied_temporal_source_fingerprint=supplied_temporal_source_fingerprint,
        pension_start_date=source.get("pension_start_date"),
        currency=source.get("currency"),
    )


def execute_current_source(db, client_id: int, source_id: str, **supplied_identities) -> dict:
    """Recompute all current authority in one read snapshot, then execute."""
    from app.services.planning_input_service import read

    planning_result = read(db, client_id)
    return execute_from_planning_result(planning_result, source_id, **supplied_identities)
