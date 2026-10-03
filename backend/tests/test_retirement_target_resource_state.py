"""Acceptance tests for canonical target-date resource-state assembly."""
import copy
import hashlib
import inspect
import json

import pytest

from app.services import retirement_target_resource_state_service as subject
from app.services import capital_projection_basis_service as capital_basis
from app.services import capital_projection_execution_service as capital_execution
from app.services import pension_target_date_portfolio_service as pension_portfolio
from app.services import planning_input_service


H_A, H_B, H_C, H_D, H_E = (character * 64 for character in "abcde")
TARGET = "2030-01-01"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def plan():
    return {
        "contract_version": planning_input_service.CONTRACT,
        "client_id": 7,
        "planning_calculation_input_fingerprint": H_A,
        "retirement_target": {"retirement_target_date": TARGET, "retirement_target_ready": True},
        "pension_inputs": [],
    }


def capital_authority(source_ids=(), *, ready=True, blockers=None, target=TARGET):
    blockers = [] if blockers is None else blockers
    sources = [
        {"source_id": source_id, "projection_basis_source_admission_fingerprint": chr(98 + index) * 64}
        for index, source_id in enumerate(source_ids)
    ]
    authority = {
        "planning_calculation_input_fingerprint": H_A,
        "covered_source_count": len(sources),
        "covered_capital_sources": sources,
        "projection_basis_ready": ready,
        "aggregate_blockers": blockers,
        "retirement_target_date": target,
    }
    authority["projection_basis_admission_fingerprint"] = digest({
        "contract": capital_basis.CONTRACT,
        "planning_calculation_input_fingerprint": H_A,
        "covered_source_count": len(sources),
        "sources": [
            {"source_id": source["source_id"], "admission": source["projection_basis_source_admission_fingerprint"]}
            for source in sources
        ],
        "ready": ready,
        "blockers": blockers,
    })
    return authority


def capital_source(source_id="capital:1", admission=H_B):
    source = {
        "source_id": source_id,
        "known_value_amount": "100.00",
        "economic_projection_start_date": "2029-01-01",
        "retirement_target_date": TARGET,
        "annual_rate": "0.07",
        "return_basis": "NET",
        "price_basis": "NOMINAL",
        "compounding_convention": "ANNUAL_EFFECTIVE",
        "day_count_convention": "ACTUAL_365_25",
        "source_semantic_fingerprint": H_C,
        "projection_timing_context_fingerprint": H_D,
        "projection_basis_decision_fingerprint": H_E,
        "projection_basis_source_admission_fingerprint": admission,
        "elapsed_days": 365,
        "year_fraction_numerator": 1460,
        "year_fraction_denominator": 1461,
        "projection_factor": "1.07",
        "projected_amount": "107",
        "calculation_contract_version": capital_execution.CONTRACT,
        "numeric_contract_version": capital_execution.NUMERIC_CONTRACT,
    }
    payload = {key: source[key] for key in capital_execution.RESULT_FIELDS}
    source["projection_result_fingerprint"] = digest(payload)
    return source


def capital_result(source_ids=(), *, blocked=False):
    blockers = ["RATE_MISSING"] if blocked else []
    authority = capital_authority(source_ids, ready=not blocked, blockers=blockers)
    sources = [] if blocked else [
        capital_source(source["source_id"], source["projection_basis_source_admission_fingerprint"])
        for source in authority["covered_capital_sources"]
    ]
    status = "BLOCKED_NO_RESULT" if blocked else (
        "AUTHORITATIVE_RESULT" if source_ids else "AUTHORITATIVE_EMPTY_RESULT"
    )
    result = {
        "contract_version": capital_execution.CONTRACT,
        "numeric_contract_version": capital_execution.NUMERIC_CONTRACT,
        "client_id": 7,
        "planning_calculation_input_fingerprint": H_A,
        "projection_basis_admission_fingerprint": authority["projection_basis_admission_fingerprint"],
        "covered_source_count": len(source_ids),
        "projected_sources": sources,
        "aggregate_blockers": blockers,
        "execution_ready": not blocked,
        "execution_status": status,
        "execution_fingerprint": None,
    }
    if not blocked:
        result["execution_fingerprint"] = digest({
            "calculation_contract_version": capital_execution.CONTRACT,
            "numeric_contract_version": capital_execution.NUMERIC_CONTRACT,
            "planning_calculation_input_fingerprint": H_A,
            "projection_basis_admission_fingerprint": result["projection_basis_admission_fingerprint"],
            "execution_status": status,
            "covered_source_count": len(source_ids),
            "sources": [
                {"source_id": source["source_id"], "projection_result_fingerprint": source["projection_result_fingerprint"]}
                for source in sources
            ],
        })
    return authority, result


