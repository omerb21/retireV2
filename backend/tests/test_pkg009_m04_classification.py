from __future__ import annotations

import json
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select, text
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
