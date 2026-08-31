from __future__ import annotations

import json
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, event, inspect, select, text, update
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base, load_all_models
from app.db.session import get_db
from app.main import app
from app.models.client import Client
from app.models.m02_intake import (
    M02IntakeRecord,
    M02PreservedBlob,
    M02PreservedSource,
)
from app.models.m04_classification import (
    M04ClassificationRevision,
    M04ClassificationSubject,
    M04ComponentDecision,
)
from app.services.m03_review_service import decide_review, start_review
from app.services.m04_classification_service import _aggregate, _row_digest
from app.services.m04_rule_catalogue import ExactRule, evaluate_exact_catalogue


def _m02(
    *,
    intake_id: str,
    client_id: int,
    reference: str,
    product_type: str | None = None,
    components: list[dict] | None = None,
) -> M02IntakeRecord:
    return M02IntakeRecord(
        intake_id=intake_id,
        client_id=client_id,
        record_kind="manual",
        manual_technical_reference=reference,
        declared_provider_name="Persisted Provider",
        product_name="Persisted Product",
        declared_product_type=product_type,
        declared_component_values=components,
        source_type="manual",
        lifecycle_status="accepted_for_review",
        preservation_status="not_applicable",
        diagnostics=[],
        created_by_actor="m02",
        updated_by_actor="m02",
        lifecycle_decided_by_actor="m02",
    )


@pytest.fixture
def api(tmp_path: Path) -> Generator[tuple[TestClient, sessionmaker[Session]], None, None]:
    load_all_models()
    engine = create_engine(f"sqlite:///{tmp_path / 'pkg009.db'}")

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    with sessions() as db:
        db.add_all(
            [
                Client(
                    client_id=1,
                    display_name="One",
                    id_number="001",
                    status="delivered",
                ),
                Client(
                    client_id=2,
                    display_name="Two",
                    id_number="002",
                    status="delivered",
                ),
                _m02(
                    intake_id="manual-1",
                    client_id=1,
                    reference="M02-MANUAL-1",
                    product_type="provident_fund",
                    components=[
                        {
                            "label": "תגמולים",
                            "code": "contribution_component",
                            "value": "100.00",
                        }
                    ],
                ),
                _m02(
                    intake_id="manual-2",
                    client_id=2,
                    reference="M02-MANUAL-2",
                    product_type="provident_fund",
                    components=[
                        {
                            "label": "תגמולים",
                            "code": "contribution_component",
                            "value": "200.00",
                        }
                    ],
                ),
                M02IntakeRecord(
                    intake_id="upload-1",
                    client_id=1,
                    record_kind="uploaded_source",
                    source_type="clearinghouse",
                    lifecycle_status="accepted_for_review",
                    preservation_status="preserved",
                    diagnostics=[],
                    created_by_actor="m02",
                    updated_by_actor="m02",
                    lifecycle_decided_by_actor="m02",
                ),
                M02PreservedBlob(
                    blob_id="blob-1",
                    client_id=1,
                    storage_key="objects/aa/file",
                    sha256_checksum="a" * 64,
                    byte_size=10,
                    validated_media_type="application/pdf",
                ),
            ]
        )
        db.flush()
        db.add(
            M02PreservedSource(
                source_id="source-1",
                client_id=1,
                intake_id="upload-1",
                blob_id="blob-1",
                original_filename="provident_fund-secret.pdf",
                sanitized_download_filename="source.pdf",
                normalized_extension=".pdf",
                declared_mime_type="application/pdf",
                validated_media_type="application/pdf",
                source_type="clearinghouse",
                byte_size=10,
                preservation_status="preserved",
                validation_diagnostics=[],
            )
        )
        db.commit()
        for client_id, intake_id in (
            (1, "manual-1"),
            (2, "manual-2"),
            (1, "upload-1"),
        ):
            root = start_review(db, client_id, intake_id)
            decide_review(
                db,
                client_id,
                intake_id,
                "accepted",
                "accepted M03 evidence",
                root.revision_id,
            )

    def override():
        with sessions() as db:
            yield db

    app.dependency_overrides[get_db] = override
    try:
        yield TestClient(app), sessions
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def _reason(expected: str, explanation: str = "explicit planner action") -> dict:
    return {
        "expected_current_revision_id": expected,
        "reason_code": "planner_decision",
        "explanation": explanation,
    }


def _override_payload(revision: dict, *, interpretation: str = "pension") -> dict:
    component = revision["components"][0]
    return {
        **_reason(revision["revision_id"], "complete planner-authored override"),
        "confirmed": True,
        "product_family": "provident_fund",
        "pension_subtype": None,
        "components": [
            {
                "evidence_identity": component["evidence_identity"],
                "component_kind": "contribution_component",
                "interpretation": interpretation,
                "current_employer_related": "unknown",
                "explanation": "planner selected the bounded component meaning",
            }
        ],
    }


def _accepted_classification(client: TestClient) -> tuple[dict, dict, dict, dict]:
    started = client.post("/api/clients/1/m04/targets/manual-1/start").json()
    proposal = client.post(
        "/api/clients/1/m04/targets/manual-1/proposal",
        json={"expected_current_revision_id": started["revision_id"]},
    ).json()
    override = client.post(
        "/api/clients/1/m04/targets/manual-1/override",
        json=_override_payload(proposal),
    ).json()
    accepted_response = client.post(
        "/api/clients/1/m04/targets/manual-1/accept",
        json=_reason(override["revision_id"], "explicit acceptance"),
    )
    assert accepted_response.status_code == 201
    return started, proposal, override, accepted_response.json()


