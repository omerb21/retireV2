"""Snapshot integration boundary without a new financial authority or router."""
from copy import deepcopy

from app.services import scenario_allocation_snapshot_service as subject
from app.services import scenario_input_manifest_service as manifest
from tests.test_scenario_input_manifest import fixture


def authoritative_pair():
    db = fixture()
    db.decisions[0].source_fingerprint_at_review = manifest._source_evidence(
        db.product, db.component,
    )["source_fingerprint"]
    from app.services.scenario_snapshot_candidate_service import _build_pair_in_snapshot
    return _build_pair_in_snapshot(db, 7, "s", None)


def test_existing_snapshot_owner_is_reused_without_second_database_read(monkeypatch):
    visited = []

    def fake_snapshot(factory, *, client_id, scenario_id, _snapshot_extension):
        visited.append((factory, client_id, scenario_id))
        return _snapshot_extension(None, authoritative_pair())

    monkeypatch.setattr(subject, "build_manifest_candidate_snapshot", fake_snapshot)
    token = object()
    result = subject.build_readonly_allocation_snapshot(
        token, client_id=7, scenario_id="s",
    )
    assert visited == [(token, 7, "s")]
    assert result["candidate_evidence_state"] == "STRUCTURALLY_CONSISTENT_NOT_ADMITTED"
    assert result["candidate_blockers"] == []
    assert result["allocation_evidence"]["sources"][0]["unallocated"] == "50.00"
    assert result["execution_allowed"] is False
    assert result["financial_result"] is None


def test_candidate_blockers_are_preserved_and_cannot_be_overridden():
    pair = authoritative_pair()
    pair["candidate"] = deepcopy(pair["candidate"])
    pair["candidate"]["evidence_state"] = "BLOCKED"
    pair["candidate"]["blockers"] = ["TEST_STRUCTURAL_BLOCKER"]
    result = subject._allocation_extension(None, pair)
    assert result["candidate_evidence_state"] == "BLOCKED"
    assert result["candidate_blockers"] == ["TEST_STRUCTURAL_BLOCKER"]
    assert result["execution_allowed"] is False
    assert result["financial_result"] is None


def test_extension_output_does_not_mutate_canonical_pair():
    pair = authoritative_pair()
    saved = deepcopy(pair)
    output = subject._allocation_extension(None, pair)
    output["candidate_blockers"].append("FAKE")
    output["allocation_evidence"]["sources"][0]["decision_ids"].append("FAKE")
    assert pair == saved


def test_no_staging_mount_or_financial_evaluation_is_added():
    result = subject._allocation_extension(None, authoritative_pair())
    assert set(result) == {
        "manifest_fingerprint",
        "candidate_evidence_state",
        "candidate_blockers",
        "allocation_evidence",
        "financial_result",
        "execution_allowed",
    }
    assert result["allocation_evidence"]["financial_result"] is None
    assert result["allocation_evidence"]["execution_allowed"] is False
