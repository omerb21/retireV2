"""Stage 6 signed pension price authority must be explicit and source-specific."""
from copy import deepcopy

from app.services.planning_input_service import fingerprint
from app.services.scenario_pension_price_basis_service import evaluate_decision
from app.services.scenario_stage6_monthly_comparison_service import compare_scenario_monthly_cashflows
from test_stage6_monthly_comparison import cashflow, target, authorized_basis, reseal_cashflow


def pension_cashflow(scenario_id, version, pension_amount):
    value = cashflow(scenario_id, version, ("2000.00", "2000.00"))
    identity = f"scenario-decision:{scenario_id}:pension1"
    pension = {
        "source_id": identity, "source_kind": "CALCULATED_PENSION",
        "decision_id": "pension1", "recurring_income_id": None,
        "label": "סינתטי", "monthly_amount_gross_ils": pension_amount,
        "income_basis": "GROSS", "price_basis": "NOMINAL_UNINDEXED",
        "start_date": "2030-01-01", "end_date": None,
        "source_reference_date": "2029-12-01",
        "authority_fingerprint": ("f" if scenario_id == "a" else "e") * 64,
        "source_state": "READY", "blocker_codes": [],
    }
    value["sources"].append(pension)
    value["sources"].sort(key=lambda item: item["source_id"])
    for row in value["monthly_rows"]:
        row["contributions"].append({
            "source_id": identity, "source_kind": "CALCULATED_PENSION",
            "amount_monthly_gross_ils": pension_amount, "contribution_state": "CALCULATED",
        })
        row["calculated_pension_subtotal_ils"] = pension_amount
        row["gross_income_total_ils"] = format(
            int(pension_amount.split(".")[0]) + 2000, ".2f"
        )
    return reseal_cashflow(value)


def decision(value, t):
    source = next(s for s in value["sources"] if s["source_kind"] == "CALCULATED_PENSION")
    row = {
        "source_id": source["source_id"], "scenario_id": value["scenario_id"],
        "decision_id": source["decision_id"], "scenario_version": value["scenario_version"],
        "source_fingerprint": source["authority_fingerprint"],
        "target_fingerprint": t["target_result_fingerprint"],
        "target_date": t["retirement_target_date"],
        "price_basis": "NOMINAL_AT_RETIREMENT_TARGET_DATE", "revision": 1,
    }
    return {**row, "record_fingerprint": fingerprint({"contract": "S6_PRICE_BASIS_V1", **row}),
            "provenance": "EXPLICIT_PROFESSIONAL"}


def compare_with_prices(a, b, t, decisions):
    basis = authorized_basis(t, a)
    result = compare_scenario_monthly_cashflows(
        object(), client_id=7, scenario_a_id="a", scenario_a_version=2,
        scenario_b_id="b", scenario_b_version=3,
        start_month="2030-01", end_month="2030-02",
        _snapshot_reader=lambda *_args, **_kwargs: (
            deepcopy(a), deepcopy(b), deepcopy(t), (deepcopy(basis), deepcopy(decisions)),
        ),
    )
    return result


def test_explicit_price_basis_completes_target_gap_but_only_in_target_month():
    a, b, t = pension_cashflow("a", 2, "6000.00"), pension_cashflow("b", 3, "3000.00"), target(amount="7000")
    da, db = decision(a, t), decision(b, t)
    result = compare_with_prices(a, b, t, {da["source_id"]: da, db["source_id"]: db})
    first, second = result["monthly_rows"]
    assert result["target_comparison_state"] == "COMPLETE"
    assert first["scenario_a_minus_target_gross_ils"] == "1000"
    assert first["scenario_b_minus_target_gross_ils"] == "-2000"
    assert second["target_comparison_state"] == "BLOCKED"


def test_price_basis_missing_stale_or_other_scenario_never_authorizes_gap():
    a, b, t = pension_cashflow("a", 2, "6000.00"), pension_cashflow("b", 3, "3000.00"), target(amount="7000")
    da, db = decision(a, t), decision(b, t)
    valid = {da["source_id"]: da, db["source_id"]: db}
    for invalid in (
        {da["source_id"]: da},
        {da["source_id"]: {**da, "source_fingerprint": "d" * 64}, db["source_id"]: db},
        {da["source_id"]: {**db, "source_id": da["source_id"]}, db["source_id"]: db},
        {da["source_id"]: {**da, "price_basis": "UNKNOWN"}, db["source_id"]: db},
    ):
        result = compare_with_prices(a, b, t, invalid)
        assert result["target_comparison_state"] == "BLOCKED"
        assert result["monthly_rows"][0]["scenario_a_minus_target_gross_ils"] is None
    changed = pension_cashflow("a", 2, "6100.00")
    changed["sources"][0 if changed["sources"][0]["source_kind"] == "CALCULATED_PENSION" else 1]["authority_fingerprint"] = "9" * 64
    changed = reseal_cashflow(changed)
    result = compare_with_prices(changed, b, t, valid)
    assert result["target_comparison_state"] == "BLOCKED"


def test_price_authority_validates_source_identity_and_fingerprint():
    a, t = pension_cashflow("a", 2, "6000.00"), target()
    source = next(s for s in a["sources"] if s["source_kind"] == "CALCULATED_PENSION")
    row = decision(a, t)
    arguments = dict(client_id=7, scenario_id="a", scenario_version=2,
                     target_fingerprint=t["target_result_fingerprint"], target_date="2030-01-01")
    assert evaluate_decision(row, source, **arguments) == "CURRENT"
    assert evaluate_decision({**row, "scenario_version": 3}, source, **arguments) == "STALE"
    assert evaluate_decision({**row, "record_fingerprint": "0" * 64}, source, **arguments) == "INVALID"
