from __future__ import annotations

import hashlib
import json
import math
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import Integer, delete, func, inspect, select, update
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.m07_evidence import (
    M07AssessmentFinding,
    M07EvidenceRevision,
    M07FactEvidence,
    M07PlannerAssertion,
)
from app.schemas.m07_evidence import (
    AssessmentFindingWrite,
    AssessmentRun,
    FactEvidenceWrite,
    PlannerAssertionAppend,
    RevisionDraftCreate,
)
from app.services.official_parameter_service import resolve_official_parameter_set


M07_FINGERPRINT_ALGORITHM = "sha256-canonical-json-v1"
M07_READ_CLASSIFICATION = "EVIDENCE_ONLY_NOT_PROFESSIONAL_AUTHORITY"
M07_ASSERTION_CLASSIFICATION = (
    "ASSERTION_EVIDENCE_ONLY_NOT_PROFESSIONAL_AUTHORITY"
)
M07_FINDING_CLASSIFICATION = (
    "TECHNICAL_ASSESSMENT_ONLY_NOT_PROFESSIONAL_AUTHORITY"
)
M07_SUPPORTED_SCHEMA_VERSIONS = {"pkg004b1.m07-evidence.v1"}
M07_SUPPORTED_RULE_VERSIONS = {"pkg004b1.technical-assessment.v1"}
M07_SOURCE_RECORD_KEYS = {
    "employment_records": "employment_record_id",
    "grants": "grant_id",
    "actual_capitalizations": "capitalization_id",
    "clearinghouse_snapshots": "clearinghouse_snapshot_id",
    "pension_holding": "id",
    "capital_asset": "id",
    "recurring_income": "id",
    "recurring_expense": "id",
    "retirement_timing_work_intention": "id",
}


class M07EvidenceNotFoundError(LookupError):
    pass


class M07EvidenceLifecycleError(ValueError):
    pass


