from __future__ import annotations

from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base, load_all_models
from app.db.session import get_db
from app.main import app
from app.models.client import Client
from app.models.m02_intake import M02IntakeRecord, M02PreservedBlob, M02PreservedSource
from app.models.m03_review import M03Annotation, M03ReviewRevision
from app.services.m03_review_service import ACTOR, m02_evidence_digest


def _revision_snapshot(row: M03ReviewRevision) -> dict[str, object]:
    return {
        column.name: getattr(row, column.name)
        for column in M03ReviewRevision.__table__.columns
    }


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
                declared_provider_name="Provider One", product_name="Product One",
                declared_account_reference="Account One",
                lifecycle_status="accepted_for_review", preservation_status="not_applicable",
                diagnostics=[], created_by_actor="m02", updated_by_actor="m02",
                lifecycle_decided_by_actor="m02",
            ),
            M02IntakeRecord(
                intake_id="manual-2", client_id=2, record_kind="manual",
                manual_technical_reference="M02-MANUAL-2", source_type="manual",
                declared_provider_name="Provider Two", product_name="Product Two",
                declared_account_reference="Account Two",
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
        "decided_at": "2000-01-01T00:00:00Z",
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


def test_material_m02_change_invalidates_authority_until_explicit_rereview(api) -> None:
    client, sessions = api
    root = client.post("/api/clients/1/m03/targets/manual-1/start").json()
    accepted_a = client.post(
        "/api/clients/1/m03/targets/manual-1/accept",
        json={
            "reason": "accepted version A",
            "expected_current_revision_id": root["revision_id"],
        },
    ).json()
    other_root = client.post("/api/clients/2/m03/targets/manual-2/start").json()
    client.post(
        "/api/clients/2/m03/targets/manual-2/accept",
        json={
            "reason": "other client accepted",
            "expected_current_revision_id": other_root["revision_id"],
        },
    ).raise_for_status()
    history_a = client.get(
        "/api/clients/1/m03/targets/manual-1/history"
    ).json()

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
                {"label": "Contributions", "value": "1000.00"}
            ],
        },
    ).raise_for_status()
    client.post(
        "/api/clients/1/m02/intakes/manual-1/lifecycle",
        json={"target_status": "accepted_for_review"},
    ).raise_for_status()

    stale = client.get(
        "/api/clients/1/m03/targets/manual-1/eligibility"
    ).json()
    assert stale["eligible"] is False
    assert stale["exclusion_reason"] == "upstream_m02_evidence_changed"
    assert stale["accepted_revision_id"] is None
    assert client.get(
        "/api/clients/1/m03/targets/manual-1/history"
    ).json() == history_a
    assert client.get(
        "/api/clients/2/m03/targets/manual-2/eligibility"
    ).json()["eligible"] is True

    reopened = client.post(
        "/api/clients/1/m03/targets/manual-1/reopen",
        json={
            "reason": "review version B",
            "expected_current_revision_id": accepted_a["revision_id"],
        },
    ).json()
    accepted_b_response = client.post(
        "/api/clients/1/m03/targets/manual-1/accept",
        json={
            "reason": "accepted version B",
            "expected_current_revision_id": reopened["revision_id"],
        },
    )
    assert accepted_b_response.status_code == 201
    accepted_b = accepted_b_response.json()
    restored = client.get(
        "/api/clients/1/m03/targets/manual-1/eligibility"
    ).json()
    assert restored["eligible"] is True
    assert restored["accepted_revision_id"] == accepted_b["revision_id"]
    with sessions() as db:
        old = db.get(M03ReviewRevision, accepted_a["revision_id"])
        new = db.get(M03ReviewRevision, accepted_b["revision_id"])
        assert old.state == "accepted"
        assert old.reason == "accepted version A"
        assert old.m02_evidence_digest != new.m02_evidence_digest


