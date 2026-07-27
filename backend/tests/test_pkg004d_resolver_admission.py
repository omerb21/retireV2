from __future__ import annotations

from copy import deepcopy
from datetime import date

import app.models.pension_analysis_record  # noqa: F401
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base, load_all_models
from app.db.session import get_db
from app.main import app
from app.models.client import Client
from app.models.fixation_input_snapshot import FixationInputSnapshot
from app.models.fixation_run import FixationRun
from app.schemas.fixation_admissibility import AdmissibleFixationInput
from app.schemas.fixation_dependency_manifest import (
    RESOLVER_MANIFEST_SCHEMA_VERSION,
)
from app.services.fixation_admission_service import (
    parse_and_admit_fixation_payload,
)
from app.services.fixation_dependency_service import (
    _build_dependency_manifest,
    compare_fixation_dependency_manifests,
    get_run_with_dependency_manifest,
    parse_persisted_manifest,
)
from app.services.fixation_service import (
    calculate_fixation_payload,
    run_fixation,
)
from app.services.m07_calculation_input_manifest import (
    M08A_FIXATION_CALCULATION_INPUT_MANIFEST,
    M08A_FIXATION_CALCULATION_SCOPE,
    M08A_FIXATION_MANIFEST_VERSION,
    M07_CALCULATION_INPUT_MANIFEST_REGISTRY,
)
from tests.pkg004d_test_support import (
    resolver_payload,
    seed_eligibility_revision,
)


@pytest.fixture
def session() -> Session:
    load_all_models()
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
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


def legacy_payload(*, client_id: int = 1, year: int = 2026) -> dict:
    return {
        "calculation_id": "pkg-004d",
        "calculation_version": "pkg-004d-v1",
        "eligibility_date": f"{year}-01-01",
        "eligibility_year": year,
        "upstream_context": {
            "profile_id": "legacy-m07",
            "client_id": client_id,
            "state": "qualified",
        },
        "parameter_set": {
            "parameter_set_id": f"params-{year}",
            "client_id": client_id,
            "tax_year": year,
            "effective_from": f"{year}-01-01",
            "effective_to": f"{year}-12-31",
            "values": {
                "monthly_cap": 1000.0,
                "exemption_percentage": 0.5,
                "capital_multiplier": 180.0,
                "grant_impact_multiplier": 1.35,
            },
            "source_basis": "accepted fixture",
            "status": "accepted",
            "accepted_for_use": True,
            "accepted_by": "planner",
            "decision_timestamp": f"{year}-01-01T08:00:00Z",
        },
        "grants_collection_state": "confirmed_none",
        "grants": [],
        "future_grant_reservation": None,
        "actual_capitalizations_collection_state": "confirmed_none",
        "actual_capitalizations": [],
        "idf": None,
        "metadata": {"source_data_version_label": "pkg004d"},
    }


def payload_for(
    session: Session,
    *,
    client_id: int = 1,
    dates: tuple[str, ...] = ("2026-01-01",),
    selections: list[dict] | None = None,
) -> tuple[dict, str, list[str]]:
    revision_id, fact_ids = seed_eligibility_revision(
        session,
        client_id=client_id,
        eligibility_dates=dates,
    )
    return (
        resolver_payload(
            legacy_payload(client_id=client_id),
            revision_id=revision_id,
            selections=selections,
        ),
        revision_id,
        fact_ids,
    )


def test_production_manifest_is_exactly_one_non_nullable_iso_date_field() -> None:
    manifest = M07_CALCULATION_INPUT_MANIFEST_REGISTRY.resolve(
        calculation_scope="m08a_fixation",
        manifest_version="1",
    )

    assert manifest is M08A_FIXATION_CALCULATION_INPUT_MANIFEST
    assert manifest.calculation_scope == M08A_FIXATION_CALCULATION_SCOPE
    assert manifest.manifest_version == M08A_FIXATION_MANIFEST_VERSION
    assert [
        (
            field.field_code,
            field.technical_type,
            field.normalization_rule,
            field.nullable,
        )
        for field in manifest.fields
    ] == [("eligibility_date", "date", "iso_date", False)]


def test_resolved_date_reaches_unchanged_engine_with_server_derived_year(
    session: Session,
) -> None:
    payload, _, _ = payload_for(session)

    result = calculate_fixation_payload(
        payload,
        client_id=1,
        db_session=session,
    )

    assert result.status == "success"
    assert result.eligibility_date == date(2026, 1, 1)
    assert result.eligibility_year == 2026
    assert result.monthly_exempt_pension == pytest.approx(500.0)


