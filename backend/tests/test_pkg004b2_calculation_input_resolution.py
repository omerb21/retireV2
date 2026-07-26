from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base, load_all_models
from app.models.client import Client
import app.models.pension_analysis_record  # noqa: F401
from app.models.m07_evidence import M07FactEvidence
from app.schemas.m07_calculation_input_resolution import (
    CalculationInputResolutionRequest,
    CalculationInputSelection,
    ResolutionOutcome,
)
from app.schemas.m07_evidence import (
    AssessmentRun,
    FactEvidenceWrite,
    PlannerAssertionAppend,
    RevisionDraftCreate,
)
from app.services.m07_calculation_input_manifest import (
    M07_CALCULATION_INPUT_MANIFEST_REGISTRY,
    CalculationInputFieldRule,
    CalculationInputManifest,
    CalculationInputManifestRegistry,
    M07CalculationInputManifestError,
)
from app.services.m07_calculation_input_resolver import (
    M07CalculationInputReferenceError,
    M07CalculationInputSelectionError,
    resolve_calculation_inputs,
)
from app.services.m07_evidence_service import (
    append_planner_assertion,
    canonical_m07_json,
    create_revision_draft,
    finalize_revision,
    write_fact_evidence,
)


NOW = datetime(2026, 7, 26, 12, 0, tzinfo=timezone.utc)
SCOPE = "test.calculation"
MANIFEST_VERSION = "test.calculation-inputs.v1"
AMOUNT_RULE = CalculationInputFieldRule(
    field_code="amount",
    technical_type="decimal",
    normalization_rule="canonical_decimal",
)
STATUS_RULE = CalculationInputFieldRule(
    field_code="status",
    technical_type="enum",
    normalization_rule="enum_exact",
    enum_values=("active", "inactive"),
)
DATE_RULE = CalculationInputFieldRule(
    field_code="event_date",
    technical_type="date",
    normalization_rule="iso_date",
)
IDENTIFIER_RULE = CalculationInputFieldRule(
    field_code="reference_id",
    technical_type="identifier",
    normalization_rule="structured_identifier",
    identifier_pattern=r"REF-[0-9]{4}",
)


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


def registry(
    *rules: CalculationInputFieldRule,
) -> CalculationInputManifestRegistry:
    return CalculationInputManifestRegistry(
        (
            CalculationInputManifest(
                calculation_scope=SCOPE,
                manifest_version=MANIFEST_VERSION,
                fields=rules or (AMOUNT_RULE,),
            ),
        )
    )


def draft_revision(session: Session, client_id: int = 1) -> str:
    revision = create_revision_draft(
        db_session=session,
        client_id=client_id,
        request=RevisionDraftCreate(
            profile_id=f"profile-{client_id}",
            tax_year=2026,
            event_year=2026,
            schema_version="pkg004b1.m07-evidence.v1",
            rule_version="pkg004b1.technical-assessment.v1",
        ),
        actor="collector",
        timestamp=NOW,
    )
    return revision.m07_evidence_revision_id


def add_fact(
    session: Session,
    revision_id: str,
    *,
    field_code: str,
    value: Any,
    fact_id: str,
    client_id: int = 1,
    source_date: date | None = None,
) -> str:
    row = write_fact_evidence(
        db_session=session,
        client_id=client_id,
        revision_id=revision_id,
        request=FactEvidenceWrite(
            field_code=field_code,
            structured_value=value,
            collection_state="recorded",
            verification_state="unverified",
            source_type="external_document",
            source_document_reference=f"document://{fact_id}",
            source_date=source_date,
        ),
        recorded_actor="collector",
        timestamp=NOW,
    )
    return row.fact_evidence_id


def add_assertion(
    session: Session,
    revision_id: str,
    *,
    field_code: str,
    value: Any,
    client_id: int = 1,
) -> str:
    assertion = append_planner_assertion(
        db_session=session,
        client_id=client_id,
        revision_id=revision_id,
        request=PlannerAssertionAppend(
            field_code=field_code,
            asserted_value=value,
            assertion_basis="manual value supplied for calculation",
            assertion_reason="user supplied the value",
        ),
        actor="planner",
        timestamp=NOW,
    )
    return assertion.assertion_id


def finalize(
    session: Session, revision_id: str, client_id: int = 1
) -> None:
    finalize_revision(
        db_session=session,
        client_id=client_id,
        revision_id=revision_id,
        actor="finalizer",
        assessment=AssessmentRun(),
        timestamp=NOW,
    )


