"""SC-SCENARIO-02 admission and nonbinding gross forecast assessment.

Invoked inside a caller-owned read-only transaction. No flush, writes, or conversions.
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
import re
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.pension_product import PensionProduct, PensionProductComponent
from app.models.scenario_draft import ScenarioDraft, ScenarioDraftDecision
from app.services.scenario_draft_service import DraftError, _source_digest
from app.services.scenario_input_manifest_service import build_inert_manifest
from app.services.scenario_snapshot_candidate_service import (
    ScenarioSnapshotError, _partition_verified_manifest,
)
from app.services.scenario_stage6_single_pension_estimate_service import _aggregate_extension


def assess(db: Session, client_id: int, scenario_id: str, *, gross_enabled: bool = False) -> dict:
    scenario = db.scalar(select(ScenarioDraft).where(
        ScenarioDraft.client_id == client_id, ScenarioDraft.scenario_id == scenario_id,
    ))
    if scenario is None:
        raise DraftError("SCENARIO_NOT_FOUND", 404)
    decisions = db.scalars(select(ScenarioDraftDecision).where(
        ScenarioDraftDecision.scenario_id == scenario_id,
    ).order_by(ScenarioDraftDecision.decision_id)).all()
    blockers: list[dict[str, str | None]] = []
    known_decision_ids = {row.decision_id for row in decisions}
    def block(code: str, decision_id: str | None = None) -> None:
        # Stage 6 aggregate blockers may prefix a decision ID to the code.
        # Preserve both fields in the public structured contract, never a colon code.
        if decision_id is None and ":" in code:
            possible_id, possible_code = code.split(":", 1)
            if possible_id in known_decision_ids and re.fullmatch(r"[A-Z0-9_]+", possible_code):
                decision_id, code = possible_id, possible_code
        if not re.fullmatch(r"[A-Z0-9_]+", code):
            code = "GROSS_FORECAST_EVIDENCE_INCOMPLETE"
            decision_id = None
        blockers.append({"code": code, "decision_id": decision_id})
    if scenario.status == "archived":
        block("SCENARIO_ARCHIVED")
    if gross_enabled and scenario.status == "needs_revalidation":
        block("SCENARIO_NEEDS_REVALIDATION")
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
        if not gross_enabled:
            # Production and disabled Stage 6 keep the original fail-closed contract.
            block("PERMISSION_NOT_ADMITTED", decision.decision_id)
            block("PROFESSIONAL_ELIGIBILITY_NOT_EVALUATED", decision.decision_id)
            block("TAX_NOT_EVALUATED", decision.decision_id)
    for key, amount in allocated.items():
        if amount > balances[key]:
            block("SOURCE_OVERALLOCATED")
    result = {
        "schema_version": "SCENARIO_CALCULATION_ADMISSION_V1",
        "client_id": client_id, "scenario_id": scenario_id,
        "scenario_version": scenario.version,
        "assessment_state": "blocked",
        "financial_result": None,
        "blockers": blockers,
    }
    if not gross_enabled:
        return result

    # Stage 6 already owns the PTE calculation, current permission rules,
    # source fingerprints and version-bound professional factor admission.
    # Reuse its sealed result inside THIS read-only snapshot; never calculate
    # a pension amount from a caller-supplied coefficient or a second snapshot.
    if any(row.action != "pension" for row in decisions):
        block("GROSS_FORECAST_NON_PENSION_DECISION")
    if blockers:
        return result
    try:
        manifest = build_inert_manifest(db, client_id, scenario_id)
        candidate = _partition_verified_manifest(manifest)
        aggregate = _aggregate_extension(client_id=client_id, scenario_id=scenario_id)(
            db, {"manifest": manifest, "candidate": candidate}
        )
    except ScenarioSnapshotError as exc:
        block(str(exc))
        return result

    rows = aggregate["decision_results"]
    if (aggregate["aggregation_state"] != "COMPLETE"
            or aggregate["scenario_version"] != scenario.version
            or len(rows) != len(decisions)
            or aggregate["monthly_pension_gross_total_ils"] is None
            or aggregate["comparison_basis"] is None
            or any(row["result_state"] != "RESULT_READY" for row in rows)):
        for code in aggregate["blockers"] or ["GROSS_FORECAST_EVIDENCE_INCOMPLETE"]:
            block(code)
        return result

    provenance = []
    for row in rows:
        source = row["coefficient_provenance"]
        if (not isinstance(source, dict)
                or source.get("factor_evidence_type") not in {
                    "INSURER_QUOTE", "POLICY_CONTRACT", "PLANNER_ASSUMPTION"
                }
                or not source.get("factor_evidence_reference")
                or not source.get("factor_value")
                or type(source.get("admission_revision")) is not int
                or source["admission_revision"] < 1
                or not row.get("professional_admission_fingerprint")):
            block("GROSS_FORECAST_COEFFICIENT_PROVENANCE_MISSING", row["decision_id"])
            return result
        provenance.append({
            "decision_id": row["decision_id"],
            "factor_value": source["factor_value"],
            "factor_evidence_type": source["factor_evidence_type"],
            "factor_evidence_reference": source["factor_evidence_reference"],
            "factor_admission_revision": source["admission_revision"],
            "professional_admission_fingerprint": row["professional_admission_fingerprint"],
            "monthly_estimate_gross_ils": row["monthly_estimate_gross_ils"],
            "source_reference_date": row["statement_date"],
            "retirement_target_date": row["retirement_target_date"],
            "result_fingerprint": row["result_fingerprint"],
        })

    result["assessment_state"] = "gross_estimate_ready"
    result["financial_result"] = {
        "result_type": "NONBINDING_GROSS_PENSION_FORECAST",
        "monthly_pension_gross_ils": aggregate["monthly_pension_gross_total_ils"],
        "comparison_basis": aggregate["comparison_basis"],
        "coefficient_provenance": provenance,
        "tax_calculated": False,
        "net_calculated": False,
        "aggregate_fingerprint": aggregate["aggregate_fingerprint"],
    }
    result["warnings"] = ["TAX_NOT_EVALUATED", "NET_NOT_EVALUATED"]
    return result
