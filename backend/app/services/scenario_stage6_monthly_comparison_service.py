"""Canonical two-scenario monthly gross-income comparison.

Both Stage 6 cashflows and the canonical RIT assessment are derived inside one
dedicated PostgreSQL REPEATABLE READ, READ ONLY snapshot.  This service never
executes historical M09, persists results, infers tax/net income, or normalizes
price bases.
"""
from __future__ import annotations

from copy import deepcopy
from calendar import monthrange
from datetime import date
from decimal import Decimal, InvalidOperation, localcontext
import hmac
import re

from sqlalchemy.orm import Session

from app.services import retirement_monthly_income_target_service as target_service
from app.services.planning_input_service import fingerprint
from app.services.scenario_draft_service import DraftError
from app.services.scenario_snapshot_candidate_service import (
    ScenarioSnapshotError, _build_pair_in_snapshot, _engine,
)
from app.services.scenario_stage6_monthly_cashflow_service import (
    _cashflow_extension, _months, validate_monthly_cashflow_result,
)


CONTRACT = "STAGE6_SCENARIO_MONTHLY_COMPARISON_V1"
FINGERPRINT_CONTRACT = "STAGE6_SCENARIO_MONTHLY_COMPARISON_FINGERPRINT_V1"
HASH = re.compile(r"^[0-9a-f]{64}$", re.ASCII)


def _decimal_text(value: Decimal) -> str:
    if value == 0:
        return "0"
    rendered = format(value, "f")
    return rendered.rstrip("0").rstrip(".") if "." in rendered else rendered


def _subtract(left: str, right: str) -> str:
    try:
        with localcontext() as context:
            context.prec = max(len(left), len(right)) + 4
            value = Decimal(left) - Decimal(right)
    except (InvalidOperation, ValueError) as exc:
        raise ScenarioSnapshotError("STAGE6_COMPARISON_AMOUNT_INVALID") from exc
    if not value.is_finite():
        raise ScenarioSnapshotError("STAGE6_COMPARISON_AMOUNT_INVALID")
    return _decimal_text(value)


def _valid_target_result(value, client_id: int) -> bool:
    keys = {
        "schema_version", "client_id", "planning_calculation_input_fingerprint",
        "retirement_target_date", "target", "authority", "authority_state",
        "target_readiness_state", "target_ready", "blockers",
        "target_semantic_fingerprint", "target_result_fingerprint",
    }
    if not isinstance(value, dict) or set(value) != keys:
        return False
    if (
        value["schema_version"] != target_service.SCHEMA_VERSION
        or value["client_id"] != client_id
        or not isinstance(value["target_ready"], bool)
        or not isinstance(value["blockers"], list)
        or value["blockers"] != sorted(set(value["blockers"]))
        or not isinstance(value["target_result_fingerprint"], str)
        or not HASH.fullmatch(value["target_result_fingerprint"])
    ):
        return False
    unsigned = {key: value[key] for key in keys - {"target_result_fingerprint"}}
    try:
        expected = target_service._fingerprint({
            "contract": target_service.RESULT_CONTRACT, **unsigned,
        })
    except Exception:
        return False
    if not hmac.compare_digest(value["target_result_fingerprint"], expected):
        return False
    if not value["target_ready"]:
        return value["target_readiness_state"] == "NOT_READY"
    target = value["target"]
    authority = value["authority"]
    if (
        value["authority_state"] != "CURRENT"
        or value["target_readiness_state"] != "READY"
        or value["blockers"]
        or not isinstance(target, dict)
        or set(target) != {
            "client_id", "planning_calculation_input_fingerprint", "retirement_target_date",
            "monthly_amount", "currency", "income_basis", "price_basis",
            "price_reference_date",
        }
        or target["client_id"] != client_id
        or target["currency"] != "ILS"
        or not isinstance(value["planning_calculation_input_fingerprint"], str)
        or not HASH.fullmatch(value["planning_calculation_input_fingerprint"])
        or target["income_basis"] not in {"GROSS", "NET"}
        or target["price_basis"] not in {
            "NOMINAL_AT_RETIREMENT_TARGET_DATE", "REAL_AT_REFERENCE_DATE",
        }
        or target["planning_calculation_input_fingerprint"]
           != value["planning_calculation_input_fingerprint"]
        or target["retirement_target_date"] != value["retirement_target_date"]
        or not isinstance(authority, dict)
        or set(authority) != {
            "record_version", "source_kind", "confirmation_state",
            "confirmation_actor", "confirmed_at", "lifecycle_state",
        }
        or isinstance(authority["record_version"], bool)
        or not isinstance(authority["record_version"], int)
        or not 1 <= authority["record_version"] <= target_service.MAX_VERSION
        or authority["source_kind"] not in target_service.SOURCE_KINDS
        or authority["confirmation_state"] != "CONFIRMED"
        or not isinstance(authority["confirmation_actor"], str)
        or not authority["confirmation_actor"].strip()
        or not isinstance(authority["confirmed_at"], str)
        or not target_service.TIMESTAMP_RE.fullmatch(authority["confirmed_at"])
        or authority["lifecycle_state"] != "CONFIRMED"
    ):
        return False
    try:
        amount, amount_error = target_service._canonical_amount(target["monthly_amount"])
        if date.fromisoformat(target["retirement_target_date"]).isoformat() != target["retirement_target_date"]:
            return False
        if (target["price_reference_date"] is not None
                and date.fromisoformat(target["price_reference_date"]).isoformat()
                != target["price_reference_date"]):
            return False
    except (TypeError, ValueError):
        return False
    if amount_error or amount != target["monthly_amount"]:
        return False
    if (
        (target["price_basis"] == "NOMINAL_AT_RETIREMENT_TARGET_DATE"
         and target["price_reference_date"] is not None)
        or (target["price_basis"] == "REAL_AT_REFERENCE_DATE"
            and not isinstance(target["price_reference_date"], str))
    ):
        return False
    try:
        semantic = target_service._semantic_fingerprint(target)
    except Exception:
        return False
    return (
        isinstance(value["target_semantic_fingerprint"], str)
        and hmac.compare_digest(value["target_semantic_fingerprint"], semantic)
    )


