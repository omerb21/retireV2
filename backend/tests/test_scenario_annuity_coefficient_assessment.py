"""SC-05 must never perform coefficient lookup from caller-owned maps."""
from datetime import date
import pytest
from app.services import scenario_annuity_coefficient_assessment_service as subject


@pytest.mark.parametrize("source_verified,permission_verified", [
    (True, True), (False, True), (True, False), (False, False),
])
def test_caller_maps_never_authorize_coefficient_lookup(monkeypatch, source_verified, permission_verified):
    import app.services.annuity_coefficient_service as catalog
    monkeypatch.setattr(catalog, "coefficient", lambda *a, **kw: pytest.fail("unauthorized catalog lookup"))
    result = subject.assess_coefficient_candidate(
        identity={"client_id": 7, "source_verified": source_verified, "manifest_fingerprint": "a"*64},
        product={"product_type": "קרן פנסיה", "version": 1},
        profile={"gender": "female", "birth_date": date(1965, 4, 2)},
        pension_options={"professional_permission_verified": permission_verified},
    )
    assert result["state"] == "BLOCKED"
    assert result["blockers"] == ["COEFFICIENT_LOOKUP_NOT_AUTHORIZED"]
    assert result["coefficient_candidate"] is None
    assert result["execution_allowed"] is False
    assert result["financial_result"] is None
    assert result["planning_snapshot"] is None
