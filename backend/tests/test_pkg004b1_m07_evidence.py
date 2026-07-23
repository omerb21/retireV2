from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
import os
from pathlib import Path
import subprocess

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, inspect as sqlalchemy_inspect, select, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.schema import CreateTable
from sqlalchemy.orm import Session

from app.db.base import Base, load_all_models
from app.models.client import Client
import app.models.pension_analysis_record  # noqa: F401
from app.models.m07_evidence import (
    M07AssessmentFinding,
    M07EvidenceImmutableError,
    M07EvidenceRevision,
    M07FactEvidence,
)
from app.schemas.m07_evidence import (
    AssessmentFindingWrite,
    AssessmentRun,
    FactEvidenceWrite,
    PlannerAssertionAppend,
    RevisionDraftCreate,
)
from app.schemas.official_parameter_sets import (
    OfficialParameterActivationRequest,
    OfficialParameterSetCreate,
    OfficialParameterValues,
    OfficialParameterVerificationRequest,
)
from app.services.m07_evidence_service import (
    M07_ASSESSMENT_MANIFESTS,
    M07DuplicateFactIdentityError,
    M07EvidenceInvariantError,
    M07EvidenceLifecycleError,
    M07EvidenceNotFoundError,
    M07EvidenceReferenceError,
    M07MultipleEvidenceBasesError,
    abandon_revision,
    append_planner_assertion,
    attach_resolved_parameter_reference,
    canonical_m07_json,
    create_revision_draft,
    create_successor_draft,
    finalize_revision,
    get_revision,
    list_client_revisions,
    m07_finding_fingerprint,
    m07_fingerprint,
    run_technical_assessment,
    supersede_revision,
    write_assessment_finding,
    write_fact_evidence,
)
from app.services.official_parameter_service import (
    activate_official_parameter_set,
    create_official_parameter_set_draft,
    verify_official_parameter_set,
)


