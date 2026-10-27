"""Stage 6 P1B: verification of persisted professional approval; no calculation.

Must be called in a fresh caller-owned PostgreSQL REPEATABLE READ READ ONLY
snapshot. An immutable audit row is never authority by itself.
"""
from __future__ import annotations
import json
import hmac
from urllib.parse import quote

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.scenario_pension_factor_admission import ScenarioPensionFactorAdmission
from app.services.scenario_pension_factor_contract import (
    fingerprint_admission_preimage, validate_admission_preimage,
)
from app.services.pension_monthly_basis_service import canonical_bytes
from app.services.scenario_permission_preview_service import (
    derive_pension_action_permission_admission,
)
from app.services.scenario_coefficient_review_context_service import (
    derive_documentary_review_context,
)
from app.services.scenario_input_manifest_service import build_inert_manifest


class FactorAdmissionBlocked(RuntimeError):
    pass


def _block(code: str):
    raise FactorAdmissionBlocked(code)


def read_current_admission(
    db: Session, *, client_id: int, scenario_id: str, decision_id: str,
 ) -> dict:
    """Reverify N1.3 against DB-derived decision/election/date context.

    All current identities are independently derived from PostgreSQL within the
    caller's snapshot; there is no caller-supplied current_context.
    Returns no financial result.
    """
    permission = derive_pension_action_permission_admission(
        db, client_id=client_id, scenario_id=scenario_id, decision_id=decision_id)
    from app.models.scenario_draft_pension_election import ScenarioDraftPensionElection
    from app.models.pension_product import PensionProduct
    review = derive_documentary_review_context(
        db, client_id=client_id, scenario_id=scenario_id, decision_id=decision_id)
    manifest = build_inert_manifest(db, client_id, scenario_id)
    decision = next((d for d in manifest["decisions"] if d["decision_id"] == decision_id), None)
    if decision is None or decision["source"] is None:
        _block("FACTOR_CURRENT_DECISION_INVALID")
    product = db.scalar(select(PensionProduct).where(
        PensionProduct.client_id == client_id,
        PensionProduct.product_id == decision["product_id"]))
    election = db.scalar(select(ScenarioDraftPensionElection).where(
        ScenarioDraftPensionElection.scenario_id == scenario_id,
        ScenarioDraftPensionElection.decision_id == decision_id,
        ScenarioDraftPensionElection.scenario_version == manifest["scenario_version"]))
    if (product is None or product.statement_date is None or election is None
            or election.coefficient_selection != "manual_review_required"
            or not isinstance(election.option_name, str) or not election.option_name.strip()
            or election.pension_start_date < product.statement_date):
        _block("FACTOR_CURRENT_CONTEXT_MISSING")
    current_context = {
        "scenario_version": manifest["scenario_version"],
        "manifest_fingerprint": manifest["manifest_fingerprint"],
        "source_fingerprint": decision["source"]["source_fingerprint"],
        "election_fingerprint": review["election_fingerprint"],
        "source_product_id": decision["product_id"],
        "source_component_id": decision["component_id"],
        "component_code": decision["component_code"],
        "amount": decision["amount"],
        "statement_date": product.statement_date.isoformat(),
        "pension_start_date": election.pension_start_date.isoformat(),
        "survivors_option": election.survivors_option,
        "spouse_age_diff": election.spouse_age_diff,
        "payout_option_name": election.option_name,
    }
    rows = db.scalars(select(ScenarioPensionFactorAdmission).where(
        ScenarioPensionFactorAdmission.client_id == client_id,
        ScenarioPensionFactorAdmission.scenario_id == scenario_id,
        ScenarioPensionFactorAdmission.decision_id == decision_id,
    ).order_by(ScenarioPensionFactorAdmission.admission_revision.desc())).all()
    if not rows:
        _block("FACTOR_ADMISSION_MISSING")
    latest = rows[0]
    try:
        data = json.loads(latest.preimage_json)
        validate_admission_preimage(data)
    except (ValueError, TypeError, KeyError):
        _block("FACTOR_ADMISSION_INVALID")
    digest = fingerprint_admission_preimage(data)
    if not hmac.compare_digest(digest, latest.record_fingerprint):
        _block("FACTOR_ADMISSION_TAMPERED")
    if canonical_bytes(data).decode("utf-8") != latest.preimage_json:
        _block("FACTOR_ADMISSION_NONCANONICAL")
    if (data["admission_revision"] != latest.admission_revision
            or data["scenario_version"] != latest.scenario_version
            or data["actor_id"] != latest.actor_id
            or data["client_id"] != latest.client_id
            or data["scenario_id"] != latest.scenario_id
            or data["decision_id"] != latest.decision_id):
        _block("FACTOR_ADMISSION_ROW_MISMATCH")
    # Duplicated indexed provenance columns must match the signed preimage.
    # Otherwise an attacker or a broken migration could mix approval identities.
    if (data["permission_admission_fingerprint"] != latest.permission_admission_fingerprint
            or data["manifest_fingerprint"] != latest.manifest_fingerprint
            or data["source_fingerprint"] != latest.source_fingerprint
            or data["election_fingerprint"] != latest.election_fingerprint):
        _block("FACTOR_ADMISSION_INDEXED_PROVENANCE_MISMATCH")
    if data["permission_admission_fingerprint"] != permission["permission_admission_fingerprint"]:
        _block("FACTOR_PERMISSION_STALE")
    if data["ruleset_digest"] != permission["ruleset_digest"]:
        _block("FACTOR_RULESET_STALE")
    # Includes amount, source, statement_date, election, version, option, payout,
    # current manifest and all other mutable source identities.
    context_fields = (
        "scenario_version", "manifest_fingerprint", "source_fingerprint",
        "election_fingerprint", "source_product_id", "source_component_id",
        "component_code", "amount", "statement_date", "pension_start_date",
        "survivors_option", "spouse_age_diff", "payout_option_name",
    )
    if set(current_context) != set(context_fields):
        _block("FACTOR_CURRENT_CONTEXT_INCOMPLETE")
    if any(data[k] != current_context[k] for k in context_fields):
        _block("FACTOR_ADMISSION_STALE")
    return {
        "schema_version": "SCENARIO_PENSION_FACTOR_ADMISSION_READ_V1",
        "admission_revision": latest.admission_revision,
        "professional_admission_fingerprint": digest,
        "factor_value": data["factor_value"],
        "factor_evidence_type": data["factor_evidence_type"],
        "factor_evidence_reference": data["factor_evidence_reference"],
        "payout_option_name": data["payout_option_name"],
        "actor_id": data["actor_id"],
        "source_id": (
            "scenario-decision:"
            + quote(scenario_id, safe="")
            + ":"
            + quote(decision_id, safe="")
        ),
        "execution_allowed": False,
    }
