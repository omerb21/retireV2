"""Stage 6 factor endpoint has no request-controlled identity authority."""
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from pydantic import ValidationError

from app.api import scenario_stage6_factor_admission_routes as routes


def request(production, enabled=True):
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(
        auth_config=SimpleNamespace(production=production),
        stage6_preview_enabled=enabled)),state=SimpleNamespace())


def payload():
    return routes.ProfessionalFactorAdmissionRequest(
        expected_scenario_version=2,expected_admission_revision=0,
        factor_value="200",factor_evidence_type="PLANNER_ASSUMPTION",
        factor_evidence_reference="Professional estimate, not insurer promise")


def test_payload_forbids_actor_and_fingerprints():
    with pytest.raises(ValidationError):
        routes.ProfessionalFactorAdmissionRequest(
            **payload().model_dump(),actor_id="forged")
    with pytest.raises(ValidationError):
        routes.ProfessionalFactorAdmissionRequest(
            **payload().model_dump(),manifest_fingerprint="a"*64)


def test_nonproduction_cannot_write():
    with patch.object(routes,"append_authenticated_serializable_factor_admission") as writer,patch.object(
        routes,"error",return_value="not-found"):
        assert routes.approve_professional_factor(
            request(False),payload(),"scenario","decision",client_id=1,factory=object())=="not-found"
        writer.assert_not_called()


def test_production_delegates_to_authenticated_writer_only():
    with patch.object(routes,"append_authenticated_serializable_factor_admission",
                      return_value={"admission_revision":1,"execution_allowed":False}) as writer:
        response=routes.approve_professional_factor(
            request(True),payload(),"scenario","decision",client_id=1,factory="factory")
    assert response.headers["cache-control"]=="no-store"
    assert writer.call_count==1
    kwargs=writer.call_args.kwargs
    assert "actor_id" not in kwargs
    assert "source_id" not in kwargs
    assert "manifest_fingerprint" not in kwargs
    assert kwargs["expected_admission_revision"]==0


def test_invalid_factor_type_never_reaches_writer():
    with pytest.raises(ValidationError):
        routes.ProfessionalFactorAdmissionRequest(
            **{**payload().model_dump(),"factor_evidence_type":"UNKNOWN"})

def test_production_with_preview_disabled_cannot_write():
    with patch.object(routes,"append_authenticated_serializable_factor_admission") as writer,patch.object(
        routes,"error",return_value="not-found"):
        assert routes.approve_professional_factor(
            request(True,enabled=False),payload(),"scenario","decision",client_id=1,
            factory=object())=="not-found"
        writer.assert_not_called()
