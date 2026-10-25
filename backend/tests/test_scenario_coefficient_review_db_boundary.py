from types import SimpleNamespace
"""SC-05E secure entrypoint cannot accept externally supplied provenance."""
from unittest.mock import Mock
import pytest

from app.services import scenario_coefficient_professional_review_store_service as store
from app.services.scenario_draft_service import DraftError


def test_direct_db_derived_writer_denied_before_projection(monkeypatch):
    monkeypatch.setattr(
        "app.services.scenario_coefficient_review_context_service.derive_documentary_review_context",
        lambda *a, **kw: pytest.fail("unexpected database projection"))
    db = Mock()
    with pytest.raises(DraftError, match="PROFESSIONAL_REVIEW_AUTHENTICATED_ENTRYPOINT_REQUIRED"):
        store.append_database_derived_documentary_review(
            db, client_id=7, scenario_id="s", decision_id="d",
            authenticated_actor="claimed-professional", review_reference="ref",
            decision="reviewed_for_candidate")
    db.add.assert_not_called()


def test_authenticated_transaction_entrypoint_rejects_forged_actor_without_sql():
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(
            auth_config=SimpleNamespace(production=True))),
        state=SimpleNamespace(
            auth_session={"actor_id": "real-professional"},
            trusted_professional_actor="forged-professional"),
    )
    with pytest.raises(DraftError, match="PROFESSIONAL_REVIEW_AUTHENTICATED_ACTOR_REQUIRED"):
        store.append_authenticated_serializable_review(
            Mock(), request=request, client_id=7, scenario_id="s",
            decision_id="d", review_reference="r",
            decision="reviewed_for_candidate")
