from __future__ import annotations

from decimal import Decimal
from datetime import timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.models.m09_cashflow import M09ResolvedComponentInventory, M09_WORKFLOW_ACTOR, authorize_m09_insert, m09_server_timestamp, new_m09_id
from app.models.m09_scenario_subject import M09ScenarioAdjustment, M09ScenarioSubject, M09SubjectMonthlyResult, M09SubjectRun, SUBJECT_FAMILY, SUBJECT_VERSION, authorize_subject_insert
from app.schemas.m09_cashflow import M09ContractRequest, M09RangeTotalsResponse
from app.schemas.m09_scenario_subject import AdjustmentResponse, CreateAdjustedSubjectRequest, ScenarioSubjectResponse, SubjectCurrentnessResponse, SubjectExecutionRequest, SubjectM10EligibilityResponse, SubjectMonthlyResultResponse, SubjectRunResponse, SubjectRunSummaryResponse
from app.services.m01_case_service import ensure_m01_editable
from app.services.m09_cashflow_service import DOMAIN_CONTRACT_VERSION, ENGINE_VERSION, FINGERPRINT_VERSION, M09CashflowError, M09NumericDomainError, RESULT_SCHEMA_VERSION, _build_inventory, _digest, _error, _included_components, _json_value, _month_range, _require_client, _typed_warnings, _validate_aggregate


SUBJECT_ENGINE_VERSION = "m09-subject-aggregation-v1"
SUBJECT_RESULT_SCHEMA_VERSION = "m09-subject-result-v1"
BASELINE_MARKER = "server_resolved_no_scenario_adjustments"
ADJUSTMENT_PROVENANCE = "planner_declared_scenario_adjustment"


def _semantic_adjustments(inputs) -> list[dict[str, str]]:
    values = [{"adjustment_type": item.adjustment_type, "amount": item.amount, "start_month": item.start_month, "end_month": item.end_month} for item in inputs]
    return sorted(values, key=lambda item: (item["adjustment_type"], item["amount"], item["start_month"], item["end_month"]))


def _manifest(semantic: list[dict[str, str]], *, baseline: bool) -> tuple[dict[str, Any], str, str]:
    payload = {
        "manifest_schema_version": "m09-scenario-adjustment-manifest-v1",
        "scenario_family": SUBJECT_FAMILY,
        "scenario_contract_version": SUBJECT_VERSION,
        "adjustments": semantic,
        "multiplicity_preserved": True,
        "baseline_evidence": BASELINE_MARKER if baseline else None,
    }
    fingerprint = _digest(payload)
    semantic_fingerprint = _digest({"scenario_family": SUBJECT_FAMILY, "scenario_contract_version": SUBJECT_VERSION, "adjustments": semantic})
    payload["manifest_fingerprint"] = fingerprint
    return payload, fingerprint, semantic_fingerprint


def _subject_integrity_payload(row: M09ScenarioSubject) -> dict[str, Any]:
    created_at = row.created_at
    if created_at.tzinfo is not None:
        created_at = created_at.astimezone(timezone.utc).replace(tzinfo=None)
    return {
        "scenario_subject_id": row.scenario_subject_id,
        "client_id": row.client_id,
        "scenario_family": row.scenario_family,
        "scenario_contract_version": row.scenario_contract_version,
        "subject_type": row.subject_type,
        "display_label": row.display_label,
        "adjustment_manifest_fingerprint": row.adjustment_manifest_fingerprint,
        "calculation_semantic_fingerprint": row.calculation_semantic_fingerprint,
        "provenance": row.provenance,
        "actor": row.actor,
        "created_at": created_at.isoformat(timespec="microseconds"),
    }


def _subject_rows(db: Session, subject: M09ScenarioSubject) -> list[M09ScenarioAdjustment]:
    return list(db.scalars(select(M09ScenarioAdjustment).where(M09ScenarioAdjustment.client_id == subject.client_id, M09ScenarioAdjustment.scenario_subject_id == subject.scenario_subject_id).order_by(M09ScenarioAdjustment.ordinal)))


