from datetime import date
import pytest
from pydantic import ValidationError
from app.schemas.scenario_pension_election import ScenarioPensionElection, ScenarioPensionElectionSet


def election(**changes):
    return dict(decision_id="d1", pension_start_date=date(2035, 1, 1),
                target_year=2035, survivors_option="תקנוני",
                spouse_age_diff=0, coefficient_selection="catalog_candidate") | changes


def test_explicit_contract_is_inert_and_closed():
    saved = ScenarioPensionElectionSet.model_validate({
        "expected_scenario_version": 3, "elections": [election()]})
    assert saved.elections[0].decision_id == "d1"
    assert saved.elections[0].pension_start_date == date(2035, 1, 1)
    assert not hasattr(saved.elections[0], "execution_allowed")
    with pytest.raises(ValidationError):
        ScenarioPensionElection.model_validate(election(professional_permission_verified=True))


@pytest.mark.parametrize("change", [
    {"pension_start_date": None}, {"target_year": None},
    {"survivors_option": None}, {"survivors_option": " "},
    {"spouse_age_diff": None}, {"coefficient_selection": None},
    {"coefficient_selection": "approved"},
    {"company_name": "Insurer"},
    {"company_name": " Insurer", "option_name": "Option"},
])
def test_missing_or_invented_option_rejected(change):
    with pytest.raises(ValidationError):
        ScenarioPensionElection.model_validate(election(**change))


def test_draft_revision_and_decision_ids_are_required():
    with pytest.raises(ValidationError):
        ScenarioPensionElectionSet.model_validate({"expected_scenario_version": 0, "elections": [election()]})
    with pytest.raises(ValidationError):
        ScenarioPensionElectionSet.model_validate({"expected_scenario_version": 1, "elections": [
            election(), election()]})
