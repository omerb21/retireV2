"""Exact display/control totals. Never distribute a discrepancy."""
from decimal import Decimal
from collections.abc import Mapping

from app.models.pension_product import COMPONENT_CODES, REWARDS_CODES, SEVERANCE_CODES


def reconcile(
    balances: Mapping[str, Decimal],
    reported_product_total: Decimal | None,
    reported_rewards_total: Decimal | None,
    reported_severance_total: Decimal | None,
) -> dict[str, Decimal | None]:
    if set(balances) != set(COMPONENT_CODES):
        raise ValueError("Canonical source must contain exactly the eleven components")
    rewards = sum((balances[code] for code in REWARDS_CODES), Decimal("0.00"))
    severance = sum((balances[code] for code in SEVERANCE_CODES), Decimal("0.00"))
    product = rewards + severance
    return {
        "rewards_component_sum": rewards,
        "severance_component_sum": severance,
        "product_component_sum": product,
        "rewards_discrepancy": None if reported_rewards_total is None else reported_rewards_total - rewards,
        "severance_discrepancy": None if reported_severance_total is None else reported_severance_total - severance,
        "product_discrepancy": None if reported_product_total is None else reported_product_total - product,
    }