def capital_client_mismatch_v2():
    """Byte-complete accepted client-8 capital vector, independently certified."""
    source_semantic = digest({
        "contract": capital_basis.CONTRACT,
        "adapter": "canonical_capital_input_v1",
        "client_id": 8,
        "source_id": "capital:1",
        "capital_asset_id": 1,
        "lifecycle_status": "current",
        "known_value_amount": "100",
        "value_as_of_date": "2029-01-01",
        "origin_kind": "manual",
        "conversion_id": None,
    })
    timing = digest({
        "planning_base_date": "2029-01-01",
        "retirement_target_date": TARGET,
    })
    decision = digest({
        "contract": capital_basis.CONTRACT,
        "annual_rate": "0",
        "return_basis": "NET",
        "price_basis": "NOMINAL",
        "compounding_convention": "ANNUAL_EFFECTIVE",
        "day_count_convention": "ACTUAL_365_25",
    })
    admission = digest({
        "planning_calculation_input_fingerprint": H_A,
        "projection_source_semantic_fingerprint": source_semantic,
        "projection_timing_context_fingerprint": timing,
        "decision": decision,
        "ready": True,
        "blockers": [],
    })
    aggregate_admission = digest({
        "contract": capital_basis.CONTRACT,
        "planning_calculation_input_fingerprint": H_A,
        "covered_source_count": 1,
        "sources": [{"source_id": "capital:1", "admission": admission}],
        "ready": True,
        "blockers": [],
    })
    source = {
        "source_id": "capital:1",
        "known_value_amount": "100",
        "economic_projection_start_date": "2029-01-01",
        "retirement_target_date": TARGET,
        "annual_rate": "0",
        "return_basis": "NET",
        "price_basis": "NOMINAL",
        "compounding_convention": "ANNUAL_EFFECTIVE",
        "day_count_convention": "ACTUAL_365_25",
        "source_semantic_fingerprint": source_semantic,
        "projection_timing_context_fingerprint": timing,
        "projection_basis_decision_fingerprint": decision,
        "projection_basis_source_admission_fingerprint": admission,
        "elapsed_days": 365,
        "year_fraction_numerator": 1460,
        "year_fraction_denominator": 1461,
        "projection_factor": "1",
        "projected_amount": "100",
        "calculation_contract_version": capital_execution.CONTRACT,
        "numeric_contract_version": capital_execution.NUMERIC_CONTRACT,
    }
    source["projection_result_fingerprint"] = digest({
        key: source[key] for key in capital_execution.RESULT_FIELDS
    })
    result = {
        "contract_version": capital_execution.CONTRACT,
        "numeric_contract_version": capital_execution.NUMERIC_CONTRACT,
        "client_id": 8,
        "planning_calculation_input_fingerprint": H_A,
        "projection_basis_admission_fingerprint": aggregate_admission,
        "covered_source_count": 1,
        "projected_sources": [source],
        "aggregate_blockers": [],
        "execution_ready": True,
        "execution_status": "AUTHORITATIVE_RESULT",
        "execution_fingerprint": None,
    }
    result["execution_fingerprint"] = digest({
        "calculation_contract_version": capital_execution.CONTRACT,
        "numeric_contract_version": capital_execution.NUMERIC_CONTRACT,
        "planning_calculation_input_fingerprint": H_A,
        "projection_basis_admission_fingerprint": aggregate_admission,
        "execution_status": "AUTHORITATIVE_RESULT",
        "covered_source_count": 1,
        "sources": [{
            "source_id": "capital:1",
            "projection_result_fingerprint": source["projection_result_fingerprint"],
        }],
    })
    authority = {
        "planning_calculation_input_fingerprint": H_A,
        "covered_source_count": 1,
        "covered_capital_sources": [{
            "source_id": "capital:1",
            "projection_basis_source_admission_fingerprint": admission,
        }],
        "projection_basis_ready": True,
        "aggregate_blockers": [],
        "retirement_target_date": TARGET,
        "projection_basis_admission_fingerprint": aggregate_admission,
    }
    return authority, result, {
        "source_semantic": source_semantic,
        "timing": timing,
        "decision": decision,
        "source_admission": admission,
        "aggregate_admission": aggregate_admission,
    }


def accepted_capital_c1():
    source = {
        "source_id": "capital:1",
        "known_value_amount": "100",
        "economic_projection_start_date": "2029-01-01",
        "retirement_target_date": TARGET,
        "elapsed_days": 365,
        "year_fraction_numerator": 1460,
        "year_fraction_denominator": 1461,
        "annual_rate": "0",
        "return_basis": "NET",
        "price_basis": "NOMINAL",
        "compounding_convention": "ANNUAL_EFFECTIVE",
        "day_count_convention": "ACTUAL_365_25",
        "projection_factor": "1",
        "projected_amount": "100",
        "source_semantic_fingerprint": "1" * 64,
        "projection_timing_context_fingerprint": "2" * 64,
        "projection_basis_decision_fingerprint": "3" * 64,
        "projection_basis_source_admission_fingerprint": "d" * 64,
        "calculation_contract_version": capital_execution.CONTRACT,
        "numeric_contract_version": capital_execution.NUMERIC_CONTRACT,
        "projection_result_fingerprint": "cb8fc3c54acab7869142d566dfc982f0a6b3afb1082d77fd04d5b6b98dd4a90d",
    }
    result = {
        "contract_version": capital_execution.CONTRACT,
        "numeric_contract_version": capital_execution.NUMERIC_CONTRACT,
        "client_id": 7,
        "planning_calculation_input_fingerprint": H_A,
        "projection_basis_admission_fingerprint": "b" * 64,
        "covered_source_count": 1,
        "projected_sources": [source],
        "aggregate_blockers": [],
        "execution_ready": True,
        "execution_status": "AUTHORITATIVE_RESULT",
        "execution_fingerprint": "b3e43b84f9dd35f9f1f4e1e47eb963e02f4f01613f019ccca8bc9913e59c7772",
    }
    return result, subject._capital_domain(result, {"retirement_target_date": TARGET})


def accepted_capital_cb():
    result = {
        "contract_version": capital_execution.CONTRACT,
        "numeric_contract_version": capital_execution.NUMERIC_CONTRACT,
        "client_id": 7,
        "planning_calculation_input_fingerprint": H_A,
        "projection_basis_admission_fingerprint": "55d978945328409e2baa73a0457b710ed557476005ee7ffb5a054ee6ebf80bc3",
        "covered_source_count": 1,
        "projected_sources": [],
        "aggregate_blockers": [
            "PRICE_BASIS_MISSING_OR_INVALID",
            "PROJECTION_BASIS_NOT_READY",
            "PROJECTION_SOURCE_NOT_READY",
            "RATE_MISSING",
            "RETURN_BASIS_MISSING_OR_INVALID",
        ],
        "execution_ready": False,
        "execution_status": "BLOCKED_NO_RESULT",
        "execution_fingerprint": None,
    }
    return result, subject._capital_domain(result, {"retirement_target_date": TARGET})


def accepted_pension(source_ids=(), *, client_id=7, planning_fingerprint=H_A, target=TARGET):
    sources = []
    if "p1" in source_ids:
        sources.append({
            "source_id": "p1",
            "pension_start_date": "2029-01-01",
            "currency": "ILS",
            "monthly_amount_basis": {
                "authority_kind": "entered_monthly_amount",
                "base_amount_representation": {
                    "amount": "100.004",
                    "representation_kind": "exact_money",
                },
                "base_amount_semantic_fingerprint": H_B,
                "base_amount_source_fingerprint": H_C,
                "basis_authority_ready": True,
                "basis_blockers": [],
            },
            "temporal_authority": {
                "temporal_authority_kind": "none",
                "temporal_origin_date": "2029-01-01",
                "annual_rate": None,
                "temporal_semantic_fingerprint": H_D,
                "temporal_source_fingerprint": H_E,
                "temporal_authority_ready": True,
                "temporal_blockers": [],
            },
        })
    planning = {
        "planning_calculation_input_fingerprint": planning_fingerprint,
        "retirement_target": {
            "retirement_target_date": target,
            "retirement_target_ready": True,
        },
        "pension_inputs": sources,
    }
    return pension_portfolio.execute_from_planning_result(
        planning,
        client_id,
        planning_fingerprint,
    )