SCHEMA_VERSION = "pkg004b1.m07-evidence.v1"
RULE_VERSION = "pkg004b1.technical-assessment.v1"
NOW = datetime(2026, 7, 23, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def session() -> Session:
    load_all_models()
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db_session:
        db_session.add_all(
            [
                Client(client_id=1, display_name="Client 1", id_number="client-1"),
                Client(client_id=2, display_name="Client 2", id_number="client-2"),
            ]
        )
        db_session.commit()
        yield db_session


def draft_request(profile_id: str = "profile-a") -> RevisionDraftCreate:
    return RevisionDraftCreate(
        profile_id=profile_id,
        tax_year=2026,
        event_year=2026,
        event_type="retirement_event",
        event_id="event-a",
        schema_version=SCHEMA_VERSION,
        rule_version=RULE_VERSION,
    )


def create_draft(session: Session, client_id: int = 1) -> M07EvidenceRevision:
    return create_revision_draft(
        db_session=session,
        client_id=client_id,
        request=draft_request(),
        actor="collector-service",
        timestamp=NOW,
    )


def recorded_fact(
    *,
    field_code: str = "identity.name",
    value="Ada",
    fact_id: str | None = None,
) -> FactEvidenceWrite:
    return FactEvidenceWrite(
        fact_evidence_id=fact_id,
        field_code=field_code,
        structured_value=value,
        collection_state="recorded",
        verification_state="verified",
        verification_basis="document match",
        source_type="external_document",
        source_document_reference="document://source-1",
        source_date=date(2026, 1, 2),
        source_metadata={"page": 1},
    )


def finalize(
    session: Session,
    revision: M07EvidenceRevision,
    required: list[str] | None = None,
) -> M07EvidenceRevision:
    return finalize_revision(
        db_session=session,
        client_id=revision.client_id,
        revision_id=revision.m07_evidence_revision_id,
        actor="finalizer-service",
        assessment=AssessmentRun(),
        timestamp=NOW,
    )


def test_command_vocabularies_are_closed_and_state_evidence_is_required() -> None:
    with pytest.raises(ValidationError):
        FactEvidenceWrite(
            field_code="x",
            collection_state="invented",
            verification_state="unverified",
        )
    with pytest.raises(ValidationError):
        FactEvidenceWrite(
            field_code="x",
            collection_state="recorded",
            verification_state="unverified",
        )
    with pytest.raises(ValidationError):
        FactEvidenceWrite(
            field_code="x",
            collection_state="confirmed_none",
            verification_state="unverified",
        )
    with pytest.raises(ValidationError):
        FactEvidenceWrite(
            field_code="x",
            structured_value=1,
            collection_state="recorded",
            verification_state="verified",
        )


def test_assertion_actor_is_not_accepted_through_ordinary_assertion_dto() -> None:
    with pytest.raises(ValidationError):
        FactEvidenceWrite(
            field_code="identity.name",
            structured_value="Ada",
            collection_state="recorded",
            verification_state="verified",
            verification_basis="document",
            source_type="external_document",
            source_document_reference="document://source",
            collection_actor="caller-controlled",
        )
    with pytest.raises(ValidationError):
        FactEvidenceWrite(
            field_code="identity.name",
            structured_value="Ada",
            collection_state="recorded",
            verification_state="verified",
            verification_basis="document",
            source_type="external_document",
            source_document_reference="document://source",
            verification_actor="caller-controlled",
        )
    with pytest.raises(ValidationError):
        PlannerAssertionAppend(
            field_code="identity.name",
            asserted_value="Ada",
            assertion_basis="planner review",
            assertion_reason="source unavailable",
            asserted_by="planner",
        )
    with pytest.raises(ValidationError):
        RevisionDraftCreate(
            **draft_request().model_dump(),
            status="finalized",
            canonical_payload={},
        )


def test_create_draft_is_client_scoped_and_revision_numbers_are_profile_scoped(
    session: Session,
) -> None:
    first = create_draft(session)
    second = create_draft(session)
    other_client = create_draft(session, client_id=2)
    assert (first.revision_number, second.revision_number) == (1, 2)
    assert other_client.revision_number == 1
    with pytest.raises(M07EvidenceNotFoundError):
        get_revision(
            db_session=session,
            client_id=2,
            revision_id=first.m07_evidence_revision_id,
        )


def test_unknown_schema_and_rule_versions_fail_closed(session: Session) -> None:
    bad_schema = draft_request().model_copy(update={"schema_version": "unknown"})
    with pytest.raises(M07EvidenceInvariantError):
        create_revision_draft(
            db_session=session,
            client_id=1,
            request=bad_schema,
            actor="actor",
        )
    bad_rule = draft_request().model_copy(update={"rule_version": "unknown"})
    with pytest.raises(M07EvidenceInvariantError):
        create_revision_draft(
            db_session=session,
            client_id=1,
            request=bad_rule,
            actor="actor",
        )


def test_fact_write_persists_provenance_and_material_fingerprint(session: Session) -> None:
    revision = create_draft(session)
    first = write_fact_evidence(
        db_session=session,
        client_id=1,
        revision_id=revision.m07_evidence_revision_id,
        request=recorded_fact(),
        recorded_actor="collector-service",
        verification_actor="verifier-service",
        timestamp=NOW,
    )
    assert first.recorded_by == "collector-service"
    assert first.verified_by == "verifier-service"
    assert len(first.content_fingerprint) == 64
    first_fingerprint = first.content_fingerprint
    updated = write_fact_evidence(
        db_session=session,
        client_id=1,
        revision_id=revision.m07_evidence_revision_id,
        request=recorded_fact(fact_id=first.fact_evidence_id, value="Grace"),
        recorded_actor="collector-service",
        verification_actor="verifier-service",
        timestamp=NOW,
    )
    assert updated.content_fingerprint != first_fingerprint
    assert updated.structured_value == "Grace"
    value_fingerprint = updated.content_fingerprint
    updated = write_fact_evidence(
        db_session=session,
        client_id=1,
        revision_id=revision.m07_evidence_revision_id,
        request=recorded_fact(fact_id=first.fact_evidence_id, value="Grace"),
        recorded_actor="different-collector",
        verification_actor="verifier-service",
        timestamp=NOW,
    )
    assert updated.content_fingerprint != value_fingerprint


def test_fact_and_assertion_references_cannot_cross_client_or_revision(
    session: Session,
) -> None:
    first = create_draft(session)
    second = create_draft(session, client_id=2)
    assertion = append_planner_assertion(
        db_session=session,
        client_id=1,
        revision_id=first.m07_evidence_revision_id,
        request=PlannerAssertionAppend(
            field_code="identity.name",
            asserted_value="Ada",
            assertion_basis="planner source comparison",
            assertion_reason="conflicting source records",
        ),
        actor="planner-service",
        timestamp=NOW,
    )
    request = FactEvidenceWrite(
        field_code="identity.name",
        structured_value="Ada",
        collection_state="recorded",
        verification_state="planner_asserted",
        assertion_id=assertion.assertion_id,
    )
    with pytest.raises(M07EvidenceInvariantError):
        write_fact_evidence(
            db_session=session,
            client_id=2,
            revision_id=second.m07_evidence_revision_id,
            request=request,
            recorded_actor="collector-service",
        )


def test_persisted_source_reference_is_validated_in_client_scope(
    session: Session,
) -> None:
    session.execute(
        text(
            """
            INSERT INTO employment_records (
                employment_record_id, client_id, employer_name,
                work_start_date, is_current
            ) VALUES ('employment-1', 1, 'Employer', '2020-01-01', 1)
            """
        )
    )
    own_revision = create_draft(session)
    source_request = recorded_fact().model_copy(
        update={
            "source_type": "persisted_record",
            "source_record_type": "employment_records",
            "source_record_id": "employment-1",
            "source_document_reference": None,
        }
    )
    row = write_fact_evidence(
        db_session=session,
        client_id=1,
        revision_id=own_revision.m07_evidence_revision_id,
        request=source_request,
        recorded_actor="collector-service",
        verification_actor="verifier-service",
    )
    assert row.source_record_id == "employment-1"
    other_revision = create_draft(session, client_id=2)
    with pytest.raises(M07EvidenceReferenceError) as foreign_source:
        write_fact_evidence(
            db_session=session,
            client_id=2,
            revision_id=other_revision.m07_evidence_revision_id,
            request=source_request,
            recorded_actor="collector-service",
            verification_actor="verifier-service",
        )
    assert foreign_source.value.code == "source_reference_invalid"


def test_assertions_are_additive_and_do_not_overwrite_facts(session: Session) -> None:
    revision = create_draft(session)
    fact = write_fact_evidence(
        db_session=session,
        client_id=1,
        revision_id=revision.m07_evidence_revision_id,
        request=recorded_fact(),
        recorded_actor="collector-service",
        verification_actor="verifier-service",
    )
    assertion = append_planner_assertion(
        db_session=session,
        client_id=1,
        revision_id=revision.m07_evidence_revision_id,
        request=PlannerAssertionAppend(
            field_code="identity.name",
            asserted_value="Different",
            assertion_basis="planner review",
            assertion_reason="source conflict",
        ),
        actor="planner-service",
    )
    assert fact.structured_value == "Ada"
    assertion.assertion_reason = "attempted mutation"
    with pytest.raises(M07EvidenceImmutableError):
        session.flush()
    session.rollback()


def test_assessment_emits_explicit_findings_and_orthogonal_outcomes(
    session: Session,
) -> None:
    revision = create_draft(session)
    write_fact_evidence(
        db_session=session,
        client_id=1,
        revision_id=revision.m07_evidence_revision_id,
        request=FactEvidenceWrite(
            field_code="employment_status",
            collection_state="unresolved",
            collection_basis="sources disagree",
            verification_state="source_conflict",
        ),
        recorded_actor="collector-service",
    )
    write_assessment_finding(
        db_session=session,
        client_id=1,
        revision_id=revision.m07_evidence_revision_id,
        request=AssessmentFindingWrite(
            finding_kind="technical_warning",
            finding_code="warning-a",
            category="technical",
            field_references=["employment_status"],
            description="Technical warning.",
        ),
        timestamp=NOW,
    )
    outcomes = run_technical_assessment(
        db_session=session,
        client_id=1,
        revision_id=revision.m07_evidence_revision_id,
        request=AssessmentRun(),
        timestamp=NOW,
    )
    assert set(outcomes.outcomes) == {
        "evidence_incomplete",
        "evidence_conflicting",
        "warning_present",
    }
    findings = session.scalars(
        select(M07AssessmentFinding).where(
            M07AssessmentFinding.m07_evidence_revision_id
            == revision.m07_evidence_revision_id
        )
    ).all()
    assert {"required_field_unresolved", "required_field_missing", "warning-a"} <= {
        finding.finding_code for finding in findings
    }


def test_technical_blocker_is_a_finding_not_a_professional_decision(
    session: Session,
) -> None:
    revision = create_draft(session)
    write_assessment_finding(
        db_session=session,
        client_id=1,
        revision_id=revision.m07_evidence_revision_id,
        request=AssessmentFindingWrite(
            finding_kind="technical_rule_outcome",
            finding_code="Q014",
            category="fixed_technical_rule",
            description="Fixed technical blocker.",
        ),
    )
    outcomes = run_technical_assessment(
        db_session=session,
        client_id=1,
        revision_id=revision.m07_evidence_revision_id,
        request=AssessmentRun(),
    )
    assert set(outcomes.outcomes) == {"technical_blocked", "evidence_incomplete"}


def test_warning_identity_and_fingerprint_are_stable_and_material(
    session: Session,
) -> None:
    revision = create_draft(session)
    warning = write_assessment_finding(
        db_session=session,
        client_id=1,
        revision_id=revision.m07_evidence_revision_id,
        request=AssessmentFindingWrite(
            finding_kind="technical_warning",
            finding_code="warning-a",
            category="technical",
            field_references=["b", "a"],
            description="Original warning.",
        ),
        timestamp=NOW,
    )
    warning_id = warning.finding_id
    original_fingerprint = warning.content_fingerprint
    updated = write_assessment_finding(
        db_session=session,
        client_id=1,
        revision_id=revision.m07_evidence_revision_id,
        request=AssessmentFindingWrite(
            finding_id=warning_id,
            finding_kind="technical_warning",
            finding_code="warning-a",
            category="technical",
            field_references=["a", "b"],
            description="Changed warning.",
        ),
        timestamp=NOW,
    )
    assert updated.finding_id == warning_id
    assert updated.content_fingerprint != original_fingerprint


def test_repeated_assessment_is_deterministic(session: Session) -> None:
    revision = create_draft(session)
    request = AssessmentRun()
    first = run_technical_assessment(
        db_session=session,
        client_id=1,
        revision_id=revision.m07_evidence_revision_id,
        request=request,
        timestamp=NOW,
    )
    first_findings = [
        (finding.finding_id, finding.content_fingerprint)
        for finding in session.scalars(
            select(M07AssessmentFinding).where(
                M07AssessmentFinding.m07_evidence_revision_id
                == revision.m07_evidence_revision_id
            )
        )
    ]
    second = run_technical_assessment(
        db_session=session,
        client_id=1,
        revision_id=revision.m07_evidence_revision_id,
        request=request,
        timestamp=NOW,
    )
    second_findings = [
        (finding.finding_id, finding.content_fingerprint)
        for finding in session.scalars(
            select(M07AssessmentFinding).where(
                M07AssessmentFinding.m07_evidence_revision_id
                == revision.m07_evidence_revision_id
            )
        )
    ]
    assert first == second
    assert first_findings == second_findings


def test_assessment_manifest_is_server_owned_and_empty_revision_is_incomplete(
    session: Session,
) -> None:
    with pytest.raises(ValidationError):
        AssessmentRun(required_field_codes=[])
    revision = create_draft(session)
    result = run_technical_assessment(
        db_session=session,
        client_id=1,
        revision_id=revision.m07_evidence_revision_id,
        request=AssessmentRun(),
        timestamp=NOW,
    )
    manifest = M07_ASSESSMENT_MANIFESTS[(SCHEMA_VERSION, RULE_VERSION)]
    assert result.manifest_version == manifest.manifest_version
    assert result.outcomes == ("evidence_incomplete",)
    assert manifest.required_field_codes


def test_final_snapshot_contains_manifest_and_manifest_material_changes_fingerprint(
    session: Session,
) -> None:
    finalized = finalize(session, create_draft(session))
    manifest_payload = finalized.canonical_payload["assessment_manifest"]
    assert manifest_payload["manifest_version"] == (
        "pkg004b1.m07-required-evidence.v1"
    )
    original = finalized.evidence_fingerprint
    changed_payload = {
        **finalized.canonical_payload,
        "assessment_manifest": {
            **manifest_payload,
            "manifest_version": "pkg004b1.m07-required-evidence.v2",
        },
    }
    assert m07_fingerprint(changed_payload) != original


def test_duplicate_fact_identity_rejected_but_distinct_sources_are_preserved(
    session: Session,
) -> None:
    revision = create_draft(session)
    first_request = recorded_fact(field_code="employment_status")
    write_fact_evidence(
        db_session=session,
        client_id=1,
        revision_id=revision.m07_evidence_revision_id,
        request=first_request,
        recorded_actor="collector",
        verification_actor="verifier",
    )
    with pytest.raises(M07DuplicateFactIdentityError) as duplicate:
        write_fact_evidence(
            db_session=session,
            client_id=1,
            revision_id=revision.m07_evidence_revision_id,
            request=first_request,
            recorded_actor="collector",
            verification_actor="verifier",
        )
    assert duplicate.value.code == "duplicate_fact_identity"
    second_request = first_request.model_copy(
        update={
            "source_document_reference": "document://source-2",
            "structured_value": "different-employment-status",
        }
    )
    write_fact_evidence(
        db_session=session,
        client_id=1,
        revision_id=revision.m07_evidence_revision_id,
        request=second_request,
        recorded_actor="collector",
        verification_actor="verifier",
    )
    facts = session.scalars(
        select(M07FactEvidence).where(
            M07FactEvidence.m07_evidence_revision_id
            == revision.m07_evidence_revision_id,
            M07FactEvidence.field_code == "employment_status",
        )
    ).all()
    assert len(facts) == 2
    result = run_technical_assessment(
        db_session=session,
        client_id=1,
        revision_id=revision.m07_evidence_revision_id,
        request=AssessmentRun(),
    )
    assert "evidence_conflicting" in result.outcomes


@pytest.mark.parametrize("verification_state", ["superseded", "rejected"])
def test_non_authoritative_required_fact_remains_incomplete(
    session: Session, verification_state: str
) -> None:
    revision = create_draft(session)
    write_fact_evidence(
        db_session=session,
        client_id=1,
        revision_id=revision.m07_evidence_revision_id,
        request=recorded_fact(field_code="employment_status").model_copy(
            update={"verification_state": verification_state}
        ),
        recorded_actor="collector",
    )
    result = run_technical_assessment(
        db_session=session,
        client_id=1,
        revision_id=revision.m07_evidence_revision_id,
        request=AssessmentRun(),
    )
    assert "evidence_incomplete" in result.outcomes
    assert session.scalars(
        select(M07FactEvidence).where(
            M07FactEvidence.m07_evidence_revision_id
            == revision.m07_evidence_revision_id
        )
    ).all()


def test_caller_cannot_control_q014_blocking_effect(session: Session) -> None:
    with pytest.raises(ValidationError):
        AssessmentFindingWrite(
            finding_kind="technical_rule_outcome",
            finding_code="Q014",
            category="fixed_technical_rule",
            description="Fixed blocker.",
            technical_blocking_effect=False,
        )
    revision = create_draft(session)
    finding = write_assessment_finding(
        db_session=session,
        client_id=1,
        revision_id=revision.m07_evidence_revision_id,
        request=AssessmentFindingWrite(
            finding_kind="technical_rule_outcome",
            finding_code="Q014",
            category="fixed_technical_rule",
            description="Fixed blocker.",
        ),
    )
    assert finding.technical_blocking_effect is True
    with pytest.raises(M07EvidenceInvariantError):
        write_assessment_finding(
            db_session=session,
            client_id=1,
            revision_id=revision.m07_evidence_revision_id,
            request=AssessmentFindingWrite(
                finding_kind="technical_rule_outcome",
                finding_code="UNKNOWN_RULE",
                category="fixed_technical_rule",
                description="Unknown blocker.",
            ),
        )


def test_complete_outcome_requires_every_server_manifest_fact(session: Session) -> None:
    revision = create_draft(session)
    manifest = M07_ASSESSMENT_MANIFESTS[(SCHEMA_VERSION, RULE_VERSION)]
    for position, field_code in enumerate(manifest.required_field_codes):
        write_fact_evidence(
            db_session=session,
            client_id=1,
            revision_id=revision.m07_evidence_revision_id,
            request=recorded_fact(
                field_code=field_code,
                value=f"value-{position}",
            ).model_copy(
                update={
                    "source_document_reference": f"document://required-{position}"
                }
            ),
            recorded_actor="collector",
            verification_actor="verifier",
        )
    result = run_technical_assessment(
        db_session=session,
        client_id=1,
        revision_id=revision.m07_evidence_revision_id,
        request=AssessmentRun(),
    )
    assert result.outcomes == ("evidence_complete",)


def test_finding_fact_and_assertion_references_are_revision_and_client_scoped(
    session: Session,
) -> None:
    revision = create_draft(session)
    with pytest.raises(M07EvidenceReferenceError) as missing:
        write_assessment_finding(
            db_session=session,
            client_id=1,
            revision_id=revision.m07_evidence_revision_id,
            request=AssessmentFindingWrite(
                finding_kind="technical_warning",
                finding_code="warning-missing",
                category="technical",
                fact_references=["missing-fact"],
                description="Missing reference.",
            ),
        )
    assert missing.value.code == "source_reference_invalid"

    other_client_revision = create_draft(session, client_id=2)
    foreign_assertion = append_planner_assertion(
        db_session=session,
        client_id=2,
        revision_id=other_client_revision.m07_evidence_revision_id,
        request=PlannerAssertionAppend(
            field_code="employment_status",
            asserted_value="employed",
            assertion_basis="basis",
            assertion_reason="reason",
        ),
        actor="planner",
    )
    with pytest.raises(M07EvidenceReferenceError) as foreign:
        write_assessment_finding(
            db_session=session,
            client_id=1,
            revision_id=revision.m07_evidence_revision_id,
            request=AssessmentFindingWrite(
                finding_kind="technical_warning",
                finding_code="warning-foreign",
                category="technical",
                assertion_references=[foreign_assertion.assertion_id],
                description="Foreign reference.",
            ),
        )
    assert foreign.value.code == "source_reference_invalid"
    assert str(foreign.value) == "referenced evidence is unavailable"

    other_revision = create_draft(session)
    other_assertion = append_planner_assertion(
        db_session=session,
        client_id=1,
        revision_id=other_revision.m07_evidence_revision_id,
        request=PlannerAssertionAppend(
            field_code="employment_status",
            asserted_value="employed",
            assertion_basis="basis",
            assertion_reason="reason",
        ),
        actor="planner",
    )
    with pytest.raises(M07EvidenceReferenceError) as cross_revision:
        write_assessment_finding(
            db_session=session,
            client_id=1,
            revision_id=revision.m07_evidence_revision_id,
            request=AssessmentFindingWrite(
                finding_kind="technical_warning",
                finding_code="warning-cross-revision",
                category="technical",
                assertion_references=[other_assertion.assertion_id],
                description="Cross revision.",
            ),
        )
    assert cross_revision.value.code == "source_reference_invalid"
    assert str(cross_revision.value) == "referenced evidence is unavailable"
    with pytest.raises(M07EvidenceReferenceError) as invalid_source:
        write_assessment_finding(
            db_session=session,
            client_id=1,
            revision_id=revision.m07_evidence_revision_id,
            request=AssessmentFindingWrite(
                finding_kind="technical_warning",
                finding_code="warning-source",
                category="technical",
                source_references=["unsupported:source"],
                description="Unsupported source.",
            ),
        )
    assert invalid_source.value.code == "source_reference_invalid"


def test_recorded_fact_requires_provenance_and_assertion_basis_is_validated(
    session: Session,
) -> None:
    revision = create_draft(session)
    without_provenance = FactEvidenceWrite(
        field_code="employment_status",
        structured_value="employed",
        collection_state="recorded",
        verification_state="unverified",
    )
    with pytest.raises(M07EvidenceInvariantError):
        write_fact_evidence(
            db_session=session,
            client_id=1,
            revision_id=revision.m07_evidence_revision_id,
            request=without_provenance,
            recorded_actor="collector",
        )
    assertion = append_planner_assertion(
        db_session=session,
        client_id=1,
        revision_id=revision.m07_evidence_revision_id,
        request=PlannerAssertionAppend(
            field_code="employment_status",
            asserted_value="employed",
            assertion_basis="planner evidence",
            assertion_reason="document unavailable",
        ),
        actor="planner",
    )
    assertion_fact = write_fact_evidence(
        db_session=session,
        client_id=1,
        revision_id=revision.m07_evidence_revision_id,
        request=FactEvidenceWrite(
            field_code="employment_status",
            structured_value="employed",
            collection_state="recorded",
            verification_state="planner_asserted",
            assertion_id=assertion.assertion_id,
        ),
        recorded_actor="collector",
    )
    assert assertion_fact.assertion_id == assertion.assertion_id
    with pytest.raises(M07EvidenceInvariantError):
        write_fact_evidence(
            db_session=session,
            client_id=1,
            revision_id=revision.m07_evidence_revision_id,
            request=FactEvidenceWrite(
                field_code="retirement_timing",
                structured_value="known",
                collection_state="recorded",
                verification_state="planner_asserted",
                assertion_id="missing-assertion",
            ),
            recorded_actor="collector",
        )


def test_whitespace_and_empty_material_values_are_rejected(session: Session) -> None:
    with pytest.raises(ValidationError):
        FactEvidenceWrite(
            **{
                **recorded_fact().model_dump(),
                "field_code": "   ",
            }
        )
    with pytest.raises(ValidationError):
        PlannerAssertionAppend(
            field_code="x",
            asserted_value="value",
            assertion_basis=" ",
            assertion_reason="reason",
        )
    revision = create_draft(session)
    with pytest.raises(ValueError):
        write_fact_evidence(
            db_session=session,
            client_id=1,
            revision_id=revision.m07_evidence_revision_id,
            request=recorded_fact(),
            recorded_actor=" ",
            verification_actor="verifier",
        )
    with pytest.raises(M07EvidenceInvariantError):
        write_fact_evidence(
            db_session=session,
            client_id=1,
            revision_id=revision.m07_evidence_revision_id,
            request=recorded_fact(value={}),
            recorded_actor="collector",
            verification_actor="verifier",
        )


def test_warning_fingerprint_normalizes_order_and_binds_rule_and_evidence(
    session: Session,
) -> None:
    revision = create_draft(session)
    first = AssessmentFindingWrite(
        finding_kind="technical_warning",
        finding_code="warning-order",
        category="technical",
        field_references=["b", "a"],
        description="Warning.",
    )
    second = first.model_copy(update={"field_references": ["a", "b"]})
    first_row = write_assessment_finding(
        db_session=session,
        client_id=1,
        revision_id=revision.m07_evidence_revision_id,
        request=first,
    )
    second_row = write_assessment_finding(
        db_session=session,
        client_id=1,
        revision_id=revision.m07_evidence_revision_id,
        request=second,
    )
    assert first_row.content_fingerprint == second_row.content_fingerprint
    changed_content = first.model_copy(update={"description": "Changed warning."})
    assert m07_finding_fingerprint(
        request=first,
        revision_id=revision.m07_evidence_revision_id,
        rule_version=RULE_VERSION,
    ) != m07_finding_fingerprint(
        request=changed_content,
        revision_id=revision.m07_evidence_revision_id,
        rule_version=RULE_VERSION,
    )
    assert m07_finding_fingerprint(
        request=first,
        revision_id=revision.m07_evidence_revision_id,
        rule_version=RULE_VERSION,
    ) != m07_finding_fingerprint(
        request=first,
        revision_id=revision.m07_evidence_revision_id,
        rule_version="different-rule-version",
    )
    changed_evidence = first.model_copy(update={"fact_references": ["fact-a"]})
    assert m07_finding_fingerprint(
        request=first,
        revision_id=revision.m07_evidence_revision_id,
        rule_version=RULE_VERSION,
    ) != m07_finding_fingerprint(
        request=changed_evidence,
        revision_id=revision.m07_evidence_revision_id,
        rule_version=RULE_VERSION,
    )


def _public_reference_failure(operation) -> tuple[type[Exception], str, str]:
    with pytest.raises(M07EvidenceReferenceError) as failure:
        operation()
    return type(failure.value), failure.value.code, str(failure.value)


def test_missing_foreign_and_cross_revision_child_references_are_indistinguishable(
    session: Session,
) -> None:
    revision = create_draft(session)
    foreign_revision = create_draft(session, client_id=2)
    cross_revision = create_draft(session)
    foreign_fact = write_fact_evidence(
        db_session=session,
        client_id=2,
        revision_id=foreign_revision.m07_evidence_revision_id,
        request=recorded_fact(),
        recorded_actor="collector",
        verification_actor="verifier",
    )
    cross_fact = write_fact_evidence(
        db_session=session,
        client_id=1,
        revision_id=cross_revision.m07_evidence_revision_id,
        request=recorded_fact(),
        recorded_actor="collector",
        verification_actor="verifier",
    )
    failures = []
    for reference_id in (
        "missing-fact",
        foreign_fact.fact_evidence_id,
        cross_fact.fact_evidence_id,
    ):
        failures.append(
            _public_reference_failure(
                lambda reference_id=reference_id: write_assessment_finding(
                    db_session=session,
                    client_id=1,
                    revision_id=revision.m07_evidence_revision_id,
                    request=AssessmentFindingWrite(
                        finding_kind="technical_warning",
                        finding_code="warning-safe-fact",
                        category="technical",
                        fact_references=[reference_id],
                        description="Safe reference failure.",
                    ),
                )
            )
        )
    assert len(set(failures)) == 1
    assert failures[0][1:] == (
        "source_reference_invalid",
        "referenced evidence is unavailable",
    )
    assert session.scalar(
        select(M07AssessmentFinding.finding_id)
        .where(
            M07AssessmentFinding.m07_evidence_revision_id
            == revision.m07_evidence_revision_id
        )
        .limit(1)
    ) is None
    local_fact = write_fact_evidence(
        db_session=session,
        client_id=1,
        revision_id=revision.m07_evidence_revision_id,
        request=recorded_fact(),
        recorded_actor="collector",
        verification_actor="verifier",
    )
    valid = write_assessment_finding(
        db_session=session,
        client_id=1,
        revision_id=revision.m07_evidence_revision_id,
        request=AssessmentFindingWrite(
            finding_kind="technical_warning",
            finding_code="warning-valid-fact",
            category="technical",
            fact_references=[local_fact.fact_evidence_id],
            description="Valid reference.",
        ),
    )
    assert valid.fact_references == [local_fact.fact_evidence_id]


def test_missing_foreign_and_cross_revision_assertions_share_safe_error(
    session: Session,
) -> None:
    revision = create_draft(session)
    foreign_revision = create_draft(session, client_id=2)
    cross_revision = create_draft(session)

    def assertion(target_revision, client_id: int):
        return append_planner_assertion(
            db_session=session,
            client_id=client_id,
            revision_id=target_revision.m07_evidence_revision_id,
            request=PlannerAssertionAppend(
                field_code="employment_status",
                asserted_value="employed",
                assertion_basis="basis",
                assertion_reason="reason",
            ),
            actor="planner",
        )

    foreign = assertion(foreign_revision, 2)
    cross = assertion(cross_revision, 1)
    failures = [
        _public_reference_failure(
            lambda reference_id=reference_id: write_assessment_finding(
                db_session=session,
                client_id=1,
                revision_id=revision.m07_evidence_revision_id,
                request=AssessmentFindingWrite(
                    finding_kind="technical_warning",
                    finding_code="warning-safe-assertion",
                    category="technical",
                    assertion_references=[reference_id],
                    description="Safe assertion failure.",
                ),
            )
        )
        for reference_id in ("missing-assertion", foreign.assertion_id, cross.assertion_id)
    ]
    assert len(set(failures)) == 1
    local = assertion(revision, 1)
    valid = write_assessment_finding(
        db_session=session,
        client_id=1,
        revision_id=revision.m07_evidence_revision_id,
        request=AssessmentFindingWrite(
            finding_kind="technical_warning",
            finding_code="warning-valid-assertion",
            category="technical",
            assertion_references=[local.assertion_id],
            description="Valid assertion.",
        ),
    )
    assert valid.assertion_references == [local.assertion_id]


def test_missing_and_foreign_persisted_sources_share_safe_error_without_partial_fact(
    session: Session,
) -> None:
    session.execute(
        text(
            """
            INSERT INTO employment_records (
                employment_record_id, client_id, employer_name,
                work_start_date, is_current
            ) VALUES
                ('employment-local', 1, 'Local', '2020-01-01', 1),
                ('employment-foreign', 2, 'Foreign', '2020-01-01', 1)
            """
        )
    )
    revision = create_draft(session)

    def persisted_request(source_id: str) -> FactEvidenceWrite:
        return recorded_fact().model_copy(
            update={
                "source_type": "persisted_record",
                "source_record_type": "employment_records",
                "source_record_id": source_id,
                "source_document_reference": None,
            }
        )

    failures = [
        _public_reference_failure(
            lambda source_id=source_id: write_fact_evidence(
                db_session=session,
                client_id=1,
                revision_id=revision.m07_evidence_revision_id,
                request=persisted_request(source_id),
                recorded_actor="collector",
                verification_actor="verifier",
            )
        )
        for source_id in ("employment-missing", "employment-foreign")
    ]
    assert failures[0] == failures[1]
    assert session.scalars(
        select(M07FactEvidence).where(
            M07FactEvidence.m07_evidence_revision_id
            == revision.m07_evidence_revision_id
        )
    ).all() == []
    local = write_fact_evidence(
        db_session=session,
        client_id=1,
        revision_id=revision.m07_evidence_revision_id,
        request=persisted_request("employment-local"),
        recorded_actor="collector",
        verification_actor="verifier",
    )
    assert local.source_record_id == "employment-local"


def test_service_enforces_exactly_one_fact_basis_and_failure_is_atomic(
    session: Session,
) -> None:
    session.execute(
        text(
            """
            INSERT INTO employment_records (
                employment_record_id, client_id, employer_name,
                work_start_date, is_current
            ) VALUES ('employment-1', 1, 'Employer', '2020-01-01', 1)
            """
        )
    )
    revision = create_draft(session)
    assertion = append_planner_assertion(
        db_session=session,
        client_id=1,
        revision_id=revision.m07_evidence_revision_id,
        request=PlannerAssertionAppend(
            field_code="employment_status",
            asserted_value="employed",
            assertion_basis="basis",
            assertion_reason="reason",
        ),
        actor="planner",
    )
    persisted = recorded_fact().model_copy(
        update={
            "source_type": "persisted_record",
            "source_record_type": "employment_records",
            "source_record_id": "employment-1",
            "source_document_reference": None,
        }
    )
    invalid_requests = [
        persisted.model_copy(update={"assertion_id": assertion.assertion_id}),
        recorded_fact().model_copy(
            update={
                "verification_state": "planner_asserted",
                "assertion_id": assertion.assertion_id,
            }
        ),
        persisted.model_copy(
            update={"source_document_reference": "document://second-basis"}
        ),
        recorded_fact().model_copy(update={"assertion_id": assertion.assertion_id}),
    ]
    for request in invalid_requests:
        with pytest.raises(M07MultipleEvidenceBasesError) as failure:
            write_fact_evidence(
                db_session=session,
                client_id=1,
                revision_id=revision.m07_evidence_revision_id,
                request=request,
                recorded_actor="collector",
                verification_actor="verifier"
                if request.verification_state == "verified"
                else None,
            )
        assert failure.value.code == "multiple_evidence_bases_forbidden"
    assert session.scalars(
        select(M07FactEvidence).where(
            M07FactEvidence.m07_evidence_revision_id
            == revision.m07_evidence_revision_id
        )
    ).all() == []


def test_canonical_payload_has_one_basis_and_basis_switch_changes_fingerprint(
    session: Session,
) -> None:
    document_revision = create_draft(session)
    write_fact_evidence(
        db_session=session,
        client_id=1,
        revision_id=document_revision.m07_evidence_revision_id,
        request=recorded_fact(field_code="employment_status"),
        recorded_actor="collector",
        verification_actor="verifier",
    )
    document_revision = finalize(session, document_revision)
    document_fact = document_revision.canonical_payload["facts"][0]
    assert document_fact["source_document_reference"] == "document://source-1"
    assert document_fact["assertion_id"] is None
    assert document_fact["source_record_id"] is None

    assertion_revision = create_draft(session)
    assertion = append_planner_assertion(
        db_session=session,
        client_id=1,
        revision_id=assertion_revision.m07_evidence_revision_id,
        request=PlannerAssertionAppend(
            field_code="employment_status",
            asserted_value="employed",
            assertion_basis="basis",
            assertion_reason="reason",
        ),
        actor="planner",
    )
    write_fact_evidence(
        db_session=session,
        client_id=1,
        revision_id=assertion_revision.m07_evidence_revision_id,
        request=FactEvidenceWrite(
            field_code="employment_status",
            structured_value="employed",
            collection_state="recorded",
            verification_state="planner_asserted",
            assertion_id=assertion.assertion_id,
        ),
        recorded_actor="collector",
    )
    assertion_revision = finalize(session, assertion_revision)
    assertion_fact = assertion_revision.canonical_payload["facts"][0]
    assert assertion_fact["assertion_id"] == assertion.assertion_id
    assert assertion_fact["source_document_reference"] is None
    assert assertion_fact["source_record_id"] is None
    assert (
        document_revision.evidence_fingerprint
        != assertion_revision.evidence_fingerprint
    )


def test_service_rejects_persisted_document_and_assertion_identity_duplicates(
    session: Session,
) -> None:
    session.execute(
        text(
            """
            INSERT INTO employment_records (
                employment_record_id, client_id, employer_name,
                work_start_date, is_current
            ) VALUES ('employment-1', 1, 'Employer', '2020-01-01', 1)
            """
        )
    )
    revision = create_draft(session)
    persisted = recorded_fact(field_code="employment_status").model_copy(
        update={
            "source_type": "persisted_record",
            "source_record_type": "employment_records",
            "source_record_id": "employment-1",
            "source_document_reference": None,
        }
    )
    document = recorded_fact(field_code="retirement_timing")
    assertion = append_planner_assertion(
        db_session=session,
        client_id=1,
        revision_id=revision.m07_evidence_revision_id,
        request=PlannerAssertionAppend(
            field_code="grant_severance_collection_state",
            asserted_value="known",
            assertion_basis="basis",
            assertion_reason="reason",
        ),
        actor="planner",
    )
    assertion_fact = FactEvidenceWrite(
        field_code="grant_severance_collection_state",
        structured_value="known",
        collection_state="recorded",
        verification_state="planner_asserted",
        assertion_id=assertion.assertion_id,
    )
    cases = (
        (persisted, "verifier"),
        (document, "verifier"),
        (assertion_fact, None),
    )
    for request, verification_actor in cases:
        write_fact_evidence(
            db_session=session,
            client_id=1,
            revision_id=revision.m07_evidence_revision_id,
            request=request,
            recorded_actor="collector",
            verification_actor=verification_actor,
        )
        with pytest.raises(M07DuplicateFactIdentityError):
            write_fact_evidence(
                db_session=session,
                client_id=1,
                revision_id=revision.m07_evidence_revision_id,
                request=request,
                recorded_actor="collector",
                verification_actor=verification_actor,
            )


def test_non_null_identity_key_blocks_direct_duplicate_and_null_bypass(
    session: Session,
) -> None:
    revision = create_draft(session)
    row = write_fact_evidence(
        db_session=session,
        client_id=1,
        revision_id=revision.m07_evidence_revision_id,
        request=recorded_fact(),
        recorded_actor="collector",
        verification_actor="verifier",
    )
    session.commit()
    values = {
        column.name: getattr(row, column.name)
        for column in M07FactEvidence.__table__.columns
    }
    values["fact_evidence_id"] = "m07fact-direct-duplicate"
    session.add(M07FactEvidence(**values))
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()

    values["fact_evidence_id"] = "m07fact-null-bypass"
    values["fact_identity_key"] = None
    session.add(M07FactEvidence(**values))
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


def test_fact_identity_constraint_compiles_for_postgresql() -> None:
    ddl = str(
        CreateTable(M07FactEvidence.__table__).compile(
            dialect=postgresql.dialect()
        )
    )
    assert "fact_identity_key VARCHAR(64) NOT NULL" in ddl
    assert "uq_m07_fact_evidence_identity_key" in ddl


def test_incomplete_revision_can_finalize_with_server_payload_and_fingerprints(
    session: Session,
) -> None:
    revision = create_draft(session)
    finalized = finalize(session, revision, required=["missing.field"])
    assert finalized.status == "finalized"
    assert finalized.technical_outcomes == ["evidence_incomplete"]
    assert finalized.canonical_payload["revision"]["client_id"] == "1"
    assert len(finalized.evidence_fingerprint) == 64
    assert len(finalized.source_snapshot_fingerprint) == 64
    assert finalized.fingerprint_algorithm_version == "sha256-canonical-json-v1"


def test_finalized_parent_and_children_are_immutable(session: Session) -> None:
    revision = create_draft(session)
    fact = write_fact_evidence(
        db_session=session,
        client_id=1,
        revision_id=revision.m07_evidence_revision_id,
        request=recorded_fact(),
        recorded_actor="collector-service",
        verification_actor="verifier-service",
    )
    finalized = finalize(session, revision)
    fact_id = fact.fact_evidence_id
    session.commit()
    finalized.event_id = "changed"
    with pytest.raises(M07EvidenceImmutableError):
        session.flush()
    session.rollback()
    fact = session.get(M07FactEvidence, fact_id)
    fact.structured_value = "changed"
    with pytest.raises(M07EvidenceImmutableError):
        session.flush()
    session.rollback()


def test_finalized_child_cannot_be_added_or_deleted(session: Session) -> None:
    revision = create_draft(session)
    fact = write_fact_evidence(
        db_session=session,
        client_id=1,
        revision_id=revision.m07_evidence_revision_id,
        request=recorded_fact(),
        recorded_actor="collector-service",
        verification_actor="verifier-service",
    )
    finalize(session, revision)
    session.commit()
    session.add(
        M07FactEvidence(
            fact_evidence_id="m07fact-direct-add",
            m07_evidence_revision_id=revision.m07_evidence_revision_id,
            client_id=1,
            field_code="direct.add",
            fact_identity_key="c" * 64,
            structured_value={"value": "forbidden"},
            collection_state="recorded",
            collection_basis=None,
            verification_state="unverified",
            authority_classification="EVIDENCE_ONLY_NOT_PROFESSIONAL_AUTHORITY",
            source_type=None,
            source_record_type=None,
            source_record_id=None,
            source_document_reference=None,
            source_date=None,
            source_excerpt=None,
            source_metadata={},
            recorded_at=NOW,
            recorded_by="direct",
            verified_at=None,
            verified_by=None,
            verification_basis=None,
            assertion_id=None,
            content_fingerprint="a" * 64,
        )
    )
    with pytest.raises(M07EvidenceImmutableError):
        session.flush()
    session.rollback()
    fact = session.get(M07FactEvidence, fact.fact_evidence_id)
    session.delete(fact)
    with pytest.raises(M07EvidenceImmutableError):
        session.flush()
    session.rollback()


def test_direct_orm_lifecycle_change_is_blocked(session: Session) -> None:
    revision = create_draft(session)
    revision.status = "finalized"
    with pytest.raises(M07EvidenceImmutableError):
        session.flush()
    session.rollback()


def test_abandoned_draft_is_closed_retained_and_not_deletable(session: Session) -> None:
    revision = create_draft(session)
    abandoned = abandon_revision(
        db_session=session,
        client_id=1,
        revision_id=revision.m07_evidence_revision_id,
        actor="collector-service",
        timestamp=NOW,
    )
    assert abandoned.status == "abandoned"
    revision_id = abandoned.m07_evidence_revision_id
    session.commit()
    session.delete(abandoned)
    with pytest.raises(M07EvidenceImmutableError):
        session.flush()
    session.rollback()
    abandoned = get_revision(
        db_session=session,
        client_id=1,
        revision_id=revision_id,
    )
    abandoned.status = "draft"
    with pytest.raises(M07EvidenceImmutableError):
        session.flush()
    session.rollback()


def test_correction_and_atomic_supersession_preserve_both_revisions(
    session: Session,
) -> None:
    predecessor = finalize(session, create_draft(session))
    successor = create_successor_draft(
        db_session=session,
        client_id=1,
        predecessor_revision_id=predecessor.m07_evidence_revision_id,
        actor="collector-service",
        timestamp=NOW,
    )
    successor = finalize(session, successor)
    superseded = supersede_revision(
        db_session=session,
        client_id=1,
        predecessor_revision_id=predecessor.m07_evidence_revision_id,
        successor_revision_id=successor.m07_evidence_revision_id,
        actor="correction-service",
        timestamp=NOW,
    )
    assert superseded.status == "superseded"
    assert superseded.superseded_by_revision_id == successor.m07_evidence_revision_id
    assert get_revision(
        db_session=session,
        client_id=1,
        revision_id=successor.m07_evidence_revision_id,
    ).status == "finalized"


def test_invalid_supersession_has_no_partial_effect(session: Session) -> None:
    predecessor = finalize(session, create_draft(session))
    unrelated = finalize(session, create_draft(session, client_id=2))
    with pytest.raises(M07EvidenceNotFoundError):
        supersede_revision(
            db_session=session,
            client_id=1,
            predecessor_revision_id=predecessor.m07_evidence_revision_id,
            successor_revision_id=unrelated.m07_evidence_revision_id,
            actor="correction-service",
        )
    assert get_revision(
        db_session=session,
        client_id=1,
        revision_id=predecessor.m07_evidence_revision_id,
    ).status == "finalized"


def test_client_list_is_bounded_and_does_not_select_a_current_revision(
    session: Session,
) -> None:
    create_draft(session)
    create_draft(session)
    create_draft(session, client_id=2)
    rows, total = list_client_revisions(
        db_session=session, client_id=1, offset=0, limit=1
    )
    assert len(rows) == 1
    assert total == 2
    with pytest.raises(ValueError):
        list_client_revisions(db_session=session, client_id=1, limit=101)


def test_parameter_reference_is_server_resolved_and_values_are_not_duplicated(
    session: Session,
) -> None:
    parameter = create_official_parameter_set_draft(
        db_session=session,
        request=OfficialParameterSetCreate(
            parameter_set_id="official-2026-r1",
            tax_year=2026,
            effective_from=date(2026, 1, 1),
            effective_to=date(2026, 12, 31),
            parameter_set_version="r1",
            values=OfficialParameterValues(
                monthly_cap=Decimal("1000"),
                exemption_percentage=Decimal("0.5"),
                capital_multiplier=Decimal("180"),
                grant_impact_multiplier=Decimal("1.35"),
            ),
            source_type="publication",
            source_title="Official publication",
            official_source_reference="official://2026",
            created_by="parameter-service",
        ),
        timestamp=NOW,
    )
    verify_official_parameter_set(
        db_session=session,
        parameter_set_id=parameter.parameter_set_id,
        request=OfficialParameterVerificationRequest(verified_by="verifier"),
        timestamp=NOW,
    )
    activate_official_parameter_set(
        db_session=session,
        parameter_set_id=parameter.parameter_set_id,
        request=OfficialParameterActivationRequest(activated_by="activator"),
        timestamp=NOW,
    )
    revision = create_draft(session)
    attached = attach_resolved_parameter_reference(
        db_session=session,
        client_id=1,
        revision_id=revision.m07_evidence_revision_id,
        tax_year=2026,
        effective_date=date(2026, 6, 1),
        timestamp=NOW,
    )
    assert attached.parameter_set_id == parameter.parameter_set_id
    assert attached.parameter_set_fingerprint == parameter.content_fingerprint
    parameter_columns = {
        column.name
        for column in M07EvidenceRevision.__table__.columns
        if column.name.startswith("parameter_")
    }
    assert parameter_columns == {
        "parameter_set_id",
        "parameter_set_fingerprint",
        "parameter_resolution_timestamp",
        "parameter_requested_tax_year",
        "parameter_effective_date",
    }


def test_canonicalization_is_stable_and_rejects_nonfinite_values() -> None:
    assert canonical_m07_json({"b": 2, "a": 1}) == canonical_m07_json(
        {"a": 1, "b": 2}
    )
    assert m07_fingerprint({"a": 1}) == m07_fingerprint({"a": 1.0})
    with pytest.raises(ValueError):
        canonical_m07_json({"amount": float("nan")})


def test_finalization_fingerprint_changes_for_material_evidence(session: Session) -> None:
    first = create_draft(session)
    write_fact_evidence(
        db_session=session,
        client_id=1,
        revision_id=first.m07_evidence_revision_id,
        request=recorded_fact(value="Ada"),
        recorded_actor="collector-service",
        verification_actor="verifier-service",
    )
    first = finalize(session, first)
    second = create_draft(session)
    write_fact_evidence(
        db_session=session,
        client_id=1,
        revision_id=second.m07_evidence_revision_id,
        request=recorded_fact(value="Grace"),
        recorded_actor="collector-service",
        verification_actor="verifier-service",
    )
    second = finalize(session, second)
    assert first.evidence_fingerprint != second.evidence_fingerprint


def test_model_contains_no_professional_selection_fields() -> None:
    columns = {
        column.name
        for table in (
            M07EvidenceRevision.__table__,
            M07FactEvidence.__table__,
            M07AssessmentFinding.__table__,
        )
        for column in table.columns
    }
    forbidden = {
        "qualification",
        "warning_reviewed",
        "accepted_for_use",
        "is_current",
        "downstream_eligibility",
    }
    assert columns.isdisjoint(forbidden)


def test_every_record_declares_evidence_only_authority(session: Session) -> None:
    revision = create_draft(session)
    fact = write_fact_evidence(
        db_session=session,
        client_id=1,
        revision_id=revision.m07_evidence_revision_id,
        request=recorded_fact(),
        recorded_actor="collector-service",
        verification_actor="verifier-service",
    )
    assertion = append_planner_assertion(
        db_session=session,
        client_id=1,
        revision_id=revision.m07_evidence_revision_id,
        request=PlannerAssertionAppend(
            field_code="identity.name",
            asserted_value="Ada",
            assertion_basis="basis",
            assertion_reason="reason",
        ),
        actor="planner-service",
    )
    finding = write_assessment_finding(
        db_session=session,
        client_id=1,
        revision_id=revision.m07_evidence_revision_id,
        request=AssessmentFindingWrite(
            finding_kind="technical_warning",
            finding_code="warning-a",
            category="technical",
            description="Warning.",
        ),
    )
    assert revision.authority_classification == (
        "EVIDENCE_ONLY_NOT_PROFESSIONAL_AUTHORITY"
    )
    assert fact.authority_classification == (
        "EVIDENCE_ONLY_NOT_PROFESSIONAL_AUTHORITY"
    )
    assert assertion.authority_classification == (
        "ASSERTION_EVIDENCE_ONLY_NOT_PROFESSIONAL_AUTHORITY"
    )
    assert finding.authority_classification == (
        "TECHNICAL_ASSESSMENT_ONLY_NOT_PROFESSIONAL_AUTHORITY"
    )


def _run_alembic(
    db_path: Path, *args: str, check: bool = True
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    return subprocess.run(
        ["alembic", *args],
        cwd=Path(__file__).resolve().parents[1],
        env=environment,
        capture_output=True,
        text=True,
        check=check,
    )


def test_migration_is_additive_unseeded_and_matches_models(tmp_path: Path) -> None:
    db_path = tmp_path / "pkg004b1.db"
    _run_alembic(db_path, "upgrade", "head")
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    inspector = sqlalchemy_inspect(engine)
    expected = {
        "m07_evidence_revisions": M07EvidenceRevision,
        "m07_fact_evidence": M07FactEvidence,
        "m07_assessment_findings": M07AssessmentFinding,
    }
    from app.models.m07_evidence import M07PlannerAssertion

    expected["m07_planner_assertions"] = M07PlannerAssertion
    assert set(expected).issubset(inspector.get_table_names())
    revision_indexes = {
        index["name"]
        for index in inspector.get_indexes("m07_evidence_revisions")
    }
    assert {
        "ix_m07_evidence_revisions_client_tax_event_year",
        "ix_m07_evidence_revisions_client_status",
        "ix_m07_evidence_revisions_client_event_reference",
        "ix_m07_evidence_revisions_client_profile",
    } <= revision_indexes
    fact_indexes = {
        index["name"]: index
        for index in inspector.get_indexes("m07_fact_evidence")
    }
    assert fact_indexes["uq_m07_fact_evidence_persisted_source_identity"][
        "unique"
    ]
    assert fact_indexes["uq_m07_fact_evidence_document_identity"]["unique"]
    assert fact_indexes["uq_m07_fact_evidence_assertion_identity"]["unique"]
    with Session(engine) as db_session:
        for table_name, model in expected.items():
            migrated_columns = {
                column["name"] for column in inspector.get_columns(table_name)
            }
            model_columns = {column.name for column in model.__table__.columns}
            assert migrated_columns == model_columns
            assert db_session.execute(
                text(f"SELECT COUNT(*) FROM {table_name}")
            ).scalar_one() == 0


def test_migration_refuses_closed_evidence_loss(tmp_path: Path) -> None:
    db_path = tmp_path / "pkg004b1-retained.db"
    _run_alembic(db_path, "upgrade", "head")
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    with Session(engine) as db_session:
        db_session.execute(
            text(
                "INSERT INTO clients (client_id, display_name, id_number) "
                "VALUES (1, 'Migration Client', 'migration-client')"
            )
        )
        db_session.execute(
            text(
                """
                INSERT INTO m07_evidence_revisions (
                    m07_evidence_revision_id, profile_id, client_id,
                    revision_number, tax_year, event_year, schema_version,
                    rule_version, status, technical_outcomes,
                    authority_classification,
                    canonical_payload, evidence_fingerprint,
                    fingerprint_algorithm_version, source_snapshot_fingerprint,
                    created_at, created_by, finalized_at, finalized_by
                ) VALUES (
                    'm07rev-retained', 'profile-a', 1, 1, 2026, 2026,
                    'pkg004b1.m07-evidence.v1',
                    'pkg004b1.technical-assessment.v1',
                    'finalized', '["evidence_incomplete"]',
                    'EVIDENCE_ONLY_NOT_PROFESSIONAL_AUTHORITY', '{}',
                    'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
                    'sha256-canonical-json-v1',
                    'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
                    CURRENT_TIMESTAMP, 'creator', CURRENT_TIMESTAMP, 'finalizer'
                )
                """
            )
        )
        db_session.commit()
    result = _run_alembic(
        db_path, "downgrade", "a8e4f2c6d901", check=False
    )
    assert result.returncode != 0
    assert "Cannot downgrade while retained PKG-004B1 M07 evidence exists" in (
        result.stdout + result.stderr
    )


def test_fact_identity_migration_derives_existing_key_and_downgrades_cleanly(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "pkg004b1-identity.db"
    _run_alembic(db_path, "upgrade", "e6f1a9c3b702")
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    with Session(engine) as db_session:
        db_session.execute(
            text(
                "INSERT INTO clients (client_id, display_name, id_number) "
                "VALUES (1, 'Identity Client', 'identity-client')"
            )
        )
        db_session.execute(
            text(
                """
                INSERT INTO m07_evidence_revisions (
                    m07_evidence_revision_id, profile_id, client_id,
                    revision_number, tax_year, event_year, schema_version,
                    rule_version, status, authority_classification,
                    technical_outcomes, fingerprint_algorithm_version,
                    created_at, created_by
                ) VALUES (
                    'm07rev-existing', 'profile-existing', 1, 1, 2026, 2026,
                    'pkg004b1.m07-evidence.v1',
                    'pkg004b1.technical-assessment.v1', 'draft',
                    'EVIDENCE_ONLY_NOT_PROFESSIONAL_AUTHORITY', '[]',
                    'sha256-canonical-json-v1', CURRENT_TIMESTAMP, 'creator'
                )
                """
            )
        )
        db_session.execute(
            text(
                """
                INSERT INTO m07_fact_evidence (
                    fact_evidence_id, m07_evidence_revision_id, client_id,
                    field_code, structured_value, collection_state,
                    verification_state, authority_classification,
                    source_type, source_document_reference, source_metadata,
                    recorded_at, recorded_by, verified_at, verified_by,
                    verification_basis, content_fingerprint
                ) VALUES (
                    'm07fact-existing', 'm07rev-existing', 1,
                    'employment_status', '"employed"', 'recorded', 'verified',
                    'EVIDENCE_ONLY_NOT_PROFESSIONAL_AUTHORITY',
                    'external_document', 'document://existing', '{}',
                    CURRENT_TIMESTAMP, 'collector', CURRENT_TIMESTAMP,
                    'verifier', 'document match',
                    'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
                )
                """
            )
        )
        db_session.commit()
    _run_alembic(db_path, "upgrade", "head")
    inspector = sqlalchemy_inspect(engine)
    assert "fact_identity_key" in {
        column["name"] for column in inspector.get_columns("m07_fact_evidence")
    }
    with Session(engine) as db_session:
        identity_key = db_session.scalar(
            text(
                "SELECT fact_identity_key FROM m07_fact_evidence "
                "WHERE fact_evidence_id = 'm07fact-existing'"
            )
        )
        assert identity_key is not None
        assert len(identity_key) == 64
    _run_alembic(db_path, "downgrade", "e6f1a9c3b702")
    downgraded = sqlalchemy_inspect(
        create_engine(f"sqlite:///{db_path.as_posix()}")
    )
    assert "fact_identity_key" not in {
        column["name"]
        for column in downgraded.get_columns("m07_fact_evidence")
    }
