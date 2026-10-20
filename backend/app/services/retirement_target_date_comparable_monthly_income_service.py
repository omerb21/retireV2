"""Canonical comparable monthly-income authority at the retirement target date."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from fractions import Fraction
import hashlib
import json
import re
from types import MappingProxyType
from typing import Any, Mapping

from sqlalchemy import event
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import Session

from app.services import retirement_target_date_income_comparison_basis_service as rticb_service
from app.services import retirement_target_date_income_source_basis_service as crtisba_service


SUCCESS_SCHEMA = "CANONICAL_RETIREMENT_TARGET_DATE_COMPARABLE_MONTHLY_INCOME_RESULT_V1"
BLOCK_SCHEMA = "CANONICAL_RETIREMENT_TARGET_DATE_COMPARABLE_MONTHLY_INCOME_BLOCK_NO_TOTAL_V1"
CONTRIBUTION_CONTRACT = "CANONICAL_RETIREMENT_TARGET_DATE_COMPARABLE_MONTHLY_INCOME_CONTRIBUTION_JSON_V1"
RESULT_CONTRACT = "CANONICAL_RETIREMENT_TARGET_DATE_COMPARABLE_MONTHLY_INCOME_RESULT_JSON_V1"
BLOCK_CONTRACT = "CANONICAL_RETIREMENT_TARGET_DATE_COMPARABLE_MONTHLY_INCOME_BLOCK_JSON_V1"

REQUEST_FIELDS = frozenset({
    "client_id", "expected_planning_calculation_input_fingerprint",
    "expected_retirement_target_date",
})
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z", re.ASCII)
DECIMAL_RE = re.compile(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?\Z", re.ASCII)
INTEGER_RE = re.compile(r"(?:0|[1-9][0-9]*)\Z", re.ASCII)
POSITIVE_INTEGER_RE = re.compile(r"[1-9][0-9]*\Z", re.ASCII)

SUCCESS_FIELDS = frozenset({
    "schema_version", "result_state", "client_id",
    "planning_calculation_input_fingerprint", "retirement_target_date",
    "target_result_fingerprint", "target_semantic_fingerprint",
    "comparison_input_fingerprint", "comparison_result_fingerprint",
    "crtisba_result_fingerprint", "rtisa_admission_result_fingerprint",
    "target_income_basis", "target_price_basis", "target_price_reference_date",
    "included_contributions", "excluded_source_ids", "total_monthly_equivalent",
    "source_count", "result_fingerprint",
})
BLOCK_FIELDS = frozenset({
    "schema_version", "result_state", "client_id",
    "supplied_planning_calculation_input_fingerprint", "supplied_retirement_target_date",
    "observed_comparison_result_fingerprint", "observed_crtisba_result_fingerprint",
    "observed_rtisa_admission_result_fingerprint", "observed_upstream_failure_stage",
    "observed_upstream_failure_detail_code", "observed_upstream_failure_fingerprint",
    "failure_stage", "failure_detail_code", "blocked_source_ids", "result_fingerprint",
})
CONTRIBUTION_FIELDS = frozenset({
    "source_id", "source_kind", "source_version", "source_fingerprint",
    "amount_authority_fingerprint", "source_comparison_fingerprint",
    "monthly_equivalent", "contribution_fingerprint",
})
RATIONAL_FIELDS = frozenset({"numerator", "denominator", "currency", "frequency"})


class _CMIAErrorMixin:
    def __setattr__(self, name: str, value: Any) -> None:
        if name in {"_stage", "_code", "_client_id"} and hasattr(self, name):
            raise AttributeError(f"{name.removeprefix('_')} is immutable")
        object.__setattr__(self, name, value)

    def _set_identity(self, stage: str, code: str, client_id: int | None) -> None:
        object.__setattr__(self, "_stage", stage)
        object.__setattr__(self, "_code", code)
        object.__setattr__(self, "_client_id", client_id)

    @property
    def stage(self) -> str:
        return self._stage

    @property
    def code(self) -> str:
        return self._code

    @property
    def client_id(self) -> int | None:
        return self._client_id


class CMIAContractError(_CMIAErrorMixin, ValueError):
    def __init__(self, stage: str, code: str, client_id: int | None, cause: BaseException | None = None):
        ValueError.__init__(self, stage, code, client_id)
        self._set_identity(stage, code, client_id)
        if cause is not None:
            self.__cause__ = cause


class CMIANumericError(_CMIAErrorMixin, ArithmeticError):
    def __init__(self, client_id: int, cause: BaseException | None = None):
        ArithmeticError.__init__(self, "aggregation", "CMIA_AGGREGATION_NUMERIC_ERROR", client_id)
        self._set_identity("aggregation", "CMIA_AGGREGATION_NUMERIC_ERROR", client_id)
        if cause is not None:
            self.__cause__ = cause


class CMIAFingerprintError(_CMIAErrorMixin, RuntimeError):
    def __init__(self, client_id: int, cause: BaseException | None = None):
        RuntimeError.__init__(self, "result_identity", "CMIA_RESULT_FINGERPRINT_CONSTRUCTION_FAILED", client_id)
        self._set_identity("result_identity", "CMIA_RESULT_FINGERPRINT_CONSTRUCTION_FAILED", client_id)
        if cause is not None:
            self.__cause__ = cause


class CMIAResultValidationError(_CMIAErrorMixin, ValueError):
    def __init__(self, client_id: int | None):
        ValueError.__init__(self, "result_validation", "CMIA_PUBLIC_RESULT_INVALID", client_id)
        self._set_identity("result_validation", "CMIA_PUBLIC_RESULT_INVALID", client_id)


@dataclass(frozen=True)
class ValidatedCMIAResult:
    result_state: str
    result: Mapping[str, Any]


def _positive_int(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value > 0


def _is_sha(value: Any) -> bool:
    return isinstance(value, str) and SHA256_RE.fullmatch(value) is not None


def _is_date(value: Any) -> bool:
    if not isinstance(value, str) or DATE_RE.fullmatch(value) is None:
        return False
    try:
        from datetime import date
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def _validated_request(request: Any) -> Mapping[str, Any]:
    client_id = request.get("client_id") if isinstance(request, Mapping) else None
    observed_client_id = client_id if _positive_int(client_id) else None
    if not isinstance(request, Mapping) or set(request) != REQUEST_FIELDS:
        raise CMIAContractError("request_validation", "CMIA_REQUEST_SCHEMA_INVALID", observed_client_id)
    if not _positive_int(client_id):
        raise CMIAContractError("request_validation", "CMIA_CLIENT_ID_INVALID", None)
    if not _is_sha(request["expected_planning_calculation_input_fingerprint"]):
        raise CMIAContractError(
            "request_validation", "CMIA_EXPECTED_PLANNING_FINGERPRINT_INVALID", client_id,
        )
    if not _is_date(request["expected_retirement_target_date"]):
        raise CMIAContractError(
            "request_validation", "CMIA_EXPECTED_RETIREMENT_TARGET_DATE_INVALID", client_id,
        )
    return request


def _canonical_bytes(value: Any, client_id: int) -> bytes:
    try:
        return json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CMIAFingerprintError(client_id, exc) from exc


def _fingerprint(value: Any, client_id: int) -> str:
    return hashlib.sha256(_canonical_bytes(value, client_id)).hexdigest()


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return deepcopy(value)


def _result_validation_error(value: Any) -> None:
    client_id = value.get("client_id") if isinstance(value, Mapping) else None
    raise CMIAResultValidationError(client_id if _positive_int(client_id) else None)


def _public_fingerprint(value: Any, contract: str, member: str) -> str | None:
    try:
        raw = json.dumps(
            {"contract": contract, member: value},
            ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError):
        return None
    return hashlib.sha256(raw).hexdigest()


def _canonical_rational(value: Any) -> Fraction | None:
    if not isinstance(value, dict) or set(value) != RATIONAL_FIELDS:
        return None
    numerator = value.get("numerator")
    denominator = value.get("denominator")
    if (
        not isinstance(numerator, str) or INTEGER_RE.fullmatch(numerator) is None
        or not isinstance(denominator, str) or POSITIVE_INTEGER_RE.fullmatch(denominator) is None
        or value.get("currency") != "ILS" or value.get("frequency") != "MONTHLY"
    ):
        return None
    fraction = Fraction(int(numerator), int(denominator))
    if str(fraction.numerator) != numerator or str(fraction.denominator) != denominator:
        return None
    return fraction


def _sorted_unique_strings(value: Any) -> bool:
    return (
        isinstance(value, list)
        and all(isinstance(item, str) and item for item in value)
        and value == sorted(set(value))
    )


def _contribution_valid(value: Any) -> tuple[bool, Fraction | None]:
    if not isinstance(value, dict) or set(value) != CONTRIBUTION_FIELDS:
        return False, None
    source_id = value.get("source_id")
    source_kind = value.get("source_kind")
    source_version = value.get("source_version")
    if (
        not isinstance(source_id, str) or not source_id
        or source_kind not in {"PENSION", "RECURRING_INCOME"}
        or (source_kind == "PENSION" and not _positive_int(source_version))
        or (source_kind == "RECURRING_INCOME" and not _is_sha(source_version))
        or not all(_is_sha(value.get(key)) for key in (
            "source_fingerprint", "amount_authority_fingerprint",
            "source_comparison_fingerprint", "contribution_fingerprint",
        ))
    ):
        return False, None
    rational = _canonical_rational(value.get("monthly_equivalent"))
    payload = {key: deepcopy(item) for key, item in value.items() if key != "contribution_fingerprint"}
    expected = _public_fingerprint(payload, CONTRIBUTION_CONTRACT, "contribution")
    return rational is not None and value["contribution_fingerprint"] == expected, rational


def validate_public_result(result: Mapping[str, Any]) -> ValidatedCMIAResult:
    """Purely validate and freeze an accepted public CMIA result."""
    if not isinstance(result, dict) or not _positive_int(result.get("client_id")):
        _result_validation_error(result)
    state = result.get("result_state")
    if state == "COMPLETE":
        if set(result) != SUCCESS_FIELDS or result.get("schema_version") != SUCCESS_SCHEMA:
            _result_validation_error(result)
        reference = result.get("target_price_reference_date")
        price_basis = result.get("target_price_basis")
        if (
            not _is_sha(result.get("planning_calculation_input_fingerprint"))
            or not _is_date(result.get("retirement_target_date"))
            or not all(_is_sha(result.get(key)) for key in (
                "target_result_fingerprint", "target_semantic_fingerprint",
                "comparison_input_fingerprint", "comparison_result_fingerprint",
                "crtisba_result_fingerprint", "rtisa_admission_result_fingerprint",
                "result_fingerprint",
            ))
            or result.get("target_income_basis") not in {"GROSS", "NET"}
            or price_basis not in {"NOMINAL_AT_RETIREMENT_TARGET_DATE", "REAL_AT_REFERENCE_DATE"}
            or not (
                (price_basis == "NOMINAL_AT_RETIREMENT_TARGET_DATE" and reference is None)
                or (price_basis == "REAL_AT_REFERENCE_DATE" and _is_date(reference))
            )
            or not isinstance(result.get("source_count"), int)
            or isinstance(result.get("source_count"), bool)
            or result["source_count"] < 0
            or not _sorted_unique_strings(result.get("excluded_source_ids"))
            or not isinstance(result.get("included_contributions"), list)
        ):
            _result_validation_error(result)
        included_ids: list[str] = []
        total = Fraction(0, 1)
        for contribution in result["included_contributions"]:
            valid, rational = _contribution_valid(contribution)
            if not valid or rational is None:
                _result_validation_error(result)
            included_ids.append(contribution["source_id"])
            total += rational
        if (
            included_ids != sorted(set(included_ids))
            or set(included_ids).intersection(result["excluded_source_ids"])
            or result["source_count"] != len(included_ids)
            or _canonical_rational(result.get("total_monthly_equivalent")) != total
        ):
            _result_validation_error(result)
        payload = {key: deepcopy(item) for key, item in result.items() if key != "result_fingerprint"}
        if result["result_fingerprint"] != _public_fingerprint(payload, RESULT_CONTRACT, "result"):
            _result_validation_error(result)
    elif state == "BLOCK_NO_TOTAL":
        if (
            set(result) != BLOCK_FIELDS or result.get("schema_version") != BLOCK_SCHEMA
            or not _is_sha(result.get("supplied_planning_calculation_input_fingerprint"))
            or not _is_date(result.get("supplied_retirement_target_date"))
            or not _is_sha(result.get("result_fingerprint"))
            or not _sorted_unique_strings(result.get("blocked_source_ids"))
        ):
            _result_validation_error(result)
        if result.get("failure_stage") == "comparability":
            valid_variant = (
                result.get("failure_detail_code") == "CMIA_DIRECT_COMPARISON_NOT_READY"
                and all(_is_sha(result.get(key)) for key in (
                    "observed_comparison_result_fingerprint",
                    "observed_crtisba_result_fingerprint",
                    "observed_rtisa_admission_result_fingerprint",
                ))
                and all(result.get(key) is None for key in (
                    "observed_upstream_failure_stage", "observed_upstream_failure_detail_code",
                    "observed_upstream_failure_fingerprint",
                ))
                and bool(result["blocked_source_ids"])
            )
        elif result.get("failure_stage") == "upstream_authority":
            valid_variant = (
                result.get("failure_detail_code") == "CMIA_UPSTREAM_COMPARISON_BLOCKED"
                and all(result.get(key) is None for key in (
                    "observed_comparison_result_fingerprint",
                    "observed_crtisba_result_fingerprint",
                    "observed_rtisa_admission_result_fingerprint",
                ))
                and result.get("observed_upstream_failure_stage") in rticb_service.FAILURE_CODES
                and result.get("observed_upstream_failure_detail_code")
                in rticb_service.FAILURE_CODES[result["observed_upstream_failure_stage"]]
                and _is_sha(result.get("observed_upstream_failure_fingerprint"))
                and result["blocked_source_ids"] == []
            )
        else:
            valid_variant = False
        payload = {key: deepcopy(item) for key, item in result.items() if key != "result_fingerprint"}
        if not valid_variant or result["result_fingerprint"] != _public_fingerprint(
            payload, BLOCK_CONTRACT, "result",
        ):
            _result_validation_error(result)
    else:
        _result_validation_error(result)
    return ValidatedCMIAResult(state, _freeze(result))


def _contract(stage: str, code: str, client_id: int, cause: BaseException | None = None):
    raise CMIAContractError(stage, code, client_id, cause) from cause


def _begin_snapshot(db: Session, connection: Any, client_id: int) -> None:
    try:
        dialect = connection.dialect.name
        if dialect == "postgresql":
            connection.exec_driver_sql("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        elif dialect == "sqlite":
            connection.exec_driver_sql("BEGIN")
        else:
            _contract("snapshot_admission", "CMIA_UNSUPPORTED_DATABASE", client_id)
        db.expire_all()
    except CMIAContractError:
        raise


def _reject_poisoned_session_reuse(_session: Session, _transaction: Any) -> None:
    raise InvalidRequestError("CMIA Session is permanently unusable after rollback failure")


def _poison_session(db: Session) -> None:
    if not event.contains(db, "after_transaction_create", _reject_poisoned_session_reuse):
        event.listen(db, "after_transaction_create", _reject_poisoned_session_reuse)
    db.invalidate()


def _rollback_owned_transaction(db: Session, connection: Any | None) -> None:
    try:
        db.rollback()
    except BaseException:
        if connection is not None:
            try:
                connection.invalidate()
            except BaseException:
                pass
        try:
            _poison_session(db)
        except BaseException:
            pass
        raise


def _rational(value: Any, client_id: int) -> Fraction:
    if not isinstance(value, Mapping) or set(value) != {"numerator", "denominator"}:
        _contract("amount_authority", "CMIA_RTISA_AMOUNT_INVALID", client_id)
    numerator = value["numerator"]
    denominator = value["denominator"]
    if (
        not isinstance(numerator, str) or DECIMAL_RE.fullmatch(numerator) is None
        or not isinstance(denominator, str) or POSITIVE_INTEGER_RE.fullmatch(denominator) is None
    ):
        _contract("amount_authority", "CMIA_RTISA_AMOUNT_INVALID", client_id)
    whole, dot, fraction = numerator.partition(".")
    scale = 10 ** len(fraction) if dot else 1
    coefficient = int(whole) * scale + (int(fraction) if fraction else 0)
    try:
        return Fraction(coefficient, scale * int(denominator))
    except (ArithmeticError, ValueError) as exc:
        _contract("amount_authority", "CMIA_RTISA_AMOUNT_INVALID", client_id, exc)


def _rational_payload(value: Fraction) -> dict[str, str]:
    return {
        "numerator": str(value.numerator), "denominator": str(value.denominator),
        "currency": "ILS", "frequency": "MONTHLY",
    }


def _planning_sources(planning: Mapping[str, Any], client_id: int) -> dict[str, Mapping[str, Any]]:
    sources: dict[str, Mapping[str, Any]] = {}
    for key in ("pension_inputs", "general_income_inputs", "excluded_sources"):
        values = planning.get(key)
        if not isinstance(values, list):
            _contract("crtisba_authority", "CMIA_CRTISBA_AUTHORITY_INVALID", client_id)
        for value in values:
            if not isinstance(value, Mapping) or not isinstance(value.get("source_id"), str):
                _contract("crtisba_authority", "CMIA_CRTISBA_AUTHORITY_INVALID", client_id)
            source_id = value["source_id"]
            if source_id in sources:
                _contract("source_universe", "CMIA_SOURCE_UNIVERSE_MISMATCH", client_id)
            sources[source_id] = value
    return sources


def _indexed(values: Any, client_id: int, *, stage: str, code: str) -> dict[str, Mapping[str, Any]]:
    if not isinstance(values, list):
        _contract(stage, code, client_id)
    result: dict[str, Mapping[str, Any]] = {}
    ids: list[str] = []
    for value in values:
        if not isinstance(value, Mapping) or not isinstance(value.get("source_id"), str):
            _contract(stage, code, client_id)
        source_id = value["source_id"]
        ids.append(source_id)
        if source_id in result:
            _contract("source_universe", "CMIA_SOURCE_UNIVERSE_MISMATCH", client_id)
        result[source_id] = value
    if ids != sorted(ids):
        _contract("source_universe", "CMIA_SOURCE_UNIVERSE_MISMATCH", client_id)
    return result


def _decimal_equal(left: Any, right: Any) -> bool:
    try:
        return Decimal(str(left)).is_finite() and Decimal(str(left)) == Decimal(str(right))
    except (InvalidOperation, ValueError):
        return False


def _reconstruct_amount(
    source_id: str, comparison: Mapping[str, Any], rtisa_entry: Mapping[str, Any],
    planning: Mapping[str, Any], portfolio: Mapping[str, Any], context: Mapping[str, Any],
    planning_sources: Mapping[str, Mapping[str, Any]], client_id: int,
) -> tuple[dict[str, Any], Mapping[str, Any]]:
    source = planning_sources.get(source_id)
    upstream = rtisa_entry.get("upstream_identity")
    monthly = rtisa_entry.get("monthly_equivalent")
    if not isinstance(source, Mapping) or not isinstance(upstream, Mapping) or not isinstance(context, Mapping):
        _contract("amount_authority", "CMIA_RTISA_AMOUNT_INVALID", client_id)
    source_fp = upstream.get("source_fingerprint")
    if not _is_sha(source_fp) or source_fp != comparison.get("source_fingerprint"):
        _contract("amount_authority", "CMIA_AMOUNT_AUTHORITY_FINGERPRINT_MISMATCH", client_id)
    if comparison.get("source_kind") == "PENSION":
        results = _indexed(
            portfolio.get("source_results"), client_id,
            stage="amount_authority", code="CMIA_RTISA_AMOUNT_INVALID",
        )
        fingerprints = _indexed(
            portfolio.get("source_entry_fingerprints"), client_id,
            stage="amount_authority", code="CMIA_RTISA_AMOUNT_INVALID",
        )
        pte = results.get(source_id)
        entry_fingerprint = fingerprints.get(source_id)
        basis = source.get("monthly_amount_basis")
        temporal = source.get("temporal_authority")
        if not all(isinstance(item, Mapping) for item in (pte, entry_fingerprint, basis, temporal)):
            _contract("amount_authority", "CMIA_RTISA_AMOUNT_INVALID", client_id)
        if not _decimal_equal((monthly or {}).get("numerator"), pte.get("unquantized_target_monthly_amount")):
            _contract("amount_authority", "CMIA_RTISA_AMOUNT_INVALID", client_id)
        preimage = {
            "contract": crtisba_service.PENSION_AMOUNT_CONTRACT,
            "client_id": client_id, "source_id": source_id,
            "source_version": source.get("version"), "source_fingerprint": source_fp,
            "base_amount_semantic_fingerprint": basis.get("base_amount_semantic_fingerprint"),
            "base_amount_source_fingerprint": basis.get("base_amount_source_fingerprint"),
            "temporal_semantic_fingerprint": temporal.get("temporal_semantic_fingerprint"),
            "temporal_source_fingerprint": temporal.get("temporal_source_fingerprint"),
            "planning_calculation_input_fingerprint": planning.get("planning_calculation_input_fingerprint"),
            "retirement_target_date": (planning.get("retirement_target") or {}).get("retirement_target_date"),
            "pension_source_execution_fingerprint": pte.get("source_execution_fingerprint"),
            "pension_source_result_fingerprint": upstream.get("pension_source_result_fingerprint"),
            "portfolio_source_entry_fingerprint": entry_fingerprint.get("source_entry_fingerprint"),
            "amount": {
                "numerator": (monthly or {}).get("numerator"), "denominator": "1",
                "currency": "ILS", "frequency": "MONTHLY",
            },
        }
    elif comparison.get("source_kind") == "RECURRING_INCOME":
        frequency_denominator = {"monthly": "1", "quarterly": "3", "annual": "12"}.get(source.get("frequency"))
        try:
            source_amount = crtisba_service._decimal_text(source.get("amount"))
        except Exception as exc:
            _contract("amount_authority", "CMIA_RTISA_AMOUNT_INVALID", client_id, exc)
        if (
            frequency_denominator is None
            or not isinstance(monthly, Mapping)
            or monthly.get("numerator") != source_amount
            or monthly.get("denominator") != frequency_denominator
        ):
            _contract("amount_authority", "CMIA_RTISA_AMOUNT_INVALID", client_id)
        preimage = {
            "contract": crtisba_service.RECURRING_AMOUNT_CONTRACT,
            "client_id": client_id, "source_id": source_id, "source_fingerprint": source_fp,
            "amount": source_amount, "amount_basis": source.get("amount_basis"),
            "frequency": source.get("frequency"),
        }
    else:
        _contract("amount_authority", "CMIA_RTISA_AMOUNT_INVALID", client_id)
    context_preimage = context.get("amount_preimage")
    if context_preimage != preimage or context.get("monthly_equivalent") != monthly:
        _contract("amount_authority", "CMIA_AMOUNT_AUTHORITY_FINGERPRINT_MISMATCH", client_id)
    try:
        expected = crtisba_service.fingerprint(preimage)
    except Exception as exc:
        _contract("amount_authority", "CMIA_AMOUNT_AUTHORITY_FINGERPRINT_MISMATCH", client_id, exc)
    if (
        expected != context.get("amount")
        or expected != comparison.get("amount_authority_fingerprint")
    ):
        _contract("amount_authority", "CMIA_AMOUNT_AUTHORITY_FINGERPRINT_MISMATCH", client_id)
    return preimage, monthly


def _blocked(
    request: Mapping[str, Any], *, comparison: Mapping[str, Any],
    collection: Mapping[str, Any] | None, rtisa: Mapping[str, Any] | None,
) -> dict:
    upstream = comparison.get("result_state") == "block_no_result"
    result = {
        "schema_version": BLOCK_SCHEMA, "result_state": "BLOCK_NO_TOTAL",
        "client_id": request["client_id"],
        "supplied_planning_calculation_input_fingerprint": request["expected_planning_calculation_input_fingerprint"],
        "supplied_retirement_target_date": request["expected_retirement_target_date"],
        "observed_comparison_result_fingerprint": None if upstream else comparison.get("comparison_result_fingerprint"),
        "observed_crtisba_result_fingerprint": None if upstream else collection.get("result_fingerprint") if collection else None,
        "observed_rtisa_admission_result_fingerprint": None if upstream else rtisa.get("admission_result_fingerprint") if rtisa else None,
        "observed_upstream_failure_stage": comparison.get("failure_stage") if upstream else None,
        "observed_upstream_failure_detail_code": comparison.get("failure_detail_code") if upstream else None,
        "observed_upstream_failure_fingerprint": comparison.get("result_fingerprint") if upstream else None,
        "failure_stage": "upstream_authority" if upstream else "comparability",
        "failure_detail_code": "CMIA_UPSTREAM_COMPARISON_BLOCKED" if upstream else "CMIA_DIRECT_COMPARISON_NOT_READY",
        "blocked_source_ids": [] if upstream else sorted(
            item["source_id"] for item in comparison["source_comparisons"]
            if item["comparison_state"] in {"NORMALIZATION_REQUIRED", "BASIS_UNRESOLVED"}
        ),
    }
    result["result_fingerprint"] = _fingerprint(
        {"contract": BLOCK_CONTRACT, "result": deepcopy(result)}, request["client_id"],
    )
    return result


def _complete(request: Mapping[str, Any], evidence: Mapping[str, Any]) -> dict:
    client_id = request["client_id"]
    comparison = evidence["comparison"]
    target = evidence["target"]
    collection = evidence["crtisba_collection"]
    rtisa = evidence["rtisa"]
    planning = evidence["planning"]
    portfolio = evidence["portfolio"]
    contexts = evidence["amount_contexts"]
    if not all(isinstance(item, Mapping) for item in (target, collection, rtisa, planning, portfolio, contexts)):
        _contract("crtisba_authority", "CMIA_CRTISBA_AUTHORITY_INVALID", client_id)
    try:
        if not rticb_service._target_schema_valid(target) or not rticb_service._target_fingerprints_valid(target):
            _contract("target_authority", "CMIA_TARGET_AUTHORITY_INVALID", client_id)
        if not (
            target["authority_state"] == "CURRENT"
            and target["target_readiness_state"] == "READY"
            and target["target_ready"] is True
            and target["target"] is not None
            and target["authority"] is not None
            and target["authority"]["confirmation_state"] == "CONFIRMED"
            and not target["blockers"]
        ):
            _contract("target_authority", "CMIA_TARGET_AUTHORITY_INVALID", client_id)
        if (
            not crtisba_service._planning_envelope_valid(planning, client_id)
            or not crtisba_service.rtisa_service._portfolio_is_valid(
                portfolio, client_id, planning,
                planning["retirement_target"]["retirement_target_date"],
            )
            or not crtisba_service._rtisa_envelope_valid(rtisa, client_id, planning, portfolio)
            or not rticb_service._collection_shape(collection)
            or not rticb_service._collection_fingerprint_valid(collection)
        ):
            _contract("crtisba_authority", "CMIA_CRTISBA_AUTHORITY_INVALID", client_id)
    except CMIAContractError:
        raise
    except Exception as exc:
        _contract("crtisba_authority", "CMIA_CRTISBA_AUTHORITY_INVALID", client_id, exc)
    if (
        comparison["crtisba_result_fingerprint"] != collection.get("result_fingerprint")
        or collection.get("rtisa_admission_result_fingerprint") != rtisa.get("admission_result_fingerprint")
    ):
        _contract("crtisba_authority", "CMIA_CRTISBA_AUTHORITY_INVALID", client_id)
    planning_fp = request["expected_planning_calculation_input_fingerprint"]
    target_date = request["expected_retirement_target_date"]
    if not (
        target.get("client_id") == collection.get("client_id") == rtisa.get("client_id")
        == planning.get("client_id") == portfolio.get("client_id") == client_id
        and target.get("planning_calculation_input_fingerprint")
        == collection.get("planning_calculation_input_fingerprint")
        == rtisa.get("planning_calculation_input_fingerprint")
        == planning.get("planning_calculation_input_fingerprint")
        == portfolio.get("planning_calculation_input_fingerprint") == planning_fp
        and target.get("retirement_target_date") == collection.get("retirement_target_date")
        == rtisa.get("retirement_target_date") == portfolio.get("retirement_target_date") == target_date
        and (planning.get("retirement_target") or {}).get("retirement_target_date") == target_date
    ):
        _contract("cross_authority_identity", "CMIA_CROSS_AUTHORITY_IDENTITY_MISMATCH", client_id)
    comparisons = _indexed(
        comparison.get("source_comparisons"), client_id,
        stage="classification", code="CMIA_COMPARISON_RESULT_INVALID",
    )
    bases = _indexed(
        collection.get("source_basis_entries"), client_id,
        stage="crtisba_authority", code="CMIA_CRTISBA_AUTHORITY_INVALID",
    )
    admissions = _indexed(
        rtisa.get("source_entries"), client_id,
        stage="crtisba_authority", code="CMIA_CRTISBA_AUTHORITY_INVALID",
    )
    planning_sources = _planning_sources(planning, client_id)
    universe = set(comparisons)
    if universe != set(bases) or universe != set(admissions) or universe != set(planning_sources) or universe != set(contexts):
        _contract("source_universe", "CMIA_SOURCE_UNIVERSE_MISMATCH", client_id)
    for source_id in sorted(universe):
        comparison_entry = comparisons[source_id]
        basis_entry = bases[source_id]
        admission_entry = admissions[source_id]
        if (
            comparison_entry.get("admission_state") != basis_entry.get("admission_state")
            or comparison_entry.get("admission_state") != admission_entry.get("admission_state")
            or comparison_entry.get("source_fingerprint") != basis_entry.get("source_fingerprint")
            or comparison_entry.get("source_fingerprint") != (admission_entry.get("upstream_identity") or {}).get("source_fingerprint")
            or comparison_entry.get("source_kind") != contexts[source_id].get("kind")
            or comparison_entry.get("source_version") != contexts[source_id].get("source_version")
            or comparison_entry.get("source_fingerprint") != contexts[source_id].get("source_fingerprint")
        ):
            _contract("source_universe", "CMIA_SOURCE_UNIVERSE_MISMATCH", client_id)
    if comparison["direct_comparison_state"] != "READY" or comparison["direct_comparison_ready"] is not True:
        return _blocked(request, comparison=comparison, collection=collection, rtisa=rtisa)
    contributions: list[dict[str, Any]] = []
    excluded: list[str] = []
    total = Fraction(0, 1)
    for source_id in sorted(universe):
        entry = comparisons[source_id]
        if entry["comparison_state"] == "NOT_ADMITTED":
            excluded.append(source_id)
            continue
        if entry["comparison_state"] != "DIRECTLY_COMPARABLE" or entry["admission_state"] != "INCLUDED":
            _contract("classification", "CMIA_COMPARISON_RESULT_INVALID", client_id)
        _preimage, monthly = _reconstruct_amount(
            source_id, entry, admissions[source_id], planning, portfolio,
            contexts[source_id], planning_sources, client_id,
        )
        rational = _rational(monthly, client_id)
        try:
            total += rational
        except ArithmeticError as exc:
            raise CMIANumericError(client_id, exc) from exc
        contribution = {
            "source_id": source_id, "source_kind": entry["source_kind"],
            "source_version": entry["source_version"], "source_fingerprint": entry["source_fingerprint"],
            "amount_authority_fingerprint": entry["amount_authority_fingerprint"],
            "source_comparison_fingerprint": entry["source_comparison_fingerprint"],
            "monthly_equivalent": _rational_payload(rational),
        }
        contribution["contribution_fingerprint"] = _fingerprint(
            {"contract": CONTRIBUTION_CONTRACT, "contribution": deepcopy(contribution)}, client_id,
        )
        contributions.append(contribution)
    target_basis = target["target"]
    result = {
        "schema_version": SUCCESS_SCHEMA, "result_state": "COMPLETE", "client_id": client_id,
        "planning_calculation_input_fingerprint": planning_fp, "retirement_target_date": target_date,
        "target_result_fingerprint": comparison["target_result_fingerprint"],
        "target_semantic_fingerprint": comparison["target_semantic_fingerprint"],
        "comparison_input_fingerprint": comparison["comparison_input_fingerprint"],
        "comparison_result_fingerprint": comparison["comparison_result_fingerprint"],
        "crtisba_result_fingerprint": comparison["crtisba_result_fingerprint"],
        "rtisa_admission_result_fingerprint": rtisa["admission_result_fingerprint"],
        "target_income_basis": target_basis["income_basis"],
        "target_price_basis": target_basis["price_basis"],
        "target_price_reference_date": target_basis["price_reference_date"],
        "included_contributions": contributions, "excluded_source_ids": excluded,
        "total_monthly_equivalent": _rational_payload(total), "source_count": len(contributions),
    }
    result["result_fingerprint"] = _fingerprint(
        {"contract": RESULT_CONTRACT, "result": deepcopy(result)}, client_id,
    )
    return result


def assess_with_target_in_snapshot(db: Session, request: Mapping[str, Any]) -> dict[str, Any]:
    """Compose CMIA and return its exact same-snapshot RIT target without owning cleanup."""
    request = _validated_request(request)
    client_id = request["client_id"]
    if not db.in_transaction():
        _contract("snapshot_admission", "CMIA_REQUIRES_FRESH_TRANSACTION", client_id)
    with db.no_autoflush:
        evidence = rticb_service.assess_with_evidence_in_snapshot(db, request)
        comparison = evidence.get("comparison") if isinstance(evidence, Mapping) else None
        if not rticb_service.public_result_valid(
            comparison, client_id,
            request["expected_planning_calculation_input_fingerprint"],
            request["expected_retirement_target_date"],
        ):
            _contract("classification", "CMIA_COMPARISON_RESULT_INVALID", client_id)
        if comparison.get("result_state") == "block_no_result":
            result = _blocked(request, comparison=comparison, collection=None, rtisa=None)
        else:
            result = _complete(request, evidence)
    return {"cmia_result": result, "target": evidence.get("target")}


def assess(db: Session, request: Mapping[str, Any]) -> dict:
    request = _validated_request(request)
    client_id = request["client_id"]
    if db.in_transaction() or db.new or db.dirty or db.deleted:
        _contract("snapshot_admission", "CMIA_REQUIRES_FRESH_TRANSACTION", client_id)
    if db.get_bind().dialect.name not in {"postgresql", "sqlite"}:
        _contract("snapshot_admission", "CMIA_UNSUPPORTED_DATABASE", client_id)
    owned_connection = None
    try:
        owned_connection = db.connection()
        _begin_snapshot(db, owned_connection, client_id)
        composition = assess_with_target_in_snapshot(db, request)
        result = composition["cmia_result"]
    except BaseException:
        transaction_owned = owned_connection is not None
        if not transaction_owned:
            try:
                transaction_owned = db.in_transaction()
            except BaseException:
                transaction_owned = False
        if transaction_owned:
            _rollback_owned_transaction(db, owned_connection)
        raise
    _rollback_owned_transaction(db, owned_connection)
    return result