def pension_ready():
    coverage = {
        "coverage_check_state": "complete", "duplicate_source_ids": [],
        "expected_source_ids": [], "missing_source_ids": [],
        "returned_source_ids": [], "unexpected_source_ids": [],
    }
    result = {
        "schema_version": pension_portfolio.SCHEMA_VERSION,
        "client_id": 7,
        "result_state": "result_ready",
        "portfolio_identity_state": "complete",
        "portfolio_execution_fingerprint": None,
        "portfolio_result_fingerprint": None,
        "planning_calculation_input_fingerprint": H_A,
        "retirement_target_date": TARGET,
        "system_currency": "ILS",
        "aggregation_contract": pension_portfolio.AGGREGATION_CONTRACT,
        "coverage_evidence": coverage,
        "failure_evidence": None,
        "expected_source_count": 0,
        "returned_source_count": 0,
        "source_results": [],
        "source_entry_fingerprints": [],
        "payable_current_source_ids": [],
        "future_start_source_ids": [],
        "unresolved_source_ids": [],
        "blocked_source_ids": [],
        "total_completeness_state": "complete",
        "partial_reason_codes": [],
        "portfolio_blockers": [],
        "aggregate_unquantized_amount": "0",
        "payable_current_monthly_total": "0.00",
    }
    recertify_pension(result)
    return result


def pension_blocked():
    result = {
        "schema_version": pension_portfolio.SCHEMA_VERSION,
        "client_id": 7,
        "result_state": "block_no_result",
        "portfolio_identity_state": "incomplete",
        "portfolio_execution_fingerprint": None,
        "portfolio_result_fingerprint": None,
        "planning_calculation_input_fingerprint": H_A,
        "retirement_target_date": TARGET,
        "system_currency": "ILS",
        "aggregation_contract": pension_portfolio.AGGREGATION_CONTRACT,
        "coverage_evidence": {
            "coverage_check_state": "complete", "duplicate_source_ids": [],
            "expected_source_ids": ["p1"], "missing_source_ids": [],
            "returned_source_ids": ["p1"], "unexpected_source_ids": [],
        },
        "failure_evidence": {
            "current_planning_calculation_input_fingerprint": H_A,
            "failed_expected_source_id": "p1",
            "failure_detail_code": "PTE_SCHEMA_VERSION_INVALID",
            "failure_stage": "source_result_validation",
            "observed_source_id": "p1",
            "supplied_planning_calculation_input_fingerprint": H_A,
        },
        "expected_source_count": 1,
        "returned_source_count": 1,
        "source_results": [],
        "source_entry_fingerprints": [],
        "payable_current_source_ids": [],
        "future_start_source_ids": [],
        "unresolved_source_ids": [],
        "blocked_source_ids": [],
        "total_completeness_state": "unavailable",
        "partial_reason_codes": [],
        "portfolio_blockers": ["PORTFOLIO_SOURCE_RESULT_SCHEMA_INVALID"],
    }
    recertify_pension(result)
    assert result["portfolio_result_fingerprint"] == "e57dfa81f405a7bb34712e432fceb1f9b0c8c061452b493ad675fdedef78f16a"
    return result


def recertify_pension(result):
    if result["result_state"] == "result_ready":
        execution_payload = {
            "aggregation_contract": pension_portfolio.AGGREGATION_CONTRACT,
            "client_id": result["client_id"],
            "contract": pension_portfolio.EXECUTION_CONTRACT,
            "planning_calculation_input_fingerprint": result["planning_calculation_input_fingerprint"],
            "retirement_target_date": result["retirement_target_date"],
            "source_identities": [],
            "system_currency": "ILS",
            "total_completeness_state": result["total_completeness_state"],
        }
        result["portfolio_execution_fingerprint"] = digest(execution_payload)
        keys = (
            "schema_version", "client_id", "result_state", "portfolio_identity_state",
            "portfolio_execution_fingerprint", "planning_calculation_input_fingerprint",
            "retirement_target_date", "system_currency", "aggregation_contract",
            "coverage_evidence", "expected_source_count", "returned_source_count",
            "source_entry_fingerprints", "payable_current_source_ids",
            "future_start_source_ids", "unresolved_source_ids", "blocked_source_ids",
            "total_completeness_state", "partial_reason_codes", "portfolio_blockers",
            "aggregate_unquantized_amount", "payable_current_monthly_total", "failure_evidence",
        )
    else:
        keys = (
            "aggregation_contract", "blocked_source_ids", "client_id", "coverage_evidence",
            "expected_source_count", "failure_evidence", "future_start_source_ids",
            "partial_reason_codes", "payable_current_source_ids",
            "planning_calculation_input_fingerprint", "portfolio_blockers",
            "portfolio_execution_fingerprint", "portfolio_identity_state", "result_state",
            "retirement_target_date", "returned_source_count", "schema_version",
            "source_entry_fingerprints", "system_currency", "total_completeness_state",
            "unresolved_source_ids",
        )
    result["portfolio_result_fingerprint"] = digest({
        "contract": pension_portfolio.RESULT_CONTRACT,
        **{key: result[key] for key in keys},
    })


def configure(monkeypatch, *, snapshot=None, capital=None, authority=None, pension=None):
    snapshot = plan() if snapshot is None else snapshot
    authority, capital = capital_result() if capital is None else (authority, capital)
    pension = pension_ready() if pension is None else pension
    calls = []
    monkeypatch.setattr(subject.planning_input_service, "read", lambda db, client_id: calls.append("planning") or snapshot)
    monkeypatch.setattr(subject.capital_basis, "derive", lambda db, client_id, value: calls.append("basis") or authority)
    monkeypatch.setattr(subject.capital_execution, "execute", lambda client_id, value, auth: calls.append("capital") or capital)
    monkeypatch.setattr(subject.pension_portfolio, "execute_from_planning_result", lambda value, client_id, expected: calls.append("pension") or pension)
    return calls


def test_one_snapshot_read_and_same_object_drives_both_domains(monkeypatch):
    snapshot = plan()
    authority, capital = capital_result()
    pension = pension_ready()
    calls = []
    monkeypatch.setattr(subject.planning_input_service, "read", lambda db, client_id: calls.append(("planning", None)) or snapshot)
    monkeypatch.setattr(subject.capital_basis, "derive", lambda db, client_id, value: calls.append(("basis", value)) or authority)
    monkeypatch.setattr(subject.capital_execution, "execute", lambda client_id, value, auth: calls.append(("capital", value)) or capital)
    monkeypatch.setattr(subject.pension_portfolio, "execute_from_planning_result", lambda value, client_id, expected: calls.append(("pension", value)) or pension)

    result = subject.read(object(), 7, H_A)

    assert [name for name, _ in calls] == ["planning", "basis", "capital", "pension"]
    assert all(value is snapshot for _, value in calls[1:])
    assert result["result_state"] == "result_ready"
    assert result["resource_completeness_state"] == "complete"


