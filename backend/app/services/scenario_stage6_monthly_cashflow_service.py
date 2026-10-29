"""Stage 6 monthly gross-income timeline for one saved scenario.

This is a bounded, read-only projection.  It reuses the canonical scenario
snapshot and PTE gates; it does not invoke the historical M09 executor and does
not calculate tax, net income, returns, discounting, or capital withdrawals.
"""
from __future__ import annotations

from calendar import monthrange
from datetime import date
from decimal import Decimal, localcontext
import re

from sqlalchemy import select

from app.models.planning_input_decision import PensionIncomeResolution
from app.models.retirement_facts import RecurringIncome
from app.models.scenario_draft_pension_election import ScenarioDraftPensionElection
from app.services.planning_input_service import fingerprint
from app.services.professional_source_snapshot_service import record
from app.services.scenario_snapshot_candidate_service import (
    ScenarioSnapshotError, _stage6_identity_extension,
    build_manifest_candidate_snapshot,
)
from app.services.scenario_stage6_single_pension_estimate_service import (
    _blocked_from_exception, _execute_verified, _valid_sealed_result,
)


CONTRACT = "STAGE6_MONTHLY_RETIREMENT_CASHFLOW_V1"
MONTH = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")
MAX_MONTHS = 600
VALID_SOURCE_STATUSES = {
    "client stated", "planner entered", "external statement",
    "employer information", "institution information",
    "government or tax source", "other",
}
VALID_VERIFICATION_STATES = {
    "reviewed", "verified", "partially verified",
    "verification not applicable",
}


def _parse_month(value: str) -> date:
    if type(value) is not str or not MONTH.fullmatch(value):
        raise ValueError("STAGE6_CASHFLOW_MONTH_INVALID")
    return date(int(value[:4]), int(value[5:]), 1)


def _next_month(value: date) -> date:
    return date(value.year + (value.month == 12), 1 if value.month == 12 else value.month + 1, 1)


def _months(start_month: str, end_month: str) -> list[date]:
    start, end = _parse_month(start_month), _parse_month(end_month)
    if end < start:
        raise ValueError("STAGE6_CASHFLOW_RANGE_INVALID")
    values = []
    current = start
    while current <= end and len(values) <= MAX_MONTHS:
        values.append(current)
        # Do not advance beyond the final requested month: 9999-12 is a
        # valid calendar month but Python's date cannot represent year 10000.
        if current == end:
            break
        current = _next_month(current)
    if len(values) > MAX_MONTHS:
        raise ValueError("STAGE6_CASHFLOW_RANGE_TOO_LARGE")
    return values


def _money_sum(values: list[str]) -> str:
    if not values:
        return "0.00"
    precision = max(len(value.replace(".", "")) for value in values)
    precision += len(str(len(values))) + 2
    with localcontext() as context:
        context.prec = precision
        total = sum((Decimal(value) for value in values), Decimal("0.00"))
    return format(total, ".2f")


def _month_contains(value: date, start: date | None, end: date | None) -> bool:
    month_end = date(value.year, value.month, monthrange(value.year, value.month)[1])
    return (start is None or start <= month_end) and (end is None or end >= value)


def _partial_month(value: date, start: date | None, end: date | None) -> bool:
    return bool(
        start is not None and start.year == value.year and start.month == value.month
        and start.day != 1
    ) or bool(
        end is not None and end.year == value.year and end.month == value.month
        and end.day != monthrange(end.year, end.month)[1]
    )


