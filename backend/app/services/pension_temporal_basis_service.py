"""Canonical pension temporal/indexation basis; deliberately performs no projection."""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import re

from sqlalchemy import select

from app.models.canonical_conversion import batches, conversions, pensions
from app.models.canonical_pension_temporal_decision import CanonicalPensionTemporalDecision as Decision
from app.services.pension_monthly_basis_service import canonical_bytes
from app.services.pension_product_service import PensionProductError, lock_client

CONTRACT = "canonical-pension-temporal-indexation-basis-v1"
SEMANTIC = "canonical-pension-temporal-indexation-semantic-v1"
SOURCE = "canonical-pension-temporal-indexation-source-v1"
REGISTRY = "canonical-pension-temporal-indexation-registry-v1"
RATE_BASIS = "ANNUAL_EFFECTIVE"
RAW_MAX_LENGTH = 128
CANONICAL_MAX_LENGTH = 128
RAW_RATE = re.compile(r"^[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?$")
BLOCKER_ORDER = (
    "TEMPORAL_AUTHORITY_MISSING",
    "TEMPORAL_CPI_NOT_AUTHORIZED",
    "TEMPORAL_AUTHORITY_UNSUPPORTED",
    "TEMPORAL_ORIGIN_DATE_MISSING",
    "TEMPORAL_FIXED_ANNUAL_RATE_MISSING",
    "TEMPORAL_FIXED_ANNUAL_RATE_INVALID",
    "TEMPORAL_FIXED_ANNUAL_RATE_NOT_POSITIVE",
    "TEMPORAL_CONVERSION_DECISION_MISSING",
    "TEMPORAL_CONVERSION_DECISION_STALE",
)


def fail(code: str) -> None:
    raise PensionProductError(code, "סמכות העיתוי או ההצמדה אינה תקינה; יש לרענן ולאשר במפורש", 409)


