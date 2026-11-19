from copy import deepcopy

import pytest

from app.services import retirement_monthly_income_target_service as target_service
from app.services import retirement_target_date_income_comparison_basis_service as basis_service
from app.services.planning_input_service import fingerprint
from app.services.scenario_snapshot_candidate_service import ScenarioSnapshotError
from app.services.scenario_stage6_monthly_comparison_service import (
    compare_scenario_monthly_cashflows,
)


def cashflow(scenario_id, version, amounts=("5000.00", "5000.00"), *, blocked=None,
             client_id=7, source_id="income:1"):
    source = {
        "source_id": source_id, "source_kind": "KNOWN_RECURRING_INCOME",
        "decision_id": None, "recurring_income_id": 1, "label": "הכנסה חודשית",
        "monthly_amount_gross_ils": amounts[0], "income_basis": "GROSS",
        "price_basis": "STATED_NOMINAL_NO_INDEXATION", "start_date": "2030-01-01",
        "end_date": None, "source_reference_date": "2029-12-31",
        "authority_fingerprint": "a" * 64, "source_state": "READY", "blocker_codes": [],
    }
    rows = []
    for index, month in enumerate(("2030-01", "2030-02")):
        amount = amounts[index]
        if blocked == month:
            rows.append({
                "month": month, "cashflow_state": "BLOCKED", "contributions": [],
                "known_income_subtotal_ils": "0.00",
                "calculated_pension_subtotal_ils": "0.00",
                "gross_income_total_ils": None, "blocker_codes": ["SOURCE_BLOCKED"],
            })
        else:
            rows.append({
                "month": month, "cashflow_state": "COMPLETE",
                "contributions": [{
                    "source_id": source_id, "source_kind": "KNOWN_RECURRING_INCOME",
                    "amount_monthly_gross_ils": amount, "contribution_state": "KNOWN",
                }],
                "known_income_subtotal_ils": amount,
                "calculated_pension_subtotal_ils": "0.00",
                "gross_income_total_ils": amount, "blocker_codes": [],
            })
    evidence = {
        "schema_version": "STAGE6_MONTHLY_RETIREMENT_CASHFLOW_V1",
        "client_id": client_id, "scenario_id": scenario_id, "scenario_version": version,
        "manifest_fingerprint": ("b" if scenario_id == "a" else "c") * 64,
        "start_month": "2030-01", "end_month": "2030-02",
        "cashflow_state": "PARTIAL" if blocked else "COMPLETE",
        "blocker_codes": ["SOURCE_BLOCKED"] if blocked else [],
        "sources": [source], "monthly_rows": rows, "execution_allowed": False,
    }
    return {**evidence, "cashflow_fingerprint": fingerprint({
        "contract_version": "STAGE6_MONTHLY_RETIREMENT_CASHFLOW_FINGERPRINT_V1",
        "result": evidence,
    })}


def target(*, basis="GROSS", amount="6500", price_basis="NOMINAL_AT_RETIREMENT_TARGET_DATE",
           client_id=7):
    target_value = {
        "client_id": client_id, "planning_calculation_input_fingerprint": "d" * 64,
        "retirement_target_date": "2030-01-01", "monthly_amount": amount,
        "currency": "ILS", "income_basis": basis, "price_basis": price_basis,
        "price_reference_date": None if price_basis == "NOMINAL_AT_RETIREMENT_TARGET_DATE"
        else "2029-01-01",
    }
    result = {
        "schema_version": target_service.SCHEMA_VERSION, "client_id": client_id,
        "planning_calculation_input_fingerprint": "d" * 64,
        "retirement_target_date": "2030-01-01", "target": target_value,
        "authority": {"record_version": 1, "source_kind": "PLANNER_SUPPLIED",
                      "confirmation_state": "CONFIRMED", "confirmation_actor": "planner",
                      "confirmed_at": "2029-01-01T00:00:00.000000Z",
                      "lifecycle_state": "CONFIRMED"},
        "authority_state": "CURRENT", "target_readiness_state": "READY",
        "target_ready": True, "blockers": [],
        "target_semantic_fingerprint": target_service._semantic_fingerprint(target_value),
    }
    return {**result, "target_result_fingerprint": target_service._fingerprint({
        "contract": target_service.RESULT_CONTRACT, **result,
    })}


def reseal_cashflow(value):
    unsigned = {key: item for key, item in value.items() if key != "cashflow_fingerprint"}
    value["cashflow_fingerprint"] = fingerprint({
        "contract_version": "STAGE6_MONTHLY_RETIREMENT_CASHFLOW_FINGERPRINT_V1",
        "result": unsigned,
    })
    return value