def test_stale_under_review_recovers_append_only_before_explicit_decision(api) -> None:
    client, sessions = api
    started = client.post("/api/clients/1/m03/targets/manual-1/start").json()
    with sessions() as db:
        original = db.get(M03ReviewRevision, started["revision_id"])
        original_snapshot = _revision_snapshot(original)

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
                {"label": "Contributions", "value": "1000.00"}
            ],
        },
    ).raise_for_status()
    client.post(
        "/api/clients/1/m02/intakes/manual-1/lifecycle",
        json={"target_status": "accepted_for_review"},
    ).raise_for_status()

    stale = client.get(
        "/api/clients/1/m03/targets/manual-1/eligibility"
    ).json()
    assert stale["eligible"] is False
    assert stale["exclusion_reason"] == "upstream_m02_evidence_changed"
    for action in ("accept", "reject"):
        blocked = client.post(
            f"/api/clients/1/m03/targets/manual-1/{action}",
            json={
                "reason": f"must not {action} stale evidence",
                "expected_current_revision_id": started["revision_id"],
            },
        )
        assert blocked.status_code == 409
        assert blocked.json()["detail"]["code"] == "M03_UPSTREAM_EVIDENCE_CHANGED"

    recovered_response = client.post(
        "/api/clients/1/m03/targets/manual-1/reopen",
        json={
            "reason": "review current version B evidence",
            "expected_current_revision_id": started["revision_id"],
        },
    )
    assert recovered_response.status_code == 201
    recovered = recovered_response.json()
    assert recovered["state"] == "under_review"
    assert recovered["revision_sequence"] == 2
    assert recovered["predecessor_revision_id"] == started["revision_id"]
    active = client.get(
        "/api/clients/1/m03/targets/manual-1/eligibility"
    ).json()
    assert active["eligible"] is False
    assert active["exclusion_reason"] == "review_under_review"

    accepted = client.post(
        "/api/clients/1/m03/targets/manual-1/accept",
        json={
            "reason": "explicitly accepted version B",
            "expected_current_revision_id": recovered["revision_id"],
        },
    )
    assert accepted.status_code == 201
    restored = client.get(
        "/api/clients/1/m03/targets/manual-1/eligibility"
    ).json()
    assert restored["eligible"] is True
    assert restored["accepted_revision_id"] == accepted.json()["revision_id"]
    with sessions() as db:
        original = db.get(M03ReviewRevision, started["revision_id"])
        recovered_row = db.get(M03ReviewRevision, recovered["revision_id"])
        assert _revision_snapshot(original) == original_snapshot
        assert recovered_row.m02_evidence_digest is not None
        assert recovered_row.m02_evidence_digest != original.m02_evidence_digest