def _recurring_source(row: RecurringIncome,
                      resolution: PensionIncomeResolution | None) -> dict:
    source_id = f"income:{row.id}"
    source_fingerprint = fingerprint(record(row))
    blockers: set[str] = set()
    if row.income_category == "pension":
        blockers.add("STAGE6_CASHFLOW_RECURRING_PENSION_NOT_CANONICAL")
    if resolution is not None and not (
        resolution.client_id == row.client_id
        and resolution.decision_kind == "MISCLASSIFIED_GENERAL_INCOME"
        and resolution.income_fingerprint == source_fingerprint
        and resolution.canonical_source_id is None
        and resolution.canonical_fingerprint is None
        and row.income_category != "pension"
    ):
        blockers.add("STAGE6_CASHFLOW_RECURRING_IDENTITY_UNRESOLVED")
    if not isinstance(row.description, str) or not row.description.strip():
        blockers.add("STAGE6_CASHFLOW_RECURRING_RECORD_INVALID")
    if row.source_status not in VALID_SOURCE_STATUSES:
        blockers.add("STAGE6_CASHFLOW_RECURRING_AUTHORITY_INCOMPLETE")
    if row.verification_state not in VALID_VERIFICATION_STATES:
        blockers.add("STAGE6_CASHFLOW_RECURRING_AUTHORITY_INCOMPLETE")
    amount = row.amount
    if not isinstance(amount, Decimal) or not amount.is_finite() or amount < 0:
        blockers.add("STAGE6_CASHFLOW_RECURRING_AMOUNT_INVALID")
    if row.amount_basis != "gross":
        blockers.add("STAGE6_CASHFLOW_RECURRING_GROSS_BASIS_REQUIRED")
    if row.frequency != "monthly":
        # Quarterly/annual records do not contain payment-month facts.  An
        # arithmetic average would invent a cash-receipt schedule.
        blockers.add("STAGE6_CASHFLOW_RECURRING_PAYMENT_SCHEDULE_UNRESOLVED")
    start = row.start_date
    end = row.end_date
    if not isinstance(start, date):
        blockers.add("STAGE6_CASHFLOW_RECURRING_START_DATE_MISSING")
    if row.continuation_status not in {"ongoing", "known end date"}:
        blockers.add("STAGE6_CASHFLOW_RECURRING_CONTINUATION_UNRESOLVED")
    if row.continuation_status == "known end date" and not isinstance(end, date):
        blockers.add("STAGE6_CASHFLOW_RECURRING_END_DATE_MISSING")
    if isinstance(start, date) and isinstance(end, date) and end < start:
        blockers.add("STAGE6_CASHFLOW_RECURRING_DATE_RANGE_INVALID")
    return {
        "source_id": source_id,
        "source_kind": "KNOWN_RECURRING_INCOME",
        "decision_id": None,
        "recurring_income_id": row.id,
        "label": row.description,
        "monthly_amount_gross_ils": format(amount, ".2f") if not blockers else None,
        "income_basis": "GROSS" if row.amount_basis == "gross" else None,
        "price_basis": "STATED_NOMINAL_NO_INDEXATION",
        "start_date": start.isoformat() if isinstance(start, date) else None,
        "end_date": end.isoformat() if isinstance(end, date) else None,
        "source_reference_date": (
            row.source_date.isoformat() if isinstance(row.source_date, date) else None
        ),
        "authority_fingerprint": source_fingerprint,
        "source_state": "READY" if not blockers else "BLOCKED",
        "blocker_codes": sorted(blockers),
    }


def _source_dates(source: dict) -> tuple[date | None, date | None]:
    start = date.fromisoformat(source["start_date"]) if source["start_date"] else None
    end = date.fromisoformat(source["end_date"]) if source["end_date"] else None
    return start, end


