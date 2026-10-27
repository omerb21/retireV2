"""Stage 6 P1B atomic planner factor acknowledgment; no calculation or payout."""
from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.scenario_draft import ScenarioDraft
from app.models.scenario_pension_factor_admission import ScenarioPensionFactorAdmission
from app.models.pension_product import PensionProduct
from app.services.scenario_coefficient_review_context_service import derive_documentary_review_context
from app.services.scenario_input_manifest_service import build_inert_manifest
from app.services.scenario_permission_preview_service import (
    _derive_pension_action_permission_in_transaction,
)
from app.services.scenario_pension_factor_contract import (
    validate_admission_preimage, fingerprint_admission_preimage,
)
from app.services.pension_monthly_basis_service import canonical_bytes, factor


class PensionFactorWriteBlocked(RuntimeError):
    pass


def _blocked(code: str):
    raise PensionFactorWriteBlocked(code)


def save_factor_admission(
    db: Session, *, client_id: int, scenario_id: str, decision_id: str,
    expected_scenario_version: int, expected_admission_revision: int,
    actor_id: str, factor_value: str, factor_evidence_type: str,
    factor_evidence_reference: str, payout_option_name: str,
    expected_manifest_fingerprint: str, expected_election_fingerprint: str,
) -> dict:
    """Append one revision in caller-owned PostgreSQL write transaction.

    The route must start a fresh REPEATABLE READ transaction and take this
    function's returned result only after successful transaction commit.
    Caller MUST derive actor_id from authenticated session, never request body.
    No read-only P1A helper is bypassed: identical private ruleset evaluation
    runs on the same locked DB snapshot, without opening another transaction.
    """
    if (type(client_id) is not int or client_id <= 0 or not scenario_id or
            not decision_id or not actor_id or type(expected_scenario_version) is not int
            or expected_scenario_version <= 0 or type(expected_admission_revision) is not int
            or expected_admission_revision < 0):
        _blocked("FACTOR_ADMISSION_REQUEST_INVALID")
    if db.get_bind().dialect.name != "postgresql" or not db.in_transaction():
        _blocked("FACTOR_ADMISSION_WRITE_TRANSACTION_REQUIRED")
    if db.new or db.dirty or db.deleted:
        _blocked("FACTOR_ADMISSION_DIRTY_SESSION")
    isolation = db.execute(text("SHOW transaction_isolation")).scalar_one()
    read_only = db.execute(text("SHOW transaction_read_only")).scalar_one()
    if str(isolation).lower() != "repeatable read" or str(read_only).lower() != "off":
        _blocked("FACTOR_ADMISSION_WRITE_TRANSACTION_REQUIRED")
    # Serialize acknowledgments to one scenario; this is the CAS lock.
    scenario = db.scalar(select(ScenarioDraft).where(
        ScenarioDraft.client_id == client_id,
        ScenarioDraft.scenario_id == scenario_id,
    ).with_for_update())
    if (scenario is None or scenario.status != "draft" or
            scenario.version != expected_scenario_version):
        _blocked("FACTOR_ADMISSION_SCENARIO_STALE")
    prior_revision = db.scalar(select(ScenarioPensionFactorAdmission.admission_revision).where(
        ScenarioPensionFactorAdmission.client_id == client_id,
        ScenarioPensionFactorAdmission.scenario_id == scenario_id,
        ScenarioPensionFactorAdmission.decision_id == decision_id,
    ).order_by(ScenarioPensionFactorAdmission.admission_revision.desc()).limit(1))
    prior_revision = prior_revision or 0
    if prior_revision != expected_admission_revision:
        _blocked("FACTOR_ADMISSION_REVISION_CONFLICT")

    permission = _derive_pension_action_permission_in_transaction(
        db, client_id=client_id, scenario_id=scenario_id, decision_id=decision_id)
    review = derive_documentary_review_context(
        db, client_id=client_id, scenario_id=scenario_id, decision_id=decision_id)
    manifest = build_inert_manifest(db, client_id, scenario_id)
    if (review["manifest_fingerprint"] != expected_manifest_fingerprint or
            review["election_fingerprint"] != expected_election_fingerprint):
        _blocked("FACTOR_ADMISSION_CONTEXT_STALE")
    decision = next((item for item in manifest["decisions"]
                     if item["decision_id"] == decision_id and item["action"] == "pension"), None)
    if decision is None or decision["source"] is None:
        _blocked("FACTOR_ADMISSION_DECISION_INVALID")
    product = db.scalar(select(PensionProduct).where(
        PensionProduct.client_id == client_id,
        PensionProduct.product_id == decision["product_id"],
    ))
    if product is None or product.statement_date is None:
        _blocked("FACTOR_ADMISSION_STATEMENT_DATE_MISSING")
    from app.models.scenario_draft_pension_election import ScenarioDraftPensionElection
    election = db.scalar(select(ScenarioDraftPensionElection).where(
        ScenarioDraftPensionElection.scenario_id == scenario_id,
        ScenarioDraftPensionElection.decision_id == decision_id,
        ScenarioDraftPensionElection.scenario_version == expected_scenario_version,
    ))
    if election is None:
        _blocked("FACTOR_ADMISSION_ELECTION_MISSING")
    if election.coefficient_selection != "manual_review_required":
        _blocked("FACTOR_ADMISSION_NOT_MANUAL")
    if payout_option_name != election.option_name:
        _blocked("FACTOR_ADMISSION_OPTION_MISMATCH")
    try:
        canonical_factor = factor(factor_value)
    except (ValueError, TypeError):
        _blocked("FACTOR_ADMISSION_FACTOR_INVALID")
    created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    preimage = dict(
        contract_version="SCENARIO_PENSION_FACTOR_ADMISSION_FINGERPRINT_V1",
        client_id=client_id, scenario_id=scenario_id, scenario_version=scenario.version,
        decision_id=decision_id, admission_revision=prior_revision + 1,
        manifest_fingerprint=manifest["manifest_fingerprint"],
        source_fingerprint=decision["source"]["source_fingerprint"],
        election_fingerprint=review["election_fingerprint"],
        ruleset_digest=permission["ruleset_digest"],
        permission_admission_fingerprint=permission["permission_admission_fingerprint"],
        source_product_id=decision["product_id"],
        source_component_id=decision["component_id"],
        component_code=decision["component_code"], amount=decision["amount"],
        statement_date=product.statement_date.isoformat(),
        pension_start_date=election.pension_start_date.isoformat(),
        factor_value=canonical_factor, factor_original_representation="DIVISOR",
        factor_evidence_type=factor_evidence_type,
        factor_evidence_reference=factor_evidence_reference,
        survivors_option=election.survivors_option,
        spouse_age_diff=election.spouse_age_diff,
        payout_option_name=payout_option_name,
        actor_id=actor_id, acknowledged_at_utc=created,
    )
    try:
        validate_admission_preimage(preimage)
    except (ValueError, TypeError) as exc:
        _blocked("FACTOR_ADMISSION_PREIMAGE_INVALID")
    digest = fingerprint_admission_preimage(preimage)
    row = ScenarioPensionFactorAdmission(
        admission_id=str(uuid4()), client_id=client_id, scenario_id=scenario_id,
        decision_id=decision_id, scenario_version=scenario.version,
        admission_revision=prior_revision + 1, actor_id=actor_id,
        preimage_json=canonical_bytes(preimage).decode("utf-8"),
        record_fingerprint=digest,
        permission_admission_fingerprint=permission["permission_admission_fingerprint"],
        manifest_fingerprint=manifest["manifest_fingerprint"],
        source_fingerprint=decision["source"]["source_fingerprint"],
        election_fingerprint=review["election_fingerprint"],
    )
    db.add(row)
    db.flush()
    # DO NOT COMMIT; caller owns atomic transaction and rollback.
    return dict(admission_revision=row.admission_revision,
                professional_admission_fingerprint=digest,
                execution_allowed=False)
