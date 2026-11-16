"""Package 1: one inert, repeatable, client-scoped retirement scenario result contract.

This is an internal read-only assembly boundary, NOT a calculation or an API.
It inherits the existing PostgreSQL REPEATABLE READ READ ONLY snapshot owner.
No caller-provided evidence, monetary result, or professional admission is accepted.
"""
from __future__ import annotations

from copy import deepcopy
import hmac

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models.client import Client
from app.models.planning_input_decision import PlanningInputDecision
from app.models.retirement_facts import PlannerAssumption
from app.models.retirement_monthly_income_target import RetirementMonthlyIncomeTargetElection
from app.models.scenario_draft_pension_election import ScenarioDraftPensionElection
from app.services.scenario_draft_service import DraftError
from app.services.scenario_input_manifest_service import (
    _fingerprint, validate_inert_manifest,
)
from app.services.scenario_snapshot_candidate_service import (
    ScenarioSnapshotError, build_manifest_candidate_snapshot,
)

CONTRACT = "UNIFIED_RETIREMENT_SCENARIO_RESULT_V1"
FINANCIAL_DOMAINS = (
    "pension_gross", "capital", "severance", "fixation_tax",
    "monthly_cashflow", "scenario_comparison",
)


def _iso(value):
    return value.isoformat() if value is not None else None


def _assumptions(db: Session, client_id: int) -> list[dict]:
    rows = db.scalars(select(PlannerAssumption).where(
        PlannerAssumption.client_id == client_id,
        PlannerAssumption.lifecycle_status == "current",
    ).order_by(PlannerAssumption.id)).all()
    return [
        {
            "id": row.id,
            "category": row.assumption_category,
            "title": row.title,
            "value_text": row.assumption_value_text,
            "rationale": row.rationale,
            "owner": row.owner,
            "effective_start_date": _iso(row.effective_start_date),
            "effective_end_date": _iso(row.effective_end_date),
            "review_date": _iso(row.review_date),
            "updated_at": _iso(row.updated_at),
            "authority_state": "UNVERIFIED_FOR_SCENARIO_EXECUTION",
        }
        for row in rows
    ]


