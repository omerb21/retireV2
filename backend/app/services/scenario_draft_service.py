"""Non-authoritative scenario draft store. No factual writes or conversion calls."""
from __future__ import annotations

from decimal import Decimal
from datetime import date
import hashlib
import json
import unicodedata
from uuid import uuid4
from sqlalchemy import select, update
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
        allocated: dict[tuple[str, str], Decimal] = {}
        for item in tracked:
            product = products.get(item["source_product_id"])
            component = components.get(item["source_component_id"])
            if (product is None or component is None
                or component.product_id != item["source_product_id"]
                or component.component_code != item["component_code"]
                or item["source_fingerprint_at_review"] is None
                or item["product_version_at_review"] != product.version
                or _source_digest(product, component) != item["source_fingerprint_at_review"]):
                item["validation_state"] = "needs_revalidation"
            if component is not None and product is not None and (
                component.product_id == product.product_id
                and component.component_code == item["component_code"]
            ):
                key = (product.product_id, component.component_id)
                allocated[key] = allocated.get(key, Decimal("0.00")) + Decimal(item["amount"])
        for item in tracked:
            product = products.get(item["source_product_id"])
            component = components.get(item["source_component_id"])
            if (product is not None and component is not None
                    and component.product_id == product.product_id
                    and component.component_code == item["component_code"]
                    and allocated.get((product.product_id, component.component_id),
                                      Decimal("0.00")) > component.balance):
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


def _materially_unchanged_decision(previous: ScenarioDraftDecision, incoming) -> bool:
    """Only a true no-op retains an election across the draft revision.

    Decision IDs alone are insufficient: a changed amount, source, date, action
    or component changes the pension decision's financial meaning.
    """
    return (
        previous.source_product_id == incoming.source_product_id
        and previous.source_component_id == incoming.source_component_id
        and previous.component_code == incoming.component_code
        and previous.amount == incoming.amount
        and previous.action == incoming.action
        and previous.effective_date == incoming.effective_date
    )


def replace(db: Session, client_id: int, scenario_id: str, payload, actor: str) -> dict:
    """Atomically replace one draft, preserving only valid *draft elections*.

    This is NOT an admission or an execution. Professional factor admissions and
    earlier monetary results remain bound to their old scenario revision.
    A new scenario version always requires fresh professional verification.
    """
    scenario = _scenario(db, client_id, scenario_id)
    _cas(db, scenario, payload.expected_version, actor, name=payload.name)

    existing = db.scalars(select(ScenarioDraftDecision).where(
        ScenarioDraftDecision.scenario_id == scenario_id
    )).all()
    previous_by_id = {row.decision_id: row for row in existing}
    supplied_ids = [row.decision_id for row in payload.decisions if row.decision_id is not None]
    if (len(supplied_ids) != len(set(supplied_ids))
            or not set(supplied_ids).issubset(previous_by_id)):
        raise DraftError("SCENARIO_DECISION_ID_MISMATCH", 422)

    # The server, not the browser, owns source identity and allocation limits.
    # Legacy references with *no matching source at all* may remain editable
    # placeholders, but are explicitly needs_revalidation and never admitted.
    product_ids = {row.source_product_id for row in payload.decisions}
    products = {
        p.product_id: p
        for p in db.scalars(select(PensionProduct).where(
            PensionProduct.client_id == client_id,
            PensionProduct.product_id.in_(product_ids),
        ))
    } if product_ids else {}
    missing_ids = product_ids - set(products)
    if missing_ids:
        foreign_ids = set(db.scalars(select(PensionProduct.product_id).where(
            PensionProduct.product_id.in_(missing_ids)
        )).all())
        if foreign_ids:
            raise DraftError("SCENARIO_SOURCE_CLIENT_MISMATCH", 422)

    component_ids = {row.source_component_id for row in payload.decisions}
    components = {
        c.component_id: c
        for c in db.scalars(select(PensionProductComponent).where(
            PensionProductComponent.component_id.in_(component_ids)
        ))
    } if component_ids else {}
    amounts_by_source: dict[tuple[str, str], Decimal] = {}
    resolved: list[tuple] = []
    retained_election_ids: set[str] = set()

    for row in payload.decisions:
        product = products.get(row.source_product_id)
        component = components.get(row.source_component_id)
        if component is not None and (
            product is None or component.product_id != row.source_product_id
            or component.component_code != row.component_code
        ):
            raise DraftError("SCENARIO_SOURCE_COMPONENT_MISMATCH", 422)
        if component is None:
            # A missing canonical source is a *blocked* placeholder, not an
            # approval. It must never be represented as a valid allocation.
            digest = None
        else:
            digest = _source_digest(product, component)
            key = (product.product_id, component.component_id)
            amounts_by_source[key] = amounts_by_source.get(key, Decimal("0.00")) + row.amount
            if amounts_by_source[key] > component.balance:
                raise DraftError("SCENARIO_SOURCE_OVERALLOCATED", 422)

        previous = previous_by_id.get(row.decision_id) if row.decision_id else None
        unchanged = previous is not None and _materially_unchanged_decision(previous, row)
        # An unchanged stale source must NOT silently acquire a fresh
        # fingerprint simply because another decision was edited.
        if unchanged:
            fingerprint = previous.source_fingerprint_at_review
            version = previous.product_version_at_review
            stale = (digest is None or fingerprint is None
                     or digest != fingerprint or version != product.version
                     or previous.validation_state == "needs_revalidation")
        else:
            fingerprint = digest
            version = product.version if digest is not None else None
            stale = digest is None
        if (unchanged and not stale and row.action == "pension"):
            retained_election_ids.add(row.decision_id)
        resolved.append((row, product, component, fingerprint,
                         stale, version))

    # Existing selections are *not* financial authority, but must survive a
    # separate conversion being added to the scenario. After the version CAS,
    # retag only unchanged, still-current choices to the new draft version.
    # The immutable professional factor-admission ledger is NEVER retagged.
    elections = db.scalars(select(ScenarioDraftPensionElection).where(
        ScenarioDraftPensionElection.scenario_id == scenario_id
    )).all()
    submitted_by_id = {row.decision_id: row for row in payload.decisions
                       if row.decision_id is not None}
    retained_elections = []
    for election in elections:
        incoming = submitted_by_id.get(election.decision_id)
        if (election.scenario_version == payload.expected_version
                and election.decision_id in retained_election_ids
                and incoming is not None
                and election.pension_start_date >= incoming.effective_date):
            retained_elections.append({
                "election_id": election.election_id,
                "scenario_id": election.scenario_id,
                "decision_id": election.decision_id,
                "scenario_version": scenario.version,
                "pension_start_date": election.pension_start_date,
                "target_year": election.target_year,
                "survivors_option": election.survivors_option,
                "spouse_age_diff": election.spouse_age_diff,
                "coefficient_selection": election.coefficient_selection,
                "company_name": election.company_name,
                "option_name": election.option_name,
            })
        db.delete(election)

    # The restricted application role intentionally has SELECT, INSERT,
    # DELETE but *not UPDATE* on draft elections. Re-create only surviving
    # selections with the new draft version. No professional authority copies.
    # No partial persistence: this all executes within the caller transaction.
    for previous in existing:
        db.delete(previous)
    db.flush()
    for row, _product, _component, fingerprint, stale, version in resolved:
        db.add(ScenarioDraftDecision(
            decision_id=row.decision_id or uuid4().hex,
            scenario_id=scenario_id,
            source_product_id=row.source_product_id,
            source_component_id=row.source_component_id,
            component_code=row.component_code,
            amount=row.amount,
            action=row.action,
            effective_date=row.effective_date,
            validation_state="needs_revalidation" if stale else "unverified",
            product_version_at_review=version,
            source_fingerprint_at_review=fingerprint,
            # An old ruleset, permission preview or professional admission
            # can never be promoted by a draft replacement.
            ruleset_digest_at_review=None,
            permission_preview_id_at_review=None,
        ))
    db.flush()
    for attributes in retained_elections:
        db.add(ScenarioDraftPensionElection(**attributes))
    db.flush()
    old_choice_ids = {item.decision_id for item in elections}
    surviving_ids = {item["decision_id"] for item in retained_elections}
    return _revision(db, scenario, "replace", actor, audit_extra={
        "retained_pension_election_decision_ids": sorted(surviving_ids),
        "invalidated_pension_election_decision_ids": sorted(
            old_choice_ids - surviving_ids),
        "professional_admission_carryover": False,
    })