def _cashflow_extension(*, client_id: int, scenario_id: str,
                        start_month: str, end_month: str):
    months = _months(start_month, end_month)

    def build(db, pair: dict) -> dict:
        manifest = pair["manifest"]
        pension_rows = sorted(
            (row for row in manifest["decisions"] if row["action"] == "pension"),
            key=lambda row: row["decision_id"],
        )
        elections = list(db.scalars(select(ScenarioDraftPensionElection).where(
            ScenarioDraftPensionElection.scenario_id == scenario_id,
            ScenarioDraftPensionElection.scenario_version == manifest["scenario_version"],
        )))
        election_by_decision = {row.decision_id: row for row in elections}
        sources = []
        source_key_counts: dict[tuple[str, str], int] = {}
        for row in pension_rows:
            decision_id = row["decision_id"]
            key = (row["product_id"], row["component_id"])
            source_key_counts[key] = source_key_counts.get(key, 0) + 1
            extension = _stage6_identity_extension(
                client_id=client_id, scenario_id=scenario_id,
                decision_id=decision_id, _stage6_executor=_execute_verified,
            )
            try:
                result = extension(db, pair)
            except ScenarioSnapshotError as exc:
                result = _blocked_from_exception(client_id, scenario_id, decision_id, exc)
            if not _valid_sealed_result(
                result, client_id=client_id, scenario_id=scenario_id,
                decision_id=decision_id,
            ):
                result = _blocked_from_exception(
                    client_id, scenario_id, decision_id,
                    ScenarioSnapshotError("STAGE6_CASHFLOW_PENSION_RESULT_INVALID"),
                )
            election = election_by_decision.get(decision_id)
            ready = result["result_state"] == "RESULT_READY"
            sources.append({
                "source_id": result["source_id"],
                "source_kind": "CALCULATED_PENSION",
                "decision_id": decision_id,
                "recurring_income_id": None,
                "label": row["component_code"],
                "monthly_amount_gross_ils": (
                    result["monthly_estimate_gross_ils"] if ready else None
                ),
                "income_basis": "GROSS" if ready else None,
                "price_basis": "NOMINAL_UNINDEXED" if ready else None,
                "start_date": (
                    result["retirement_target_date"] if ready else
                    election.pension_start_date.isoformat() if election is not None else None
                ),
                "end_date": None,
                "source_reference_date": result["statement_date"] if ready else None,
                "authority_fingerprint": result["result_fingerprint"],
                "source_state": "READY" if ready else "BLOCKED",
                "blocker_codes": [] if ready else list(result["blockers"]),
            })

        duplicate_keys = {key for key, count in source_key_counts.items() if count > 1}
        for source, row in zip(sources, pension_rows):
            if (row["product_id"], row["component_id"]) in duplicate_keys:
                source["source_state"] = "BLOCKED"
                source["monthly_amount_gross_ils"] = None
                source["blocker_codes"] = sorted(set(source["blocker_codes"]) | {
                    "STAGE6_CASHFLOW_DUPLICATE_PENSION_SOURCE",
                })

        recurring_rows = list(db.scalars(select(RecurringIncome).where(
            RecurringIncome.client_id == client_id,
            RecurringIncome.lifecycle_status == "current",
        ).order_by(RecurringIncome.id)))
        resolutions = list(db.scalars(select(PensionIncomeResolution).where(
            PensionIncomeResolution.client_id == client_id,
        ).order_by(PensionIncomeResolution.income_id)))
        resolution_by_income = {row.income_id: row for row in resolutions}
        sources.extend(
            _recurring_source(row, resolution_by_income.get(row.id))
            for row in recurring_rows
        )
        sources.sort(key=lambda source: source["source_id"])
        if len({source["source_id"] for source in sources}) != len(sources):
            raise ScenarioSnapshotError("STAGE6_CASHFLOW_SOURCE_IDENTITY_DUPLICATE")

        monthly_rows = []
        no_sources = not sources
        for month in months:
            contributions = []
            blockers: set[str] = set()
            if no_sources:
                blockers.add("STAGE6_CASHFLOW_NO_INCOME_SOURCES")
            for source in sources:
                start, end = _source_dates(source)
                if start is None:
                    blockers.update(
                        f'{source["source_id"]}:{code}' for code in source["blocker_codes"]
                    )
                    if not source["blocker_codes"]:
                        blockers.add(f'{source["source_id"]}:STAGE6_CASHFLOW_START_DATE_MISSING')
                    continue
                if not _month_contains(month, start, end):
                    continue
                if source["source_state"] != "READY":
                    blockers.update(
                        f'{source["source_id"]}:{code}' for code in source["blocker_codes"]
                    )
                    continue
                if _partial_month(month, start, end):
                    blockers.add(
                        f'{source["source_id"]}:STAGE6_CASHFLOW_PARTIAL_MONTH_PRORATION_UNDEFINED'
                    )
                    continue
                contributions.append({
                    "source_id": source["source_id"],
                    "source_kind": source["source_kind"],
                    "amount_monthly_gross_ils": source["monthly_amount_gross_ils"],
                    "contribution_state": (
                        "CALCULATED" if source["source_kind"] == "CALCULATED_PENSION"
                        else "KNOWN"
                    ),
                })
            known = [row["amount_monthly_gross_ils"] for row in contributions
                     if row["contribution_state"] == "KNOWN"]
            calculated = [row["amount_monthly_gross_ils"] for row in contributions
                          if row["contribution_state"] == "CALCULATED"]
            if blockers:
                state = "PARTIAL" if contributions else "BLOCKED"
                total = None
            else:
                state = "COMPLETE"
                total = _money_sum(known + calculated)
            monthly_rows.append({
                "month": month.strftime("%Y-%m"),
                "cashflow_state": state,
                "contributions": contributions,
                "known_income_subtotal_ils": _money_sum(known),
                "calculated_pension_subtotal_ils": _money_sum(calculated),
                "gross_income_total_ils": total,
                "blocker_codes": sorted(blockers),
            })

        states = {row["cashflow_state"] for row in monthly_rows}
        overall = (
            "COMPLETE" if states == {"COMPLETE"}
            else "PARTIAL" if "COMPLETE" in states or "PARTIAL" in states
            else "BLOCKED"
        )
        blockers = sorted({
            code for row in monthly_rows for code in row["blocker_codes"]
        })
        evidence = {
            "schema_version": CONTRACT,
            "client_id": client_id,
            "scenario_id": scenario_id,
            "scenario_version": manifest["scenario_version"],
            "manifest_fingerprint": manifest["manifest_fingerprint"],
            "start_month": start_month,
            "end_month": end_month,
            "cashflow_state": overall,
            "blocker_codes": blockers,
            "sources": sources,
            "monthly_rows": monthly_rows,
            "execution_allowed": False,
        }
        return {**evidence, "cashflow_fingerprint": fingerprint({
            "contract_version": "STAGE6_MONTHLY_RETIREMENT_CASHFLOW_FINGERPRINT_V1",
            "result": evidence,
        })}
    return build


