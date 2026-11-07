"""Bind the existing Capital Projection engine to a single scenario snapshot.

No new financial math or assumed tax/liquidity: all numeric projections come
from capital_projection_execution_service.execute, using the canonical plan
and its source/assumption admission derived in the caller's read-only snapshot.
"""
from __future__ import annotations

import hmac

from app.services import planning_input_service as planning
from app.services import capital_projection_basis_service as basis
from app.services import capital_projection_execution_service as projection
from app.services.pension_product_service import PensionProductError
from app.services.scenario_input_manifest_service import _fingerprint

CONTRACT = "SCENARIO_ADMITTED_CAPITAL_PROJECTION_V1"


def _blocked(code, *, extra=()):
    return {"state": "BLOCKED", "result": None, "result_fingerprint": None,
            "producer_contract": projection.CONTRACT, "professional_authority": False,
            "blockers": sorted(set((code, *extra)))}


def _verified_result(engine, authority, plan, client_id, target):
    """Verify the native engine envelope and every native source digest."""
    if (engine.get("contract_version") != projection.CONTRACT
            or engine.get("client_id") != client_id
            or engine.get("execution_status") != "AUTHORITATIVE_RESULT"
            or engine.get("execution_ready") is not True
            or engine.get("aggregate_blockers") != []
            or engine.get("planning_calculation_input_fingerprint")
            != plan["planning_calculation_input_fingerprint"]
            or engine.get("projection_basis_admission_fingerprint")
            != authority["projection_basis_admission_fingerprint"]):
        return False
    rows = engine.get("projected_sources")
    admitted = authority["covered_capital_sources"]
    if (not isinstance(rows, list) or not rows or len(rows) != len(admitted)
            or engine.get("covered_source_count") != len(rows)):
        return False
    expected_ids = [source["source_id"] for source in admitted]
    if sorted(row["source_id"] for row in rows) != sorted(expected_ids):
        return False
    for row in rows:
        if (row.get("retirement_target_date") != target
                or not isinstance(row.get("projected_amount"), str)
                or not projection.is_fingerprint(row.get("projection_result_fingerprint"))
                or row["projection_result_fingerprint"] != projection.result_fingerprint(row)):
            return False
    return (projection.is_fingerprint(engine.get("execution_fingerprint"))
            and hmac.compare_digest(
                engine["execution_fingerprint"], projection.aggregate_fingerprint(engine)))


def build_scenario_capital_projection(db, base, financial_evidence):
    """Called only inside the existing unified snapshot, not via engine.read."""
    identity = base["identity"]
    client_id, scenario_id, version = (identity["client_id"],
                                      identity["scenario_id"],
                                      identity["scenario_version"])
    capital = financial_evidence["capital"]
    if (capital["client_id"] != client_id or capital["scenario_id"] != scenario_id
            or capital["scenario_version"] != version):
        return _blocked("CAPITAL_SCENARIO_EVIDENCE_IDENTITY_INVALID")
    if base["blockers"]:
        return _blocked("CAPITAL_SCENARIO_SOURCE_NOT_CURRENT")
    if "CAPITAL_SOURCE_OVERALLOCATED" in capital["blockers"]:
        return _blocked("CAPITAL_SOURCE_OVERALLOCATED")
    if any(e["source_state"] != "CURRENT_STRUCTURAL_ONLY"
           for e in capital["facts"]["decisions"]):
        return _blocked("CAPITAL_SCENARIO_DECISION_STALE")
    if any(e["action"] == "capital_asset"
           for e in capital["facts"]["decisions"]):
        # Source components are pension-product holdings, not independent
        # CapitalAsset rows. No authorized mapping currently exists to subtract
        # those allocations from the source asset projection.
        return _blocked("CAPITAL_COMPONENT_WITHDRAWAL_SCENARIO_ADAPTER_MISSING")
    if "CAPITAL_PROJECTION_BASIS_CLIENT_ASSET_MISMATCH" in capital["blockers"]:
        return _blocked("CAPITAL_PROJECTION_BASIS_CLIENT_ASSET_MISMATCH")
    if any(asset["origin_kind"] != "manual" or asset["conversion_id"] is not None
           for asset in capital["facts"]["canonical_assets"]):
        return _blocked("CAPITAL_CONVERTED_SOURCE_OVERLAP_UNRESOLVED")
    if any(asset["verification_state"] != "verified"
           or asset["reported_current_value_ils"] is None
           or asset["value_as_of_date"] is None
           for asset in capital["facts"]["canonical_assets"]):
        return _blocked("CAPITAL_SOURCE_VERIFICATION_INCOMPLETE")
    if not capital["facts"]["canonical_assets"]:
        return _blocked("CAPITAL_NO_ELIGIBLE_SOURCES")
    try:
        plan = planning.derive(db, client_id)
        authority = basis.derive(db, client_id, plan)
        if (plan["planning_base_date"] != base["reference_dates"]["planning_base_date"]
                or plan["retirement_target"]["retirement_target_date"]
                != base["reference_dates"]["retirement_target_date"]
                or plan["decision_version"]
                != base["reference_dates"]["planning_decision_version"]):
            return _blocked("CAPITAL_SCENARIO_REFERENCE_DATE_MISMATCH")
        if not authority["projection_basis_ready"]:
            return _blocked("CAPITAL_PROJECTION_SOURCE_NOT_ADMITTED",
                            extra=authority["aggregate_blockers"])
        engine = projection.execute(client_id, plan, authority)
        target = plan["retirement_target"]["retirement_target_date"]
        if not _verified_result(engine, authority, plan, client_id, target):
            return _blocked("CAPITAL_PROJECTION_ENGINE_RESULT_INVALID")
    except PensionProductError as error:
        # Original engine error codes are preserved for auditing, not
        # converted into a guessed result or silently defaulted values.
        return _blocked("CAPITAL_PROJECTION_ENGINE_BLOCKED",
                        extra=[error.code])

    # Only a separately verified, unconverted CapitalAsset can appear here.
    # Existing pension component allocations are not summed or projected.
    result = {
        "contract": CONTRACT,
        "client_id": client_id, "scenario_id": scenario_id,
        "scenario_version": version,
        "planning_base_date": plan["planning_base_date"],
        "retirement_target_date": target,
        "capital_evidence_fingerprint": capital["evidence_fingerprint"],
        "manifest_fingerprint": base["manifest_fingerprint"],
        "planning_calculation_input_fingerprint":
            plan["planning_calculation_input_fingerprint"],
        "projection_basis_admission_fingerprint":
            authority["projection_basis_admission_fingerprint"],
        "native_execution_fingerprint": engine["execution_fingerprint"],
        "projection": engine,
        "projection_kind": "NONBINDING_INDEPENDENT_CAPITAL_ASSETS",
        "withdrawable_amount_ils": None,
        "actual_withdrawal_ils": None,
        "tax_effect_ils": None,
        "execution_allowed": False,
    }
    return {
        "state": "NONBINDING_PROJECTION", "result": result,
        "result_fingerprint": _fingerprint(result),
        "producer_contract": projection.CONTRACT,
        "professional_authority": False, "blockers": [],
    }