def test_snapshot_read_exception_is_canonical_and_stops(monkeypatch):
    monkeypatch.setattr(subject.planning_input_service, "read", lambda *args: (_ for _ in ()).throw(RuntimeError("secret")))
    result = subject.read(object(), 7, H_A)
    assert result["resource_state_blockers"] == ["RESOURCE_STATE_PLANNING_SNAPSHOT_UNAVAILABLE"]
    assert result["failure_evidence"] == {
        "current_planning_calculation_input_fingerprint": None,
        "supplied_planning_calculation_input_fingerprint": H_A,
        "current_retirement_target_date": None,
        "failed_domain": None,
        "failure_stage": "snapshot_admission",
        "failure_detail_code": "PLANNING_SNAPSHOT_READ_EXCEPTION",
        "expected_identity": None,
        "observed_identity": None,
    }
    assert result["capital_domain"] is result["pension_domain"] is None
    assert result["resource_state_result_fingerprint"] == "8b0701832edb12cbe9f1fe71d5c2ddf395d982d5b631988840f59645b058d1db"


@pytest.mark.parametrize("snapshot", [None, [], {}, {"contract_version": planning_input_service.CONTRACT, "client_id": 7, "planning_calculation_input_fingerprint": "bad", "retirement_target": {}}])
def test_invalid_snapshot_precedes_stale_identity(monkeypatch, snapshot):
    monkeypatch.setattr(subject.planning_input_service, "read", lambda *args: snapshot)
    result = subject.read(object(), 7, H_B)
    assert result["failure_evidence"]["failure_detail_code"] == "PLANNING_SNAPSHOT_SCHEMA_INVALID"
    assert result["planning_calculation_input_fingerprint"] is None
    assert result["failure_evidence"]["supplied_planning_calculation_input_fingerprint"] == H_B


@pytest.mark.parametrize("snapshot", [None, {"contract_version": planning_input_service.CONTRACT, "client_id": 7, "planning_calculation_input_fingerprint": "bad", "retirement_target": {}}])
def test_invalid_snapshot_goldens_s2_s3(monkeypatch, snapshot):
    monkeypatch.setattr(subject.planning_input_service, "read", lambda *args: snapshot)
    result = subject.read(object(), 7, H_A)
    assert result["resource_state_result_fingerprint"] == "44cb7df4781b624a642acf5885313ded80f16335d8c998a3eb1f65e3dc06e637"


def test_stale_identity_precedes_target(monkeypatch):
    snapshot = plan()
    snapshot["retirement_target"] = None
    monkeypatch.setattr(subject.planning_input_service, "read", lambda *args: snapshot)
    result = subject.read(object(), 7, H_B)
    assert result["resource_state_blockers"] == ["RESOURCE_STATE_PLANNING_INPUT_IDENTITY_STALE"]
    assert result["failure_evidence"]["expected_identity"] == H_B
    assert result["failure_evidence"]["observed_identity"] == H_A


def test_stale_identity_golden_s4(monkeypatch):
    monkeypatch.setattr(subject.planning_input_service, "read", lambda *args: plan())
    result = subject.read(object(), 7, "9" * 64)
    assert result["retirement_target_date"] == TARGET
    assert result["failure_evidence"]["current_retirement_target_date"] == TARGET
    assert result["resource_state_result_fingerprint"] == "105434484ca0e2329909293ec3f24f86479a96997984d994cf7e65797ea08ca1"


def test_target_not_ready_stops_before_capital(monkeypatch):
    snapshot = plan()
    snapshot["retirement_target"] = {"retirement_target_date": None, "retirement_target_ready": False}
    calls = configure(monkeypatch, snapshot=snapshot)
    result = subject.read(object(), 7, H_A)
    assert calls == ["planning"]
    assert result["resource_state_blockers"] == ["RESOURCE_STATE_RETIREMENT_TARGET_NOT_READY"]


@pytest.mark.parametrize("phase", ["derive", "execute"])
def test_capital_exceptions_share_canonical_boundary_and_stop_pension(monkeypatch, phase):
    calls = configure(monkeypatch)
    if phase == "derive":
        monkeypatch.setattr(subject.capital_basis, "derive", lambda *args: (_ for _ in ()).throw(RuntimeError("derive")))
    else:
        monkeypatch.setattr(subject.capital_execution, "execute", lambda *args: (_ for _ in ()).throw(RuntimeError("execute")))
    result = subject.read(object(), 7, H_A)
    assert "pension" not in calls
    assert result["resource_state_blockers"] == ["RESOURCE_STATE_CAPITAL_EXECUTION_ERROR"]
    assert result["failure_evidence"]["failure_detail_code"] == "CAPITAL_EXECUTOR_EXCEPTION"
    assert result["capital_domain"] is result["pension_domain"] is None
    assert result["resource_state_result_fingerprint"] == "d5d7d2c3c0f0588f31256e46a3a61365e908cf8ac5e9b8dfdecd8b325775dbe7"


@pytest.mark.parametrize(("source_ids", "blocked", "state"), [
    (("capital:1",), False, "complete"),
    ((), False, "complete"),
    (("capital:1",), True, "blocked"),
])
def test_capital_ready_empty_and_blocked_contracts(monkeypatch, source_ids, blocked, state):
    authority, capital = capital_result(source_ids, blocked=blocked)
    configure(monkeypatch, capital=capital, authority=authority)
    result = subject.read(object(), 7, H_A)
    assert result["result_state"] == "result_ready"
    assert result["capital_domain"]["domain_state"] == state


def test_blocked_domain_identity_contracts(monkeypatch):
    authority, capital = capital_result(("capital:1",), blocked=True)
    pension = pension_blocked()
    configure(monkeypatch, capital=capital, authority=authority, pension=pension)

    result = subject.read(object(), 7, H_A)

    assert result["result_state"] == "result_ready"
    assert result["resource_completeness_state"] == "blocked"
    assert result["capital_domain"]["identity_kind"] == "blocked_result_fingerprint"
    assert result["capital_domain"]["identity_fingerprint"] == result["capital_domain"]["domain_result_fingerprint"]
    assert result["pension_domain"]["identity_kind"] == "blocked_result_fingerprint"
    assert result["pension_domain"]["identity_fingerprint"] == pension["portfolio_result_fingerprint"]
    assert pension["portfolio_result_fingerprint"] == (
        "e57dfa81f405a7bb34712e432fceb1f9b0c8c061452b493ad675fdedef78f16a"
    )
    assert result["pension_domain"]["domain_result_fingerprint"] == pension["portfolio_result_fingerprint"]


