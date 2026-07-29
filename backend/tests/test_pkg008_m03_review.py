from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base, load_all_models
from app.db.session import get_db
from app.main import app
from app.models.client import Client
from app.models.m02_intake import M02IntakeRecord, M02PreservedBlob, M02PreservedSource
from app.models.m03_review import M03Annotation, M03ReviewRevision


@pytest.fixture
def api(tmp_path: Path) -> Generator[tuple[TestClient, sessionmaker[Session]], None, None]:
    load_all_models()
    engine = create_engine(f"sqlite:///{tmp_path / 'pkg008.db'}")

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    with sessions() as db:
        db.add_all([
            Client(client_id=1, display_name="One", id_number="001", status="delivered"),
            Client(client_id=2, display_name="Two", id_number="002", status="delivered"),
            M02IntakeRecord(
                intake_id="manual-1", client_id=1, record_kind="manual",
                manual_technical_reference="M02-MANUAL-1", source_type="manual",
                lifecycle_status="accepted_for_review", preservation_status="not_applicable",
                diagnostics=[], created_by_actor="m02", updated_by_actor="m02",
                lifecycle_decided_by_actor="m02",
            ),
            M02IntakeRecord(
                intake_id="manual-2", client_id=2, record_kind="manual",
                manual_technical_reference="M02-MANUAL-2", source_type="manual",
                lifecycle_status="accepted_for_review", preservation_status="not_applicable",
                diagnostics=[], created_by_actor="m02", updated_by_actor="m02",
                lifecycle_decided_by_actor="m02",
            ),
            M02IntakeRecord(
                intake_id="upload-1", client_id=1, record_kind="uploaded_source",
                source_type="clearinghouse", lifecycle_status="accepted_for_review",
                preservation_status="preserved", diagnostics=[], created_by_actor="m02",
                updated_by_actor="m02", lifecycle_decided_by_actor="m02",
            ),
            M02PreservedBlob(
                blob_id="blob-1", client_id=1, storage_key="objects/aa/file",
                sha256_checksum="a" * 64, byte_size=10,
                validated_media_type="application/pdf",
            ),
        ])
        db.flush()
        db.add(M02PreservedSource(
            source_id="source-1", client_id=1, intake_id="upload-1", blob_id="blob-1",
            original_filename="source.pdf", sanitized_download_filename="source.pdf",
            normalized_extension=".pdf", declared_mime_type="application/pdf",
            validated_media_type="application/pdf", source_type="clearinghouse",
            byte_size=10, preservation_status="preserved", validation_diagnostics=[],
        ))
        db.commit()

    def override():
        with sessions() as db:
            yield db

    app.dependency_overrides[get_db] = override
    try:
        yield TestClient(app), sessions
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def test_candidate_reads_are_side_effect_free_and_target_kinds_are_exact(api) -> None:
    client, sessions = api
    first = client.get("/api/clients/1/m03/candidates")
    second = client.get("/api/clients/1/m03/candidates")
    assert first.status_code == second.status_code == 200
    rows = {row["intake_id"]: row for row in first.json()}
    assert rows["manual-1"]["target_kind"] == "manual_record_review"
    assert rows["manual-1"]["source_id"] is None
    assert rows["manual-1"]["blob_id"] is None
    assert rows["manual-1"]["sha256_checksum"] is None
    assert rows["upload-1"]["target_kind"] == "source_evidence_review"
    assert rows["upload-1"]["source_id"] == "source-1"
    assert rows["upload-1"]["blob_id"] == "blob-1"
    with sessions() as db:
        assert db.scalar(text("SELECT COUNT(*) FROM m03_review_revisions")) == 0