def _source_projection(cashflow: dict) -> list[dict]:
    return [{
        "source_id": source["source_id"],
        "source_kind": source["source_kind"],
        "authority_fingerprint": source["authority_fingerprint"],
        "source_state": source["source_state"],
    } for source in cashflow["sources"]]


def _source_events(cashflow: dict, month_text: str) -> tuple[list[str], list[str]]:
    month = date.fromisoformat(month_text + "-01")
    previous = (
        None if month.year == 1 and month.month == 1
        else date(month.year - 1, 12, 1) if month.month == 1
        else date(month.year, month.month - 1, 1)
    )

    def active(source: dict, current: date) -> bool:
        start = date.fromisoformat(source["start_date"]) if source["start_date"] else None
        end = date.fromisoformat(source["end_date"]) if source["end_date"] else None
        current_end = date(current.year, current.month, monthrange(current.year, current.month)[1])
        return start is not None and start <= current_end and (end is None or end >= current)

    started = []
    ended = []
    for source in cashflow["sources"]:
        now = active(source, month)
        before = previous is not None and active(source, previous)
        if now and not before:
            started.append(source["source_id"])
        elif before and not now:
            ended.append(source["source_id"])
    return sorted(started), sorted(ended)


def _target_projection(target_result: dict) -> dict:
    target = target_result["target"] if target_result["target_ready"] else None
    if target is None:
        state = "NOT_READY"
        amount = basis = price_basis = target_date = None
        blockers = list(target_result["blockers"] or ["STAGE6_COMPARISON_TARGET_NOT_READY"])
    elif target["income_basis"] != "GROSS":
        state = "NET_NOT_COMPARABLE"
        amount, basis, price_basis, target_date = (
            target["monthly_amount"], target["income_basis"], target["price_basis"],
            target["retirement_target_date"],
        )
        blockers = ["STAGE6_COMPARISON_NET_TARGET_NOT_COMPARABLE"]
    elif target["price_basis"] != "NOMINAL_AT_RETIREMENT_TARGET_DATE":
        state = "PRICE_BASIS_NOT_COMPARABLE"
        amount, basis, price_basis, target_date = (
            target["monthly_amount"], target["income_basis"], target["price_basis"],
            target["retirement_target_date"],
        )
        blockers = ["STAGE6_COMPARISON_TARGET_PRICE_BASIS_NOT_COMPARABLE"]
    else:
        state = "GROSS_NOMINAL_TARGET_MONTH_ONLY"
        amount, basis, price_basis, target_date = (
            target["monthly_amount"], target["income_basis"], target["price_basis"],
            target["retirement_target_date"],
        )
        blockers = []
    return {
        "target_state": state,
        "monthly_amount_ils": amount,
        "income_basis": basis,
        "price_basis": price_basis,
        "retirement_target_date": target_date,
        "target_semantic_fingerprint": target_result["target_semantic_fingerprint"],
        "target_result_fingerprint": target_result["target_result_fingerprint"],
        "blocker_codes": sorted(set(blockers)),
    }