def test_exact_resource_execution_preimages_and_goldens_d_f():
    _, capital_domain = accepted_capital_cb()
    p1 = accepted_pension(("p1",))
    p1_domain = subject._pension_domain(p1)
    pb_domain = subject._pension_domain(pension_blocked())

    assert capital_domain["domain_result_fingerprint"] == (
        "5a37bbeb1b56bc0202c86a6d86f1a6c8b1a455e32a0e3bc67f1cf032c1141a30"
    )
    assert p1["portfolio_execution_fingerprint"] == (
        "daefe24dd720e9d0759f58e121e1f5022d8974dd2d01ace43520c425c497a6ce"
    )
    assert p1["portfolio_result_fingerprint"] == (
        "7b8668ad77428d45464b67b61133c1ce5a5f3454e33637a8b935e3e099fd1807"
    )

    expected_d = {
        "contract": subject.EXECUTION_CONTRACT,
        "client_id": 7,
        "planning_calculation_input_fingerprint": H_A,
        "retirement_target_date": TARGET,
        "resource_completeness_state": "blocked",
        "domains": [
            {
                "domain_kind": "capital",
                "domain_state": "blocked",
                "identity_kind": "blocked_result_fingerprint",
                "identity_fingerprint": "5a37bbeb1b56bc0202c86a6d86f1a6c8b1a455e32a0e3bc67f1cf032c1141a30",
                "domain_result_fingerprint": "5a37bbeb1b56bc0202c86a6d86f1a6c8b1a455e32a0e3bc67f1cf032c1141a30",
            },
            {
                "domain_kind": "pension",
                "domain_state": "complete",
                "identity_kind": "execution_fingerprint",
                "identity_fingerprint": "daefe24dd720e9d0759f58e121e1f5022d8974dd2d01ace43520c425c497a6ce",
                "domain_result_fingerprint": "7b8668ad77428d45464b67b61133c1ce5a5f3454e33637a8b935e3e099fd1807",
            },
        ],
    }
    expected_f = copy.deepcopy(expected_d)
    expected_f["domains"][1] = {
        "domain_kind": "pension",
        "domain_state": "blocked",
        "identity_kind": "blocked_result_fingerprint",
        "identity_fingerprint": "e57dfa81f405a7bb34712e432fceb1f9b0c8c061452b493ad675fdedef78f16a",
        "domain_result_fingerprint": "e57dfa81f405a7bb34712e432fceb1f9b0c8c061452b493ad675fdedef78f16a",
    }

    actual_d = subject._execution_payload(7, H_A, TARGET, "blocked", capital_domain, p1_domain)
    actual_f = subject._execution_payload(7, H_A, TARGET, "blocked", capital_domain, pb_domain)
    assert actual_d == expected_d
    assert actual_f == expected_f
    assert digest(actual_d) == "a2a76152588193a450087fca36c7e147209a416931842bc1110a9cf2a6ba4383"
    assert digest(actual_f) == "2a600f906c4bcd1d4e575ff7d8d45cfcfec500629d771a1fe962d79371240b94"

    d = subject._ready(7, H_A, TARGET, capital_domain, p1_domain)
    f = subject._ready(7, H_A, TARGET, capital_domain, pb_domain)
    assert d["resource_state_execution_fingerprint"] == (
        "a2a76152588193a450087fca36c7e147209a416931842bc1110a9cf2a6ba4383"
    )
    assert d["resource_state_result_fingerprint"] == (
        "acb6b3ecf5ca8ae6de908023416e49e1f228bcb9b8a23132c7d8e6313a26b236"
    )
    assert f["resource_state_execution_fingerprint"] == (
        "2a600f906c4bcd1d4e575ff7d8d45cfcfec500629d771a1fe962d79371240b94"
    )
    assert f["resource_state_result_fingerprint"] == (
        "8c7f0fcd8956a5903e2ca3dc59592bb2b8e69b977165ec4c78a4545564abd95b"
    )


