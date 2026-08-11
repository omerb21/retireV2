from __future__ import annotations

import calendar
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.models.client import Client
from app.models.m09_cashflow import (
    M09MonthlyResult,
    M09ResolvedComponentInventory,
    M09ScenarioRun,
    M09_WORKFLOW_ACTOR,
    authorize_m09_insert,
    m09_server_timestamp,
    new_m09_id,
)
from app.models.retirement_facts import RecurringExpense, RecurringIncome
from app.schemas.m09_cashflow import (
    M09ContractRequest,
    M09CurrentnessResponse,
    M09InventoryResponse,
    M09M10EligibilityResponse,
    M09MonthlyResultResponse,
    M09RangeTotalsResponse,
    M09RunResponse,
    M09RunSummaryResponse,
)
from app.services.m01_case_service import ensure_m01_editable
from app.services.m06_conversion_service import list_subjects as list_m06_subjects


FAMILY = "deterministic_monthly_cashflow"
CONTRACT_VERSION = "v1"
DOMAIN_CONTRACT_VERSION = "m09-component-domains-v1"
MANIFEST_SCHEMA_VERSION = "m09-assumption-manifest-v1"
SNAPSHOT_SCHEMA_VERSION = "m09-upstream-snapshot-v1"
RESULT_SCHEMA_VERSION = "m09-result-v1"
ENGINE_VERSION = "m09-aggregation-v1"
FINGERPRINT_VERSION = "sha256-canonical-json-v1"
MONEY_PATTERN = re.compile(r"^(0|[1-9]\d*)\.\d{2}$")


@dataclass(frozen=True)
class M09CashflowError(Exception):
    code: str
    message: str
    status_code: int = 409


def _error(code: str, message: str, status_code: int = 409) -> M09CashflowError:
    return M09CashflowError(code=code, message=message, status_code=status_code)