def request(
    revision_id: str,
    *,
    selections: list[CalculationInputSelection] | None = None,
) -> CalculationInputResolutionRequest:
    return CalculationInputResolutionRequest(
        calculation_scope=SCOPE,
        manifest_version=MANIFEST_VERSION,
        b1_evidence_revision_id=revision_id,
        selections=selections or [],
    )


def test_unknown_manifest_fails_closed_without_loading_a_revision(
    session: Session,
) -> None:
    with pytest.raises(M07CalculationInputManifestError):
        resolve_calculation_inputs(
            db_session=session,
            client_id=1,
            request=request("missing-revision"),
            manifest_registry=M07_CALCULATION_INPUT_MANIFEST_REGISTRY,
        )


def test_missing_required_value_returns_diagnostics_only(session: Session) -> None:
    revision_id = draft_revision(session)
    finalize(session, revision_id)

    result = resolve_calculation_inputs(
        db_session=session,
        client_id=1,
        request=request(revision_id),
        manifest_registry=registry(AMOUNT_RULE),
    )

    assert result.outcome == "missing_inputs"
    assert result.missing_fields == ["amount"]
    assert result.calculation_payload is None


def test_technically_invalid_value_is_not_usable(session: Session) -> None:
    revision_id = draft_revision(session)
    add_fact(
        session,
        revision_id,
        field_code="amount",
        value="not-a-number",
        fact_id="fact-invalid",
    )
    finalize(session, revision_id)

    result = resolve_calculation_inputs(
        db_session=session,
        client_id=1,
        request=request(revision_id),
        manifest_registry=registry(AMOUNT_RULE),
    )

    assert result.outcome == "missing_inputs"
    assert result.missing_fields == ["amount"]


def test_one_valid_value_is_normalized_and_resolved(session: Session) -> None:
    revision_id = draft_revision(session)
    add_fact(
        session,
        revision_id,
        field_code="amount",
        value="001.2300",
        fact_id="fact-one",
    )
    finalize(session, revision_id)

    result = resolve_calculation_inputs(
        db_session=session,
        client_id=1,
        request=request(revision_id),
        manifest_registry=registry(AMOUNT_RULE),
    )

    assert result.outcome == "resolved"
    assert result.normalized_selected_values == {"amount": "1.23"}
    assert result.calculation_payload is not None


def test_identical_normalized_values_coalesce_and_keep_sources(
    session: Session,
) -> None:
    revision_id = draft_revision(session)
    first_id = add_fact(
        session,
        revision_id,
        field_code="amount",
        value="1.0",
        fact_id="fact-one",
    )
    second_id = add_fact(
        session,
        revision_id,
        field_code="amount",
        value="1.00",
        fact_id="fact-two",
    )
    finalize(session, revision_id)

    result = resolve_calculation_inputs(
        db_session=session,
        client_id=1,
        request=request(revision_id),
        manifest_registry=registry(AMOUNT_RULE),
    )

    assert result.outcome == "resolved"
    assert result.normalized_selected_values == {"amount": "1"}
    assert {
        item.source_id for item in result.source_references["amount"]
    } == {first_id, second_id}


def test_conflicting_values_are_ambiguous_without_selection(
    session: Session,
) -> None:
    revision_id = draft_revision(session)
    add_fact(
        session,
        revision_id,
        field_code="amount",
        value="1",
        fact_id="fact-one",
    )
    add_fact(
        session,
        revision_id,
        field_code="amount",
        value="2",
        fact_id="fact-two",
    )
    finalize(session, revision_id)

    result = resolve_calculation_inputs(
        db_session=session,
        client_id=1,
        request=request(revision_id),
        manifest_registry=registry(AMOUNT_RULE),
    )

    assert result.outcome == "ambiguous_inputs"
    assert result.calculation_payload is None
    assert {
        item.normalized_value
        for item in result.ambiguous_fields[0].candidates
    } == {"1", "2"}


def test_valid_explicit_selection_resolves_a_conflict(session: Session) -> None:
    revision_id = draft_revision(session)
    add_fact(
        session,
        revision_id,
        field_code="amount",
        value="1",
        fact_id="fact-one",
    )
    selected_fact_id = add_fact(
        session,
        revision_id,
        field_code="amount",
        value="2",
        fact_id="fact-two",
    )
    finalize(session, revision_id)

    result = resolve_calculation_inputs(
        db_session=session,
        client_id=1,
        request=request(
            revision_id,
            selections=[
                CalculationInputSelection(
                    field_code="amount",
                    selected_normalized_value="2.00",
                )
            ],
        ),
        manifest_registry=registry(AMOUNT_RULE),
    )

    assert result.outcome == "resolved"
    assert result.normalized_selected_values == {"amount": "2"}
    assert [
        item.source_id for item in result.source_references["amount"]
    ] == [selected_fact_id]


