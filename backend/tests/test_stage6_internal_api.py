"""Stage 6 preview is opt-in on authenticated staging and not deployed by default."""
from types import SimpleNamespace
from unittest.mock import patch

from app.api import scenario_stage6_internal_routes as route
from app.main import create_app
from app.security.config import AuthConfig


def paths(app):
    return {getattr(r,"path","") for r in app.routes}


def test_preview_is_absent_by_default_even_with_production_style_auth(monkeypatch):
    monkeypatch.delenv("STAGE6_PREVIEW_ENABLED",raising=False)
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME","staging")
    app=create_app(AuthConfig(production=True))
    assert app.state.stage6_preview_enabled is False
    assert not any("/gross-estimate" in p for p in paths(app))
    assert not any("/factor-admissions" in p for p in paths(app))


def test_preview_cannot_be_mounted_on_railway_production(monkeypatch):
    monkeypatch.setenv("STAGE6_PREVIEW_ENABLED","1")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME","production")
    app=create_app(AuthConfig(production=True))
    assert app.state.stage6_preview_enabled is False
    assert not any("/pension-elections" in p for p in paths(app))


def test_staging_preview_mounts_only_with_production_style_auth(monkeypatch):
    monkeypatch.setenv("STAGE6_PREVIEW_ENABLED","1")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME","staging")
    app=create_app(AuthConfig(production=True))
    p=paths(app)
    assert app.state.stage6_preview_enabled is True
    assert any("/gross-estimate" in x for x in p)
    assert any("/factor-admissions" in x for x in p)
    assert any("/pension-elections" in x for x in p)
    ordinary=create_app(AuthConfig(production=False))
    assert ordinary.state.stage6_preview_enabled is False
    assert not any("/gross-estimate" in x for x in paths(ordinary))


def request(*, enabled=True, actor=None):
    state=SimpleNamespace()
    if actor is not None:
        state.trusted_professional_actor=actor
        state.auth_session={"actor_id":actor}
    return SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(
            stage6_preview_enabled=enabled,
            auth_config=SimpleNamespace(production=True))),
        state=state,
    )


def test_missing_trusted_actor_never_calls_pte_service():
    r=request()
    with patch.object(route,"validate_session",return_value=None),patch.object(
        route,"estimate_single_pension_decision") as estimate,patch.object(
        route,"error",return_value="unauthorized") as reject:
        result=route.internal_gross_estimate(r,"scenario","decision",client_id=1,factory=object())
    assert result=="unauthorized"
    reject.assert_called_once_with(r,401,"AUTHENTICATION_REQUIRED")
    estimate.assert_not_called()


def test_preview_disabled_even_with_valid_actor():
    r=request(enabled=False,actor="planner:authenticated")
    with patch.object(route,"estimate_single_pension_decision") as estimate,patch.object(
        route,"error",return_value="not-found") as reject:
        result=route.internal_gross_estimate(r,"scenario","decision",client_id=1,factory=object())
    assert result=="not-found"
    reject.assert_called_once_with(r,404,"ROUTE_NOT_FOUND")
    estimate.assert_not_called()


def test_valid_staging_session_calls_canonical_service_once():
    r=request(actor="planner:authenticated")
    with patch.object(route,"validate_session",return_value=None),patch.object(
        route,"estimate_single_pension_decision",
        return_value={"result_state":"BLOCKED","execution_allowed":False}) as estimate:
        result=route.internal_gross_estimate(r,"scenario","decision",client_id=1,factory="factory")
    estimate.assert_called_once_with(
        "factory",client_id=1,scenario_id="scenario",decision_id="decision")
    assert result.headers["cache-control"]=="no-store"


def test_invalid_signed_session_never_calls_service():
    r=request(actor="planner:authenticated")
    with patch.object(route,"validate_session",return_value="invalid"),patch.object(
        route,"estimate_single_pension_decision") as estimate,patch.object(
        route,"error",return_value="unauthorized"):
        result=route.internal_gross_estimate(r,"scenario","decision",client_id=1,factory=object())
    assert result=="unauthorized"
    estimate.assert_not_called()