def test_corrected_resource_regression_goldens_h_through_l_and_pension_boundaries(monkeypatch):
    c1, capital_domain = accepted_capital_c1()
    assert c1["projected_sources"][0]["projection_result_fingerprint"] == (
        "cb8fc3c54acab7869142d566dfc982f0a6b3afb1082d77fd04d5b6b98dd4a90d"
    )
    assert capital_domain["domain_result_fingerprint"] == (
        "15cf4fb3d67e0c213cd2847c6a8f5ee01a163990baa94f450f82c4c96176a2ec"
    )

    ph_domain = subject._pension_domain(accepted_pension(planning_fingerprint=H_B))
    pi_domain = subject._pension_domain(accepted_pension(target="2031-01-01"))
    p1 = accepted_pension(("p1",))
    p1_domain = subject._pension_domain(p1)
    p1_client_8 = accepted_pension(("p1",), client_id=8)
    p1_client_8_domain = subject._pension_domain(p1_client_8)

    h = subject._fatal(
        7, H_A, H_A, TARGET,
        "RESOURCE_STATE_CROSS_DOMAIN_PLANNING_IDENTITY_MISMATCH",
        "cross_domain_validation", "CROSS_DOMAIN_PLANNING_FINGERPRINT_MISMATCH",
        domain="pension", expected=H_A, observed=H_B,
        capital_domain=capital_domain, pension_domain=ph_domain,
    )
    i = subject._fatal(
        7, H_A, H_A, TARGET,
        "RESOURCE_STATE_CROSS_DOMAIN_TARGET_DATE_MISMATCH",
        "cross_domain_validation", "CROSS_DOMAIN_RETIREMENT_TARGET_DATE_MISMATCH",
        domain="pension", expected=TARGET, observed="2031-01-01",
        capital_domain=capital_domain, pension_domain=pi_domain,
    )
    j = subject._fatal(
        7, H_A, H_A, TARGET, "RESOURCE_STATE_CAPITAL_RESULT_INVALID",
        "capital_validation", "CAPITAL_EXECUTION_FINGERPRINT_MISMATCH",
        domain="capital", expected=c1["execution_fingerprint"], observed="0" * 64,
    )
    k = subject._fatal(
        7, H_A, H_A, TARGET, "RESOURCE_STATE_PENSION_RESULT_INVALID",
        "pension_validation", "PENSION_RESULT_FINGERPRINT_MISMATCH",
        domain="pension", expected=p1["portfolio_result_fingerprint"], observed="0" * 64,
        capital_domain=capital_domain,
    )
    l = subject._fatal(
        7, H_A, H_A, TARGET, "RESOURCE_STATE_IDENTITY_ERROR",
        "resource_identity", "RESOURCE_EXECUTION_IDENTITY_ASSEMBLY_FAILED",
        capital_domain=capital_domain, pension_domain=p1_domain,
    )
    pension_exception = subject._fatal(
        7, H_A, H_A, TARGET, "RESOURCE_STATE_PENSION_EXECUTION_ERROR",
        "pension_execution", "PENSION_EXECUTOR_EXCEPTION",
        domain="pension", capital_domain=capital_domain,
    )
    pension_client_mismatch = subject._fatal(
        7, H_A, H_A, TARGET, "RESOURCE_STATE_CROSS_DOMAIN_CLIENT_ID_MISMATCH",
        "cross_domain_validation", "CROSS_DOMAIN_CLIENT_ID_MISMATCH",
        domain="pension", expected="7", observed="8",
        capital_domain=capital_domain, pension_domain=p1_client_8_domain,
    )

    assert ph_domain["domain_result_fingerprint"] == (
        "09ea3d2caa9d60622d4dcaa253839a8e95b0ba232ee2863b7e94d68b40f99a98"
    )
    assert pi_domain["domain_result_fingerprint"] == (
        "2b2183d20889be5975af24cb92461d6adc9dd7606913f236cfe515b74f2fcc4f"
    )
    assert h["resource_state_result_fingerprint"] == "835630ad739537d6b6c094182bd7f4f724e7caa091ea5b885b978ed499301d3b"
    assert i["resource_state_result_fingerprint"] == "770a1bfd5618cb651387762486ec5a4c2a83af52148415329371bf07ce1b2ec5"
    assert j["resource_state_result_fingerprint"] == "4c706c896fb81bbfa7d31f73921f6f92882a9ad806dd67224403fdcf8784af83"
    assert k["resource_state_result_fingerprint"] == "b34896edeeff3065fa2a52d4bf22dc293bf0d0305774845c9f6570124152ad6f"
    assert l["resource_state_result_fingerprint"] == "ec3430663f98f82ef34c1c58feb7db8631be391e485606903f9254b8005fc0d5"
    assert pension_exception["resource_state_result_fingerprint"] == (
        "0ac96d06ad109434bfbf72643c28e234a3e3474bafa1b8f914ed80dc79b78dc4"
    )
    assert p1_client_8["portfolio_execution_fingerprint"] == (
        "5d784e94c671b2af72d9fcdcd5caf6506ad7079c42594fee2ad6ef8a7d4f07b5"
    )
    assert p1_client_8["portfolio_result_fingerprint"] == (
        "19e2df61389be73bf578e1b0498dad7e68fffe79b29f50651e3571d816ff76b4"
    )
    assert pension_client_mismatch["resource_state_result_fingerprint"] == (
        "3f207095dff29a9f5f514814a6b48e2a01f8b61b89c3bc9f8aefdbc95e4132ac"
    )

    authority, capital, _ = capital_client_mismatch_v2()
    configure(monkeypatch, capital=capital, authority=authority)
    assert subject.read(object(), 7, H_A)["resource_state_result_fingerprint"] == (
        "30371169f0e1614b9f42731cc8f0d70de14573937e661930461d16f5c080d316"
    )


def assembled_capital(sources):
    authority = capital_authority([source["source_id"] for source in sources])
    for target, source in zip(authority["covered_capital_sources"], sources):
        target["projection_basis_source_admission_fingerprint"] = source["projection_basis_source_admission_fingerprint"]
    authority["projection_basis_admission_fingerprint"] = digest({
        "contract": capital_basis.CONTRACT,
        "planning_calculation_input_fingerprint": H_A,
        "covered_source_count": len(sources),
        "sources": [{"source_id": source["source_id"], "admission": source["projection_basis_source_admission_fingerprint"]} for source in sources],
        "ready": True,
        "blockers": [],
    })
    result = capital_result()[1]
    result.update(
        projection_basis_admission_fingerprint=authority["projection_basis_admission_fingerprint"],
        covered_source_count=len(sources), projected_sources=sources,
        execution_status="AUTHORITATIVE_RESULT", execution_ready=True,
    )
    result["execution_fingerprint"] = digest({
        "calculation_contract_version": capital_execution.CONTRACT,
        "numeric_contract_version": capital_execution.NUMERIC_CONTRACT,
        "planning_calculation_input_fingerprint": H_A,
        "projection_basis_admission_fingerprint": result["projection_basis_admission_fingerprint"],
        "execution_status": "AUTHORITATIVE_RESULT", "covered_source_count": len(sources),
        "sources": [{"source_id": source["source_id"], "projection_result_fingerprint": source["projection_result_fingerprint"]} for source in sources],
    })
    return authority, result


def test_capital_source_priority_p1_bad_a_fingerprint_before_bad_b_shape():
    a, b = capital_source("a"), capital_source("b")
    a["projection_result_fingerprint"] = "0" * 64
    b.pop("annual_rate")
    authority, result = assembled_capital([a, b])
    assert subject._validate_capital(result, authority)[0] == "CAPITAL_SOURCE_RESULT_FINGERPRINT_MISMATCH"


def test_capital_source_priority_p2_bad_a_shape_before_bad_b_fingerprint():
    a, b = capital_source("a"), capital_source("b")
    a.pop("annual_rate")
    b["projection_result_fingerprint"] = "0" * 64
    authority, result = assembled_capital([a, b])
    assert subject._validate_capital(result, authority)[0] == "CAPITAL_RESULT_SCHEMA_INVALID"


@pytest.mark.parametrize(("bad_shape", "bad_fingerprint", "expected"), [
    ("b", None, "CAPITAL_RESULT_SCHEMA_INVALID"),
    (None, "b", "CAPITAL_SOURCE_RESULT_FINGERPRINT_MISMATCH"),
])
def test_capital_source_priority_p3_p4(bad_shape, bad_fingerprint, expected):
    a, b = capital_source("a"), capital_source("b")
    if bad_shape:
        b.pop("annual_rate")
    if bad_fingerprint:
        b["projection_result_fingerprint"] = "0" * 64
    authority, result = assembled_capital([a, b])
    assert subject._validate_capital(result, authority)[0] == expected