def _subject_response(db: Session, row: M09ScenarioSubject) -> ScenarioSubjectResponse:
    adjustments = _subject_rows(db, row)
    return ScenarioSubjectResponse(
        scenario_subject_id=row.scenario_subject_id, client_id=row.client_id, scenario_family=row.scenario_family,
        scenario_contract_version=row.scenario_contract_version, subject_type=row.subject_type, display_label=row.display_label,
        adjustment_manifest=row.adjustment_manifest, adjustment_manifest_fingerprint=row.adjustment_manifest_fingerprint,
        calculation_semantic_fingerprint=row.calculation_semantic_fingerprint, integrity_fingerprint=row.integrity_fingerprint,
        provenance=row.provenance, actor=row.actor, created_at=row.created_at,
        adjustments=[AdjustmentResponse(adjustment_id=a.adjustment_id, ordinal=a.ordinal, adjustment_type=a.adjustment_type, amount=a.amount_text, start_month=a.start_month, end_month=a.end_month, provenance=a.provenance, semantic_fingerprint=a.semantic_fingerprint, actor=a.actor, created_at=a.created_at) for a in adjustments],
    )


def _require_subject(db: Session, client_id: int, subject_id: str) -> M09ScenarioSubject:
    row = db.scalar(select(M09ScenarioSubject).where(M09ScenarioSubject.client_id == client_id, M09ScenarioSubject.scenario_subject_id == subject_id))
    if row is None:
        raise _error("m09_subject_resource_not_found", "scenario subject is unavailable", 404)
    return row


def resolve_baseline(db: Session, client_id: int) -> ScenarioSubjectResponse:
    client = _require_client(db, client_id)
    ensure_m01_editable(client)
    _, _, semantic_fp = _manifest([], baseline=True)
    existing = db.scalar(select(M09ScenarioSubject).where(M09ScenarioSubject.client_id == client_id, M09ScenarioSubject.scenario_family == SUBJECT_FAMILY, M09ScenarioSubject.scenario_contract_version == SUBJECT_VERSION, M09ScenarioSubject.calculation_semantic_fingerprint == semantic_fp))
    if existing:
        return _subject_response(db, existing)
    now = m09_server_timestamp(); subject_id = new_m09_id("M09-S")
    manifest, manifest_fp, semantic_fp = _manifest([], baseline=True)
    row = M09ScenarioSubject(scenario_subject_id=subject_id, client_id=client_id, scenario_family=SUBJECT_FAMILY, scenario_contract_version=SUBJECT_VERSION, subject_type="baseline", display_label="Baseline", adjustment_manifest=manifest, adjustment_manifest_fingerprint=manifest_fp, calculation_semantic_fingerprint=semantic_fp, integrity_fingerprint="0" * 64, provenance=BASELINE_MARKER, actor=M09_WORKFLOW_ACTOR, created_at=now)
    row.integrity_fingerprint = _digest(_subject_integrity_payload(row)); authorize_subject_insert(row)
    try:
        db.add(row); db.commit(); db.refresh(row)
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(M09ScenarioSubject).where(M09ScenarioSubject.client_id == client_id, M09ScenarioSubject.calculation_semantic_fingerprint == semantic_fp))
        if existing: return _subject_response(db, existing)
        raise
    return _subject_response(db, row)