def test_candidates_preview_and_exact_catalogue_are_read_only(api) -> None:
    client, sessions = api
    targets = client.get("/api/clients/1/m04/targets")
    assert targets.status_code == 200
    assert {row["intake_id"] for row in targets.json()} == {"manual-1", "upload-1"}

    first = client.get("/api/clients/1/m04/targets/manual-1/preview")
    second = client.get("/api/clients/1/m04/targets/manual-1/preview")
    assert first.status_code == second.status_code == 200
    preview = first.json()
    assert preview["catalogue_version"] == "m04-rules-v1"
    assert preview["product_family"] == "provident_fund"
    assert preview["components"][0]["component_kind"] == "contribution_component"
    assert preview["components"][0]["interpretation"] == "unresolved"
    assert preview["persists_revision"] is False
    with sessions() as db:
        assert db.scalar(text("SELECT COUNT(*) FROM m04_classification_revisions")) == 0


def test_start_proposal_override_accept_and_m05_gate(api) -> None:
    client, _ = api
    started, proposal, override, accepted = _accepted_classification(client)
    assert [started["state"], proposal["state"], override["state"], accepted["state"]] == [
        "under_review",
        "proposed",
        "proposed",
        "accepted",
    ]
    assert proposal["catalogue_version"] == "m04-rules-v1"
    assert proposal["match_basis"] == "exact_rule_catalogue"
    assert override["match_basis"] == "planner_authored_override"
    assert override["aggregate_interpretation"] == "pension"
    assert override["action_evidence"]["old_values"]
    assert override["action_evidence"]["new_values"]
    eligibility = client.get(
        "/api/clients/1/m04/targets/manual-1/eligibility"
    ).json()
    assert eligibility["eligible_for_m05"] is True
    assert eligibility["accepted_revision_id"] == accepted["revision_id"]
    assert "separately authorized M05" in eligibility["meaning"]