def _assemble(db: Session, pair: dict, client_id: int, scenario_id: str) -> dict:
    # The manifest and candidate are already database-derived in this transaction.
    manifest = validate_inert_manifest(pair["manifest"])
    candidate = pair["candidate"]
    if manifest["client_id"] != client_id or manifest["scenario_id"] != scenario_id:
        raise ScenarioSnapshotError("UNIFIED_SCENARIO_IDENTITY_MISMATCH")
    if (candidate.get("client_id", client_id) != client_id
            or candidate.get("scenario_id", scenario_id) != scenario_id
            or candidate.get("scenario_version", manifest["scenario_version"])
            != manifest["scenario_version"]):
        raise ScenarioSnapshotError("UNIFIED_CANDIDATE_IDENTITY_MISMATCH")

    client = db.scalar(select(Client).where(Client.client_id == client_id))
    if client is None:
        raise DraftError("CLIENT_NOT_FOUND", 404)
    planning = db.scalar(select(PlanningInputDecision).where(
        PlanningInputDecision.client_id == client_id
    ))
    income_target = db.scalar(select(RetirementMonthlyIncomeTargetElection).where(
        RetirementMonthlyIncomeTargetElection.client_id == client_id
    ))
    elections = db.scalars(select(ScenarioDraftPensionElection).where(
        ScenarioDraftPensionElection.scenario_id == scenario_id
    ).order_by(ScenarioDraftPensionElection.decision_id)).all()
    by_decision = {}
    for row in elections:
        if row.decision_id in by_decision:
            raise ScenarioSnapshotError("UNIFIED_DUPLICATE_ELECTION")
        by_decision[row.decision_id] = row

    blockers = set(candidate.get("blockers", []))
    if candidate.get("evidence_state") != "STRUCTURALLY_CONSISTENT_NOT_ADMITTED":
        blockers.add("UNIFIED_SOURCE_EVIDENCE_NOT_CONSISTENT")
    if manifest["scenario_status"] != "draft":
        blockers.add("UNIFIED_SCENARIO_NOT_ACTIVE")

    decisions = []
    for decision in manifest["decisions"]:
        source = decision["source"]
        election = by_decision.pop(decision["decision_id"], None)
        source_current = (
            source is not None
            and decision["validation_state"] == "unverified"
            and decision["product_version_at_review"] == source["product_version"]
            and decision["source_fingerprint_at_review"] == source["source_fingerprint"]
        )
        if source is None:
            source_state = "MISSING"
        elif source_current:
            source_state = "CURRENT_STRUCTURAL_ONLY"
        else:
            source_state = "BLOCKED_STALE"
        if source_state != "CURRENT_STRUCTURAL_ONLY":
            blockers.add("UNIFIED_SOURCE_" + source_state + ":" + decision["decision_id"])
        election_data = None
        election_state = "NOT_APPLICABLE" if decision["action"] != "pension" else "MISSING"
        if election is not None:
            valid_election = (
                decision["action"] == "pension"
                and election.scenario_version == manifest["scenario_version"]
                and _iso(election.pension_start_date) >= decision["effective_date"]
                and source_current
            )
            election_state = "CURRENT_DRAFT_ONLY" if valid_election else "BLOCKED_STALE"
            if not valid_election:
                blockers.add("UNIFIED_ELECTION_STALE:" + decision["decision_id"])
            election_data = {
                "decision_id": election.decision_id,
                "scenario_version": election.scenario_version,
                "pension_start_date": _iso(election.pension_start_date),
                "target_year": election.target_year,
                "survivors_option": election.survivors_option,
                "spouse_age_diff": election.spouse_age_diff,
                "coefficient_selection": election.coefficient_selection,
                "company_name": election.company_name,
                "option_name": election.option_name,
                "authority_state": "NOT_PROFESSIONALLY_ADMITTED",
            }
        # A saved selection is never a factor approval. Unselected pension
        # decisions stay explicit, rather than silently receiving defaults.
        if decision["action"] == "pension" and election_state == "MISSING":
            blockers.add("UNIFIED_ELECTION_MISSING:" + decision["decision_id"])
        decision_entry = {
            "decision": deepcopy(decision),
            "source_state": source_state,
            "election": election_data,
            "election_state": election_state,
        }
        decision_entry["dependency_fingerprint"] = _fingerprint(decision_entry)
        decisions.append(decision_entry)
    if by_decision:
        blockers.add("UNIFIED_ORPHAN_ELECTION")
    if not decisions:
        blockers.add("UNIFIED_DECISIONS_MISSING")

    planning_dates = {
        "planning_base_date": _iso(planning.planning_base_date) if planning else None,
        "retirement_target_date": _iso(planning.retirement_target_date) if planning else None,
        "planning_decision_version": planning.version if planning else None,
        "planning_reference_fingerprint": (
            planning.retirement_target_reference_fingerprint if planning else None
        ),
        "client_planned_retirement_date": _iso(client.planned_retirement_date),
        "client_planned_retirement_age": client.planned_retirement_age,
    }
    if planning_dates["retirement_target_date"] is None:
        blockers.add("UNIFIED_RETIREMENT_TARGET_DATE_MISSING")
    target_data = None
    if income_target is not None:
        target_data = {
            "version": income_target.version,
            "lifecycle_state": income_target.lifecycle_state,
            "retirement_target_date": _iso(income_target.retirement_target_date),
            "monthly_amount_text": income_target.monthly_amount_text,
            "currency": income_target.currency,
            "income_basis": income_target.income_basis,
            "price_basis": income_target.price_basis,
            "price_reference_date": _iso(income_target.price_reference_date),
            "source_kind": income_target.source_kind,
            "target_semantic_fingerprint": income_target.target_semantic_fingerprint,
            "planning_calculation_input_fingerprint":
                income_target.planning_calculation_input_fingerprint,
            "authority_state": "NOT_REVALIDATED_FOR_SCENARIO",
        }
        if (income_target.lifecycle_state != "CONFIRMED"
                or _iso(income_target.retirement_target_date)
                != planning_dates["retirement_target_date"]):
            blockers.add("UNIFIED_INCOME_TARGET_STALE")
    assumptions = _assumptions(db, client_id)
    client_facts = {
        "client_id": client.client_id,
        "birth_date": _iso(client.birth_date),
        "employment_status": client.employment_status,
        "updated_at": _iso(client.updated_at),
    }
    # No calculation output is imported without the authoritative engine's
    # native in-snapshot validation and professional admission (package 2).
    # This prevents a synthetic gross amount, taxation, or a stale preimage
    # being promoted by this packaging layer.
    financial_domains = {
        name: {
            "state": "BLOCKED" if blockers else "NOT_CONNECTED",
            "result": None,
            "professional_authority": False,
            "result_fingerprint": None,
        }
        for name in FINANCIAL_DOMAINS
    }
    payload = {
        "schema_version": CONTRACT,
        "identity": {
            "client_id": client_id,
            "scenario_id": scenario_id,
            "scenario_version": manifest["scenario_version"],
            "scenario_status": manifest["scenario_status"],
        },
        "reference_dates": planning_dates,
        "client_facts": client_facts,
        "manifest_fingerprint": manifest["manifest_fingerprint"],
        "source_candidate_state": candidate.get("evidence_state", "BLOCKED"),
        "source_facts": deepcopy(candidate.get("source_facts", [])),
        "decisions": decisions,
        "assumptions": assumptions,
        "income_target": target_data,
        "financial_domains": financial_domains,
        "blockers": sorted(blockers),
        "execution_allowed": False,
        "professional_authority": False,
    }
    payload["result_fingerprint"] = _fingerprint(payload)
    return payload


def build_unified_scenario_result(
    factory: sessionmaker[Session], *, client_id: int, scenario_id: str,
) -> dict:
    """Read-only, repeatable, one-transaction contract. No HTTP exposure."""
    return build_manifest_candidate_snapshot(
        factory, client_id=client_id, scenario_id=scenario_id,
        _snapshot_extension=lambda db, pair: _assemble(db, pair, client_id, scenario_id),
    )


def assert_unified_result_current(
    factory: sessionmaker[Session], *, client_id: int, scenario_id: str,
    expected_result_fingerprint: str,
) -> bool:
    """Re-derive all dependencies; false if *any* client/scenario fact changed.

    Only a valid current result can be compared. A failure to retrieve/validate
    the new snapshot propagates, never silently preserves old authority.
    """
    if (not isinstance(expected_result_fingerprint, str)
            or len(expected_result_fingerprint) != 64
            or any(ch not in "0123456789abcdef" for ch in expected_result_fingerprint)):
        return False
    current = build_unified_scenario_result(
        factory, client_id=client_id, scenario_id=scenario_id,
    )
    return hmac.compare_digest(
        current["result_fingerprint"], expected_result_fingerprint,
    )