def test_stale_selection_cannot_produce_resolved(session: Session) -> None:
    revision_id = draft_revision(session)
    add_fact(
        session,
        revision_id,
        field_code="amount",
        value="1",
        fact_id="fact-one",
    )
    finalize(session, revision_id)

    result = resolve_calculation_inputs(
        db_session=session,
        client_id=1,
        request=request(
            revision_id,
            selections=[
                CalculationInputSelection(
                    field_code="amount",
                    candidate_identity="fact:removed",
                )
            ],
        ),
        manifest_registry=registry(AMOUNT_RULE),
    )

    assert result.outcome == "ambiguous_inputs"
    assert result.calculation_payload is None


def test_selection_bound_to_another_revision_is_rejected(
    session: Session,
) -> None:
    revision_id = draft_revision(session)
    finalize(session, revision_id)
    with pytest.raises(M07CalculationInputSelectionError) as error:
        resolve_calculation_inputs(
            db_session=session,
            client_id=1,
            request=request(
                revision_id,
                selections=[
                    CalculationInputSelection(
                        field_code="amount",
                        selected_normalized_value="1",
                        b1_evidence_revision_id="another-revision",
                    )
                ],
            ),
            manifest_registry=registry(AMOUNT_RULE),
        )
    assert str(error.value) == "calculation input selection is invalid"


def test_candidate_identity_from_another_field_is_rejected(
    session: Session,
) -> None:
    revision_id = draft_revision(session)
    add_fact(
        session,
        revision_id,
        field_code="amount",
        value="1",
        fact_id="fact-amount",
    )
    status_fact_id = add_fact(
        session,
        revision_id,
        field_code="status",
        value="active",
        fact_id="fact-status",
    )
    finalize(session, revision_id)
    with pytest.raises(M07CalculationInputSelectionError):
        resolve_calculation_inputs(
            db_session=session,
            client_id=1,
            request=request(
                revision_id,
                selections=[
                    CalculationInputSelection(
                        field_code="amount",
                        candidate_identity=f"fact:{status_fact_id}",
                    )
                ],
            ),
            manifest_registry=registry(AMOUNT_RULE, STATUS_RULE),
        )


@pytest.mark.parametrize(
    ("rule", "value", "expected"),
    [
        (DATE_RULE, "2026-07-01", "2026-07-01"),
        (STATUS_RULE, "active", "active"),
        (IDENTIFIER_RULE, "REF-0042", "REF-0042"),
    ],
)
def test_objective_normalization_rules_are_deterministic(
    session: Session,
    rule: CalculationInputFieldRule,
    value: Any,
    expected: Any,
) -> None:
    revision_id = draft_revision(session)
    add_fact(
        session,
        revision_id,
        field_code=rule.field_code,
        value=value,
        fact_id=f"fact-{rule.field_code}",
    )
    finalize(session, revision_id)
    result = resolve_calculation_inputs(
        db_session=session,
        client_id=1,
        request=request(revision_id),
        manifest_registry=registry(rule),
    )
    assert result.normalized_selected_values[rule.field_code] == expected


def test_identical_resolution_has_deterministic_fingerprint(
    session: Session,
) -> None:
    revision_id = draft_revision(session)
    add_fact(
        session,
        revision_id,
        field_code="amount",
        value="10.00",
        fact_id="fact-amount",
    )
    finalize(session, revision_id)
    first = resolve_calculation_inputs(
        db_session=session,
        client_id=1,
        request=request(revision_id),
        manifest_registry=registry(AMOUNT_RULE),
    )
    second = resolve_calculation_inputs(
        db_session=session,
        client_id=1,
        request=request(revision_id),
        manifest_registry=registry(AMOUNT_RULE),
    )
    assert first.fingerprint == second.fingerprint
    assert first.canonical_result == second.canonical_result


def test_foreign_and_missing_revision_are_hidden_identically(
    session: Session,
) -> None:
    foreign_revision = draft_revision(session, client_id=2)
    finalize(session, foreign_revision, client_id=2)
    messages = []
    for revision_id in (foreign_revision, "missing-revision"):
        with pytest.raises(M07CalculationInputReferenceError) as error:
            resolve_calculation_inputs(
                db_session=session,
                client_id=1,
                request=request(revision_id),
                manifest_registry=registry(AMOUNT_RULE),
            )
        messages.append(str(error.value))
    assert messages == [
        "calculation input evidence is unavailable",
        "calculation input evidence is unavailable",
    ]


