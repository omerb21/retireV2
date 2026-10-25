"""SC-06A must remain documentary-only, with no invented admission."""
from unittest.mock import Mock
import pytest

from app.services import scenario_coefficient_readiness_service as subject


def test_missing_decision_id_blocks_before_snapshot(monkeypatch):
    monkeypatch.setattr(subject, "build_manifest_candidate_snapshot",
                        lambda *a, **kw: pytest.fail("unexpected snapshot"))
    result = subject.assess_documentary_readiness(
        Mock(), client_id=7, scenario_id="s", decision_id="")
    assert result["state"] == "BLOCKED"
    assert result["coefficient_candidate"] is None
    assert result["execution_allowed"] is False


def test_unverified_candidate_does_not_read_reviews(monkeypatch):
    def snapshot(factory, **kwargs):
        db = Mock()
        response = kwargs["_snapshot_extension"](db, {
            "candidate": {"evidence_state": "BLOCKED"},
        })
        db.scalars.assert_not_called()
        return response
    monkeypatch.setattr(subject, "build_manifest_candidate_snapshot", snapshot)
    result = subject.assess_documentary_readiness(
        Mock(), client_id=7, scenario_id="s", decision_id="d")
    assert result["blockers"] == ["SCENARIO_SOURCE_UNVERIFIED"]
    assert result["authority_state"] == "NOT_EVALUATED"
    assert result["financial_result"] is None


def test_missing_documentary_review_remains_blocked(monkeypatch):
    def snapshot(factory, **kwargs):
        db = Mock()
        db.scalars.return_value.all.return_value = []
        monkeypatch.setattr(subject, "derive_documentary_review_context",
                            lambda *a, **kw: {"scenario_version": 2})
        return kwargs["_snapshot_extension"](db, {
            "candidate": {"evidence_state": "STRUCTURALLY_CONSISTENT_NOT_ADMITTED"},
        })
    monkeypatch.setattr(subject, "build_manifest_candidate_snapshot", snapshot)
    result = subject.assess_documentary_readiness(
        Mock(), client_id=7, scenario_id="s", decision_id="d")
    assert result["blockers"] == ["DOCUMENTARY_REVIEW_MISSING"]
    assert result["execution_allowed"] is False