@pytest.mark.parametrize(
    "field,value",
    [
        ("eligibility_date", "2026-01-01"),
        ("eligibility_year", 2026),
        ("upstream_context", {"state": "qualified"}),
        ("calculation_scope", "m08a_fixation"),
        ("manifest_version", "1"),
        ("resolver_outcome", "resolved"),
        ("resolver_fingerprint", "0" * 64),
        ("source_references", []),
    ],
)
def test_caller_controlled_m07_or_resolver_fields_are_rejected(
    session: Session, field: str, value
) -> None:
    payload, _, _ = payload_for(session)
    payload[field] = value

    result = calculate_fixation_payload(
        payload,
        client_id=1,
        db_session=session,
    )

    assert result.status == "validation_failed"
    assert result.m07_resolution is None


def test_missing_date_stops_before_cbs_and_engine(
    session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    revision_id, _ = seed_eligibility_revision(
        session,
        client_id=1,
        eligibility_dates=(),
    )
    payload = resolver_payload(legacy_payload(), revision_id=revision_id)

    def forbidden_cbs(**_kwargs):
        raise AssertionError("CBS must not run before M07 resolution")

    monkeypatch.setattr(
        "app.services.fixation_service.calculate_fixation_engine",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("engine must not run before M07 resolution")
        ),
    )
    result = calculate_fixation_payload(
        payload,
        client_id=1,
        db_session=session,
        cbs_calculator=forbidden_cbs,
    )

    assert result.status == "validation_failed"
    assert result.m07_resolution is not None
    assert result.m07_resolution.outcome == "missing_inputs"
    assert result.m07_resolution.missing_fields == ["eligibility_date"]


def test_invalid_stored_date_is_missing_not_repaired(session: Session) -> None:
    payload, _, fact_ids = payload_for(session)
    session.execute(
        text(
            """
            UPDATE m07_fact_evidence
            SET structured_value = '"not-a-date"'
            WHERE fact_evidence_id = :fact_id
            """
        ),
        {"fact_id": fact_ids[0]},
    )
    session.flush()

    result = calculate_fixation_payload(
        payload,
        client_id=1,
        db_session=session,
    )

    assert result.status == "validation_failed"
    assert result.m07_resolution is not None
    assert result.m07_resolution.outcome == "missing_inputs"


def test_ambiguous_dates_return_candidates_identities_and_sources(
    session: Session,
) -> None:
    payload, _, fact_ids = payload_for(
        session,
        dates=("2026-01-01", "2027-01-01"),
    )

    result = calculate_fixation_payload(
        payload,
        client_id=1,
        db_session=session,
    )

    assert result.status == "validation_failed"
    assert result.m07_resolution is not None
    assert result.m07_resolution.outcome == "ambiguous_inputs"
    field = result.m07_resolution.ambiguous_fields[0]
    assert field.field_code == "eligibility_date"
    assert {candidate.normalized_value for candidate in field.candidates} == {
        "2026-01-01",
        "2027-01-01",
    }
    assert {
        identity
        for candidate in field.candidates
        for identity in candidate.candidate_identities
    } == {f"fact:{fact_id}" for fact_id in fact_ids}
    assert {
        reference.source_id
        for candidate in field.candidates
        for reference in candidate.source_references
    } == set(fact_ids)


def test_valid_selection_resolves_and_stale_selection_does_not(
    session: Session,
) -> None:
    base_payload, revision_id, fact_ids = payload_for(
        session,
        dates=("2026-01-01", "2027-01-01"),
    )
    valid = deepcopy(base_payload)
    valid["m07_input_reference"]["selections"] = [
        {
            "field_code": "eligibility_date",
            "candidate_identity": f"fact:{fact_ids[0]}",
            "b1_evidence_revision_id": revision_id,
        }
    ]
    stale = deepcopy(base_payload)
    stale["m07_input_reference"]["selections"] = [
        {
            "field_code": "eligibility_date",
            "candidate_identity": "fact:stale",
            "b1_evidence_revision_id": revision_id,
        }
    ]

    valid_result = calculate_fixation_payload(
        valid, client_id=1, db_session=session
    )
    stale_result = calculate_fixation_payload(
        stale, client_id=1, db_session=session
    )

    assert valid_result.status == "success"
    assert valid_result.eligibility_date == date(2026, 1, 1)
    assert stale_result.status == "validation_failed"
    assert stale_result.m07_resolution is not None
    assert stale_result.m07_resolution.outcome == "ambiguous_inputs"


