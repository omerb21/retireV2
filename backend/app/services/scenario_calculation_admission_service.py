"""SC-SCENARIO-02 admission assessment: evidence only, never execution authority.

Invoked inside a caller-owned read-only transaction. No flush, writes, or conversions.
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.pension_product import PensionProduct, PensionProductComponent
from app.models.scenario_draft import ScenarioDraft, ScenarioDraftDecision
from app.services.scenario_draft_service import DraftError, _source_digest


def assess(db: Session, client_id: int, scenario_id: str) -> dict:
    scenario = db.scalar(select(ScenarioDraft).where(
        ScenarioDraft.client_id == client_id, ScenarioDraft.scenario_id == scenario_id,
    ))
    if scenario is None:
        raise DraftError("SCENARIO_NOT_FOUND", 404)
    decisions = db.scalars(select(ScenarioDraftDecision).where(
        ScenarioDraftDecision.scenario_id == scenario_id,
    ).order_by(ScenarioDraftDecision.decision_id)).all()
    blockers: list[dict[str, str | None]] = []
    def block(code: str, decision_id: str | None = None) -> None:
        blockers.append({"code": code, "decision_id": decision_id})
    if scenario.status == "archived":
        block("SCENARIO_ARCHIVED")
    if not decisions:
        block("SCENARIO_EMPTY")
    allocated: dict[tuple[str, str], Decimal] = defaultdict(lambda: Decimal("0.00"))
    balances: dict[tuple[str, str], Decimal] = {}
    for decision in decisions:
        product = db.scalar(select(PensionProduct).where(
            PensionProduct.client_id == client_id,
            PensionProduct.product_id == decision.source_product_id,
        ))
        component = db.scalar(select(PensionProductComponent).where(
            PensionProductComponent.product_id == decision.source_product_id,
            PensionProductComponent.component_id == decision.source_component_id,
            PensionProductComponent.component_code == decision.component_code,
        )) if product is not None else None
        if product is None or component is None:
            block("SOURCE_NOT_FOUND", decision.decision_id)
            continue
        key = (product.product_id, component.component_id)
        if decision.source_fingerprint_at_review is None or (
            decision.product_version_at_review != product.version
            or _source_digest(product, component) != decision.source_fingerprint_at_review
        ) or decision.validation_state == "needs_revalidation":
            block("SOURCE_STALE", decision.decision_id)
        if decision.amount <= 0 or decision.amount.as_tuple().exponent < -2:
            block("AMOUNT_INVALID", decision.decision_id)
        else:
            allocated[key] += decision.amount
        balances[key] = component.balance
        # No permission-approval evidence is written by 01B, and neither
        # tax nor professional eligibility was admitted in earlier slices.
        block("PERMISSION_NOT_ADMITTED", decision.decision_id)
        block("PROFESSIONAL_ELIGIBILITY_NOT_EVALUATED", decision.decision_id)
        block("TAX_NOT_EVALUATED", decision.decision_id)
    for key, amount in allocated.items():
        if amount > balances[key]:
            block("SOURCE_OVERALLOCATED")
    return {
        "schema_version": "SCENARIO_CALCULATION_ADMISSION_V1",
        "client_id": client_id, "scenario_id": scenario_id,
        "scenario_version": scenario.version,
        "assessment_state": "blocked",
        "financial_result": None,
        "blockers": blockers,
    }
