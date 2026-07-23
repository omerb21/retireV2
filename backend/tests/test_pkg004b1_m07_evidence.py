from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
import os
from pathlib import Path
import subprocess

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, inspect as sqlalchemy_inspect, select, text
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
    M07EvidenceInvariantError,
    M07EvidenceLifecycleError,
    M07EvidenceNotFoundError,
    abandon_revision,
    append_planner_assertion,
    attach_resolved_parameter_reference,
    canonical_m07_json,
    create_revision_draft,
    create_successor_draft,
    finalize_revision,
    get_revision,
    list_client_revisions,
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
        collection_actor="collector-service",
        verification_actor="verifier-service",
        verification_basis="document match",
        source_type="document",
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
        assessment=AssessmentRun(
            required_field_codes=required or [],
            rule_version=RULE_VERSION,
        ),
        timestamp=NOW,
    )


def test_command_vocabularies_are_closed_and_state_evidence_is_required() -> None:
    with pytest.raises(ValidationError):
        FactEvidenceWrite(
            field_code="x",
            collection_state="invented",
            verification_state="unverified",
            collection_actor="actor",
        )
    with pytest.raises(ValidationError):
        FactEvidenceWrite(
            field_code="x",
            collection_state="recorded",
            verification_state="unverified",
            collection_actor="actor",
        )
    with pytest.raises(ValidationError):
        FactEvidenceWrite(
            field_code="x",
            collection_state="confirmed_none",
            verification_state="unverified",
            collection_actor="actor",
        )
    with pytest.raises(ValidationError):
        FactEvidenceWrite(
            field_code="x",
            structured_value=1,
            collection_state="recorded",
            verification_state="verified",
            collection_actor="actor",
        )


def test_assertion_actor_is_not_accepted_through_ordinary_assertion_dto() -> None:
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
        timestamp=NOW,
    )
    assert updated.content_fingerprint != first_fingerprint
    assert updated.structured_value == "Grace"


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
        collection_actor="collector-service",
        assertion_id=assertion.assertion_id,
    )
    with pytest.raises(M07EvidenceInvariantError):
        write_fact_evidence(
            db_session=session,
            client_id=2,
            revision_id=second.m07_evidence_revision_id,
            request=request,
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
            "source_record_type": "employment_records",
            "source_record_id": "employment-1",
        }
    )
    row = write_fact_evidence(
        db_session=session,
        client_id=1,
        revision_id=own_revision.m07_evidence_revision_id,
        request=source_request,
    )
    assert row.source_record_id == "employment-1"
    other_revision = create_draft(session, client_id=2)
    with pytest.raises(M07EvidenceNotFoundError):
        write_fact_evidence(
            db_session=session,
            client_id=2,
            revision_id=other_revision.m07_evidence_revision_id,
            request=source_request,
        )


def test_assertions_are_additive_and_do_not_overwrite_facts(session: Session) -> None:
    revision = create_draft(session)
    fact = write_fact_evidence(
        db_session=session,
        client_id=1,
        revision_id=revision.m07_evidence_revision_id,
        request=recorded_fact(),
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
            field_code="conflict.field",
            collection_state="unresolved",
            verification_state="source_conflict",
            collection_actor="collector-service",
        ),
    )
    write_assessment_finding(
        db_session=session,
        client_id=1,
        revision_id=revision.m07_evidence_revision_id,
        request=AssessmentFindingWrite(
            finding_kind="technical_warning",
            finding_code="warning-a",
            category="technical",
            field_references=["conflict.field"],
            description="Technical warning.",
        ),
        timestamp=NOW,
    )
    outcomes = run_technical_assessment(
        db_session=session,
        client_id=1,
        revision_id=revision.m07_evidence_revision_id,
        request=AssessmentRun(
            required_field_codes=["conflict.field", "missing.field"],
            rule_version=RULE_VERSION,
        ),
        timestamp=NOW,
    )
    assert set(outcomes) == {
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
            technical_blocking_effect=True,
        ),
    )
    outcomes = run_technical_assessment(
        db_session=session,
        client_id=1,
        revision_id=revision.m07_evidence_revision_id,
        request=AssessmentRun(required_field_codes=[], rule_version=RULE_VERSION),
    )
    assert outcomes == ["technical_blocked"]


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
    request = AssessmentRun(
        required_field_codes=["missing.field"], rule_version=RULE_VERSION
    )
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
    )
    finalize(session, revision)
    session.commit()
    session.add(
        M07FactEvidence(
            fact_evidence_id="m07fact-direct-add",
            m07_evidence_revision_id=revision.m07_evidence_revision_id,
            client_id=1,
            field_code="direct.add",
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
    )
    first = finalize(session, first)
    second = create_draft(session)
    write_fact_evidence(
        db_session=session,
        client_id=1,
        revision_id=second.m07_evidence_revision_id,
        request=recorded_fact(value="Grace"),
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
