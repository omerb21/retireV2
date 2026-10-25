"""SC-05E trusted database projection for documentary review evidence.

Read canonical draft/source/election facts in the *caller's* transaction.
No external hash maps are accepted as an authority source.
"""
from sqlalchemy import select

from app.models.client_profile import ClientProfile
from app.models.pension_product import PensionProduct
from app.models.scenario_draft_pension_election import ScenarioDraftPensionElection
from app.services.scenario_draft_service import DraftError
from app.services.scenario_input_manifest_service import build_inert_manifest, _fingerprint
from app.services.scenario_snapshot_candidate_service import _partition_verified_manifest


def derive_documentary_review_context(db, *, client_id: int, scenario_id: str,
                                       decision_id: str) -> dict:
    manifest = build_inert_manifest(db, client_id, scenario_id)
    candidate = _partition_verified_manifest(manifest)
    if candidate["evidence_state"] != "STRUCTURALLY_CONSISTENT_NOT_ADMITTED":
        raise DraftError("PROFESSIONAL_REVIEW_SOURCE_UNVERIFIED", 409)
    decision = next((r for r in manifest["decisions"] if r["decision_id"] == decision_id
                     and r["action"] == "pension"), None)
    if decision is None or decision["source"] is None:
        raise DraftError("PROFESSIONAL_REVIEW_DECISION_STALE", 409)
    election = db.scalar(select(ScenarioDraftPensionElection).where(
        ScenarioDraftPensionElection.scenario_id == scenario_id,
        ScenarioDraftPensionElection.decision_id == decision_id,
        ScenarioDraftPensionElection.scenario_version == manifest["scenario_version"]))
    if (election is None or election.pension_start_date.isoformat() < decision["effective_date"]
            or election.coefficient_selection not in {"catalog_candidate", "manual_review_required"}):
        raise DraftError("PROFESSIONAL_REVIEW_ELECTION_MISSING_OR_STALE", 409)
    product = db.scalar(select(PensionProduct).where(
        PensionProduct.client_id == client_id,
        PensionProduct.product_id == decision["product_id"]))
    profile = db.scalar(select(ClientProfile).where(ClientProfile.client_id == client_id))
    if (product is None or product.version != decision["source"]["product_version"]
            or profile is None or profile.birth_date is None or profile.gender is None):
        raise DraftError("PROFESSIONAL_REVIEW_INPUT_FACTS_MISSING", 409)
    election_identity = {
        "decision_id": election.decision_id,
        "scenario_version": election.scenario_version,
        "pension_start_date": election.pension_start_date.isoformat(),
        "target_year": election.target_year,
        "survivors_option": election.survivors_option,
        "spouse_age_diff": election.spouse_age_diff,
        "coefficient_selection": election.coefficient_selection,
        "company_name": election.company_name,
        "option_name": election.option_name,
    }
    # Include DB-owned coefficient facts so profile/product changes invalidate
    # prior documentary reviews even without an explicit scenario version bump.
    inventory_preimage = {
        "manifest_fingerprint": manifest["manifest_fingerprint"],
        "election": election_identity,
        "product_version": product.version,
        "product_type": product.product_type,
        "product_start_date": product.start_date.isoformat() if product.start_date else None,
        "profile_birth_date": profile.birth_date.isoformat(),
        "profile_gender": profile.gender,
    }
    return {
        "client_id": client_id, "scenario_id": scenario_id,
        "scenario_version": manifest["scenario_version"],
        "decision_id": decision_id,
        "product_id": decision["product_id"],
        "component_id": decision["component_id"],
        "product_version": product.version,
        "manifest_fingerprint": manifest["manifest_fingerprint"],
        "inventory_fingerprint": _fingerprint(inventory_preimage),
        "election_fingerprint": _fingerprint(election_identity),
        "source_fingerprint": decision["source"]["source_fingerprint"],
    }
