"""SC-SCENARIO-03A: inert, versioned scenario-input manifest.

This is evidence packaging, NOT an executable planning snapshot or financial
calculation authority. Caller must own an isolated read-only transaction.
"""
from __future__ import annotations

from decimal import Decimal
import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.pension_product import PensionProduct, PensionProductComponent
from app.models.scenario_draft import ScenarioDraft, ScenarioDraftDecision
from app.services.scenario_draft_service import DraftError, _source_digest


def _fingerprint(value: dict) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_inert_manifest(db: Session, client_id: int, scenario_id: str) -> dict:
    """Return detached JSON-compatible evidence; never authorize execution.

    All reads must occur within the same caller-provided repeatable-read-only
    database snapshot. Never infer professional, permission or tax eligibility.
    """
    scenario = db.scalar(select(ScenarioDraft).where(
        ScenarioDraft.client_id == client_id, ScenarioDraft.scenario_id == scenario_id,
    ))
    if scenario is None:
        raise DraftError("SCENARIO_NOT_FOUND", 404)
    decisions = db.scalars(select(ScenarioDraftDecision).where(
        ScenarioDraftDecision.scenario_id == scenario_id,
    ).order_by(ScenarioDraftDecision.decision_id)).all()
    evidence = []
    for row in decisions:
        product = db.scalar(select(PensionProduct).where(
            PensionProduct.client_id == client_id,
            PensionProduct.product_id == row.source_product_id,
        ))
        component = db.scalar(select(PensionProductComponent).where(
            PensionProductComponent.product_id == row.source_product_id,
            PensionProductComponent.component_id == row.source_component_id,
            PensionProductComponent.component_code == row.component_code,
        )) if product is not None else None
        source = None
        if product is not None and component is not None:
            source = {
                "product_id": product.product_id,
                "product_version": product.version,
                "component_id": component.component_id,
                "component_code": component.component_code,
                "balance": format(component.balance, ".2f"),
                "source_fingerprint": _source_digest(product, component),
            }
        evidence.append({
            "decision_id": row.decision_id,
            "product_id": row.source_product_id,
            "component_id": row.source_component_id,
            "component_code": row.component_code,
            "amount": format(row.amount, ".2f"),
            "action": row.action,
            "effective_date": row.effective_date.isoformat(),
            "validation_state": row.validation_state,
            "product_version_at_review": row.product_version_at_review,
            "source_fingerprint_at_review": row.source_fingerprint_at_review,
            "source": source,
        })
    identity = {
        "schema_version": "SCENARIO_INERT_MANIFEST_V1",
        "client_id": client_id,
        "scenario_id": scenario_id,
        "scenario_version": scenario.version,
        "scenario_status": scenario.status,
        "decisions": evidence,
    }
    return {
        **identity,
        "manifest_fingerprint": _fingerprint(identity),
        "execution_allowed": False,
        "planning_snapshot": None,
        "financial_result": None,
        "authority_state": "NOT_EVALUATED",
    }