def rename(db: Session, client_id: int, scenario_id: str, name: str,
           expected: int, actor: str) -> dict:
    """Rename draft metadata without re-reviewing or replacing decisions.

    Source fingerprints and pension elections are version-bound evidence. A
    display-name edit is not a factual review and therefore may not refresh,
    delete, or otherwise rewrite that evidence.
    """
    scenario = _scenario(db, client_id, scenario_id)
    _cas(db, scenario, expected, actor, name=name)

    # Renaming is metadata-only: it must not erase a valid draft election.
    # Rebind its scenario revision using SELECT/DELETE/INSERT, since the app
    # role deliberately lacks UPDATE grants on pension-election rows.
    assessment = read(db, client_id, scenario_id)
    valid_decisions = {
        row["decision_id"]: row for row in assessment["decisions"]
        if row["action"] == "pension" and row["validation_state"] == "unverified"
    }
    previous = db.scalars(select(ScenarioDraftPensionElection).where(
        ScenarioDraftPensionElection.scenario_id == scenario_id
    )).all()
    preserved = []
    for election in previous:
        decision = valid_decisions.get(election.decision_id)
        if (election.scenario_version == expected and decision is not None
                and election.pension_start_date >= date.fromisoformat(
                    decision["effective_date"])):
            preserved.append({
                "election_id": election.election_id,
                "scenario_id": scenario_id,
                "decision_id": election.decision_id,
                "scenario_version": scenario.version,
                "pension_start_date": election.pension_start_date,
                "target_year": election.target_year,
                "survivors_option": election.survivors_option,
                "spouse_age_diff": election.spouse_age_diff,
                "coefficient_selection": election.coefficient_selection,
                "company_name": election.company_name,
                "option_name": election.option_name,
            })
        db.delete(election)
    db.flush()
    for values in preserved:
        db.add(ScenarioDraftPensionElection(**values))
    db.flush()
    surviving_ids = {item["decision_id"] for item in preserved}
    return _revision(db, scenario, "rename", actor, audit_extra={
        "retained_pension_election_decision_ids": sorted(surviving_ids),
        "invalidated_pension_election_decision_ids": sorted(
            {item.decision_id for item in previous} - surviving_ids),
        "professional_admission_carryover": False,
    })


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