def test_incomplete_proposal_cannot_be_accepted(api) -> None:
    client, _ = api
    started = client.post("/api/clients/1/m04/targets/manual-1/start").json()
    proposal = client.post(
        "/api/clients/1/m04/targets/manual-1/proposal",
        json={"expected_current_revision_id": started["revision_id"]},
    ).json()
    response = client.post(
        "/api/clients/1/m04/targets/manual-1/accept",
        json=_reason(proposal["revision_id"]),
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "M04_CLASSIFICATION_INCOMPLETE"


def test_override_reject_and_undo_never_reactivate_old_authority(api) -> None:
    client, _ = api
    _, _, _, accepted = _accepted_classification(client)
    override = client.post(
        "/api/clients/1/m04/targets/manual-1/override",
        json=_override_payload(accepted, interpretation="capital"),
    )
    assert override.status_code == 201
    assert client.get(
        "/api/clients/1/m04/targets/manual-1/eligibility"
    ).json()["exclusion_reason"] == "classification_proposed"
    rejected = client.post(
        "/api/clients/1/m04/targets/manual-1/reject",
        json=_reason(override.json()["revision_id"], "reject override"),
    ).json()
    assert client.get(
        "/api/clients/1/m04/targets/manual-1/eligibility"
    ).json()["exclusion_reason"] == "classification_rejected"
    undo = client.post(
        "/api/clients/1/m04/targets/manual-1/undo",
        json={
            **_reason(rejected["revision_id"], "re-propose historical values"),
            "confirmed": True,
            "historical_revision_id": accepted["revision_id"],
        },
    )
    assert undo.status_code == 201
    assert undo.json()["state"] == "proposed"
    assert undo.json()["historical_revision_id"] == accepted["revision_id"]
    assert client.get(
        "/api/clients/1/m04/targets/manual-1/eligibility"
    ).json()["eligible_for_m05"] is False


def test_unresolved_reopen_and_prohibited_transitions(api) -> None:
    client, _ = api
    started = client.post("/api/clients/1/m04/targets/upload-1/start").json()
    no_mapping = client.post(
        "/api/clients/1/m04/targets/upload-1/proposal",
        json={"expected_current_revision_id": started["revision_id"]},
    )
    assert no_mapping.status_code == 409
    assert no_mapping.json()["detail"]["code"] == "M04_NO_EXACT_MAPPING"
    unresolved = client.post(
        "/api/clients/1/m04/targets/upload-1/unresolved",
        json=_reason(started["revision_id"], "opaque uploaded facts unavailable"),
    )
    assert unresolved.status_code == 201
    assert unresolved.json()["state"] == "unresolved"
    assert "opaque_uploaded_facts_unavailable" in unresolved.json()["action_evidence"]["unresolved_reasons"]
    opaque_eligibility = client.get(
        "/api/clients/1/m04/targets/upload-1/eligibility"
    ).json()
    assert opaque_eligibility["eligible_for_m05"] is False
    assert (
        opaque_eligibility["exclusion_reason"]
        == "opaque_uploaded_facts_unavailable"
    )
    reopened = client.post(
        "/api/clients/1/m04/targets/upload-1/reopen",
        json=_reason(unresolved.json()["revision_id"], "review again"),
    )
    assert reopened.status_code == 201
    assert reopened.json()["state"] == "under_review"
    assert reopened.json()["components"] == []
    assert client.post(
        "/api/clients/1/m04/targets/upload-1/accept",
        json=_reason(reopened.json()["revision_id"]),
    ).status_code == 409
    assert client.post(
        "/api/clients/1/m04/targets/upload-1/override",
        json={
            **_reason(reopened.json()["revision_id"]),
            "confirmed": True,
            "product_family": "provident_fund",
            "components": [],
        },
    ).status_code == 409


def test_archive_reopen_requires_fresh_revalidation_acceptance(api) -> None:
    client, sessions = api
    _, _, _, accepted = _accepted_classification(client)
    with sessions() as db:
        case = db.get(Client, 1)
        case.status = "archived"
        db.commit()
    assert client.get(
        "/api/clients/1/m04/targets/manual-1/eligibility"
    ).json()["exclusion_reason"] == "archived_case"
    assert client.post(
        "/api/clients/1/m04/targets/manual-1/reopen",
        json=_reason(accepted["revision_id"]),
    ).json()["detail"]["code"] == "M04_ARCHIVED_CASE_READ_ONLY"

    with sessions() as db:
        case = db.get(Client, 1)
        case.status = "delivered"
        db.commit()
    assert client.get(
        "/api/clients/1/m04/targets/manual-1/eligibility"
    ).json()["exclusion_reason"] == "m04_revalidation_required"
    revalidation = client.post(
        "/api/clients/1/m04/targets/manual-1/start-revalidation",
        json=_reason(accepted["revision_id"], "case reopened"),
    )
    assert revalidation.status_code == 201
    assert revalidation.json()["state"] == "under_review"
    assert revalidation.json()["action_type"] == "start_revalidation"
    proposal = client.post(
        "/api/clients/1/m04/targets/manual-1/proposal",
        json={"expected_current_revision_id": revalidation.json()["revision_id"]},
    )
    assert proposal.status_code == 201
    override = client.post(
        "/api/clients/1/m04/targets/manual-1/override",
        json=_override_payload(proposal.json()),
    )
    assert override.status_code == 201
    accepted_again = client.post(
        "/api/clients/1/m04/targets/manual-1/accept",
        json=_reason(override.json()["revision_id"], "accept revalidated proposal"),
    )
    assert accepted_again.status_code == 201
    assert client.get(
        "/api/clients/1/m04/targets/manual-1/eligibility"
    ).json()["eligible_for_m05"] is True


def test_m03_invalidation_is_read_time_and_does_not_mutate_m04(api) -> None:
    client, sessions = api
    _accepted_classification(client)
    history_before = client.get(
        "/api/clients/1/m04/targets/manual-1/history"
    ).json()
    with sessions() as db:
        current_m03 = db.execute(
            text(
                "SELECT revision_id FROM m03_review_revisions "
                "WHERE intake_id='manual-1' ORDER BY revision_sequence DESC LIMIT 1"
            )
        ).scalar_one()
        decide_review(
            db, 1, "manual-1", "reopen", "M03 reopened", current_m03
        )
    eligibility = client.get(
        "/api/clients/1/m04/targets/manual-1/eligibility"
    ).json()
    assert eligibility["eligible_for_m05"] is False
    assert eligibility["exclusion_reason"] == "m03_ineligible"
    assert client.get(
        "/api/clients/1/m04/targets/manual-1/history"
    ).json() == history_before


def test_material_m02_change_preserves_history_and_requires_m03_m04_rereview(api) -> None:
    client, sessions = api
    _, _, _, accepted_a = _accepted_classification(client)
    history_a = client.get(
        "/api/clients/1/m04/targets/manual-1/history"
    ).json()
    m03_a = client.get(
        "/api/clients/1/m03/targets/manual-1"
    ).json()["current_revision"]

    client.post(
        "/api/clients/1/m02/intakes/manual-1/lifecycle",
        json={"target_status": "metadata_review"},
    ).raise_for_status()
    client.put(
        "/api/clients/1/m02/intakes/manual-1",
        json={
            "declared_statement_date": "2026-07-01",
            "declared_total_balance_amount": "1000.00",
            "declared_component_values": [
                {"label": "Updated contributions", "value": "1000.00"}
            ],
        },
    ).raise_for_status()
    client.post(
        "/api/clients/1/m02/intakes/manual-1/lifecycle",
        json={"target_status": "accepted_for_review"},
    ).raise_for_status()

    m03_stale = client.get(
        "/api/clients/1/m03/targets/manual-1/eligibility"
    ).json()
    assert m03_stale["eligible"] is False
    assert m03_stale["exclusion_reason"] == "upstream_m02_evidence_changed"
    m04_stale = client.get(
        "/api/clients/1/m04/targets/manual-1/eligibility"
    ).json()
    assert m04_stale["eligible_for_m05"] is False
    assert m04_stale["exclusion_reason"] == "m03_ineligible"
    retained = client.get(
        "/api/clients/1/m04/targets/manual-1"
    ).json()
    assert retained["current_revision"]["revision_id"] == accepted_a["revision_id"]
    assert client.get(
        "/api/clients/1/m04/targets/manual-1/history"
    ).json() == history_a
    blocked = client.post(
        "/api/clients/1/m04/targets/manual-1/reopen",
        json=_reason(accepted_a["revision_id"], "cannot reuse old authority"),
    )
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["code"] == "M04_M03_INELIGIBLE"

    reopened_m03 = client.post(
        "/api/clients/1/m03/targets/manual-1/reopen",
        json={
            "reason": "review updated M02 evidence",
            "expected_current_revision_id": m03_a["revision_id"],
        },
    ).json()
    accepted_m03_b = client.post(
        "/api/clients/1/m03/targets/manual-1/accept",
        json={
            "reason": "accept updated M02 evidence",
            "expected_current_revision_id": reopened_m03["revision_id"],
        },
    ).json()
    still_stale = client.get(
        "/api/clients/1/m04/targets/manual-1/eligibility"
    ).json()
    assert still_stale["eligible_for_m05"] is False
    assert still_stale["exclusion_reason"] == "m04_revalidation_required"
    assert still_stale["m03_revision_id"] == accepted_m03_b["revision_id"]

    reopened_m04 = client.post(
        "/api/clients/1/m04/targets/manual-1/start-revalidation",
        json=_reason(accepted_a["revision_id"], "classify version B"),
    ).json()
    assert reopened_m04["action_type"] == "start_revalidation"
    assert (
        reopened_m04["input_snapshot"]["accepted_m03_revision_id"]
        == accepted_m03_b["revision_id"]
    )
    proposal_b = client.post(
        "/api/clients/1/m04/targets/manual-1/proposal",
        json={"expected_current_revision_id": reopened_m04["revision_id"]},
    ).json()
    override_b = client.post(
        "/api/clients/1/m04/targets/manual-1/override",
        json=_override_payload(proposal_b),
    ).json()
    accepted_b = client.post(
        "/api/clients/1/m04/targets/manual-1/accept",
        json=_reason(override_b["revision_id"], "accept version B"),
    )
    assert accepted_b.status_code == 201
    assert client.get(
        "/api/clients/1/m04/targets/manual-1/eligibility"
    ).json()["eligible_for_m05"] is True
    history_b = client.get(
        "/api/clients/1/m04/targets/manual-1/history"
    ).json()
    assert history_b[: len(history_a)] == history_a
    with sessions() as db:
        historical = db.get(M04ClassificationRevision, accepted_a["revision_id"])
        assert historical.state == "accepted"
        assert historical.input_snapshot == history_a[-1]["input_snapshot"]


def test_old_m04_proposal_cannot_be_accepted_after_material_m02_change(api) -> None:
    client, _sessions = api
    started = client.post("/api/clients/1/m04/targets/manual-1/start").json()
    proposal = client.post(
        "/api/clients/1/m04/targets/manual-1/proposal",
        json={"expected_current_revision_id": started["revision_id"]},
    ).json()
    history_before = client.get(
        "/api/clients/1/m04/targets/manual-1/history"
    ).json()
    client.post(
        "/api/clients/1/m02/intakes/manual-1/lifecycle",
        json={"target_status": "metadata_review"},
    ).raise_for_status()
    client.put(
        "/api/clients/1/m02/intakes/manual-1",
        json={"declared_statement_date": "2026-07-01"},
    ).raise_for_status()
    client.post(
        "/api/clients/1/m02/intakes/manual-1/lifecycle",
        json={"target_status": "accepted_for_review"},
    ).raise_for_status()
    response = client.post(
        "/api/clients/1/m04/targets/manual-1/accept",
        json=_reason(proposal["revision_id"], "stale acceptance"),
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "M04_M03_INELIGIBLE"
    assert client.get(
        "/api/clients/1/m04/targets/manual-1/history"
    ).json() == history_before


def test_stale_proposed_can_start_append_only_revalidation_against_current_m03(api) -> None:
    client, _sessions = api
    started = client.post("/api/clients/1/m04/targets/manual-1/start").json()
    proposal_a = client.post(
        "/api/clients/1/m04/targets/manual-1/proposal",
        json={"expected_current_revision_id": started["revision_id"]},
    ).json()
    m03_a = client.get(
        "/api/clients/1/m03/targets/manual-1"
    ).json()["current_revision"]
    client.post(
        "/api/clients/1/m02/intakes/manual-1/lifecycle",
        json={"target_status": "metadata_review"},
    ).raise_for_status()
    client.put(
        "/api/clients/1/m02/intakes/manual-1",
        json={
            "declared_statement_date": "2026-07-01",
            "declared_account_reference": "A-001",
            "declared_total_balance_amount": "1000.00",
            "declared_component_values": [
                {"label": "Updated contributions", "value": "1000.00"}
            ],
        },
    ).raise_for_status()
    client.post(
        "/api/clients/1/m02/intakes/manual-1/lifecycle",
        json={"target_status": "accepted_for_review"},
    ).raise_for_status()
    reopened_m03 = client.post(
        "/api/clients/1/m03/targets/manual-1/reopen",
        json={
            "reason": "review current evidence",
            "expected_current_revision_id": m03_a["revision_id"],
        },
    ).json()
    accepted_m03_b = client.post(
        "/api/clients/1/m03/targets/manual-1/accept",
        json={
            "reason": "accept current evidence",
            "expected_current_revision_id": reopened_m03["revision_id"],
        },
    ).json()

    gate = client.get(
        "/api/clients/1/m04/targets/manual-1/eligibility"
    ).json()
    assert gate["exclusion_reason"] == "m04_revalidation_required"
    m05_candidate = next(
        row
        for row in client.get("/api/clients/1/m05/candidates").json()
        if row["intake_id"] == "manual-1"
    )
    assert m05_candidate["eligible"] is False
    assert m05_candidate["exclusion_reason"] == "upstream_revalidation_required"
    for action in ("accept", "reject"):
        blocked = client.post(
            f"/api/clients/1/m04/targets/manual-1/{action}",
            json=_reason(proposal_a["revision_id"], "stale decision is forbidden"),
        )
        assert blocked.status_code == 409
        assert blocked.json()["detail"]["code"] == "M04_REVALIDATION_REQUIRED"

    history_before = client.get(
        "/api/clients/1/m04/targets/manual-1/history"
    ).json()
    revalidation = client.post(
        "/api/clients/1/m04/targets/manual-1/start-revalidation",
        json=_reason(proposal_a["revision_id"], "bind classification to current M03"),
    )
    assert revalidation.status_code == 201
    current = revalidation.json()
    assert current["state"] == "under_review"
    assert current["action_type"] == "start_revalidation"
    assert current["predecessor_revision_id"] == proposal_a["revision_id"]
    assert current["historical_revision_id"] == proposal_a["revision_id"]
    assert (
        current["input_snapshot"]["accepted_m03_revision_id"]
        == accepted_m03_b["revision_id"]
    )
    assert current["components"] == []
    history_after = client.get(
        "/api/clients/1/m04/targets/manual-1/history"
    ).json()
    assert history_after[:-1] == history_before
    assert history_after[-1]["revision_id"] == current["revision_id"]
    preview = client.get(
        "/api/clients/1/m04/targets/manual-1/preview"
    )
    assert preview.status_code == 200
    assert client.get(
        "/api/clients/1/m04/targets/manual-1/eligibility"
    ).json()["eligible_for_m05"] is False


def test_foreign_ids_and_caller_forgery_are_rejected(api) -> None:
    client, _ = api
    foreign = client.get("/api/clients/2/m04/targets/manual-1")
    missing = client.get("/api/clients/2/m04/targets/missing")
    assert foreign.status_code == missing.status_code == 404
    assert foreign.json() == missing.json()
    forged = client.post(
        "/api/clients/1/m04/targets/manual-1/start",
        json={
            "actor": "human",
            "catalogue_version": "forged",
            "eligible_for_m05": True,
        },
    )
    assert forged.status_code == 422
    with_body = client.post(
        "/api/clients/1/m04/targets/manual-1/proposal",
        json={
            "expected_current_revision_id": "forged",
            "rule_ids": ["forged"],
            "accepted": True,
        },
    )
    assert with_body.status_code == 422


def test_ordinary_orm_update_delete_and_direct_insert_are_blocked(api) -> None:
    client, sessions = api
    _accepted_classification(client)
    with sessions() as db:
        revision = db.scalar(select(M04ClassificationRevision))
        revision.explanation = "mutated"
        with pytest.raises(ValueError, match="immutable"):
            db.commit()
        db.rollback()
    with sessions() as db:
        component = db.scalar(select(M04ComponentDecision))
        db.delete(component)
        with pytest.raises(ValueError, match="cannot be deleted"):
            db.commit()
        db.rollback()
    with sessions() as db:
        subject = db.scalar(select(M04ClassificationSubject))
        forged = M04ClassificationRevision(
            revision_id="forged",
            subject_id=subject.subject_id,
            client_id=1,
            intake_id="manual-1",
            target_kind="manual_record_review",
            m03_revision_id="forged",
            revision_sequence=99,
            state="accepted",
            action_type="accept",
            input_snapshot={},
            catalogue_version="m04-rules-v1",
            matched_rule_evidence=[],
            match_basis="forged",
            action_evidence={},
            evidence_digest="0" * 64,
            actor="forged",
        )
        db.add(forged)
        with pytest.raises(ValueError, match="only by the M04 service"):
            db.commit()


@pytest.mark.parametrize(
    ("model", "field", "value"),
    [
        (M04ClassificationRevision, "explanation", "bulk rewrite"),
        (M04ClassificationRevision, "revision_sequence", 999),
        (M04ClassificationRevision, "predecessor_revision_id", "forged"),
        (M04ClassificationRevision, "input_snapshot", {"forged": True}),
        (M04ClassificationRevision, "matched_rule_evidence", []),
        (M04ComponentDecision, "explanation", "bulk component rewrite"),
    ],
)
def test_bulk_update_of_immutable_m04_rows_is_blocked(
    api, model, field: str, value
) -> None:
    client, sessions = api
    _accepted_classification(client)
    with sessions() as db:
        before = db.scalar(select(model))
        before_value = getattr(before, field)
        with pytest.raises(ValueError, match="bulk updated or deleted"):
            db.execute(update(model).values({field: value}))
        db.rollback()
    with sessions() as db:
        after = db.scalar(select(model))
        assert getattr(after, field) == before_value


@pytest.mark.parametrize(
    "model", [M04ClassificationRevision, M04ComponentDecision]
)
def test_bulk_delete_of_immutable_m04_rows_is_blocked(api, model) -> None:
    client, sessions = api
    _accepted_classification(client)
    with sessions() as db:
        before = db.scalar(select(model))
        before_id = inspect(before).identity
        with pytest.raises(ValueError, match="bulk updated or deleted"):
            db.execute(delete(model))
        db.rollback()
    with sessions() as db:
        assert db.get(model, before_id) is not None


def test_bulk_alias_and_synchronize_session_variants_are_blocked(api) -> None:
    client, sessions = api
    _accepted_classification(client)
    revision_alias = M04ClassificationRevision.__table__.alias("revision_alias")
    with sessions() as db:
        with pytest.raises(ValueError, match="bulk updated or deleted"):
            db.execute(update(revision_alias).values(explanation="alias rewrite"))
        db.rollback()
        with pytest.raises(ValueError, match="bulk updated or deleted"):
            db.execute(
                delete(M04ComponentDecision),
                execution_options={"synchronize_session": False},
            )
        db.rollback()


def test_instance_component_update_and_revision_delete_are_blocked(api) -> None:
    client, sessions = api
    _accepted_classification(client)
    with sessions() as db:
        component = db.scalar(select(M04ComponentDecision))
        original = component.explanation
        component.explanation = "instance rewrite"
        with pytest.raises(ValueError, match="immutable"):
            db.flush()
        db.rollback()
    with sessions() as db:
        assert db.scalar(select(M04ComponentDecision)).explanation == original
        revision = db.scalar(select(M04ClassificationRevision))
        revision_id = revision.revision_id
        db.delete(revision)
        with pytest.raises(ValueError, match="cannot be deleted"):
            db.flush()
        db.rollback()
    with sessions() as db:
        assert db.get(M04ClassificationRevision, revision_id) is not None


def test_parent_delete_and_arbitrary_subject_update_are_blocked(api) -> None:
    client, sessions = api
    _accepted_classification(client)
    with sessions() as db:
        subject = db.scalar(select(M04ClassificationSubject))
        subject_id = subject.subject_id
        db.delete(subject)
        with pytest.raises(ValueError, match="cannot be deleted"):
            db.flush()
        db.rollback()
        with pytest.raises(ValueError, match="bulk updated or deleted"):
            db.execute(
                update(M04ClassificationSubject).values(archive_generation=99)
            )
        db.rollback()
    with sessions() as db:
        subject = db.get(M04ClassificationSubject, subject_id)
        assert subject is not None
        assert subject.archive_generation == 0
        assert db.scalar(select(M04ClassificationRevision)) is not None


def test_controlled_archive_generation_and_unrelated_bulk_dml_remain_allowed(api) -> None:
    client, sessions = api
    _accepted_classification(client)
    with sessions() as db:
        db.add(Client(client_id=3, display_name="Disposable", id_number="003"))
        db.commit()
        db.execute(update(Client).where(Client.client_id == 3).values(display_name="Updated"))
        db.commit()
    with sessions() as db:
        assert db.get(Client, 3).display_name == "Updated"
        db.execute(delete(Client).where(Client.client_id == 3))
        db.commit()
    with sessions() as db:
        assert db.get(Client, 3) is None
        client_row = db.get(Client, 1)
        client_row.status = "archived"
        db.commit()
    with sessions() as db:
        subject = db.scalar(select(M04ClassificationSubject))
        assert subject.archive_generation == 1


def test_raw_sql_corruption_fails_eligibility_closed(api) -> None:
    client, sessions = api
    _accepted_classification(client)
    with sessions() as db:
        db.execute(
            text(
                "UPDATE m04_classification_revisions "
                "SET evidence_digest = :digest WHERE state = 'accepted'"
            ),
            {"digest": "0" * 64},
        )
        db.commit()
    response = client.get(
        "/api/clients/1/m04/targets/manual-1/eligibility"
    )
    assert response.status_code == 200
    assert response.json()["eligible_for_m05"] is False
    assert response.json()["exclusion_reason"] == "malformed_classification_chain"


def _redigest_accepted(db: Session) -> None:
    db.expire_all()
    accepted = db.scalar(
        select(M04ClassificationRevision).where(
            M04ClassificationRevision.state == "accepted"
        )
    )
    assert accepted is not None
    components = list(
        db.scalars(
            select(M04ComponentDecision).where(
                M04ComponentDecision.revision_id == accepted.revision_id
            )
        )
    )
    digest = _row_digest(accepted, components)
    db.connection().exec_driver_sql(
        "UPDATE m04_classification_revisions SET evidence_digest = ? "
        "WHERE revision_id = ?",
        (digest, accepted.revision_id),
    )
    db.commit()


def _add_corrupt_component(
    db: Session, *, interpretation: str, update_snapshot: bool = True
) -> None:
    accepted = db.scalar(
        select(M04ClassificationRevision).where(
            M04ClassificationRevision.state == "accepted"
        )
    )
    assert accepted is not None
    identity = "component:corrupt:second"
    db.connection().exec_driver_sql(
        "INSERT INTO m04_component_decisions "
        "(component_decision_id, revision_id, client_id, intake_id, target_kind, "
        "evidence_identity, original_label, original_code, component_kind, "
        "interpretation, matched_rule_evidence, explanation, "
        "current_employer_related, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
        (
            "M04-C-corrupt-second",
            accepted.revision_id,
            accepted.client_id,
            accepted.intake_id,
            accepted.target_kind,
            identity,
            "Second component",
            "severance_component",
            "severance_component",
            interpretation,
            "[]",
            "corruption fixture",
            "unknown",
        ),
    )
    if update_snapshot:
        snapshot = dict(accepted.input_snapshot)
        snapshot["components"] = [
            *snapshot.get("components", []),
            {
                "evidence_identity": identity,
                "original_label": "Second component",
                "original_code": "severance_component",
                "declared_value": "50.00",
                "current_employer_related": "unknown",
            },
        ]
        db.connection().exec_driver_sql(
            "UPDATE m04_classification_revisions SET input_snapshot = ? "
            "WHERE revision_id = ?",
            (json.dumps(snapshot), accepted.revision_id),
        )


@pytest.mark.parametrize(
    "case",
    [
        "pension_aggregate_all_capital",
        "capital_aggregate_all_pension",
        "mixed_aggregate_all_same",
        "nonmixed_aggregate_mixed_components",
        "component_interpretation_mixed",
        "accepted_unresolved_component",
        "missing_component",
        "inconsistent_evidence_identity",
        "component_set_changed_with_redigest",
        "aggregate_changed_with_redigest",
    ],
)
def test_aggregate_corruption_matrix_fails_closed(api, case: str) -> None:
    client, sessions = api
    _accepted_classification(client)
    with sessions() as db:
        connection = db.connection()
        if case == "pension_aggregate_all_capital":
            connection.exec_driver_sql(
                "UPDATE m04_component_decisions SET interpretation = 'capital' "
                "WHERE revision_id IN (SELECT revision_id FROM "
                "m04_classification_revisions WHERE state = 'accepted')"
            )
        elif case in {"capital_aggregate_all_pension", "aggregate_changed_with_redigest"}:
            connection.exec_driver_sql(
                "UPDATE m04_classification_revisions SET aggregate_interpretation = 'capital' "
                "WHERE state = 'accepted'"
            )
        elif case == "mixed_aggregate_all_same":
            connection.exec_driver_sql(
                "UPDATE m04_classification_revisions SET aggregate_interpretation = 'mixed' "
                "WHERE state = 'accepted'"
            )
        elif case == "nonmixed_aggregate_mixed_components":
            _add_corrupt_component(db, interpretation="capital")
        elif case == "component_interpretation_mixed":
            connection.exec_driver_sql("PRAGMA ignore_check_constraints = ON")
            connection.exec_driver_sql(
                "UPDATE m04_component_decisions SET interpretation = 'mixed' "
                "WHERE revision_id IN (SELECT revision_id FROM "
                "m04_classification_revisions WHERE state = 'accepted')"
            )
        elif case == "accepted_unresolved_component":
            connection.exec_driver_sql(
                "UPDATE m04_component_decisions SET interpretation = 'unresolved' "
                "WHERE revision_id IN (SELECT revision_id FROM "
                "m04_classification_revisions WHERE state = 'accepted')"
            )
        elif case == "missing_component":
            connection.exec_driver_sql(
                "DELETE FROM m04_component_decisions WHERE revision_id IN "
                "(SELECT revision_id FROM m04_classification_revisions "
                "WHERE state = 'accepted')"
            )
        elif case == "inconsistent_evidence_identity":
            connection.exec_driver_sql(
                "UPDATE m04_component_decisions SET evidence_identity = 'forged-identity' "
                "WHERE revision_id IN (SELECT revision_id FROM "
                "m04_classification_revisions WHERE state = 'accepted')"
            )
        elif case == "component_set_changed_with_redigest":
            _add_corrupt_component(
                db, interpretation="pension", update_snapshot=False
            )
        _redigest_accepted(db)
    result = client.get(
        "/api/clients/1/m04/targets/manual-1/eligibility"
    )
    assert result.status_code == 200
    assert result.json()["eligible_for_m05"] is False
    assert result.json()["accepted_revision_id"] is None
    assert result.json()["exclusion_reason"] == "malformed_classification_chain"
    detail = client.get("/api/clients/1/m04/targets/manual-1")
    assert detail.status_code == 409
    assert detail.json()["detail"]["code"] in {
        "M04_CLASSIFICATION_CHAIN_INCONSISTENT",
        "M04_COMPONENT_EVIDENCE_INCONSISTENT",
    }


def test_authoritative_aggregate_derivation_positive_cases() -> None:
    assert _aggregate([{"interpretation": "pension"}]) == "pension"
    assert _aggregate([{"interpretation": "capital"}]) == "capital"
    assert _aggregate(
        [{"interpretation": "pension"}, {"interpretation": "capital"}]
    ) == "mixed"
    assert _aggregate([]) == "unresolved"
    assert _aggregate([{"interpretation": "unresolved"}]) == "unresolved"


@pytest.mark.parametrize(
    "case",
    [
        "duplicate_identical_identity",
        "duplicate_conflicting_interpretation",
        "duplicate_conflicting_label",
        "duplicate_conflicting_code",
        "duplicate_with_malformed_payload",
        "missing_identity",
        "empty_identity",
        "non_string_identity",
        "snapshot_count_greater_than_rows",
        "snapshot_count_less_than_rows",
        "two_snapshot_identities_for_one_row",
        "unknown_malformed_entry",
    ],
)
def test_raw_snapshot_component_multiplicity_fails_closed(api, case: str) -> None:
    client, sessions = api
    _accepted_classification(client)
    with sessions() as db:
        revision_ids_before = tuple(
            db.scalars(
                select(M04ClassificationRevision.revision_id).order_by(
                    M04ClassificationRevision.revision_sequence
                )
            )
        )
        accepted = db.scalar(
            select(M04ClassificationRevision).where(
                M04ClassificationRevision.state == "accepted"
            )
        )
        assert accepted is not None
        snapshot = json.loads(json.dumps(accepted.input_snapshot))
        components = snapshot["components"]
        original = dict(components[0])
        if case == "duplicate_identical_identity":
            components.append(dict(original))
        elif case == "duplicate_conflicting_interpretation":
            components.append({**original, "interpretation": "capital"})
        elif case == "duplicate_conflicting_label":
            components.append({**original, "original_label": "Conflicting label"})
        elif case == "duplicate_conflicting_code":
            components.append({**original, "original_code": "conflicting_code"})
        elif case == "duplicate_with_malformed_payload":
            components.append({"evidence_identity": original["evidence_identity"]})
        elif case == "missing_identity":
            components[0] = {key: value for key, value in original.items()
                             if key != "evidence_identity"}
        elif case == "empty_identity":
            components[0] = {**original, "evidence_identity": ""}
        elif case == "non_string_identity":
            components[0] = {**original, "evidence_identity": 123}
        elif case == "snapshot_count_greater_than_rows":
            components.append({**original, "evidence_identity": "extra-identity"})
        elif case == "snapshot_count_less_than_rows":
            snapshot["components"] = []
        elif case == "two_snapshot_identities_for_one_row":
            components.append({**original, "evidence_identity": "second-identity"})
        elif case == "unknown_malformed_entry":
            components.append("malformed-entry")
        db.connection().exec_driver_sql(
            "UPDATE m04_classification_revisions SET input_snapshot = ? "
            "WHERE revision_id = ?",
            (json.dumps(snapshot), accepted.revision_id),
        )
        _redigest_accepted(db)
    detail = client.get("/api/clients/1/m04/targets/manual-1")
    assert detail.status_code == 409
    assert detail.json()["detail"]["code"] == "M04_CLASSIFICATION_CHAIN_INCONSISTENT"
    eligibility = client.get(
        "/api/clients/1/m04/targets/manual-1/eligibility"
    )
    assert eligibility.status_code == 200
    assert eligibility.json()["eligible_for_m05"] is False
    assert eligibility.json()["accepted_revision_id"] is None
    assert eligibility.json()["exclusion_reason"] == "malformed_classification_chain"
    with sessions() as db:
        assert tuple(
            db.scalars(
                select(M04ClassificationRevision.revision_id).order_by(
                    M04ClassificationRevision.revision_sequence
                )
            )
        ) == revision_ids_before


@pytest.mark.parametrize("aggregate", ["pension", "capital", "mixed"])
def test_valid_snapshot_component_one_to_one_positive_controls(api, aggregate: str) -> None:
    client, sessions = api
    _accepted_classification(client)
    with sessions() as db:
        connection = db.connection()
        if aggregate == "capital":
            connection.exec_driver_sql(
                "UPDATE m04_component_decisions SET interpretation = 'capital' "
                "WHERE revision_id IN (SELECT revision_id FROM "
                "m04_classification_revisions WHERE state = 'accepted')"
            )
            connection.exec_driver_sql(
                "UPDATE m04_classification_revisions "
                "SET aggregate_interpretation = 'capital' WHERE state = 'accepted'"
            )
        elif aggregate == "mixed":
            _add_corrupt_component(db, interpretation="capital")
            connection.exec_driver_sql(
                "UPDATE m04_classification_revisions "
                "SET aggregate_interpretation = 'mixed' WHERE state = 'accepted'"
            )
        _redigest_accepted(db)
    detail = client.get("/api/clients/1/m04/targets/manual-1")
    assert detail.status_code == 200
    assert detail.json()["current_revision"]["aggregate_interpretation"] == aggregate
    eligibility = client.get(
        "/api/clients/1/m04/targets/manual-1/eligibility"
    ).json()
    assert eligibility["eligible_for_m05"] is True
    assert eligibility["accepted_revision_id"] is not None


def test_accept_rejects_semantically_inconsistent_proposal(api) -> None:
    client, sessions = api
    started = client.post("/api/clients/1/m04/targets/manual-1/start").json()
    proposal = client.post(
        "/api/clients/1/m04/targets/manual-1/proposal",
        json={"expected_current_revision_id": started["revision_id"]},
    ).json()
    override = client.post(
        "/api/clients/1/m04/targets/manual-1/override",
        json=_override_payload(proposal),
    ).json()
    with sessions() as db:
        db.connection().exec_driver_sql(
            "UPDATE m04_classification_revisions SET aggregate_interpretation = 'capital' "
            "WHERE revision_id = ?",
            (override["revision_id"],),
        )
        db.expire_all()
        row = db.get(M04ClassificationRevision, override["revision_id"])
        components = list(
            db.scalars(
                select(M04ComponentDecision).where(
                    M04ComponentDecision.revision_id == row.revision_id
                )
            )
        )
        digest = _row_digest(row, components)
        db.connection().exec_driver_sql(
            "UPDATE m04_classification_revisions SET evidence_digest = ? "
            "WHERE revision_id = ?",
            (digest, row.revision_id),
        )
        db.commit()
    rejected = client.post(
        "/api/clients/1/m04/targets/manual-1/accept",
        json=_reason(override["revision_id"]),
    )
    assert rejected.status_code == 409
    assert rejected.json()["detail"]["code"] == "M04_CLASSIFICATION_CHAIN_INCONSISTENT"


def test_invalid_rule_evidence_has_stable_exclusion(api) -> None:
    client, sessions = api
    _accepted_classification(client)
    with sessions() as db:
        db.execute(
            text(
                "UPDATE m04_classification_revisions "
                "SET matched_rule_evidence = :evidence WHERE state = 'accepted'"
            ),
            {"evidence": '[{"rule_id":"caller-forged-rule"}]'},
        )
        db.commit()
    invalid_rule = client.get(
        "/api/clients/1/m04/targets/manual-1/eligibility"
    ).json()
    assert invalid_rule["eligible_for_m05"] is False
    assert invalid_rule["exclusion_reason"] == "invalid_rule_evidence"


def test_inconsistent_provenance_has_stable_exclusion(api) -> None:
    client, sessions = api
    _accepted_classification(client)
    with sessions() as db:
        accepted = db.scalar(
            select(M04ClassificationRevision).where(
                M04ClassificationRevision.state == "accepted"
            )
        )
        assert accepted is not None
        snapshot = dict(accepted.input_snapshot)
        snapshot["client_id"] = 999
        db.execute(
            text(
                "UPDATE m04_classification_revisions "
                "SET input_snapshot = :snapshot WHERE state = 'accepted'"
            ),
            {"snapshot": json.dumps(snapshot)},
        )
        db.commit()
    inconsistent = client.get(
        "/api/clients/1/m04/targets/manual-1/eligibility"
    ).json()
    assert inconsistent["eligible_for_m05"] is False
    assert (
        inconsistent["exclusion_reason"]
        == "foreign_or_inconsistent_provenance"
    )


def test_concurrent_start_is_atomic(api) -> None:
    client, sessions = api

    def start_once() -> int:
        return client.post(
            "/api/clients/1/m04/targets/manual-1/start"
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = sorted(pool.map(lambda _index: start_once(), range(2)))
    assert statuses == [201, 409]
    with sessions() as db:
        assert db.scalar(
            text("SELECT COUNT(*) FROM m04_classification_subjects")
        ) == 1
        assert db.scalar(
            text("SELECT COUNT(*) FROM m04_classification_revisions")
        ) == 1


def test_vocabularies_and_forbidden_scope_are_closed(api) -> None:
    client, _ = api
    started = client.post("/api/clients/1/m04/targets/manual-1/start").json()
    proposal = client.post(
        "/api/clients/1/m04/targets/manual-1/proposal",
        json={"expected_current_revision_id": started["revision_id"]},
    ).json()
    payload = _override_payload(proposal)
    payload["product_family"] = "severance_component"
    assert client.post(
        "/api/clients/1/m04/targets/manual-1/override", json=payload
    ).status_code == 422
    payload = _override_payload(proposal)
    payload["components"][0]["component_kind"] = "compensation_component"
    assert client.post(
        "/api/clients/1/m04/targets/manual-1/override", json=payload
    ).status_code == 422
    payload = _override_payload(proposal)
    payload["pension_subtype"] = "old_pension_fund"
    response = client.post(
        "/api/clients/1/m04/targets/manual-1/override", json=payload
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "M04_PENSION_SUBTYPE_UNSUPPORTED"


def test_rule_catalogue_has_no_provider_partial_or_fuzzy_fallback() -> None:
    result = evaluate_exact_catalogue(
        {
            "target_kind": "manual_record_review",
            "declared_provider_name": "provident_fund",
            "declared_product_type": "provident_fund extra",
            "components": [
                {
                    "evidence_identity": "component:0:test",
                    "original_label": "תגמולים extra",
                    "original_code": "contribution",
                    "current_employer_related": "unknown",
                }
            ],
        }
    )
    assert result["product_family"] == "unknown_or_unresolved"
    assert result["components"][0]["component_kind"] == "unknown_component"
    assert result["matched_rule_evidence"] == []


def test_conflicting_exact_rules_fail_unresolved_without_latest_wins() -> None:
    common = {
        "matcher_type": "declared_product_type_exact",
        "exact_matcher_value": "provident_fund",
        "scope": "asset",
        "output_component_kind": None,
        "output_interpretation": None,
        "rationale": "test-only exact conflict",
        "authority_reference": "test fixture",
    }
    result = evaluate_exact_catalogue(
        {
            "target_kind": "manual_record_review",
            "declared_product_type": "provident_fund",
            "components": [],
        },
        catalogue=(
            ExactRule(
                rule_id="test.rule.one",
                output_product_family="provident_fund",
                **common,
            ),
            ExactRule(
                rule_id="test.rule.two",
                output_product_family="savings_policy",
                **common,
            ),
        ),
    )
    assert result["product_family"] == "unknown_or_unresolved"
    assert result["conflicts"] == ["conflicting_exact_asset_rules"]


def test_component_rule_never_classifies_parent_asset() -> None:
    result = evaluate_exact_catalogue(
        {
            "target_kind": "manual_record_review",
            "declared_product_type": None,
            "components": [
                {
                    "evidence_identity": "component:0:test",
                    "original_label": "תגמולים",
                    "original_code": None,
                    "current_employer_related": "unknown",
                }
            ],
        }
    )
    assert result["product_family"] == "unknown_or_unresolved"
    assert result["components"][0]["component_kind"] == "contribution_component"
