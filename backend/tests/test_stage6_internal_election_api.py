"""Stage 6 internal election API security/CAS adapter tests.

These tests do not grant production route availability.
"""
from types import SimpleNamespace
from unittest.mock import patch

from app.api import scenario_stage6_internal_routes as route
from app.schemas.scenario_pension_election import ScenarioPensionElectionSet
from app.services.scenario_draft_service import DraftError


def req(production=True, enabled=True):
    return SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(
            auth_config=SimpleNamespace(production=production),
            stage6_preview_enabled=enabled)),
        state=SimpleNamespace(trusted_professional_actor="planner:valid",
                              auth_session={"actor_id":"planner:valid"}),
    )


def body():
    return ScenarioPensionElectionSet(
        expected_scenario_version=2,
        elections=[{
            "decision_id":"d1","pension_start_date":"2027-09-30",
            "target_year":2027,"survivors_option":"spouse",
            "spouse_age_diff":0,
            "coefficient_selection":"manual_review_required",
            "company_name":"insurer","option_name":"standard",
        }],
    )


def test_missing_signed_session_blocks_election_read():
    db=SimpleNamespace(rollback=lambda:None)
    with patch.object(route,"validate_session",return_value="bad-session"),patch.object(
        route,"current_elections") as read:
        with patch.object(route,"error",return_value="auth-error") as reject:
            result=route.read_internal_pension_elections(
                req(),scenario_id="sc",client_id=1,db=db)
    assert result=="auth-error"
    reject.assert_called_once()
    read.assert_not_called()


def test_invalid_csrf_blocks_election_write_before_any_db_change():
    db=SimpleNamespace(rollback=lambda:None)
    with patch.object(route,"validate_session",return_value=None),patch.object(
        route,"validate_origin",return_value=None),patch.object(
        route,"validate_csrf",return_value="csrf-error"),patch.object(
        route,"replace_elections") as writer:
        result=route.save_internal_pension_elections(
            req(),body(),scenario_id="sc",client_id=1,db=db)
    assert result=="csrf-error"
    writer.assert_not_called()


def test_successful_election_cas_commits_once_and_passes_trusted_actor():
    commits=[]
    db=SimpleNamespace(commit=lambda:commits.append("commit"),
                       rollback=lambda:commits.append("rollback"))
    with patch.object(route,"validate_session",return_value=None),patch.object(
        route,"validate_origin",return_value=None),patch.object(
        route,"validate_csrf",return_value=None),patch.object(
        route,"replace_elections",return_value={"scenario_version":3}) as writer:
        result=route.save_internal_pension_elections(
            req(),body(),scenario_id="sc",client_id=1,db=db)
    assert result.status_code==200
    assert commits==["commit"]
    writer.assert_called_once_with(db,1,"sc",body(),"planner:valid")


def test_election_version_conflict_rolls_back_and_preserves_cas():
    commits=[]
    db=SimpleNamespace(commit=lambda:commits.append("commit"),
                       rollback=lambda:commits.append("rollback"))
    with patch.object(route,"validate_session",return_value=None),patch.object(
        route,"validate_origin",return_value=None),patch.object(
        route,"validate_csrf",return_value=None),patch.object(
        route,"replace_elections",side_effect=DraftError("SCENARIO_VERSION_CONFLICT",409)):
        result=route.save_internal_pension_elections(
            req(),body(),scenario_id="sc",client_id=1,db=db)
    assert result.status_code==409
    assert commits==["rollback"]


def test_production_internal_election_is_not_authorized():
    with patch.object(route,"replace_elections") as writer,patch.object(
        route,"error",return_value="disabled") as reject:
        result=route.save_internal_pension_elections(
            req(True,enabled=False),body(),scenario_id="sc",client_id=1,db=object())
    assert result=="disabled"
    writer.assert_not_called()
