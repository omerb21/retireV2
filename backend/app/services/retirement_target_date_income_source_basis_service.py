"""CRTISBA: append-only professional source-basis authority."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from decimal import Decimal
import hashlib
import json
import re
from typing import Any

from sqlalchemy import Select, desc, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from app.models.canonical_conversion import pensions as canonical_pension_destinations
from app.models.canonical_manual_pension_source import CanonicalManualPensionSource
from app.models.client import Client
from app.models.retirement_facts import RecurringIncome
from app.models.retirement_income_source_basis import RetirementTargetDateIncomeSourceBasisDecision as Decision
from app.schemas.retirement_income_source_basis import _Command
from app.services import planning_input_service
from app.services import pension_target_date_portfolio_service as portfolio_service
from app.services import retirement_target_date_income_source_admission_service as rtisa_service
from app.services.pension_product_service import PensionProductError
from app.services.professional_source_snapshot_service import record, serialize

SHA = re.compile(r"^[0-9a-f]{64}$")
MAX_VERSION = 9223372036854775807
DECISION_CONTRACT = "CANONICAL_RETIREMENT_TARGET_DATE_INCOME_SOURCE_BASIS_DECISION_JSON_V1"
PENSION_AMOUNT_CONTRACT = "CANONICAL_RETIREMENT_TARGET_DATE_INCOME_SOURCE_BASIS_PENSION_AMOUNT_AUTHORITY_JSON_V1"
RECURRING_AMOUNT_CONTRACT = "CANONICAL_RETIREMENT_TARGET_DATE_INCOME_SOURCE_BASIS_RECURRING_AMOUNT_AUTHORITY_JSON_V1"
RESULT_CONTRACT = "CANONICAL_RETIREMENT_TARGET_DATE_INCOME_SOURCE_BASIS_RESULT_JSON_V1"
FAILURE_CONTRACT = "CANONICAL_RETIREMENT_TARGET_DATE_INCOME_SOURCE_BASIS_FAILURE_JSON_V1"
NO_COLLECTION = {
    "RTISA_SOURCE_UNIVERSE_INVALID": ("source_universe", "CRTISBA_SOURCE_UNIVERSE_INVALID"),
    "RTISA_PENSION_RESULT_INVALID": ("pension_result", "CRTISBA_PENSION_RESULT_INVALID"),
}
NON_DELEGATION_UNRESOLVED = {
    "RTISA_PENSION_AUTHORITY_UNAVAILABLE", "RTISA_PENSION_SOURCE_NOT_READY",
    "RTISA_SOURCE_CURRENCY_UNSUPPORTED", "RTISA_PENSION_APPLICABILITY_UNRESOLVED",
    "RTISA_SOURCE_IDENTITY_STALE", "RTISA_SOURCE_RECORD_INVALID",
    "RTISA_SOURCE_AUTHORITY_NOT_RECORDED", "RTISA_SOURCE_REVIEW_INCOMPLETE",
    "RTISA_SOURCE_AMOUNT_INVALID", "RTISA_SOURCE_FREQUENCY_UNSUPPORTED",
    "RTISA_NATIVE_INCOME_BASIS_UNKNOWN", "RTISA_SOURCE_START_DATE_MISSING",
    "RTISA_SOURCE_CONTINUATION_UNRESOLVED", "RTISA_SOURCE_END_DATE_MISSING",
    "RTISA_SOURCE_DATE_RANGE_INVALID", "RTISA_SOURCE_IDENTITY_AMBIGUOUS",
    "RTISA_DUPLICATE_COLLISION_UNRESOLVED",
}
PARTITION_STATES = {
    "CURRENT": "current", "MISSING": "missing", "UNKNOWN": "unknown", "STALE": "stale",
    "INVALID": "invalid", "UPSTREAM_UNRESOLVED": "upstream_unresolved",
    "NOT_APPLICABLE_DELEGATED": "not_applicable_delegated",
    "NOT_APPLICABLE_NOT_ADMITTED": "not_applicable_not_admitted",
    "DELEGATION_UNRESOLVED": "delegation_unresolved", "DELEGATION_STALE": "delegation_stale",
}
CHECK_CONSTRAINTS = {
    "ck_crtisba_decision_version_positive", "ck_crtisba_source_kind",
    "ck_crtisba_source_identity_shape", "ck_crtisba_income_basis",
    "ck_crtisba_income_basis_provenance", "ck_crtisba_price_basis",
    "ck_crtisba_price_basis_provenance", "ck_crtisba_kind_payload",
    "ck_crtisba_reference_date", "ck_crtisba_hash_shapes",
}


class CRTISBAError(PensionProductError):
    def __init__(self, code: str, status_code: int = 409, field_paths: list[str] | None = None):
        super().__init__(code, "לא ניתן להשלים את הבקשה", status_code)
        self.field_paths = field_paths or []


class CRTISBAFingerprintConstructionError(RuntimeError):
    pass


def _json_default(value: Any):
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, date):
        return value.isoformat()
    raise TypeError(type(value).__name__)


def canonical_json(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                          allow_nan=False, default=_json_default)
    except (TypeError, ValueError) as exc:
        raise CRTISBAFingerprintConstructionError from exc


def fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _decimal_text(value: Any) -> str:
    decimal = value if isinstance(value, Decimal) else Decimal(str(value))
    if not decimal.is_finite():
        raise CRTISBAFingerprintConstructionError
    return format(decimal, "f")


def _pristine(db: Session) -> None:
    if db.in_transaction() or db.new or db.dirty or db.deleted:
        raise CRTISBAError("CRTISBA_REQUIRES_FRESH_TRANSACTION", 503)


def _begin(db: Session, *, write: bool) -> None:
    dialect = db.get_bind().dialect.name
    if dialect != "postgresql":
        raise CRTISBAError("CRTISBA_UNSUPPORTED_DATABASE", 503)
    level = "SERIALIZABLE" if write else "REPEATABLE READ"
    db.connection(execution_options={"isolation_level": level})
    if not write:
        db.execute(text("SET TRANSACTION READ ONLY"))


def _rollback(db: Session) -> None:
    connection = None
    try:
        connection = db.connection()
    except Exception:
        pass
    try:
        db.rollback()
    except Exception as exc:
        try:
            if connection is not None:
                connection.invalidate()
        except Exception:
            pass
        db.close()
        raise CRTISBAError("CRTISBA_ROLLBACK_FAILED", 503) from exc


def _decision_preimage(values: dict) -> dict:
    return {
        "contract": DECISION_CONTRACT,
        "client_id": values["client_id"], "source_id": values["source_id"],
        "source_kind": values["source_kind"], "decision_version": values["decision_version"],
        "planning_calculation_input_fingerprint": values["planning_calculation_input_fingerprint"],
        "source_version": values["source_version"], "source_fingerprint": values["source_fingerprint"],
        "amount_authority_fingerprint": values["amount_authority_fingerprint"],
        "income_basis": values["income_basis"], "income_basis_provenance": values["income_basis_provenance"],
        "price_basis": values["price_basis"], "price_reference_date": values["price_reference_date"],
        "price_basis_provenance": values["price_basis_provenance"],
    }


def decision_fingerprint(values: dict) -> str:
    return fingerprint(_decision_preimage(values))


def _failure(client_id: int, source_id: str | None, operation: str, stage: str, code: str,
             fields: list[str] | None = None, observed: dict | None = None) -> dict:
    observed = observed or {}
    body = {
        "schema_version": "CRTISBA_BLOCK_NO_RESULT_V1", "result_state": "block_no_result",
        "client_id": client_id, "source_id": source_id, "operation": operation,
        "failure_stage": stage, "failure_detail_code": code,
        "field_paths": sorted(set(fields or [])),
        "observed_planning_calculation_input_fingerprint": observed.get("planning"),
        "observed_source_version": observed.get("source_version"),
        "observed_source_fingerprint": observed.get("source_fingerprint"),
        "observed_amount_authority_fingerprint": observed.get("amount"),
        "observed_decision_version": observed.get("decision_version"),
    }
    body["failure_fingerprint"] = fingerprint({"contract": FAILURE_CONTRACT, **{
        key: value for key, value in body.items() if key not in {"schema_version", "result_state", "failure_fingerprint"}
    }})
    return body


def _planning(db: Session, client_id: int, operation: str, source_id: str | None = None):
    try:
        result = planning_input_service.derive(db, client_id)
    except PensionProductError:
        return None, _failure(client_id, source_id, operation, "planning_context", "CRTISBA_PLANNING_CONTEXT_UNAVAILABLE")
    if not isinstance(result, dict) or result.get("client_id") != client_id:
        raise CRTISBAError("PRODUCER_RESPONSE_INVALID", 500)
    planning_fp = result.get("planning_calculation_input_fingerprint")
    if not isinstance(planning_fp, str) or not SHA.fullmatch(planning_fp):
        raise CRTISBAError("PRODUCER_RESPONSE_INVALID", 500)
    target = result.get("retirement_target")
    if not isinstance(target, dict):
        raise CRTISBAError("PRODUCER_RESPONSE_INVALID", 500)
    if target.get("retirement_target_ready") is not True or not isinstance(target.get("retirement_target_date"), str):
        return None, _failure(client_id, source_id, operation, "retirement_target", "CRTISBA_RETIREMENT_TARGET_NOT_READY", observed={"planning": planning_fp})
    pension_inputs = result.get("pension_inputs")
    if not isinstance(pension_inputs, list) or any(not isinstance(item, dict) for item in pension_inputs):
        raise CRTISBAError("PRODUCER_RESPONSE_INVALID", 500)
    ids = [item.get("source_id") for item in pension_inputs]
    if any(not isinstance(item, str) or not item for item in ids) or len(ids) != len(set(ids)):
        raise CRTISBAError("PRODUCER_RESPONSE_INVALID", 500)
    return result, None


def _amount_context(planning: dict, portfolio: dict, rtisa: dict) -> dict[str, dict]:
    pension_inputs = {item["source_id"]: item for item in planning.get("pension_inputs", [])}
    recurring_inputs = {item["source_id"]: item for item in planning.get("general_income_inputs", [])
                        if isinstance(item, dict) and isinstance(item.get("source_id"), str)}
    pension_results = {item.get("source_id"): item for item in portfolio.get("source_results", []) if isinstance(item, dict)}
    portfolio_entries = {item.get("source_id"): item.get("source_entry_fingerprint") for item in portfolio.get("source_entry_fingerprints", []) if isinstance(item, dict)}
    contexts: dict[str, dict] = {}
    for entry in rtisa.get("source_entries", []):
        source_id = entry.get("source_id")
        source_fp = (entry.get("upstream_identity") or {}).get("source_fingerprint")
        if not isinstance(source_id, str) or not isinstance(source_fp, str) or not SHA.fullmatch(source_fp):
            raise CRTISBAError("PRODUCER_RESPONSE_INVALID", 500)
        if source_id.startswith(("manual:", "conversion:")):
            source = pension_inputs.get(source_id) or {}
            pte = pension_results.get(source_id) or {}
            monthly = source.get("monthly_amount_basis") or {}
            temporal = source.get("temporal_authority") or {}
            upstream_result_fp = (entry.get("upstream_identity") or {}).get("pension_source_result_fingerprint")
            entry_fp = portfolio_entries.get(source_id)
            numerator = (entry.get("monthly_equivalent") or {}).get("numerator")
            exact = pte.get("unquantized_target_monthly_amount")
            amount_fp = None
            if numerator is not None and exact is not None and Decimal(str(numerator)) == Decimal(str(exact)):
                preimage = {
                    "contract": PENSION_AMOUNT_CONTRACT, "client_id": planning["client_id"], "source_id": source_id,
                    "source_version": source.get("version"), "source_fingerprint": source_fp,
                    "base_amount_semantic_fingerprint": monthly.get("base_amount_semantic_fingerprint"),
                    "base_amount_source_fingerprint": monthly.get("base_amount_source_fingerprint"),
                    "temporal_semantic_fingerprint": temporal.get("temporal_semantic_fingerprint"),
                    "temporal_source_fingerprint": temporal.get("temporal_source_fingerprint"),
                    "planning_calculation_input_fingerprint": planning["planning_calculation_input_fingerprint"],
                    "retirement_target_date": planning["retirement_target"]["retirement_target_date"],
                    "pension_source_execution_fingerprint": pte.get("source_execution_fingerprint"),
                    "pension_source_result_fingerprint": upstream_result_fp,
                    "portfolio_source_entry_fingerprint": entry_fp,
                    "amount": {"numerator": str(numerator), "denominator": "1", "currency": "ILS", "frequency": "MONTHLY"},
                }
                if isinstance(source.get("version"), int) and all(isinstance(preimage[key], str) and SHA.fullmatch(preimage[key]) for key in (
                    "source_fingerprint", "base_amount_semantic_fingerprint", "base_amount_source_fingerprint",
                    "temporal_semantic_fingerprint", "temporal_source_fingerprint", "planning_calculation_input_fingerprint",
                    "pension_source_execution_fingerprint", "pension_source_result_fingerprint", "portfolio_source_entry_fingerprint")):
                    amount_fp = fingerprint(preimage)
            contexts[source_id] = {
                "kind": "PENSION", "source_version": source.get("version"), "source_fingerprint": source_fp,
                "amount": amount_fp, "pension_source_execution_fingerprint": pte.get("source_execution_fingerprint"),
                "pension_source_result_fingerprint": upstream_result_fp, "portfolio_source_entry_fingerprint": entry_fp,
                "retirement_target_date": planning["retirement_target"]["retirement_target_date"],
            }
        else:
            native = entry.get("native_amount") or {}
            source = recurring_inputs.get(source_id) or {}
            amount_fp = None
            reasons = sorted(set(entry.get("reason_codes") or []))
            amount_eligible = entry.get("admission_state") == "INCLUDED" or reasons == ["RTISA_SOURCE_FREQUENCY_UNSUPPORTED"]
            if amount_eligible and source.get("amount") is not None:
                amount_fp = fingerprint({
                    "contract": RECURRING_AMOUNT_CONTRACT, "client_id": planning["client_id"], "source_id": source_id,
                    "source_fingerprint": source_fp, "amount": _decimal_text(source["amount"]),
                    "amount_basis": source.get("amount_basis"), "frequency": source.get("frequency"),
                })
            contexts[source_id] = {"kind": "RECURRING_INCOME", "source_version": source_fp,
                                    "source_fingerprint": source_fp, "amount": amount_fp}
    return contexts


def _derive_snapshot(db: Session, client_id: int, operation: str, source_id: str | None = None):
    if db.get(Client, client_id) is None:
        raise CRTISBAError("CLIENT_NOT_FOUND", 404, ["/path/client_id"])
    planning, blocked = _planning(db, client_id, operation, source_id)
    if blocked:
        return blocked, None
    planning_fp = planning["planning_calculation_input_fingerprint"]
    portfolio = portfolio_service.execute_from_planning_result(planning, client_id, planning_fp)
    try:
        rtisa = rtisa_service.read_in_snapshot(db, client_id, planning_fp)
    except rtisa_service.RetirementTargetIncomeSourceAdmissionTechnicalError as exc:
        raise CRTISBAError("CRTISBA_UPSTREAM_TECHNICAL_FAILURE", 503) from exc
    if not isinstance(rtisa, dict):
        raise CRTISBAError("PRODUCER_RESPONSE_INVALID", 500)
    supplied_rtisa_fingerprint = rtisa.get("admission_result_fingerprint")
    rtisa_payload = {key: deepcopy(value) for key, value in rtisa.items() if key != "admission_result_fingerprint"}
    if supplied_rtisa_fingerprint != rtisa_service._result_fingerprint(rtisa_payload):
        raise CRTISBAError("PRODUCER_RESPONSE_INVALID", 500)
    if rtisa.get("client_id") != client_id:
        raise CRTISBAError("RESPONSE_CLIENT_MISMATCH", 500)
    entries = rtisa.get("source_entries")
    blockers = rtisa.get("blockers")
    rtisa_fingerprint = rtisa.get("admission_result_fingerprint")
    if not isinstance(entries, list) or not isinstance(blockers, list):
        raise CRTISBAError("PRODUCER_RESPONSE_INVALID", 500)
    if not isinstance(rtisa_fingerprint, str) or not SHA.fullmatch(rtisa_fingerprint):
        raise CRTISBAError("PRODUCER_RESPONSE_INVALID", 500)
    if not entries:
        if (blockers == [] and rtisa.get("included_source_ids") == []
                and rtisa.get("excluded_source_ids") == [] and rtisa.get("unresolved_source_ids") == []
                and rtisa.get("universe_completeness_state") == "COMPLETE_EVIDENCED"
                and rtisa.get("admission_readiness_state") == "READY"
                and rtisa.get("admission_ready") is True):
            return None, {"planning": planning, "portfolio": portfolio, "rtisa": rtisa, "contexts": {}}
        unique = sorted(set(blockers))
        if (len(blockers) != 1 or blockers != unique or blockers[0] not in NO_COLLECTION
                or rtisa.get("included_source_ids") != [] or rtisa.get("excluded_source_ids") != []
                or rtisa.get("unresolved_source_ids") != []
                or rtisa.get("universe_completeness_state") != "UNAVAILABLE"
                or rtisa.get("admission_readiness_state") != "NOT_READY"
                or rtisa.get("admission_ready") is not False):
            raise CRTISBAError("PRODUCER_RESPONSE_INVALID", 500)
        stage, code = NO_COLLECTION[blockers[0]]
        return _failure(client_id, source_id, operation, stage, code, observed={"planning": planning_fp}), None
    return None, {"planning": planning, "portfolio": portfolio, "rtisa": rtisa,
                  "contexts": _amount_context(planning, portfolio, rtisa)}


def _latest_rows(db: Session, client_id: int) -> dict[str, Decision]:
    rows = list(db.scalars(select(Decision).where(Decision.client_id == client_id)
                           .order_by(Decision.source_id, desc(Decision.decision_version))))
    latest: dict[str, Decision] = {}
    for row in rows:
        latest.setdefault(row.source_id, row)
    return latest


def _row_values(row: Decision) -> dict:
    source_version = row.pension_source_version if row.source_kind == "PENSION" else row.recurring_source_version_fingerprint
    return {
        "client_id": row.client_id, "source_id": row.source_id, "source_kind": row.source_kind,
        "decision_version": row.decision_version,
        "planning_calculation_input_fingerprint": row.planning_calculation_input_fingerprint,
        "source_version": source_version, "source_fingerprint": row.source_fingerprint,
        "amount_authority_fingerprint": row.amount_authority_fingerprint,
        "income_basis": row.income_basis, "income_basis_provenance": row.income_basis_provenance,
        "price_basis": row.price_basis, "price_reference_date": row.price_reference_date,
        "price_basis_provenance": row.price_basis_provenance,
    }


def _valid_row(row: Decision) -> bool:
    try:
        values = _row_values(row)
        return (row.decision_version > 0 and row.source_kind in {"PENSION", "RECURRING_INCOME"}
                and all(isinstance(getattr(row, field), str) and SHA.fullmatch(getattr(row, field)) for field in (
                    "planning_calculation_input_fingerprint", "source_fingerprint", "amount_authority_fingerprint", "decision_fingerprint"))
                and decision_fingerprint(values) == row.decision_fingerprint)
    except Exception:
        return False


def _current_matches(row: Decision, context: dict, planning_fp: str) -> bool:
    if row.source_kind != context["kind"] or row.planning_calculation_input_fingerprint != planning_fp:
        return False
    source_version = row.pension_source_version if row.source_kind == "PENSION" else row.recurring_source_version_fingerprint
    if source_version != context["source_version"] or row.source_fingerprint != context["source_fingerprint"] or row.amount_authority_fingerprint != context["amount"]:
        return False
    if row.source_kind == "PENSION":
        return (row.pension_source_execution_fingerprint == context["pension_source_execution_fingerprint"]
                and row.pension_source_result_fingerprint == context["pension_source_result_fingerprint"]
                and row.portfolio_source_entry_fingerprint == context["portfolio_source_entry_fingerprint"]
                and row.retirement_target_date.isoformat() == context["retirement_target_date"])
    return True


def _safe_basis(kind: str, entry: dict):
    if kind == "PENSION":
        return "UNKNOWN", "MISSING", "NOMINAL_AT_RETIREMENT_TARGET_DATE", None, "OWNER_DECISION_OD2"
    income = entry.get("native_income_basis") if entry.get("native_income_basis") in {"GROSS", "NET"} else "UNKNOWN"
    provenance = "UPSTREAM_RECURRING_AMOUNT_BASIS" if income in {"GROSS", "NET"} else "MISSING"
    return income, provenance, "UNKNOWN", None, "MISSING"


def _entry(entry: dict, context: dict | None, row: Decision | None, planning_fp: str) -> dict:
    source_id = entry["source_id"]
    kind = context["kind"] if context else ("PENSION" if source_id.startswith(("manual:", "conversion:")) else "RECURRING_INCOME")
    reasons = sorted(set(entry.get("reason_codes") or []))
    admission = entry.get("admission_state")
    state = None
    blockers: list[str] = []
    expose = False
    if admission == "EXCLUDED" and reasons == ["RTISA_SAME_CANONICAL_PENSION"]:
        state = "NOT_APPLICABLE_DELEGATED"
    elif admission == "UNRESOLVED" and reasons == ["RTISA_SOURCE_IDENTITY_UNRESOLVED"]:
        state, blockers = "DELEGATION_UNRESOLVED", reasons
    elif admission == "UNRESOLVED" and reasons == ["RTISA_SOURCE_IDENTITY_STALE"] and entry.get("source_category") == "PENSION_REPRESENTATION":
        state, blockers = "DELEGATION_STALE", reasons
    elif admission == "EXCLUDED":
        state = "NOT_APPLICABLE_NOT_ADMITTED"
    elif admission == "UNRESOLVED":
        if not reasons or any(reason not in NON_DELEGATION_UNRESOLVED for reason in reasons):
            raise CRTISBAError("PRODUCER_RESPONSE_INVALID", 500)
        state, blockers = "UPSTREAM_UNRESOLVED", reasons
        expose = reasons == ["RTISA_SOURCE_FREQUENCY_UNSUPPORTED"] and context is not None and context.get("amount") is not None
    elif admission == "INCLUDED" and context is not None:
        if row is None:
            state, blockers = "MISSING", ["CRTISBA_DECISION_MISSING"]
        elif not _valid_row(row):
            state, blockers = "INVALID", ["CRTISBA_DECISION_INVALID"]
        elif not _current_matches(row, context, planning_fp):
            state, blockers = "STALE", ["CRTISBA_DECISION_STALE"]
            expose = True
        elif (kind == "PENSION" and row.income_basis == "UNKNOWN") or (kind == "RECURRING_INCOME" and row.price_basis == "UNKNOWN"):
            state, blockers = "UNKNOWN", ["CRTISBA_DECISION_UNKNOWN"]
            expose = True
        else:
            state, expose = "CURRENT", True
    else:
        raise CRTISBAError("PRODUCER_RESPONSE_INVALID", 500)
    source_version = context.get("source_version") if context else None
    source_fp = context.get("source_fingerprint") if context else (entry.get("upstream_identity") or {}).get("source_fingerprint")
    amount_fp = context.get("amount") if context and state not in {"NOT_APPLICABLE_DELEGATED", "NOT_APPLICABLE_NOT_ADMITTED", "DELEGATION_UNRESOLVED", "DELEGATION_STALE"} else None
    if state == "INVALID":
        decision_version = decision_fp = None
    elif row is not None and expose:
        decision_version, decision_fp = row.decision_version, row.decision_fingerprint
    else:
        decision_version = decision_fp = None
    if state in {"NOT_APPLICABLE_DELEGATED", "NOT_APPLICABLE_NOT_ADMITTED", "DELEGATION_UNRESOLVED", "DELEGATION_STALE"} or (state == "UPSTREAM_UNRESOLVED" and not expose):
        basis = (None, None, None, None, None)
    elif state == "CURRENT" or (state == "UPSTREAM_UNRESOLVED" and expose and row is not None and _valid_row(row) and _current_matches(row, context, planning_fp)):
        if kind == "PENSION":
            basis = (row.income_basis, row.income_basis_provenance, "NOMINAL_AT_RETIREMENT_TARGET_DATE", None, "OWNER_DECISION_OD2")
        else:
            basis = (entry.get("native_income_basis", "UNKNOWN"), "UPSTREAM_RECURRING_AMOUNT_BASIS" if entry.get("native_income_basis") in {"GROSS", "NET"} else "MISSING", row.price_basis, row.price_reference_date.isoformat() if row.price_reference_date else None, row.price_basis_provenance)
    else:
        basis = _safe_basis(kind, entry)
    return {
        "schema_version": "CRTISBA_SOURCE_BASIS_ENTRY_V1", "source_id": source_id, "source_kind": kind,
        "source_category": entry.get("source_category"), "admission_state": admission,
        "rtisa_reason_codes": reasons, "source_version": source_version, "source_fingerprint": source_fp,
        "amount_authority_fingerprint": amount_fp, "decision_version": decision_version,
        "decision_fingerprint": decision_fp, "decision_state": state,
        "income_basis": basis[0], "income_basis_provenance": basis[1], "price_basis": basis[2],
        "price_reference_date": basis[3], "price_basis_provenance": basis[4], "blockers": blockers,
    }


def derive_in_snapshot(db: Session, client_id: int, operation: str = "READ", source_id: str | None = None) -> dict:
    blocked, snapshot = _derive_snapshot(db, client_id, operation, source_id)
    if blocked:
        return blocked
    planning, rtisa = snapshot["planning"], snapshot["rtisa"]
    latest = _latest_rows(db, client_id)
    result_entries = [_entry(item, snapshot["contexts"].get(item.get("source_id")), latest.get(item.get("source_id")), planning["planning_calculation_input_fingerprint"])
                      for item in rtisa["source_entries"]]
    result_entries.sort(key=lambda item: item["source_id"])
    partitions = {name: [] for name in PARTITION_STATES.values()}
    blockers: list[str] = []
    for item in result_entries:
        partitions[PARTITION_STATES[item["decision_state"]]].append(item["source_id"])
        blockers.extend(item["blockers"])
    blockers = sorted(set(blockers))
    body = {
        "schema_version": "CRTISBA_COLLECTION_RESULT_V1", "client_id": client_id,
        "planning_calculation_input_fingerprint": planning["planning_calculation_input_fingerprint"],
        "retirement_target_date": planning["retirement_target"]["retirement_target_date"],
        "rtisa_admission_result_fingerprint": rtisa.get("admission_result_fingerprint"),
        "source_basis_entries": result_entries, "partitions": partitions, "blockers": blockers,
        "basis_readiness_state": "READY" if not blockers else "NOT_READY", "basis_ready": not blockers,
    }
    body["result_fingerprint"] = fingerprint({"contract": RESULT_CONTRACT, "result": deepcopy(body)})
    return body


def read(db: Session, client_id: int) -> dict:
    _pristine(db)
    acquired = False
    try:
        _begin(db, write=False)
        acquired = True
        result = derive_in_snapshot(db, client_id)
        _rollback(db)
        return result
    except CRTISBAError:
        if db.in_transaction():
            _rollback(db)
        raise
    except Exception as exc:
        if db.in_transaction():
            _rollback(db)
        raise CRTISBAError("CRTISBA_DATABASE_FAILURE", 503) from exc


def _lock_source(db: Session, client_id: int, source_id: str, kind: str):
    if kind == "RECURRING_INCOME":
        try: identity = int(source_id.removeprefix("income:"))
        except ValueError: raise CRTISBAError("CRTISBA_SOURCE_NOT_FOUND", 404, ["/path/source_id"])
        row = db.scalar(select(RecurringIncome).where(RecurringIncome.id == identity, RecurringIncome.client_id == client_id).with_for_update())
        current = row is not None and row.lifecycle_status == "current"
    elif source_id.startswith("manual:"):
        row = db.scalar(select(CanonicalManualPensionSource).where(CanonicalManualPensionSource.manual_pension_source_id == source_id.removeprefix("manual:"), CanonicalManualPensionSource.client_id == client_id).with_for_update())
        current = row is not None and row.lifecycle_status == "current"
    elif source_id.startswith("conversion:"):
        row = db.execute(select(canonical_pension_destinations).where(canonical_pension_destinations.c.pension_destination_id == source_id.removeprefix("conversion:"), canonical_pension_destinations.c.client_id == client_id).with_for_update()).mappings().first()
        current = row is not None and row["status"] == "active"
    else:
        row, current = None, False
    if row is None:
        raise CRTISBAError("CRTISBA_SOURCE_NOT_FOUND", 404, ["/path/source_id"])
    if not current:
        raise CRTISBAError("CRTISBA_SOURCE_NOT_CURRENT", 409, ["/path/source_id"])
    return row


def _classify_integrity(exc: DBAPIError, phase: str) -> CRTISBAError:
    orig = getattr(exc, "orig", None)
    state = str(getattr(orig, "pgcode", None) or getattr(orig, "sqlstate", None) or "").upper()
    diag = getattr(orig, "diag", None)
    constraint = getattr(diag, "constraint_name", None)
    invalid = bool(getattr(exc, "connection_invalidated", False))
    if phase == "COMMIT_DISPATCHED":
        if invalid or state.startswith("08"):
            return CRTISBAError("CRTISBA_COMMIT_OUTCOME_UNKNOWN", 503)
        if state in {"40001", "40P01", "25P02"}:
            return CRTISBAError("CRTISBA_SERIALIZATION_FAILURE" if state in {"40001", "40P01"} else "CRTISBA_COMMIT_FAILED", 503)
        if state == "23505":
            if constraint == "uq_crtisba_source_decision_version":
                return CRTISBAError("CRTISBA_DECISION_VERSION_CONFLICT", 409, ["/expected_decision_version"])
            if constraint == "pk_crtisba_decisions":
                return CRTISBAError("CRTISBA_PERSISTENCE_IDENTITY_CONFLICT", 500)
        if state == "23503" and constraint == "fk_crtisba_decision_client":
            return CRTISBAError("CLIENT_NOT_FOUND", 404, ["/path/client_id"])
        if state == "23514" and constraint in CHECK_CONSTRAINTS:
            return CRTISBAError("CRTISBA_PERSISTENCE_CONTRACT_VIOLATION", 500)
        if state == "P7501" and constraint == "trg_crtisba_decision_immutable":
            return CRTISBAError("CRTISBA_PERSISTENCE_IMMUTABILITY_VIOLATION", 500)
        return CRTISBAError("CRTISBA_COMMIT_OUTCOME_UNKNOWN", 503)
    if state in {"40001", "40P01"}:
        return CRTISBAError("CRTISBA_SERIALIZATION_FAILURE", 503)
    if state == "23505":
        if constraint == "uq_crtisba_source_decision_version":
            return CRTISBAError("CRTISBA_DECISION_VERSION_CONFLICT", 409, ["/expected_decision_version"])
        if constraint == "pk_crtisba_decisions":
            return CRTISBAError("CRTISBA_PERSISTENCE_IDENTITY_CONFLICT", 500)
    if state == "23503" and constraint == "fk_crtisba_decision_client":
        return CRTISBAError("CLIENT_NOT_FOUND", 404, ["/path/client_id"])
    if state == "23514" and constraint in CHECK_CONSTRAINTS:
        return CRTISBAError("CRTISBA_PERSISTENCE_CONTRACT_VIOLATION", 500)
    if state == "P7501" and constraint == "trg_crtisba_decision_immutable":
        return CRTISBAError("CRTISBA_PERSISTENCE_IMMUTABILITY_VIOLATION", 500)
    return CRTISBAError("CRTISBA_FLUSH_FAILED" if phase == "FLUSHING" else "CRTISBA_DATABASE_FAILURE", 503)


def write(db: Session, client_id: int, source_id: str, command: _Command, actor: str) -> dict:
    _pristine(db)
    if not isinstance(actor, str) or not actor or len(actor) > 128:
        raise CRTISBAError("INTERNAL_ERROR", 500)
    acquired, phase = False, "BEFORE_TRANSACTION"
    try:
        _begin(db, write=True); acquired, phase = True, "IN_TRANSACTION"
        if db.get(Client, client_id) is None:
            raise CRTISBAError("CLIENT_NOT_FOUND", 404, ["/path/client_id"])
        planning, blocked = _planning(db, client_id, command.operation, source_id)
        if blocked:
            _rollback(db)
            return blocked
        _lock_source(db, client_id, source_id, command.source_kind)
        if command.expected_planning_calculation_input_fingerprint != planning["planning_calculation_input_fingerprint"]:
            raise CRTISBAError(
                "CRTISBA_PLANNING_IDENTITY_STALE", 409,
                ["/expected_planning_calculation_input_fingerprint"],
            )
        latest = db.scalar(select(Decision).where(Decision.client_id == client_id, Decision.source_kind == command.source_kind, Decision.source_id == source_id).order_by(desc(Decision.decision_version)).limit(1).with_for_update())
        blocked, snapshot = _derive_snapshot(db, client_id, command.operation, source_id)
        if blocked:
            _rollback(db)
            return blocked
        planning = snapshot["planning"]
        context = snapshot["contexts"].get(source_id)
        rtisa_entry = next((item for item in snapshot["rtisa"]["source_entries"] if item.get("source_id") == source_id), None)
        if context is None or rtisa_entry is None:
            raise CRTISBAError("CRTISBA_SOURCE_NOT_FOUND", 404, ["/path/source_id"])
        if context["kind"] != command.source_kind:
            raise CRTISBAError("CRTISBA_SOURCE_KIND_MISMATCH", 409, ["/source_kind"])
        if rtisa_entry.get("admission_state") == "EXCLUDED" or (rtisa_entry.get("source_category") == "PENSION_REPRESENTATION"):
            raise CRTISBAError("CRTISBA_SOURCE_DECISION_FORBIDDEN", 409, ["/path/source_id"])
        observed = {
            "planning": planning["planning_calculation_input_fingerprint"], "source_version": context["source_version"],
            "source_fingerprint": context["source_fingerprint"], "amount": context["amount"],
            "decision_version": latest.decision_version if latest else 0,
        }
        checks = [
            (command.expected_planning_calculation_input_fingerprint, observed["planning"], "CRTISBA_PLANNING_IDENTITY_STALE", "/expected_planning_calculation_input_fingerprint"),
            (command.expected_source_version, observed["source_version"], "CRTISBA_SOURCE_VERSION_STALE", "/expected_source_version"),
            (command.expected_source_fingerprint, observed["source_fingerprint"], "CRTISBA_SOURCE_FINGERPRINT_STALE", "/expected_source_fingerprint"),
            (command.expected_amount_authority_fingerprint, observed["amount"], "CRTISBA_AMOUNT_AUTHORITY_STALE", "/expected_amount_authority_fingerprint"),
            (command.expected_decision_version, observed["decision_version"], "CRTISBA_DECISION_VERSION_CONFLICT", "/expected_decision_version"),
        ]
        if observed["amount"] is None:
            raise CRTISBAError("CRTISBA_AMOUNT_AUTHORITY_UNAVAILABLE", 409, ["/expected_amount_authority_fingerprint"])
        for expected, actual, code, field in checks:
            if expected != actual:
                raise CRTISBAError(code, 409, [field])
        if observed["decision_version"] == MAX_VERSION:
            raise CRTISBAError("CRTISBA_DECISION_VERSION_EXHAUSTED", 409, ["/expected_decision_version"])
        version = observed["decision_version"] + 1
        if command.source_kind == "PENSION":
            income_basis = getattr(command, "income_basis", "UNKNOWN") if command.operation == "CLASSIFY" else "UNKNOWN"
            income_provenance = "EXPLICIT_PROFESSIONAL" if command.operation == "CLASSIFY" else "MISSING"
            price_basis = price_date = price_provenance = None
        else:
            native_basis = rtisa_entry.get("native_income_basis")
            income_basis = native_basis if native_basis in {"GROSS", "NET"} else "UNKNOWN"
            income_provenance = "UPSTREAM_RECURRING_AMOUNT_BASIS" if income_basis != "UNKNOWN" else "MISSING"
            price_basis = getattr(command, "price_basis", "UNKNOWN") if command.operation == "CLASSIFY" else "UNKNOWN"
            raw_price_date = getattr(command, "price_reference_date", None) if command.operation == "CLASSIFY" else None
            price_date = date.fromisoformat(raw_price_date) if raw_price_date else None
            price_provenance = "EXPLICIT_PROFESSIONAL" if command.operation == "CLASSIFY" else "MISSING"
        values = {
            "client_id": client_id, "source_id": source_id, "source_kind": command.source_kind,
            "decision_version": version, "planning_calculation_input_fingerprint": observed["planning"],
            "source_version": observed["source_version"], "source_fingerprint": observed["source_fingerprint"],
            "amount_authority_fingerprint": observed["amount"], "income_basis": income_basis,
            "income_basis_provenance": income_provenance, "price_basis": price_basis,
            "price_reference_date": price_date, "price_basis_provenance": price_provenance,
        }
        row = Decision(
            **{key: values[key] for key in ("client_id", "source_id", "source_kind", "decision_version", "planning_calculation_input_fingerprint", "source_fingerprint", "amount_authority_fingerprint", "income_basis", "income_basis_provenance", "price_basis", "price_reference_date", "price_basis_provenance")},
            pension_source_version=observed["source_version"] if command.source_kind == "PENSION" else None,
            recurring_source_version_fingerprint=observed["source_version"] if command.source_kind == "RECURRING_INCOME" else None,
            pension_source_execution_fingerprint=context.get("pension_source_execution_fingerprint"),
            pension_source_result_fingerprint=context.get("pension_source_result_fingerprint"),
            portfolio_source_entry_fingerprint=context.get("portfolio_source_entry_fingerprint"),
            retirement_target_date=date.fromisoformat(context["retirement_target_date"]) if command.source_kind == "PENSION" else None,
            decision_actor=actor, decision_fingerprint=decision_fingerprint(values),
        )
        db.add(row); phase = "FLUSHING"; db.flush(); phase = "FLUSHED"
        result = {
            "schema_version": "CRTISBA_WRITE_RESULT_V1", **values,
            "decision_state": "UNKNOWN" if command.operation == "CLEAR" else "CURRENT",
            "decision_fingerprint": row.decision_fingerprint,
            "price_reference_date": price_date.isoformat() if isinstance(price_date, date) else None,
        }
        if command.source_kind == "PENSION":
            result.update(
                price_basis="NOMINAL_AT_RETIREMENT_TARGET_DATE",
                price_reference_date=None,
                price_basis_provenance="OWNER_DECISION_OD2",
            )
        phase = "COMMIT_DISPATCHED"; db.commit(); phase = "COMMITTED"
        return result
    except CRTISBAError:
        if db.in_transaction(): _rollback(db)
        raise
    except DBAPIError as exc:
        classified = _classify_integrity(exc, phase)
        if classified.code == "CRTISBA_COMMIT_OUTCOME_UNKNOWN":
            try: db.connection().invalidate()
            except Exception: pass
            db.close()
        elif db.in_transaction():
            _rollback(db)
        raise classified from exc
    except Exception as exc:
        if db.in_transaction(): _rollback(db)
        raise CRTISBAError("INTERNAL_ERROR", 500) from exc
