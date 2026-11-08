"""Non-authoritative severance planning choices in the existing scenario revision store.

No separate decision ledger or tax engine. The scenario CAS and its immutable
versioned revision snapshots remain the only persistence boundary.
"""
from __future__ import annotations

import json
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.scenario_draft import ScenarioDraftRevision, ScenarioDraftDecision
from app.models.employment_record import EmploymentRecord
from app.models.grant import Grant
from app.models.pension_product import (
    PensionProduct, PensionProductComponent, SEVERANCE_CODES,
)
from app.services.professional_source_snapshot_service import record, serialize
from app.services.scenario_input_manifest_service import _fingerprint
from app.services.scenario_draft_service import (
    DraftError, _cas, _revision, _scenario, _source_evidence,
)

CHOICES = frozenset({
    "UNDECIDED", "PLANNED_WITHDRAWAL", "PLANNED_PENSION_CONTINUITY",
    "PLANNED_SEVERANCE_CONTINUITY",
})
SOURCE_TYPES = frozenset({"grant", "pension_component"})


def _previous(db: Session, scenario_id: str):
    latest = db.scalar(select(ScenarioDraftRevision).where(
        ScenarioDraftRevision.scenario_id == scenario_id
    ).order_by(ScenarioDraftRevision.version.desc()).limit(1))
    return json.loads(latest.snapshot_json).get("severance_planning_decisions", []) if latest else []


def _source(db: Session, client_id: int, kind: str, source_id: str):
    if kind == "grant":
        row = db.get(Grant, source_id)
        if row is None or row.client_id != client_id:
            raise DraftError("SEVERANCE_SOURCE_CLIENT_MISMATCH", 422)
        if row.employment_record_id:
            employer = db.get(EmploymentRecord, row.employment_record_id)
            if employer is None or employer.client_id != client_id:
                raise DraftError("SEVERANCE_EMPLOYMENT_CLIENT_MISMATCH", 422)
        return _fingerprint(serialize(record(row))), (
            Decimal(row.nominal_amount) if row.nominal_amount is not None else None
        )
    if kind == "pension_component":
        component = db.get(PensionProductComponent, source_id)
        if component is None:
            raise DraftError("SEVERANCE_SOURCE_CLIENT_MISMATCH", 422)
        product = db.get(PensionProduct, component.product_id)
        if (product is None or product.client_id != client_id
                or component.component_code not in SEVERANCE_CODES):
            raise DraftError("SEVERANCE_SOURCE_CLIENT_MISMATCH", 422)
        return _source_evidence(product, component)["source_fingerprint"], component.balance
    raise DraftError("SEVERANCE_SOURCE_KIND_INVALID", 422)


def _current_state(db: Session, client_id: int, scenario_id: str, entry: dict):
    try:
        current, _ = _source(db, client_id, entry["source_kind"], entry["source_id"])
    except DraftError:
        return "BLOCKED_SOURCE_MISSING_OR_FOREIGN"
    if current != entry["source_fingerprint"]:
        return "BLOCKED_SOURCE_STALE"
    # A saved selection can never mean an executed act or tax admission.
    return "DRAFT_ONLY"


def read_choices(db: Session, client_id: int, scenario_id: str) -> dict:
    scenario = _scenario(db, client_id, scenario_id)
    saved = _previous(db, scenario_id)
    grant_present = db.scalar(select(Grant.grant_id).where(Grant.client_id == client_id).limit(1)) is not None
    severance_components = db.scalar(select(PensionProductComponent.component_id).join(
        PensionProduct, PensionProduct.product_id == PensionProductComponent.product_id
    ).where(PensionProduct.client_id == client_id,
            PensionProductComponent.component_code.in_(SEVERANCE_CODES),
            PensionProductComponent.balance > 0).limit(1)) is not None
    overlap = grant_present and severance_components
    output = []
    for item in saved:
        state = _current_state(db, client_id, scenario_id, item)
        if scenario.status != "draft":
            state = "BLOCKED_SCENARIO_NOT_ACTIVE"
        elif state == "DRAFT_ONLY" and overlap:
            state = "BLOCKED_GRANT_COMPONENT_OVERLAP_UNRECONCILED"
        output.append({
            **item, "scenario_id": scenario_id,
            "client_id": client_id, "current_scenario_version": scenario.version,
            "state": state, "execution_allowed": False,
            "actual_paid_amount_ils": None,
            "future_payable_amount_ils": None,
            "exempt_amount_ils": None, "net_amount_ils": None,
            "professional_authority": False,
        })
    return {"client_id": client_id, "scenario_id": scenario_id,
            "scenario_version": scenario.version, "choices": output,
            "authority_state": "DRAFT_ONLY", "execution_allowed": False}