def test_append_only_accept_reopen_and_eligibility(api) -> None:
    client, sessions = api
    started = client.post("/api/clients/1/m03/targets/manual-1/start")
    assert started.status_code == 201
    root = started.json()
    assert root["state"] == "under_review"
    assert client.get("/api/clients/1/m03/targets/manual-1/eligibility").json()["eligible"] is False

    accepted = client.post("/api/clients/1/m03/targets/manual-1/accept", json={
        "reason": "reviewed source-level record",
        "expected_current_revision_id": root["revision_id"],
        "actor": "forged",
    })
    assert accepted.status_code == 422
    accepted = client.post("/api/clients/1/m03/targets/manual-1/accept", json={
        "reason": "reviewed source-level record",
        "expected_current_revision_id": root["revision_id"],
    })
    assert accepted.status_code == 201
    terminal = accepted.json()
    eligible = client.get("/api/clients/1/m03/targets/manual-1/eligibility").json()
    assert eligible["eligible"] is True
    assert eligible["accepted_revision_id"] == terminal["revision_id"]

    stale = client.post("/api/clients/1/m03/targets/manual-1/reopen", json={
        "reason": "new review needed", "expected_current_revision_id": root["revision_id"],
    })
    assert stale.status_code == 409
    reopened = client.post("/api/clients/1/m03/targets/manual-1/reopen", json={
        "reason": "new review needed", "expected_current_revision_id": terminal["revision_id"],
    })
    assert reopened.status_code == 201
    assert reopened.json()["state"] == "under_review"
    assert client.get("/api/clients/1/m03/targets/manual-1/eligibility").json()["eligible"] is False
    history = client.get("/api/clients/1/m03/targets/manual-1/history").json()
    assert [row["state"] for row in history] == ["under_review", "accepted", "under_review"]
    assert [row["revision_sequence"] for row in history] == [1, 2, 3]
    with sessions() as db:
        root_row = db.get(M03ReviewRevision, root["revision_id"])
        terminal_row = db.get(M03ReviewRevision, terminal["revision_id"])
        assert root_row.state == "under_review"
        assert terminal_row.state == "accepted"


def test_rejection_m02_exclusion_annotations_and_archived_mutations(api) -> None:
    client, sessions = api
    root = client.post("/api/clients/1/m03/targets/upload-1/start").json()
    rejected = client.post("/api/clients/1/m03/targets/upload-1/reject", json={
        "reason": "not accepted", "expected_current_revision_id": root["revision_id"],
    }).json()
    annotation = client.post("/api/clients/1/m03/targets/upload-1/annotations", json={
        "review_revision_id": rejected["revision_id"], "topic": "history",
        "note": "historical note", "reason": "retain context",
    })
    assert annotation.status_code == 201
    assert client.get("/api/clients/1/m03/targets/upload-1/eligibility").json()["exclusion_reason"] == "review_rejected"
    with sessions() as db:
        intake = db.get(M02IntakeRecord, "upload-1")
        intake.lifecycle_status = "superseded"
        db.commit()
        assert db.scalar(select(M03Annotation)).note == "historical note"
    assert client.get("/api/clients/1/m03/targets/upload-1/eligibility").json()["exclusion_reason"] == "m02_superseded"
    with sessions() as db:
        db.get(Client, 1).status = "archived"
        db.commit()
    blocked = client.post("/api/clients/1/m03/targets/upload-1/annotations", json={
        "review_revision_id": rejected["revision_id"], "topic": "x", "note": "x", "reason": "x",
    })
    assert blocked.status_code == 409
    assert client.get("/api/clients/1/m03/targets/upload-1/history").status_code == 200


def test_foreign_ids_are_indistinguishable_and_create_no_rows(api) -> None:
    client, sessions = api
    missing = client.get("/api/clients/1/m03/targets/no-such")
    foreign = client.get("/api/clients/1/m03/targets/manual-2")
    assert missing.status_code == foreign.status_code == 404
    assert missing.json() == foreign.json()
    assert client.post("/api/clients/1/m03/targets/manual-2/start").json() == foreign.json()
    with sessions() as db:
        assert db.scalar(text("SELECT COUNT(*) FROM m03_review_revisions")) == 0