@pytest.mark.parametrize("sources", [
    [capital_source("b"), capital_source("a")],
    [capital_source("a"), capital_source("a")],
])
def test_capital_source_priority_p5_collection_before_fingerprint(sources):
    sources[0]["projection_result_fingerprint"] = "0" * 64
    authority, result = assembled_capital(sources)
    assert subject._validate_capital(result, authority)[0] == "CAPITAL_RESULT_SCHEMA_INVALID"


def test_capital_execution_fingerprint_mismatch(monkeypatch):
    authority, capital = capital_result()
    capital["execution_fingerprint"] = "0" * 64
    configure(monkeypatch, capital=capital, authority=authority)
    result = subject.read(object(), 7, H_A)
    assert result["failure_evidence"]["failure_detail_code"] == "CAPITAL_EXECUTION_FINGERPRINT_MISMATCH"
    assert result["capital_domain"] is result["pension_domain"] is None


def test_capital_client_mismatch_v2_cross_domain_golden(monkeypatch):
    authority, capital, chain = capital_client_mismatch_v2()
    calls = configure(monkeypatch, capital=capital, authority=authority)

    assert chain == {
        "source_semantic": "122074f3c12c40623b4b4626be7d37590cf3198ba553a21aeba035d1c5bcb748",
        "timing": "3f37fc19b72f65de2ed65f74f338bc4bdb8f51439ae957d0f67b597e05abeb21",
        "decision": "616323b5f41bc4a64b8946c7bb0dae60e887b5b1f230fb7944995d9716ff338e",
        "source_admission": "0772e1b091c0f0110a5b85e7aa009243c654aa968ece1569b336beae0a4e3fe5",
        "aggregate_admission": "22a6bf52938542178441e25c5b11d7e926310eef7ff72262280ec3ebcccef1cc",
    }
    assert capital["projected_sources"][0]["projection_result_fingerprint"] == (
        "2bf894db3d5a3e74f5e81ad26de41cd9274cbbd1a4d140e08149b4eb8feb78f4"
    )
    assert capital["execution_fingerprint"] == (
        "9dc5a7e3f8a981c0fcc694361dc3d00b00f00ce7a927cc663a4d466c1d985332"
    )
    assert subject._validate_capital(capital, authority) == (None, None, None)
    assert subject._capital_domain_payload(capital, authority) == {
        "contract": subject.CAPITAL_DOMAIN_CONTRACT,
        "client_id": 8,
        "planning_calculation_input_fingerprint": H_A,
        "retirement_target_date": TARGET,
        "capital_execution_contract_version": capital_execution.CONTRACT,
        "numeric_contract_version": capital_execution.NUMERIC_CONTRACT,
        "projection_basis_admission_fingerprint": chain["aggregate_admission"],
        "execution_status": "AUTHORITATIVE_RESULT",
        "execution_ready": True,
        "capital_execution_fingerprint": capital["execution_fingerprint"],
        "covered_source_count": 1,
        "aggregate_blockers": [],
        "projected_source_results": [{
            "source_id": "capital:1",
            "projection_result_fingerprint": capital["projected_sources"][0]["projection_result_fingerprint"],
        }],
    }
    assert digest(subject._capital_domain_payload(capital, authority)) == (
        "cae1bde71216f3e1cf249b92d43c44336b59cecd07411dcc5d259179772382c1"
    )

    result = subject.read(object(), 7, H_A)

    assert calls == ["planning", "basis", "capital"]
    assert result["resource_state_blockers"] == ["RESOURCE_STATE_CROSS_DOMAIN_CLIENT_ID_MISMATCH"]
    assert result["failure_evidence"]["failure_detail_code"] == "CROSS_DOMAIN_CLIENT_ID_MISMATCH"
    assert result["failure_evidence"]["failure_stage"] == "cross_domain_validation"
    assert result["failure_evidence"]["failed_domain"] == "capital"
    assert result["failure_evidence"]["expected_identity"] == "7"
    assert result["failure_evidence"]["observed_identity"] == "8"
    assert result["capital_domain"]["domain_result_fingerprint"] == (
        "cae1bde71216f3e1cf249b92d43c44336b59cecd07411dcc5d259179772382c1"
    )
    assert result["pension_domain"] is None
    assert result["resource_state_result_fingerprint"] == (
        "30371169f0e1614b9f42731cc8f0d70de14573937e661930461d16f5c080d316"
    )


@pytest.mark.parametrize("malformed", [None, True, "8", 8.0])
def test_malformed_capital_client_remains_intrinsic_schema_failure(monkeypatch, malformed):
    authority, capital, _ = capital_client_mismatch_v2()
    capital["client_id"] = malformed
    calls = configure(monkeypatch, capital=capital, authority=authority)

    result = subject.read(object(), 7, H_A)

    assert calls == ["planning", "basis", "capital"]
    assert result["resource_state_blockers"] == ["RESOURCE_STATE_CAPITAL_RESULT_INVALID"]
    assert result["failure_evidence"]["failure_stage"] == "capital_validation"
    assert result["failure_evidence"]["failure_detail_code"] == "CAPITAL_RESULT_SCHEMA_INVALID"
    assert result["capital_domain"] is result["pension_domain"] is None


def test_missing_capital_client_remains_intrinsic_schema_failure(monkeypatch):
    authority, capital, _ = capital_client_mismatch_v2()
    del capital["client_id"]
    calls = configure(monkeypatch, capital=capital, authority=authority)

    result = subject.read(object(), 7, H_A)

    assert calls == ["planning", "basis", "capital"]
    assert result["resource_state_blockers"] == ["RESOURCE_STATE_CAPITAL_RESULT_INVALID"]
    assert result["failure_evidence"]["failure_detail_code"] == "CAPITAL_RESULT_SCHEMA_INVALID"
    assert result["capital_domain"] is result["pension_domain"] is None