def create_adjusted_subject(db: Session, client_id: int, request: CreateAdjustedSubjectRequest) -> ScenarioSubjectResponse:
    client = _require_client(db, client_id); ensure_m01_editable(client)
    semantic = _semantic_adjustments(request.adjustments)
    manifest, manifest_fp, semantic_fp = _manifest(semantic, baseline=False)
    if db.scalar(select(M09ScenarioSubject.scenario_subject_id).where(M09ScenarioSubject.client_id == client_id, M09ScenarioSubject.scenario_family == SUBJECT_FAMILY, M09ScenarioSubject.scenario_contract_version == SUBJECT_VERSION, M09ScenarioSubject.calculation_semantic_fingerprint == semantic_fp)):
        raise _error("scenario_subject_semantically_duplicate", "scenario subject semantics already exist")
    now = m09_server_timestamp(); subject_id = new_m09_id("M09-S")
    row = M09ScenarioSubject(scenario_subject_id=subject_id, client_id=client_id, scenario_family=SUBJECT_FAMILY, scenario_contract_version=SUBJECT_VERSION, subject_type="adjusted", display_label=request.display_label, adjustment_manifest=manifest, adjustment_manifest_fingerprint=manifest_fp, calculation_semantic_fingerprint=semantic_fp, integrity_fingerprint="0" * 64, provenance=ADJUSTMENT_PROVENANCE, actor=M09_WORKFLOW_ACTOR, created_at=now)
    row.integrity_fingerprint = _digest(_subject_integrity_payload(row)); authorize_subject_insert(row)
    adjustment_rows = []
    for ordinal, item in enumerate(request.adjustments, 1):
        adjustment_id = new_m09_id("M09-A")
        evidence = {"adjustment_type": item.adjustment_type, "amount": item.amount, "start_month": item.start_month, "end_month": item.end_month}
        adjustment = M09ScenarioAdjustment(adjustment_id=adjustment_id, scenario_subject_id=subject_id, client_id=client_id, ordinal=ordinal, adjustment_type=item.adjustment_type, amount=Decimal(item.amount), amount_text=item.amount, start_month=item.start_month, end_month=item.end_month, provenance=ADJUSTMENT_PROVENANCE, semantic_fingerprint=_digest(evidence), actor=M09_WORKFLOW_ACTOR, created_at=now)
        authorize_subject_insert(adjustment); adjustment_rows.append(adjustment)
    try:
        db.add(row); db.add_all(adjustment_rows); db.commit(); db.refresh(row)
    except IntegrityError as exc:
        db.rollback(); raise _error("scenario_subject_semantically_duplicate", "scenario subject semantics already exist") from exc
    return _subject_response(db, row)


def list_subjects(db: Session, client_id: int) -> list[ScenarioSubjectResponse]:
    _require_client(db, client_id)
    rows = list(db.scalars(select(M09ScenarioSubject).where(M09ScenarioSubject.client_id == client_id).order_by(M09ScenarioSubject.created_at)))
    return [_subject_response(db, row) for row in rows]


def get_subject(db: Session, client_id: int, subject_id: str) -> ScenarioSubjectResponse:
    return _subject_response(db, _require_subject(db, client_id, subject_id))


def _legacy_inventory(db: Session, client_id: int, request: SubjectExecutionRequest) -> M09ResolvedComponentInventory:
    return _build_inventory(db, client_id, M09ContractRequest(scenario_family="deterministic_monthly_cashflow", scenario_contract_version="v1", start_month=request.start_month, end_month=request.end_month))


def _factual_material(inventory: M09ResolvedComponentInventory) -> str:
    payload = inventory.inventory_payload
    return _digest({
        "factual_material_schema_version": "m09-factual-baseline-material-v1",
        "component_domain_contract_version": inventory.component_domain_contract_version,
        "factual_inventory_material_fingerprint": payload.get("material_fingerprint"),
        "start_month": inventory.start_month,
        "end_month": inventory.end_month,
        "factual_engine_version": ENGINE_VERSION,
        "factual_result_schema_version": RESULT_SCHEMA_VERSION,
    })


def _current_subject_run(db: Session, subject: M09ScenarioSubject) -> M09SubjectRun | None:
    return db.scalar(select(M09SubjectRun).where(M09SubjectRun.client_id == subject.client_id, M09SubjectRun.scenario_subject_id == subject.scenario_subject_id).order_by(M09SubjectRun.run_sequence.desc()).limit(1))


