"""Stage 6 internal API safety: production omission and trusted actor requirement."""
from types import SimpleNamespace
from unittest.mock import patch

from app.api import scenario_stage6_internal_routes as route
from app.main import create_app


def test_stage6_route_not_registered_in_production_style_app():
    # Structural assurance: registration is conditional on not production.
    import inspect
    code=inspect.getsource(create_app)
    assert "if not config.production:" in code
    assert "app.include_router(scenario_stage6_internal_router)" in code
    assert code.index("if not config.production:\n        app.include_router(scenario_stage6_internal_router)")>code.index("for router in (")


def test_missing_trusted_actor_never_runs_estimate():
    request=SimpleNamespace(state=SimpleNamespace(),app=SimpleNamespace(
        state=SimpleNamespace(auth_config=SimpleNamespace(production=False))))
    with patch.object(route,"estimate_single_pension_decision") as estimate,patch.object(
        route,"error",return_value="unauthorized") as reject:
        result=route.internal_gross_estimate(
            request,scenario_id="scenario",decision_id="decision",client_id=1,
            factory=object())
    assert result=="unauthorized"
    reject.assert_called_once_with(request,401,"AUTHENTICATION_REQUIRED")
    estimate.assert_not_called()


def test_production_request_is_unavailable_even_if_route_imported():
    request=SimpleNamespace(
        state=SimpleNamespace(trusted_professional_actor="planner:authenticated"),
        app=SimpleNamespace(state=SimpleNamespace(
            auth_config=SimpleNamespace(production=True))))
    with patch.object(route,"estimate_single_pension_decision") as estimate,patch.object(
        route,"error",return_value="not-found") as reject:
        result=route.internal_gross_estimate(
            request,scenario_id="scenario",decision_id="decision",client_id=1,
            factory=object())
    assert result=="not-found"
    reject.assert_called_once_with(request,404,"ROUTE_NOT_FOUND")
    estimate.assert_not_called()


def test_authenticated_development_route_calls_canonical_service_once():
    request=SimpleNamespace(
        state=SimpleNamespace(trusted_professional_actor="planner:authenticated"),
        app=SimpleNamespace(state=SimpleNamespace(
            auth_config=SimpleNamespace(production=False))))
    with patch.object(route,"estimate_single_pension_decision",
                      return_value={"result_state":"BLOCKED","execution_allowed":False}) as estimate:
        response=route.internal_gross_estimate(
            request,scenario_id="scenario",decision_id="decision",client_id=1,
            factory="factory")
    estimate.assert_called_once_with(
        "factory",client_id=1,scenario_id="scenario",decision_id="decision")
    assert response.headers["cache-control"]=="no-store"