@pytest.mark.parametrize(
    "forbidden_field",
    ["outcome", "fingerprint", "canonical_result", "manual_candidates"],
)
def test_caller_cannot_supply_server_results_or_manual_candidates(
    forbidden_field: str,
) -> None:
    payload = {
        "calculation_scope": SCOPE,
        "manifest_version": MANIFEST_VERSION,
        "b1_evidence_revision_id": "revision",
        forbidden_field: "caller-value",
    }
    with pytest.raises(ValidationError):
        CalculationInputResolutionRequest.model_validate(payload)


def test_planner_assertion_is_consumed_only_through_b1(session: Session) -> None:
    revision_id = draft_revision(session)
    assertion_id = add_assertion(
        session,
        revision_id,
        field_code="amount",
        value="5.00",
    )
    finalize(session, revision_id)
    result = resolve_calculation_inputs(
        db_session=session,
        client_id=1,
        request=request(revision_id),
        manifest_registry=registry(AMOUNT_RULE),
    )
    assert result.outcome == "resolved"
    assert result.normalized_selected_values == {"amount": "5"}
    assert result.source_references["amount"][0].source_id == assertion_id


def test_source_date_and_origin_never_rank_conflicting_values(
    session: Session,
) -> None:
    revision_id = draft_revision(session)
    add_fact(
        session,
        revision_id,
        field_code="amount",
        value="10",
        fact_id="fact-newer",
        source_date=date(2026, 7, 1),
    )
    add_fact(
        session,
        revision_id,
        field_code="amount",
        value="20",
        fact_id="fact-older",
        source_date=date(2020, 1, 1),
    )
    finalize(session, revision_id)
    result = resolve_calculation_inputs(
        db_session=session,
        client_id=1,
        request=request(revision_id),
        manifest_registry=registry(AMOUNT_RULE),
    )
    assert result.outcome == "ambiguous_inputs"
    assert result.normalized_selected_values == {}


def test_resolved_payload_contains_only_server_resolved_material(
    session: Session,
) -> None:
    revision_id = draft_revision(session)
    add_fact(
        session,
        revision_id,
        field_code="amount",
        value="7",
        fact_id="fact-seven",
    )
    finalize(session, revision_id)
    result = resolve_calculation_inputs(
        db_session=session,
        client_id=1,
        request=request(revision_id),
        manifest_registry=registry(AMOUNT_RULE),
    )
    assert result.calculation_payload is not None
    assert result.calculation_payload.resolution_fingerprint == result.fingerprint
    assert result.calculation_payload.b1_evidence_revision_id == revision_id
    assert result.calculation_payload.normalized_selected_values == {"amount": "7"}


def test_resolution_does_not_modify_finalized_b1_evidence(
    session: Session,
) -> None:
    revision_id = draft_revision(session)
    add_fact(
        session,
        revision_id,
        field_code="amount",
        value="9",
        fact_id="fact-nine",
    )
    finalize(session, revision_id)
    facts_before = [
        (
            fact.fact_evidence_id,
            fact.content_fingerprint,
            canonical_m07_json(fact.structured_value),
        )
        for fact in session.scalars(
            select(M07FactEvidence).where(
                M07FactEvidence.m07_evidence_revision_id == revision_id
            )
        )
    ]

    resolve_calculation_inputs(
        db_session=session,
        client_id=1,
        request=request(revision_id),
        manifest_registry=registry(AMOUNT_RULE),
    )

    facts_after = [
        (
            fact.fact_evidence_id,
            fact.content_fingerprint,
            canonical_m07_json(fact.structured_value),
        )
        for fact in session.scalars(
            select(M07FactEvidence).where(
                M07FactEvidence.m07_evidence_revision_id == revision_id
            )
        )
    ]
    assert facts_after == facts_before
    assert not session.new
    assert not session.dirty
    assert not session.deleted


def test_package_adds_no_resolution_persistence_or_authority_vocabulary() -> None:
    assert set(ResolutionOutcome.__args__) == {
        "resolved",
        "missing_inputs",
        "ambiguous_inputs",
    }
    assert not any(
        "resolution" in table_name
        for table_name in Base.metadata.tables
    )
    schema_fields = set(CalculationInputResolutionRequest.model_fields)
    assert {
        "qualified",
        "warning_reviewed",
        "accepted_for_use",
        "current_resolution",
        "approval",
    }.isdisjoint(schema_fields)
