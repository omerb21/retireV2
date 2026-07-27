from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.db.base import Base, load_all_models
from app.models.client import Client
import app.models.pension_analysis_record  # noqa: F401
from app.models.m07_evidence import M07FactEvidence, M07PlannerAssertion
from app.schemas.m07_evidence import (
    FactEvidenceWrite,
    PlannerAssertionAppend,
    RevisionDraftCreate,
)
from app.services.m07_evidence_service import (
    M07_DERIVED_ONLY_FIELD_CODES,
    M07_EVIDENCE_FIELD_CONTRACTS,
    M07EvidenceInvariantError,
    M07EvidenceNotFoundError,
    append_planner_assertion,
    create_revision_draft,
    write_fact_evidence,
)


SCHEMA_VERSION = "pkg004b1.m07-evidence.v1"
RULE_VERSION = "pkg004b1.technical-assessment.v1"
NOW = datetime(2026, 7, 27, 12, 0, tzinfo=timezone.utc)


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


def create_draft(session: Session, *, client_id: int = 1, profile_id: str = "p-1"):
    return create_revision_draft(
        db_session=session,
        client_id=client_id,
        request=RevisionDraftCreate(
            profile_id=profile_id,
            tax_year=2026,
            event_year=2026,
            event_type="retirement_event",
            event_id="event-1",
            schema_version=SCHEMA_VERSION,
            rule_version=RULE_VERSION,
        ),
        actor="collector",
        timestamp=NOW,
    )


def documentary_fact(
    value,
    *,
    field_code: str = "eligibility_date",
    document_reference: str = "document://eligibility-1",
) -> FactEvidenceWrite:
    return FactEvidenceWrite(
        field_code=field_code,
        structured_value=value,
        collection_state="recorded",
        verification_state="unverified",
        source_type="external_document",
        source_document_reference=document_reference,
        source_date=date(2026, 7, 1),
        source_excerpt="Supplied evidence value",
        source_metadata={"page": 1},
    )


def write_documentary_fact(
    session: Session,
    revision_id: str,
    value,
    *,
    field_code: str = "eligibility_date",
    document_reference: str = "document://eligibility-1",
):
    return write_fact_evidence(
        db_session=session,
        client_id=1,
        revision_id=revision_id,
        request=documentary_fact(
            value,
            field_code=field_code,
            document_reference=document_reference,
        ),
        recorded_actor="collector",
        timestamp=NOW,
    )


def test_contract_metadata_defines_exact_non_nullable_iso_date_field() -> None:
    assert "eligibility_date" in M07_EVIDENCE_FIELD_CONTRACTS
    assert "eligibility_year" not in M07_EVIDENCE_FIELD_CONTRACTS
    contract = M07_EVIDENCE_FIELD_CONTRACTS["eligibility_date"]
    assert contract.field_code == "eligibility_date"
    assert contract.technical_type == "date"
    assert contract.canonical_representation == "YYYY-MM-DD"
    assert contract.normalization_rule == "strict_iso_calendar_date"
    assert contract.nullable is False


@pytest.mark.parametrize("value", ["2026-07-27", "2024-02-29"])
def test_valid_iso_calendar_dates_are_stored_canonically(
    session: Session, value: str
) -> None:
    revision = create_draft(session)

    row = write_documentary_fact(
        session, revision.m07_evidence_revision_id, value
    )

    assert row.structured_value == value
    assert isinstance(row.structured_value, str)


@pytest.mark.parametrize(
    "value",
    [
        "2025-02-29",
        "",
        "   ",
        "2026",
        67,
        "retiring next spring",
        "2026-07-27T00:00:00",
        "2026-07-27T00:00:00+03:00",
        datetime(2026, 7, 27, 0, 0),
        date(2026, 7, 27),
        {"employment_termination_date": "2026-07-27"},
    ],
)
def test_invalid_or_adjacent_fact_values_are_rejected(
    session: Session, value
) -> None:
    revision = create_draft(session)

    with pytest.raises(M07EvidenceInvariantError):
        write_documentary_fact(
            session, revision.m07_evidence_revision_id, value
        )


def test_null_is_rejected_when_eligibility_date_field_is_supplied(
    session: Session,
) -> None:
    revision = create_draft(session)
    request = FactEvidenceWrite(
        field_code="eligibility_date",
        structured_value=None,
        collection_state="unknown",
        collection_basis="No value supplied",
        verification_state="unverified",
    )

    with pytest.raises(M07EvidenceInvariantError):
        write_fact_evidence(
            db_session=session,
            client_id=1,
            revision_id=revision.m07_evidence_revision_id,
            request=request,
            recorded_actor="collector",
        )


def test_planner_assertion_represents_valid_iso_value(session: Session) -> None:
    revision = create_draft(session)

    row = append_planner_assertion(
        db_session=session,
        client_id=1,
        revision_id=revision.m07_evidence_revision_id,
        request=PlannerAssertionAppend(
            field_code="eligibility_date",
            asserted_value="2026-07-27",
            assertion_basis="Planner reviewed supplied evidence",
            assertion_reason="Record the supplied date as assertion evidence",
            source_note="manual value represented through B1",
        ),
        actor="planner",
        timestamp=NOW,
    )

    assert row.asserted_value == "2026-07-27"
    assert row.authority_classification == (
        "ASSERTION_EVIDENCE_ONLY_NOT_PROFESSIONAL_AUTHORITY"
    )


@pytest.mark.parametrize(
    "value", [None, 67, "2026", "2026-07-27T00:00:00Z"]
)
def test_planner_assertion_rejects_non_date_values(
    session: Session, value
) -> None:
    revision = create_draft(session)

    with pytest.raises(M07EvidenceInvariantError):
        append_planner_assertion(
            db_session=session,
            client_id=1,
            revision_id=revision.m07_evidence_revision_id,
            request=PlannerAssertionAppend(
                field_code="eligibility_date",
                asserted_value=value,
                assertion_basis="Planner reviewed supplied evidence",
                assertion_reason="Record the supplied value",
            ),
            actor="planner",
        )