def replace_choices(db: Session, client_id: int, scenario_id: str, *,
                    expected_version: int, choices: list[dict], actor: str):
    """Caller transaction owns commit/rollback. Version CAS is atomic."""
    if type(expected_version) is not int or expected_version < 1:
        raise DraftError("SEVERANCE_SCENARIO_VERSION_INVALID", 422)
    if not isinstance(choices, list) or len(choices) > 500:
        raise DraftError("SEVERANCE_CHOICES_INVALID", 422)
    scenario = _scenario(db, client_id, scenario_id)
    if scenario.version != expected_version:
        raise DraftError("SCENARIO_VERSION_CONFLICT", 409)
    normalized = []
    seen = set()
    component_allocations = {}
    for item in choices:
        if not isinstance(item, dict) or set(item) != {
            "source_kind", "source_id", "choice", "planned_amount_ils",
        }:
            raise DraftError("SEVERANCE_CHOICE_SHAPE_INVALID", 422)
        kind, source_id, choice = item["source_kind"], item["source_id"], item["choice"]
        if kind not in SOURCE_TYPES or not isinstance(source_id, str) or not source_id or len(source_id) > 64 or choice not in CHOICES:
            raise DraftError("SEVERANCE_CHOICE_INVALID", 422)
        key = (kind, source_id)
        if key in seen:
            raise DraftError("SEVERANCE_DUPLICATE_SOURCE_CHOICE", 422)
        seen.add(key)
        fingerprint, reported_amount = _source(db, client_id, kind, source_id)
        amount = item["planned_amount_ils"]
        if choice == "UNDECIDED":
            if amount is not None:
                raise DraftError("SEVERANCE_UNDECIDED_AMOUNT_INVALID", 422)
        elif amount is not None:
            if type(amount) is not str:
                raise DraftError("SEVERANCE_AMOUNT_INVALID", 422)
            try:
                parsed = Decimal(amount)
            except (ValueError, ArithmeticError):
                raise DraftError("SEVERANCE_AMOUNT_INVALID", 422)
            if (not parsed.is_finite() or parsed <= 0 or parsed.as_tuple().exponent < -2
                    or format(parsed, ".2f") != amount):
                raise DraftError("SEVERANCE_AMOUNT_INVALID", 422)
            if reported_amount is None or parsed > reported_amount:
                raise DraftError("SEVERANCE_REPORTED_AMOUNT_EXCEEDED", 422)
            if kind == "pension_component":
                component_allocations[source_id] = parsed
        normalized.append({
            "source_kind": kind, "source_id": source_id,
            "choice": choice, "planned_amount_ils": amount,
            "source_fingerprint": fingerprint,
            "saved_from_scenario_version": expected_version + 1,
        })
    if component_allocations:
        # Draft pension/capital allocations consume the SAME component balance.
        draft = db.scalars(select(ScenarioDraftDecision).where(
            ScenarioDraftDecision.scenario_id == scenario_id,
            ScenarioDraftDecision.source_component_id.in_(component_allocations),
        )).all()
        for row in draft:
            component_allocations[row.source_component_id] += row.amount
        for source_id, total in component_allocations.items():
            _, capacity = _source(db, client_id, "pension_component", source_id)
            if total > capacity:
                raise DraftError("SEVERANCE_COMPONENT_OVERALLOCATED", 422)
    _cas(db, scenario, expected_version, actor)
    # Revisions, not a new mutable side ledger, own the saved choices.
    result = _revision(db, scenario, "replace_severance_planning", actor,
                       audit_extra={"severance_planning_decisions": normalized,
                                    "severance_professional_admission": False})
    return result
