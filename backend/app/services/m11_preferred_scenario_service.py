"""Single-planner M11 choice ledger; never authorizes or executes calculations."""
from __future__ import annotations
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.client import Client
from app.models.scenario_draft import ScenarioDraft
from app.models.m11_preferred_scenario import M11PreferredScenarioRevision
from app.services.scenario_draft_service import DraftError

def _serialize(row: M11PreferredScenarioRevision) -> dict:
    return {
        "selection_id": row.selection_id, "client_id": row.client_id,
        "scenario_id": row.scenario_id, "scenario_version": row.scenario_version,
        "revision": row.revision, "rationale": row.rationale,
        "calculation_references": row.calculation_references,
        "actor_id": row.actor_id,
        "saved_at": row.saved_at.isoformat() if row.saved_at else None,
        "professional_approval": False,
    }

def _history(db: Session, client_id: int) -> list[M11PreferredScenarioRevision]:
    return list(db.scalars(
        select(M11PreferredScenarioRevision)
        .where(M11PreferredScenarioRevision.client_id == client_id)
        .order_by(M11PreferredScenarioRevision.revision.desc())
    ))

def read(db: Session, client_id: int) -> dict:
    if db.get(Client, client_id) is None:
        raise DraftError("CLIENT_NOT_FOUND", 404)
    history = _history(db, client_id)
    latest = history[0] if history else None
    current_scenario = (db.scalar(select(ScenarioDraft).where(
        ScenarioDraft.client_id == client_id,
        ScenarioDraft.scenario_id == latest.scenario_id,
    )) if latest else None)
    outdated = bool(latest and (
        current_scenario is None or current_scenario.version != latest.scenario_version
        or current_scenario.status != "draft"
    ))
    return {
        "client_id": client_id, "current": _serialize(latest) if latest else None,
        "revision": latest.revision if latest else 0,
        "outdated": outdated,
        "history": [_serialize(row) for row in history],
        "calculation_authorized": False, "report_authorized": False,
    }

def save(db: Session, *, client_id: int, scenario_id: str, expected_scenario_version: int,
         expected_selection_revision: int, rationale: str, actor_id: str) -> dict:
    if (type(expected_selection_revision) is not int or expected_selection_revision < 0
            or type(expected_scenario_version) is not int or expected_scenario_version < 1
            or not isinstance(rationale, str) or len(rationale) > 5000
            or not isinstance(actor_id, str) or not actor_id.strip() or len(actor_id) > 128):
        raise DraftError("M11_SELECTION_INVALID", 422)
    # Serialize concurrent M11 saves per client, including the first save.
    client = db.scalar(select(Client).where(Client.client_id == client_id).with_for_update())
    if client is None:
        raise DraftError("CLIENT_NOT_FOUND", 404)
    scenario = db.scalar(select(ScenarioDraft).where(
        ScenarioDraft.client_id == client_id, ScenarioDraft.scenario_id == scenario_id
    ).with_for_update())
    if scenario is None or scenario.status != "draft":
        raise DraftError("M11_SCENARIO_NOT_ACTIVE", 409)
    if scenario.version != expected_scenario_version:
        raise DraftError("M11_SCENARIO_VERSION_CONFLICT", 409)
    previous = db.scalar(select(M11PreferredScenarioRevision).where(
        M11PreferredScenarioRevision.client_id == client_id
    ).order_by(M11PreferredScenarioRevision.revision.desc()).limit(1))
    actual_revision = previous.revision if previous else 0
    if expected_selection_revision != actual_revision:
        raise DraftError("M11_SELECTION_VERSION_CONFLICT", 409)
    # No run is claimed: M09 subject runs do not have an authenticated
    # scenario-draft binding; Stage 6 estimates are not persisted M11 runs.
    row = M11PreferredScenarioRevision(
        selection_id=str(uuid4()), client_id=client_id, scenario_id=scenario_id,
        scenario_version=scenario.version, revision=actual_revision + 1,
        rationale=rationale, calculation_references=[], actor_id=actor_id,
    )
    db.add(row)
    db.flush()
    return read(db, client_id)
