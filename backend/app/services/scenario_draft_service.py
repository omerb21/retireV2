"""Non-authoritative scenario draft store. No factual writes or conversion calls."""
from __future__ import annotations

from decimal import Decimal
import json
from uuid import uuid4
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.client import Client
from app.models.scenario_draft import ScenarioDraft, ScenarioDraftDecision, ScenarioDraftRevision


class DraftError(RuntimeError):
    def __init__(self, code: str, status: int = 409):
        super().__init__(code)
        self.code, self.status = code, status


def _client(db: Session, client_id: int) -> None:
    if db.scalar(select(Client.client_id).where(Client.client_id == client_id)) is None:
        raise DraftError("SCENARIO_NOT_FOUND", 404)


def _scenario(db: Session, client_id: int, scenario_id: str) -> ScenarioDraft:
    scenario = db.scalar(select(ScenarioDraft).where(
        ScenarioDraft.client_id == client_id, ScenarioDraft.scenario_id == scenario_id
    ))
    if scenario is None:
        raise DraftError("SCENARIO_NOT_FOUND", 404)
    return scenario


def _decision_json(row: ScenarioDraftDecision) -> dict:
    return {
        "decision_id": row.decision_id, "source_product_id": row.source_product_id,
        "source_component_id": row.source_component_id, "component_code": row.component_code,
        "amount": format(row.amount, ".2f"), "action": row.action,
        "effective_date": row.effective_date.isoformat(),
        "validation_state": row.validation_state,
        "product_version_at_review": row.product_version_at_review,
        "source_fingerprint_at_review": row.source_fingerprint_at_review,
        "ruleset_digest_at_review": row.ruleset_digest_at_review,
        "permission_preview_id_at_review": row.permission_preview_id_at_review,
    }


def read(db: Session, client_id: int, scenario_id: str) -> dict:
    scenario = _scenario(db, client_id, scenario_id)
    decisions = db.scalars(select(ScenarioDraftDecision).where(
        ScenarioDraftDecision.scenario_id == scenario.scenario_id
    ).order_by(ScenarioDraftDecision.decision_id)).all()
    return {
        "scenario_id": scenario.scenario_id, "client_id": scenario.client_id,
        "name": scenario.name, "status": scenario.status, "version": scenario.version,
        "created_by": scenario.created_by, "updated_by": scenario.updated_by,
        "decisions": [_decision_json(item) for item in decisions],
        "financial_validation": "not_evaluated",
    }


def list_drafts(db: Session, client_id: int) -> list[dict]:
    _client(db, client_id)
    ids = db.scalars(select(ScenarioDraft.scenario_id).where(
        ScenarioDraft.client_id == client_id
    ).order_by(ScenarioDraft.created_at, ScenarioDraft.scenario_id)).all()
    return [read(db, client_id, scenario_id) for scenario_id in ids]


def _revision(db: Session, scenario: ScenarioDraft, action: str, actor: str) -> dict:
    snapshot = read(db, scenario.client_id, scenario.scenario_id)
    db.add(ScenarioDraftRevision(
        revision_id=uuid4().hex, scenario_id=scenario.scenario_id,
        version=scenario.version, action=action, actor=actor,
        snapshot_json=json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
    ))
    return snapshot


def create(db: Session, client_id: int, name: str, actor: str) -> dict:
    _client(db, client_id)
    scenario = ScenarioDraft(scenario_id=uuid4().hex, client_id=client_id,
                             name=name, status="draft", version=1,
                             created_by=actor, updated_by=actor)
    db.add(scenario)
    db.flush()
    return _revision(db, scenario, "create", actor)


def _cas(db: Session, scenario: ScenarioDraft, expected: int, actor: str, **values) -> None:
    if scenario.status == "archived":
        raise DraftError("SCENARIO_ARCHIVED", 409)
    result = db.execute(update(ScenarioDraft).where(
        ScenarioDraft.scenario_id == scenario.scenario_id,
        ScenarioDraft.client_id == scenario.client_id,
        ScenarioDraft.version == expected,
        ScenarioDraft.status != "archived",
    ).values(version=expected + 1, updated_by=actor, **values))
    if result.rowcount != 1:
        raise DraftError("SCENARIO_VERSION_CONFLICT", 409)
    db.flush()
    db.refresh(scenario)


def replace(db: Session, client_id: int, scenario_id: str, payload, actor: str) -> dict:
    scenario = _scenario(db, client_id, scenario_id)
    _cas(db, scenario, payload.expected_version, actor, name=payload.name)
    existing = db.scalars(select(ScenarioDraftDecision).where(
        ScenarioDraftDecision.scenario_id == scenario_id
    )).all()
    for item in existing:
        db.delete(item)
    db.flush()
    for item in payload.decisions:
        db.add(ScenarioDraftDecision(
            decision_id=uuid4().hex, scenario_id=scenario_id,
            source_product_id=item.source_product_id,
            source_component_id=item.source_component_id,
            component_code=item.component_code, amount=item.amount,
            action=item.action, effective_date=item.effective_date,
            validation_state="unverified",
        ))
    db.flush()
    return _revision(db, scenario, "replace", actor)


def archive(db: Session, client_id: int, scenario_id: str, expected: int, actor: str) -> dict:
    scenario = _scenario(db, client_id, scenario_id)
    _cas(db, scenario, expected, actor, status="archived")
    return _revision(db, scenario, "archive", actor)


def duplicate(db: Session, client_id: int, scenario_id: str, name: str, actor: str) -> dict:
    original = read(db, client_id, scenario_id)
    result = create(db, client_id, name, actor)
    if original["decisions"]:
        # New draft is intentionally unverified; no prior approvals carry over.
        from app.schemas.scenario_draft import DraftDecisionWrite, DraftReplace
        decisions = [
            DraftDecisionWrite(
                source_product_id=d["source_product_id"],
                source_component_id=d["source_component_id"],
                component_code=d["component_code"],
                amount=Decimal(d["amount"]), action=d["action"],
                effective_date=d["effective_date"],
            ) for d in original["decisions"]
        ]
        result = replace(db, client_id, result["scenario_id"],
                         DraftReplace(name=name, expected_version=1, decisions=decisions), actor)
    return result
