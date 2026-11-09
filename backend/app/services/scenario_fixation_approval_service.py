"""Scenario-scoped fixation professional draft ledger.

All reads and writes operate in their caller's PostgreSQL Session. No engine,
fixation admission, preview, tax calculation or official approval is invoked.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.scenario_draft import ScenarioDraft
from app.models.scenario_fixation_approval import (
    ScenarioFixationApprovalHead, ScenarioFixationApprovalRevision,
)
from app.schemas.scenario_fixation_approval import FixationProfessionalDraftReplace
from app.services.scenario_draft_service import DraftError, _scenario
from app.services.scenario_input_manifest_service import _fingerprint
from app.services.scenario_snapshot_candidate_service import _build_pair_in_snapshot

CONTRACT = "SCENARIO_FIXATION_PROFESSIONAL_APPROVAL_V1"
# No positive gate exists. This is intentional until a separate, admitted
# professional authority contract is approved.
UNRESOLVED_AUTHORITY = "FIXATION_PROFESSIONAL_GATE_NOT_ADMITTED"


def _current(db, client_id: int, scenario_id: str) -> dict:
    # Late import prevents a circular dependency with unified projection.
    from app.services.scenario_unified_engine_binding_service import _assemble_bound
    pair = _build_pair_in_snapshot(db, client_id, scenario_id, None)
    bound = _assemble_bound(db, pair, client_id, scenario_id,
                            start_month=None, end_month=None)
    return bound["domain_results"]["fixation_tax"]["readiness"]


def _head(db, client_id, scenario_id):
    return db.scalar(select(ScenarioFixationApprovalHead).where(
        ScenarioFixationApprovalHead.client_id == client_id,
        ScenarioFixationApprovalHead.scenario_id == scenario_id,
    ))


def _revision(db, head):
    return db.scalar(select(ScenarioFixationApprovalRevision).where(
        ScenarioFixationApprovalRevision.approval_id == head.approval_id,
        ScenarioFixationApprovalRevision.approval_version == head.current_version,
    ))


def project_approval(db, client_id: int, scenario_id: str, readiness: dict) -> dict:
    """For unified result: reuse its already-derived readiness, no recursion."""
    if any(readiness[k] != val for k, val in (
        ("client_id", client_id), ("scenario_id", scenario_id)
    )):
        raise DraftError("FIXATION_APPROVAL_READINESS_IDENTITY_INVALID", 409)
    head = _head(db, client_id, scenario_id)
    blockers = set(readiness["blockers"])
    blockers.add(UNRESOLVED_AUTHORITY)
    if head is None:
        return {
            "contract": CONTRACT, "client_id": client_id,
            "scenario_id": scenario_id, "approval_id": None,
            "approval_version": 0, "record_status": "MISSING",
            "validity_state": "BLOCKED",
            "decisions": [], "actor_id": None,
            "approval_fingerprint": None, "dependency_fingerprint": None,
            "readiness_fingerprint_at_save": None,
            "blockers": sorted(blockers),
            "professional_authority": False, "execution_allowed": False,
            "tax_authority_approval": None,
        }
    row = _revision(db, head)
    if row is None or row.client_id != client_id or row.scenario_id != scenario_id:
        raise DraftError("FIXATION_APPROVAL_REVISION_IDENTITY_INVALID", 409)
    current_dependency = _fingerprint({
        "manifest_fingerprint": readiness["manifest_fingerprint"],
        "readiness_fingerprint": readiness["readiness_fingerprint"],
        "decisions": row.decisions_json,
    })
    stale = (
        row.scenario_version != readiness["scenario_version"]
        or row.manifest_fingerprint != readiness["manifest_fingerprint"]
        or row.readiness_fingerprint != readiness["readiness_fingerprint"]
        or row.dependency_fingerprint != current_dependency
    )
    if stale:
        blockers.add("FIXATION_PROFESSIONAL_APPROVAL_STALE")
    return {
        "contract": CONTRACT, "client_id": client_id, "scenario_id": scenario_id,
        "approval_id": head.approval_id,
        "approval_version": head.current_version,
        "scenario_version_at_save": row.scenario_version,
        "manifest_fingerprint_at_save": row.manifest_fingerprint,
        "readiness_fingerprint_at_save": row.readiness_fingerprint,
        "dependency_fingerprint": row.dependency_fingerprint,
        "approval_fingerprint": row.approval_fingerprint,
        "record_status": row.status, "validity_state": "STALE" if stale else "BLOCKED",
        "decisions": row.decisions_json["decisions"],
        "actor_id": row.actor_id,
        "blockers": sorted(blockers),
        "professional_authority": False, "execution_allowed": False,
        "tax_authority_approval": None,
    }


def read(db, client_id: int, scenario_id: str) -> dict:
    _scenario(db, client_id, scenario_id)
    return project_approval(db, client_id, scenario_id, _current(db, client_id, scenario_id))


def history(db, client_id: int, scenario_id: str) -> list[dict]:
    _scenario(db, client_id, scenario_id)
    head = _head(db, client_id, scenario_id)
    if head is None:
        return []
    rows = db.scalars(select(ScenarioFixationApprovalRevision).where(
        ScenarioFixationApprovalRevision.approval_id == head.approval_id,
    ).order_by(ScenarioFixationApprovalRevision.approval_version)).all()
    return [{
        "revision_id": r.revision_id, "approval_id": r.approval_id,
        "approval_version": r.approval_version, "scenario_version": r.scenario_version,
        "manifest_fingerprint": r.manifest_fingerprint,
        "readiness_fingerprint": r.readiness_fingerprint,
        "dependency_fingerprint": r.dependency_fingerprint,
        "approval_fingerprint": r.approval_fingerprint,
        "decisions": r.decisions_json["decisions"],
        "blockers": r.blockers_json, "status": r.status,
        "action": r.action, "actor_id": r.actor_id,
        "occurred_at": r.occurred_at.isoformat(),
        "professional_authority": False,
        "tax_authority_approval": None,
    } for r in rows]


def save_draft(db, client_id: int, scenario_id: str,
               request: FixationProfessionalDraftReplace, actor: str) -> dict:
    if db.get_bind().dialect.name != "postgresql":
        raise DraftError("FIXATION_APPROVAL_REQUIRES_POSTGRESQL", 503)
    if not actor or actor == "local-development-only":
        raise DraftError("FIXATION_PROFESSIONAL_ACTOR_REQUIRED", 403)
    # Serialize all saves for the same scenario. A concurrent writer must wait
    # before validating CAS. Source changes after commit are caught by reads.
    scenario = db.scalar(select(ScenarioDraft).where(
        ScenarioDraft.client_id == client_id,
        ScenarioDraft.scenario_id == scenario_id,
    ).with_for_update())
    if scenario is None:
        raise DraftError("SCENARIO_NOT_FOUND", 404)
    if scenario.status != "draft":
        raise DraftError("FIXATION_APPROVAL_SCENARIO_INACTIVE", 409)
    readiness = _current(db, client_id, scenario_id)
    if (request.expected_scenario_version != readiness["scenario_version"]
            or request.expected_manifest_fingerprint != readiness["manifest_fingerprint"]
            or request.expected_readiness_fingerprint != readiness["readiness_fingerprint"]):
        raise DraftError("FIXATION_APPROVAL_SOURCE_CONFLICT", 409)
    records = [r.model_dump(mode="json") for r in request.decisions]
    content = {"decisions": sorted(records, key=lambda r: (r["group"], r["source_id"]))}
    # Asserted source IDs and evidence references are recorded, not promoted to
    # admission. Unknown sources remain explicitly blocked in this phase.
    head = _head(db, client_id, scenario_id)
    expected = request.expected_approval_version
    if head is None:
        if expected != 0:
            raise DraftError("FIXATION_APPROVAL_VERSION_CONFLICT", 409)
        approval_id = uuid4().hex
        db.execute(pg_insert(ScenarioFixationApprovalHead).values(
            approval_id=approval_id, client_id=client_id,
            scenario_id=scenario_id, current_version=1,
            status="DRAFT", updated_by=actor,
        ).on_conflict_do_nothing(index_elements=["client_id", "scenario_id"]))
        head = _head(db, client_id, scenario_id)
        if head is None or head.approval_id != approval_id:
            raise DraftError("FIXATION_APPROVAL_VERSION_CONFLICT", 409)
        version = 1
    else:
        if expected != head.current_version:
            raise DraftError("FIXATION_APPROVAL_VERSION_CONFLICT", 409)
        version = expected + 1
        result = db.execute(update(ScenarioFixationApprovalHead).where(
            ScenarioFixationApprovalHead.approval_id == head.approval_id,
            ScenarioFixationApprovalHead.client_id == client_id,
            ScenarioFixationApprovalHead.scenario_id == scenario_id,
            ScenarioFixationApprovalHead.current_version == expected,
        ).values(current_version=version, updated_by=actor))
        if result.rowcount != 1:
            raise DraftError("FIXATION_APPROVAL_VERSION_CONFLICT", 409)
    dependency = _fingerprint({
        "manifest_fingerprint": readiness["manifest_fingerprint"],
        "readiness_fingerprint": readiness["readiness_fingerprint"],
        "decisions": content,
    })
    approval_fp = _fingerprint({
        "contract": CONTRACT, "client_id": client_id, "scenario_id": scenario_id,
        "approval_version": version, "dependency_fingerprint": dependency,
        "actor_id": actor, "status": "DRAFT",
    })
    db.add(ScenarioFixationApprovalRevision(
        revision_id=uuid4().hex, approval_id=head.approval_id,
        client_id=client_id, scenario_id=scenario_id,
        approval_version=version, scenario_version=readiness["scenario_version"],
        manifest_fingerprint=readiness["manifest_fingerprint"],
        readiness_fingerprint=readiness["readiness_fingerprint"],
        dependency_fingerprint=dependency, approval_fingerprint=approval_fp,
        decisions_json=content, blockers_json=readiness["blockers"],
        status="DRAFT", action="SAVE_DRAFT", actor_id=actor,
        occurred_at=datetime.now(timezone.utc),
    ))
    db.flush()
    return project_approval(db, client_id, scenario_id, readiness)


def request_internal_approval(db, client_id: int, scenario_id: str,
                              expected_version: int, expected_fingerprint: str,
                              actor: str) -> dict:
    """Explicit action with fail-closed gate. Does not write or invoke tax."""
    if not actor or actor == "local-development-only":
        raise DraftError("FIXATION_PROFESSIONAL_ACTOR_REQUIRED", 403)
    item = read(db, client_id, scenario_id)
    if item["approval_version"] != expected_version or (
            item["approval_fingerprint"] != expected_fingerprint):
        raise DraftError("FIXATION_APPROVAL_VERSION_CONFLICT", 409)
    if item["validity_state"] == "STALE":
        raise DraftError("FIXATION_PROFESSIONAL_APPROVAL_STALE", 409)
    # The readiness contract is explicitly BLOCKED. There is no sanctioned
    # evidence-to-admission transition yet; no synthetic happy path allowed.
    raise DraftError("FIXATION_PROFESSIONAL_GATE_NOT_ADMITTED", 422)