def _adjustment_components(subject: M09ScenarioSubject, adjustments: list[M09ScenarioAdjustment], months: list[str]) -> list[dict[str, Any]]:
    components = []
    for adjustment in adjustments:
        if adjustment.start_month < months[0] or adjustment.end_month > months[-1]:
            raise _error("adjustment_outside_run_horizon", "adjustment range must be contained in run horizon", 422)
        for month in months:
            if adjustment.start_month <= month <= adjustment.end_month:
                components.append({"component_id": f"{adjustment.adjustment_id}:{month}", "component_type": adjustment.adjustment_type, "direction": "inflow" if adjustment.adjustment_type.endswith("income") else "outflow", "amount": adjustment.amount_text, "month": month, "source_identity": adjustment.adjustment_id, "source_fingerprint": adjustment.semantic_fingerprint, "authority": ADJUSTMENT_PROVENANCE, "applicability": "applicable_full_month"})
    return components


def _monthly_rows(run_id: str, subject: M09ScenarioSubject, months: list[str], components: list[dict[str, Any]]):
    by_month = {month: [] for month in months}; seen = set()
    for component in components:
        if component["component_id"] in seen: raise _error("duplicate_adjustment_identity", "duplicate component identity")
        seen.add(component["component_id"]); by_month[component["month"]].append(component)
    rows=[]; semantic=[]; range_in=Decimal("0.00"); range_out=Decimal("0.00")
    for month in months:
        evidence=sorted(by_month[month], key=lambda x:(x["component_type"],x["source_identity"],x["component_id"]))
        inflow=_validate_aggregate(sum((Decimal(x["amount"]) for x in evidence if x["direction"]=="inflow"), Decimal("0.00")))
        outflow=_validate_aggregate(sum((Decimal(x["amount"]) for x in evidence if x["direction"]=="outflow"), Decimal("0.00")))
        net=_validate_aggregate(inflow-outflow); payload={"month":month,"component_evidence":evidence,"gross_inflow_total":format(inflow,".2f"),"gross_outflow_total":format(outflow,".2f"),"period_net":format(net,".2f")}; fp=_digest(payload)
        semantic_evidence=[]
        occurrences: dict[tuple[str, str, str], int] = {}
        for item in evidence:
            if item.get("authority") == ADJUSTMENT_PROVENANCE:
                key=(item["component_type"],item["amount"],item["source_fingerprint"]); occurrences[key]=occurrences.get(key,0)+1
                semantic_evidence.append({"component_type":item["component_type"],"direction":item["direction"],"amount":item["amount"],"month":item["month"],"source_fingerprint":item["source_fingerprint"],"occurrence":occurrences[key],"authority":item["authority"],"applicability":item["applicability"]})
            else:
                semantic_evidence.append(item)
        semantic_evidence=sorted(semantic_evidence,key=lambda item:(str(item.get("component_type")),str(item.get("amount")),str(item.get("source_fingerprint")),int(item.get("occurrence",0)),str(item.get("component_id",""))))
        row=M09SubjectMonthlyResult(monthly_result_id="M09-SM-"+_digest({"run":run_id,"month":month})[:45],run_id=run_id,scenario_subject_id=subject.scenario_subject_id,client_id=subject.client_id,month=month,gross_inflow_total=inflow,gross_outflow_total=outflow,period_net=net,component_evidence=evidence,result_fingerprint=fp); authorize_subject_insert(row); rows.append(row); semantic.append({"month":month,"component_evidence":semantic_evidence,"gross_inflow_total":format(inflow,".2f"),"gross_outflow_total":format(outflow,".2f"),"period_net":format(net,".2f")}); range_in=_validate_aggregate(range_in+inflow); range_out=_validate_aggregate(range_out+outflow)
    totals={"gross_inflow_total":format(range_in,".2f"),"gross_outflow_total":format(range_out,".2f"),"period_net":format(_validate_aggregate(range_in-range_out),".2f")}
    semantic_fp=_digest({"result_schema_version":SUBJECT_RESULT_SCHEMA_VERSION,"scenario_family":SUBJECT_FAMILY,"scenario_contract_version":SUBJECT_VERSION,"months":semantic,"range_totals":totals})
    return rows,totals,semantic_fp