def test_missing_and_foreign_revision_have_safe_equivalent_failure(
    session: Session,
) -> None:
    foreign_revision, _ = seed_eligibility_revision(
        session,
        client_id=2,
    )
    missing = resolver_payload(
        legacy_payload(), revision_id="m07rev-does-not-exist"
    )
    foreign = resolver_payload(
        legacy_payload(), revision_id=foreign_revision
    )

    missing_result = calculate_fixation_payload(
        missing, client_id=1, db_session=session
    )
    foreign_result = calculate_fixation_payload(
        foreign, client_id=1, db_session=session
    )

    assert missing_result.model_dump(mode="json") == (
        foreign_result.model_dump(mode="json")
    )
    assert missing_result.validation_errors[0].message == (
        "calculation input evidence is unavailable"
    )


def test_retirement_timing_does_not_fallback_to_eligibility_date(
    session: Session,
) -> None:
    revision_id, _ = seed_eligibility_revision(
        session,
        client_id=1,
        eligibility_dates=(),
    )
    session.execute(
        text(
            """
            INSERT INTO m07_fact_evidence (
                fact_evidence_id, m07_evidence_revision_id, client_id,
                field_code, structured_value, collection_state,
                verification_state, authority_classification,
                source_type, source_document_reference, recorded_at,
                source_metadata, recorded_by, fact_identity_key,
                content_fingerprint
            ) VALUES (
                'retirement-timing-fact', :revision_id, 1,
                'retirement_timing', '"2026-01-01"', 'recorded',
                'unverified', 'EVIDENCE_ONLY_NOT_PROFESSIONAL_AUTHORITY',
                'external_document', 'document://retirement-timing',
                '2026-07-27T12:00:00Z', '{}', 'test', :identity,
                :fingerprint
            )
            """
        ),
        {
            "revision_id": revision_id,
            "identity": "a" * 64,
            "fingerprint": "b" * 64,
        },
    )
    payload = resolver_payload(legacy_payload(), revision_id=revision_id)

    result = calculate_fixation_payload(
        payload, client_id=1, db_session=session
    )

    assert result.status == "validation_failed"
    assert result.m07_resolution is not None
    assert result.m07_resolution.outcome == "missing_inputs"


def test_m08b_and_m08c_gates_remain_after_resolution(session: Session) -> None:
    payload, _, _ = payload_for(session)
    wrong_year = deepcopy(payload)
    wrong_year["parameter_set"]["tax_year"] = 2025
    unaccepted_grant = deepcopy(payload)
    unaccepted_grant["grants_collection_state"] = "items_recorded"
    unaccepted_grant["grants"] = [
        {
            "grant_id": "grant-1",
            "client_id": 1,
            "item_type": "severance_grant",
            "indexation_mode": "asserted_indexed_amount",
            "indexed_amount": 1000.0,
            "grant_date": "2020-01-01",
            "work_start_date": "2010-01-01",
            "work_end_date": "2020-01-01",
            "source_basis": "source",
            "status": "reviewed",
            "accepted_for_use": False,
            "inclusion_decision": "include",
            "support_status": "supported",
            "conflict_indicator": False,
            "actor": "planner",
            "decision_timestamp": "2026-01-01T08:01:00Z",
        }
    ]

    wrong_year_result = calculate_fixation_payload(
        wrong_year, client_id=1, db_session=session
    )
    unaccepted_result = calculate_fixation_payload(
        unaccepted_grant, client_id=1, db_session=session
    )

    assert {error.path for error in wrong_year_result.validation_errors} == {
        "parameter_set.tax_year"
    }
    assert {
        error.path for error in unaccepted_result.validation_errors
    } == {"grants[0].accepted_for_use"}