def test_legacy_null_digest_under_review_recovers_without_backfill(api) -> None:
    client, sessions = api
    with sessions() as db:
        legacy = M03ReviewRevision(
            revision_id="server-replaces-this-id",
            client_id=1,
            target_kind="manual_record_review",
            intake_id="manual-1",
            source_id=None,
            predecessor_revision_id=None,
            revision_sequence=1,
            state="under_review",
            reason=None,
            m02_evidence_digest=None,
            actor=ACTOR,
            decided_at=datetime.now(timezone.utc),
        )
        db.add(legacy)
        db.commit()
        db.refresh(legacy)
        legacy_id = legacy.revision_id
        legacy_snapshot = _revision_snapshot(legacy)

    history = client.get("/api/clients/1/m03/targets/manual-1/history")
    assert history.status_code == 200
    assert [row["revision_id"] for row in history.json()] == [legacy_id]
    stale = client.get(
        "/api/clients/1/m03/targets/manual-1/eligibility"
    ).json()
    assert stale["eligible"] is False
    assert stale["exclusion_reason"] == "upstream_m02_evidence_changed"
    for action in ("accept", "reject"):
        blocked = client.post(
            f"/api/clients/1/m03/targets/manual-1/{action}",
            json={
                "reason": "legacy evidence requires current review",
                "expected_current_revision_id": legacy_id,
            },
        )
        assert blocked.status_code == 409
        assert blocked.json()["detail"]["code"] == "M03_UPSTREAM_EVIDENCE_CHANGED"

    recovered_response = client.post(
        "/api/clients/1/m03/targets/manual-1/reopen",
        json={
            "reason": "bind a fresh review to current evidence",
            "expected_current_revision_id": legacy_id,
        },
    )
    assert recovered_response.status_code == 201
    recovered = recovered_response.json()
    assert recovered["state"] == "under_review"
    assert recovered["revision_sequence"] == 2
    assert recovered["predecessor_revision_id"] == legacy_id
    accepted = client.post(
        "/api/clients/1/m03/targets/manual-1/accept",
        json={
            "reason": "explicit current-evidence acceptance",
            "expected_current_revision_id": recovered["revision_id"],
        },
    )
    assert accepted.status_code == 201
    assert client.get(
        "/api/clients/1/m03/targets/manual-1/eligibility"
    ).json()["eligible"] is True
    with sessions() as db:
        legacy = db.get(M03ReviewRevision, legacy_id)
        recovered_row = db.get(M03ReviewRevision, recovered["revision_id"])
        accepted_row = db.get(M03ReviewRevision, accepted.json()["revision_id"])
        assert _revision_snapshot(legacy) == legacy_snapshot
        assert legacy.m02_evidence_digest is None
        assert recovered_row.m02_evidence_digest is not None
        assert recovered_row.predecessor_revision_id == legacy_id
        assert accepted_row.predecessor_revision_id == recovered_row.revision_id
        assert [legacy.revision_sequence, recovered_row.revision_sequence,
                accepted_row.revision_sequence] == [1, 2, 3]


def test_current_evidence_under_review_cannot_reopen_into_generic_loop(api) -> None:
    client, sessions = api
    started = client.post("/api/clients/1/m03/targets/manual-1/start").json()
    blocked = client.post(
        "/api/clients/1/m03/targets/manual-1/reopen",
        json={
            "reason": "must not create an ordinary under-review loop",
            "expected_current_revision_id": started["revision_id"],
        },
    )
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["code"] == "M03_WRONG_CURRENT_STATE"
    with sessions() as db:
        root = db.get(M03ReviewRevision, started["revision_id"])
        db.add(M03ReviewRevision(
            revision_id="server-replaces-this-id",
            client_id=root.client_id,
            target_kind=root.target_kind,
            intake_id=root.intake_id,
            source_id=root.source_id,
            predecessor_revision_id=root.revision_id,
            revision_sequence=2,
            state="under_review",
            reason="attempt generic loop",
            m02_evidence_digest=root.m02_evidence_digest,
            actor=ACTOR,
            decided_at=datetime.now(timezone.utc),
        ))
        with pytest.raises(ValueError, match="lifecycle transition is invalid"):
            db.commit()
        db.rollback()
        rows = list(db.scalars(select(M03ReviewRevision)).all())
        assert len(rows) == 1
        assert rows[0].revision_id == started["revision_id"]


