"""Read-only gross monthly income gap against an explicitly gross goal.

This helper does not choose/persist a client goal, authorize cashflow, infer
net income, or combine different scenario snapshots. It only annotates a
previously validated canonical Stage 6 cashflow result.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from app.services.planning_input_service import fingerprint

CONTRACT = "STAGE6_GROSS_INCOME_GOAL_GAP_V1"


def _goal(raw: str) -> Decimal:
    if type(raw) is not str or len(raw) > 32:
        raise ValueError("STAGE6_GOAL_GROSS_AMOUNT_INVALID")
    try:
        value = Decimal(raw)
    except (InvalidOperation, ValueError):
        raise ValueError("STAGE6_GOAL_GROSS_AMOUNT_INVALID") from None
    if not value.is_finite() or value < 0 or value.as_tuple().exponent < -2:
        raise ValueError("STAGE6_GOAL_GROSS_AMOUNT_INVALID")
    if format(value, "f") != raw and not (
        raw.isascii() and raw.replace(".", "", 1).isdigit()
    ):
        raise ValueError("STAGE6_GOAL_GROSS_AMOUNT_INVALID")
    return value


def compare_monthly_gross_income_with_goal(cashflow: dict, goal_gross_ils: str) -> dict:
    """Compare like-for-like gross ILS amounts, blocking unverified months.

    The caller must independently validate the Stage 6 snapshot/fingerprint
    before passing it here; this is a read-only comparison, not an authority
    gate. No financial result is emitted from a PARTIAL/BLOCKED month.
    """
    goal = _goal(goal_gross_ils)
    if (
        not isinstance(cashflow, dict)
        or cashflow.get("schema_version") != "STAGE6_MONTHLY_RETIREMENT_CASHFLOW_V1"
        or type(cashflow.get("client_id")) is not int
        or type(cashflow.get("scenario_id")) is not str
        or not cashflow.get("scenario_id")
        or type(cashflow.get("scenario_version")) is not int
        or type(cashflow.get("cashflow_fingerprint")) is not str
        or len(cashflow["cashflow_fingerprint"]) != 64
        or cashflow.get("execution_allowed") is not False
        or not isinstance(cashflow.get("monthly_rows"), list)
        or not 1 <= len(cashflow["monthly_rows"]) <= 600
    ):
        raise ValueError("STAGE6_GOAL_CASHFLOW_CONTRACT_INVALID")
    rows = []
    seen = set()
    for row in cashflow["monthly_rows"]:
        if not isinstance(row, dict) or type(row.get("month")) is not str or row["month"] in seen:
            raise ValueError("STAGE6_GOAL_CASHFLOW_CONTRACT_INVALID")
        seen.add(row["month"])
        complete = row.get("cashflow_state") == "COMPLETE"
        raw = row.get("gross_income_total_ils")
        if complete:
            if type(raw) is not str:
                raise ValueError("STAGE6_GOAL_CASHFLOW_CONTRACT_INVALID")
            try:
                total = Decimal(raw)
            except InvalidOperation:
                raise ValueError("STAGE6_GOAL_CASHFLOW_CONTRACT_INVALID") from None
            if not total.is_finite() or total < 0 or total.as_tuple().exponent < -2 or row.get("blocker_codes"):
                raise ValueError("STAGE6_GOAL_CASHFLOW_CONTRACT_INVALID")
            difference = total - goal
            rows.append({
                "month": row["month"],
                "comparison_state": "COMPLETE",
                "gross_income_ils": f"{total:.2f}",
                "gross_goal_ils": f"{goal:.2f}",
                "gross_surplus_ils": f"{difference:.2f}" if difference >= 0 else None,
                "gross_shortfall_ils": f"{-difference:.2f}" if difference < 0 else None,
                "blocker_codes": [],
            })
        elif row.get("cashflow_state") in {"PARTIAL", "BLOCKED"} and raw is None:
            rows.append({
                "month": row["month"], "comparison_state": "BLOCKED",
                "gross_income_ils": None, "gross_goal_ils": f"{goal:.2f}",
                "gross_surplus_ils": None, "gross_shortfall_ils": None,
                "blocker_codes": ["STAGE6_GOAL_SOURCE_CASHFLOW_INCOMPLETE"],
            })
        else:
            raise ValueError("STAGE6_GOAL_CASHFLOW_CONTRACT_INVALID")
    result = {
        "schema_version": CONTRACT,
        "client_id": cashflow["client_id"],
        "scenario_id": cashflow["scenario_id"],
        "scenario_version": cashflow["scenario_version"],
        "cashflow_fingerprint": cashflow["cashflow_fingerprint"],
        "goal_basis": "MONTHLY_GROSS_ILS_NOMINAL_UNINDEXED",
        "gross_goal_ils": f"{goal:.2f}",
        "comparison_state": "COMPLETE" if all(row["comparison_state"] == "COMPLETE" for row in rows) else "PARTIAL",
        "monthly_rows": rows,
        "execution_allowed": False,
    }
    return {**result, "comparison_fingerprint": fingerprint({
        "contract_version": CONTRACT, "result": result,
    })}
