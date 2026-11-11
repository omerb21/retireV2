"""Scenario-scoped fixation professional draft ledger.

All reads and writes operate in their caller's PostgreSQL Session. No engine,
fixation admission, preview, tax calculation or official approval is invoked.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import func, select, update, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.scenario_draft import ScenarioDraft, ScenarioDraftDecision
from app.models.official_parameter_set import OfficialParameterSet
from app.services.official_parameter_service import resolve_official_parameter_set
from app.models.scenario_fixation_approval import (
    ScenarioFixationApprovalHead, ScenarioFixationApprovalRevision,
)
from app.schemas.scenario_fixation_approval import FixationProfessionalDraftReplace, FixationProfessionalApprovalRequest
from app.services.scenario_draft_service import DraftError, _scenario
from app.services.scenario_input_manifest_service import _fingerprint
from app.services.scenario_snapshot_candidate_service import _build_pair_in_snapshot

CONTRACT = "SCENARIO_FIXATION_PROFESSIONAL_APPROVAL_V1"
# No positive gate exists. This is intentional until a separate, admitted
# professional authority contract is approved.
UNRESOLVED_AUTHORITY = "FIXATION_PROFESSIONAL_GATE_NOT_ADMITTED"


def _current(db, client_id: int, scenario_id: str) -> dict:
    # Late import prevents a circular dependency with unified projection.
    from app.services.scenario_unified_engine_binding_service import _assemble_bound
    pair = _build_pair_in_snapshot(db, client_id, scenario_id, None)
    bound = _assemble_bound(db, pair, client_id, scenario_id,
                            start_month=None, end_month=None)
    return bound["domain_results"]["fixation_tax"]["readiness"]


def _head(db, client_id, scenario_id):
    return db.scalar(select(ScenarioFixationApprovalHead).where(
        ScenarioFixationApprovalHead.client_id == client_id,
        ScenarioFixationApprovalHead.scenario_id == scenario_id,
    ))


def _revision(db, head):
    return db.scalar(select(ScenarioFixationApprovalRevision).where(
        ScenarioFixationApprovalRevision.approval_id == head.approval_id,
        ScenarioFixationApprovalRevision.approval_version == head.current_version,
    ))


def _selected_sources(db, client_id: int, scenario_id: str,
                      readiness: dict, decisions: list[dict]) -> tuple[list[dict], list[str]]:
    """Resolve declared source IDs against this client/scenario, never trust IDs.

    Resolution here proves only that a record exists and its content is
    current. It intentionally does NOT convert planner assertions into
    professional eligibility, a qualified pension, paid grant or tax approval.
    """
    sources = readiness["source_evidence"]
    by_m07 = {r["revision_id"]: r for r in sources["m07"]}
    by_grant = {r["grant_id"]: r for r in sources["grants"]}
    by_cap = {r["capitalization_id"]: r for r in sources["historical_capitalizations"]}
    by_choice = {r["source_id"]: r for r in sources["severance_choice_source_ids"]}
    by_pension = {
        r.decision_id: r for r in db.scalars(select(ScenarioDraftDecision).where(
            ScenarioDraftDecision.scenario_id == scenario_id
        )).all()
    }
    records = []
    blockers = set()
    eligibility_dates = {
        r["eligibility_date"] for r in decisions
        if r["group"] == "eligibility" and r["eligibility_date"] is not None
    }
    # No implicit selection of one of several professional determinations.
    eligibility_date = next(iter(eligibility_dates)) if len(eligibility_dates) == 1 else None
    if len(eligibility_dates) > 1:
        blockers.add("FIXATION_REVIEW_ELIGIBILITY_DATES_CONFLICT")
    for decision in decisions:
        group, source_id = decision["group"], decision["source_id"]
        evidence = None
        reason = None
        if group == "eligibility":
            row = by_m07.get(source_id)
            if row is not None:
                evidence = {"revision_id": row["revision_id"],
                            "evidence_fingerprint": row["evidence_fingerprint"],
                            "source_snapshot_fingerprint": row["source_snapshot_fingerprint"],
                            "status": row["status"]}
            else:
                reason = "FIXATION_REVIEW_M07_SOURCE_NOT_FINALIZED_OR_FOREIGN"
        elif group == "historical_grant":
            row = by_grant.get(source_id)
            if row is not None:
                evidence = {"grant_id": row["grant_id"],
                            "source_fingerprint": row["source_fingerprint"],
                            "payment_classification": row["payment_classification"]}
            else:
                reason = "FIXATION_REVIEW_GRANT_SOURCE_NOT_FOUND"
        elif group == "historical_capitalization":
            row = by_cap.get(source_id)
            if row is not None:
                evidence = {k: row[k] for k in (
                    "capitalization_id", "reported_amount_ils",
                    "capitalization_date", "source_label", "source_basis",
                )}
            else:
                reason = "FIXATION_REVIEW_CAPITALIZATION_SOURCE_NOT_FOUND"
        elif group == "severance_continuity":
            row = by_choice.get(source_id)
            if row is not None:
                evidence = {k: row[k] for k in (
                    "source_kind", "source_id", "state", "source_fingerprint",
                )}
                if row["state"] != "DRAFT_ONLY":
                    reason = "FIXATION_REVIEW_SEVERANCE_SOURCE_BLOCKED"
            else:
                reason = "FIXATION_REVIEW_SEVERANCE_SOURCE_NOT_FOUND"
        elif group == "pension_classification":
            row = by_pension.get(source_id)
            if row is not None and row.action == "pension":
                evidence = {"decision_id": row.decision_id,
                            "source_component_id": row.source_component_id,
                            "source_fingerprint_at_review": row.source_fingerprint_at_review,
                            "amount_ils": format(row.amount, ".2f")}
            else:
                reason = "FIXATION_REVIEW_PENSION_SOURCE_NOT_FOUND"
        elif group == "planned_withdrawal_or_commutation":
            row = by_pension.get(source_id)
            if row is not None and row.action == "capital_asset":
                evidence = {"decision_id": row.decision_id,
                            "source_component_id": row.source_component_id,
                            "source_fingerprint_at_review": row.source_fingerprint_at_review,
                            "amount_ils": format(row.amount, ".2f")}
            else:
                reason = "FIXATION_REVIEW_CAPITAL_SOURCE_NOT_FOUND"
        elif group == "tax_year_and_parameters":
            row = db.get(OfficialParameterSet, source_id)
            tax_year = decision["tax_year"]
            if row is None:
                reason = "FIXATION_REVIEW_PARAMETER_SET_NOT_FOUND"
            else:
                evidence = {
                    "parameter_set_id": row.parameter_set_id,
                    "tax_year": row.tax_year, "effective_from": row.effective_from.isoformat(),
                    "effective_to": row.effective_to.isoformat() if row.effective_to else None,
                    "status": row.status, "content_fingerprint": row.content_fingerprint,
                    "parameter_set_version": row.parameter_set_version,
                }
                if (tax_year is None or tax_year != row.tax_year
                        or decision["parameter_set_id"] != source_id
                        or eligibility_date is None):
                    reason = "FIXATION_REVIEW_PARAMETER_SCOPE_NOT_ESTABLISHED"
                else:
                    from datetime import date
                    selected_date = date.fromisoformat(eligibility_date)
                    resolved = resolve_official_parameter_set(
                        db_session=db, tax_year=tax_year, effective_date=selected_date,
                    )
                    if (resolved.result != "resolved"
                            or resolved.selected_parameter_set_id != source_id):
                        reason = "FIXATION_REVIEW_PARAMETER_SET_NOT_APPLICABLE"
        else:
            reason = "FIXATION_REVIEW_UNSUPPORTED_GROUP"
        if reason:
            blockers.add(reason)
        records.append({
            "group": group, "source_id": source_id,
            "source_evidence": evidence, "blocker": reason,
        })
    return records, sorted(blockers)


def project_approval(db, client_id: int, scenario_id: str, readiness: dict) -> dict:
    """For unified result: reuse its already-derived readiness, no recursion."""
    if any(readiness[k] != val for k, val in (
        ("client_id", client_id), ("scenario_id", scenario_id)
    )):
        raise DraftError("FIXATION_APPROVAL_READINESS_IDENTITY_INVALID", 409)
    head = _head(db, client_id, scenario_id)
    blockers = set(readiness["blockers"])
    # Do not infer downstream execution authority from an internal decision.
    blockers.add(UNRESOLVED_AUTHORITY)
    # Existing GET contract supplies server-derived CAS tokens and factual
    # readiness evidence. Never accept these tokens without revalidating them
    # inside the save transaction.
    current_snapshot = {
        "scenario_version": readiness["scenario_version"],
        "manifest_fingerprint": readiness["manifest_fingerprint"],
        "readiness_fingerprint": readiness["readiness_fingerprint"],
        "readiness_state": readiness["readiness_state"],
        "mapping": readiness["mapping"],
        "source_evidence": readiness["source_evidence"],
        "blockers": readiness["blockers"],
        "professional_authority": False,
        "execution_allowed": False,
    }
    if head is None:
        return {
            "decision_state": "MISSING", "authority_scope": "FIXATION_INTERNAL_REVIEW_ONLY",
            "internal_professional_authority": False,
            "contract": CONTRACT, "client_id": client_id,
            "scenario_id": scenario_id, "approval_id": None,
            "approval_version": 0, "record_status": "MISSING",
            "validity_state": "BLOCKED",
            "decisions": [], "actor_id": None,
            "admission_controls": None, "occurred_at": None,
            "approval_fingerprint": None, "dependency_fingerprint": None,
            "readiness_fingerprint_at_save": None,
            "current_readiness": current_snapshot,
            "blockers": sorted(blockers),
            "professional_authority": False, "execution_allowed": False,
            "tax_authority_approval": None,
        }
    row = _revision(db, head)
    if row is None or row.client_id != client_id or row.scenario_id != scenario_id:
        raise DraftError("FIXATION_APPROVAL_REVISION_IDENTITY_INVALID", 409)
    selected_sources, review_blockers = _selected_sources(
        db, client_id, scenario_id, readiness, row.decisions_json["decisions"],
    )
    current_dependency = _fingerprint({
        "manifest_fingerprint": readiness["manifest_fingerprint"],
        "readiness_fingerprint": readiness["readiness_fingerprint"],
        "decisions": row.decisions_json["decisions"],
        "admission_controls": row.decisions_json.get("admission_controls"),
        "selected_sources": selected_sources,
    })
    blockers.update(review_blockers)
    stale = (
        row.scenario_version != readiness["scenario_version"]
        or row.manifest_fingerprint != readiness["manifest_fingerprint"]
        or row.readiness_fingerprint != readiness["readiness_fingerprint"]
        or row.dependency_fingerprint != current_dependency
    )
    if stale:
        blockers.add("FIXATION_PROFESSIONAL_APPROVAL_STALE")
    decision_state = row.status if row.status == "APPROVED_INTERNAL" else "DRAFT"
    decision_meta = row.decisions_json.get("internal_decision")
    approved_current = (
        decision_state == "APPROVED_INTERNAL"
        and not stale and isinstance(decision_meta, dict)
        and decision_meta.get("authority_scope") == "FIXATION_INTERNAL_REVIEW_ONLY"
        and decision_meta.get("admission_review_fingerprint")
        and decision_meta.get("preparation_fingerprint")
        and decision_meta.get("eligibility_fingerprint")
        and decision_meta.get("review_reference")
        and row.action == "APPROVE_INTERNAL"
    )
    if decision_state == "APPROVED_INTERNAL" and not approved_current and not stale:
        blockers.add("FIXATION_INTERNAL_APPROVAL_RECORD_INVALID")
    # A stored decision remains historical; only a matching current source
    # snapshot can produce CURRENT. The existing authority flags stay false
    # for every downstream calculation and tax consumer.
    return {
        "decision_state": decision_state,
        "authority_scope": "FIXATION_INTERNAL_REVIEW_ONLY",
        "internal_professional_authority": bool(approved_current),
        "internal_decision": decision_meta if decision_state == "APPROVED_INTERNAL" else None,
        "contract": CONTRACT, "client_id": client_id, "scenario_id": scenario_id,
        "approval_id": head.approval_id,
        "approval_version": head.current_version,
        "scenario_version_at_save": row.scenario_version,
        "manifest_fingerprint_at_save": row.manifest_fingerprint,
        "readiness_fingerprint_at_save": row.readiness_fingerprint,
        "dependency_fingerprint": row.dependency_fingerprint,
        "approval_fingerprint": row.approval_fingerprint,
        "record_status": row.status, "validity_state": "STALE" if stale else "CURRENT" if approved_current else "BLOCKED",
        "decisions": row.decisions_json["decisions"],
        "admission_controls": row.decisions_json.get("admission_controls"),
        "actor_id": row.actor_id, "occurred_at": row.occurred_at.isoformat(),
        "selected_source_evidence": selected_sources,
        "current_readiness": current_snapshot,
        "blockers": sorted(blockers),
        "professional_authority": False, "execution_allowed": False,
        "tax_authority_approval": None,
    }


def read(db, client_id: int, scenario_id: str) -> dict:
    _scenario(db, client_id, scenario_id)
    return project_approval(db, client_id, scenario_id, _current(db, client_id, scenario_id))


def history(db, client_id: int, scenario_id: str) -> list[dict]:
    _scenario(db, client_id, scenario_id)
    head = _head(db, client_id, scenario_id)
    if head is None:
        return []
    rows = db.scalars(select(ScenarioFixationApprovalRevision).where(
        ScenarioFixationApprovalRevision.approval_id == head.approval_id,
    ).order_by(ScenarioFixationApprovalRevision.approval_version)).all()
    return [{
        "revision_id": r.revision_id, "approval_id": r.approval_id,
        "approval_version": r.approval_version, "scenario_version": r.scenario_version,
        "manifest_fingerprint": r.manifest_fingerprint,
        "readiness_fingerprint": r.readiness_fingerprint,
        "dependency_fingerprint": r.dependency_fingerprint,
        "approval_fingerprint": r.approval_fingerprint,
        "decisions": r.decisions_json["decisions"],
        "admission_controls": r.decisions_json.get("admission_controls"),
        "selected_source_evidence_at_save": r.decisions_json.get(
            "selected_source_evidence_at_save", [],
        ),
        "blockers": r.blockers_json, "status": r.status,
        "action": r.action, "actor_id": r.actor_id,
        "decision_state": r.status,
        "internal_decision": r.decisions_json.get("internal_decision"),
        "occurred_at": r.occurred_at.isoformat(),
        "professional_authority": False,
        "tax_authority_approval": None,
    } for r in rows]


def save_draft(db, client_id: int, scenario_id: str,
               request: FixationProfessionalDraftReplace, actor: str) -> dict:
    if db.get_bind().dialect.name != "postgresql":
        raise DraftError("FIXATION_APPROVAL_REQUIRES_POSTGRESQL", 503)
    if not actor or actor == "local-development-only":
        raise DraftError("FIXATION_PROFESSIONAL_ACTOR_REQUIRED", 403)
    # Serialize all saves for the same scenario. A concurrent writer must wait
    # before validating CAS. Source changes after commit are caught by reads.
    scenario = db.scalar(select(ScenarioDraft).where(
        ScenarioDraft.client_id == client_id,
        ScenarioDraft.scenario_id == scenario_id,
    ).with_for_update())
    if scenario is None:
        raise DraftError("SCENARIO_NOT_FOUND", 404)
    if scenario.status != "draft":
        raise DraftError("FIXATION_APPROVAL_SCENARIO_INACTIVE", 409)
    readiness = _current(db, client_id, scenario_id)
    if (request.expected_scenario_version != readiness["scenario_version"]
            or request.expected_manifest_fingerprint != readiness["manifest_fingerprint"]
            or request.expected_readiness_fingerprint != readiness["readiness_fingerprint"]):
        raise DraftError("FIXATION_APPROVAL_SOURCE_CONFLICT", 409)
    records = [r.model_dump(mode="json") for r in request.decisions]
    content = {"decisions": sorted(records, key=lambda r: (r["group"], r["source_id"]))}
    content["admission_controls"] = (
        request.admission_controls.model_dump(mode="json")
        if request.admission_controls is not None else None
    )
    # Asserted source IDs and evidence references are recorded, not promoted to
    # admission. Unknown sources remain explicitly blocked in this phase.
    head = _head(db, client_id, scenario_id)
    expected = request.expected_approval_version
    if head is None:
        if expected != 0:
            raise DraftError("FIXATION_APPROVAL_VERSION_CONFLICT", 409)
        approval_id = uuid4().hex
        db.execute(pg_insert(ScenarioFixationApprovalHead).values(
            approval_id=approval_id, client_id=client_id,
            scenario_id=scenario_id, current_version=1,
            status="DRAFT", updated_by=actor,
        ).on_conflict_do_nothing(index_elements=["client_id", "scenario_id"]))
        head = _head(db, client_id, scenario_id)
        if head is None or head.approval_id != approval_id:
            raise DraftError("FIXATION_APPROVAL_VERSION_CONFLICT", 409)
        version = 1
    else:
        if expected != head.current_version:
            raise DraftError("FIXATION_APPROVAL_VERSION_CONFLICT", 409)
        version = expected + 1
        result = db.execute(update(ScenarioFixationApprovalHead).where(
            ScenarioFixationApprovalHead.approval_id == head.approval_id,
            ScenarioFixationApprovalHead.client_id == client_id,
            ScenarioFixationApprovalHead.scenario_id == scenario_id,
            ScenarioFixationApprovalHead.current_version == expected,
        ).values(current_version=version, status="DRAFT", updated_by=actor, updated_at=func.now()))
        if result.rowcount != 1:
            raise DraftError("FIXATION_APPROVAL_VERSION_CONFLICT", 409)
    selected_sources, selection_blockers = _selected_sources(
        db, client_id, scenario_id, readiness, content["decisions"],
    )
    # Preserve the exact server-derived source preimages used at save time.
    # Live reads independently resolve these again to determine staleness.
    content["selected_source_evidence_at_save"] = selected_sources
    dependency = _fingerprint({
        "manifest_fingerprint": readiness["manifest_fingerprint"],
        "readiness_fingerprint": readiness["readiness_fingerprint"],
        "decisions": content["decisions"],
        "admission_controls": content["admission_controls"],
        "selected_sources": selected_sources,
    })
    approval_fp = _fingerprint({
        "contract": CONTRACT, "client_id": client_id, "scenario_id": scenario_id,
        "approval_version": version, "dependency_fingerprint": dependency,
        "actor_id": actor, "status": "DRAFT",
    })
    db.add(ScenarioFixationApprovalRevision(
        revision_id=uuid4().hex, approval_id=head.approval_id,
        client_id=client_id, scenario_id=scenario_id,
        approval_version=version, scenario_version=readiness["scenario_version"],
        manifest_fingerprint=readiness["manifest_fingerprint"],
        readiness_fingerprint=readiness["readiness_fingerprint"],
        dependency_fingerprint=dependency, approval_fingerprint=approval_fp,
        decisions_json=content, blockers_json=sorted(set(
            readiness["blockers"] + selection_blockers + [UNRESOLVED_AUTHORITY]
        )),
        status="DRAFT", action="SAVE_DRAFT", actor_id=actor,
        occurred_at=datetime.now(timezone.utc),
    ))
    db.flush()
    return project_approval(db, client_id, scenario_id, readiness)


# Only readiness blockers intrinsic to the deliberately non-authoritative
# projection may be superseded by a fresh successful Admission Review.
# Unrecognized/new blockers fail closed, never silently become approved.
_INTERNAL_READINESS_NOT_EXECUTION = frozenset({
    "FIXATION_ELIGIBILITY_SCENARIO_BINDING_MISSING",
    "FIXATION_SCENARIO_TAX_YEAR_MISSING",
    "FIXATION_GRANTS_PAYMENT_AND_TAX_CLASSIFICATION_UNVERIFIED",
    "FIXATION_PLANNED_SEVERANCE_NOT_ADMITTED",
    "FIXATION_HISTORICAL_CAPITALIZATIONS_NOT_ADMITTED",
    "FIXATION_IDF_APPLICABILITY_UNRESOLVED",
    "FIXATION_CALCULATION_VERSION_NOT_ADMITTED",
    "FIXATION_QUALIFYING_PENSION_CLASSIFICATION_MISSING",
    "FIXATION_PLANNED_CAPITAL_TAX_TREATMENT_MISSING",
    "FIXATION_TAX_AUTHORITY_APPROVAL_NOT_ESTABLISHED",
})
_REQUIRED_GROUPS = frozenset({
    "eligibility", "tax_year_and_parameters", "pension_classification",
})


def _internal_professional_blockers(item: dict, prepared: dict, eligible: dict,
                                    admitted: dict) -> list[str]:
    """The accepted initial scope is the verified basic, no-grants/no-IDF path.

    Human attestation is mandatory IN ADDITION to server-derived evidence,
    not an algorithmic inference of pension/tax rights. Unsupported cases
    remain blocked until independently reviewed and a contract is approved.
    """
    blockers = set()
    current = item["current_readiness"]
    blockers.update(set(current["blockers"]) - _INTERNAL_READINESS_NOT_EXECUTION)
    if item["validity_state"] == "STALE":
        blockers.add("FIXATION_INTERNAL_REVIEW_STALE")
    if item["record_status"] != "DRAFT":
        blockers.add("FIXATION_INTERNAL_DRAFT_REQUIRED")
    controls = item.get("admission_controls")
    if not isinstance(controls, dict) or any(
        controls.get(group, {}).get("state") != "confirmed_none"
        for group in ("grants_collection", "actual_capitalizations_collection")
    ):
        blockers.add("FIXATION_INTERNAL_UNSUPPORTED_COLLECTION_SCOPE")
    if not isinstance(controls, dict) or controls.get("idf", {}).get("applicability") != "NOT_APPLICABLE":
        blockers.add("FIXATION_INTERNAL_IDF_REQUIRES_SEPARATE_REVIEW")
    decisions = item.get("decisions", [])
    groups = {d["group"] for d in decisions}
    if groups != _REQUIRED_GROUPS or len(decisions) != 3:
        blockers.add("FIXATION_INTERNAL_UNRESOLVED_DECISION_SCOPE")
    for decision in decisions:
        if (decision.get("determination") != "PLANNER_ASSERTED"
                or not decision.get("reason", "").strip()
                or not decision.get("evidence_references")):
            blockers.add("FIXATION_INTERNAL_OPEN_OR_UNSUPPORTED_ASSERTION")
        if decision["group"] == "eligibility" and not decision.get("eligibility_date"):
            blockers.add("FIXATION_INTERNAL_ELIGIBILITY_NOT_DETERMINED")
        if decision["group"] == "tax_year_and_parameters" and (
                not decision.get("tax_year") or not decision.get("parameter_set_id")):
            blockers.add("FIXATION_INTERNAL_PARAMETERS_NOT_DETERMINED")
        if decision["group"] == "pension_classification" and not decision.get("tax_classification"):
            blockers.add("FIXATION_INTERNAL_PENSION_CLASSIFICATION_NOT_DETERMINED")
    by_group = {d["group"]: d for d in item.get("selected_source_evidence", [])}
    for group in _REQUIRED_GROUPS:
        source = by_group.get(group)
        if not source or source.get("blocker") or not source.get("source_evidence"):
            blockers.add("FIXATION_INTERNAL_SOURCE_UNVERIFIED")
        if (group == "eligibility" and source
                and (source.get("source_evidence") or {}).get("status") != "finalized"):
            blockers.add("FIXATION_INTERNAL_M07_NOT_FINALIZED")
    if prepared["state"] != "PREPARED":
        blockers.add("FIXATION_INTERNAL_PREPARATION_NOT_READY")
    if eligible["state"] != "ELIGIBLE_FOR_ADMISSION_REVIEW":
        blockers.add("FIXATION_INTERNAL_ELIGIBILITY_NOT_READY")
    if admitted["state"] != "ADMITTED_FOR_REVIEW":
        blockers.add("FIXATION_INTERNAL_ADMISSION_NOT_PASSED")
    return sorted(blockers)


def request_internal_approval(db, client_id: int, scenario_id: str,
                              request: FixationProfessionalApprovalRequest,
                              actor: str) -> dict:
    """Explicit, limited-scope professional decision in one SERIALIZABLE TX.

    Caller owns commit/rollback; never returns an approved result until
    successful commit. No tax, CBS, capital or net engine is invoked.
    """
    if not isinstance(actor, str) or not actor.strip() or actor == "local-development-only":
        raise DraftError("FIXATION_PROFESSIONAL_ACTOR_REQUIRED", 403)
    if db.get_bind().dialect.name != "postgresql" or db.in_transaction():
        raise DraftError("FIXATION_INTERNAL_FRESH_POSTGRES_TX_REQUIRED", 503)
    # SSI protects the read-set of ALL source queries against concurrent
    # modifications, not merely writes to the approval head.
    db.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))
    scenario = db.scalar(select(ScenarioDraft).where(
        ScenarioDraft.client_id == client_id,
        ScenarioDraft.scenario_id == scenario_id,
    ).with_for_update())
    if scenario is None:
        raise DraftError("SCENARIO_NOT_FOUND", 404)
    if scenario.status != "draft":
        raise DraftError("FIXATION_INTERNAL_SCENARIO_INACTIVE", 409)
    head = db.scalar(select(ScenarioFixationApprovalHead).where(
        ScenarioFixationApprovalHead.client_id == client_id,
        ScenarioFixationApprovalHead.scenario_id == scenario_id,
    ).with_for_update())
    if head is None:
        raise DraftError("FIXATION_INTERNAL_DRAFT_REQUIRED", 422)
    item = read(db, client_id, scenario_id)
    if (item["approval_version"] != request.expected_approval_version
            or item["approval_fingerprint"] != request.expected_approval_fingerprint
            or scenario.version != request.expected_scenario_version
            or item["current_readiness"]["manifest_fingerprint"] != request.expected_manifest_fingerprint
            or item["current_readiness"]["readiness_fingerprint"] != request.expected_readiness_fingerprint):
        raise DraftError("FIXATION_INTERNAL_SOURCE_CONFLICT", 409)
    if item["validity_state"] == "STALE":
        raise DraftError("FIXATION_INTERNAL_REVIEW_STALE", 409)

    # Lazy import avoids the existing preparation -> approval.read dependency.
    from app.services import scenario_fixation_admission_preparation_service as preparation
    from app.services import scenario_fixation_admission_eligibility_service as eligibility
    from app.services import scenario_fixation_admission_review_service as admission_review
    prepared = preparation.prepare(db, client_id, scenario_id)
    eligible = eligibility.assess(db, client_id, scenario_id)
    if (prepared["preparation_fingerprint"] != request.expected_preparation_fingerprint
            or eligible["eligibility_fingerprint"] != request.expected_eligibility_fingerprint
            or eligible["preparation_fingerprint"] != prepared["preparation_fingerprint"]):
        raise DraftError("FIXATION_INTERNAL_ADMISSION_SOURCE_CONFLICT", 409)
    admitted = admission_review.review(
        db, client_id, scenario_id,
        expected_preparation_fingerprint=prepared["preparation_fingerprint"],
        expected_eligibility_fingerprint=eligible["eligibility_fingerprint"],
    )
    if admitted["admission_review_fingerprint"] != request.expected_admission_review_fingerprint:
        raise DraftError("FIXATION_INTERNAL_ADMISSION_SOURCE_CONFLICT", 409)
    blockers = _internal_professional_blockers(item, prepared, eligible, admitted)
    # An arbitrary document:// string is not evidence. Bind the explicit
    # professional review reference to a VERIFIED M07 fact of this client and
    # the chosen finalized eligibility revision. No opaque browser reference
    # can create a positive professional decision.
    from app.models.m07_evidence import M07FactEvidence
    eligibility_sources = [
        d["source_id"] for d in item["decisions"]
        if d["group"] == "eligibility" and d["determination"] == "PLANNER_ASSERTED"
    ]
    verified_document = None
    if len(eligibility_sources) == 1:
        verified_document = db.scalar(select(M07FactEvidence.fact_evidence_id).where(
            M07FactEvidence.client_id == client_id,
            M07FactEvidence.m07_evidence_revision_id == eligibility_sources[0],
            M07FactEvidence.verification_state == "verified",
            M07FactEvidence.source_document_reference == request.review_reference,
        ).limit(1))
    if verified_document is None:
        blockers.append("FIXATION_INTERNAL_REVIEW_REFERENCE_NOT_VERIFIED")
    blockers = sorted(set(blockers))
    if blockers:
        return {
            "approval_attempt_state": "BLOCKED", "blockers": blockers,
            "professional_authority": False, "execution_allowed": False,
            "tax_authority_approval": None,
        }

    version = head.current_version + 1
    metadata = {
        "authority_scope": "FIXATION_INTERNAL_REVIEW_ONLY",
        "decision_reason": request.decision_reason,
        "review_reference": request.review_reference,
        "attestations": sorted(request.attestations),
        "preparation_fingerprint": prepared["preparation_fingerprint"],
        "eligibility_fingerprint": eligible["eligibility_fingerprint"],
        "admission_review_fingerprint": admitted["admission_review_fingerprint"],
    }
    source = db.scalar(select(ScenarioFixationApprovalRevision).where(
        ScenarioFixationApprovalRevision.approval_id == head.approval_id,
        ScenarioFixationApprovalRevision.approval_version == head.current_version,
    ))
    if source is None or source.status != "DRAFT":
        raise DraftError("FIXATION_INTERNAL_DRAFT_REQUIRED", 409)
    content = {**source.decisions_json, "internal_decision": metadata}
    fingerprint = _fingerprint({
        "contract": CONTRACT, "client_id": client_id, "scenario_id": scenario_id,
        "approval_version": version, "dependency_fingerprint": item["dependency_fingerprint"],
        "actor_id": actor, "status": "APPROVED_INTERNAL", "internal_decision": metadata,
    })
    updated = db.execute(update(ScenarioFixationApprovalHead).where(
        ScenarioFixationApprovalHead.approval_id == head.approval_id,
        ScenarioFixationApprovalHead.current_version == request.expected_approval_version,
    ).values(current_version=version, status="APPROVED_INTERNAL",
             updated_by=actor, updated_at=func.now()))
    if updated.rowcount != 1:
        raise DraftError("FIXATION_APPROVAL_VERSION_CONFLICT", 409)
    db.add(ScenarioFixationApprovalRevision(
        revision_id=uuid4().hex, approval_id=head.approval_id,
        client_id=client_id, scenario_id=scenario_id,
        approval_version=version, scenario_version=scenario.version,
        manifest_fingerprint=item["current_readiness"]["manifest_fingerprint"],
        readiness_fingerprint=item["current_readiness"]["readiness_fingerprint"],
        dependency_fingerprint=item["dependency_fingerprint"],
        approval_fingerprint=fingerprint, decisions_json=content, blockers_json=[],
        status="APPROVED_INTERNAL", action="APPROVE_INTERNAL",
        actor_id=actor, occurred_at=datetime.now(timezone.utc),
    ))
    db.flush()
    return {
        "approval_attempt_state": "APPROVED_INTERNAL",
        "decision_state": "APPROVED_INTERNAL", "validity_state": "CURRENT",
        "authority_scope": "FIXATION_INTERNAL_REVIEW_ONLY",
        "client_id": client_id, "scenario_id": scenario_id,
        "approval_id": head.approval_id, "approval_version": version,
        "decision_fingerprint": fingerprint,
        "internal_professional_authority": True,
        "professional_authority": False, "execution_allowed": False,
        "tax_authority_approval": None, "blockers": [],
    }
