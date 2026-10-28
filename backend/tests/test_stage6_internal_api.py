"""Stage 6 preview is opt-in on authenticated staging and not deployed by default."""
from types import SimpleNamespace
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.api import scenario_stage6_internal_routes as route
from app.api import scenario_stage6_factor_admission_routes as factor_route
from app.main import create_app
from app.security.config import AuthConfig
from app.security.session import COOKIE_NAME, issue


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
    assert result.headers["cache-control"]=="no-store, private"
    assert result.headers["pragma"]=="no-cache"


def test_invalid_signed_session_never_calls_service():
    r=request(actor="planner:authenticated")
    with patch.object(route,"validate_session",return_value="invalid"),patch.object(
        route,"estimate_single_pension_decision") as estimate,patch.object(
        route,"error",return_value="unauthorized"):
        result=route.internal_gross_estimate(r,"scenario","decision",client_id=1,factory=object())
    assert result=="unauthorized"
    estimate.assert_not_called()


def _production_config():
    return AuthConfig(
        production=True, public_origin="https://retire.example",
        public_authority="retire.example", actor_id="planner:stage6",
        session_secret=b"s"*32, rate_limit_secret=b"r"*32,
    )


def _edge_headers(**extra):
    values={
        "host":"retire.example", "x-real-ip":"2001:db8::6",
        "x-forwarded-proto":"https", "x-forwarded-host":"retire.example",
    }
    values.update(extra)
    return values


def test_real_middleware_requires_signed_session_for_mounted_preview(monkeypatch):
    monkeypatch.setenv("STAGE6_PREVIEW_ENABLED","1")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME","staging")
    config=_production_config()
    app=create_app(config)
    app.dependency_overrides[route.get_stage6_factory]=lambda:"factory"
    client=TestClient(app)
    path="/api/clients/1/scenario-drafts/sc/pension-decisions/d/gross-estimate"
    with patch.object(route,"estimate_single_pension_decision",
                      return_value={"result_state":"BLOCKED"}) as estimate:
        missing=client.get(path,headers=_edge_headers())
        token,_=issue(config)
        client.cookies.set(COOKIE_NAME,token)
        accepted=client.get(path,headers=_edge_headers())
    assert (missing.status_code,missing.json()["code"])==(401,"SESSION_MISSING")
    assert accepted.status_code==200
    estimate.assert_called_once_with(
        "factory",client_id=1,scenario_id="sc",decision_id="d")


def test_real_middleware_requires_session_bound_csrf_for_factor_write(monkeypatch):
    monkeypatch.setenv("STAGE6_PREVIEW_ENABLED","1")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME","staging")
    config=_production_config()
    app=create_app(config)
    app.dependency_overrides[factor_route.get_stage6_admission_factory]=lambda:"factory"
    client=TestClient(app)
    token,session=issue(config)
    client.cookies.set(COOKIE_NAME,token)
    path="/api/clients/1/scenario-drafts/sc/pension-decisions/d/factor-admissions"
    body={
        "expected_scenario_version":2,"expected_admission_revision":0,
        "factor_value":"200","factor_evidence_type":"PLANNER_ASSUMPTION",
        "factor_evidence_reference":"professional assumption",
    }
    headers=_edge_headers(origin="https://retire.example")
    with patch.object(factor_route,"append_authenticated_serializable_factor_admission",
                      return_value={"admission_revision":1,"execution_allowed":False}) as writer:
        rejected=client.post(path,json=body,headers=headers)
        accepted=client.post(path,json=body,headers={
            **headers,"x-rtdir-csrf":session["csrf"],
        })
    assert (rejected.status_code,rejected.json()["code"])==(403,"CSRF_INVALID")
    assert accepted.status_code==200
    writer.assert_called_once()