def execute_subject_run(db: Session, client_id: int, subject_id: str, request: SubjectExecutionRequest) -> SubjectRunResponse:
    client=_require_client(db,client_id); ensure_m01_editable(client); subject=_require_subject(db,client_id,subject_id)
    adjustments=_subject_rows(db,subject); months=_month_range(request.start_month,request.end_month); inventory=_legacy_inventory(db,client_id,request); factual_fp=_factual_material(inventory); current=_current_subject_run(db,subject); run_id=new_m09_id("M09-SR"); sequence=1 if current is None else current.run_sequence+1
    blockers=list(inventory.blocker_codes); status="success_complete" if inventory.complete else "dependency_failed"; rows=[]; totals=None; semantic_fp=None; integrity_fp=None
    snapshot={"snapshot_schema_version":"m09-subject-upstream-snapshot-v1","scenario_subject_id":subject_id,"scenario_family":SUBJECT_FAMILY,"scenario_contract_version":SUBJECT_VERSION,"start_month":request.start_month,"end_month":request.end_month,"component_domain_contract_version":DOMAIN_CONTRACT_VERSION,"factual_inventory":inventory.inventory_payload,"factual_inventory_fingerprint":inventory.inventory_fingerprint,"factual_baseline_material_fingerprint":factual_fp,"adjustment_manifest_fingerprint":subject.adjustment_manifest_fingerprint,"engine_version":SUBJECT_ENGINE_VERSION,"result_schema_version":SUBJECT_RESULT_SCHEMA_VERSION}
    snapshot_fp=_digest(snapshot); snapshot["snapshot_fingerprint"]=snapshot_fp
    if status=="success_complete":
        try:
            components=_included_components(inventory)+_adjustment_components(subject,adjustments,months); rows,totals,semantic_fp=_monthly_rows(run_id,subject,months,components); integrity_fp=_digest({"semantic_result_fingerprint":semantic_fp,"upstream_snapshot_fingerprint":snapshot_fp,"factual_baseline_material_fingerprint":factual_fp,"monthly_result_fingerprints":[r.result_fingerprint for r in rows],"range_totals":totals})
        except M09NumericDomainError as exc:
            status="calculation_failed"; blockers.append(exc.code); rows=[]; totals=semantic_fp=integrity_fp=None
    run=M09SubjectRun(run_id=run_id,scenario_subject_id=subject_id,client_id=client_id,predecessor_run_id=current.run_id if current else None,run_sequence=sequence,scenario_family=SUBJECT_FAMILY,scenario_contract_version=SUBJECT_VERSION,start_month=request.start_month,end_month=request.end_month,component_domain_contract_version=DOMAIN_CONTRACT_VERSION,factual_inventory=inventory.inventory_payload,factual_inventory_fingerprint=inventory.inventory_fingerprint,factual_baseline_material_fingerprint=factual_fp,adjustment_manifest=subject.adjustment_manifest,adjustment_manifest_fingerprint=subject.adjustment_manifest_fingerprint,upstream_snapshot=snapshot,upstream_snapshot_fingerprint=snapshot_fp,status=status,warnings=_typed_warnings(inventory)+([{"code":ADJUSTMENT_PROVENANCE,"classification":"informational_warning"}] if adjustments else []),blocker_codes=sorted(set(blockers)),range_totals=totals,semantic_result_fingerprint=semantic_fp,result_integrity_fingerprint=integrity_fp,actor=M09_WORKFLOW_ACTOR,created_at=m09_server_timestamp()); authorize_subject_insert(run)
    try:
        db.add(inventory); db.add(run); db.add_all(rows); db.commit(); db.refresh(run)
    except (IntegrityError,OperationalError) as exc:
        db.rollback(); raise _error("m09_subject_run_conflict","another run won this subject chain") from exc
    return subject_run_response(db,client_id,subject_id,run_id)