def test_m02_evidence_digest_canonicalization_and_material_inputs(api) -> None:
    _client, sessions = api
    with sessions() as db:
        manual = db.get(M02IntakeRecord, "manual-1")
        manual.notes = "קצבה – café"
        manual.declared_total_balance_amount = Decimal("1000.0")
        manual.declared_component_values = [
            {"label": "Alpha", "value": "600.00"},
            {"label": "Beta", "value": "400.00"},
        ]
        db.commit()
        db.expire_all()
        manual = db.get(M02IntakeRecord, "manual-1")
        persisted = m02_evidence_digest(manual, "manual_record_review", None)
        assert persisted == m02_evidence_digest(
            manual, "manual_record_review", None
        )

        manual.declared_component_values = [
            {"value": "600.00", "label": "Alpha"},
            {"value": "400.00", "label": "Beta"},
        ]
        key_reordered = m02_evidence_digest(
            manual, "manual_record_review", None
        )
        assert key_reordered == persisted

        manual.declared_total_balance_amount = Decimal("1000.00")
        db.commit()
        db.expire_all()
        manual = db.get(M02IntakeRecord, "manual-1")
        assert m02_evidence_digest(
            manual, "manual_record_review", None
        ) == persisted

        manual.declared_statement_date = date(2026, 7, 1)
        assert m02_evidence_digest(
            manual, "manual_record_review", None
        ) != persisted
        manual.declared_statement_date = None
        manual.declared_component_values = [
            {"label": "Beta", "value": "400.00"},
            {"label": "Alpha", "value": "600.00"},
        ]
        assert m02_evidence_digest(
            manual, "manual_record_review", None
        ) != persisted

        uploaded = db.get(M02IntakeRecord, "upload-1")
        source = db.get(M02PreservedSource, "source-1")
        source_digest = m02_evidence_digest(
            uploaded, "source_evidence_review", source
        )
        source.original_filename = "מקור.pdf"
        db.commit()
        db.expire_all()
        uploaded = db.get(M02IntakeRecord, "upload-1")
        source = db.get(M02PreservedSource, "source-1")
        renamed_digest = m02_evidence_digest(
            uploaded, "source_evidence_review", source
        )
        assert renamed_digest != source_digest

        replacement_blob = M02PreservedBlob(
            blob_id="blob-2",
            client_id=1,
            storage_key="objects/bb/file",
            sha256_checksum="b" * 64,
            byte_size=11,
            validated_media_type="application/pdf",
        )
        db.add(replacement_blob)
        source.blob = replacement_blob
        source.blob_id = replacement_blob.blob_id
        db.commit()
        db.expire_all()
        uploaded = db.get(M02IntakeRecord, "upload-1")
        source = db.get(M02PreservedSource, "source-1")
        assert m02_evidence_digest(
            uploaded, "source_evidence_review", source
        ) != renamed_digest


def test_lifecycle_only_round_trip_does_not_change_m02_evidence_authority(api) -> None:
    client, _sessions = api
    root = client.post("/api/clients/1/m03/targets/manual-1/start").json()
    client.post(
        "/api/clients/1/m03/targets/manual-1/accept",
        json={
            "reason": "accepted evidence",
            "expected_current_revision_id": root["revision_id"],
        },
    ).raise_for_status()
    client.post(
        "/api/clients/1/m02/intakes/manual-1/lifecycle",
        json={"target_status": "metadata_review"},
    ).raise_for_status()
    assert client.get(
        "/api/clients/1/m03/targets/manual-1/eligibility"
    ).json()["exclusion_reason"] == "m02_metadata_review"
    client.post(
        "/api/clients/1/m02/intakes/manual-1/lifecycle",
        json={"target_status": "accepted_for_review"},
    ).raise_for_status()
    eligibility = client.get(
        "/api/clients/1/m03/targets/manual-1/eligibility"
    ).json()
    assert eligibility["eligible"] is True
    assert eligibility["exclusion_reason"] is None


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


@pytest.mark.parametrize("reason", ["", "   ", "\t", "\n", " \t\r\n "])
@pytest.mark.parametrize("action", ["accept", "reject"])
def test_decision_reasons_reject_all_whitespace_without_partial_writes(api, reason: str, action: str) -> None:
    client, sessions = api
    root = client.post("/api/clients/1/m03/targets/manual-1/start").json()
    response = client.post(f"/api/clients/1/m03/targets/manual-1/{action}", json={
        "reason": reason,
        "expected_current_revision_id": root["revision_id"],
    })
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] in {"value_error", "string_too_short"}
    with sessions() as db:
        assert db.scalar(text("SELECT COUNT(*) FROM m03_review_revisions")) == 1


