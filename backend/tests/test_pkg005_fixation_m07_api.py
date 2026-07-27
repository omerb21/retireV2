from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base, load_all_models
from app.db.session import get_db
from app.main import app
from app.models.client import Client
from app.models.m07_evidence import (
    M07EvidenceRevision,
    M07FactEvidence,
    M07PlannerAssertion,
)
from app.schemas.m07_evidence import AssessmentRun, RevisionDraftCreate
from app.services.fixation_m07_service import FIXATION_UI_TECHNICAL_ACTOR
from app.services.m07_evidence_service import (
    create_revision_draft,
    finalize_revision,
)
from tests.pkg004d_test_support import seed_eligibility_revision


@pytest.fixture
def api(
    tmp_path: Path,
) -> Generator[tuple[TestClient, sessionmaker], None, None]:
    load_all_models()
    engine = create_engine(f"sqlite:///{tmp_path / 'pkg005.db'}")
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, expire_on_commit=False)
    with session_local() as session:
        session.add_all(
            [
                Client(client_id=1, display_name="Client 1", id_number="client-1"),
                Client(client_id=2, display_name="Client 2", id_number="client-2"),
            ]
        )
        session.commit()

    def override_get_db():
        with session_local() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app), session_local
    finally:
        app.dependency_overrides.pop(get_db, None)


def _seed_missing_revision(session: Session, *, client_id: int) -> str:
    revision = create_revision_draft(
        db_session=session,
        client_id=client_id,
        request=RevisionDraftCreate(
            profile_id="missing-eligibility",
            tax_year=2026,
            event_year=2026,
            schema_version="pkg004b1.m07-evidence.v1",
            rule_version="pkg004b1.technical-assessment.v1",
        ),
        actor="test",
    )
    finalized = finalize_revision(
        db_session=session,
        client_id=client_id,
        revision_id=revision.m07_evidence_revision_id,
        actor="test",
        assessment=AssessmentRun(),
    )
    session.commit()
    return finalized.m07_evidence_revision_id


def _fixation_payload(
    revision_id: str,
    *,
    selections: list[dict] | None = None,
    parameter_accepted: bool = True,
) -> dict:
    return {
        "calculation_id": "pkg005",
        "calculation_version": "pkg005-v1",
        "m07_input_reference": {
            "b1_evidence_revision_id": revision_id,
            "selections": selections or [],
        },
        "parameter_set": {
            "parameter_set_id": "params-2026",
            "client_id": 1,
            "tax_year": 2026,
            "effective_from": "2026-01-01",
            "effective_to": "2026-12-31",
            "values": {
                "monthly_cap": 1000,
                "exemption_percentage": 0.5,
                "capital_multiplier": 180,
                "grant_impact_multiplier": 1.35,
            },
            "source_basis": "accepted fixture",
            "status": "accepted" if parameter_accepted else "rejected",
            "accepted_for_use": parameter_accepted,
            "accepted_by": "planner",
            "decision_timestamp": "2026-01-01T08:00:00Z",
        },
        "grants_collection_state": "confirmed_none",
        "grants": [],
        "future_grant_reservation": None,
        "actual_capitalizations_collection_state": "confirmed_none",
        "actual_capitalizations": [],
        "idf": None,
        "metadata": {"source_data_version_label": "pkg005-test"},
    }