def test_success_snapshot_and_dependency_preserve_resolver_evidence(
    session: Session,
) -> None:
    payload, revision_id, fact_ids = payload_for(session)

    run_id = run_fixation(
        client_id=1,
        input_data=payload,
        db_session=session,
    )
    snapshot = session.scalar(
        select(FixationInputSnapshot).where(
            FixationInputSnapshot.fixation_run_id == run_id
        )
    )
    run = get_run_with_dependency_manifest(
        client_id=1,
        run_id=run_id,
        db_session=session,
    )
    manifest = parse_persisted_manifest(run)

    assert snapshot is not None
    assert "upstream_context" not in snapshot.input_payload
    assert snapshot.input_payload["eligibility_date"] == "2026-01-01"
    assert snapshot.input_payload["eligibility_year"] == 2026
    assert snapshot.input_payload["m07_resolution"]["outcome"] == "resolved"
    assert manifest is not None
    assert manifest.manifest_schema_version == RESOLVER_MANIFEST_SCHEMA_VERSION
    resolver_entry = next(
        entry
        for entry in manifest.dependencies
        if entry.dependency_type == "m07_resolver"
    )
    assert resolver_entry.stable_identity == revision_id
    assert resolver_entry.canonical_content.resolver_outcome == "resolved"
    assert {
        ref.source_id
        for ref in resolver_entry.canonical_content.source_references
    } == set(fact_ids)


def test_failed_save_preserves_unresolved_outcome_without_success_result(
    session: Session,
) -> None:
    revision_id, _ = seed_eligibility_revision(
        session,
        client_id=1,
        eligibility_dates=(),
    )
    payload = resolver_payload(legacy_payload(), revision_id=revision_id)

    run_id = run_fixation(
        client_id=1,
        input_data=payload,
        db_session=session,
    )
    run = session.get(FixationRun, run_id)
    snapshot = session.scalar(
        select(FixationInputSnapshot).where(
            FixationInputSnapshot.fixation_run_id == run_id
        )
    )

    assert run is not None and run.status == "validation_failed"
    assert run.fixation_result is None
    assert snapshot is not None
    assert snapshot.input_payload["m07_resolution"]["outcome"] == (
        "missing_inputs"
    )
    assert "eligibility_date" not in snapshot.input_payload


def test_legacy_manifest_remains_readable_and_cross_version_is_unknown(
    session: Session,
) -> None:
    legacy_context = AdmissibleFixationInput(**legacy_payload())
    legacy_manifest = _build_dependency_manifest(
        run_id=1,
        run_identity="legacy-run",
        client_id=1,
        calculation_version="pkg-004d-v1",
        input_contract_version="pkg-004d-v1",
        result_contract_version="pkg-004d-v1",
        context=legacy_context,
    )
    payload, _, _ = payload_for(session)
    resolved_context, _, errors, resolution = parse_and_admit_fixation_payload(
        payload,
        client_id=1,
        db_session=session,
    )
    assert not errors and resolution is not None
    current_manifest = _build_dependency_manifest(
        run_id=1,
        run_identity="legacy-run",
        client_id=1,
        calculation_version="pkg-004d-v1",
        input_contract_version="pkg-004d-v1",
        result_contract_version="pkg-004d-v1",
        context=resolved_context,
        resolution=resolution,
    )

    comparison = compare_fixation_dependency_manifests(
        legacy_manifest,
        current_manifest,
    )

    assert legacy_manifest.manifest_schema_version == (
        "pkg003.fixation-dependency-manifest.v1"
    )
    assert comparison.technical_result == "unknown"
    assert comparison.reason_codes == ["comparison_schema_incompatible"]


def test_no_new_resolution_persistence_table_exists() -> None:
    assert not {
        table_name
        for table_name in Base.metadata.tables
        if "resolution" in table_name
    }


@pytest.mark.parametrize("operation", ["validate", "calculate", "save"])
def test_existing_api_operations_share_server_resolution(
    session: Session, operation: str
) -> None:
    payload, _, _ = payload_for(session)

    def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    try:
        if operation == "save":
            response = client.post(
                "/api/fixation/save",
                json={"client_id": 1, "input_data": payload},
            )
        else:
            response = client.post(
                f"/api/clients/1/fixation/{operation}",
                json=payload,
            )
        assert response.status_code == 200
        assert response.json()["status"] == "success"
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_review_conversion_cannot_bypass_new_admission(
    session: Session,
) -> None:
    legacy = legacy_payload()
    converted_result = calculate_fixation_payload(
        legacy,
        client_id=1,
        db_session=session,
    )

    assert converted_result.status == "validation_failed"
    assert converted_result.m07_resolution is None