def test_reopen_and_annotation_reasons_are_trimmed_and_blank_is_atomic(api) -> None:
    client, sessions = api
    root = client.post("/api/clients/1/m03/targets/manual-1/start").json()
    accepted = client.post("/api/clients/1/m03/targets/manual-1/accept", json={
        "reason": "  reviewed  ",
        "expected_current_revision_id": root["revision_id"],
    }).json()
    assert accepted["reason"] == "reviewed"
    blank_reopen = client.post("/api/clients/1/m03/targets/manual-1/reopen", json={
        "reason": "\t\n ",
        "expected_current_revision_id": accepted["revision_id"],
    })
    assert blank_reopen.status_code == 422
    blank_annotation = client.post("/api/clients/1/m03/targets/manual-1/annotations", json={
        "review_revision_id": accepted["revision_id"],
        "topic": "topic",
        "note": "note",
        "reason": "\r\n\t",
    })
    assert blank_annotation.status_code == 422
    annotation = client.post("/api/clients/1/m03/targets/manual-1/annotations", json={
        "review_revision_id": accepted["revision_id"],
        "topic": "  topic  ",
        "note": "  note  ",
        "reason": "  context  ",
    }).json()
    assert (annotation["topic"], annotation["note"], annotation["reason"]) == ("topic", "note", "context")
    with sessions() as db:
        assert db.scalar(text("SELECT COUNT(*) FROM m03_review_revisions")) == 2
        assert db.scalar(text("SELECT COUNT(*) FROM m03_annotations")) == 1


def test_ordinary_orm_insert_replaces_caller_owned_ids_and_timestamps(api) -> None:
    _client_api, sessions = api
    caller_timestamp = datetime(2000, 1, 1, tzinfo=timezone.utc)
    with sessions() as db:
        revision = M03ReviewRevision(
            revision_id="caller-chosen-root",
            client_id=1,
            target_kind="manual_record_review",
            intake_id="manual-1",
            source_id=None,
            predecessor_revision_id=None,
            revision_sequence=1,
            state="under_review",
            reason=None,
            actor=ACTOR,
            decided_at=caller_timestamp,
        )
        db.add(revision)
        db.commit()
        db.refresh(revision)
        assert revision.revision_id != "caller-chosen-root"
        assert revision.revision_id.startswith("M03-R-")
        assert revision.decided_at.replace(tzinfo=timezone.utc) > caller_timestamp

        annotation = M03Annotation(
            annotation_id="caller-chosen-note",
            client_id=1,
            intake_id="manual-1",
            source_id=None,
            review_revision_id=revision.revision_id,
            topic="topic",
            note="note",
            reason="reason",
            actor=ACTOR,
            created_at=caller_timestamp,
        )
        db.add(annotation)
        db.commit()
        db.refresh(annotation)
        assert annotation.annotation_id != "caller-chosen-note"
        assert annotation.annotation_id.startswith("M03-A-")
        assert annotation.created_at.replace(tzinfo=timezone.utc) > caller_timestamp
        assert db.get(M03ReviewRevision, "caller-chosen-root") is None
        assert db.get(M03Annotation, "caller-chosen-note") is None


