"""Exact retirement monthly-income gap authority (RMIGA)."""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import hashlib
import json
from math import gcd
import re
from typing import Any, Mapping

from sqlalchemy import event
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import Session

from app.services import retirement_target_date_comparable_monthly_income_service as cmia_service
from app.services import retirement_target_date_income_comparison_basis_service as rticb_service


SUCCESS_SCHEMA = "RETIREMENT_MONTHLY_INCOME_GAP_AUTHORITY_RESULT_V1"
BLOCK_SCHEMA = "RETIREMENT_MONTHLY_INCOME_GAP_AUTHORITY_BLOCK_NO_GAP_V1"
RESULT_CONTRACT = "RETIREMENT_MONTHLY_INCOME_GAP_AUTHORITY_RESULT_JSON_V1"
BLOCK_CONTRACT = "RETIREMENT_MONTHLY_INCOME_GAP_AUTHORITY_BLOCK_JSON_V1"
REQUEST_FIELDS = frozenset({
    "client_id", "expected_planning_calculation_input_fingerprint",
    "expected_retirement_target_date",
})
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z", re.ASCII)
TARGET_AMOUNT_RE = re.compile(r"(?:0|[1-9][0-9]*)(?:\.[0-9]{1,6})?\Z", re.ASCII)


class _RMIGAErrorMixin:
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


class RMIGAContractError(_RMIGAErrorMixin, ValueError):
    def __init__(self, stage: str, code: str, client_id: int | None, cause: BaseException | None = None):
        ValueError.__init__(self, stage, code, client_id)
        self._set_identity(stage, code, client_id)
        if cause is not None:
            self.__cause__ = cause


class RMIGANumericError(_RMIGAErrorMixin, ArithmeticError):
    def __init__(self, client_id: int, cause: BaseException | None = None):
        ArithmeticError.__init__(self, "arithmetic", "RMIGA_ARITHMETIC_ERROR", client_id)
        self._set_identity("arithmetic", "RMIGA_ARITHMETIC_ERROR", client_id)
        if cause is not None:
            self.__cause__ = cause


class RMIGAFingerprintError(_RMIGAErrorMixin, RuntimeError):
    def __init__(self, client_id: int, cause: BaseException | None = None):
        RuntimeError.__init__(
            self, "result_identity", "RMIGA_RESULT_FINGERPRINT_CONSTRUCTION_FAILED", client_id,
        )
        self._set_identity("result_identity", "RMIGA_RESULT_FINGERPRINT_CONSTRUCTION_FAILED", client_id)
        if cause is not None:
            self.__cause__ = cause


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


def _contract(stage: str, code: str, client_id: int | None, cause: BaseException | None = None):
    raise RMIGAContractError(stage, code, client_id, cause) from cause


def _validated_request(request: Any) -> Mapping[str, Any]:
    client_id = request.get("client_id") if isinstance(request, Mapping) else None
    observed_client_id = client_id if _positive_int(client_id) else None
    if not isinstance(request, Mapping) or set(request) != REQUEST_FIELDS:
        _contract("request_validation", "RMIGA_REQUEST_SCHEMA_INVALID", observed_client_id)
    if not _positive_int(client_id):
        _contract("request_validation", "RMIGA_CLIENT_ID_INVALID", None)
    if not _is_sha(request["expected_planning_calculation_input_fingerprint"]):
        _contract(
            "request_validation", "RMIGA_EXPECTED_PLANNING_FINGERPRINT_INVALID", client_id,
        )
    if not _is_date(request["expected_retirement_target_date"]):
        _contract(
            "request_validation", "RMIGA_EXPECTED_RETIREMENT_TARGET_DATE_INVALID", client_id,
        )
    return request


def _fingerprint(value: Any, client_id: int) -> str:
    try:
        raw = json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise RMIGAFingerprintError(client_id, exc) from exc
    return hashlib.sha256(raw).hexdigest()


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return deepcopy(value)


def _ascii_digits_to_int(value: str) -> int:
    chunk_size = 9
    first_size = len(value) % chunk_size or chunk_size
    number = int(value[:first_size])
    for offset in range(first_size, len(value), chunk_size):
        number = number * 1_000_000_000 + int(value[offset:offset + chunk_size])
    return number


def _int_to_ascii(value: int) -> str:
    if value == 0:
        return "0"
    negative = value < 0
    remaining = -value if negative else value
    chunks: list[int] = []
    while remaining:
        remaining, chunk = divmod(remaining, 1_000_000_000)
        chunks.append(chunk)
    rendered = str(chunks.pop()) + "".join(f"{chunk:09d}" for chunk in reversed(chunks))
    return "-" + rendered if negative else rendered


