"""SC-05E internal writer refuses unauthenticated and stale review evidence."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.services import scenario_coefficient_professional_review_store_service as store
from app.services.scenario_draft_service import DraftError


def context():
    return {
        "client_id": 7, "scenario_id": "s", "scenario_version": 3,
        "decision_id": "d", "product_id": "p", "component_id": "c",
        "product_version": 2,
        "manifest_fingerprint": "a" * 64,
        "inventory_fingerprint": "b" * 64,
        "election_fingerprint": "c" * 64,
        "source_fingerprint": "d" * 64,
    }


def test_anonymous_actor_rejected_without_database_touch():
    db = Mock()
    with pytest.raises(DraftError, match="PROFESSIONAL_REVIEW_AUTHENTICATED_ACTOR_REQUIRED"):
        store.append_documentary_review(db, client_id=7, scenario_id="s",
            expected=context(), authenticated_actor="", review_reference="ref",
            decision="reviewed_for_candidate")
    db.assert_not_called()


def test_stale_version_rejected_before_write(monkeypatch):
    monkeypatch.setattr(store, "_scenario", lambda *args:
                        SimpleNamespace(version=4, status="draft"))
    db = Mock()
    with pytest.raises(DraftError, match="PROFESSIONAL_REVIEW_CONTEXT_STALE"):
        store.append_documentary_review(db, client_id=7, scenario_id="s",
            expected=context(), authenticated_actor="trusted-professional",
            review_reference="ref", decision="reviewed_for_candidate")
    db.add.assert_not_called()


def test_valid_documentary_evidence_remains_inert(monkeypatch):
    monkeypatch.setattr(store, "_scenario", lambda *args:
                        SimpleNamespace(version=3, status="draft"))
    db = Mock()
    db.scalar.return_value = SimpleNamespace(
        source_product_id="p", source_component_id="c")
    result = store.append_documentary_review(db, client_id=7, scenario_id="s",
        expected=context(), authenticated_actor="trusted-professional",
        review_reference="ref", decision="reviewed_for_candidate")
    assert result["review_state"] == "RECORDED_NOT_AUTHORIZED"
    assert result["execution_allowed"] is False
    assert result["coefficient_candidate"] is None
    assert result["financial_result"] is None
    assert db.add.call_count == 1
    assert db.flush.call_count == 1