class M07EvidenceInvariantError(RuntimeError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _canonical_decimal(value: Decimal) -> str:
    if not value.is_finite():
        raise ValueError("non-finite numeric evidence is not supported")
    rendered = format(value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return "0" if rendered in {"", "-0"} else rendered


def canonicalize_m07_value(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="python")
    if isinstance(value, dict):
        return {
            str(key): canonicalize_m07_value(value[key])
            for key in sorted(value, key=lambda item: str(item))
        }
    if isinstance(value, (list, tuple)):
        return [canonicalize_m07_value(item) for item in value]
    if isinstance(value, bool):
        return value
    if isinstance(value, Decimal):
        return _canonical_decimal(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite numeric evidence is not supported")
        return _canonical_decimal(Decimal(str(value)))
    if isinstance(value, int):
        return _canonical_decimal(Decimal(value))
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.isoformat(timespec="microseconds")
        return (
            value.astimezone(timezone.utc)
            .isoformat(timespec="microseconds")
            .replace("+00:00", "Z")
        )
    if isinstance(value, date):
        return value.isoformat()
    if value is None or isinstance(value, str):
        return value
    raise TypeError(f"unsupported M07 evidence value: {type(value).__name__}")


def canonical_m07_json(value: Any) -> str:
    return json.dumps(
        canonicalize_m07_value(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def m07_fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_m07_json(value).encode("utf-8")).hexdigest()


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}"


def get_revision(
    *,
    db_session: Session,
    client_id: int,
    revision_id: str,
) -> M07EvidenceRevision:
    row = db_session.scalar(
        select(M07EvidenceRevision).where(
            M07EvidenceRevision.client_id == client_id,
            M07EvidenceRevision.m07_evidence_revision_id == revision_id,
        )
    )
    if row is None:
        raise M07EvidenceNotFoundError(revision_id)
    return row


def list_client_revisions(
    *,
    db_session: Session,
    client_id: int,
    profile_id: str | None = None,
    tax_year: int | None = None,
    status: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[M07EvidenceRevision], int]:
    if offset < 0 or limit < 1 or limit > 100:
        raise ValueError("offset must be >= 0 and limit must be between 1 and 100")
    filters = [M07EvidenceRevision.client_id == client_id]
    if profile_id is not None:
        filters.append(M07EvidenceRevision.profile_id == profile_id)
    if tax_year is not None:
        filters.append(M07EvidenceRevision.tax_year == tax_year)
    if status is not None:
        if status not in {"draft", "finalized", "superseded", "abandoned"}:
            raise ValueError("unsupported revision lifecycle status")
        filters.append(M07EvidenceRevision.status == status)
    statement = select(M07EvidenceRevision).where(*filters)
    total = int(
        db_session.scalar(
            select(func.count()).select_from(M07EvidenceRevision).where(*filters)
        )
        or 0
    )
    rows = list(
        db_session.scalars(
            statement.order_by(
                M07EvidenceRevision.profile_id,
                M07EvidenceRevision.revision_number,
            )
            .offset(offset)
            .limit(limit)
        ).all()
    )
    return rows, total


def create_revision_draft(
    *,
    db_session: Session,
    client_id: int,
    request: RevisionDraftCreate,
    actor: str,
    timestamp: datetime | None = None,
    predecessor_revision_id: str | None = None,
) -> M07EvidenceRevision:
    if not actor.strip():
        raise ValueError("actor is required")
    if request.schema_version not in M07_SUPPORTED_SCHEMA_VERSIONS:
        raise M07EvidenceInvariantError("unsupported M07 evidence schema version")
    if request.rule_version not in M07_SUPPORTED_RULE_VERSIONS:
        raise M07EvidenceInvariantError("unsupported M07 technical rule version")
    if predecessor_revision_id is not None:
        predecessor = get_revision(
            db_session=db_session,
            client_id=client_id,
            revision_id=predecessor_revision_id,
        )
        if predecessor.status != "finalized":
            raise M07EvidenceLifecycleError(
                "a successor draft requires a finalized predecessor"
            )
        if predecessor.profile_id != request.profile_id:
            raise M07EvidenceInvariantError("successor profile must match predecessor")
    next_number = int(
        db_session.scalar(
            select(func.max(M07EvidenceRevision.revision_number)).where(
                M07EvidenceRevision.client_id == client_id,
                M07EvidenceRevision.profile_id == request.profile_id,
            )
        )
        or 0
    ) + 1
    row = M07EvidenceRevision(
        m07_evidence_revision_id=_id("m07rev"),
        profile_id=request.profile_id,
        client_id=client_id,
        revision_number=next_number,
        predecessor_revision_id=predecessor_revision_id,
        superseded_by_revision_id=None,
        tax_year=request.tax_year,
        event_year=request.event_year,
        event_type=request.event_type,
        event_id=request.event_id,
        schema_version=request.schema_version,
        rule_version=request.rule_version,
        status="draft",
        authority_classification=M07_READ_CLASSIFICATION,
        technical_outcomes=[],
        assessment_timestamp=None,
        canonical_payload=None,
        evidence_fingerprint=None,
        fingerprint_algorithm_version=M07_FINGERPRINT_ALGORITHM,
        source_snapshot_fingerprint=None,
        parameter_set_id=None,
        parameter_set_fingerprint=None,
        parameter_resolution_timestamp=None,
        parameter_requested_tax_year=None,
        parameter_effective_date=None,
        created_at=timestamp or _utc_now(),
        created_by=actor,
        finalized_at=None,
        finalized_by=None,
        abandoned_at=None,
        abandoned_by=None,
        superseded_at=None,
        superseded_by=None,
    )
    db_session.add(row)
    db_session.flush()
    return row


def create_successor_draft(
    *,
    db_session: Session,
    client_id: int,
    predecessor_revision_id: str,
    actor: str,
    timestamp: datetime | None = None,
) -> M07EvidenceRevision:
    predecessor = get_revision(
        db_session=db_session,
        client_id=client_id,
        revision_id=predecessor_revision_id,
    )
    request = RevisionDraftCreate(
        profile_id=predecessor.profile_id,
        tax_year=predecessor.tax_year,
        event_year=predecessor.event_year,
        event_type=predecessor.event_type,
        event_id=predecessor.event_id,
        schema_version=predecessor.schema_version,
        rule_version=predecessor.rule_version,
    )
    return create_revision_draft(
        db_session=db_session,
        client_id=client_id,
        request=request,
        actor=actor,
        timestamp=timestamp,
        predecessor_revision_id=predecessor_revision_id,
    )


def _require_draft(row: M07EvidenceRevision) -> None:
    if row.status != "draft":
        raise M07EvidenceLifecycleError("operation requires a draft revision")


def _fact_content(request: FactEvidenceWrite) -> dict[str, Any]:
    return request.model_dump(
        mode="python",
        exclude={"fact_evidence_id", "collection_actor", "verification_actor"},
    )


def _validate_source_record_scope(
    *,
    db_session: Session,
    client_id: int,
    source_record_type: str | None,
    source_record_id: str | None,
) -> None:
    if source_record_type is None and source_record_id is None:
        return
    if source_record_type is None or source_record_id is None:
        raise M07EvidenceInvariantError(
            "source record type and ID must be supplied together"
        )
    key_name = M07_SOURCE_RECORD_KEYS.get(source_record_type)
    table = Base.metadata.tables.get(source_record_type)
    if key_name is None or table is None:
        raise M07EvidenceInvariantError("unsupported source record type")
    key_column = table.c[key_name]
    key_value: str | int = source_record_id
    if isinstance(key_column.type, Integer):
        try:
            key_value = int(source_record_id)
        except ValueError as error:
            raise M07EvidenceInvariantError("invalid numeric source record ID") from error
    exists = db_session.scalar(
        select(table.c.client_id).where(
            table.c.client_id == client_id,
            key_column == key_value,
        )
    )
    if exists is None:
        raise M07EvidenceNotFoundError("source record was not found in client scope")


def write_fact_evidence(
    *,
    db_session: Session,
    client_id: int,
    revision_id: str,
    request: FactEvidenceWrite,
    timestamp: datetime | None = None,
) -> M07FactEvidence:
    revision = get_revision(
        db_session=db_session, client_id=client_id, revision_id=revision_id
    )
    _require_draft(revision)
    _validate_source_record_scope(
        db_session=db_session,
        client_id=client_id,
        source_record_type=request.source_record_type,
        source_record_id=request.source_record_id,
    )
    if request.assertion_id is not None:
        assertion = db_session.scalar(
            select(M07PlannerAssertion).where(
                M07PlannerAssertion.client_id == client_id,
                M07PlannerAssertion.m07_evidence_revision_id == revision_id,
                M07PlannerAssertion.assertion_id == request.assertion_id,
            )
        )
        if assertion is None:
            raise M07EvidenceInvariantError("assertion reference is outside revision scope")
    row = None
    if request.fact_evidence_id:
        row = db_session.scalar(
            select(M07FactEvidence).where(
                M07FactEvidence.client_id == client_id,
                M07FactEvidence.m07_evidence_revision_id == revision_id,
                M07FactEvidence.fact_evidence_id == request.fact_evidence_id,
            )
        )
        if row is None:
            raise M07EvidenceNotFoundError(request.fact_evidence_id)
    now = timestamp or _utc_now()
    values = dict(
        field_code=request.field_code,
        structured_value=canonicalize_m07_value(request.structured_value),
        collection_state=request.collection_state,
        collection_basis=request.collection_basis,
        verification_state=request.verification_state,
        authority_classification=M07_READ_CLASSIFICATION,
        source_type=request.source_type,
        source_record_type=request.source_record_type,
        source_record_id=request.source_record_id,
        source_document_reference=request.source_document_reference,
        source_date=request.source_date,
        source_excerpt=request.source_excerpt,
        source_metadata=canonicalize_m07_value(request.source_metadata),
        recorded_at=now,
        recorded_by=request.collection_actor,
        verified_at=now
        if request.verification_state in {"verified", "partly_verified"}
        else None,
        verified_by=request.verification_actor,
        verification_basis=request.verification_basis,
        assertion_id=request.assertion_id,
        content_fingerprint=m07_fingerprint(_fact_content(request)),
    )
    if row is None:
        row = M07FactEvidence(
            fact_evidence_id=request.fact_evidence_id or _id("m07fact"),
            m07_evidence_revision_id=revision_id,
            client_id=client_id,
            **values,
        )
        db_session.add(row)
    else:
        for key, value in values.items():
            setattr(row, key, value)
    db_session.flush()
    return row


def append_planner_assertion(
    *,
    db_session: Session,
    client_id: int,
    revision_id: str,
    request: PlannerAssertionAppend,
    actor: str,
    timestamp: datetime | None = None,
) -> M07PlannerAssertion:
    revision = get_revision(
        db_session=db_session, client_id=client_id, revision_id=revision_id
    )
    _require_draft(revision)
    if not actor.strip():
        raise ValueError("actor is required")
    if request.predecessor_assertion_id:
        predecessor = db_session.scalar(
            select(M07PlannerAssertion).where(
                M07PlannerAssertion.client_id == client_id,
                M07PlannerAssertion.m07_evidence_revision_id == revision_id,
                M07PlannerAssertion.assertion_id
                == request.predecessor_assertion_id,
            )
        )
        if predecessor is None:
            raise M07EvidenceInvariantError(
                "predecessor assertion is outside revision scope"
            )
    content = request.model_dump(mode="python")
    row = M07PlannerAssertion(
        assertion_id=_id("m07assert"),
        m07_evidence_revision_id=revision_id,
        client_id=client_id,
        field_code=request.field_code,
        asserted_value=canonicalize_m07_value(request.asserted_value),
        authority_classification=M07_ASSERTION_CLASSIFICATION,
        assertion_basis=request.assertion_basis,
        assertion_reason=request.assertion_reason,
        source_note=request.source_note,
        asserted_at=timestamp or _utc_now(),
        asserted_by=actor,
        predecessor_assertion_id=request.predecessor_assertion_id,
        content_fingerprint=m07_fingerprint(
            {
                "revision_id": revision_id,
                "rule_version": revision.rule_version,
                **content,
            }
        ),
    )
    db_session.add(row)
    db_session.flush()
    return row


def write_assessment_finding(
    *,
    db_session: Session,
    client_id: int,
    revision_id: str,
    request: AssessmentFindingWrite,
    timestamp: datetime | None = None,
) -> M07AssessmentFinding:
    revision = get_revision(
        db_session=db_session, client_id=client_id, revision_id=revision_id
    )
    _require_draft(revision)
    row = None
    if request.finding_id:
        row = db_session.scalar(
            select(M07AssessmentFinding).where(
                M07AssessmentFinding.client_id == client_id,
                M07AssessmentFinding.m07_evidence_revision_id == revision_id,
                M07AssessmentFinding.finding_id == request.finding_id,
            )
        )
    content = request.model_dump(mode="python", exclude={"finding_id"})
    values = dict(
        finding_kind=request.finding_kind,
        finding_code=request.finding_code,
        authority_classification=M07_FINDING_CLASSIFICATION,
        category=request.category,
        field_references=sorted(set(request.field_references)),
        fact_references=sorted(set(request.fact_references)),
        assertion_references=sorted(set(request.assertion_references)),
        source_references=sorted(set(request.source_references)),
        description=request.description,
        rule_version=revision.rule_version,
        assessment_timestamp=timestamp or _utc_now(),
        technical_blocking_effect=request.technical_blocking_effect,
        content_fingerprint=m07_fingerprint(
            {
                "revision_id": revision_id,
                "rule_version": revision.rule_version,
                **content,
            }
        ),
    )
    if row is None:
        row = M07AssessmentFinding(
            finding_id=request.finding_id or _id("m07finding"),
            m07_evidence_revision_id=revision_id,
            client_id=client_id,
            **values,
        )
        db_session.add(row)
    else:
        for key, value in values.items():
            setattr(row, key, value)
    db_session.flush()
    return row


def run_technical_assessment(
    *,
    db_session: Session,
    client_id: int,
    revision_id: str,
    request: AssessmentRun,
    timestamp: datetime | None = None,
) -> list[str]:
    revision = get_revision(
        db_session=db_session, client_id=client_id, revision_id=revision_id
    )
    _require_draft(revision)
    if request.rule_version != revision.rule_version:
        raise M07EvidenceInvariantError("assessment rule version does not match revision")
    if request.rule_version not in M07_SUPPORTED_RULE_VERSIONS:
        raise M07EvidenceInvariantError("unsupported M07 technical rule version")
    now = timestamp or _utc_now()
    facts = list(
        db_session.scalars(
            select(M07FactEvidence).where(
                M07FactEvidence.client_id == client_id,
                M07FactEvidence.m07_evidence_revision_id == revision_id,
            )
        ).all()
    )
    db_session.execute(
        delete(M07AssessmentFinding).where(
            M07AssessmentFinding.client_id == client_id,
            M07AssessmentFinding.m07_evidence_revision_id == revision_id,
            M07AssessmentFinding.category == "system_required_field_assessment",
        )
    )
    by_field = {fact.field_code: fact for fact in facts}
    incomplete = False
    conflicting = False
    for field_code in sorted(request.required_field_codes):
        fact = by_field.get(field_code)
        kind = None
        code = None
        if fact is None:
            kind, code = "missing_required_field", "required_field_missing"
        elif fact.collection_state in {"unknown", "not_collected"}:
            kind, code = fact.collection_state, f"required_field_{fact.collection_state}"
        elif fact.collection_state == "unresolved":
            kind, code = "unresolved", "required_field_unresolved"
            conflicting = True
        elif fact.verification_state == "source_conflict":
            kind, code = "source_conflict", "required_field_source_conflict"
            conflicting = True
        elif fact.verification_state in {"unverified", "rejected"}:
            kind = "rejected_evidence" if fact.verification_state == "rejected" else "unknown"
            code = f"required_field_{fact.verification_state}"
        if kind is not None:
            if kind not in {"unresolved", "source_conflict"}:
                incomplete = True
            token = m07_fingerprint(
                {
                    "revision_id": revision_id,
                    "field_code": field_code,
                    "code": code,
                    "rule_version": request.rule_version,
                }
            )
            write_assessment_finding(
                db_session=db_session,
                client_id=client_id,
                revision_id=revision_id,
                request=AssessmentFindingWrite(
                    finding_id=f"m07finding-{token[:32]}",
                    finding_kind=kind,
                    finding_code=code,
                    category="system_required_field_assessment",
                    field_references=[field_code],
                    fact_references=[] if fact is None else [fact.fact_evidence_id],
                    description=f"Required evidence field {field_code} is {code}.",
                ),
                timestamp=now,
            )
    findings = list(
        db_session.scalars(
            select(M07AssessmentFinding).where(
                M07AssessmentFinding.client_id == client_id,
                M07AssessmentFinding.m07_evidence_revision_id == revision_id,
            )
        ).all()
    )
    conflicting = conflicting or any(
        finding.finding_kind in {"unresolved", "source_conflict", "incompatible_evidence"}
        for finding in findings
    )
    blocked = any(finding.technical_blocking_effect for finding in findings)
    warning = any(finding.finding_kind == "technical_warning" for finding in findings)
    outcomes: list[str] = []
    if blocked:
        outcomes.append("technical_blocked")
    if conflicting:
        outcomes.append("evidence_conflicting")
    if incomplete:
        outcomes.append("evidence_incomplete")
    if not (blocked or conflicting or incomplete):
        outcomes.append("evidence_complete")
    if warning:
        outcomes.append("warning_present")
    revision.technical_outcomes = outcomes
    revision.assessment_timestamp = now
    db_session.flush()
    return outcomes


def attach_resolved_parameter_reference(
    *,
    db_session: Session,
    client_id: int,
    revision_id: str,
    tax_year: int,
    effective_date: date,
    timestamp: datetime | None = None,
) -> M07EvidenceRevision:
    revision = get_revision(
        db_session=db_session, client_id=client_id, revision_id=revision_id
    )
    _require_draft(revision)
    resolution = resolve_official_parameter_set(
        db_session=db_session,
        tax_year=tax_year,
        effective_date=effective_date,
        resolution_timestamp=timestamp,
    )
    if (
        resolution.result != "resolved"
        or resolution.selected_parameter_set_id is None
        or resolution.evidence is None
    ):
        raise M07EvidenceInvariantError(
            "official parameter reference could not be resolved uniquely"
        )
    revision.parameter_set_id = resolution.selected_parameter_set_id
    revision.parameter_set_fingerprint = resolution.evidence.content_fingerprint
    revision.parameter_resolution_timestamp = resolution.resolution_timestamp
    revision.parameter_requested_tax_year = tax_year
    revision.parameter_effective_date = effective_date
    db_session.flush()
    return revision


def _child_rows(db_session: Session, revision: M07EvidenceRevision):
    scope = (
        M07FactEvidence.client_id == revision.client_id,
        M07FactEvidence.m07_evidence_revision_id
        == revision.m07_evidence_revision_id,
    )
    facts = list(
        db_session.scalars(
            select(M07FactEvidence)
            .where(*scope)
            .order_by(M07FactEvidence.field_code, M07FactEvidence.fact_evidence_id)
        ).all()
    )
    assertions = list(
        db_session.scalars(
            select(M07PlannerAssertion)
            .where(
                M07PlannerAssertion.client_id == revision.client_id,
                M07PlannerAssertion.m07_evidence_revision_id
                == revision.m07_evidence_revision_id,
            )
            .order_by(M07PlannerAssertion.field_code, M07PlannerAssertion.assertion_id)
        ).all()
    )
    findings = list(
        db_session.scalars(
            select(M07AssessmentFinding)
            .where(
                M07AssessmentFinding.client_id == revision.client_id,
                M07AssessmentFinding.m07_evidence_revision_id
                == revision.m07_evidence_revision_id,
            )
            .order_by(
                M07AssessmentFinding.finding_code,
                M07AssessmentFinding.finding_id,
            )
        ).all()
    )
    return facts, assertions, findings


def _material_columns(row, excluded: set[str]) -> dict[str, Any]:
    return {
        column.key: getattr(row, column.key)
        for column in inspect(row).mapper.column_attrs
        if column.key not in excluded
    }


def build_canonical_revision_payload(
    *, db_session: Session, revision: M07EvidenceRevision
) -> tuple[dict[str, Any], str]:
    facts, assertions, findings = _child_rows(db_session, revision)
    payload = {
        "revision": _material_columns(
            revision,
            {
                "status",
                "canonical_payload",
                "evidence_fingerprint",
                "source_snapshot_fingerprint",
                "created_at",
                "created_by",
                "finalized_at",
                "finalized_by",
                "abandoned_at",
                "abandoned_by",
                "superseded_at",
                "superseded_by",
                "superseded_by_revision_id",
            },
        ),
        "facts": [_material_columns(fact, set()) for fact in facts],
        "assertions": [_material_columns(assertion, set()) for assertion in assertions],
        "findings": [_material_columns(finding, set()) for finding in findings],
    }
    canonical = canonicalize_m07_value(payload)
    source_snapshot = m07_fingerprint(
        {
            "facts": canonical["facts"],
            "assertions": canonical["assertions"],
            "findings": canonical["findings"],
        }
    )
    return canonical, source_snapshot


def finalize_revision(
    *,
    db_session: Session,
    client_id: int,
    revision_id: str,
    actor: str,
    assessment: AssessmentRun,
    timestamp: datetime | None = None,
) -> M07EvidenceRevision:
    revision = get_revision(
        db_session=db_session, client_id=client_id, revision_id=revision_id
    )
    _require_draft(revision)
    now = timestamp or _utc_now()
    run_technical_assessment(
        db_session=db_session,
        client_id=client_id,
        revision_id=revision_id,
        request=assessment,
        timestamp=now,
    )
    payload, source_snapshot = build_canonical_revision_payload(
        db_session=db_session, revision=revision
    )
    fingerprint = m07_fingerprint(payload)
    result = db_session.execute(
        update(M07EvidenceRevision)
        .where(
            M07EvidenceRevision.client_id == client_id,
            M07EvidenceRevision.m07_evidence_revision_id == revision_id,
            M07EvidenceRevision.status == "draft",
        )
        .values(
            status="finalized",
            canonical_payload=payload,
            evidence_fingerprint=fingerprint,
            source_snapshot_fingerprint=source_snapshot,
            finalized_at=now,
            finalized_by=actor,
        )
    )
    if result.rowcount != 1:
        raise M07EvidenceLifecycleError("draft finalization lost its lifecycle precondition")
    db_session.expire(revision)
    return get_revision(
        db_session=db_session, client_id=client_id, revision_id=revision_id
    )


def abandon_revision(
    *,
    db_session: Session,
    client_id: int,
    revision_id: str,
    actor: str,
    timestamp: datetime | None = None,
) -> M07EvidenceRevision:
    result = db_session.execute(
        update(M07EvidenceRevision)
        .where(
            M07EvidenceRevision.client_id == client_id,
            M07EvidenceRevision.m07_evidence_revision_id == revision_id,
            M07EvidenceRevision.status == "draft",
        )
        .values(
            status="abandoned",
            abandoned_at=timestamp or _utc_now(),
            abandoned_by=actor,
        )
    )
    if result.rowcount != 1:
        raise M07EvidenceLifecycleError("only a draft revision may be abandoned")
    return get_revision(
        db_session=db_session, client_id=client_id, revision_id=revision_id
    )


def supersede_revision(
    *,
    db_session: Session,
    client_id: int,
    predecessor_revision_id: str,
    successor_revision_id: str,
    actor: str,
    timestamp: datetime | None = None,
) -> M07EvidenceRevision:
    predecessor = get_revision(
        db_session=db_session,
        client_id=client_id,
        revision_id=predecessor_revision_id,
    )
    successor = get_revision(
        db_session=db_session,
        client_id=client_id,
        revision_id=successor_revision_id,
    )
    if predecessor.status != "finalized" or successor.status != "finalized":
        raise M07EvidenceLifecycleError(
            "supersession requires distinct finalized revisions"
        )
    if predecessor_revision_id == successor_revision_id:
        raise M07EvidenceInvariantError("a revision cannot supersede itself")
    if (
        predecessor.profile_id != successor.profile_id
        or successor.predecessor_revision_id != predecessor_revision_id
        or predecessor.superseded_by_revision_id is not None
    ):
        raise M07EvidenceInvariantError("invalid predecessor/successor relationship")
    result = db_session.execute(
        update(M07EvidenceRevision)
        .where(
            M07EvidenceRevision.client_id == client_id,
            M07EvidenceRevision.m07_evidence_revision_id
            == predecessor_revision_id,
            M07EvidenceRevision.status == "finalized",
            M07EvidenceRevision.superseded_by_revision_id.is_(None),
        )
        .values(
            status="superseded",
            superseded_by_revision_id=successor_revision_id,
            superseded_at=timestamp or _utc_now(),
            superseded_by=actor,
        )
    )
    if result.rowcount != 1:
        raise M07EvidenceLifecycleError(
            "supersession lost its lifecycle precondition"
        )
    db_session.expire(predecessor)
    return get_revision(
        db_session=db_session,
        client_id=client_id,
        revision_id=predecessor_revision_id,
    )