def test_revision_and_annotation_orm_update_and_delete_are_blocked(api) -> None:
    client, sessions = api
    root = client.post("/api/clients/1/m03/targets/manual-1/start").json()
    accepted = client.post("/api/clients/1/m03/targets/manual-1/accept", json={
        "reason": "accepted",
        "expected_current_revision_id": root["revision_id"],
    }).json()
    annotation = client.post("/api/clients/1/m03/targets/manual-1/annotations", json={
        "review_revision_id": accepted["revision_id"],
        "topic": "topic",
        "note": "note",
        "reason": "reason",
    }).json()

    revision_changes = {
        "revision_id": "forged-revision",
        "client_id": 2,
        "target_kind": "source_evidence_review",
        "intake_id": "manual-2",
        "source_id": "source-1",
        "predecessor_revision_id": root["revision_id"],
        "revision_sequence": 99,
        "state": "rejected",
        "reason": "changed",
        "actor": "forged",
        "decided_at": datetime(2000, 1, 1, tzinfo=timezone.utc),
    }
    annotation_changes = {
        "annotation_id": "forged-annotation",
        "client_id": 2,
        "intake_id": "manual-2",
        "source_id": "source-1",
        "review_revision_id": root["revision_id"],
        "topic": "changed",
        "note": "changed",
        "reason": "changed",
        "actor": "forged",
        "supersedes_annotation_id": annotation["annotation_id"],
        "created_at": datetime(2000, 1, 1, tzinfo=timezone.utc),
    }
    for model, row_id, changes in (
        (M03ReviewRevision, accepted["revision_id"], revision_changes),
        (M03Annotation, annotation["annotation_id"], annotation_changes),
    ):
        for field, value in changes.items():
            with sessions() as db:
                row = db.get(model, row_id)
                setattr(row, field, value)
                with pytest.raises(ValueError, match="immutable"):
                    db.commit()
                db.rollback()
        with sessions() as db:
            row = db.get(model, row_id)
            db.delete(row)
            with pytest.raises(ValueError, match="cannot be deleted"):
                db.commit()
            db.rollback()

    with sessions() as db:
        revision = db.get(M03ReviewRevision, accepted["revision_id"])
        note = db.get(M03Annotation, annotation["annotation_id"])
        assert revision.state == "accepted"
        assert revision.reason == "accepted"
        assert note.topic == "topic"
        assert note.note == "note"
    reopened = client.post("/api/clients/1/m03/targets/manual-1/reopen", json={
        "reason": "append remains available",
        "expected_current_revision_id": accepted["revision_id"],
    })
    assert reopened.status_code == 201


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"client_id": 2}, "same client"),
        ({"target_kind": "source_evidence_review", "source_id": "source-1"}, "manual review"),
        ({"intake_id": "upload-1", "target_kind": "source_evidence_review", "source_id": None}, "uploaded review"),
        ({"intake_id": "upload-1", "target_kind": "source_evidence_review", "source_id": "missing"}, "uploaded review"),
    ],
)
def test_direct_orm_revision_insert_enforces_target_provenance(api, overrides: dict, message: str) -> None:
    _client_api, sessions = api
    values = {
        "revision_id": "direct-invalid",
        "client_id": 1,
        "target_kind": "manual_record_review",
        "intake_id": "manual-1",
        "source_id": None,
        "predecessor_revision_id": None,
        "revision_sequence": 1,
        "state": "under_review",
        "reason": None,
        "actor": ACTOR,
    }
    values.update(overrides)
    with sessions() as db:
        db.add(M03ReviewRevision(**values))
        with pytest.raises(ValueError, match=message):
            db.commit()
        db.rollback()
        assert db.scalar(text("SELECT COUNT(*) FROM m03_review_revisions")) == 0


def test_direct_orm_predecessor_and_annotation_must_stay_in_target_chain(api) -> None:
    client, sessions = api
    manual_root = client.post("/api/clients/1/m03/targets/manual-1/start").json()
    upload_root = client.post("/api/clients/1/m03/targets/upload-1/start").json()
    with sessions() as db:
        db.add(M03ReviewRevision(
            revision_id="cross-target-child", client_id=1,
            target_kind="source_evidence_review", intake_id="upload-1", source_id="source-1",
            predecessor_revision_id=manual_root["revision_id"], revision_sequence=2,
            state="accepted", reason="forged", actor=ACTOR,
        ))
        with pytest.raises(ValueError, match="same target chain"):
            db.commit()
        db.rollback()
        db.add(M03Annotation(
            annotation_id="cross-target-note", client_id=1, intake_id="upload-1",
            source_id="source-1", review_revision_id=manual_root["revision_id"],
            topic="topic", note="note", reason="reason", actor=ACTOR,
        ))
        with pytest.raises(ValueError, match="same target chain"):
            db.commit()
        db.rollback()
        assert db.get(M03ReviewRevision, upload_root["revision_id"]) is not None
        assert db.get(M03ReviewRevision, "cross-target-child") is None
        assert db.get(M03Annotation, "cross-target-note") is None


