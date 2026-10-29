"""Non-authoritative scenario draft store. No factual writes or conversion calls."""
from __future__ import annotations

from decimal import Decimal
import hashlib
import json
import unicodedata
from uuid import uuid4
from sqlalchemy import select, update, delete
from sqlalchemy.orm import Session

from app.models.client import Client
from app.models.pension_product import (
    COMPONENT_CODES, PensionProduct, PensionProductComponent,
)
from app.models.scenario_draft import ScenarioDraft, ScenarioDraftDecision, ScenarioDraftRevision
from app.models.scenario_draft_pension_election import ScenarioDraftPensionElection


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



def _canonical_json(value: dict) -> str:
    def normalize(item):
        if isinstance(item, str):
            return unicodedata.normalize("NFC", item)
        if isinstance(item, dict):
            return {normalize(key): normalize(child) for key, child in item.items()}
        if isinstance(item, list):
            return [normalize(child) for child in item]
        return item
    return json.dumps(
        normalize(value), ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    )


def _source_evidence(product: PensionProduct, component: PensionProductComponent) -> dict:
    """Return the closed database-derived source preimage plus its digest.

    The digest is a staleness identity only.  Callers must first prove that the
    product belongs to the addressed client and that the component belongs to
    that product; a digest supplied by a browser is never source evidence.
    """
    values = (
        product.product_id, product.product_type, product.source_kind,
        product.source_identity, component.product_id, component.component_id,
        component.component_code,
    )
    if (
        type(product.client_id) is not int or product.client_id <= 0
        or type(product.version) is not int or product.version <= 0
        or not all(isinstance(value, str) and value for value in values)
        or product.source_kind not in {"manual", "imported"}
        or component.component_code not in COMPONENT_CODES
        or component.product_id != product.product_id
        or not isinstance(component.balance, Decimal)
        or not component.balance.is_finite() or component.balance < 0
        or component.balance.as_tuple().exponent < -2
    ):
        raise DraftError("SCENARIO_SOURCE_EVIDENCE_INVALID", 409)
    fields = {
        "schema": "scenario-draft-source-v1",
        "client_id": product.client_id,
        "product_id": product.product_id,
        "product_version": product.version,
        "product_type": product.product_type,
        "source_kind": product.source_kind,
        "source_identity": product.source_identity,
        "component_product_id": component.product_id,
        "component_id": component.component_id,
        "component_code": component.component_code,
        "balance": format(component.balance, ".2f"),
    }
    return {
        **fields,
        "source_fingerprint": hashlib.sha256(
            _canonical_json(fields).encode("utf-8"),
        ).hexdigest(),
    }


def _source_digest(product: PensionProduct, component: PensionProductComponent) -> str:
    """Database-derived draft staleness identity, never permission authority."""
    return _source_evidence(product, component)["source_fingerprint"]


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
    output_decisions = [_decision_json(item) for item in decisions]
    tracked = output_decisions
    if tracked:
        product_ids = {item["source_product_id"] for item in tracked}
        products = {
            p.product_id: p
            for p in db.scalars(select(PensionProduct).where(
                PensionProduct.client_id == client_id, PensionProduct.product_id.in_(product_ids)
            ))
        }
        component_ids = {item["source_component_id"] for item in tracked}
        components = {
            c.component_id: c
            for c in db.scalars(select(PensionProductComponent).where(
                PensionProductComponent.component_id.in_(component_ids)
            ))
        }
        for item in tracked:
            product = products.get(item["source_product_id"])
            component = components.get(item["source_component_id"])
            if (product is None or component is None
                or component.product_id != item["source_product_id"]
                or component.component_code != item["component_code"]
                or item["source_fingerprint_at_review"] is None
                or _source_digest(product, component) != item["source_fingerprint_at_review"]):
                item["validation_state"] = "needs_revalidation"
    return {
        "scenario_id": scenario.scenario_id, "client_id": scenario.client_id,
        "name": scenario.name, "status": ("needs_revalidation" if scenario.status != "archived" and any(d["validation_state"] == "needs_revalidation" for d in output_decisions) else scenario.status), "version": scenario.version,
        "created_by": scenario.created_by, "updated_by": scenario.updated_by,
        "decisions": output_decisions,
        "financial_validation": "not_evaluated",
    }


def list_drafts(db: Session, client_id: int) -> list[dict]:
    _client(db, client_id)
    ids = db.scalars(select(ScenarioDraft.scenario_id).where(
        ScenarioDraft.client_id == client_id
    ).order_by(ScenarioDraft.created_at, ScenarioDraft.scenario_id)).all()
    return [read(db, client_id, scenario_id) for scenario_id in ids]


def _revision(db: Session, scenario: ScenarioDraft, action: str, actor: str, *,
              audit_extra: dict | None = None) -> dict:
    snapshot = read(db, scenario.client_id, scenario.scenario_id)
    if audit_extra is not None:
        snapshot = {**snapshot, **audit_extra}
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
    known_ids = {item.decision_id for item in existing}
    supplied_ids = [item.decision_id for item in payload.decisions if item.decision_id is not None]
    if len(supplied_ids) != len(set(supplied_ids)) or not set(supplied_ids).issubset(known_ids):
        raise DraftError("SCENARIO_DECISION_ID_MISMATCH", 422)
    # Any changed decision set invalidates all existing pension elections.
    db.execute(delete(ScenarioDraftPensionElection).where(ScenarioDraftPensionElection.scenario_id == scenario_id))
    for item in existing:
        db.delete(item)
    db.flush()
    product_ids = {item.source_product_id for item in payload.decisions}
    products = {
        p.product_id: p
        for p in db.scalars(select(PensionProduct).where(
            PensionProduct.client_id == client_id, PensionProduct.product_id.in_(product_ids)
        ))
    } if product_ids else {}
    for item in payload.decisions:
        product = products.get(item.source_product_id)
        # Capture source version only when a canonical row really exists.
        # It is a staleness anchor, NEVER a professional approval.
        component = db.scalar(select(PensionProductComponent).where(
            PensionProductComponent.product_id == item.source_product_id,
            PensionProductComponent.component_id == item.source_component_id,
            PensionProductComponent.component_code == item.component_code,
        )) if product is not None else None
        version = product.version if component is not None else None
        db.add(ScenarioDraftDecision(
            decision_id=item.decision_id or uuid4().hex, scenario_id=scenario_id,
            source_product_id=item.source_product_id,
            source_component_id=item.source_component_id,
            component_code=item.component_code, amount=item.amount,
            action=item.action, effective_date=item.effective_date,
            validation_state="unverified", product_version_at_review=version,
            source_fingerprint_at_review=_source_digest(product, component) if component is not None else None,
        ))
    db.flush()
    return _revision(db, scenario, "replace", actor)


def rename(db: Session, client_id: int, scenario_id: str, name: str,
           expected: int, actor: str) -> dict:
    """Rename draft metadata without re-reviewing or replacing decisions.

    Source fingerprints and pension elections are version-bound evidence. A
    display-name edit is not a factual review and therefore may not refresh,
    delete, or otherwise rewrite that evidence.
    """
    scenario = _scenario(db, client_id, scenario_id)
    _cas(db, scenario, expected, actor, name=name)
    return _revision(db, scenario, "rename", actor)


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
