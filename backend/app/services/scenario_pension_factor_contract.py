"""Stage 6 P1B: strict factor-admission fingerprint preimage validation (not an approval)."""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import hashlib
import re

from app.services.pension_monthly_basis_service import canonical_bytes

_SHA = re.compile(r"^[0-9a-f]{64}$")
_UTC = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{6}Z$")
_INTS = ("client_id", "scenario_version", "admission_revision")
_HASHES = ("manifest_fingerprint", "source_fingerprint", "election_fingerprint",
           "ruleset_digest", "permission_admission_fingerprint")
_TEXTS = ("scenario_id", "decision_id", "source_product_id", "source_component_id",
          "component_code", "factor_evidence_reference", "survivors_option",
          "payout_option_name", "actor_id")
_FIELDS = frozenset(("contract_version", *_INTS, *_HASHES, *_TEXTS,
     "amount", "statement_date", "pension_start_date", "factor_value",
     "factor_original_representation", "factor_evidence_type", "spouse_age_diff",
     "acknowledged_at_utc"))
_EVIDENCE = frozenset(("INSURER_QUOTE", "POLICY_CONTRACT", "PLANNER_ASSUMPTION"))


def _exact_decimal(value: str, *, money: bool = False) -> None:
    if not isinstance(value, str) or not value or any(ch in value for ch in "eE+"):
        raise ValueError("DECIMAL_NONCANONICAL")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("DECIMAL_INVALID") from exc
    if not parsed.is_finite() or parsed <= 0:
        raise ValueError("DECIMAL_INVALID")
    full = format(parsed, "f")
    canonical = (format(parsed, ".2f") if money else
                 full.rstrip("0").rstrip(".") if "." in full else full)
    if canonical != value:
        raise ValueError("DECIMAL_NONCANONICAL")


def validate_admission_preimage(value: dict) -> dict:
    """Require precisely the N1.3 hashed fields; this is never a permission grant."""
    if type(value) is not dict or set(value) != _FIELDS:
        raise ValueError("ADMISSION_FIELD_SET_INVALID")
    if value["contract_version"] != "SCENARIO_PENSION_FACTOR_ADMISSION_FINGERPRINT_V1":
        raise ValueError("ADMISSION_VERSION_INVALID")
    for key in _INTS:
        if type(value[key]) is not int or value[key] <= 0:
            raise ValueError("ADMISSION_INTEGER_INVALID")
    if (type(value["spouse_age_diff"]) is not int
            or not -100 <= value["spouse_age_diff"] <= 100):
        raise ValueError("ADMISSION_SPOUSE_DIFFERENCE_INVALID")
    for key in _HASHES:
        if type(value[key]) is not str or not _SHA.fullmatch(value[key]):
            raise ValueError("ADMISSION_HASH_INVALID")
    for key in _TEXTS:
        if type(value[key]) is not str or not value[key] or len(value[key]) > 512:
            raise ValueError("ADMISSION_TEXT_INVALID")
    _exact_decimal(value["amount"], money=True)
    _exact_decimal(value["factor_value"])
    if value["factor_original_representation"] != "DIVISOR":
        raise ValueError("ADMISSION_FACTOR_UNITS_UNSUPPORTED")
    if value["factor_evidence_type"] not in _EVIDENCE:
        raise ValueError("ADMISSION_EVIDENCE_INVALID")
    try:
        valuation = date.fromisoformat(value["statement_date"])
        payout = date.fromisoformat(value["pension_start_date"])
        if (valuation.isoformat() != value["statement_date"] or
                payout.isoformat() != value["pension_start_date"] or payout < valuation):
            raise ValueError("ADMISSION_DATE_INVALID")
        if not isinstance(value["acknowledged_at_utc"], str) or not _UTC.fullmatch(value["acknowledged_at_utc"]):
            raise ValueError("ADMISSION_TIMESTAMP_INVALID")
        datetime.strptime(value["acknowledged_at_utc"], "%Y-%m-%dT%H:%M:%S.%fZ")
    except (TypeError, ValueError) as exc:
        raise ValueError("ADMISSION_DATE_INVALID") from exc
    return dict(value)


def fingerprint_admission_preimage(value: dict) -> str:
    """Hash only a validated DB-produced immutable preimage, never authorize execution."""
    return hashlib.sha256(canonical_bytes(validate_admission_preimage(value))).hexdigest()
