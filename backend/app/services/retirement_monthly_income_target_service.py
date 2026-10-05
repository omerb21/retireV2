"""Explicit retirement-income target authority; no downstream arithmetic."""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
import unicodedata
from typing import Mapping

from sqlalchemy import select
from sqlalchemy.exc import DBAPIError, IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.models.retirement_monthly_income_target import RetirementMonthlyIncomeTargetElection as Election
from app.services import planning_input_service as planning
from app.services.pension_product_service import PensionProductError, lock_client

SCHEMA_VERSION = "CANONICAL_RETIREMENT_MONTHLY_INCOME_TARGET_AUTHORITY_RESULT_V1"
SEMANTIC_CONTRACT = "CANONICAL_RETIREMENT_MONTHLY_INCOME_TARGET_AUTHORITY_SEMANTIC_FINGERPRINT_JSON_V1"
RESULT_CONTRACT = "CANONICAL_RETIREMENT_MONTHLY_INCOME_TARGET_AUTHORITY_RESULT_FINGERPRINT_JSON_V1"
MAX_VERSION = 9223372036854775807
COMMAND_FIELDS = frozenset({
    "client_id", "expected_record_version", "expected_planning_calculation_input_fingerprint",
    "expected_retirement_target_date", "monthly_amount", "income_basis", "price_basis",
    "price_reference_date", "source_kind",
})
INCOME_BASES = {"GROSS", "NET"}
PRICE_BASES = {"NOMINAL_AT_RETIREMENT_TARGET_DATE", "REAL_AT_REFERENCE_DATE"}
SOURCE_KINDS = {"CLIENT_SUPPLIED", "PLANNER_SUPPLIED", "CLIENT_SUPPLIED_PLANNER_CONFIRMED"}
HASH_RE = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
AMOUNT_RE = re.compile(r"[+-]?[0-9]+(?:\.[0-9]+)?\Z", re.ASCII)
DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z", re.ASCII)
TIMESTAMP_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}Z\Z", re.ASCII)


class RetirementMonthlyIncomeTargetError(PensionProductError):
    pass


class TargetResultFingerprintConstructionError(RuntimeError):
    pass


def _fail(code: str, status: int = 409):
    raise RetirementMonthlyIncomeTargetError(code, code, status)


def _canonical_bytes(value) -> bytes:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise TargetResultFingerprintConstructionError(str(exc)) from exc