def _require_run(db: Session, client_id: int, subject_id: str, run_id: str) -> M09SubjectRun:
    row=db.scalar(select(M09SubjectRun).where(M09SubjectRun.client_id==client_id,M09SubjectRun.scenario_subject_id==subject_id,M09SubjectRun.run_id==run_id))
    if row is None: raise _error("m09_subject_resource_not_found","subject run is unavailable",404)
    return row


def _stored_months(db: Session,run:M09SubjectRun): return list(db.scalars(select(M09SubjectMonthlyResult).where(M09SubjectMonthlyResult.client_id==run.client_id,M09SubjectMonthlyResult.scenario_subject_id==run.scenario_subject_id,M09SubjectMonthlyResult.run_id==run.run_id).order_by(M09SubjectMonthlyResult.month)))


def subject_currentness(db: Session,client_id:int,subject_id:str,run_id:str)->SubjectCurrentnessResponse:
    subject=_require_subject(db,client_id,subject_id); run=_require_run(db,client_id,subject_id,run_id); current=_current_subject_run(db,subject); reasons=[]
    if current is None or current.run_id!=run.run_id: reasons.append("run_not_current_within_subject")
    if subject.scenario_family!=SUBJECT_FAMILY or subject.scenario_contract_version!=SUBJECT_VERSION: reasons.append("scenario_contract_unsupported")
    if _digest({k:v for k,v in subject.adjustment_manifest.items() if k!="manifest_fingerprint"})!=subject.adjustment_manifest_fingerprint: reasons.append("adjustment_manifest_integrity_invalid")
    if _digest(_subject_integrity_payload(subject))!=subject.integrity_fingerprint: reasons.append("subject_integrity_invalid")
    snapshot_without={k:v for k,v in run.upstream_snapshot.items() if k!="snapshot_fingerprint"}
    if _digest(snapshot_without)!=run.upstream_snapshot_fingerprint or run.upstream_snapshot.get("snapshot_fingerprint")!=run.upstream_snapshot_fingerprint: reasons.append("upstream_snapshot_integrity_invalid")
    rows=_stored_months(db,run)
    if run.status=="success_complete":
        if [row.month for row in rows] != _month_range(run.start_month,run.end_month): reasons.append("monthly_result_set_invalid")
        for row in rows:
            payload={"month":row.month,"component_evidence":row.component_evidence,"gross_inflow_total":format(row.gross_inflow_total,".2f"),"gross_outflow_total":format(row.gross_outflow_total,".2f"),"period_net":format(row.period_net,".2f")}
            if _digest(payload)!=row.result_fingerprint: reasons.append("monthly_result_integrity_invalid"); break
        expected_integrity=_digest({"semantic_result_fingerprint":run.semantic_result_fingerprint,"upstream_snapshot_fingerprint":run.upstream_snapshot_fingerprint,"factual_baseline_material_fingerprint":run.factual_baseline_material_fingerprint,"monthly_result_fingerprints":[row.result_fingerprint for row in rows],"range_totals":run.range_totals})
        if expected_integrity!=run.result_integrity_fingerprint: reasons.append("result_integrity_invalid")
    elif rows: reasons.append("failed_run_has_monthly_results")
    try:
        reassessed=_legacy_inventory(db,client_id,SubjectExecutionRequest(start_month=run.start_month,end_month=run.end_month))
        if _factual_material(reassessed)!=run.factual_baseline_material_fingerprint: reasons.append("factual_baseline_material_changed")
        if not reassessed.complete: reasons.append("dependency_no_longer_eligible")
    except Exception: reasons.append("dependency_reassessment_failed")
    return SubjectCurrentnessResponse(run_id=run.run_id,current_run_id=current.run_id if current else run.run_id,scenario_subject_id=subject_id,is_current=not reasons,reason_codes=list(dict.fromkeys(reasons)),assessment_timestamp=m09_server_timestamp())