@pytest.mark.parametrize(("kind", "detail"), [
    ("planning", "CAPITAL_PLANNING_FINGERPRINT_MISMATCH"),
    ("target", "CAPITAL_RETIREMENT_TARGET_DATE_MISMATCH"),
])
def test_capital_cross_domain_priority_and_retention(monkeypatch, kind, detail):
    authority, capital = capital_result()
    if kind == "client":
        capital["client_id"] = 8
    elif kind == "planning":
        capital["planning_calculation_input_fingerprint"] = H_B
        capital["execution_fingerprint"] = digest(subject._capital_execution_payload(capital))
    else:
        authority["retirement_target_date"] = "2031-01-01"
    calls = configure(monkeypatch, capital=capital, authority=authority)
    result = subject.read(object(), 7, H_A)
    assert result["failure_evidence"]["failure_detail_code"] == detail
    assert result["capital_domain"] is not None and result["pension_domain"] is None
    assert "pension" not in calls


def test_pension_executor_exception_retains_capital(monkeypatch):
    calls = configure(monkeypatch)
    monkeypatch.setattr(subject.pension_portfolio, "execute_from_planning_result", lambda *args: (_ for _ in ()).throw(RuntimeError("pension")))
    result = subject.read(object(), 7, H_A)
    assert result["failure_evidence"]["failure_detail_code"] == "PENSION_EXECUTOR_EXCEPTION"
    assert result["capital_domain"] is not None and result["pension_domain"] is None


def test_pension_schema_and_result_fingerprint_failures_retain_capital(monkeypatch):
    pension = pension_ready()
    pension["extra"] = True
    configure(monkeypatch, pension=pension)
    schema = subject.read(object(), 7, H_A)
    assert schema["failure_evidence"]["failure_detail_code"] == "PENSION_RESULT_SCHEMA_INVALID"
    assert schema["capital_domain"] is not None and schema["pension_domain"] is None

    pension = pension_ready()
    pension["portfolio_result_fingerprint"] = "0" * 64
    configure(monkeypatch, pension=pension)
    fingerprint = subject.read(object(), 7, H_A)
    assert fingerprint["failure_evidence"]["failure_detail_code"] == "PENSION_RESULT_FINGERPRINT_MISMATCH"


def test_pension_execution_fingerprint_mismatch_uses_result_detail(monkeypatch):
    pension = pension_ready()
    pension["portfolio_execution_fingerprint"] = "0" * 64
    recertify_pension(result := pension)
    result["portfolio_execution_fingerprint"] = "0" * 64
    keys = tuple(key for key in pension_portfolio._ready_result_payload(result) if key != "contract")
    result["portfolio_result_fingerprint"] = digest({"contract": pension_portfolio.RESULT_CONTRACT, **{key: result[key] for key in keys}})
    configure(monkeypatch, pension=result)
    output = subject.read(object(), 7, H_A)
    assert output["failure_evidence"]["failure_detail_code"] == "PENSION_RESULT_FINGERPRINT_MISMATCH"


@pytest.mark.parametrize(("kind", "detail"), [
    ("client", "CROSS_DOMAIN_CLIENT_ID_MISMATCH"),
    ("planning", "CROSS_DOMAIN_PLANNING_FINGERPRINT_MISMATCH"),
    ("target", "CROSS_DOMAIN_RETIREMENT_TARGET_DATE_MISMATCH"),
])
def test_pension_cross_domain_mismatch_retains_both_domains(monkeypatch, kind, detail):
    pension = pension_ready()
    if kind == "client":
        pension["client_id"] = 8
    elif kind == "planning":
        pension["planning_calculation_input_fingerprint"] = H_B
    else:
        pension["retirement_target_date"] = "2031-01-01"
    recertify_pension(pension)
    configure(monkeypatch, pension=pension)
    result = subject.read(object(), 7, H_A)
    assert result["failure_evidence"]["failure_detail_code"] == detail
    assert result["capital_domain"] is not None and result["pension_domain"] is not None


def test_resource_identity_failure_retains_both_domains(monkeypatch):
    configure(monkeypatch)
    original = subject._fingerprint
    monkeypatch.setattr(subject, "_fingerprint", lambda payload: (_ for _ in ()).throw(ValueError("identity")) if payload.get("contract") == subject.EXECUTION_CONTRACT else original(payload))
    result = subject.read(object(), 7, H_A)
    assert result["resource_state_blockers"] == ["RESOURCE_STATE_IDENTITY_ERROR"]
    assert result["failure_evidence"]["failure_stage"] == "resource_identity"
    assert result["capital_domain"] is not None and result["pension_domain"] is not None


def test_capital_wrapper_and_final_result_fingerprint_boundaries(monkeypatch):
    authority, capital = capital_result()
    original = subject._fingerprint
    monkeypatch.setattr(subject, "_fingerprint", lambda payload: (_ for _ in ()).throw(TypeError("domain")) if payload.get("contract") == subject.CAPITAL_DOMAIN_CONTRACT else original(payload))
    with pytest.raises(subject.CapitalDomainResultFingerprintConstructionError):
        subject._capital_domain(capital, authority)

    monkeypatch.setattr(subject, "canonical_bytes", lambda value: (_ for _ in ()).throw(TypeError("result")))
    with pytest.raises(subject.ResourceStateResultFingerprintConstructionError):
        subject._fatal(7, None, H_A, None, "RESOURCE_STATE_PLANNING_SNAPSHOT_UNAVAILABLE", "snapshot_admission", "PLANNING_SNAPSHOT_READ_EXCEPTION")


def test_public_signature_has_no_injected_domain_results():
    assert list(inspect.signature(subject.read).parameters) == [
        "db", "client_id", "expected_planning_calculation_input_fingerprint",
    ]


def test_result_and_failure_schemas_are_exact(monkeypatch):
    configure(monkeypatch)
    result = subject.read(object(), 7, H_A)
    assert set(result) == {
        "schema_version", "client_id", "result_state", "resource_completeness_state",
        "planning_calculation_input_fingerprint", "retirement_target_date", "capital_domain",
        "pension_domain", "resource_state_execution_fingerprint", "resource_state_result_fingerprint",
        "resource_state_reason_codes", "resource_state_blockers", "failure_evidence",
    }
    monkeypatch.setattr(subject.planning_input_service, "read", lambda *args: None)
    fatal = subject.read(object(), 7, H_A)
    assert set(fatal) == set(result)
    assert set(fatal["failure_evidence"]) == {
        "current_planning_calculation_input_fingerprint",
        "supplied_planning_calculation_input_fingerprint", "current_retirement_target_date",
        "failed_domain", "failure_stage", "failure_detail_code", "expected_identity", "observed_identity",
    }


def test_service_is_read_only_and_has_no_persistence_or_arithmetic_dependency():
    source = inspect.getsource(subject).lower()
    assert "sqlalchemy" not in source
    assert "alembic" not in source
    assert "decimal(" not in source