def _compose(*, client_id: int, scenario_a_id: str, scenario_a_version: int,
             scenario_b_id: str, scenario_b_version: int, start_month: str,
             end_month: str, cashflow_a: dict, cashflow_b: dict,
             target_result: dict) -> dict:
    if not validate_monthly_cashflow_result(
        cashflow_a, client_id=client_id, scenario_id=scenario_a_id,
        scenario_version=scenario_a_version, start_month=start_month, end_month=end_month,
    ) or not validate_monthly_cashflow_result(
        cashflow_b, client_id=client_id, scenario_id=scenario_b_id,
        scenario_version=scenario_b_version, start_month=start_month, end_month=end_month,
    ):
        raise ScenarioSnapshotError("STAGE6_COMPARISON_CASHFLOW_INVALID")
    if not _valid_target_result(target_result, client_id):
        raise ScenarioSnapshotError("STAGE6_COMPARISON_TARGET_RESULT_INVALID")
    target = _target_projection(target_result)
    rows = []
    target_complete = False
    for row_a, row_b in zip(cashflow_a["monthly_rows"], cashflow_b["monthly_rows"]):
        started_a, ended_a = _source_events(cashflow_a, row_a["month"])
        started_b, ended_b = _source_events(cashflow_b, row_b["month"])
        changes = {
            "scenario_a_started_source_ids": started_a,
            "scenario_a_ended_source_ids": ended_a,
            "scenario_b_started_source_ids": started_b,
            "scenario_b_ended_source_ids": ended_b,
        }
        blockers = []
        complete = (
            row_a["cashflow_state"] == "COMPLETE"
            and row_b["cashflow_state"] == "COMPLETE"
        )
        if not complete:
            if row_a["cashflow_state"] != "COMPLETE":
                blockers.append("STAGE6_COMPARISON_SCENARIO_A_INCOMPLETE")
            if row_b["cashflow_state"] != "COMPLETE":
                blockers.append("STAGE6_COMPARISON_SCENARIO_B_INCOMPLETE")
            amount_a = amount_b = difference = None
        else:
            amount_a = row_a["gross_income_total_ils"]
            amount_b = row_b["gross_income_total_ils"]
            difference = _subtract(amount_b, amount_a)
        target_amount = gap_a = gap_b = None
        goal_state = "BLOCKED"
        if target["target_state"] == "GROSS_NOMINAL_TARGET_MONTH_ONLY":
            target_month = target["retirement_target_date"][:7]
            if row_a["month"] == target_month and complete:
                target_amount = target["monthly_amount_ils"]
                gap_a = _subtract(amount_a, target_amount)
                gap_b = _subtract(amount_b, target_amount)
                goal_state = "COMPLETE"
                target_complete = True
            elif row_a["month"] != target_month:
                blockers.append("STAGE6_COMPARISON_TARGET_OUTSIDE_COMPARABLE_MONTH")
            else:
                blockers.append("STAGE6_COMPARISON_TARGET_MONTH_INCOMPLETE")
        else:
            blockers.extend(target["blocker_codes"])
        rows.append({
            "month": row_a["month"],
            "comparison_state": "COMPLETE" if complete else "BLOCKED",
            "scenario_a_gross_income_ils": amount_a,
            "scenario_b_gross_income_ils": amount_b,
            "scenario_b_minus_a_gross_ils": difference,
            "target_comparison_state": goal_state,
            "target_gross_income_ils": target_amount,
            "scenario_a_minus_target_gross_ils": gap_a,
            "scenario_b_minus_target_gross_ils": gap_b,
            "change_events": changes,
            "blocker_codes": sorted(set(blockers)),
        })
    comparison_states = {row["comparison_state"] for row in rows}
    comparison_state = (
        "COMPLETE" if comparison_states == {"COMPLETE"}
        else "PARTIAL" if "COMPLETE" in comparison_states else "BLOCKED"
    )
    result = {
        "schema_version": CONTRACT,
        "client_id": client_id,
        "start_month": start_month,
        "end_month": end_month,
        "comparison_state": comparison_state,
        "target_comparison_state": "COMPLETE" if target_complete else "BLOCKED",
        "scenario_a": {
            "scenario_id": scenario_a_id,
            "scenario_version": scenario_a_version,
            "manifest_fingerprint": cashflow_a["manifest_fingerprint"],
            "cashflow_fingerprint": cashflow_a["cashflow_fingerprint"],
            "sources": _source_projection(cashflow_a),
        },
        "scenario_b": {
            "scenario_id": scenario_b_id,
            "scenario_version": scenario_b_version,
            "manifest_fingerprint": cashflow_b["manifest_fingerprint"],
            "cashflow_fingerprint": cashflow_b["cashflow_fingerprint"],
            "sources": _source_projection(cashflow_b),
        },
        "shared_source_ids": sorted(
            {source["source_id"] for source in cashflow_a["sources"]}
            & {source["source_id"] for source in cashflow_b["sources"]}
        ),
        "target": target,
        "monthly_rows": rows,
        "execution_allowed": False,
    }
    return {**result, "comparison_fingerprint": fingerprint({
        "contract_version": FINGERPRINT_CONTRACT, "result": result,
    })}


