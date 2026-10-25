"""SC-03B exact callable compatibility without financial execution."""
import pytest
from sqlalchemy.orm import Session

from app.services import scenario_engine_compatibility_service as subject
from app.services.scenario_input_manifest_service import build_inert_manifest
from test_pension_target_date_execution import HASHES, inputs as pension_inputs
from test_projection_execution import pair as capital_pair, ready as ready_capital
from test_recovery_pension_products import engine
from test_retirement_target_date_income_comparison_basis import _request as gap_request
from test_scenario_input_manifest import fixture


def manifest():
    return build_inert_manifest(fixture(), 7, "s")


def pension_payload(planning_result, **supplied):
    values = {
        "supplied_planning_calculation_input_fingerprint": None,
        "supplied_monthly_basis_semantic_fingerprint": None,
        "supplied_monthly_basis_source_fingerprint": None,
        "supplied_temporal_semantic_fingerprint": None,
        "supplied_temporal_source_fingerprint": None,
    }
    values.update(supplied)
    return {
        "planning_result": planning_result,
        "source_id": "manual:7",
        **values,
    }


def test_exact_real_engine_callable_contracts_are_frozen():
    assert subject._actual_parameter_contract("pension_target_date") == (
        ("planning_result", "POSITIONAL_OR_KEYWORD", True),
        ("source_id", "POSITIONAL_OR_KEYWORD", True),
        ("supplied_planning_calculation_input_fingerprint", "KEYWORD_ONLY", True),
        ("supplied_monthly_basis_semantic_fingerprint", "KEYWORD_ONLY", True),
        ("supplied_monthly_basis_source_fingerprint", "KEYWORD_ONLY", True),
        ("supplied_temporal_semantic_fingerprint", "KEYWORD_ONLY", True),
        ("supplied_temporal_source_fingerprint", "KEYWORD_ONLY", True),
    )
    assert subject._actual_parameter_contract("capital_projection") == (
        ("client_id", "POSITIONAL_OR_KEYWORD", True),
        ("plan", "POSITIONAL_OR_KEYWORD", True),
        ("authority", "POSITIONAL_OR_KEYWORD", True),
    )
    assert subject._actual_parameter_contract("monthly_income_gap") == (
        ("db", "POSITIONAL_OR_KEYWORD", True),
        ("request", "POSITIONAL_OR_KEYWORD", True),
    )


def test_existing_pension_fixture_is_structurally_compatible_but_not_admitted():
    values = pension_inputs()
    planning_result = {
        "pension_inputs": [{
            "source_id": values["source_id"],
            "monthly_amount_basis": values["monthly_basis"],
            "temporal_authority": values["temporal_authority"],
        }],
        "retirement_target": values["retirement_target"],
        "planning_calculation_input_fingerprint": HASHES["3"],
    }
    result = subject.assess_engine_input_shape("pension_target_date", {
        "planning_result": planning_result,
        "source_id": values["source_id"],
        "supplied_planning_calculation_input_fingerprint": HASHES["3"],
        "supplied_monthly_basis_semantic_fingerprint": HASHES["1"],
        "supplied_monthly_basis_source_fingerprint": HASHES["2"],
        "supplied_temporal_semantic_fingerprint": HASHES["4"],
        "supplied_temporal_source_fingerprint": HASHES["5"],
    })
    assert result["structural_state"] == "STRUCTURALLY_COMPATIBLE_NOT_ADMITTED"
    assert result["execution_allowed"] is False
    assert result["permission_state"] == "NOT_ADMITTED"
    assert result["professional_eligibility_state"] == "NOT_EVALUATED"
    assert result["tax_state"] == "NOT_EVALUATED"


@pytest.mark.parametrize("sources", [
    [],
    [{"source_id": "manual:7"}, {"source_id": "manual:7"}],
])
def test_absent_or_duplicate_source_is_compatible_blocked_engine_input(
    monkeypatch, sources,
):
    planning = {
        "pension_inputs": sources,
        "retirement_target": pension_inputs()["retirement_target"],
        "planning_calculation_input_fingerprint": HASHES["3"],
    }
    payload = pension_payload(
        planning,
        supplied_planning_calculation_input_fingerprint=HASHES["3"],
        supplied_monthly_basis_semantic_fingerprint=HASHES["1"],
        supplied_monthly_basis_source_fingerprint=HASHES["2"],
        supplied_temporal_semantic_fingerprint=HASHES["4"],
        supplied_temporal_source_fingerprint=HASHES["5"],
    )
    actual = subject.pension.execute_from_planning_result(**payload)
    assert actual["result_state"] == "block_no_result"
    assert "SOURCE_NOT_CURRENT" in actual["blockers"]
    assert actual["execution_identity_evidence"]["source_current_state"] == "not_current"
    monkeypatch.setattr(
        subject.pension, "execute_source",
        lambda **_kwargs: pytest.fail("compatibility service invoked pension execution"),
    )
    compatibility = subject.assess_engine_input_shape("pension_target_date", payload)
    assert compatibility["structural_state"] == "STRUCTURALLY_COMPATIBLE_NOT_ADMITTED"
    assert compatibility["execution_allowed"] is False


