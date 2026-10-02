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


@pytest.mark.parametrize(("kind", "detail"), [
    ("client", "CAPITAL_CLIENT_ID_MISMATCH"),
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
    ("client", "PENSION_CLIENT_ID_MISMATCH"),
    ("planning", "PENSION_PLANNING_FINGERPRINT_MISMATCH"),
    ("target", "PENSION_RETIREMENT_TARGET_DATE_MISMATCH"),
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