@pytest.mark.parametrize("corruption", [
    "actor = 'forged'",
    "client_id = 2",
    "target_kind = 'source_evidence_review', source_id = 'source-1'",
    "predecessor_revision_id = revision_id",
    "state = 'under_review'",
    "revision_sequence = 99",
    "revision_id = 'malformed-review-id'",
    "decided_at = '2000-01-01 00:00:00'",
])
def test_eligibility_fails_closed_for_forged_persisted_chain(api, corruption: str) -> None:
    client, sessions = api
    root = client.post("/api/clients/1/m03/targets/manual-1/start").json()
    accepted = client.post("/api/clients/1/m03/targets/manual-1/accept", json={
        "reason": "accepted",
        "expected_current_revision_id": root["revision_id"],
    }).json()
    assert client.get("/api/clients/1/m03/targets/manual-1/eligibility").json()["eligible"] is True
    with sessions() as db:
        db.execute(
            text(f"UPDATE m03_review_revisions SET {corruption} WHERE revision_id = :revision_id"),
            {"revision_id": accepted["revision_id"]},
        )
        db.commit()
    result = client.get("/api/clients/1/m03/targets/manual-1/eligibility")
    assert result.status_code == 200
    assert result.json()["eligible"] is False
    assert result.json()["exclusion_reason"] == "review_chain_inconsistent"


def test_eligibility_fails_closed_for_inconsistent_uploaded_provenance(api) -> None:
    client, sessions = api
    root = client.post("/api/clients/1/m03/targets/upload-1/start").json()
    accepted = client.post("/api/clients/1/m03/targets/upload-1/accept", json={
        "reason": "accepted", "expected_current_revision_id": root["revision_id"],
    })
    assert accepted.status_code == 201
    with sessions() as db:
        db.execute(text("UPDATE m02_preserved_sources SET byte_size = 9 WHERE source_id = 'source-1'"))
        db.commit()
    result = client.get("/api/clients/1/m03/targets/upload-1/eligibility")
    assert result.status_code == 200
    assert result.json()["eligible"] is False
    assert result.json()["exclusion_reason"] == "uploaded_provenance_inconsistent"


def test_timestamp_constraints_and_ordering_fail_closed(api) -> None:
    client, sessions = api
    root = client.post("/api/clients/1/m03/targets/manual-1/start").json()
    accepted = client.post("/api/clients/1/m03/targets/manual-1/accept", json={
        "reason": "accepted", "expected_current_revision_id": root["revision_id"],
    }).json()
    with sessions() as db:
        with pytest.raises(IntegrityError):
            db.execute(
                text("UPDATE m03_review_revisions SET decided_at = NULL WHERE revision_id = :revision_id"),
                {"revision_id": accepted["revision_id"]},
            )
            db.commit()
        db.rollback()
        db.execute(
            text("UPDATE m03_review_revisions SET decided_at = '2999-01-01 00:00:00' WHERE revision_id = :revision_id"),
            {"revision_id": root["revision_id"]},
        )
        db.commit()
    result = client.get("/api/clients/1/m03/targets/manual-1/eligibility")
    assert result.status_code == 200
    assert result.json()["eligible"] is False
    assert result.json()["exclusion_reason"] == "review_chain_inconsistent"