def _json_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, dict):
        return {key: _json_value(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def _canonical_bytes(payload: Any) -> bytes:
    return json.dumps(
        _json_value(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _digest(payload: Any) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _money_text(value: Decimal) -> str:
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        raise ValueError("invalid monetary source")
    if value != value.quantize(Decimal("0.01")):
        raise ValueError("source amount is not canonical two-decimal money")
    return format(value, ".2f")


def _month_range(start: str, end: str) -> list[str]:
    year, month = (int(part) for part in start.split("-"))
    end_year, end_month = (int(part) for part in end.split("-"))
    result: list[str] = []
    while (year, month) <= (end_year, end_month):
        result.append(f"{year:04d}-{month:02d}")
        if month == 12:
            year, month = year + 1, 1
        else:
            month += 1
    return result


def _month_bounds(month: str) -> tuple[date, date]:
    year, number = (int(part) for part in month.split("-"))
    return date(year, number, 1), date(
        year, number, calendar.monthrange(year, number)[1]
    )


def _component_id(component_type: str, source_identity: str, month: str) -> str:
    return "M09-C-" + _digest(
        {
            "component_type": component_type,
            "source_identity": source_identity,
            "month": month,
            "contract": DOMAIN_CONTRACT_VERSION,
        }
    )[:48]


def _monthly_component(
    *,
    component_type: str,
    direction: str,
    source_identity: str,
    source_version: str,
    source_fingerprint: str,
    amount: str,
    month: str,
    provenance: dict[str, Any],
) -> dict[str, Any]:
    return {
        "component_id": _component_id(component_type, source_identity, month),
        "component_type": component_type,
        "direction": direction,
        "amount": amount,
        "currency": "ILS",
        "unit": "ILS/month",
        "month": month,
        "source_identity": source_identity,
        "source_version": source_version,
        "source_fingerprint": source_fingerprint,
        "source_owner": (
            "M06"
            if component_type == "m06_monthly_pension_result"
            else "V2 recurring-fact contract"
        ),
        "provenance": provenance,
    }


def _recurring_source_payload(row: RecurringIncome | RecurringExpense) -> dict[str, Any]:
    payload = {
        "id": row.id,
        "client_id": row.client_id,
        "description": row.description,
        "amount": format(row.amount, "f"),
        "frequency": row.frequency,
        "continuation_status": row.continuation_status,
        "lifecycle_status": row.lifecycle_status,
        "source_status": row.source_status,
        "verification_state": row.verification_state,
        "start_date": row.start_date,
        "end_date": row.end_date,
        "source_type": row.source_type,
        "source_date": row.source_date,
        "updated_at": row.updated_at,
    }
    if isinstance(row, RecurringIncome):
        payload.update(
            income_category=row.income_category, amount_basis=row.amount_basis
        )
    else:
        payload.update(
            expense_category=row.expense_category, expense_type=row.expense_type
        )
    return payload


def _overlaps_horizon(
    start_date: date | None,
    end_date: date | None,
    months: list[str],
) -> bool:
    horizon_start = _month_bounds(months[0])[0]
    horizon_end = _month_bounds(months[-1])[1]
    return not (
        (start_date is not None and start_date > horizon_end)
        or (end_date is not None and end_date < horizon_start)
    )


def _recurring_domain(
    rows: Iterable[RecurringIncome | RecurringExpense],
    months: list[str],
    *,
    domain: str,
) -> dict[str, Any]:
    is_income = domain == "recurring_income"
    component_type = (
        "recurring_income_record" if is_income else "recurring_expense_record"
    )
    direction = "inflow" if is_income else "outflow"
    candidates: list[dict[str, Any]] = []
    blockers: list[str] = []
    economic_keys: dict[tuple[Any, ...], list[str]] = {}

    for row in rows:
        source_identity = f"{domain}:{row.id}"
        source_payload = _recurring_source_payload(row)
        source_fingerprint = _digest(source_payload)
        reasons: list[str] = []
        current = row.lifecycle_status == "current"
        overlaps = _overlaps_horizon(row.start_date, row.end_date, months)
        if not current:
            reasons.append("source_superseded")
        if row.frequency != "monthly":
            reasons.append("frequency_not_monthly")
        if is_income and row.amount_basis != "gross":
            reasons.append("income_amount_basis_not_gross")
        if row.source_status == "not recorded":
            reasons.append("source_authority_not_recorded")
        if row.verification_state == "collected - not yet reviewed":
            reasons.append("source_review_incomplete")
        try:
            amount = _money_text(row.amount)
        except (ValueError, InvalidOperation):
            amount = None
            reasons.append("amount_not_canonical_nonnegative_ils")
        if row.start_date and row.end_date and row.end_date < row.start_date:
            reasons.append("source_date_range_invalid")

        components: list[dict[str, Any]] = []
        partial_month = False
        if current and overlaps and not reasons:
            for month in months:
                first, last = _month_bounds(month)
                if row.start_date is not None and row.start_date > last:
                    continue
                if row.end_date is not None and row.end_date < first:
                    continue
                if (
                    row.start_date is not None and first < row.start_date <= last
                ) or (row.end_date is not None and first <= row.end_date < last):
                    partial_month = True
                    continue
                components.append(
                    _monthly_component(
                        component_type=component_type,
                        direction=direction,
                        source_identity=source_identity,
                        source_version=(
                            row.updated_at.isoformat()
                            if row.updated_at is not None
                            else "unversioned"
                        ),
                        source_fingerprint=source_fingerprint,
                        amount=amount or "0.00",
                        month=month,
                        provenance={
                            "record_id": row.id,
                            "source_status": row.source_status,
                            "verification_state": row.verification_state,
                            "currency_evidence": "accepted-v2-recurring-amount-contract-ils",
                            "amount_basis": (
                                row.amount_basis
                                if isinstance(row, RecurringIncome)
                                else None
                            ),
                        },
                    )
                )
        if partial_month:
            reasons.append("partial_month_unsupported")
            components = []
        if current and overlaps and not components and not reasons:
            reasons.append("no_full_month_applicability")
        if not overlaps and "source_superseded" not in reasons:
            reasons.append("outside_horizon")

        eligible = current and overlaps and not reasons and bool(components)
        if current and overlaps and not eligible:
            blockers.extend(reasons)
        if eligible:
            key = (
                getattr(row, "income_category", None),
                getattr(row, "expense_category", None),
                row.description.strip().casefold(),
                amount,
                row.start_date,
                row.end_date,
            )
            economic_keys.setdefault(key, []).append(source_identity)
        candidates.append(
            {
                "candidate_identity": source_identity,
                "source_identity": source_identity,
                "source_version": (
                    row.updated_at.isoformat()
                    if row.updated_at is not None
                    else "unversioned"
                ),
                "source_fingerprint": source_fingerprint,
                "current": current,
                "eligible": eligible,
                "included": eligible,
                "exclusion_reasons": sorted(set(reasons)),
                "components": components,
                "economic_meaning": {
                    "category": getattr(
                        row,
                        "income_category" if is_income else "expense_category",
                    ),
                    "description": row.description,
                },
            }
        )

    duplicate_groups = [ids for ids in economic_keys.values() if len(ids) > 1]
    if duplicate_groups:
        blockers.append("duplicate_economic_meaning_unresolved")
    included = [item for item in candidates if item["included"]]
    complete = not blockers
    domain_payload: dict[str, Any] = {
        "domain_identity": domain,
        "required": True,
        "candidates": candidates,
        "authoritative_eligible_candidate_ids": [
            item["candidate_identity"] for item in included
        ],
        "mandatory_source_identities": [item["source_identity"] for item in included],
        "complete": complete,
        "ambiguity": bool(duplicate_groups),
        "duplicate_economic_meaning_groups": duplicate_groups,
        "currentness": "current" if complete else "blocked",
        "blocker_codes": sorted(set(blockers)),
        "server_resolved_none": None,
    }
    domain_payload["domain_material_fingerprint"] = _digest(
        {key: value for key, value in domain_payload.items() if key != "server_resolved_none"}
    )
    return domain_payload


def _m06_domain(db: Session, client_id: int, months: list[str]) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    blockers: list[str] = []
    identities: dict[str, list[str]] = {}
    try:
        subjects = list_m06_subjects(db, client_id)
    except Exception:
        subjects = []
        blockers.append("m06_inventory_unavailable")

    for subject in subjects:
        revision = subject.current_revision
        if revision is None:
            continue
        source_identity = f"m06:{subject.subject_id}:{revision.revision_id}"
        manifest = revision.manifest
        reasons: list[str] = []
        relevant = revision.mode == "balance_to_monthly_pension"
        if not relevant:
            reasons.append("m06_mode_not_monthly_pension")
        if revision.state == "superseded":
            reasons.append("m06_superseded")
        if relevant and not subject.eligibility.eligible_for_downstream:
            reasons.extend(subject.eligibility.exclusion_reasons or ["m06_ineligible"])
        handoff = manifest.authoritative_monthly_amount if manifest else None
        if relevant and revision.state != "superseded":
            if manifest is None or handoff is None:
                reasons.append("m06_authoritative_monthly_handoff_missing")
            elif MONEY_PATTERN.fullmatch(handoff) is None:
                reasons.append("m06_authoritative_monthly_handoff_invalid")
        source_fingerprint = _digest(
            {
                "subject_id": subject.subject_id,
                "revision_id": revision.revision_id,
                "state": revision.state,
                "mode": revision.mode,
                "evidence_digest": manifest.fingerprint if manifest else None,
                "handoff": handoff,
                "eligibility": subject.eligibility.model_dump(mode="json"),
            }
        )
        eligible = relevant and revision.state != "superseded" and not reasons
        components = (
            [
                _monthly_component(
                    component_type="m06_monthly_pension_result",
                    direction="inflow",
                    source_identity=source_identity,
                    source_version=revision.revision_id,
                    source_fingerprint=source_fingerprint,
                    amount=handoff or "0.00",
                    month=month,
                    provenance={
                        "m06_subject_id": subject.subject_id,
                        "m06_revision_id": revision.revision_id,
                        "m06_manifest_id": manifest.manifest_id if manifest else None,
                        "m06_manifest_fingerprint": (
                            manifest.fingerprint if manifest else None
                        ),
                        "m05_predecessor_evidence": revision.predecessor_snapshot,
                        "handoff_contract_version": "m06-to-m09-monthly-amount-v1",
                        "formula_owner": "M06",
                    },
                )
                for month in months
            ]
            if eligible
            else []
        )
        if relevant and revision.state != "superseded" and not eligible:
            blockers.extend(reasons)
        if eligible:
            identities.setdefault(revision.input_identity, []).append(source_identity)
        candidates.append(
            {
                "candidate_identity": source_identity,
                "source_identity": source_identity,
                "source_version": revision.revision_id,
                "source_fingerprint": source_fingerprint,
                "current": revision.state != "superseded",
                "eligible": eligible,
                "included": eligible,
                "exclusion_reasons": sorted(set(reasons)),
                "components": components,
                "economic_meaning": {
                    "input_identity": revision.input_identity,
                    "mode": revision.mode,
                },
                "informational_warnings": sorted(
                    set(subject.eligibility.informational_warnings)
                ),
            }
        )

    duplicate_groups = [ids for ids in identities.values() if len(ids) > 1]
    if duplicate_groups:
        blockers.append("duplicate_economic_meaning_unresolved")
    included = [item for item in candidates if item["included"]]
    complete = not blockers
    payload: dict[str, Any] = {
        "domain_identity": "m06_monthly_pension",
        "required": True,
        "candidates": candidates,
        "authoritative_eligible_candidate_ids": [
            item["candidate_identity"] for item in included
        ],
        "mandatory_source_identities": [item["source_identity"] for item in included],
        "complete": complete,
        "ambiguity": bool(duplicate_groups),
        "duplicate_economic_meaning_groups": duplicate_groups,
        "currentness": "current" if complete else "blocked",
        "blocker_codes": sorted(set(blockers)),
        "server_resolved_none": None,
    }
    payload["domain_material_fingerprint"] = _digest(
        {key: value for key, value in payload.items() if key != "server_resolved_none"}
    )
    return payload


def _attach_server_none(
    domain: dict[str, Any],
    *,
    client_id: int,
    request: M09ContractRequest,
    inventory_id: str,
    assessed_at: datetime,
) -> None:
    if domain["complete"] and not domain["authoritative_eligible_candidate_ids"]:
        evidence = {
            "client_id": client_id,
            "domain": domain["domain_identity"],
            "scenario_family": request.scenario_family,
            "scenario_contract_version": request.scenario_contract_version,
            "start_month": request.start_month,
            "end_month": request.end_month,
            "inventory_assessment_id": inventory_id,
            "resolver_actor": M09_WORKFLOW_ACTOR,
            "assessment_timestamp": assessed_at,
            "source_snapshot_digest": _digest(domain["candidates"]),
        }
        evidence["result_fingerprint"] = _digest(evidence)
        domain["server_resolved_none"] = evidence


def _require_client(db: Session, client_id: int) -> Client:
    client = db.scalar(select(Client).where(Client.client_id == client_id))
    if client is None:
        raise _error("m09_resource_not_found", "M09 resource is unavailable", 404)
    return client


def _validate_contract(request: M09ContractRequest) -> None:
    if request.scenario_family != FAMILY:
        raise _error("scenario_family_unsupported", "scenario family is unsupported", 422)
    if request.scenario_contract_version != CONTRACT_VERSION:
        raise _error(
            "scenario_contract_version_unsupported",
            "scenario contract version is unsupported",
            422,
        )


def _build_inventory(
    db: Session, client_id: int, request: M09ContractRequest
) -> M09ResolvedComponentInventory:
    _require_client(db, client_id)
    _validate_contract(request)
    months = _month_range(request.start_month, request.end_month)
    income_rows = list(
        db.scalars(
            select(RecurringIncome)
            .where(RecurringIncome.client_id == client_id)
            .order_by(RecurringIncome.id)
        )
    )
    expense_rows = list(
        db.scalars(
            select(RecurringExpense)
            .where(RecurringExpense.client_id == client_id)
            .order_by(RecurringExpense.id)
        )
    )
    domains = [
        _recurring_domain(income_rows, months, domain="recurring_income"),
        _recurring_domain(expense_rows, months, domain="recurring_expense"),
        _m06_domain(db, client_id, months),
    ]

    pension_income = any(
        candidate["included"]
        and candidate["economic_meaning"].get("category") == "pension"
        for candidate in domains[0]["candidates"]
    )
    m06_income = bool(domains[2]["authoritative_eligible_candidate_ids"])
    if pension_income and m06_income:
        for domain in (domains[0], domains[2]):
            domain["ambiguity"] = True
            domain["complete"] = False
            domain["currentness"] = "blocked"
            domain["blocker_codes"] = sorted(
                set(domain["blocker_codes"] + ["duplicate_economic_meaning_unresolved"])
            )
            domain["domain_material_fingerprint"] = _digest(
                {
                    key: value
                    for key, value in domain.items()
                    if key not in {"server_resolved_none", "domain_material_fingerprint"}
                }
            )

    inventory_id = new_m09_id("M09-I")
    assessed_at = m09_server_timestamp()
    for domain in domains:
        _attach_server_none(
            domain,
            client_id=client_id,
            request=request,
            inventory_id=inventory_id,
            assessed_at=assessed_at,
        )
    blockers = sorted(
        {
            code
            for domain in domains
            for code in domain["blocker_codes"]
        }
    )
    material_fingerprint = _digest(
        {
            "client_id": client_id,
            "scenario_family": request.scenario_family,
            "scenario_contract_version": request.scenario_contract_version,
            "start_month": request.start_month,
            "end_month": request.end_month,
            "component_domain_contract_version": DOMAIN_CONTRACT_VERSION,
            "domain_material_fingerprints": [
                domain["domain_material_fingerprint"] for domain in domains
            ],
        }
    )
    payload = {
        "inventory_schema_version": "m09-resolved-component-inventory-v1",
        "client_id": client_id,
        "scenario_family": request.scenario_family,
        "scenario_contract_version": request.scenario_contract_version,
        "start_month": request.start_month,
        "end_month": request.end_month,
        "component_domain_contract_version": DOMAIN_CONTRACT_VERSION,
        "inventory_assessment_id": inventory_id,
        "assessment_timestamp": assessed_at,
        "actor": M09_WORKFLOW_ACTOR,
        "domains": domains,
        "complete": all(domain["complete"] for domain in domains),
        "blocker_codes": blockers,
        "material_fingerprint": material_fingerprint,
    }
    fingerprint = _digest(payload)
    row = M09ResolvedComponentInventory(
        inventory_id=inventory_id,
        client_id=client_id,
        scenario_family=request.scenario_family,
        scenario_contract_version=request.scenario_contract_version,
        start_month=request.start_month,
        end_month=request.end_month,
        component_domain_contract_version=DOMAIN_CONTRACT_VERSION,
        assessment_timestamp=assessed_at,
        actor=M09_WORKFLOW_ACTOR,
        inventory_payload=_json_value(payload),
        inventory_fingerprint=fingerprint,
        complete=payload["complete"],
        blocker_codes=blockers,
    )
    authorize_m09_insert(row)
    return row


def _inventory_response(row: M09ResolvedComponentInventory) -> M09InventoryResponse:
    return M09InventoryResponse(
        inventory_id=row.inventory_id,
        client_id=row.client_id,
        scenario_family=row.scenario_family,
        scenario_contract_version=row.scenario_contract_version,
        start_month=row.start_month,
        end_month=row.end_month,
        component_domain_contract_version=row.component_domain_contract_version,
        assessment_timestamp=row.assessment_timestamp,
        actor=row.actor,
        domains=row.inventory_payload["domains"],
        complete=row.complete,
        blocker_codes=row.blocker_codes,
        inventory_fingerprint=row.inventory_fingerprint,
    )


def assess_inventory(
    db: Session, client_id: int, request: M09ContractRequest
) -> M09InventoryResponse:
    row = _build_inventory(db, client_id, request)
    try:
        db.add(row)
        db.commit()
        db.refresh(row)
    except Exception:
        db.rollback()
        raise
    return _inventory_response(row)


def get_inventory(
    db: Session, client_id: int, inventory_id: str
) -> M09InventoryResponse:
    row = db.scalar(
        select(M09ResolvedComponentInventory).where(
            M09ResolvedComponentInventory.client_id == client_id,
            M09ResolvedComponentInventory.inventory_id == inventory_id,
        )
    )
    if row is None:
        raise _error("m09_resource_not_found", "M09 resource is unavailable", 404)
    return _inventory_response(row)


def _current_run(db: Session, client_id: int) -> M09ScenarioRun | None:
    return db.scalar(
        select(M09ScenarioRun)
        .where(
            M09ScenarioRun.client_id == client_id,
            M09ScenarioRun.scenario_family == FAMILY,
            M09ScenarioRun.scenario_contract_version == CONTRACT_VERSION,
        )
        .order_by(M09ScenarioRun.run_sequence.desc())
        .limit(1)
    )


def _require_run(db: Session, client_id: int, run_id: str) -> M09ScenarioRun:
    row = db.scalar(
        select(M09ScenarioRun).where(
            M09ScenarioRun.client_id == client_id,
            M09ScenarioRun.run_id == run_id,
        )
    )
    if row is None:
        raise _error("m09_resource_not_found", "M09 resource is unavailable", 404)
    return row


def _included_components(inventory: M09ResolvedComponentInventory) -> list[dict[str, Any]]:
    return [
        component
        for domain in inventory.inventory_payload["domains"]
        for candidate in domain["candidates"]
        if candidate["included"]
        for component in candidate["components"]
    ]


def _typed_warnings(inventory: M09ResolvedComponentInventory) -> list[dict[str, str]]:
    warnings = [
        {"code": code, "classification": "blocking_condition"}
        for code in inventory.blocker_codes
    ]
    informational = sorted(
        {
            str(code)
            for domain in inventory.inventory_payload["domains"]
            for candidate in domain["candidates"]
            for code in candidate.get("informational_warnings", [])
        }
    )
    warnings.extend(
        {"code": code, "classification": "informational_warning"}
        for code in informational
    )
    return warnings


def _monthly_rows(
    run_id: str,
    client_id: int,
    months: list[str],
    components: list[dict[str, Any]],
) -> tuple[list[M09MonthlyResult], dict[str, str], str]:
    by_month: dict[str, list[dict[str, Any]]] = {month: [] for month in months}
    seen: set[str] = set()
    for component in components:
        component_id = component["component_id"]
        if component_id in seen:
            raise _error(
                "duplicate_component_identity",
                "duplicate component identity blocks authoritative execution",
            )
        seen.add(component_id)
        by_month[component["month"]].append(component)

    rows: list[M09MonthlyResult] = []
    range_inflow = Decimal("0.00")
    range_outflow = Decimal("0.00")
    semantic_months: list[dict[str, Any]] = []
    for month in months:
        evidence = sorted(
            by_month[month],
            key=lambda item: (
                item["component_type"],
                item["source_identity"],
                item["component_id"],
            ),
        )
        inflow = sum(
            (Decimal(item["amount"]) for item in evidence if item["direction"] == "inflow"),
            Decimal("0.00"),
        )
        outflow = sum(
            (Decimal(item["amount"]) for item in evidence if item["direction"] == "outflow"),
            Decimal("0.00"),
        )
        net = inflow - outflow
        inflow_text, outflow_text, net_text = (
            format(inflow, ".2f"),
            format(outflow, ".2f"),
            format(net, ".2f"),
        )
        payload = {
            "month": month,
            "component_evidence": evidence,
            "gross_inflow_total": inflow_text,
            "gross_outflow_total": outflow_text,
            "period_net": net_text,
        }
        fingerprint = _digest(payload)
        row = M09MonthlyResult(
            monthly_result_id="M09-M-" + _digest({"run_id": run_id, "month": month})[:48],
            run_id=run_id,
            client_id=client_id,
            month=month,
            gross_inflow_total=inflow,
            gross_outflow_total=outflow,
            period_net=net,
            component_evidence=evidence,
            result_fingerprint=fingerprint,
        )
        authorize_m09_insert(row)
        rows.append(row)
        semantic_months.append(payload | {"result_fingerprint": fingerprint})
        range_inflow += inflow
        range_outflow += outflow
    range_totals = {
        "gross_inflow_total": format(range_inflow, ".2f"),
        "gross_outflow_total": format(range_outflow, ".2f"),
        "period_net": format(range_inflow - range_outflow, ".2f"),
    }
    semantic = _digest(
        {
            "result_schema_version": RESULT_SCHEMA_VERSION,
            "scenario_family": FAMILY,
            "scenario_contract_version": CONTRACT_VERSION,
            "months": semantic_months,
            "range_totals": range_totals,
        }
    )
    return rows, range_totals, semantic


def execute_run(
    db: Session, client_id: int, request: M09ContractRequest
) -> M09RunResponse:
    client = _require_client(db, client_id)
    ensure_m01_editable(client)
    _validate_contract(request)
    inventory = _build_inventory(db, client_id, request)
    current = _current_run(db, client_id)
    run_id = new_m09_id("M09-R")
    sequence = 1 if current is None else current.run_sequence + 1
    manifest = {
        "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
        "scenario_contract_version": request.scenario_contract_version,
        "scenario_family": request.scenario_family,
        "client_id": client_id,
        "start_month": request.start_month,
        "end_month": request.end_month,
        "resolved_component_inventory_id": inventory.inventory_id,
        "resolved_component_inventory_fingerprint": inventory.inventory_fingerprint,
        "engine_version": ENGINE_VERSION,
        "fingerprint_algorithm_version": FINGERPRINT_VERSION,
        "warning_dispositions": [],
    }
    manifest_fingerprint = _digest(manifest)
    manifest["manifest_fingerprint"] = manifest_fingerprint
    snapshot = {
        "snapshot_schema_version": SNAPSHOT_SCHEMA_VERSION,
        "client_id": client_id,
        "scenario_family": request.scenario_family,
        "scenario_contract_version": request.scenario_contract_version,
        "start_month": request.start_month,
        "end_month": request.end_month,
        "inventory_id": inventory.inventory_id,
        "inventory_fingerprint": inventory.inventory_fingerprint,
        "inventory": inventory.inventory_payload,
        "component_evidence": _included_components(inventory),
        "warning_dispositions": [],
        "engine_version": ENGINE_VERSION,
    }
    snapshot_fingerprint = _digest(snapshot)
    snapshot["snapshot_fingerprint"] = snapshot_fingerprint
    status = "success_complete" if inventory.complete else "dependency_failed"
    rows: list[M09MonthlyResult] = []
    range_totals: dict[str, str] | None = None
    semantic_fingerprint: str | None = None
    result_integrity_fingerprint: str | None = None
    blockers = list(inventory.blocker_codes)
    if status == "success_complete":
        rows, range_totals, semantic_fingerprint = _monthly_rows(
            run_id,
            client_id,
            _month_range(request.start_month, request.end_month),
            _included_components(inventory),
        )
        result_integrity_fingerprint = _digest(
            {
                "semantic_result_fingerprint": semantic_fingerprint,
                "assumption_manifest_fingerprint": manifest_fingerprint,
                "upstream_snapshot_fingerprint": snapshot_fingerprint,
                "monthly_result_fingerprints": [row.result_fingerprint for row in rows],
                "range_totals": range_totals,
            }
        )
    run = M09ScenarioRun(
        run_id=run_id,
        client_id=client_id,
        predecessor_run_id=current.run_id if current else None,
        run_sequence=sequence,
        scenario_family=FAMILY,
        scenario_contract_version=CONTRACT_VERSION,
        start_month=request.start_month,
        end_month=request.end_month,
        inventory_id=inventory.inventory_id,
        status=status,
        assumption_manifest=_json_value(manifest),
        assumption_manifest_fingerprint=manifest_fingerprint,
        upstream_snapshot=_json_value(snapshot),
        upstream_snapshot_fingerprint=snapshot_fingerprint,
        warnings=_typed_warnings(inventory),
        blocker_codes=blockers,
        range_totals=range_totals,
        semantic_result_fingerprint=semantic_fingerprint,
        result_integrity_fingerprint=result_integrity_fingerprint,
        actor=M09_WORKFLOW_ACTOR,
        created_at=m09_server_timestamp(),
    )
    authorize_m09_insert(run)
    try:
        db.add(inventory)
        db.add(run)
        db.add_all(rows)
        db.commit()
        db.refresh(run)
    except (IntegrityError, OperationalError) as exc:
        db.rollback()
        raise _error(
            "m09_run_conflict", "another M09 run already won the current chain"
        ) from exc
    except Exception:
        db.rollback()
        raise
    return run_response(db, client_id, run.run_id)


def _monthly_result_response(row: M09MonthlyResult) -> M09MonthlyResultResponse:
    return M09MonthlyResultResponse(
        monthly_result_id=row.monthly_result_id,
        month=row.month,
        gross_inflow_total=format(row.gross_inflow_total, ".2f"),
        gross_outflow_total=format(row.gross_outflow_total, ".2f"),
        period_net=format(row.period_net, ".2f"),
        component_evidence=row.component_evidence,
        result_fingerprint=row.result_fingerprint,
    )


def _stored_months(db: Session, run: M09ScenarioRun) -> list[M09MonthlyResult]:
    return list(
        db.scalars(
            select(M09MonthlyResult)
            .where(
                M09MonthlyResult.client_id == run.client_id,
                M09MonthlyResult.run_id == run.run_id,
            )
            .order_by(M09MonthlyResult.month)
        )
    )


def _integrity_reasons(db: Session, run: M09ScenarioRun) -> list[str]:
    reasons: list[str] = []
    inventory = db.scalar(
        select(M09ResolvedComponentInventory).where(
            M09ResolvedComponentInventory.client_id == run.client_id,
            M09ResolvedComponentInventory.inventory_id == run.inventory_id,
        )
    )
    if inventory is None or _digest(inventory.inventory_payload) != inventory.inventory_fingerprint:
        reasons.append("inventory_integrity_invalid")
    manifest_without_fingerprint = {
        key: value
        for key, value in run.assumption_manifest.items()
        if key != "manifest_fingerprint"
    }
    if (
        _digest(manifest_without_fingerprint) != run.assumption_manifest_fingerprint
        or run.assumption_manifest.get("manifest_fingerprint")
        != run.assumption_manifest_fingerprint
    ):
        reasons.append("assumption_manifest_integrity_invalid")
    snapshot_without_fingerprint = {
        key: value
        for key, value in run.upstream_snapshot.items()
        if key != "snapshot_fingerprint"
    }
    if (
        _digest(snapshot_without_fingerprint) != run.upstream_snapshot_fingerprint
        or run.upstream_snapshot.get("snapshot_fingerprint")
        != run.upstream_snapshot_fingerprint
    ):
        reasons.append("upstream_snapshot_integrity_invalid")
    rows = _stored_months(db, run)
    if run.status == "success_complete":
        expected_months = _month_range(run.start_month, run.end_month)
        if [row.month for row in rows] != expected_months:
            reasons.append("monthly_result_set_invalid")
        for row in rows:
            payload = {
                "month": row.month,
                "component_evidence": row.component_evidence,
                "gross_inflow_total": format(row.gross_inflow_total, ".2f"),
                "gross_outflow_total": format(row.gross_outflow_total, ".2f"),
                "period_net": format(row.period_net, ".2f"),
            }
            if _digest(payload) != row.result_fingerprint:
                reasons.append("monthly_result_integrity_invalid")
                break
        semantic = _digest(
            {
                "result_schema_version": RESULT_SCHEMA_VERSION,
                "scenario_family": run.scenario_family,
                "scenario_contract_version": run.scenario_contract_version,
                "months": [
                    {
                        "month": row.month,
                        "component_evidence": row.component_evidence,
                        "gross_inflow_total": format(row.gross_inflow_total, ".2f"),
                        "gross_outflow_total": format(row.gross_outflow_total, ".2f"),
                        "period_net": format(row.period_net, ".2f"),
                        "result_fingerprint": row.result_fingerprint,
                    }
                    for row in rows
                ],
                "range_totals": run.range_totals,
            }
        )
        if semantic != run.semantic_result_fingerprint:
            reasons.append("semantic_result_integrity_invalid")
        expected_integrity = _digest(
            {
                "semantic_result_fingerprint": run.semantic_result_fingerprint,
                "assumption_manifest_fingerprint": run.assumption_manifest_fingerprint,
                "upstream_snapshot_fingerprint": run.upstream_snapshot_fingerprint,
                "monthly_result_fingerprints": [row.result_fingerprint for row in rows],
                "range_totals": run.range_totals,
            }
        )
        if expected_integrity != run.result_integrity_fingerprint:
            reasons.append("result_integrity_invalid")
    elif rows:
        reasons.append("failed_run_has_monthly_results")
    return list(dict.fromkeys(reasons))


def currentness(
    db: Session, client_id: int, run_id: str
) -> M09CurrentnessResponse:
    run = _require_run(db, client_id, run_id)
    current = _current_run(db, client_id)
    reasons: list[str] = []
    if current is None or current.run_id != run.run_id:
        reasons.append("run_not_current")
    if run.scenario_family != FAMILY or run.scenario_contract_version != CONTRACT_VERSION:
        reasons.append("scenario_contract_unsupported")
    reasons.extend(_integrity_reasons(db, run))
    request = M09ContractRequest(
        scenario_family=run.scenario_family,
        scenario_contract_version=run.scenario_contract_version,
        start_month=run.start_month,
        end_month=run.end_month,
    )
    try:
        reassessed = _build_inventory(db, client_id, request)
        captured_material = run.upstream_snapshot.get("inventory", {}).get(
            "material_fingerprint"
        )
        if reassessed.inventory_payload.get("material_fingerprint") != captured_material:
            reasons.append("dependency_materially_changed")
        if not reassessed.complete:
            reasons.append("dependency_no_longer_eligible")
    except Exception:
        reasons.append("dependency_reassessment_failed")
    return M09CurrentnessResponse(
        run_id=run.run_id,
        current_run_id=current.run_id if current else run.run_id,
        is_current=not reasons,
        reason_codes=list(dict.fromkeys(reasons)),
        assessment_timestamp=m09_server_timestamp(),
    )


def m10_eligibility(
    db: Session, client_id: int, run_id: str
) -> M09M10EligibilityResponse:
    run = _require_run(db, client_id, run_id)
    current = currentness(db, client_id, run_id)
    reasons = list(current.reason_codes)
    if run.status != "success_complete":
        reasons.append("run_not_success_complete")
    if run.blocker_codes:
        reasons.append("run_has_blockers")
    mandatory = [
        warning
        for warning in run.warnings
        if warning.get("classification") == "mandatory_review_warning"
    ]
    if mandatory:
        reasons.append("mandatory_warning_not_disposed")
    informational = [
        str(warning.get("code"))
        for warning in run.warnings
        if warning.get("classification") == "informational_warning"
    ]
    return M09M10EligibilityResponse(
        assessed_scenario_run_id=run.run_id,
        current_scenario_run_id=current.current_run_id,
        eligible_for_m10=not reasons,
        reason_codes=list(dict.fromkeys(reasons)),
        informational_warnings=informational,
        assessment_timestamp=m09_server_timestamp(),
    )


def run_response(db: Session, client_id: int, run_id: str) -> M09RunResponse:
    run = _require_run(db, client_id, run_id)
    inventory = db.scalar(
        select(M09ResolvedComponentInventory).where(
            M09ResolvedComponentInventory.client_id == client_id,
            M09ResolvedComponentInventory.inventory_id == run.inventory_id,
        )
    )
    if inventory is None:
        raise _error("m09_chain_inconsistent", "M09 inventory is unavailable")
    rows = _stored_months(db, run)
    return M09RunResponse(
        run_id=run.run_id,
        client_id=run.client_id,
        predecessor_run_id=run.predecessor_run_id,
        run_sequence=run.run_sequence,
        scenario_family=run.scenario_family,
        scenario_contract_version=run.scenario_contract_version,
        start_month=run.start_month,
        end_month=run.end_month,
        inventory=_inventory_response(inventory),
        status=run.status,
        assumption_manifest=run.assumption_manifest,
        assumption_manifest_fingerprint=run.assumption_manifest_fingerprint,
        upstream_snapshot=run.upstream_snapshot,
        upstream_snapshot_fingerprint=run.upstream_snapshot_fingerprint,
        warnings=run.warnings,
        blocker_codes=run.blocker_codes,
        monthly_results=[_monthly_result_response(row) for row in rows],
        range_totals=(
            M09RangeTotalsResponse(**run.range_totals) if run.range_totals else None
        ),
        semantic_result_fingerprint=run.semantic_result_fingerprint,
        result_integrity_fingerprint=run.result_integrity_fingerprint,
        currentness=currentness(db, client_id, run_id),
        m10_eligibility=m10_eligibility(db, client_id, run_id),
        actor=run.actor,
        created_at=run.created_at,
    )


def list_runs(db: Session, client_id: int) -> list[M09RunSummaryResponse]:
    _require_client(db, client_id)
    rows = list(
        db.scalars(
            select(M09ScenarioRun)
            .where(M09ScenarioRun.client_id == client_id)
            .order_by(M09ScenarioRun.run_sequence.desc())
        )
    )
    result: list[M09RunSummaryResponse] = []
    for run in rows:
        current = currentness(db, client_id, run.run_id)
        eligibility = m10_eligibility(db, client_id, run.run_id)
        result.append(
            M09RunSummaryResponse(
                run_id=run.run_id,
                predecessor_run_id=run.predecessor_run_id,
                run_sequence=run.run_sequence,
                status=run.status,
                start_month=run.start_month,
                end_month=run.end_month,
                inventory_id=run.inventory_id,
                blocker_codes=run.blocker_codes,
                semantic_result_fingerprint=run.semantic_result_fingerprint,
                is_current=current.is_current,
                eligible_for_m10=eligibility.eligible_for_m10,
                created_at=run.created_at,
            )
        )
    return result