def _blocked_result(client_id: int, scenario_id: str, start_month: str,
                    end_month: str, code: str) -> dict:
    monthly_rows = [{
        "month": month.strftime("%Y-%m"), "cashflow_state": "BLOCKED",
        "contributions": [], "known_income_subtotal_ils": "0.00",
        "calculated_pension_subtotal_ils": "0.00",
        "gross_income_total_ils": None, "blocker_codes": [code],
    } for month in _months(start_month, end_month)]
    evidence = {
        "schema_version": CONTRACT, "client_id": client_id,
        "scenario_id": scenario_id, "scenario_version": None,
        "manifest_fingerprint": None, "start_month": start_month,
        "end_month": end_month, "cashflow_state": "BLOCKED",
        "blocker_codes": [code], "sources": [],
        "monthly_rows": monthly_rows, "execution_allowed": False,
    }
    return {**evidence, "cashflow_fingerprint": fingerprint({
        "contract_version": "STAGE6_MONTHLY_RETIREMENT_CASHFLOW_FINGERPRINT_V1",
        "result": evidence,
    })}


def build_scenario_monthly_cashflow(factory, *, client_id: int,
                                    scenario_id: str, start_month: str,
                                    end_month: str) -> dict:
    if (type(client_id) is not int or client_id <= 0
            or type(scenario_id) is not str or not scenario_id
            or len(scenario_id) > 64):
        raise ValueError("STAGE6_CASHFLOW_ROUTE_INVALID")
    _months(start_month, end_month)
    try:
        return build_manifest_candidate_snapshot(
            factory, client_id=client_id, scenario_id=scenario_id,
            _snapshot_extension=_cashflow_extension(
                client_id=client_id, scenario_id=scenario_id,
                start_month=start_month, end_month=end_month,
            ),
        )
    except ScenarioSnapshotError as exc:
        code = str(exc)
        if not code.startswith(("STAGE6_", "SCENARIO_")):
            code = "STAGE6_CASHFLOW_SNAPSHOT_UNAVAILABLE"
        return _blocked_result(client_id, scenario_id, start_month, end_month, code)