def test_missing_basis_identity_and_unready_target_are_compatible_blocked_input(
    monkeypatch,
):
    planning = {
        "pension_inputs": [{
            "source_id": "manual:7",
            "monthly_amount_basis": None,
            "temporal_authority": None,
        }],
        "retirement_target": {
            "retirement_target_date": None,
            "retirement_target_ready": False,
        },
        "planning_calculation_input_fingerprint": None,
    }
    payload = pension_payload(planning)
    actual = subject.pension.execute_from_planning_result(**payload)
    assert actual["result_state"] == "block_no_result"
    assert actual["execution_identity_evidence"]["source_current_state"] == "current"
    assert {
        "MONTHLY_BASIS_NOT_READY", "TEMPORAL_AUTHORITY_NOT_READY",
        "RETIREMENT_TARGET_NOT_READY", "PLANNING_INPUT_IDENTITY_STALE",
    } <= set(actual["blockers"])
    monkeypatch.setattr(
        subject.pension, "execute_source",
        lambda **_kwargs: pytest.fail("compatibility service invoked pension execution"),
    )
    compatibility = subject.assess_engine_input_shape("pension_target_date", payload)
    assert compatibility["structural_state"] == "STRUCTURALLY_COMPATIBLE_NOT_ADMITTED"
    assert compatibility["execution_allowed"] is False
    assert compatibility["permission_state"] == "NOT_ADMITTED"
    assert compatibility["professional_eligibility_state"] == "NOT_EVALUATED"
    assert compatibility["tax_state"] == "NOT_EVALUATED"


@pytest.mark.parametrize("payload", [
    pension_payload({"pension_inputs": None}),
    pension_payload({
        "pension_inputs": [{
            "source_id": "manual:7",
            "monthly_amount_basis": "not-a-mapping",
            "temporal_authority": None,
        }],
        "retirement_target": None,
    }),
    pension_payload({}, supplied_monthly_basis_semantic_fingerprint="not-a-sha"),
])
def test_malformed_outer_pension_contract_remains_incompatible(payload):
    result = subject.assess_engine_input_shape("pension_target_date", payload)
    assert result["structural_state"] == "INCOMPATIBLE"
    assert result["execution_allowed"] is False


@pytest.mark.parametrize(("monthly", "temporal"), [
    ({"authority_kind": object()}, None),
    (None, {"temporal_authority_kind": object()}),
])
def test_noncanonical_authority_kind_that_breaks_engine_is_incompatible(
    monthly, temporal,
):
    payload = pension_payload({
        "pension_inputs": [{
            "source_id": "manual:7",
            "monthly_amount_basis": monthly,
            "temporal_authority": temporal,
        }],
        "retirement_target": None,
        "planning_calculation_input_fingerprint": None,
    })
    with pytest.raises(ValueError, match="Noncanonical JSON value"):
        subject.pension.execute_from_planning_result(**payload)
    result = subject.assess_engine_input_shape("pension_target_date", payload)
    assert result["structural_state"] == "INCOMPATIBLE"
    assert result["execution_allowed"] is False


def test_existing_capital_fixture_is_structurally_compatible_but_not_admitted(engine):
    ready_capital(engine)
    plan, authority = capital_pair(engine)
    result = subject.assess_engine_input_shape("capital_projection", {
        "client_id": 1, "plan": plan, "authority": authority,
    })
    assert result["structural_state"] == "STRUCTURALLY_COMPATIBLE_NOT_ADMITTED"
    assert result["execution_allowed"] is False


def test_existing_gap_fixture_is_structurally_compatible_but_not_admitted(engine):
    with Session(engine) as db:
        result = subject.assess_engine_input_shape("monthly_income_gap", {
            "db": db, "request": gap_request(),
        })
        assert result["structural_state"] == "STRUCTURALLY_COMPATIBLE_NOT_ADMITTED"
        assert result["execution_allowed"] is False


def test_manifest_map_names_exact_adapter_gaps_and_never_executes(monkeypatch):
    reached = []

    def pension_call(
        planning_result, source_id, *, supplied_planning_calculation_input_fingerprint,
        supplied_monthly_basis_semantic_fingerprint, supplied_monthly_basis_source_fingerprint,
        supplied_temporal_semantic_fingerprint, supplied_temporal_source_fingerprint,
    ):
        reached.append("pension")

    def capital_call(client_id, plan, authority):
        reached.append("capital")

    def gap_call(db, request):
        reached.append("gap")

    monkeypatch.setitem(subject.ENGINE_CONTRACTS["pension_target_date"], "callable", pension_call)
    monkeypatch.setitem(subject.ENGINE_CONTRACTS["capital_projection"], "callable", capital_call)
    monkeypatch.setitem(subject.ENGINE_CONTRACTS["monthly_income_gap"], "callable", gap_call)
    result = subject.assess_engine_compatibility(manifest())
    assert reached == []
    assert result["execution_allowed"] is False
    assert set(result["engines"]) == {
        "pension_target_date", "capital_projection", "monthly_income_gap",
    }
    for engine_result in result["engines"].values():
        assert engine_result["structural_state"] == "SCENARIO_ADAPTER_MISSING"
        assert engine_result["execution_allowed"] is False
        assert engine_result["result"] is None
        assert "PERMISSION_NOT_ADMITTED" in engine_result["blockers"]


def test_forged_or_incomplete_input_shapes_never_grant_execution():
    forged = {
        "db": object(),
        "request": {**gap_request(), "professional_eligibility": True},
    }
    result = subject.assess_engine_input_shape("monthly_income_gap", forged)
    assert result["structural_state"] == "INCOMPATIBLE"
    assert result["execution_allowed"] is False

    capital_result = subject.assess_engine_input_shape("capital_projection", {
        "client_id": 1,
        "plan": {
            "capital_inputs": [], "retirement_target": {},
            "planning_calculation_input_fingerprint": "1" * 64,
        },
        "authority": {
            "client_id": 1, "covered_capital_sources": [],
            "projection_basis_admission_fingerprint": "2" * 64,
        },
    })
    assert capital_result["structural_state"] == "INCOMPATIBLE"
    assert capital_result["execution_allowed"] is False


def test_invalid_manifest_fails_closed():
    invalid = subject.assess_engine_compatibility({"schema_version": "other"})
    assert invalid["engines"] == {}
    assert invalid["execution_allowed"] is False
