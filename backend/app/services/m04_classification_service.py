from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import json
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.models.client import Client
from app.models.m02_intake import M02IntakeRecord
from app.models.m04_classification import (
    M04_CATALOGUE_VERSION,
    M04_COMPONENT_INTERPRETATIONS,
    M04_COMPONENT_KINDS,
    M04_EMPLOYER_RELATED,
    M04_INTERPRETATIONS,
    M04_PRODUCT_FAMILIES,
    M04_WORKFLOW_ACTOR,
    M04ClassificationRevision,
    M04ClassificationSubject,
    M04ComponentDecision,
    authorize_m04_insert,
)
from app.schemas.m04_classification import (
    M04ComponentResponse,
    M04EligibilityResponse,
    M04OverrideRequest,
    M04ReasonRequest,
    M04RevisionResponse,
    M04RulePreviewResponse,
    M04TargetResponse,
    M04UndoRequest,
)
from app.services.m01_case_service import effective_lifecycle_status
from app.services.m03_review_service import (
    M03ReviewError,
    ensure_current_input_context,
    target_response as m03_target_response,
)
from app.services.m04_rule_catalogue import CATALOGUE, evaluate_exact_catalogue


REVISION_ID_PATTERN = re.compile(r"^M04-R-[0-9a-f]{32}$")
RULES_BY_ID = {rule.rule_id: rule.evidence() for rule in CATALOGUE}


class M04ClassificationError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


@dataclass(frozen=True)
class M04Context:
    client: Client
    intake: M02IntakeRecord
    target_kind: str
    source_id: str | None
    m03: Any
    subject: M04ClassificationSubject | None


def _not_found() -> M04ClassificationError:
    return M04ClassificationError(404, "M04_RESOURCE_NOT_FOUND", "Resource not found")