def _fingerprint(value) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _semantic_fingerprint(target: dict) -> str:
    return _fingerprint({"contract": SEMANTIC_CONTRACT, **target})


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _strict_date(value) -> date | None:
    if not isinstance(value, str) or not DATE_RE.fullmatch(value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _canonical_amount(value) -> tuple[str | None, str | None]:
    if not isinstance(value, str) or len(value) > 128:
        return None, "RIT_AMOUNT_INVALID"
    raw = value.strip(" \t\r\n")
    if not AMOUNT_RE.fullmatch(raw):
        return None, "RIT_AMOUNT_INVALID"
    try:
        number = Decimal(raw)
    except InvalidOperation:
        return None, "RIT_AMOUNT_INVALID"
    if not number.is_finite() or number <= 0:
        return None, "RIT_AMOUNT_INVALID"
    unsigned = raw[1:] if raw[:1] in "+-" else raw
    integer, dot, fraction = unsigned.partition(".")
    integer = integer.lstrip("0") or "0"
    fraction = fraction.rstrip("0") if dot else ""
    if len(integer) > 18 or len(fraction) > 6:
        return None, "RIT_AMOUNT_PRECISION_UNSUPPORTED"
    return integer + (("." + fraction) if fraction else ""), None


def _valid_actor(value) -> bool:
    return (
        isinstance(value, str) and 1 <= len(value) <= 128
        and value == value.strip(" \t\r\n")
        and not any(unicodedata.category(char) == "Cc" for char in value)
    )


def _validate_command(command) -> dict:
    if not isinstance(command, Mapping) or set(command) != COMMAND_FIELDS:
        _fail("RIT_COMMAND_SCHEMA_INVALID")
    data = dict(command)
    blockers = []
    client_id = data["client_id"]
    version = data["expected_record_version"]
    if isinstance(client_id, bool) or not isinstance(client_id, int) or client_id <= 0:
        blockers.append("RIT_CLIENT_ID_INVALID")
    if isinstance(version, bool) or not isinstance(version, int) or not 0 <= version <= MAX_VERSION:
        blockers.append("RIT_TARGET_RECORD_INVALID")
    if not isinstance(data["expected_planning_calculation_input_fingerprint"], str) or not HASH_RE.fullmatch(data["expected_planning_calculation_input_fingerprint"]):
        blockers.append("RIT_PLANNING_CONTEXT_INVALID")
    if _strict_date(data["expected_retirement_target_date"]) is None:
        blockers.append("RIT_PLANNING_CONTEXT_INVALID")
    if data["monthly_amount"] is None:
        amount, amount_error = None, "RIT_AMOUNT_MISSING"
    else:
        amount, amount_error = _canonical_amount(data["monthly_amount"])
    if amount_error:
        blockers.append(amount_error)
    if data["income_basis"] is None:
        blockers.append("RIT_INCOME_BASIS_MISSING")
    elif not isinstance(data["income_basis"], str) or data["income_basis"] not in INCOME_BASES:
        blockers.append("RIT_INCOME_BASIS_INVALID")
    price_basis = data["price_basis"]
    if price_basis is None:
        blockers.append("RIT_PRICE_BASIS_MISSING")
    elif not isinstance(price_basis, str) or price_basis not in PRICE_BASES:
        blockers.append("RIT_PRICE_BASIS_INVALID")
    elif price_basis == "NOMINAL_AT_RETIREMENT_TARGET_DATE":
        if data["price_reference_date"] is not None:
            blockers.append("RIT_NOMINAL_PRICE_REFERENCE_DATE_NOT_NULL")
    elif data["price_reference_date"] is None:
        blockers.append("RIT_PRICE_REFERENCE_DATE_MISSING")
    elif _strict_date(data["price_reference_date"]) is None:
        blockers.append("RIT_PRICE_REFERENCE_DATE_INVALID")
    if not isinstance(data["source_kind"], str) or data["source_kind"] not in SOURCE_KINDS:
        blockers.append("RIT_CONFIRMATION_INVALID")
    if blockers:
        _fail(sorted(set(blockers))[0])
    data["monthly_amount"] = amount
    data["expected_retirement_target_date"] = _strict_date(data["expected_retirement_target_date"])
    data["price_reference_date"] = _strict_date(data["price_reference_date"]) if data["price_reference_date"] is not None else None
    return data


def _begin(db: Session) -> None:
    if db.in_transaction() or db.new or db.dirty or db.deleted:
        _fail("RIT_RECORD_UNAVAILABLE")
    connection = db.connection()
    dialect = connection.dialect.name
    if dialect == "postgresql":
        connection.exec_driver_sql("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
    elif dialect == "sqlite":
        connection.exec_driver_sql("BEGIN IMMEDIATE")
    else:
        _fail("RIT_RECORD_UNAVAILABLE", 503)


def _context(db: Session, client_id: int) -> dict:
    try:
        plan = planning.derive(db, client_id)
    except RetirementMonthlyIncomeTargetError:
        raise
    except PensionProductError:
        _fail("RIT_PLANNING_CONTEXT_UNAVAILABLE")
    if plan.get("client_id") != client_id:
        _fail("RIT_PLANNING_CONTEXT_INVALID")
    fingerprint = plan.get("planning_calculation_input_fingerprint")
    target = plan.get("retirement_target")
    if not isinstance(fingerprint, str) or not HASH_RE.fullmatch(fingerprint) or not isinstance(target, dict):
        _fail("RIT_PLANNING_CONTEXT_INVALID")
    target_date = target.get("retirement_target_date")
    if not target.get("retirement_target_ready") or target_date is None:
        _fail("RIT_RETIREMENT_TARGET_NOT_READY")
    parsed = _strict_date(target_date)
    if parsed is None:
        _fail("RIT_PLANNING_CONTEXT_INVALID")
    return {"client_id": client_id, "fingerprint": fingerprint, "retirement_target_date": parsed}


def _lock_client(db: Session, client_id: int) -> None:
    try:
        lock_client(db, client_id)
    except PensionProductError as exc:
        if exc.code == "CLIENT_NOT_FOUND":
            _fail("RIT_CLIENT_ID_INVALID")
        raise


def _target_from_values(*, client_id, planning_fingerprint, target_date, amount, income_basis, price_basis, reference_date):
    return {
        "client_id": client_id,
        "planning_calculation_input_fingerprint": planning_fingerprint,
        "retirement_target_date": target_date.isoformat(),
        "monthly_amount": amount,
        "currency": "ILS",
        "income_basis": income_basis,
        "price_basis": price_basis,
        "price_reference_date": reference_date.isoformat() if reference_date else None,
    }


def _authority(row: Election) -> tuple[dict | None, list[str]]:
    missing = row.confirmation_state is None or row.confirmation_actor is None or row.confirmed_at is None
    if missing:
        return None, ["RIT_CONFIRMATION_MISSING"]
    if (row.lifecycle_state not in {"CONFIRMED", "STALE"}
        or not isinstance(row.version, int) or isinstance(row.version, bool)
        or not 1 <= row.version <= MAX_VERSION):
        return None, ["RIT_TARGET_RECORD_INVALID"]
    if (row.confirmation_state != "CONFIRMED" or row.source_kind not in SOURCE_KINDS
        or not _valid_actor(row.confirmation_actor)):
        return None, ["RIT_CONFIRMATION_INVALID"]
    try:
        confirmed = _timestamp(row.confirmed_at)
    except Exception:
        return None, ["RIT_CONFIRMATION_INVALID"]
    if not TIMESTAMP_RE.fullmatch(confirmed):
        return None, ["RIT_CONFIRMATION_INVALID"]
    return {
        "record_version": row.version,
        "source_kind": row.source_kind,
        "confirmation_state": row.confirmation_state,
        "confirmation_actor": row.confirmation_actor,
        "confirmed_at": confirmed,
        "lifecycle_state": row.lifecycle_state,
    }, []


def _stored_target(row: Election) -> tuple[dict | None, list[str]]:
    blockers = []
    amount, error = _canonical_amount(row.monthly_amount_text)
    if row.monthly_amount_text is None:
        blockers.append("RIT_AMOUNT_MISSING")
    elif error:
        blockers.append(error)
    elif amount != row.monthly_amount_text:
        blockers.append("RIT_TARGET_RECORD_INVALID")
    if row.currency != "ILS": blockers.append("RIT_CURRENCY_INVALID")
    if row.income_basis is None: blockers.append("RIT_INCOME_BASIS_MISSING")
    elif row.income_basis not in INCOME_BASES: blockers.append("RIT_INCOME_BASIS_INVALID")
    if row.price_basis is None: blockers.append("RIT_PRICE_BASIS_MISSING")
    elif row.price_basis not in PRICE_BASES: blockers.append("RIT_PRICE_BASIS_INVALID")
    elif row.price_basis == "NOMINAL_AT_RETIREMENT_TARGET_DATE" and row.price_reference_date is not None:
        blockers.append("RIT_NOMINAL_PRICE_REFERENCE_DATE_NOT_NULL")
    elif row.price_basis == "REAL_AT_REFERENCE_DATE" and row.price_reference_date is None:
        blockers.append("RIT_PRICE_REFERENCE_DATE_MISSING")
    if not isinstance(row.client_id, int) or row.client_id <= 0 or not isinstance(row.retirement_target_date, date):
        blockers.append("RIT_TARGET_RECORD_INVALID")
    if not isinstance(row.planning_calculation_input_fingerprint, str) or not HASH_RE.fullmatch(row.planning_calculation_input_fingerprint):
        blockers.append("RIT_TARGET_RECORD_INVALID")
    if blockers:
        return None, sorted(set(blockers))
    return _target_from_values(client_id=row.client_id, planning_fingerprint=row.planning_calculation_input_fingerprint,
        target_date=row.retirement_target_date, amount=amount, income_basis=row.income_basis,
        price_basis=row.price_basis, reference_date=row.price_reference_date), []


def _result(context: dict, row: Election | None, blockers: list[str] | None = None, state: str | None = None) -> dict:
    blockers = list(blockers or [])
    target = authority = None
    semantic = None
    if row is None:
        blockers = blockers or ["RIT_TARGET_MISSING"]
        state = state or "MISSING"
    else:
        if row.client_id != context.get("client_id"):
            blockers.append("RIT_TARGET_CLIENT_MISMATCH")
        target, target_blockers = _stored_target(row)
        authority, authority_blockers = _authority(row)
        blockers.extend(target_blockers + authority_blockers)
        if target is not None:
            semantic = _semantic_fingerprint(target)
            if not isinstance(row.target_semantic_fingerprint, str) or not HASH_RE.fullmatch(row.target_semantic_fingerprint) or row.target_semantic_fingerprint != semantic:
                blockers.append("RIT_STORED_FINGERPRINT_MISMATCH")
        if blockers:
            state = state or "INVALID"
        else:
            if row.planning_calculation_input_fingerprint != context["fingerprint"]:
                blockers.append("RIT_PLANNING_IDENTITY_STALE")
            if row.retirement_target_date != context["retirement_target_date"]:
                blockers.append("RIT_RETIREMENT_TARGET_STALE")
            if row.lifecycle_state == "STALE" or blockers:
                blockers.append("RIT_RECONFIRMATION_REQUIRED")
                state = "STALE"
            else:
                state = "CURRENT"
    blockers = sorted(set(blockers))
    ready = state == "CURRENT" and target is not None and authority is not None and not blockers
    result = {
        "schema_version": SCHEMA_VERSION,
        "client_id": context.get("client_id"),
        "planning_calculation_input_fingerprint": context.get("fingerprint"),
        "retirement_target_date": context["retirement_target_date"].isoformat() if context.get("retirement_target_date") else None,
        "target": target,
        "authority": authority,
        "authority_state": state,
        "target_readiness_state": "READY" if ready else "NOT_READY",
        "target_ready": ready,
        "blockers": blockers,
        "target_semantic_fingerprint": semantic,
    }
    result["target_result_fingerprint"] = _fingerprint({"contract": RESULT_CONTRACT, **result})
    return result


def _locked_row(db: Session, client_id: int) -> Election | None:
    return db.scalar(select(Election).where(Election.client_id == client_id).with_for_update().execution_options(populate_existing=True))


def _retryable(exc: BaseException) -> bool:
    original = getattr(exc, "orig", None)
    code = getattr(original, "pgcode", None) or getattr(original, "sqlstate", None)
    if code in {"40001", "40P01"}:
        return True
    if code == "23505" and isinstance(exc, IntegrityError):
        diagnostics = getattr(original, "diag", None)
        constraint = getattr(diagnostics, "constraint_name", None)
        table = getattr(diagnostics, "table_name", None)
        return (
            constraint == "retirement_monthly_income_target_elections_pkey"
            and table in {None, "retirement_monthly_income_target_elections"}
        )
    sqlite_code = getattr(original, "sqlite_errorcode", None)
    return (
        isinstance(exc, OperationalError)
        and isinstance(sqlite_code, int)
        and sqlite_code & 0xFF in {5, 6}  # SQLITE_BUSY / SQLITE_LOCKED
    )


def _prepare_authoritative_state(db: Session) -> None:
    """Exclude identity-map objects retained from an earlier transaction."""
    db.expire_all()


def confirm(db: Session, complete_command, trusted_professional_actor: str) -> dict:
    command = _validate_command(complete_command)
    if not _valid_actor(trusted_professional_actor):
        _fail("RIT_CONFIRMATION_INVALID")
    for attempt in range(3):
        try:
            _begin(db)
            _prepare_authoritative_state(db)
            _lock_client(db, command["client_id"])
            context = _context(db, command["client_id"])
            row = _locked_row(db, command["client_id"])
            if context["fingerprint"] != command["expected_planning_calculation_input_fingerprint"] or context["retirement_target_date"] != command["expected_retirement_target_date"]:
                _fail("RIT_CONFIRMATION_CONTEXT_STALE")
            current_version = row.version if row else 0
            target = _target_from_values(client_id=command["client_id"], planning_fingerprint=context["fingerprint"],
                target_date=context["retirement_target_date"], amount=command["monthly_amount"], income_basis=command["income_basis"],
                price_basis=command["price_basis"], reference_date=command["price_reference_date"])
            semantic = _semantic_fingerprint(target)
            # Bounded retry of the immediately produced current revision.
            if row is not None and row.version == command["expected_record_version"] + 1:
                existing, defects = _stored_target(row)
                authority, authority_defects = _authority(row)
                if (not defects and not authority_defects and row.lifecycle_state == "CONFIRMED"
                    and existing == target and row.source_kind == command["source_kind"]
                    and row.confirmation_actor == trusted_professional_actor
                    and row.target_semantic_fingerprint == semantic):
                    result = _result(context, row)
                    db.commit()
                    return result
                _fail("RIT_RECORD_VERSION_CONFLICT")
            if current_version != command["expected_record_version"]:
                _fail("RIT_RECORD_VERSION_CONFLICT")
            if current_version >= MAX_VERSION:
                _fail("RIT_RECORD_VERSION_EXHAUSTED")
            now = _utc_now()
            if row is None:
                row = Election(client_id=command["client_id"], created_at=now)
                db.add(row)
            row.version = current_version + 1
            row.lifecycle_state = "CONFIRMED"
            row.planning_calculation_input_fingerprint = context["fingerprint"]
            row.retirement_target_date = context["retirement_target_date"]
            row.monthly_amount_text = command["monthly_amount"]
            row.currency = "ILS"
            row.income_basis = command["income_basis"]
            row.price_basis = command["price_basis"]
            row.price_reference_date = command["price_reference_date"]
            row.source_kind = command["source_kind"]
            row.confirmation_state = "CONFIRMED"
            row.confirmation_actor = trusted_professional_actor
            row.confirmed_at = now
            row.target_semantic_fingerprint = semantic
            row.updated_at = now
            db.flush()
            result = _result(context, row)
            db.commit()
            return result
        except RetirementMonthlyIncomeTargetError:
            db.rollback()
            raise
        except (OperationalError, IntegrityError, DBAPIError) as exc:
            db.rollback()
            db.expunge_all()
            if attempt == 2 or not _retryable(exc):
                raise
    raise AssertionError("unreachable")


def assess(db: Session, client_id: int) -> dict:
    if isinstance(client_id, bool) or not isinstance(client_id, int) or client_id <= 0:
        context = {"client_id": None, "fingerprint": None, "retirement_target_date": None}
        return _result(context, None, ["RIT_CLIENT_ID_INVALID"], "UNAVAILABLE")
    for attempt in range(3):
        try:
            _begin(db)
            _prepare_authoritative_state(db)
            _lock_client(db, client_id)
            try:
                context = _context(db, client_id)
            except RetirementMonthlyIncomeTargetError as exc:
                if exc.code not in {"RIT_PLANNING_CONTEXT_UNAVAILABLE", "RIT_PLANNING_CONTEXT_INVALID", "RIT_RETIREMENT_TARGET_NOT_READY"}:
                    raise
                context = {"client_id": client_id, "fingerprint": None, "retirement_target_date": None}
                result = _result(context, None, [exc.code], "UNAVAILABLE")
                db.commit()
                return result
            row = _locked_row(db, client_id)
            result = _result(context, row)
            if row is not None and result["authority_state"] == "STALE" and row.lifecycle_state == "CONFIRMED":
                if row.version >= MAX_VERSION:
                    _fail("RIT_RECORD_VERSION_EXHAUSTED")
                row.lifecycle_state = "STALE"
                row.version += 1
                row.updated_at = _utc_now()
                db.flush()
                result = _result(context, row)
            db.commit()
            return result
        except RetirementMonthlyIncomeTargetError:
            db.rollback()
            raise
        except (OperationalError, IntegrityError, DBAPIError) as exc:
            db.rollback()
            db.expunge_all()
            if attempt == 2 or not _retryable(exc):
                raise
    raise AssertionError("unreachable")