def subject_eligibility(db:Session,client_id:int,subject_id:str,run_id:str)->SubjectM10EligibilityResponse:
    run=_require_run(db,client_id,subject_id,run_id); current=subject_currentness(db,client_id,subject_id,run_id); reasons=list(current.reason_codes)
    if run.status!="success_complete": reasons.append("run_not_success_complete")
    if run.blocker_codes: reasons.append("run_has_blockers")
    if any(warning.get("classification")=="mandatory_review_warning" for warning in run.warnings): reasons.append("mandatory_review_required")
    if len(run.factual_baseline_material_fingerprint)!=64: reasons.append("factual_baseline_material_fingerprint_invalid")
    return SubjectM10EligibilityResponse(assessed_scenario_run_id=run_id,current_scenario_run_id=current.current_run_id,scenario_subject_id=subject_id,eligible_for_m10=not reasons,reason_codes=list(dict.fromkeys(reasons)),informational_warnings=[w["code"] for w in run.warnings if w.get("classification")=="informational_warning"],factual_baseline_material_fingerprint=run.factual_baseline_material_fingerprint,assessment_timestamp=m09_server_timestamp())


def subject_run_response(db:Session,client_id:int,subject_id:str,run_id:str)->SubjectRunResponse:
    run=_require_run(db,client_id,subject_id,run_id); rows=_stored_months(db,run)
    return SubjectRunResponse(run_id=run.run_id,scenario_subject_id=subject_id,client_id=client_id,predecessor_run_id=run.predecessor_run_id,run_sequence=run.run_sequence,scenario_family=run.scenario_family,scenario_contract_version=run.scenario_contract_version,start_month=run.start_month,end_month=run.end_month,status=run.status,factual_inventory=run.factual_inventory,factual_inventory_fingerprint=run.factual_inventory_fingerprint,factual_baseline_material_fingerprint=run.factual_baseline_material_fingerprint,adjustment_manifest=run.adjustment_manifest,adjustment_manifest_fingerprint=run.adjustment_manifest_fingerprint,upstream_snapshot=run.upstream_snapshot,upstream_snapshot_fingerprint=run.upstream_snapshot_fingerprint,warnings=run.warnings,blocker_codes=run.blocker_codes,monthly_results=[SubjectMonthlyResultResponse(monthly_result_id=r.monthly_result_id,month=r.month,gross_inflow_total=format(r.gross_inflow_total,".2f"),gross_outflow_total=format(r.gross_outflow_total,".2f"),period_net=format(r.period_net,".2f"),component_evidence=r.component_evidence,result_fingerprint=r.result_fingerprint) for r in rows],range_totals=M09RangeTotalsResponse(**run.range_totals) if run.range_totals else None,semantic_result_fingerprint=run.semantic_result_fingerprint,result_integrity_fingerprint=run.result_integrity_fingerprint,currentness=subject_currentness(db,client_id,subject_id,run_id),m10_eligibility=subject_eligibility(db,client_id,subject_id,run_id),actor=run.actor,created_at=run.created_at)


def list_subject_runs(db:Session,client_id:int,subject_id:str)->list[SubjectRunSummaryResponse]:
    subject=_require_subject(db,client_id,subject_id); rows=list(db.scalars(select(M09SubjectRun).where(M09SubjectRun.client_id==client_id,M09SubjectRun.scenario_subject_id==subject_id).order_by(M09SubjectRun.run_sequence.desc())))
    return [SubjectRunSummaryResponse(run_id=r.run_id,scenario_subject_id=subject_id,run_sequence=r.run_sequence,status=r.status,start_month=r.start_month,end_month=r.end_month,factual_baseline_material_fingerprint=r.factual_baseline_material_fingerprint,is_current=subject_currentness(db,client_id,subject_id,r.run_id).is_current,eligible_for_m10=subject_eligibility(db,client_id,subject_id,r.run_id).eligible_for_m10,created_at=r.created_at) for r in rows]