def authorized_basis(t, a, *, entries=None):
    """Synthetic, RTICB-signed source evidence; no invented indexation."""
    if entries is None:
        entries = [{
            "schema_version": "CRTISBA_SOURCE_BASIS_ENTRY_V1", "source_id": "income:1",
            "source_kind": "RECURRING_INCOME", "source_category": "RENTAL",
            "admission_state": "INCLUDED", "rtisa_reason_codes": [],
            "source_version": "a" * 64, "source_fingerprint": "a" * 64,
            "amount_authority_fingerprint": "b" * 64, "decision_version": 1,
            "decision_fingerprint": "c" * 64, "decision_state": "CURRENT",
            "income_basis": "GROSS", "income_basis_provenance": "UPSTREAM_RECURRING_AMOUNT_BASIS",
            "price_basis": "NOMINAL_AT_RETIREMENT_TARGET_DATE", "price_reference_date": None,
            "price_basis_provenance": "EXPLICIT_PROFESSIONAL", "blockers": [],
        }]
    collection = {
        "client_id": 7, "planning_calculation_input_fingerprint": "d" * 64,
        "retirement_target_date": t["retirement_target_date"],
        "result_fingerprint": "e" * 64, "source_basis_entries": entries,
    }
    return basis_service._result({
        "client_id": 7,
        "expected_planning_calculation_input_fingerprint": "d" * 64,
        "expected_retirement_target_date": t["retirement_target_date"],
    }, t, collection)


def reader(a, b, t, basis=None):
    return lambda *_args, **_kwargs: (deepcopy(a), deepcopy(b), deepcopy(t),
                                      deepcopy(authorized_basis(t, a) if basis is None else
                                               None if basis == "unavailable" else basis))


def compare(a=None, b=None, t=None, **overrides):
    a = a or cashflow("a", 2)
    b = b or cashflow("b", 3, ("7000.00", "7000.00"))
    t = t or target()
    reader_override = overrides.pop("_snapshot_reader", reader(a, b, t))
    return compare_scenario_monthly_cashflows(
        object(), client_id=7, scenario_a_id="a", scenario_a_version=2,
        scenario_b_id="b", scenario_b_version=3,
        start_month="2030-01", end_month="2030-02",
        _snapshot_reader=reader_override, **overrides,
    )


def test_two_scenarios_compare_and_only_target_month_has_authoritative_gap():
    result = compare()
    assert result["comparison_state"] == "COMPLETE"
    assert result["monthly_rows"][0]["scenario_b_minus_a_gross_ils"] == "2000"
    assert result["monthly_rows"][0]["scenario_a_minus_target_gross_ils"] == "-1500"
    assert result["monthly_rows"][0]["scenario_b_minus_target_gross_ils"] == "500"
    assert result["monthly_rows"][1]["target_gross_income_ils"] is None
    assert "STAGE6_COMPARISON_TARGET_OUTSIDE_COMPARABLE_MONTH" in result["monthly_rows"][1]["blocker_codes"]
    assert result["shared_source_ids"] == ["income:1"]
    assert result["execution_allowed"] is False
    assert len(result["comparison_fingerprint"]) == 64


def test_matching_explicit_authority_is_required_for_positive_target_gap():
    result = compare()
    assert result["target_comparison_state"] == "COMPLETE"
    assert result["monthly_rows"][0]["scenario_a_minus_target_gross_ils"] == "-1500"


