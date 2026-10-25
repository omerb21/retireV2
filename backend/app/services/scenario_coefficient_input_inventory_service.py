"""SC-05B: DB-owned scenario coefficient-input inventory, no professional admission.

Inputs are read in the exact SC-03 PostgreSQL read-only snapshot. Never accept
caller-supplied identities, profile facts, pension elections or permissions.
"""
from __future__ import annotations

from sqlalchemy import select
from app.models.client_profile import ClientProfile
from app.models.scenario_draft_pension_election import ScenarioDraftPensionElection
from app.models.pension_product import PensionProduct
from app.services.scenario_input_manifest_service import _fingerprint
from app.services.scenario_snapshot_candidate_service import build_manifest_candidate_snapshot


def build_coefficient_input_inventory(factory, *, client_id: int, scenario_id: str) -> dict:
    """Document missing scenario-safe coefficient inputs without lookup/execution."""

    def within_snapshot(db, pair):
        manifest, candidate = pair["manifest"], pair["candidate"]
        blocked = candidate.get("evidence_state") != "STRUCTURALLY_CONSISTENT_NOT_ADMITTED"
        profile = db.scalar(select(ClientProfile).where(ClientProfile.client_id == client_id))
        products = {
            p.product_id: p for p in db.scalars(
                select(PensionProduct).where(PensionProduct.client_id == client_id)
            )
        }
        elections = {e.decision_id: e for e in db.scalars(select(ScenarioDraftPensionElection).where(
            ScenarioDraftPensionElection.scenario_id == scenario_id))}
        entries = []
        for row in manifest["decisions"]:
            if row["action"] != "pension":
                continue
            source = row.get("source")
            product = products.get(row["product_id"])
            identity_ok = (
                not blocked and source is not None and product is not None
                and product.version == source["product_version"]
                and product.product_id == source["product_id"]
                and candidate.get("manifest_fingerprint") == manifest["manifest_fingerprint"]
            )
            missing = ["SCENARIO_CANDIDATE_NOT_VERIFIED"] if not identity_ok else []
            if not profile or profile.birth_date is None or profile.gender is None:
                missing.append("EXPLICIT_PROFILE_FACTS_REQUIRED")
            if product is None:
                missing.append("PRODUCT_NOT_FOUND")
            elif product.start_date is None and (
                "ביטוח מנהלים" in product.product_type or "insurance" in product.product_type.lower()
            ):
                missing.append("INSURANCE_GENERATION_DATE_REQUIRED")
            election = elections.get(row["decision_id"])
            election_current = (
                identity_ok and election is not None
                and election.scenario_version == manifest["scenario_version"]
                and election.pension_start_date.isoformat() >= row["effective_date"]
                and election.coefficient_selection in ("catalog_candidate", "manual_review_required")
                and bool(election.survivors_option and election.survivors_option.strip())
                and type(election.target_year) is int
                and type(election.spouse_age_diff) is int
            )
            if not election_current:
                missing.append("SCENARIO_PENSION_ELECTION_MISSING_OR_STALE")
            missing.append("SCENARIO_COEFFICIENT_PERMISSION_NOT_EVALUATED")
            entries.append({
                "decision_id": row["decision_id"],
                "product_id": row["product_id"],
                "component_id": row["component_id"],
                "state": "BLOCKED" if not identity_ok else "UNRESOLVED",
                "blockers": sorted(set(missing)),
                "coefficient_candidate": None,
                "election_state": "CURRENT_DRAFT_NOT_ADMITTED" if election_current else "MISSING_OR_STALE",
            })
        identity = {
            "schema_version": "SCENARIO_COEFFICIENT_INPUT_INVENTORY_V1",
            "client_id": manifest["client_id"],
            "scenario_id": manifest["scenario_id"],
            "scenario_version": manifest["scenario_version"],
            "manifest_fingerprint": manifest["manifest_fingerprint"],
            "entries": entries,
        }
        return {
            **identity, "inventory_fingerprint": _fingerprint(identity),
            "inventory_state": "BLOCKED" if blocked else "UNRESOLVED",
            "execution_allowed": False, "financial_result": None,
            "planning_snapshot": None, "authority_state": "NOT_EVALUATED",
        }

    return build_manifest_candidate_snapshot(
        factory, client_id=client_id, scenario_id=scenario_id,
        _snapshot_extension=within_snapshot,
    )
