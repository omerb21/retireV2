"""SC-03B: fail-closed engine contract compatibility for inert draft manifests.

This is a static interface gate. It cannot admit computation, call an engine,
or manufacture canonical planning/permission/tax authority.
"""
from __future__ import annotations

from collections.abc import Mapping

MANIFEST_VERSION = "SCENARIO_INERT_MANIFEST_V1"
ENGINE_CONTRACTS = {
    "pension_target_date": {
        "requires": ("scenario_planning_snapshot", "scenario_planning_fingerprint",
                     "retirement_target_authority", "complete_pension_source_coverage",
                     "pension_temporal_authority", "scenario_execution_identity"),
    },
    "capital_projection": {
        "requires": ("scenario_planning_snapshot", "scenario_planning_fingerprint",
                     "retirement_target_authority", "capital_projection_basis_admission",
                     "complete_capital_source_coverage", "scenario_execution_identity"),
    },
    "monthly_income_gap": {
        "requires": ("scenario_planning_snapshot", "scenario_planning_fingerprint",
                     "retirement_target_authority", "comparable_income_authority",
                     "confirmed_income_target_authority", "scenario_execution_identity"),
    },
}


def assess_engine_compatibility(manifest: Mapping) -> dict:
    """Return explicit blockers. Never derive readiness from caller-provided claims."""
    if not isinstance(manifest, Mapping) or manifest.get("schema_version") != MANIFEST_VERSION:
        return {
            "schema_version": "SCENARIO_ENGINE_COMPATIBILITY_V1",
            "compatibility_state": "BLOCKED",
            "execution_allowed": False,
            "engines": {},
            "blockers": ["SCENARIO_MANIFEST_SCHEMA_INVALID"],
        }
    integrity = manifest.get("execution_allowed") is False and manifest.get("planning_snapshot") is None
    integrity = integrity and manifest.get("financial_result") is None
    integrity = integrity and manifest.get("authority_state") == "NOT_EVALUATED"
    integrity = integrity and isinstance(manifest.get("manifest_fingerprint"), str)
    common = [] if integrity else ["SCENARIO_MANIFEST_INERT_CONTRACT_INVALID"]
    if manifest.get("scenario_status") != "draft":
        common.append("SCENARIO_STATUS_NOT_DRAFT")
    decisions = manifest.get("decisions")
    if not isinstance(decisions, list) or not decisions:
        common.append("SCENARIO_DECISIONS_EMPTY_OR_INVALID")
    elif any(not isinstance(d, Mapping) or d.get("source") is None for d in decisions):
        common.append("SCENARIO_SOURCE_EVIDENCE_INCOMPLETE")
    # The inert manifest cannot certify canonical source coverage or authority.
    # Every engine remains blocked even if a caller inserts counterfeit keys.
    engines = {}
    for engine, contract in ENGINE_CONTRACTS.items():
        blockers = list(common) + [
            "MISSING_VERIFIED_" + field.upper() for field in contract["requires"]
        ]
        blockers += [
            "PERMISSION_NOT_ADMITTED",
            "PROFESSIONAL_ELIGIBILITY_NOT_EVALUATED",
            "TAX_NOT_EVALUATED",
        ]
        engines[engine] = {
            "compatibility_state": "BLOCKED",
            "execution_allowed": False,
            "result": None,
            "missing_verified_contract_fields": list(contract["requires"]),
            "blockers": blockers,
        }
    return {
        "schema_version": "SCENARIO_ENGINE_COMPATIBILITY_V1",
        "compatibility_state": "BLOCKED",
        "execution_allowed": False,
        "scenario_id": manifest.get("scenario_id"),
        "scenario_version": manifest.get("scenario_version"),
        "manifest_fingerprint": manifest.get("manifest_fingerprint"),
        "engines": engines,
        "blockers": common + ["NO_SCENARIO_ENGINE_ADMISSION_CONTRACT"],
    }