def _read_snapshot_evidence(factory, *, client_id: int, scenario_a_id: str,
                            scenario_b_id: str, start_month: str, end_month: str):
    engine = _engine(factory)
    connection = transaction = db = None
    evidence = None
    primary = None
    cleanup_failed = False
    try:
        connection = engine.connect()
        if connection.dialect.name != "postgresql":
            raise ScenarioSnapshotError("STAGE6_COMPARISON_REQUIRES_POSTGRESQL")
        connection = connection.execution_options(
            isolation_level="REPEATABLE READ", postgresql_readonly=True,
        )
        transaction = connection.begin()
        db = Session(bind=connection, autoflush=False, expire_on_commit=False)
        pair_a = _build_pair_in_snapshot(db, client_id, scenario_a_id, None)
        cashflow_a = _cashflow_extension(
            client_id=client_id, scenario_id=scenario_a_id,
            start_month=start_month, end_month=end_month,
        )(db, pair_a)
        pair_b = _build_pair_in_snapshot(db, client_id, scenario_b_id, None)
        cashflow_b = _cashflow_extension(
            client_id=client_id, scenario_id=scenario_b_id,
            start_month=start_month, end_month=end_month,
        )(db, pair_b)
        target = target_service.assess_in_snapshot(db, client_id)
        evidence = (cashflow_a, cashflow_b, target)
    except BaseException as exc:
        primary = exc
    finally:
        if connection is not None:
            try:
                if transaction is not None and transaction.is_active:
                    transaction.rollback()
                elif connection.in_transaction():
                    connection.rollback()
            except BaseException:
                cleanup_failed = True
        if db is not None:
            try:
                db.close()
            except BaseException:
                cleanup_failed = True
        if connection is not None:
            if cleanup_failed:
                try:
                    connection.invalidate()
                except BaseException:
                    pass
            try:
                connection.close()
            except BaseException:
                cleanup_failed = True
                try:
                    connection.invalidate()
                except BaseException:
                    pass
    if cleanup_failed:
        raise ScenarioSnapshotError("STAGE6_COMPARISON_CLEANUP_FAILED")
    if primary is not None:
        if isinstance(primary, ScenarioSnapshotError):
            raise primary
        if isinstance(primary, DraftError):
            raise ScenarioSnapshotError(primary.code) from primary
        raise ScenarioSnapshotError("STAGE6_COMPARISON_DATABASE_UNAVAILABLE") from primary
    assert evidence is not None
    return deepcopy(evidence)


def compare_scenario_monthly_cashflows(factory, *, client_id: int,
                                       scenario_a_id: str, scenario_a_version: int,
                                       scenario_b_id: str, scenario_b_version: int,
                                       start_month: str, end_month: str,
                                       _snapshot_reader=None) -> dict:
    if (
        isinstance(client_id, bool) or not isinstance(client_id, int) or client_id <= 0
        or not isinstance(scenario_a_id, str) or not scenario_a_id or len(scenario_a_id) > 64
        or not isinstance(scenario_b_id, str) or not scenario_b_id or len(scenario_b_id) > 64
        or scenario_a_id == scenario_b_id
        or isinstance(scenario_a_version, bool) or not isinstance(scenario_a_version, int)
        or scenario_a_version <= 0
        or isinstance(scenario_b_version, bool) or not isinstance(scenario_b_version, int)
        or scenario_b_version <= 0
    ):
        raise ValueError("STAGE6_COMPARISON_REQUEST_INVALID")
    _months(start_month, end_month)
    reader = _snapshot_reader or _read_snapshot_evidence
    cashflow_a, cashflow_b, target = reader(
        factory, client_id=client_id, scenario_a_id=scenario_a_id,
        scenario_b_id=scenario_b_id, start_month=start_month, end_month=end_month,
    )
    if (
        cashflow_a.get("scenario_version") != scenario_a_version
        or cashflow_b.get("scenario_version") != scenario_b_version
    ):
        raise ScenarioSnapshotError("STAGE6_COMPARISON_SCENARIO_VERSION_STALE")
    return _compose(
        client_id=client_id, scenario_a_id=scenario_a_id,
        scenario_a_version=scenario_a_version, scenario_b_id=scenario_b_id,
        scenario_b_version=scenario_b_version, start_month=start_month,
        end_month=end_month, cashflow_a=cashflow_a, cashflow_b=cashflow_b,
        target_result=target,
    )