def test_documentary_and_persisted_sources_use_existing_fact_persistence(
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
    documentary = write_documentary_fact(
        session,
        revision.m07_evidence_revision_id,
        "2026-07-27",
        document_reference="document://eligibility",
    )
    persisted = write_fact_evidence(
        db_session=session,
        client_id=1,
        revision_id=revision.m07_evidence_revision_id,
        request=FactEvidenceWrite(
            field_code="eligibility_date",
            structured_value="2026-07-27",
            collection_state="recorded",
            verification_state="unverified",
            source_type="persisted_record",
            source_record_type="employment_records",
            source_record_id="employment-1",
        ),
        recorded_actor="collector",
    )

    assert isinstance(documentary, M07FactEvidence)
    assert isinstance(persisted, M07FactEvidence)
    assert persisted.source_record_id == "employment-1"


def test_client_isolation_precedes_field_write(session: Session) -> None:
    revision = create_draft(session, client_id=1)

    with pytest.raises(M07EvidenceNotFoundError):
        write_fact_evidence(
            db_session=session,
            client_id=2,
            revision_id=revision.m07_evidence_revision_id,
            request=documentary_fact("2026-07-27"),
            recorded_actor="collector",
        )

    assert session.scalars(
        select(M07FactEvidence).where(M07FactEvidence.client_id == 2)
    ).all() == []


def test_fact_preserves_revision_identity_and_provenance(session: Session) -> None:
    revision = create_draft(session)

    row = write_documentary_fact(
        session, revision.m07_evidence_revision_id, "2026-07-27"
    )

    assert row.client_id == 1
    assert row.m07_evidence_revision_id == revision.m07_evidence_revision_id
    assert row.fact_evidence_id
    assert row.source_type == "external_document"
    assert row.source_document_reference == "document://eligibility-1"
    assert row.source_excerpt == "Supplied evidence value"
    assert row.recorded_by == "collector"


@pytest.mark.parametrize("channel", ["fact", "assertion"])
def test_eligibility_year_is_derived_only_and_cannot_be_supplied(
    session: Session, channel: str
) -> None:
    assert M07_DERIVED_ONLY_FIELD_CODES == {"eligibility_year"}
    revision = create_draft(session)

    with pytest.raises(M07EvidenceInvariantError):
        if channel == "fact":
            write_documentary_fact(
                session,
                revision.m07_evidence_revision_id,
                2026,
                field_code="eligibility_year",
            )
        else:
            append_planner_assertion(
                db_session=session,
                client_id=1,
                revision_id=revision.m07_evidence_revision_id,
                request=PlannerAssertionAppend(
                    field_code="eligibility_year",
                    asserted_value=2026,
                    assertion_basis="basis",
                    assertion_reason="reason",
                ),
                actor="planner",
            )


def test_adjacent_fields_do_not_derive_or_alias_eligibility_date(
    session: Session,
) -> None:
    revision = create_draft(session)
    write_documentary_fact(
        session,
        revision.m07_evidence_revision_id,
        "2026-07-27",
        field_code="retirement_timing",
        document_reference="document://retirement-timing",
    )
    write_documentary_fact(
        session,
        revision.m07_evidence_revision_id,
        "1960-01-01",
        field_code="birth_date",
        document_reference="document://birth-date",
    )

    eligibility_rows = session.scalars(
        select(M07FactEvidence).where(
            M07FactEvidence.m07_evidence_revision_id
            == revision.m07_evidence_revision_id,
            M07FactEvidence.field_code == "eligibility_date",
        )
    ).all()

    assert eligibility_rows == []


def test_distinct_sources_remain_additive_without_latest_wins(
    session: Session,
) -> None:
    revision = create_draft(session)
    first = write_documentary_fact(
        session,
        revision.m07_evidence_revision_id,
        "2026-07-27",
        document_reference="document://older-source",
    )
    second = write_documentary_fact(
        session,
        revision.m07_evidence_revision_id,
        "2027-01-01",
        document_reference="document://newer-source",
    )

    rows = session.scalars(
        select(M07FactEvidence).where(
            M07FactEvidence.m07_evidence_revision_id
            == revision.m07_evidence_revision_id,
            M07FactEvidence.field_code == "eligibility_date",
        )
    ).all()

    assert {row.fact_evidence_id for row in rows} == {
        first.fact_evidence_id,
        second.fact_evidence_id,
    }
    assert {row.structured_value for row in rows} == {
        "2026-07-27",
        "2027-01-01",
    }


def test_contract_uses_existing_tables_and_revision_lifecycle(
    session: Session,
) -> None:
    assert [
        table_name
        for table_name in Base.metadata.tables
        if "eligibility" in table_name
    ] == []
    revision = create_draft(session)
    fact = write_documentary_fact(
        session, revision.m07_evidence_revision_id, "2026-07-27"
    )

    assert fact.__tablename__ == "m07_fact_evidence"
    assert revision.status == "draft"


def test_other_generic_b1_field_behavior_is_unchanged(session: Session) -> None:
    revision = create_draft(session)
    value = {"planned_date": "2026-07-27", "description": "client plan"}

    fact = write_documentary_fact(
        session,
        revision.m07_evidence_revision_id,
        value,
        field_code="retirement_timing",
        document_reference="document://retirement-plan",
    )
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

    assert fact.structured_value == value
    assert assertion.asserted_value == "employed"
    assert isinstance(assertion, M07PlannerAssertion)
