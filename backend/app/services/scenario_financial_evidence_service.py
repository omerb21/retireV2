"""Scenario-bound, read-only financial evidence adapters for Package 2.

These adapters carry canonical facts and hypothetical allocation provenance,
not new financial calculations, withdrawals, severance settlements, tax
exemptions or official fixation authorizations. They run inside the existing
unified REPEATABLE READ READ ONLY transaction, never open another snapshot.
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from sqlalchemy import select

from app.models.retirement_facts import CapitalAsset
from app.models.employment_record import EmploymentRecord
from app.models.grant import Grant
from app.models.actual_capitalization import ActualCapitalization
from app.models.fixation_run import FixationRun
from app.services.scenario_input_manifest_service import _fingerprint

CONTRACT = "SCENARIO_FINANCIAL_EVIDENCE_BINDING_V1"


def _date(value):
    return value.isoformat() if value is not None else None


def _money(value):
    return format(Decimal(value), ".2f") if value is not None else None


def _pack(identity, kind, facts, blockers):
    document = {
        "contract": CONTRACT,
        "client_id": identity["client_id"],
        "scenario_id": identity["scenario_id"],
        "scenario_version": identity["scenario_version"],
        "domain": kind,
        "facts": facts,
        "authority_state": "FACTUAL_EVIDENCE_ONLY",
        "estimated_withdrawable_amount_ils": None,
        "actual_cash_paid_from_plan_ils": None,
        "tax_effect_ils": None,
        "blockers": sorted(set(blockers)),
    }
    document["evidence_fingerprint"] = _fingerprint(document)
    return document


def _capital(db, base):
    identity = base["identity"]
    client_id = identity["client_id"]
    assets = db.scalars(select(CapitalAsset).where(
        CapitalAsset.client_id == client_id,
        CapitalAsset.lifecycle_status == "current",
    ).order_by(CapitalAsset.id)).all()
    decisions = []
    used = defaultdict(Decimal)
    caps = {}
    blockers = {"CAPITAL_PROJECTION_CLIENT_SCOPE_ONLY",
                "CAPITAL_WITHDRAWAL_ELIGIBILITY_NOT_ESTABLISHED"}
    for entry in base["decisions"]:
        row = entry["decision"]
        src = row["source"]
        if src is None:
            blockers.add("CAPITAL_SOURCE_EVIDENCE_MISSING")
        else:
            key = (src["product_id"], src["component_id"])
            capacity = Decimal(src["balance"])
            if key not in caps:
                caps[key] = capacity
            elif caps[key] != capacity:
                blockers.add("CAPITAL_SOURCE_CAPACITY_CONFLICT")
            used[key] += Decimal(row["amount"])
        if entry["source_state"] != "CURRENT_STRUCTURAL_ONLY":
            blockers.add("CAPITAL_SOURCE_STALE_OR_MISSING")
        decisions.append({
            "decision_id": row["decision_id"],
            "action": row["action"],
            "source_product_id": row["product_id"],
            "source_component_id": row["component_id"],
            "amount_planned_ils": row["amount"],
            "effective_date": row["effective_date"],
            "source_state": entry["source_state"],
            "source_fingerprint": src["source_fingerprint"] if src else None,
            "decision_fingerprint": entry["dependency_fingerprint"],
            "cash_paid": False,
            "withdrawal_eligibility_state": "NOT_ESTABLISHED",
        })
    for key, total in used.items():
        if total > caps[key]:
            blockers.add("CAPITAL_SOURCE_OVERALLOCATED")
    records = [{
        "asset_id": row.id,
        "asset_category": row.asset_category,
        "description": row.asset_description,
        "source_status": row.source_status,
        "verification_state": row.verification_state,
        "origin_kind": row.origin_kind,
        "conversion_id": row.conversion_id,
        "reported_current_value_ils": _money(row.known_value_amount),
        "value_as_of_date": _date(row.value_as_of_date),
        "liquidity_note": row.liquidity_note,
        "restriction_note": row.restriction_note,
        "updated_at": _date(row.updated_at),
        "projection_is_admitted": False,
        "available_to_withdraw_ils": None,
    } for row in assets]
    if any(r["origin_kind"] == "conversion" or r["conversion_id"] for r in records):
        blockers.add("CAPITAL_CONVERTED_ASSET_NOT_ADMITTED_FOR_SCENARIO")
    return _pack(identity, "capital", {
        "planning_base_date": base["reference_dates"]["planning_base_date"],
        "retirement_target_date": base["reference_dates"]["retirement_target_date"],
        "decisions": decisions,
        "canonical_assets": records,
        "source_components_consumed_once": [
            {
                "product_id": product_id,
                "component_id": component_id,
                "capacity_ils": _money(caps[(product_id, component_id)]),
                "planned_allocations_total_ils": _money(total),
            }
            for (product_id, component_id), total in sorted(used.items())
        ],
        "capital_projection_contract": "canonical-pre-retirement-capital-projection-execution-v1",
        "scenario_projection_admission": "NOT_AVAILABLE",
    }, blockers)


def _severance(db, base):
    identity = base["identity"]
    client_id = identity["client_id"]
    employment = db.scalars(select(EmploymentRecord).where(
        EmploymentRecord.client_id == client_id,
    ).order_by(EmploymentRecord.employment_record_id)).all()
    grants = db.scalars(select(Grant).where(
        Grant.client_id == client_id,
    ).order_by(Grant.grant_id)).all()
    employer_ids = {r.employment_record_id for r in employment}
    blockers = {"SEVERANCE_ELECTION_NOT_SCENARIO_BOUND",
                "SEVERANCE_HISTORICAL_PAYMENT_NOT_VERIFIED"}
    records = [{
        "employment_record_id": r.employment_record_id,
        "employer_name": r.employer_name,
        "work_start_date": _date(r.work_start_date),
        "work_end_date": _date(r.work_end_date),
        "is_current": r.is_current,
        "exempt_grant_status": r.exempt_grant_status,
        "updated_at": _date(r.updated_at),
    } for r in employment]
    items = []
    for grant in grants:
        if grant.employment_record_id and grant.employment_record_id not in employer_ids:
            blockers.add("SEVERANCE_EMPLOYMENT_REFERENCE_MISSING")
        items.append({
            "grant_id": grant.grant_id,
            "employment_record_id": grant.employment_record_id,
            "employer_name": grant.employer_name,
            "grant_date": _date(grant.grant_date),
            "work_start_date": _date(grant.work_start_date),
            "work_end_date": _date(grant.work_end_date),
            "reported_nominal_amount_ils": _money(grant.nominal_amount),
            "reported_indexed_amount_ils": _money(grant.indexed_amount),
            "updated_at": _date(grant.updated_at),
            # A dated record is NOT proof that it was paid.
            "payment_classification": "UNKNOWN_NOT_VERIFIED",
            "actual_payment_ils": None,
            "future_payment_ils": None,
            "continuity_election": None,
            "tax_exemption_ils": None,
        })
    return _pack(identity, "severance", {
        "employment_records": records,
        "grants": items,
        "scenario_severance_election": "NOT_DEFINED",
    }, blockers)


def _fixation(db, base):
    identity = base["identity"]
    client_id = identity["client_id"]
    caps = db.scalars(select(ActualCapitalization).where(
        ActualCapitalization.client_id == client_id,
    ).order_by(ActualCapitalization.capitalization_id)).all()
    runs = db.scalars(select(FixationRun).where(
        FixationRun.client_id == client_id,
    ).order_by(FixationRun.id)).all()
    # A stored fixation run means only that calculation records exist.
    # There is no field proving a formal Israel Tax Authority determination.
    facts = {
        "historical_actual_capitalizations": [{
            "capitalization_id": r.capitalization_id,
            "reported_amount_ils": _money(r.amount),
            "capitalization_date": _date(r.capitalization_date),
            "source_label": r.source_label,
            "source_basis": r.source_basis,
            "updated_at": _date(r.updated_at),
            "authority_state": "REPORTED_HISTORICAL_FACT_NOT_REVALIDATED",
        } for r in caps],
        "historical_fixation_run_references": [{
            "run_id": r.id,
            "fixation_run_id": r.fixation_run_id,
            "calculation_version": r.calculation_version,
            "calculation_status": r.status,
            "created_at": _date(r.created_at),
            "authority_state": "HISTORICAL_CALCULATION_NOT_TAX_AUTHORITY_APPROVAL",
        } for r in runs],
        "scenario_tax_year": None,
        "scenario_eligibility_admission": None,
        "scenario_fixation_result": None,
        "tax_authority_approval": None,
    }
    return _pack(identity, "fixation_tax", facts, [
        "FIXATION_SCENARIO_ADMISSION_MISSING",
        "FIXATION_OFFICIAL_APPROVAL_NOT_ESTABLISHED",
        "SCENARIO_TAX_BASE_NOT_COMPLETE",
    ])


def collect_scenario_financial_evidence(db, base):
    """One client/version-scoped set of raw facts, no money admission."""
    identity = base["identity"]
    if (type(identity["client_id"]) is not int or identity["client_id"] <= 0
            or type(identity["scenario_version"]) is not int
            or identity["scenario_version"] <= 0
            or not isinstance(identity["scenario_id"], str)
            or not identity["scenario_id"]):
        raise ValueError("SCENARIO_FINANCIAL_EVIDENCE_IDENTITY_INVALID")
    return {
        "capital": _capital(db, base),
        "severance": _severance(db, base),
        "fixation_tax": _fixation(db, base),
    }