def _json_value(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _component_source_snapshot(
    values: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for index, raw in enumerate(values or []):
        if not isinstance(raw, dict):
            continue
        label = next(
            (
                str(raw[key])
                for key in ("label", "component_label", "name")
                if raw.get(key) is not None
            ),
            None,
        )
        code = next(
            (
                str(raw[key])
                for key in ("code", "component_code")
                if raw.get(key) is not None
            ),
            None,
        )
        identity_seed = f"{index}|{code or ''}|{label or ''}"
        identity = (
            f"component:{index}:"
            f"{hashlib.sha256(identity_seed.encode('utf-8')).hexdigest()[:16]}"
        )
        employer = raw.get("current_employer_related", "unknown")
        if employer not in M04_EMPLOYER_RELATED:
            employer = "unknown"
        result.append(
            {
                "evidence_identity": identity,
                "original_label": label,
                "original_code": code,
                "declared_value": _json_value(
                    raw.get("value", raw.get("amount"))
                ),
                "current_employer_related": employer,
            }
        )
    return result


def _context(db: Session, client_id: int, intake_id: str) -> M04Context:
    client = db.scalar(select(Client).where(Client.client_id == client_id))
    if client is None:
        raise _not_found()
    intake = db.scalar(
        select(M02IntakeRecord).where(
            M02IntakeRecord.client_id == client_id,
            M02IntakeRecord.intake_id == intake_id,
        )
    )
    if intake is None:
        raise _not_found()
    try:
        m03 = m03_target_response(db, client_id, intake_id)
    except M03ReviewError as error:
        if error.status_code == 404:
            raise _not_found() from error
        raise M04ClassificationError(
            409, "M04_M03_PREDECESSOR_INVALID", "M03 predecessor is invalid"
        ) from error
    subject = db.scalar(
        select(M04ClassificationSubject).where(
            M04ClassificationSubject.client_id == client_id,
            M04ClassificationSubject.intake_id == intake_id,
            M04ClassificationSubject.target_kind == m03.target_kind,
        )
    )
    return M04Context(
        client=client,
        intake=intake,
        target_kind=m03.target_kind,
        source_id=m03.source_id,
        m03=m03,
        subject=subject,
    )


def _require_active(context: M04Context) -> None:
    if effective_lifecycle_status(context.client.status) == "archived":
        raise M04ClassificationError(
            409, "M04_ARCHIVED_CASE_READ_ONLY", "Archived client cases are read-only"
        )


def _require_m03_eligible(context: M04Context) -> None:
    if not context.m03.eligible or not context.m03.accepted_revision_id:
        raise M04ClassificationError(
            409,
            "M04_M03_INELIGIBLE",
            "The target is not currently eligible under M03",
        )


def _snapshot(context: M04Context, *, archive_generation: int) -> dict[str, Any]:
    return {
        "schema_version": "m04-input-v1",
        "client_id": context.client.client_id,
        "intake_id": context.intake.intake_id,
        "target_kind": context.target_kind,
        "source_id": context.source_id,
        "accepted_m03_revision_id": context.m03.accepted_revision_id,
        "m03_evaluated_at": datetime.now(timezone.utc).isoformat(),
        "m03_lifecycle_status": (
            context.m03.current_revision.state
            if context.m03.current_revision is not None
            else None
        ),
        "m03_eligibility_basis": (
            "current_accepted_review"
            if context.m03.eligible
            else context.m03.exclusion_reason
        ),
        "m02_lifecycle_status": context.intake.lifecycle_status,
        "archive_generation": archive_generation,
        "declared_provider_name": context.intake.declared_provider_name,
        "product_name": context.intake.product_name,
        "declared_product_type": context.intake.declared_product_type,
        "product_identifier": context.intake.product_identifier,
        "declared_account_reference": context.intake.declared_account_reference,
        "declared_statement_date": _json_value(
            context.intake.declared_statement_date
        ),
        "components": _component_source_snapshot(
            context.intake.declared_component_values
        ),
        "provenance": {
            "intake_id": context.intake.intake_id,
            "source_id": context.source_id,
            "record_kind": context.intake.record_kind,
        },
    }


def _history(
    db: Session, subject: M04ClassificationSubject | None
) -> list[M04ClassificationRevision]:
    if subject is None:
        return []
    return list(
        db.scalars(
            select(M04ClassificationRevision)
            .where(M04ClassificationRevision.subject_id == subject.subject_id)
            .order_by(M04ClassificationRevision.revision_sequence)
        ).all()
    )


def _components(
    db: Session, revision_id: str
) -> list[M04ComponentDecision]:
    return list(
        db.scalars(
            select(M04ComponentDecision)
            .where(M04ComponentDecision.revision_id == revision_id)
            .order_by(M04ComponentDecision.evidence_identity)
        ).all()
    )


def _component_data(row: M04ComponentDecision) -> dict[str, Any]:
    return {
        "evidence_identity": row.evidence_identity,
        "original_label": row.original_label,
        "original_code": row.original_code,
        "component_kind": row.component_kind,
        "interpretation": row.interpretation,
        "matched_rule_evidence": row.matched_rule_evidence,
        "explanation": row.explanation,
        "current_employer_related": row.current_employer_related,
    }


def _digest_data(
    *,
    subject_id: str,
    client_id: int,
    intake_id: str,
    target_kind: str,
    source_id: str | None,
    m03_revision_id: str,
    predecessor_revision_id: str | None,
    revision_sequence: int,
    state: str,
    action_type: str,
    product_family: str | None,
    pension_subtype: str | None,
    aggregate_interpretation: str | None,
    explanation: str | None,
    reason_code: str | None,
    reason: str | None,
    input_snapshot: dict[str, Any],
    catalogue_version: str,
    matched_rule_evidence: list[dict[str, Any]],
    match_basis: str,
    action_evidence: dict[str, Any],
    historical_revision_id: str | None,
    components: list[dict[str, Any]],
) -> str:
    payload = {
        "subject_id": subject_id,
        "client_id": client_id,
        "intake_id": intake_id,
        "target_kind": target_kind,
        "source_id": source_id,
        "m03_revision_id": m03_revision_id,
        "predecessor_revision_id": predecessor_revision_id,
        "revision_sequence": revision_sequence,
        "state": state,
        "action_type": action_type,
        "product_family": product_family,
        "pension_subtype": pension_subtype,
        "aggregate_interpretation": aggregate_interpretation,
        "explanation": explanation,
        "reason_code": reason_code,
        "reason": reason,
        "input_snapshot": input_snapshot,
        "catalogue_version": catalogue_version,
        "matched_rule_evidence": matched_rule_evidence,
        "match_basis": match_basis,
        "action_evidence": action_evidence,
        "historical_revision_id": historical_revision_id,
        "components": sorted(components, key=lambda item: item["evidence_identity"]),
    }
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _row_digest(
    row: M04ClassificationRevision, components: list[M04ComponentDecision]
) -> str:
    return _digest_data(
        subject_id=row.subject_id,
        client_id=row.client_id,
        intake_id=row.intake_id,
        target_kind=row.target_kind,
        source_id=row.source_id,
        m03_revision_id=row.m03_revision_id,
        predecessor_revision_id=row.predecessor_revision_id,
        revision_sequence=row.revision_sequence,
        state=row.state,
        action_type=row.action_type,
        product_family=row.product_family,
        pension_subtype=row.pension_subtype,
        aggregate_interpretation=row.aggregate_interpretation,
        explanation=row.explanation,
        reason_code=row.reason_code,
        reason=row.reason,
        input_snapshot=row.input_snapshot,
        catalogue_version=row.catalogue_version,
        matched_rule_evidence=row.matched_rule_evidence,
        match_basis=row.match_basis,
        action_evidence=row.action_evidence,
        historical_revision_id=row.historical_revision_id,
        components=[_component_data(component) for component in components],
    )


def _valid_rule_evidence(evidence: list[dict[str, Any]]) -> bool:
    if not isinstance(evidence, list):
        return False
    for row in evidence:
        if not isinstance(row, dict):
            return False
        expected = RULES_BY_ID.get(row.get("rule_id"))
        if expected is None or row != expected:
            return False
    return True


def _transition_is_valid(
    previous: M04ClassificationRevision | None,
    current: M04ClassificationRevision,
) -> bool:
    if previous is None:
        return (
            current.action_type == "start"
            and current.state == "under_review"
            and current.revision_sequence == 1
            and current.predecessor_revision_id is None
        )
    allowed = {
        "proposal": ({"under_review"}, "proposed"),
        "unresolved": ({"under_review"}, "unresolved"),
        "accept": ({"proposed"}, "accepted"),
        "reject": ({"proposed"}, "rejected"),
        "reopen": ({"accepted", "unresolved", "rejected"}, "under_review"),
        "override": (
            {"proposed", "accepted", "unresolved", "rejected"},
            "proposed",
        ),
        "undo": (
            {"proposed", "accepted", "unresolved", "rejected"},
            "proposed",
        ),
        "start_revalidation": (
            {"under_review", "proposed", "accepted", "unresolved", "rejected"},
            "under_review",
        ),
    }
    rule = allowed.get(current.action_type)
    return (
        rule is not None
        and previous.state in rule[0]
        and current.state == rule[1]
        and current.revision_sequence == previous.revision_sequence + 1
        and current.predecessor_revision_id == previous.revision_id
    )


def _validated_snapshot_component_map(
    snapshot: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    raw_components = snapshot.get("components")
    if not isinstance(raw_components, list):
        raise M04ClassificationError(
            409,
            "M04_CLASSIFICATION_CHAIN_INCONSISTENT",
            "Classification snapshot components must be a structured list",
        )
    component_map: dict[str, dict[str, Any]] = {}
    for item in raw_components:
        if not isinstance(item, dict):
            raise M04ClassificationError(
                409,
                "M04_CLASSIFICATION_CHAIN_INCONSISTENT",
                "Classification snapshot component is malformed",
            )
        identity = item.get("evidence_identity")
        if (
            not isinstance(identity, str)
            or not identity.strip()
            or identity in component_map
        ):
            raise M04ClassificationError(
                409,
                "M04_CLASSIFICATION_CHAIN_INCONSISTENT",
                "Classification snapshot component identity is invalid or duplicated",
            )
        component_map[identity] = item
    return component_map


def _validated_history(
    db: Session, context: M04Context
) -> tuple[list[M04ClassificationRevision], dict[str, list[M04ComponentDecision]]]:
    rows = _history(db, context.subject)
    component_map: dict[str, list[M04ComponentDecision]] = {}
    previous: M04ClassificationRevision | None = None
    for row in rows:
        components = _components(db, row.revision_id)
        component_map[row.revision_id] = components
        snapshot = row.input_snapshot
        snapshot_components = (
            _validated_snapshot_component_map(snapshot)
            if isinstance(snapshot, dict)
            else {}
        )
        created_at = row.created_at
        previous_created_at = previous.created_at if previous else None
        if (
            REVISION_ID_PATTERN.fullmatch(row.revision_id) is None
            or context.subject is None
            or row.subject_id != context.subject.subject_id
            or row.client_id != context.client.client_id
            or row.intake_id != context.intake.intake_id
            or row.target_kind != context.target_kind
            or row.source_id != context.source_id
            or row.actor != M04_WORKFLOW_ACTOR
            or row.catalogue_version != M04_CATALOGUE_VERSION
            or not _transition_is_valid(previous, row)
            or not isinstance(snapshot, dict)
            or snapshot.get("client_id") != row.client_id
            or snapshot.get("intake_id") != row.intake_id
            or snapshot.get("target_kind") != row.target_kind
            or snapshot.get("source_id") != row.source_id
            or snapshot.get("accepted_m03_revision_id") != row.m03_revision_id
            or snapshot.get("archive_generation") is None
            or not _valid_rule_evidence(row.matched_rule_evidence)
            or not isinstance(row.action_evidence, dict)
            or (previous_created_at is not None and created_at < previous_created_at)
            or _row_digest(row, components) != row.evidence_digest
        ):
            raise M04ClassificationError(
                409,
                "M04_CLASSIFICATION_CHAIN_INCONSISTENT",
                "Classification chain is inconsistent",
            )
        persisted_identities = [component.evidence_identity for component in components]
        if row.state != "under_review" and (
            len(persisted_identities) != len(set(persisted_identities))
            or set(persisted_identities) != set(snapshot_components)
        ):
            raise M04ClassificationError(
                409,
                "M04_CLASSIFICATION_CHAIN_INCONSISTENT",
                "Classification snapshot identities do not match persisted components",
            )
        seen: set[str] = set()
        for component in components:
            source_component = snapshot_components.get(component.evidence_identity)
            if (
                component.evidence_identity in seen
                or component.client_id != row.client_id
                or component.intake_id != row.intake_id
                or component.target_kind != row.target_kind
                or source_component is None
                or component.original_label != source_component.get("original_label")
                or component.original_code != source_component.get("original_code")
                or component.component_kind not in M04_COMPONENT_KINDS
                or component.interpretation not in M04_COMPONENT_INTERPRETATIONS
                or component.current_employer_related
                != source_component.get("current_employer_related", "unknown")
                or not _valid_rule_evidence(component.matched_rule_evidence)
            ):
                raise M04ClassificationError(
                    409,
                    "M04_COMPONENT_EVIDENCE_INCONSISTENT",
                    "Component evidence is inconsistent",
                )
            seen.add(component.evidence_identity)
        if row.state == "under_review":
            aggregate_is_consistent = (
                row.aggregate_interpretation is None and not components
            )
        else:
            aggregate_is_consistent = (
                seen == set(snapshot_components)
                and row.aggregate_interpretation
                == _aggregate(
                    [
                        {"interpretation": component.interpretation}
                        for component in components
                    ]
                )
            )
        if not aggregate_is_consistent:
            raise M04ClassificationError(
                409,
                "M04_CLASSIFICATION_CHAIN_INCONSISTENT",
                "Classification aggregate is inconsistent with its components",
            )
        previous = row
    return rows, component_map


def _integrity_exclusion_reason(db: Session, context: M04Context) -> str:
    """Return the narrowest stable fail-closed reason visible to this client."""
    for row in _history(db, context.subject):
        snapshot = row.input_snapshot
        if (
            row.catalogue_version != M04_CATALOGUE_VERSION
            or not _valid_rule_evidence(row.matched_rule_evidence)
        ):
            return "invalid_rule_evidence"
        if (
            context.subject is None
            or row.subject_id != context.subject.subject_id
            or row.client_id != context.client.client_id
            or row.intake_id != context.intake.intake_id
            or row.target_kind != context.target_kind
            or row.source_id != context.source_id
            or not isinstance(snapshot, dict)
            or snapshot.get("client_id") != row.client_id
            or snapshot.get("intake_id") != row.intake_id
            or snapshot.get("target_kind") != row.target_kind
            or snapshot.get("source_id") != row.source_id
        ):
            return "foreign_or_inconsistent_provenance"
        for component in _components(db, row.revision_id):
            if not _valid_rule_evidence(component.matched_rule_evidence):
                return "invalid_rule_evidence"
            if (
                component.client_id != row.client_id
                or component.intake_id != row.intake_id
                or component.target_kind != row.target_kind
            ):
                return "foreign_or_inconsistent_provenance"
    return "malformed_classification_chain"


def _revalidation_required(
    context: M04Context,
    rows: list[M04ClassificationRevision],
) -> bool:
    subject = context.subject
    leaf = rows[-1] if rows else None
    if subject is None or leaf is None:
        return False
    current_m03_revision_id = context.m03.accepted_revision_id
    upstream_authority_changed = bool(
        context.m03.eligible
        and current_m03_revision_id
        and leaf.m03_revision_id != current_m03_revision_id
    )
    archive_revalidation_required = subject.archive_generation > 0
    if not upstream_authority_changed and not archive_revalidation_required:
        return False
    revalidation = next(
        (
            row
            for row in reversed(rows)
            if row.action_type == "start_revalidation"
            and row.input_snapshot.get("archive_generation")
            == subject.archive_generation
            and row.m03_revision_id == current_m03_revision_id
        ),
        None,
    )
    return (
        revalidation is None
        or leaf.state != "accepted"
        or leaf.revision_sequence <= revalidation.revision_sequence
    )


def _current_revalidation_started(
    context: M04Context,
    rows: list[M04ClassificationRevision],
) -> bool:
    subject = context.subject
    if subject is None:
        return False
    return any(
        row.action_type == "start_revalidation"
        and row.input_snapshot.get("archive_generation")
        == subject.archive_generation
        and row.m03_revision_id == context.m03.accepted_revision_id
        for row in rows
    )


def _aggregate(component_rows: list[dict[str, Any]]) -> str:
    if not component_rows:
        return "unresolved"
    interpretations = {row["interpretation"] for row in component_rows}
    if "unresolved" in interpretations:
        return "unresolved"
    if interpretations == {"pension", "capital"}:
        return "mixed"
    if len(interpretations) == 1:
        return next(iter(interpretations))
    return "unresolved"


def _decision_values(
    row: M04ClassificationRevision | None,
    components: list[M04ComponentDecision],
) -> dict[str, Any]:
    if row is None:
        return {}
    return {
        "product_family": row.product_family,
        "pension_subtype": row.pension_subtype,
        "aggregate_interpretation": row.aggregate_interpretation,
        "components": [_component_data(component) for component in components],
    }


def _append(
    db: Session,
    context: M04Context,
    subject: M04ClassificationSubject,
    *,
    previous: M04ClassificationRevision | None,
    state: str,
    action_type: str,
    snapshot: dict[str, Any],
    product_family: str | None = None,
    pension_subtype: str | None = None,
    aggregate_interpretation: str | None = None,
    explanation: str | None = None,
    reason_code: str | None = None,
    reason: str | None = None,
    matched_rule_evidence: list[dict[str, Any]] | None = None,
    match_basis: str = "workflow",
    action_evidence: dict[str, Any] | None = None,
    historical_revision_id: str | None = None,
    components: list[dict[str, Any]] | None = None,
) -> M04ClassificationRevision:
    component_rows = components or []
    sequence = 1 if previous is None else previous.revision_sequence + 1
    evidence = matched_rule_evidence or []
    action_details = action_evidence or {}
    digest = _digest_data(
        subject_id=subject.subject_id,
        client_id=context.client.client_id,
        intake_id=context.intake.intake_id,
        target_kind=context.target_kind,
        source_id=context.source_id,
        m03_revision_id=snapshot["accepted_m03_revision_id"],
        predecessor_revision_id=previous.revision_id if previous else None,
        revision_sequence=sequence,
        state=state,
        action_type=action_type,
        product_family=product_family,
        pension_subtype=pension_subtype,
        aggregate_interpretation=aggregate_interpretation,
        explanation=explanation,
        reason_code=reason_code,
        reason=reason,
        input_snapshot=snapshot,
        catalogue_version=M04_CATALOGUE_VERSION,
        matched_rule_evidence=evidence,
        match_basis=match_basis,
        action_evidence=action_details,
        historical_revision_id=historical_revision_id,
        components=component_rows,
    )
    row = M04ClassificationRevision(
        subject_id=subject.subject_id,
        client_id=context.client.client_id,
        intake_id=context.intake.intake_id,
        target_kind=context.target_kind,
        source_id=context.source_id,
        m03_revision_id=snapshot["accepted_m03_revision_id"],
        predecessor_revision_id=previous.revision_id if previous else None,
        revision_sequence=sequence,
        state=state,
        action_type=action_type,
        product_family=product_family,
        pension_subtype=pension_subtype,
        aggregate_interpretation=aggregate_interpretation,
        explanation=explanation,
        reason_code=reason_code,
        reason=reason,
        input_snapshot=snapshot,
        catalogue_version=M04_CATALOGUE_VERSION,
        matched_rule_evidence=evidence,
        match_basis=match_basis,
        action_evidence=action_details,
        evidence_digest=digest,
        historical_revision_id=historical_revision_id,
        actor=M04_WORKFLOW_ACTOR,
    )
    authorize_m04_insert(row)
    db.add(row)
    try:
        db.flush()
        for component in component_rows:
            component_row = M04ComponentDecision(
                revision_id=row.revision_id,
                client_id=row.client_id,
                intake_id=row.intake_id,
                target_kind=row.target_kind,
                evidence_identity=component["evidence_identity"],
                original_label=component.get("original_label"),
                original_code=component.get("original_code"),
                component_kind=component["component_kind"],
                interpretation=component["interpretation"],
                matched_rule_evidence=component.get("matched_rule_evidence", []),
                explanation=component["explanation"],
                current_employer_related=component.get(
                    "current_employer_related", "unknown"
                ),
            )
            authorize_m04_insert(component_row)
            db.add(component_row)
        db.commit()
    except (IntegrityError, OperationalError, ValueError) as error:
        db.rollback()
        raise M04ClassificationError(
            409,
            "M04_CONCURRENT_LEAF_CONFLICT",
            "Classification changed concurrently or violates append-only integrity",
        ) from error
    db.refresh(row)
    return row


def _current(
    db: Session, context: M04Context
) -> tuple[
    list[M04ClassificationRevision],
    dict[str, list[M04ComponentDecision]],
    M04ClassificationRevision | None,
]:
    rows, component_map = _validated_history(db, context)
    return rows, component_map, rows[-1] if rows else None


def _expect(
    leaf: M04ClassificationRevision | None,
    expected_revision_id: str,
) -> M04ClassificationRevision:
    if leaf is None:
        raise M04ClassificationError(
            409, "M04_CLASSIFICATION_NOT_STARTED", "Classification has not started"
        )
    if leaf.revision_id != expected_revision_id:
        raise M04ClassificationError(
            409,
            "M04_STALE_CURRENT_REVISION",
            "Classification changed before this action",
        )
    return leaf


def _component_response(row: M04ComponentDecision) -> M04ComponentResponse:
    return M04ComponentResponse(
        component_decision_id=row.component_decision_id,
        evidence_identity=row.evidence_identity,
        original_label=row.original_label,
        original_code=row.original_code,
        component_kind=row.component_kind,
        interpretation=row.interpretation,
        matched_rule_evidence=row.matched_rule_evidence,
        explanation=row.explanation,
        current_employer_related=row.current_employer_related,
    )


def revision_response(
    db: Session, row: M04ClassificationRevision
) -> M04RevisionResponse:
    return M04RevisionResponse(
        revision_id=row.revision_id,
        revision_sequence=row.revision_sequence,
        predecessor_revision_id=row.predecessor_revision_id,
        historical_revision_id=row.historical_revision_id,
        state=row.state,
        action_type=row.action_type,
        product_family=row.product_family,
        pension_subtype=row.pension_subtype,
        aggregate_interpretation=row.aggregate_interpretation,
        explanation=row.explanation,
        reason_code=row.reason_code,
        reason=row.reason,
        catalogue_version=row.catalogue_version,
        matched_rule_evidence=row.matched_rule_evidence,
        match_basis=row.match_basis,
        action_evidence=row.action_evidence,
        input_snapshot=row.input_snapshot,
        actor=row.actor,
        created_at=row.created_at,
        components=[_component_response(item) for item in _components(db, row.revision_id)],
    )


def _catalogue_result_is_m05_complete(result: dict[str, Any]) -> bool:
    components = result.get("components")
    return bool(
        not result.get("conflicts")
        and result.get("matched_rule_evidence")
        and result.get("product_family") not in {None, "unknown_or_unresolved"}
        and isinstance(components, list)
        and components
        and all(
            item.get("component_kind") != "unknown_component"
            for item in components
        )
    )


def _materialize_catalogue_result(
    db: Session,
    context: M04Context,
    leaf: M04ClassificationRevision,
) -> M04ClassificationRevision:
    result = evaluate_exact_catalogue(
        _snapshot(context, archive_generation=context.subject.archive_generation)
    )
    if not _catalogue_result_is_m05_complete(result):
        return mark_unresolved(
            db,
            context.client.client_id,
            context.intake.intake_id,
            M04ReasonRequest(
                expected_current_revision_id=leaf.revision_id,
                reason_code="professional_classification_required",
                explanation="A specific professional classification decision is required.",
            ),
        )
    proposal = create_proposal(
        db, context.client.client_id, context.intake.intake_id, leaf.revision_id
    )
    return _append(
        db,
        context,
        context.subject,
        previous=proposal,
        state="accepted",
        action_type="accept",
        snapshot=proposal.input_snapshot,
        product_family=proposal.product_family,
        aggregate_interpretation=proposal.aggregate_interpretation,
        explanation="Deterministic rules resolved every classification axis required by M05.",
        reason_code="deterministic_m05_classification",
        reason="No planner authority review is required for M05 material axes.",
        matched_rule_evidence=proposal.matched_rule_evidence,
        match_basis=proposal.match_basis,
        action_evidence={
            "proposal_revision_id": proposal.revision_id,
            "m05_material_axes": ["product_family", "component_kind"],
            "non_material_axes_may_remain_unresolved": True,
        },
        components=[item for item in result["components"]],
    )


def ensure_current_classification(
    db: Session, client_id: int, intake_id: str
) -> M04ClassificationRevision | None:
    """Lazily materialize current classification without authority ceremony."""
    context = _context(db, client_id, intake_id)
    if (
        context.intake.lifecycle_status != "accepted_for_review"
        or effective_lifecycle_status(context.client.status) == "archived"
    ):
        rows, _, leaf = _current(db, context)
        _ = rows
        return leaf

    ensure_current_input_context(db, client_id, intake_id)
    context = _context(db, client_id, intake_id)
    _require_m03_eligible(context)
    if context.subject is None:
        start_classification(db, client_id, intake_id)
        context = _context(db, client_id, intake_id)

    rows, component_map, leaf = _current(db, context)
    assert context.subject is not None and leaf is not None
    current_anchor = context.m03.accepted_revision_id
    current_generation = context.subject.archive_generation
    bound_to_current = (
        leaf.m03_revision_id == current_anchor
        and leaf.input_snapshot.get("archive_generation") == current_generation
    )
    if not bound_to_current:
        leaf = _append(
            db,
            context,
            context.subject,
            previous=leaf,
            state="under_review",
            action_type="start_revalidation",
            snapshot=_snapshot(context, archive_generation=current_generation),
            explanation="Current user-provided input changed; classification was recomputed.",
            reason_code="upstream_input_changed",
            reason="Current user-provided input changed.",
            match_basis="system_stale_recomputation",
            action_evidence={
                "historical_revision_id": leaf.revision_id,
                "historical_values_are_authority": False,
            },
            historical_revision_id=leaf.revision_id,
        )
        context = _context(db, client_id, intake_id)
        return _materialize_catalogue_result(db, context, leaf)

    if leaf.state == "accepted" or leaf.state == "unresolved":
        return leaf
    if leaf.state == "proposed":
        if leaf.match_basis == "exact_rule_catalogue":
            result = {
                "conflicts": leaf.action_evidence.get("conflicts", []),
                "matched_rule_evidence": leaf.matched_rule_evidence,
                "product_family": leaf.product_family,
                "components": [
                    _component_data(item)
                    for item in component_map.get(leaf.revision_id, [])
                ],
            }
            if _catalogue_result_is_m05_complete(result):
                return _append(
                    db,
                    context,
                    context.subject,
                    previous=leaf,
                    state="accepted",
                    action_type="accept",
                    snapshot=leaf.input_snapshot,
                    product_family=leaf.product_family,
                    aggregate_interpretation=leaf.aggregate_interpretation,
                    explanation="Deterministic rules resolved every classification axis required by M05.",
                    reason_code="deterministic_m05_classification",
                    reason="No planner authority review is required for M05 material axes.",
                    matched_rule_evidence=leaf.matched_rule_evidence,
                    match_basis=leaf.match_basis,
                    action_evidence={
                        "proposal_revision_id": leaf.revision_id,
                        "m05_material_axes": ["product_family", "component_kind"],
                        "non_material_axes_may_remain_unresolved": True,
                    },
                    components=result["components"],
                )
        return leaf
    if leaf.state == "rejected" and leaf.match_basis == "exact_rule_catalogue":
        leaf = reopen_classification(
            db,
            client_id,
            intake_id,
            M04ReasonRequest(
                expected_current_revision_id=leaf.revision_id,
                reason_code="simplified_current_classification",
                explanation="Recompute current professional classification under the simplified workflow.",
            ),
        )
        context = _context(db, client_id, intake_id)
    if leaf.state == "under_review":
        return _materialize_catalogue_result(db, context, leaf)
    return leaf


def eligibility(
    db: Session, client_id: int, intake_id: str
) -> M04EligibilityResponse:
    context = _context(db, client_id, intake_id)
    try:
        rows, component_map = _validated_history(db, context)
    except M04ClassificationError:
        return M04EligibilityResponse(
            eligible_for_m05=False,
            exclusion_reason=_integrity_exclusion_reason(db, context),
            current_revision_id=None,
            accepted_revision_id=None,
            m03_revision_id=context.m03.accepted_revision_id,
        )
    leaf = rows[-1] if rows else None
    current_id = leaf.revision_id if leaf else None
    if effective_lifecycle_status(context.client.status) == "archived":
        reason = "archived_case"
    elif not rows:
        reason = "no_classification"
    elif _revalidation_required(context, rows):
        reason = "m04_revalidation_required"
    elif not context.m03.eligible:
        reason = (
            "target_superseded_or_rejected"
            if context.intake.lifecycle_status in {"superseded", "rejected"}
            else "m03_ineligible"
        )
    elif leaf is None:
        reason = "no_classification"
    elif leaf.m03_revision_id != context.m03.accepted_revision_id:
        reason = "m03_ineligible"
    elif leaf.state == "under_review":
        reason = "classification_under_review"
    elif leaf.state == "proposed":
        reason = "classification_proposed"
    elif leaf.state == "unresolved":
        unresolved_reasons = (
            leaf.action_evidence.get("unresolved_reasons", [])
            if isinstance(leaf.action_evidence, dict)
            else []
        )
        reason = (
            "opaque_uploaded_facts_unavailable"
            if "opaque_uploaded_facts_unavailable" in unresolved_reasons
            else "classification_unresolved"
        )
    elif leaf.state == "rejected":
        reason = "classification_rejected"
    elif leaf.state != "accepted":
        reason = "malformed_classification_chain"
    elif leaf.catalogue_version != M04_CATALOGUE_VERSION:
        reason = "invalid_rule_evidence"
    elif leaf.product_family in (None, "unknown_or_unresolved"):
        reason = "classification_unresolved"
    else:
        components = component_map.get(leaf.revision_id, [])
        if not components or any(
            component.component_kind == "unknown_component"
            for component in components
        ):
            reason = "unresolved_required_component"
        else:
            reason = None
    return M04EligibilityResponse(
        eligible_for_m05=reason is None,
        exclusion_reason=reason,
        current_revision_id=current_id,
        accepted_revision_id=leaf.revision_id if reason is None and leaf else None,
        m03_revision_id=context.m03.accepted_revision_id,
    )


def target_response(
    db: Session, client_id: int, intake_id: str
) -> M04TargetResponse:
    context = _context(db, client_id, intake_id)
    rows, _, leaf = _current(db, context)
    _ = rows
    return M04TargetResponse(
        client_id=client_id,
        intake_id=intake_id,
        target_kind=context.target_kind,
        record_kind=context.intake.record_kind,
        m01_lifecycle_status=effective_lifecycle_status(context.client.status),
        m02_lifecycle_status=context.intake.lifecycle_status,
        m03_eligible=context.m03.eligible,
        m03_exclusion_reason=context.m03.exclusion_reason,
        m03_accepted_revision_id=context.m03.accepted_revision_id,
        source_id=context.source_id,
        declared_provider_name=context.intake.declared_provider_name,
        product_name=context.intake.product_name,
        declared_product_type=context.intake.declared_product_type,
        product_identifier=context.intake.product_identifier,
        declared_account_reference=context.intake.declared_account_reference,
        declared_component_values=_json_value(
            context.intake.declared_component_values or []
        ),
        current_revision=revision_response(db, leaf) if leaf else None,
        eligibility=eligibility(db, client_id, intake_id),
    )


def list_targets(db: Session, client_id: int) -> list[M04TargetResponse]:
    client = db.scalar(select(Client).where(Client.client_id == client_id))
    if client is None:
        raise _not_found()
    intakes = db.scalars(
        select(M02IntakeRecord)
        .where(M02IntakeRecord.client_id == client_id)
        .order_by(M02IntakeRecord.created_at, M02IntakeRecord.intake_id)
    ).all()
    result: list[M04TargetResponse] = []
    for intake in intakes:
        response = target_response(db, client_id, intake.intake_id)
        has_history = response.current_revision is not None
        if response.m03_eligible or has_history:
            result.append(response)
    return result


def revision_history(
    db: Session, client_id: int, intake_id: str
) -> list[M04RevisionResponse]:
    context = _context(db, client_id, intake_id)
    rows, _ = _validated_history(db, context)
    return [revision_response(db, row) for row in rows]


def matched_rule_evidence(
    db: Session, client_id: int, intake_id: str
) -> list[dict[str, Any]]:
    context = _context(db, client_id, intake_id)
    rows, _ = _validated_history(db, context)
    return rows[-1].matched_rule_evidence if rows else []


def preview_rules(
    db: Session, client_id: int, intake_id: str
) -> M04RulePreviewResponse:
    context = _context(db, client_id, intake_id)
    _require_active(context)
    generation = context.subject.archive_generation if context.subject else 0
    result = evaluate_exact_catalogue(
        _snapshot(context, archive_generation=generation)
    )
    return M04RulePreviewResponse(
        catalogue_version=M04_CATALOGUE_VERSION,
        product_family=result["product_family"],
        aggregate_interpretation=result["aggregate_interpretation"],
        components=[
            M04ComponentResponse(
                component_decision_id=f"preview:{item['evidence_identity']}",
                **item,
            )
            for item in result["components"]
        ],
        matched_rule_evidence=result["matched_rule_evidence"],
        conflicts=result["conflicts"],
        unresolved_reasons=result["unresolved_reasons"],
    )


def start_classification(
    db: Session, client_id: int, intake_id: str
) -> M04ClassificationRevision:
    context = _context(db, client_id, intake_id)
    _require_active(context)
    _require_m03_eligible(context)
    if context.subject is not None:
        raise M04ClassificationError(
            409, "M04_CLASSIFICATION_ALREADY_STARTED", "Classification already exists"
        )
    subject = M04ClassificationSubject(
        client_id=client_id,
        intake_id=intake_id,
        target_kind=context.target_kind,
    )
    authorize_m04_insert(subject)
    db.add(subject)
    try:
        db.flush()
        context = M04Context(
            client=context.client,
            intake=context.intake,
            target_kind=context.target_kind,
            source_id=context.source_id,
            m03=context.m03,
            subject=subject,
        )
        return _append(
            db,
            context,
            subject,
            previous=None,
            state="under_review",
            action_type="start",
            snapshot=_snapshot(context, archive_generation=0),
            match_basis="explicit_start",
        )
    except M04ClassificationError:
        raise
    except (IntegrityError, OperationalError, ValueError) as error:
        db.rollback()
        raise M04ClassificationError(
            409, "M04_CONCURRENT_LEAF_CONFLICT", "Classification started concurrently"
        ) from error


def _mutation_context(
    db: Session, client_id: int, intake_id: str
) -> tuple[
    M04Context,
    list[M04ClassificationRevision],
    dict[str, list[M04ComponentDecision]],
    M04ClassificationRevision,
]:
    context = _context(db, client_id, intake_id)
    _require_active(context)
    _require_m03_eligible(context)
    rows, component_map, leaf = _current(db, context)
    if leaf is None or context.subject is None:
        raise M04ClassificationError(
            409, "M04_CLASSIFICATION_NOT_STARTED", "Classification has not started"
        )
    return context, rows, component_map, leaf


def create_proposal(
    db: Session, client_id: int, intake_id: str, expected: str
) -> M04ClassificationRevision:
    context, rows, _, leaf = _mutation_context(db, client_id, intake_id)
    _expect(leaf, expected)
    if _revalidation_required(context, rows) and not _current_revalidation_started(
        context, rows
    ):
        raise M04ClassificationError(
            409, "M04_REVALIDATION_REQUIRED", "Revalidation is required"
        )
    if leaf.state != "under_review":
        raise M04ClassificationError(
            409, "M04_INVALID_TRANSITION", "Proposal requires under_review"
        )
    snapshot = _snapshot(
        context, archive_generation=context.subject.archive_generation
    )
    result = evaluate_exact_catalogue(snapshot)
    if result["conflicts"]:
        raise M04ClassificationError(
            409, "M04_EXACT_MAPPING_CONFLICT", "Exact rules conflict"
        )
    if not result["matched_rule_evidence"]:
        raise M04ClassificationError(
            409, "M04_NO_EXACT_MAPPING", "No approved exact rule matched"
        )
    return _append(
        db,
        context,
        context.subject,
        previous=leaf,
        state="proposed",
        action_type="proposal",
        snapshot=snapshot,
        product_family=result["product_family"],
        aggregate_interpretation=result["aggregate_interpretation"],
        explanation="Server exact-rule proposal; unresolved axes require planner action.",
        matched_rule_evidence=result["matched_rule_evidence"],
        match_basis="exact_rule_catalogue",
        action_evidence={"conflicts": [], "unresolved_reasons": result["unresolved_reasons"]},
        components=result["components"],
    )


def mark_unresolved(
    db: Session,
    client_id: int,
    intake_id: str,
    payload: M04ReasonRequest,
) -> M04ClassificationRevision:
    context, rows, _, leaf = _mutation_context(db, client_id, intake_id)
    _expect(leaf, payload.expected_current_revision_id)
    if _revalidation_required(context, rows) and not _current_revalidation_started(
        context, rows
    ):
        raise M04ClassificationError(
            409, "M04_REVALIDATION_REQUIRED", "Revalidation is required"
        )
    if leaf.state != "under_review":
        raise M04ClassificationError(
            409, "M04_INVALID_TRANSITION", "Unresolved requires under_review"
        )
    snapshot = _snapshot(
        context, archive_generation=context.subject.archive_generation
    )
    result = evaluate_exact_catalogue(snapshot)
    return _append(
        db,
        context,
        context.subject,
        previous=leaf,
        state="unresolved",
        action_type="unresolved",
        snapshot=snapshot,
        product_family=result["product_family"],
        aggregate_interpretation="unresolved",
        explanation=payload.explanation,
        reason_code=payload.reason_code,
        reason=payload.explanation,
        matched_rule_evidence=result["matched_rule_evidence"],
        match_basis="explicit_unresolved",
        action_evidence={
            "conflicts": result["conflicts"],
            "unresolved_reasons": result["unresolved_reasons"],
        },
        components=result["components"],
    )


def _is_m05_materially_resolved(
    row: M04ClassificationRevision,
    components: list[M04ComponentDecision],
) -> bool:
    return (
        row.product_family not in (None, "unknown_or_unresolved")
        and bool(components)
        and all(
            component.component_kind != "unknown_component"
            for component in components
        )
    )


def decide_proposal(
    db: Session,
    client_id: int,
    intake_id: str,
    action: str,
    payload: M04ReasonRequest,
) -> M04ClassificationRevision:
    context, rows, component_map, leaf = _mutation_context(db, client_id, intake_id)
    _expect(leaf, payload.expected_current_revision_id)
    if _revalidation_required(context, rows) and not _current_revalidation_started(
        context, rows
    ):
        raise M04ClassificationError(
            409, "M04_REVALIDATION_REQUIRED", "Use start_revalidation"
        )
    if leaf.state != "proposed" or action not in {"accept", "reject"}:
        raise M04ClassificationError(
            409, "M04_INVALID_TRANSITION", "Decision requires a current proposal"
        )
    components = component_map[leaf.revision_id]
    if action == "accept" and not _is_m05_materially_resolved(leaf, components):
        raise M04ClassificationError(
            409,
            "M04_CLASSIFICATION_INCOMPLETE",
            "Classification axes required by M05 must be resolved",
        )
    return _append(
        db,
        context,
        context.subject,
        previous=leaf,
        state="accepted" if action == "accept" else "rejected",
        action_type=action,
        snapshot=leaf.input_snapshot,
        product_family=leaf.product_family,
        pension_subtype=leaf.pension_subtype,
        aggregate_interpretation=leaf.aggregate_interpretation,
        explanation=payload.explanation,
        reason_code=payload.reason_code,
        reason=payload.explanation,
        matched_rule_evidence=leaf.matched_rule_evidence,
        match_basis=leaf.match_basis,
        action_evidence={"proposal_revision_id": leaf.revision_id},
        components=[_component_data(component) for component in components],
    )


def reopen_classification(
    db: Session,
    client_id: int,
    intake_id: str,
    payload: M04ReasonRequest,
) -> M04ClassificationRevision:
    context, rows, _, leaf = _mutation_context(db, client_id, intake_id)
    _expect(leaf, payload.expected_current_revision_id)
    if _revalidation_required(context, rows):
        raise M04ClassificationError(
            409, "M04_REVALIDATION_REQUIRED", "Use start_revalidation"
        )
    if leaf.state not in {"accepted", "unresolved", "rejected"}:
        raise M04ClassificationError(
            409, "M04_INVALID_TRANSITION", "Reopen is not allowed"
        )
    snapshot = _snapshot(
        context, archive_generation=context.subject.archive_generation
    )
    return _append(
        db,
        context,
        context.subject,
        previous=leaf,
        state="under_review",
        action_type="reopen",
        snapshot=snapshot,
        explanation=payload.explanation,
        reason_code=payload.reason_code,
        reason=payload.explanation,
        match_basis="explicit_reopen",
        action_evidence={"prior_revision_id": leaf.revision_id},
    )


def override_classification(
    db: Session,
    client_id: int,
    intake_id: str,
    payload: M04OverrideRequest,
) -> M04ClassificationRevision:
    context, rows, component_map, leaf = _mutation_context(db, client_id, intake_id)
    _expect(leaf, payload.expected_current_revision_id)
    if _revalidation_required(context, rows) and not _current_revalidation_started(
        context, rows
    ):
        raise M04ClassificationError(
            409, "M04_REVALIDATION_REQUIRED", "Use start_revalidation"
        )
    if leaf.state not in {"proposed", "accepted", "unresolved", "rejected"}:
        raise M04ClassificationError(
            409, "M04_INVALID_TRANSITION", "Override is not allowed"
        )
    if payload.pension_subtype is not None:
        raise M04ClassificationError(
            409,
            "M04_PENSION_SUBTYPE_UNSUPPORTED",
            "No approved exact pension subtype evidence is registered",
        )
    snapshot_components = {
        row["evidence_identity"]: row for row in leaf.input_snapshot.get("components", [])
    }
    if {item.evidence_identity for item in payload.components} != set(
        snapshot_components
    ):
        raise M04ClassificationError(
            409,
            "M04_COMPONENT_SET_MISMATCH",
            "Override must classify the complete persisted component set",
        )
    new_components: list[dict[str, Any]] = []
    for item in payload.components:
        source = snapshot_components[item.evidence_identity]
        if item.current_employer_related != source.get(
            "current_employer_related", "unknown"
        ):
            raise M04ClassificationError(
                409,
                "M04_EMPLOYER_RELATION_EVIDENCE_REQUIRED",
                "Employer relation must remain tied to persisted evidence",
            )
        new_components.append(
            {
                "evidence_identity": item.evidence_identity,
                "original_label": source.get("original_label"),
                "original_code": source.get("original_code"),
                "component_kind": item.component_kind,
                "interpretation": item.interpretation,
                "matched_rule_evidence": [],
                "explanation": item.explanation,
                "current_employer_related": item.current_employer_related,
            }
        )
    aggregate = _aggregate(new_components)
    old_values = _decision_values(leaf, component_map[leaf.revision_id])
    new_values = {
        "product_family": payload.product_family,
        "pension_subtype": None,
        "aggregate_interpretation": aggregate,
        "components": new_components,
    }
    return _append(
        db,
        context,
        context.subject,
        previous=leaf,
        state="proposed",
        action_type="override",
        snapshot=leaf.input_snapshot,
        product_family=payload.product_family,
        aggregate_interpretation=aggregate,
        explanation=payload.explanation,
        reason_code=payload.reason_code,
        reason=payload.explanation,
        matched_rule_evidence=leaf.matched_rule_evidence,
        match_basis="planner_authored_override",
        action_evidence={
            "confirmed": True,
            "old_values": old_values,
            "new_values": new_values,
        },
        components=new_components,
    )


def undo_classification(
    db: Session,
    client_id: int,
    intake_id: str,
    payload: M04UndoRequest,
) -> M04ClassificationRevision:
    context, rows, component_map, leaf = _mutation_context(db, client_id, intake_id)
    _expect(leaf, payload.expected_current_revision_id)
    if _revalidation_required(context, rows):
        raise M04ClassificationError(
            409, "M04_REVALIDATION_REQUIRED", "Use start_revalidation"
        )
    if leaf.state not in {"proposed", "accepted", "unresolved", "rejected"}:
        raise M04ClassificationError(
            409, "M04_INVALID_TRANSITION", "Undo is not allowed"
        )
    historical = next(
        (row for row in rows if row.revision_id == payload.historical_revision_id),
        None,
    )
    if historical is None or historical.revision_sequence >= leaf.revision_sequence:
        raise M04ClassificationError(
            404, "M04_RESOURCE_NOT_FOUND", "Resource not found"
        )
    selected_components = component_map[historical.revision_id]
    values = _decision_values(historical, selected_components)
    return _append(
        db,
        context,
        context.subject,
        previous=leaf,
        state="proposed",
        action_type="undo",
        snapshot=leaf.input_snapshot,
        product_family=historical.product_family,
        pension_subtype=historical.pension_subtype,
        aggregate_interpretation=historical.aggregate_interpretation,
        explanation=payload.explanation,
        reason_code=payload.reason_code,
        reason=payload.explanation,
        matched_rule_evidence=historical.matched_rule_evidence,
        match_basis="planner_authored_undo",
        action_evidence={
            "confirmed": True,
            "current_revision_id": leaf.revision_id,
            "selected_historical_revision_id": historical.revision_id,
            "reproposed_values": values,
        },
        historical_revision_id=historical.revision_id,
        components=[_component_data(component) for component in selected_components],
    )


def start_revalidation(
    db: Session,
    client_id: int,
    intake_id: str,
    payload: M04ReasonRequest,
) -> M04ClassificationRevision:
    context, rows, component_map, leaf = _mutation_context(db, client_id, intake_id)
    _expect(leaf, payload.expected_current_revision_id)
    if not _revalidation_required(context, rows):
        raise M04ClassificationError(
            409,
            "M04_REVALIDATION_NOT_REQUIRED",
            "No prior archive requires revalidation",
        )
    if leaf.state not in {"proposed", "accepted", "unresolved", "rejected"}:
        raise M04ClassificationError(
            409, "M04_INVALID_TRANSITION", "Revalidation is not allowed"
        )
    snapshot = _snapshot(
        context, archive_generation=context.subject.archive_generation
    )
    return _append(
        db,
        context,
        context.subject,
        previous=leaf,
        state="under_review",
        action_type="start_revalidation",
        snapshot=snapshot,
        explanation=payload.explanation,
        reason_code=payload.reason_code,
        reason=payload.explanation,
        match_basis="explicit_revalidation",
        action_evidence={
            "historical_revision_id": leaf.revision_id,
            "historical_values": _decision_values(
                leaf, component_map[leaf.revision_id]
            ),
            "historical_values_are_authority": False,
        },
        historical_revision_id=leaf.revision_id,
    )
