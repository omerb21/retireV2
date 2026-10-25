"""SC-05E secure entrypoint cannot accept externally supplied provenance."""
from unittest.mock import Mock
import pytest

from app.services import scenario_coefficient_professional_review_store_service as store
from app.services.scenario_draft_service import DraftError


def test_missing_trusted_actor_denied_before_projection(monkeypatch):
    monkeypatch.setattr(
        "app.services.scenario_coefficient_review_context_service.derive_documentary_review_context",
        lambda *a, **kw: pytest.fail("unexpected database projection"))
    with pytest.raises(DraftError, match="PROFESSIONAL_REVIEW_AUTHENTICATED_ACTOR_REQUIRED"):
        store.append_database_derived_documentary_review(
            Mock(), client_id=7, scenario_id="s", decision_id="d",
            authenticated_actor="", review_reference="ref",
            decision="reviewed_for_candidate")


def test_only_internal_projection_provides_identity(monkeypatch):
    canonical = {
        "client_id": 7, "scenario_id": "s", "scenario_version": 2,
        "decision_id": "d", "product_id": "p", "component_id": "c",
        "product_version": 1, "manifest_fingerprint": "a"*64,
        "inventory_fingerprint": "b"*64, "election_fingerprint": "c"*64,
        "source_fingerprint": "d"*64,
    }
    calls = []
    def project(db, **kwargs):
        calls.append(("projection", kwargs))
        return canonical
    def save(db, **kwargs):
        calls.append(("store", kwargs))
        assert kwargs["expected"] is canonical
        return {"execution_allowed": False, "authority_state": "NOT_EVALUATED"}
    monkeypatch.setattr(
        "app.services.scenario_coefficient_review_context_service.derive_documentary_review_context",
        project)
    monkeypatch.setattr(store, "append_documentary_review", save)
    result = store.append_database_derived_documentary_review(
        Mock(), client_id=7, scenario_id="s", decision_id="d",
        authenticated_actor="trusted-professional", review_reference="ref",
        decision="reviewed_for_candidate")
    assert [name for name, _ in calls] == ["projection", "store"]
    assert result["execution_allowed"] is False
