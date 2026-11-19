"""Retired self-approval cannot create new revisions; historical reads remain routed."""
import json
from types import SimpleNamespace
from unittest.mock import patch

from app.api import scenario_draft_routes as routes


def test_direct_self_approval_api_is_retired_without_accessing_database():
    with patch.object(routes.fixation_review_service, "request_internal_approval") as writer:
        result = routes.approve_fixation_professional_review(
            SimpleNamespace(state=SimpleNamespace()), None, "scenario-1", client_id=1, db=None,
        )
        writer.assert_not_called()
    assert result.status_code == 410
    assert json.loads(result.body)["code"] == "FIXATION_INTERNAL_SELF_APPROVAL_RETIRED"


def test_historical_review_routes_remain_registered():
    paths = {(route.path, method) for route in routes.router.routes
             for method in getattr(route, "methods", set())}
    assert ("/api/clients/{client_id}/scenario-drafts/{scenario_id}/fixation-professional-review/history", "GET") in paths
    assert ("/api/clients/{client_id}/scenario-drafts/{scenario_id}/fixation-professional-review", "PUT") in paths