@pytest.mark.parametrize("kind", ["missing", "unknown", "different_date", "partial", "target_changed", "pension_od2"])
def test_unverified_price_authority_never_generates_partial_or_certified_gap(kind):
    t = target()
    a, b = cashflow("a", 2), cashflow("b", 3, ("7000.00", "7000.00"))
    basis = authorized_basis(t, a)
    if kind == "missing":
        basis = "unavailable"
    elif kind == "unknown":
        entry = {**basis["source_comparisons"][0], "decision_state": "UNKNOWN",
                 "price_basis": "UNKNOWN", "price_basis_provenance": "MISSING",
                 "decision_version": None, "decision_fingerprint": None,
                 "source_comparison_fingerprint": "f" * 64}
        basis = authorized_basis(t, a, entries=[{
            "schema_version": "CRTISBA_SOURCE_BASIS_ENTRY_V1",
            **{key: value for key, value in entry.items() if key in basis_service.ENTRY_FIELDS - {"schema_version", "blockers"}},
            "blockers": ["CRTISBA_DECISION_UNKNOWN"],
        }])
    elif kind == "different_date":
        entries = [{
            "schema_version": "CRTISBA_SOURCE_BASIS_ENTRY_V1",
            **{key: value for key, value in basis["source_comparisons"][0].items()
               if key in basis_service.ENTRY_FIELDS - {"schema_version", "blockers"}},
            "price_basis": "REAL_AT_REFERENCE_DATE", "price_reference_date": "2029-01-01",
            "blockers": [],
        }]
        basis = authorized_basis(t, a, entries=entries)
    elif kind == "partial":
        b = cashflow("b", 3, ("7000.00", "7000.00"), source_id="income:2")
        b["sources"][0]["recurring_income_id"] = 2
    elif kind == "target_changed":
        t = target()
        t["target"]["retirement_target_date"] = "2030-02-01"
        t["retirement_target_date"] = "2030-02-01"
        t["target_semantic_fingerprint"] = target_service._semantic_fingerprint(t["target"])
        t["target_result_fingerprint"] = target_service._fingerprint({
            "contract": target_service.RESULT_CONTRACT,
            **{key: value for key, value in t.items() if key != "target_result_fingerprint"},
        })
    else:
        pension_entry = {
            "schema_version": "CRTISBA_SOURCE_BASIS_ENTRY_V1", "source_id": "manual:1",
            "source_kind": "PENSION", "source_category": "PENSION",
            "admission_state": "INCLUDED", "rtisa_reason_codes": [],
            "source_version": 1, "source_fingerprint": "a" * 64,
            "amount_authority_fingerprint": "b" * 64, "decision_version": 1,
            "decision_fingerprint": "c" * 64, "decision_state": "CURRENT",
            "income_basis": "GROSS", "income_basis_provenance": "EXPLICIT_PROFESSIONAL",
            "price_basis": "NOMINAL_AT_RETIREMENT_TARGET_DATE", "price_reference_date": None,
            "price_basis_provenance": "OWNER_DECISION_OD2", "blockers": [],
        }
        recurring_entry = {
            "schema_version": "CRTISBA_SOURCE_BASIS_ENTRY_V1",
            **{key: value for key, value in basis["source_comparisons"][0].items()
               if key in basis_service.ENTRY_FIELDS - {"schema_version", "blockers"}},
            "blockers": [],
        }
        basis = authorized_basis(t, a, entries=[recurring_entry, pension_entry])
        a["sources"][0].update(source_kind="CALCULATED_PENSION", source_id="scenario-decision:a:d1", recurring_income_id=None, decision_id="d1", price_basis="NOMINAL_UNINDEXED")
        a["monthly_rows"][0]["contributions"][0].update(source_kind="CALCULATED_PENSION", source_id="scenario-decision:a:d1", contribution_state="CALCULATED")
        a["monthly_rows"][1]["contributions"][0].update(source_kind="CALCULATED_PENSION", source_id="scenario-decision:a:d1", contribution_state="CALCULATED")
        for row in a["monthly_rows"]:
            row["known_income_subtotal_ils"] = "0.00"
            row["calculated_pension_subtotal_ils"] = row["gross_income_total_ils"]
        a = reseal_cashflow(a)
    if kind == "partial":
        b = reseal_cashflow(b)
    result = compare(a=a, b=b, t=t, _snapshot_reader=reader(a, b, t, basis))
    assert result["target_comparison_state"] == "BLOCKED"
    assert all(row["scenario_a_minus_target_gross_ils"] is None for row in result["monthly_rows"])
    assert all(row["scenario_b_minus_target_gross_ils"] is None for row in result["monthly_rows"])
    assert result["monthly_rows"][0]["scenario_a_gross_income_ils"] is not None


@pytest.mark.parametrize("basis,price", [("NET", "NOMINAL_AT_RETIREMENT_TARGET_DATE"), ("GROSS", "REAL_AT_REFERENCE_DATE")])
def test_old_target_basis_barriers_remain_after_price_authority_gate(basis, price):
    assert compare(t=target(basis=basis, price_basis=price))["target_comparison_state"] == "BLOCKED"


def test_one_blocked_scenario_suppresses_all_comparative_amounts_for_that_month():
    result = compare(a=cashflow("a", 2, blocked="2030-02"))
    row = result["monthly_rows"][1]
    assert result["comparison_state"] == "PARTIAL"
    assert row["comparison_state"] == "BLOCKED"
    assert row["scenario_a_gross_income_ils"] is None
    assert row["scenario_b_gross_income_ils"] is None
    assert row["scenario_b_minus_a_gross_ils"] is None