def test_create_eligibility_revision_is_atomic_and_records_technical_actor(
    api: tuple[TestClient, sessionmaker],
) -> None:
    client, session_local = api

    response = client.post(
        "/api/clients/1/fixation/m07/eligibility-date-revisions",
        json={"eligibility_date": "2026-04-15"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "finalized"
    assert payload["eligibility_date"] == "2026-04-15"
    assert payload["technical_actor"] == FIXATION_UI_TECHNICAL_ACTOR
    revision_id = payload["revision_id"]

    with session_local() as session:
        revision = session.scalar(
            select(M07EvidenceRevision).where(
                M07EvidenceRevision.m07_evidence_revision_id == revision_id
            )
        )
        assertion = session.scalar(
            select(M07PlannerAssertion).where(
                M07PlannerAssertion.m07_evidence_revision_id == revision_id
            )
        )
        fact = session.scalar(
            select(M07FactEvidence).where(
                M07FactEvidence.m07_evidence_revision_id == revision_id
            )
        )
        assert revision is not None
        assert assertion is not None
        assert fact is not None
        assert revision.client_id == 1
        assert revision.status == "finalized"
        assert revision.created_by == FIXATION_UI_TECHNICAL_ACTOR
        assert revision.finalized_by == FIXATION_UI_TECHNICAL_ACTOR
        assert assertion.asserted_by == FIXATION_UI_TECHNICAL_ACTOR
        assert fact.recorded_by == FIXATION_UI_TECHNICAL_ACTOR
        assert fact.source_metadata == {
            "actor_code": "fixation-ui",
            "actor_label": "Fixation workflow",
            "actor_type": "system",
        }


def test_invalid_date_and_browser_actor_do_not_create_a_revision(
    api: tuple[TestClient, sessionmaker],
) -> None:
    client, session_local = api

    invalid = client.post(
        "/api/clients/1/fixation/m07/eligibility-date-revisions",
        json={"eligibility_date": "2026-02-30"},
    )
    actor_attempt = client.post(
        "/api/clients/1/fixation/m07/eligibility-date-revisions",
        json={"eligibility_date": "2026-02-20", "actor": "browser-user"},
    )

    assert invalid.status_code == 422
    assert actor_attempt.status_code == 422
    with session_local() as session:
        assert session.scalar(select(M07EvidenceRevision)) is None


def test_list_revisions_is_finalized_bounded_explicit_and_client_isolated(
    api: tuple[TestClient, sessionmaker],
) -> None:
    client, session_local = api
    with session_local() as session:
        resolved_id, _ = seed_eligibility_revision(
            session,
            client_id=1,
            eligibility_dates=("2026-01-01",),
        )
        ambiguous_id, _ = seed_eligibility_revision(
            session,
            client_id=1,
            eligibility_dates=("2026-01-01", "2026-02-01"),
        )
        missing_id = _seed_missing_revision(session, client_id=1)
        foreign_id, _ = seed_eligibility_revision(
            session,
            client_id=2,
            eligibility_dates=("2027-01-01",),
        )

    response = client.get("/api/clients/1/fixation/m07/revisions?limit=2")
    assert response.status_code == 200
    first_page = response.json()
    assert first_page["total"] == 3
    assert first_page["limit"] == 2
    assert len(first_page["items"]) == 2

    all_response = client.get("/api/clients/1/fixation/m07/revisions?limit=50")
    assert all_response.status_code == 200
    by_id = {item["revision_id"]: item for item in all_response.json()["items"]}
    assert foreign_id not in by_id
    assert by_id[resolved_id]["eligibility_outcome"] == "resolved"
    assert by_id[resolved_id]["eligibility_dates"] == ["2026-01-01"]
    assert by_id[ambiguous_id]["eligibility_outcome"] == "ambiguous_inputs"
    assert by_id[ambiguous_id]["eligibility_dates"] == [
        "2026-01-01",
        "2026-02-01",
    ]
    assert by_id[missing_id]["eligibility_outcome"] == "missing_inputs"
    assert by_id[missing_id]["eligibility_dates"] == []
    assert all(item["status"] == "finalized" for item in by_id.values())
    assert "current" not in all_response.text
    assert "selected" not in all_response.text


def test_missing_client_is_safe_for_list_and_create(
    api: tuple[TestClient, sessionmaker],
) -> None:
    client, _ = api

    listed = client.get("/api/clients/999/fixation/m07/revisions")
    created = client.post(
        "/api/clients/999/fixation/m07/eligibility-date-revisions",
        json={"eligibility_date": "2026-04-15"},
    )

    assert listed.status_code == 404
    assert created.status_code == 404
    assert listed.json()["detail"]["code"] == "CLIENT_NOT_FOUND"
    assert created.json()["detail"]["code"] == "CLIENT_NOT_FOUND"


def test_complete_validate_calculate_save_and_reopen_workflow(
    api: tuple[TestClient, sessionmaker],
) -> None:
    client, _ = api
    created = client.post(
        "/api/clients/1/fixation/m07/eligibility-date-revisions",
        json={"eligibility_date": "2026-04-15"},
    )
    revision_id = created.json()["revision_id"]
    payload = _fixation_payload(revision_id)

    validated = client.post("/api/clients/1/fixation/validate", json=payload)
    calculated = client.post("/api/clients/1/fixation/calculate", json=payload)
    saved = client.post(
        "/api/fixation/save",
        json={"client_id": 1, "input_data": payload},
    )

    assert validated.status_code == 200
    assert validated.json()["status"] == "success"
    assert validated.json()["eligibility_date"] == "2026-04-15"
    assert validated.json()["eligibility_year"] == 2026
    assert calculated.status_code == 200
    assert calculated.json()["status"] == "success"
    assert saved.status_code == 200
    assert saved.json()["status"] == "success"
    assert saved.json()["created_at"]

    detail = client.get(
        f"/api/clients/1/fixation/runs/{saved.json()['run_id']}"
    )
    assert detail.status_code == 200
    assert saved.json()["created_at"] == detail.json()["run"]["created_at"]
    snapshot = detail.json()["input_snapshot"]
    assert snapshot["m07_input_reference"] == {
        "b1_evidence_revision_id": revision_id,
        "selections": [],
    }
    assert snapshot["eligibility_date"] == "2026-04-15"
    assert snapshot["eligibility_year"] == 2026
    assert snapshot["m07_resolution"]["outcome"] == "resolved"
    assert snapshot["m07_resolution"]["b1_evidence_revision_id"] == revision_id
    assert snapshot["m07_resolution"]["fingerprint"]
    assert detail.json()["result"]["status"] == "success"
    assert detail.json()["audit_rows"]


def test_missing_m07_stops_before_cbs_and_engine(
    api: tuple[TestClient, sessionmaker],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, session_local = api
    with session_local() as session:
        revision_id = _seed_missing_revision(session, client_id=1)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("CBS and engine must not run for missing M07 input")

    monkeypatch.setattr(
        "app.services.fixation_admission_service.calculate_cbs_indexation",
        forbidden,
    )
    monkeypatch.setattr(
        "app.services.fixation_service.calculate_fixation_engine",
        forbidden,
    )

    response = client.post(
        "/api/clients/1/fixation/validate",
        json=_fixation_payload(revision_id),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "validation_failed"
    assert response.json()["m07_resolution"]["outcome"] == "missing_inputs"
    assert response.json()["m07_resolution"]["missing_fields"] == [
        "eligibility_date"
    ]


def test_ambiguous_selection_is_explicit_and_persisted(
    api: tuple[TestClient, sessionmaker],
) -> None:
    client, session_local = api
    with session_local() as session:
        revision_id, _ = seed_eligibility_revision(
            session,
            client_id=1,
            eligibility_dates=("2026-01-01", "2026-02-01"),
        )
        session.commit()

    ambiguous = client.post(
        "/api/clients/1/fixation/validate",
        json=_fixation_payload(revision_id),
    )
    assert ambiguous.json()["m07_resolution"]["outcome"] == "ambiguous_inputs"
    candidate = ambiguous.json()["m07_resolution"]["ambiguous_fields"][0][
        "candidates"
    ][1]
    selection = {
        "field_code": "eligibility_date",
        "candidate_identity": candidate["candidate_identities"][0],
        "b1_evidence_revision_id": revision_id,
    }
    selected_payload = _fixation_payload(
        revision_id,
        selections=[selection],
    )
    selected = client.post(
        "/api/clients/1/fixation/calculate",
        json=selected_payload,
    )
    saved = client.post(
        "/api/fixation/save",
        json={"client_id": 1, "input_data": selected_payload},
    )

    assert selected.json()["status"] == "success"
    assert selected.json()["eligibility_date"] == candidate["normalized_value"]
    detail = client.get(
        f"/api/clients/1/fixation/runs/{saved.json()['run_id']}"
    ).json()
    persisted_selection = detail["input_snapshot"]["m07_input_reference"][
        "selections"
    ][0]
    assert {
        key: persisted_selection[key]
        for key in (
            "field_code",
            "candidate_identity",
            "b1_evidence_revision_id",
        )
    } == selection
    assert detail["input_snapshot"]["m07_resolution"]["outcome"] == "resolved"


def test_resolved_m07_does_not_bypass_parameter_gate(
    api: tuple[TestClient, sessionmaker],
) -> None:
    client, session_local = api
    with session_local() as session:
        revision_id, _ = seed_eligibility_revision(
            session,
            client_id=1,
            eligibility_dates=("2026-01-01",),
        )
        session.commit()

    response = client.post(
        "/api/clients/1/fixation/validate",
        json=_fixation_payload(revision_id, parameter_accepted=False),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "validation_failed"
    assert any(
        error["path"] == "parameter_set.accepted_for_use"
        for error in response.json()["validation_errors"]
    )