def test_start_and_decisions_are_atomic_under_concurrency(api) -> None:
    client, sessions = api

    def start():
        return client.post("/api/clients/1/m03/targets/manual-1/start")

    with ThreadPoolExecutor(max_workers=2) as pool:
        starts = list(pool.map(lambda _index: start(), range(2)))
    assert sorted(response.status_code for response in starts) == [201, 409]
    assert next(response.json()["detail"]["code"] for response in starts if response.status_code == 409) in {
        "M03_REVIEW_ALREADY_STARTED",
        "M03_CONCURRENT_LEAF_CONFLICT",
    }
    root = next(response.json() for response in starts if response.status_code == 201)
    with sessions() as db:
        rows = list(db.scalars(select(M03ReviewRevision)).all())
        assert len(rows) == 1
        assert rows[0].revision_sequence == 1

    def decide(action: str):
        return client.post(f"/api/clients/1/m03/targets/manual-1/{action}", json={
            "reason": action,
            "expected_current_revision_id": root["revision_id"],
        })

    with ThreadPoolExecutor(max_workers=2) as pool:
        decisions = list(pool.map(decide, ["accept", "reject"]))
    assert sorted(response.status_code for response in decisions) == [201, 409]
    with sessions() as db:
        rows = list(db.scalars(select(M03ReviewRevision).order_by(M03ReviewRevision.revision_sequence)).all())
        assert len(rows) == 2
        assert rows[1].state in {"accepted", "rejected"}

    terminal = next(response.json() for response in decisions if response.status_code == 201)

    def reopen():
        return client.post("/api/clients/1/m03/targets/manual-1/reopen", json={
            "reason": "reopen",
            "expected_current_revision_id": terminal["revision_id"],
        })

    with ThreadPoolExecutor(max_workers=2) as pool:
        reopens = list(pool.map(lambda _index: reopen(), range(2)))
    assert sorted(response.status_code for response in reopens) == [201, 409]
    with sessions() as db:
        rows = list(db.scalars(select(M03ReviewRevision).order_by(M03ReviewRevision.revision_sequence)).all())
        assert len(rows) == 3
        assert rows[-1].state == "under_review"


def test_annotation_supersession_is_append_only_and_safe(api) -> None:
    client, sessions = api
    root = client.post("/api/clients/1/m03/targets/manual-1/start").json()
    accepted = client.post("/api/clients/1/m03/targets/manual-1/accept", json={
        "reason": "accepted", "expected_current_revision_id": root["revision_id"],
    }).json()
    first = client.post("/api/clients/1/m03/targets/manual-1/annotations", json={
        "review_revision_id": accepted["revision_id"], "topic": "old",
        "note": "old note", "reason": "old reason",
    }).json()
    second_response = client.post("/api/clients/1/m03/targets/manual-1/annotations", json={
        "review_revision_id": accepted["revision_id"], "topic": "new",
        "note": "new note", "reason": "supersede",
        "supersedes_annotation_id": first["annotation_id"],
    })
    assert second_response.status_code == 201
    second = second_response.json()
    assert second["supersedes_annotation_id"] == first["annotation_id"]
    history = client.get("/api/clients/1/m03/targets/manual-1/annotations").json()
    assert [row["annotation_id"] for row in history] == [first["annotation_id"], second["annotation_id"]]
    assert history[0]["note"] == "old note"
    assert client.get("/api/clients/1/m03/targets/manual-1/eligibility").json()["eligible"] is True

    foreign_root = client.post("/api/clients/2/m03/targets/manual-2/start").json()
    foreign_note = client.post("/api/clients/2/m03/targets/manual-2/annotations", json={
        "review_revision_id": foreign_root["revision_id"], "topic": "foreign",
        "note": "foreign", "reason": "foreign",
    }).json()
    foreign_or_missing = ["missing-annotation", foreign_note["annotation_id"]]
    for annotation_id in foreign_or_missing:
        response = client.post("/api/clients/1/m03/targets/manual-1/annotations", json={
            "review_revision_id": accepted["revision_id"], "topic": "x",
            "note": "x", "reason": "x", "supersedes_annotation_id": annotation_id,
        })
        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "M03_RESOURCE_NOT_FOUND"
    with sessions() as db:
        assert db.scalar(text("SELECT COUNT(*) FROM m03_annotations WHERE client_id = 1")) == 2
