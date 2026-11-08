"""Scenario fixation readiness, evidence only. Never invoke the tax engine."""
from __future__ import annotations

from sqlalchemy import select

from app.models.m07_evidence import M07EvidenceRevision, M07FactEvidence, M07PlannerAssertion
from app.services.scenario_input_manifest_service import _fingerprint
from app.services.scenario_snapshot_candidate_service import ScenarioSnapshotError

CONTRACT = "SCENARIO_FIXATION_READINESS_V1"


def _mapping(source, present=False, verified=False, scenario_bound=False,
             professional_decision=True, blocker=None, references=None):
    return {
        "source": source,
        "present": bool(present),
        "verified": bool(verified),
        "scenario_bound": bool(scenario_bound),
        "professional_decision_required": bool(professional_decision),
        "blocker": blocker,
        "references": references or [],
    }


def build_fixation_readiness(db, base, evidence, domains):
    """Run in the caller-owned PG16 REPEATABLE READ READ ONLY transaction.

    No time-based defaults, no inferred tax year and no cross-client evidence.
    M07 facts are listed for provenance, not accepted as eligibility rights.
    """
    identity = base["identity"]
    expected = {key: identity[key] for key in (
        "client_id", "scenario_id", "scenario_version",
    )}
    for kind in ("fixation_tax", "severance", "capital"):
        row = evidence[kind]
        if (any(row.get(key) != value for key, value in expected.items())
                or row.get("authority_state") != "FACTUAL_EVIDENCE_ONLY"):
            raise ScenarioSnapshotError("FIXATION_READINESS_EVIDENCE_IDENTITY_INVALID")
    severance = domains["severance"]["planning"]
    if any(severance.get(k) != v for k, v in expected.items()):
        raise ScenarioSnapshotError("FIXATION_READINESS_SEVERANCE_IDENTITY_INVALID")
    pension = domains["pension_gross"]
    if pension["state"] == "NONBINDING_ESTIMATE" and (
            not isinstance(pension["result"], dict) or not pension["result_fingerprint"]):
        raise ScenarioSnapshotError("FIXATION_READINESS_PENSION_INVALID")
    client_id = identity["client_id"]
    revisions = db.scalars(select(M07EvidenceRevision).where(
        M07EvidenceRevision.client_id == client_id,
    ).order_by(M07EvidenceRevision.m07_evidence_revision_id)).all()
    revision_ids = [row.m07_evidence_revision_id for row in revisions]
    facts = db.scalars(select(M07FactEvidence).where(
        M07FactEvidence.client_id == client_id,
        M07FactEvidence.m07_evidence_revision_id.in_(revision_ids),
    ).order_by(M07FactEvidence.fact_evidence_id)).all() if revision_ids else []
    assertions = db.scalars(select(M07PlannerAssertion).where(
        M07PlannerAssertion.client_id == client_id,
        M07PlannerAssertion.m07_evidence_revision_id.in_(revision_ids),
    ).order_by(M07PlannerAssertion.assertion_id)).all() if revision_ids else []

    # Exclude observation timestamps and unrelated draft revisions. Finalized
    # evidence fingerprints are content-derived, never application wall-clock.
    finalized = {r.m07_evidence_revision_id: r for r in revisions
                 if r.status == "finalized"}
    eligibility = [{
        "revision_id": r.m07_evidence_revision_id,
        "status": r.status,
        "authority_classification": r.authority_classification,
        "tax_year_on_client_evidence_not_scenario_tax_year": r.tax_year,
        "evidence_fingerprint": r.evidence_fingerprint,
        "source_snapshot_fingerprint": r.source_snapshot_fingerprint,
        "parameter_set_id_on_client_evidence": r.parameter_set_id,
        "parameter_set_fingerprint_on_client_evidence": r.parameter_set_fingerprint,
        "fact_sources": sorted([{
            "fact_evidence_id": f.fact_evidence_id,
            "field_code": f.field_code,
            "verification_state": f.verification_state,
            "content_fingerprint": f.content_fingerprint,
        } for f in facts if f.m07_evidence_revision_id == r.m07_evidence_revision_id],
            key=lambda item: item["fact_evidence_id"]),
        "planner_assertion_sources": sorted([{
            "assertion_id": a.assertion_id,
            "field_code": a.field_code,
            "content_fingerprint": a.content_fingerprint,
            "authority_classification": a.authority_classification,
        } for a in assertions if a.m07_evidence_revision_id == r.m07_evidence_revision_id],
            key=lambda item: item["assertion_id"]),
    } for r in finalized.values()]
    eligibility.sort(key=lambda item: item["revision_id"])
    tax_facts = evidence["fixation_tax"]["facts"]
    grant_facts = evidence["severance"]["facts"]
    capital_facts = evidence["capital"]["facts"]
    choices = severance["choices"]
    grants = grant_facts["grants"]
    cap = tax_facts["historical_actual_capitalizations"]
    overlap = "SEVERANCE_GRANT_COMPONENT_OVERLAP_UNRECONCILED" in evidence["severance"]["blockers"]
    blocked_choices = [r["source_id"] for r in choices if r["state"] != "DRAFT_ONLY"]
    source_evidence = {
        "m07": eligibility,
        "grants": [{
            "grant_id": g["grant_id"], "source_fingerprint": g["source_fingerprint"],
            "linked_employment_record_id": g["employment_record_id"],
            "payment_classification": g["payment_classification"],
        } for g in grants],
        "employment": [{
            "employment_record_id": e["employment_record_id"],
            "source_fingerprint": e["source_fingerprint"],
        } for e in grant_facts["employment_records"]],
        "severance_planning_fingerprint": severance["planning_fingerprint"],
        "severance_choice_source_ids": sorted([
            {"source_kind": r["source_kind"], "source_id": r["source_id"],
             "state": r["state"], "source_fingerprint": r["source_fingerprint"]}
            for r in choices
        ], key=lambda r: (r["source_kind"], r["source_id"])),
        "capital_evidence_fingerprint": evidence["capital"]["evidence_fingerprint"],
        "capital_projection_result_fingerprint": domains["capital"]["result_fingerprint"],
        "historical_capitalizations": [{
            "capitalization_id": c["capitalization_id"],
            "reported_amount_ils": c["reported_amount_ils"],
            "capitalization_date": c["capitalization_date"],
            "source_label": c["source_label"],
            "source_basis": c["source_basis"],
        } for c in cap],
        "pension_gross_result_fingerprint": pension["result_fingerprint"],
        "historical_fixation_run_references": [{
            "run_id": r["run_id"], "calculation_version": r["calculation_version"],
            "calculation_status": r["calculation_status"],
            "authority_state": r["authority_state"],
        } for r in tax_facts["historical_fixation_run_references"]],
        "official_parameter_set": None,
        "tax_year": None,
        "scenario_eligibility_admission": None,
    }
    # No scenario-bound verified eligibility tax year/date is available.
    # Never use M07 event tax_year, target retirement, today, or a prior run
    # to invoke the official-parameter resolver.
    group_mapping = {
        "m07_input_reference": _mapping(
            "M07 finalized client evidence", bool(eligibility), False, False, True,
            "FIXATION_ELIGIBILITY_SCENARIO_BINDING_MISSING",
            [r["revision_id"] for r in eligibility]),
        "parameter_set": _mapping(
            "OfficialParameterSet resolver (requires admitted scenario tax year/date)",
            False, False, False, True, "FIXATION_SCENARIO_TAX_YEAR_MISSING"),
        "grants_collection_state_and_grants": _mapping(
            "Grant and EmploymentRecord", bool(grants), False, False, True,
            "FIXATION_GRANTS_PAYMENT_AND_TAX_CLASSIFICATION_UNVERIFIED",
            [g["grant_id"] for g in grants]),
        "future_grant_reservation": _mapping(
            "Scenario severance planning choices", bool(choices), False, True, True,
            "FIXATION_PLANNED_SEVERANCE_NOT_ADMITTED",
            [r["source_id"] for r in choices]),
        "actual_capitalizations_collection_state_and_items": _mapping(
            "ActualCapitalization", bool(cap), False, False, True,
            "FIXATION_HISTORICAL_CAPITALIZATIONS_NOT_ADMITTED",
            [r["capitalization_id"] for r in cap]),
        "idf": _mapping(
            "No scenario-bound verified IDF commutation record",
            False, False, False, True, "FIXATION_IDF_APPLICABILITY_UNRESOLVED"),
        "calculation_version": _mapping(
            "Fixation calculation version requires separate admission",
            False, False, False, True, "FIXATION_CALCULATION_VERSION_NOT_ADMITTED"),
        "pension_qualification": _mapping(
            "Scenario gross pension and source classification",
            pension["result_fingerprint"] is not None, False, False, True,
            "FIXATION_QUALIFYING_PENSION_CLASSIFICATION_MISSING"),
        "planned_capital_and_commutations": _mapping(
            "Scenario capital evidence", bool(capital_facts["decisions"]),
            False, False, True, "FIXATION_PLANNED_CAPITAL_TAX_TREATMENT_MISSING"),
        "tax_authority_approval": _mapping(
            "No scenario-specific verified authority decision",
            False, False, False, True, "FIXATION_TAX_AUTHORITY_APPROVAL_NOT_ESTABLISHED"),
    }
    blockers = {r["blocker"] for r in group_mapping.values() if r["blocker"]}
    blockers.update(evidence["fixation_tax"]["blockers"])
    if overlap:
        blockers.add("FIXATION_GRANT_COMPONENT_OVERLAP_UNRECONCILED")
    if blocked_choices:
        blockers.add("FIXATION_SEVERANCE_CHOICES_BLOCKED")
    if base["blockers"]:
        blockers.add("FIXATION_SCENARIO_BASE_NOT_CURRENT")
    if identity.get("scenario_status") != "draft":
        blockers.add("FIXATION_SCENARIO_NOT_ACTIVE")
    document = {
        "contract": CONTRACT,
        **expected,
        "manifest_fingerprint": base["manifest_fingerprint"],
        "readiness_state": "BLOCKED",
        "mapping": group_mapping,
        "source_evidence": source_evidence,
        "blockers": sorted(blockers),
        "approved_monthly_exemption_ils": None,
        "tax_due_ils": None,
        "net_cashflow_ils": None,
        "execution_allowed": False,
        "professional_authority": False,
    }
    document["readiness_fingerprint"] = _fingerprint(document)
    return document
