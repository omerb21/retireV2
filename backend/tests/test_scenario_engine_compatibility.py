"""SC-03B exact callable compatibility without financial execution."""
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