def test_source_start_and_end_events_come_from_authoritative_dates_not_missing_rows():
    a = cashflow("a", 2)
    a["sources"][0]["end_date"] = "2030-01-31"
    a["monthly_rows"][1].update({
        "contributions": [], "known_income_subtotal_ils": "0.00",
        "gross_income_total_ils": "0.00",
    })
    b = cashflow("b", 3, ("7000.00", "7000.00"))
    b["sources"][0]["start_date"] = "2030-02-01"
    b["monthly_rows"][0].update({
        "contributions": [], "known_income_subtotal_ils": "0.00",
        "gross_income_total_ils": "0.00",
    })
    result = compare(a=reseal_cashflow(a), b=reseal_cashflow(b))
    assert result["monthly_rows"][0]["change_events"] == {
        "scenario_a_started_source_ids": ["income:1"],
        "scenario_a_ended_source_ids": [],
        "scenario_b_started_source_ids": [],
        "scenario_b_ended_source_ids": [],
    }
    assert result["monthly_rows"][1]["change_events"] == {
        "scenario_a_started_source_ids": [],
        "scenario_a_ended_source_ids": ["income:1"],
        "scenario_b_started_source_ids": ["income:1"],
        "scenario_b_ended_source_ids": [],
    }


@pytest.mark.parametrize("basis,price,code", [
    ("NET", "NOMINAL_AT_RETIREMENT_TARGET_DATE", "STAGE6_COMPARISON_NET_TARGET_NOT_COMPARABLE"),
    ("GROSS", "REAL_AT_REFERENCE_DATE", "STAGE6_COMPARISON_TARGET_PRICE_BASIS_NOT_COMPARABLE"),
])
def test_non_comparable_target_basis_never_produces_goal_gap(basis, price, code):
    result = compare(t=target(basis=basis, price_basis=price))
    assert result["target_comparison_state"] == "BLOCKED"
    assert all(row["target_gross_income_ils"] is None for row in result["monthly_rows"])
    assert all(code in row["blocker_codes"] for row in result["monthly_rows"])
    assert result["comparison_state"] == "COMPLETE"


def test_coherently_rehashed_but_internally_inconsistent_cashflow_is_rejected():
    forged = cashflow("a", 2)
    forged["monthly_rows"][0]["gross_income_total_ils"] = "9999.00"
    unsigned = {key: value for key, value in forged.items() if key != "cashflow_fingerprint"}
    forged["cashflow_fingerprint"] = fingerprint({
        "contract_version": "STAGE6_MONTHLY_RETIREMENT_CASHFLOW_FINGERPRINT_V1",
        "result": unsigned,
    })
    with pytest.raises(ScenarioSnapshotError, match="STAGE6_COMPARISON_CASHFLOW_INVALID"):
        compare(a=forged)

    identity_swap = cashflow("a", 2)
    identity_swap["sources"][0]["recurring_income_id"] = 99
    identity_unsigned = {
        key: value for key, value in identity_swap.items() if key != "cashflow_fingerprint"
    }
    identity_swap["cashflow_fingerprint"] = fingerprint({
        "contract_version": "STAGE6_MONTHLY_RETIREMENT_CASHFLOW_FINGERPRINT_V1",
        "result": identity_unsigned,
    })
    with pytest.raises(ScenarioSnapshotError, match="STAGE6_COMPARISON_CASHFLOW_INVALID"):
        compare(a=identity_swap)


def test_target_fingerprint_and_client_binding_are_enforced():
    forged = target()
    forged["target_result_fingerprint"] = "0" * 64
    with pytest.raises(ScenarioSnapshotError, match="STAGE6_COMPARISON_TARGET_RESULT_INVALID"):
        compare(t=forged)
    with pytest.raises(ScenarioSnapshotError, match="STAGE6_COMPARISON_CASHFLOW_INVALID"):
        compare(a=cashflow("a", 2, client_id=8))


def test_expected_scenario_versions_prevent_stale_result_reuse():
    stale = cashflow("a", 1)
    with pytest.raises(ScenarioSnapshotError, match="STAGE6_COMPARISON_SCENARIO_VERSION_STALE"):
        compare_scenario_monthly_cashflows(
            object(), client_id=7, scenario_a_id="a", scenario_a_version=2,
            scenario_b_id="b", scenario_b_version=3,
            start_month="2030-01", end_month="2030-02",
            _snapshot_reader=reader(stale, cashflow("b", 3), target()),
        )


def test_request_rejects_same_scenario_or_invalid_range_before_snapshot_access():
    called = False
    def forbidden(*_args, **_kwargs):
        nonlocal called
        called = True
    with pytest.raises(ValueError, match="STAGE6_COMPARISON_REQUEST_INVALID"):
        compare_scenario_monthly_cashflows(
            object(), client_id=7, scenario_a_id="a", scenario_a_version=2,
            scenario_b_id="a", scenario_b_version=2,
            start_month="2030-01", end_month="2030-02", _snapshot_reader=forbidden,
        )
    assert called is False