def _begin_snapshot(db: Session, connection: Any, client_id: int) -> None:
    dialect = connection.dialect.name
    if dialect == "postgresql":
        connection.exec_driver_sql("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
    elif dialect == "sqlite":
        connection.exec_driver_sql("BEGIN")
    else:
        _contract("snapshot_admission", "RMIGA_UNSUPPORTED_DATABASE", client_id)
    db.expire_all()


def _reject_poisoned_session_reuse(_session: Session, _transaction: Any) -> None:
    raise InvalidRequestError("RMIGA Session is permanently unusable after rollback failure")


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


def _target_fraction(value: Any, client_id: int) -> Fraction:
    if not isinstance(value, str) or TARGET_AMOUNT_RE.fullmatch(value) is None:
        _contract("amount_authority", "RMIGA_TARGET_AMOUNT_INVALID", client_id)
    whole, dot, fraction = value.partition(".")
    scale = 10 ** len(fraction) if dot else 1
    coefficient = _ascii_digits_to_int(whole) * scale + (
        _ascii_digits_to_int(fraction) if fraction else 0
    )
    if coefficient <= 0:
        _contract("amount_authority", "RMIGA_TARGET_AMOUNT_INVALID", client_id)
    return Fraction(coefficient, scale)


def _cmia_fraction(value: Any, client_id: int) -> Fraction:
    if not isinstance(value, Mapping) or set(value) != {
        "numerator", "denominator", "currency", "frequency",
    }:
        _contract("amount_authority", "RMIGA_COMPARABLE_AMOUNT_INVALID", client_id)
    try:
        numerator = value["numerator"]
        denominator = value["denominator"]
        if (
            not isinstance(numerator, str) or re.fullmatch(r"(?:0|[1-9][0-9]*)", numerator) is None
            or not isinstance(denominator, str) or re.fullmatch(r"[1-9][0-9]*", denominator) is None
            or value["currency"] != "ILS" or value["frequency"] != "MONTHLY"
        ):
            raise ValueError("noncanonical rational")
        numerator_value = _ascii_digits_to_int(numerator)
        denominator_value = _ascii_digits_to_int(denominator)
        if gcd(numerator_value, denominator_value) != 1:
            raise ValueError("unreduced rational")
        return Fraction(numerator_value, denominator_value)
    except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
        _contract("amount_authority", "RMIGA_COMPARABLE_AMOUNT_INVALID", client_id, exc)


def _rational_payload(value: Fraction) -> dict[str, str]:
    return {
        "numerator": _int_to_ascii(value.numerator),
        "denominator": _int_to_ascii(value.denominator),
        "currency": "ILS", "frequency": "MONTHLY",
    }


def _blocked_identity_valid(request: Mapping[str, Any], cmia: Mapping[str, Any]) -> bool:
    return (
        cmia["client_id"] == request["client_id"]
        and cmia["supplied_planning_calculation_input_fingerprint"]
        == request["expected_planning_calculation_input_fingerprint"]
        and cmia["supplied_retirement_target_date"]
        == request["expected_retirement_target_date"]
    )


def _block_result(request: Mapping[str, Any], cmia: Mapping[str, Any]) -> dict[str, Any]:
    client_id = request["client_id"]
    if not _blocked_identity_valid(request, cmia):
        _contract("cmia_authority", "RMIGA_CMIA_RESULT_INVALID", client_id)
    result = {
        "schema_version": BLOCK_SCHEMA, "result_state": "BLOCK_NO_GAP",
        "client_id": client_id,
        "supplied_planning_calculation_input_fingerprint": request[
            "expected_planning_calculation_input_fingerprint"
        ],
        "supplied_retirement_target_date": request["expected_retirement_target_date"],
        "observed_cmia_result_fingerprint": cmia["result_fingerprint"],
        "observed_cmia_failure_stage": cmia["failure_stage"],
        "observed_cmia_failure_detail_code": cmia["failure_detail_code"],
        "observed_cmia_blocked_source_ids": _thaw(cmia["blocked_source_ids"]),
        "failure_stage": "upstream_authority",
        "failure_detail_code": "RMIGA_COMPARABLE_INCOME_BLOCKED",
    }
    result["result_fingerprint"] = _fingerprint(
        {"contract": BLOCK_CONTRACT, "result": deepcopy(result)}, client_id,
    )
    return result


def _complete_identity_valid(
    request: Mapping[str, Any], cmia: Mapping[str, Any], target: Mapping[str, Any],
    target_value: Mapping[str, Any],
) -> bool:
    client_id = request["client_id"]
    planning = request["expected_planning_calculation_input_fingerprint"]
    target_date = request["expected_retirement_target_date"]
    return (
        target["client_id"] == target_value["client_id"] == cmia["client_id"] == client_id
        and target["planning_calculation_input_fingerprint"]
        == target_value["planning_calculation_input_fingerprint"]
        == cmia["planning_calculation_input_fingerprint"] == planning
        and target["retirement_target_date"] == target_value["retirement_target_date"]
        == cmia["retirement_target_date"] == target_date
        and target["target_result_fingerprint"] == cmia["target_result_fingerprint"]
        and target["target_semantic_fingerprint"] == cmia["target_semantic_fingerprint"]
    )


def _basis_valid(cmia: Mapping[str, Any], target_value: Mapping[str, Any]) -> bool:
    return (
        target_value["currency"] == cmia["total_monthly_equivalent"]["currency"] == "ILS"
        and target_value["income_basis"] == cmia["target_income_basis"]
        and target_value["price_basis"] == cmia["target_price_basis"]
        and target_value["price_reference_date"] == cmia["target_price_reference_date"]
    )


def _subtract(target_amount: Fraction, comparable: Fraction) -> Fraction:
    return target_amount - comparable


def _gap_state(gap: Fraction) -> str:
    return "SHORTFALL" if gap > 0 else "SURPLUS" if gap < 0 else "EQUAL"


def _source_projection(cmia: Mapping[str, Any]) -> tuple[Any, Any, Any]:
    return (
        _thaw(cmia["included_contributions"]),
        _thaw(cmia["excluded_source_ids"]),
        cmia["source_count"],
    )


def _complete_result(
    request: Mapping[str, Any], cmia: Mapping[str, Any], target: Any,
) -> dict[str, Any]:
    client_id = request["client_id"]
    try:
        target_valid = (
            rticb_service._target_schema_valid(target)
            and rticb_service._target_fingerprints_valid(target)
            and target["authority_state"] == "CURRENT"
            and target["target_readiness_state"] == "READY"
            and target["target_ready"] is True
            and target["target"] is not None
            and target["authority"] is not None
            and target["authority"]["confirmation_state"] == "CONFIRMED"
            and not target["blockers"]
        )
    except Exception as exc:
        _contract("target_authority", "RMIGA_TARGET_AUTHORITY_INVALID", client_id, exc)
    if not target_valid:
        _contract("target_authority", "RMIGA_TARGET_AUTHORITY_INVALID", client_id)
    target_value = target["target"]
    planning = request["expected_planning_calculation_input_fingerprint"]
    target_date = request["expected_retirement_target_date"]
    if not _complete_identity_valid(request, cmia, target, target_value):
        _contract("cross_authority_identity", "RMIGA_CROSS_AUTHORITY_IDENTITY_MISMATCH", client_id)
    if not _basis_valid(cmia, target_value):
        _contract("basis_compatibility", "RMIGA_BASIS_IDENTITY_MISMATCH", client_id)
    target_amount = _target_fraction(target_value["monthly_amount"], client_id)
    comparable = _cmia_fraction(cmia["total_monthly_equivalent"], client_id)
    try:
        gap = _subtract(target_amount, comparable)
    except ArithmeticError as exc:
        raise RMIGANumericError(client_id, exc) from exc
    included_contributions, excluded_source_ids, source_count = _source_projection(cmia)
    result = {
        "schema_version": SUCCESS_SCHEMA, "result_state": "COMPLETE", "client_id": client_id,
        "planning_calculation_input_fingerprint": planning,
        "retirement_target_date": target_date,
        "target_result_fingerprint": target["target_result_fingerprint"],
        "target_semantic_fingerprint": target["target_semantic_fingerprint"],
        "cmia_result_fingerprint": cmia["result_fingerprint"],
        "target_income_basis": target_value["income_basis"],
        "target_price_basis": target_value["price_basis"],
        "target_price_reference_date": target_value["price_reference_date"],
        "target_monthly_amount": _rational_payload(target_amount),
        "comparable_monthly_income": _thaw(cmia["total_monthly_equivalent"]),
        "monthly_gap": _rational_payload(gap),
        "gap_state": _gap_state(gap),
        "included_contributions": included_contributions,
        "excluded_source_ids": excluded_source_ids,
        "source_count": source_count,
    }
    result["result_fingerprint"] = _fingerprint(
        {"contract": RESULT_CONTRACT, "result": deepcopy(result)}, client_id,
    )
    return result


def assess(db: Session, request: Mapping[str, Any]) -> dict[str, Any]:
    request = _validated_request(request)
    client_id = request["client_id"]
    if db.in_transaction() or db.new or db.dirty or db.deleted:
        _contract("snapshot_admission", "RMIGA_REQUIRES_FRESH_TRANSACTION", client_id)
    if db.get_bind().dialect.name not in {"postgresql", "sqlite"}:
        _contract("snapshot_admission", "RMIGA_UNSUPPORTED_DATABASE", client_id)
    owned_connection = None
    try:
        owned_connection = db.connection()
        _begin_snapshot(db, owned_connection, client_id)
        with db.no_autoflush:
            composition = cmia_service.assess_with_target_in_snapshot(db, request)
            if not isinstance(composition, Mapping) or set(composition) != {"cmia_result", "target"}:
                _contract("cmia_authority", "RMIGA_CMIA_RESULT_INVALID", client_id)
            validated = cmia_service.validate_public_result(composition["cmia_result"])
            cmia = validated.result
            if validated.result_state == "BLOCK_NO_TOTAL":
                result = _block_result(request, cmia)
            else:
                result = _complete_result(request, cmia, composition["target"])
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
