"""Owner 261: a saved-run judgment is documentation, not freshness approval."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api import fixation_routes
from app.db.session import get_db
from app.main import app
from app.schemas.fixation_contracts import InternalPlannerJudgmentCreateRequest
from app.services import fixation_service


@pytest.mark.parametrize("freshness", ["legacy", "changed", "unknown"])
def test_historical_judgment_is_saved_without_freshness_certification(freshness, monkeypatch):
    """The freshness status is intentionally not an admission input to notes."""
    db = MagicMock()
    saved_run = SimpleNamespace(id=42, client_id=7, freshness_state=freshness)
    db.scalar.side_effect = [saved_run, None]
    monkeypatch.setattr(fixation_service, "_new_id", lambda prefix: "judgment-261")
    payload = InternalPlannerJudgmentCreateRequest(
        handling_status="internal_action_identified",
        next_internal_action=f"Review historical {freshness} result",
    )
    result = fixation_service.create_internal_planner_judgment(7, 42, payload, db)
    assert result.fixation_run_id == 42
    assert result.handling_status == "internal_action_identified"
    assert result.next_internal_action == f"Review historical {freshness} result"
    db.add.assert_called_once_with(result)
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(result)
    # The creation path does not update the saved run or its freshness.
    assert saved_run.freshness_state == freshness
    assert not hasattr(result, "freshness_state")


@pytest.mark.parametrize("freshness", ["legacy", "changed", "unknown"])
def test_api_records_history_without_using_a_prior_freshness_get(freshness, monkeypatch):
    db = object()
    observations = []

    def override_db():
        yield db

    def create(*, client_id, run_id, judgment_data, db_session):
        observations.append((client_id, run_id, judgment_data.handling_status, db_session))
        return SimpleNamespace(
            fixation_run_id=run_id, handling_status=judgment_data.handling_status,
            next_internal_action=judgment_data.next_internal_action,
            internal_note=judgment_data.internal_note,
        )

    def forbidden_freshness(**kwargs):
        raise AssertionError("Historical documentation must not require currentness")

    monkeypatch.setattr(fixation_routes, "create_internal_planner_judgment", create)
    monkeypatch.setattr(fixation_routes, "assess_persisted_fixation_freshness", forbidden_freshness)
    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/clients/7/fixation/runs/42/internal-planner-judgment",
                json={"handling_status": "internal_action_identified",
                      "next_internal_action": f"Review historical {freshness} result"},
            )
        assert response.status_code == 200
        assert response.json() == {
            "saved_run_id": 42, "handling_status": "internal_action_identified",
            "next_internal_action": f"Review historical {freshness} result",
            "internal_note": None,
        }
        assert observations == [(7, 42, "internal_action_identified", db)]
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_judgment_rejects_missing_or_foreign_run_and_duplicate():
    payload = InternalPlannerJudgmentCreateRequest(
        handling_status="continue_internal_review", next_internal_action="Document next step",
    )
    foreign_db = MagicMock()
    foreign_db.scalar.return_value = None  # No run for the requested client.
    with pytest.raises(fixation_service.InternalPlannerJudgmentRunNotFoundError):
        fixation_service.create_internal_planner_judgment(8, 42, payload, foreign_db)
    foreign_db.add.assert_not_called()
    foreign_db.commit.assert_not_called()

    duplicate_db = MagicMock()
    duplicate_db.scalar.side_effect = [SimpleNamespace(id=42, client_id=7), object()]
    with pytest.raises(fixation_service.InternalPlannerJudgmentAlreadyExistsError):
        fixation_service.create_internal_planner_judgment(7, 42, payload, duplicate_db)
    duplicate_db.add.assert_not_called()
    duplicate_db.commit.assert_not_called()