def fingerprint(value) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def canonical_rate(raw: str | None) -> str:
    if raw is None:
        fail("TEMPORAL_FIXED_ANNUAL_RATE_MISSING")
    if not isinstance(raw, str) or len(raw.encode("utf-8")) > RAW_MAX_LENGTH or not RAW_RATE.fullmatch(raw):
        fail("TEMPORAL_FIXED_ANNUAL_RATE_INVALID")
    try:
        number = Decimal(raw)
    except (InvalidOperation, ValueError, ArithmeticError):
        fail("TEMPORAL_FIXED_ANNUAL_RATE_INVALID")
    if not number.is_finite():
        fail("TEMPORAL_FIXED_ANNUAL_RATE_INVALID")
    if number <= 0:
        fail("TEMPORAL_FIXED_ANNUAL_RATE_NOT_POSITIVE")
    # Do not expand hostile scientific notation into an enormous in-memory
    # fixed-point string. The accepted limit applies to the expanded value.
    exponent = number.as_tuple().exponent
    adjusted = number.adjusted()
    integer_length = max(adjusted + 1, 1)
    fractional_length = max(-exponent, 0)
    possible_length = integer_length + (1 + fractional_length if fractional_length else 0)
    if adjusted >= CANONICAL_MAX_LENGTH or exponent <= -CANONICAL_MAX_LENGTH or possible_length > CANONICAL_MAX_LENGTH:
        fail("TEMPORAL_FIXED_ANNUAL_RATE_INVALID")
    text = format(number, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text.startswith("+"):
        text = text[1:]
    if text.startswith("."):
        text = "0" + text
    if len(text) > CANONICAL_MAX_LENGTH:
        fail("TEMPORAL_FIXED_ANNUAL_RATE_INVALID")
    return text


def semantics(authority) -> tuple[str, str | None, str | None]:
    if authority is None:
        fail("TEMPORAL_DECISION_PAYLOAD_INVALID")
    kind = authority.authority_kind
    if kind == "none":
        if authority.annual_rate is not None:
            fail("TEMPORAL_DECISION_PAYLOAD_INVALID")
        return kind, None, None
    if kind == "fixed_manual":
        return kind, canonical_rate(authority.annual_rate), RATE_BASIS
    fail("TEMPORAL_DECISION_PAYLOAD_INVALID")


def ordered(values) -> list[str]:
    found = set(values)
    return [code for code in BLOCKER_ORDER if code in found]


def semantic_fingerprint(kind: str, origin: str | None, annual_rate: str | None, rate_basis: str | None) -> str:
    return fingerprint(dict(contract_version=SEMANTIC, temporal_authority_kind=kind,
        temporal_origin_date=origin, annual_rate=annual_rate, rate_basis=rate_basis))


def manual(row, client_id: int) -> dict:
    if row.client_id != client_id:
        fail("TEMPORAL_SOURCE_OWNERSHIP_INVALID")
    if row.lifecycle_status != "current":
        fail("TEMPORAL_SOURCE_NOT_CURRENT")
    raw_method = row.indexation_method
    raw_rate = row.fixed_indexation_rate
    if row.temporal_authority_explicit and (
        raw_method not in ("none", "fixed")
        or (raw_method == "none" and raw_rate is not None)
    ):
        fail("TEMPORAL_DECISION_STRUCTURE_INVALID")
    blockers = []
    origin = row.base_amount_effective_date.isoformat() if row.base_amount_effective_date else None
    if origin is None:
        blockers.append("TEMPORAL_ORIGIN_DATE_MISSING")
    kind = None
    rate = None
    basis = None
    if not row.temporal_authority_explicit:
        if raw_method == "cpi":
            blockers.append("TEMPORAL_CPI_NOT_AUTHORIZED")
        elif raw_method not in (None, "none", "fixed"):
            blockers.append("TEMPORAL_AUTHORITY_UNSUPPORTED")
        else:
            blockers.append("TEMPORAL_AUTHORITY_MISSING")
    elif raw_method == "none" and raw_rate is None:
        kind = "none"
    elif raw_method == "fixed":
        kind = "fixed_manual"
        basis = RATE_BASIS
        try:
            rate = canonical_rate(raw_rate)
        except PensionProductError as error:
            blockers.append(error.code)
    blockers = ordered(blockers)
    ready = not blockers and kind is not None
    semantic = semantic_fingerprint(kind, origin, rate, basis) if ready else None
    provenance = dict(manual_pension_source_id=row.manual_pension_source_id,
        lifecycle_status=row.lifecycle_status, raw_indexation_method=raw_method,
        raw_fixed_indexation_rate=raw_rate,
        base_amount_effective_date=origin,
        temporal_authority_explicit=row.temporal_authority_explicit)
    source_id = "manual:" + row.manual_pension_source_id
    source_fp = fingerprint(dict(contract_version=SOURCE, client_id=client_id, source_id=source_id,
        source_kind="manual", amount_authority_kind=("entered_monthly_amount" if row.input_mode == "entered" else "manual_balance_ratio"),
        temporal_semantic_fingerprint=semantic, temporal_authority_ready=ready,
        temporal_blockers=blockers, provenance=provenance))
    return dict(contract_version=CONTRACT, source_id=source_id, source_kind="manual",
        temporal_authority_kind=kind, temporal_origin_date=origin, annual_rate=rate,
        rate_basis=basis, temporal_authority_ready=ready, temporal_blockers=blockers,
        temporal_semantic_fingerprint=semantic, temporal_source_fingerprint=source_fp,
        provenance=provenance)


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _validate_conversion(client_id: int, destination, conversion, batch) -> None:
    if destination is None:
        fail("TEMPORAL_SOURCE_NOT_FOUND")
    if destination["client_id"] != client_id:
        fail("TEMPORAL_SOURCE_OWNERSHIP_INVALID")
    if not destination["conversion_id"] or conversion is None or batch is None:
        fail("TEMPORAL_SOURCE_STRUCTURE_INVALID")
    if conversion["client_id"] != client_id or conversion["conversion_id"] != destination["conversion_id"]:
        fail("TEMPORAL_SOURCE_STRUCTURE_INVALID")
    if conversion["destination_type"] != "pension" or batch["client_id"] != client_id or conversion["batch_id"] != batch["batch_id"]:
        fail("TEMPORAL_SOURCE_STRUCTURE_INVALID")
    pair = (conversion["status"], destination["status"])
    if pair == ("reversed", "reversed"):
        fail("TEMPORAL_SOURCE_NOT_CURRENT")
    if pair != ("active", "active"):
        fail("TEMPORAL_SOURCE_STRUCTURE_INVALID")
    if destination["effective_date"] is None or batch["effective_date"] is None or destination["effective_date"] != batch["effective_date"]:
        fail("TEMPORAL_SOURCE_STRUCTURE_INVALID")
    if not isinstance(destination["version"], int) or destination["version"] <= 0:
        fail("TEMPORAL_SOURCE_STRUCTURE_INVALID")


def conversion(db, client_id: int, destination, conversion_row, batch, decision=None) -> dict:
    _validate_conversion(client_id, destination, conversion_row, batch)
    if decision is None:
        decision = db.get(Decision, destination["pension_destination_id"])
    blockers = []
    kind = rate = basis = semantic = None
    if decision is None:
        blockers.append("TEMPORAL_CONVERSION_DECISION_MISSING")
        decision_version = 0
        source_version = None
        actor = decided_at = None
    else:
        if decision.client_id != client_id or decision.pension_destination_id != destination["pension_destination_id"]:
            fail("TEMPORAL_SOURCE_STRUCTURE_INVALID")
        if decision.authority_kind == "none" and decision.annual_rate_text is None and decision.rate_basis is None:
            kind = "none"
        elif decision.authority_kind == "fixed_manual" and decision.rate_basis == RATE_BASIS:
            kind, basis = "fixed_manual", RATE_BASIS
            try:
                rate = canonical_rate(decision.annual_rate_text)
            except PensionProductError:
                fail("TEMPORAL_SOURCE_STRUCTURE_INVALID")
            if rate != decision.annual_rate_text:
                fail("TEMPORAL_SOURCE_STRUCTURE_INVALID")
        else:
            fail("TEMPORAL_SOURCE_STRUCTURE_INVALID")
        if decision.source_version_at_decision != destination["version"]:
            blockers.append("TEMPORAL_CONVERSION_DECISION_STALE")
        decision_version = decision.version
        source_version = decision.source_version_at_decision
        actor = decision.actor
        decided_at = _timestamp(decision.decided_at)
    blockers = ordered(blockers)
    ready = not blockers and kind is not None
    origin = destination["effective_date"].isoformat()
    if ready:
        semantic = semantic_fingerprint(kind, origin, rate, basis)
    provenance = dict(pension_destination_id=destination["pension_destination_id"],
        conversion_id=destination["conversion_id"], destination_version=destination["version"],
        decision_version=decision_version, source_version_at_decision=source_version,
        raw_authority_kind=(decision.authority_kind if decision else None),
        raw_annual_rate_text=(decision.annual_rate_text if decision else None),
        rate_basis=(decision.rate_basis if decision else None), actor=actor, decided_at=decided_at,
        conversion_effective_date=origin, conversion_status=conversion_row["status"],
        destination_status=destination["status"])
    source_id = "conversion:" + destination["pension_destination_id"]
    source_fp = fingerprint(dict(contract_version=SOURCE, client_id=client_id,
        source_id=source_id, source_kind="conversion", amount_authority_kind="persisted_conversion_ratio",
        temporal_semantic_fingerprint=semantic, temporal_authority_ready=ready,
        temporal_blockers=blockers, provenance=provenance))
    return dict(contract_version=CONTRACT, source_id=source_id, source_kind="conversion",
        temporal_authority_kind=kind, temporal_origin_date=origin, annual_rate=rate,
        rate_basis=basis, temporal_authority_ready=ready, temporal_blockers=blockers,
        temporal_semantic_fingerprint=semantic, temporal_source_fingerprint=source_fp,
        provenance=provenance)


def registry(client_id: int, sources: list[dict]) -> str:
    if len({source["source_id"] for source in sources}) != len(sources):
        fail("TEMPORAL_SOURCE_STRUCTURE_INVALID")
    return fingerprint(dict(contract_version=REGISTRY, client_id=client_id,
        sources=[dict(source_id=source["source_id"],
            temporal_source_fingerprint=source["temporal_source_fingerprint"],
            temporal_authority_ready=source["temporal_authority_ready"],
            temporal_blockers=source["temporal_blockers"])
            for source in sorted(sources, key=lambda item: item["source_id"])]))


def apply_manual(payload, row, *, creating: bool) -> None:
    legacy = {"indexation_method", "fixed_indexation_rate"} & payload.model_fields_set
    if legacy:
        fail("TEMPORAL_DECISION_PAYLOAD_INVALID")
    supplied = "temporal_authority" in payload.model_fields_set
    if not supplied and not creating:
        return
    authority = payload.temporal_authority if supplied else None
    if authority is None:
        row.temporal_authority_explicit = False
        row.indexation_method = None
        row.fixed_indexation_rate = None
        return
    kind, rate, _ = semantics(authority)
    row.temporal_authority_explicit = True
    row.indexation_method = "none" if kind == "none" else "fixed"
    row.fixed_indexation_rate = rate


def write_conversion(db, client_id: int, destination_id: str, payload) -> dict:
    # Match the canonical conversion/reversal lock order.  Besides serializing
    # client-scoped writers, this prevents the decision INSERT's client FK
    # check from deadlocking with a reversal that already holds the client row.
    lock_client(db, client_id)
    destination = db.execute(select(pensions).where(
        pensions.c.pension_destination_id == destination_id).with_for_update()).mappings().first()
    if destination is None:
        fail("TEMPORAL_SOURCE_NOT_FOUND")
    if destination["client_id"] != client_id:
        fail("TEMPORAL_SOURCE_OWNERSHIP_INVALID")
    conversion_row = db.execute(select(conversions).where(
        conversions.c.conversion_id == destination["conversion_id"])).mappings().first()
    batch = None if conversion_row is None else db.execute(select(batches).where(
        batches.c.batch_id == conversion_row["batch_id"])).mappings().first()
    _validate_conversion(client_id, destination, conversion_row, batch)
    if destination["version"] != payload.expected_source_version:
        fail("TEMPORAL_SOURCE_VERSION_STALE")
    decision = db.scalar(select(Decision).where(Decision.pension_destination_id == destination_id).with_for_update())
    if decision is None and payload.expected_decision_version > 0:
        fail("TEMPORAL_DECISION_STRUCTURE_INVALID")
    current_version = decision.version if decision else 0
    if current_version != payload.expected_decision_version:
        fail("TEMPORAL_DECISION_VERSION_STALE")
    kind, rate, basis = semantics(payload.temporal_authority)
    current_semantics = None if decision is None else (decision.authority_kind, decision.annual_rate_text, decision.rate_basis)
    requested = (kind, rate, basis)
    now = datetime.now(timezone.utc)
    if decision is None:
        decision = Decision(pension_destination_id=destination_id, client_id=client_id,
            authority_kind=kind, annual_rate_text=rate, rate_basis=basis,
            source_version_at_decision=destination["version"], version=1,
            actor=payload.actor, decided_at=now)
        db.add(decision)
        outcome = "TEMPORAL_DECISION_CREATED"
    elif current_semantics != requested:
        decision.authority_kind, decision.annual_rate_text, decision.rate_basis = requested
        decision.version += 1
        decision.source_version_at_decision = destination["version"]
        decision.actor, decision.decided_at = payload.actor, now
        outcome = "TEMPORAL_DECISION_UPDATED"
    elif decision.source_version_at_decision == destination["version"]:
        outcome = "TEMPORAL_DECISION_UNCHANGED"
    else:
        decision.version += 1
        decision.source_version_at_decision = destination["version"]
        decision.actor, decision.decided_at = payload.actor, now
        outcome = "TEMPORAL_DECISION_REAUTHORIZED"
    db.flush()
    result = conversion(db, client_id, destination, conversion_row, batch, decision)
    return {"outcome": outcome, "decision_version": decision.version,
        "source_version_at_decision": decision.source_version_at_decision, "temporal_authority": result}
