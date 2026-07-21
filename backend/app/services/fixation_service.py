from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date
from decimal import Decimal
from time import time_ns
from uuid import uuid4

from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

from app.engines.fixation_engine import (
    calculate_fixation as calculate_fixation_engine,
)
from app.models.actual_capitalization import ActualCapitalization
from app.models.client import Client
from app.models.client_profile import ClientProfile
from app.models.employment_record import EmploymentRecord
from app.models.fixation_audit_row import FixationAuditRow
from app.models.fixation_input_snapshot import FixationInputSnapshot
from app.models.fixation_result import FixationResult as FixationResultModel
from app.models.fixation_run import FixationRun
from app.models.fixation_validation_error import FixationValidationError
from app.models.grant import Grant
from app.models.internal_planner_judgment import InternalPlannerJudgment
from app.schemas.fixation_contracts import (
    FixationInput,
    FixationResult,
    InternalPlannerJudgmentCreateRequest,
    PlannerReviewContextEnvelope,
    ValidationError,
)
from app.services.fixation_admission_service import (
    parse_and_admit_fixation_payload,
    validation_failed_result,
)


class InternalPlannerJudgmentRunNotFoundError(ValueError):
    pass


class InternalPlannerJudgmentAlreadyExistsError(ValueError):
    pass


def _new_id(prefix: str) -> str:
    return f"{prefix}-{time_ns()}-{uuid4().hex}"


def _as_float(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value)


def calculate_fixation_payload(
    input_payload: dict,
    *,
    client_id: int | None = None,
) -> FixationResult:
    _, engine_input, errors = parse_and_admit_fixation_payload(
        input_payload,
        client_id=client_id,
    )
    if errors:
        return validation_failed_result(input_payload, errors)
    assert engine_input is not None
    return calculate_fixation_engine(engine_input)


def _is_success_result(result: FixationResult | list[ValidationError]) -> bool:
    return isinstance(result, FixationResult)


def create_client_source_data(
    *,
    db_session: Session,
    client_data: Mapping,
    profile_data: Mapping | None,
    employment_records_data: Sequence[Mapping],
    grants_data: Sequence[Mapping],
    actual_capitalizations_data: Sequence[Mapping],
) -> int:
    client = Client(
        display_name=str(client_data["display_name"]),
        id_number=str(client_data["id_number"]),
        birth_date=client_data.get("birth_date"),
        status=client_data.get("status"),
    )
    if "client_id" in client_data and client_data["client_id"] is not None:
        client.client_id = int(client_data["client_id"])

    db_session.add(client)
    db_session.flush()
    client_id = int(client.client_id)

    if profile_data is not None:
        db_session.add(
            ClientProfile(
                client_profile_id=str(profile_data["client_profile_id"]),
                client_id=client_id,
                birth_date=profile_data.get("birth_date"),
                gender=profile_data.get("gender"),
                notes=profile_data.get("notes"),
            )
        )

    for record in employment_records_data:
        db_session.add(
            EmploymentRecord(
                employment_record_id=str(record["employment_record_id"]),
                client_id=client_id,
                employer_name=str(record["employer_name"]),
                work_start_date=record["work_start_date"],
                work_end_date=record.get("work_end_date"),
                is_current=bool(record["is_current"]),
                notes=record.get("notes"),
            )
        )

    for grant_data in grants_data:
        db_session.add(
            Grant(
                grant_id=str(grant_data["grant_id"]),
                client_id=client_id,
                employment_record_id=(
                    str(grant_data["employment_record_id"])
                    if grant_data.get("employment_record_id") is not None
                    else None
                ),
                employer_name=grant_data.get("employer_name"),
                nominal_amount=grant_data.get("nominal_amount"),
                indexed_amount=grant_data["indexed_amount"],
                grant_date=grant_data["grant_date"],
                work_start_date=grant_data["work_start_date"],
                work_end_date=grant_data["work_end_date"],
                notes=grant_data.get("notes"),
            )
        )

    for cap_data in actual_capitalizations_data:
        db_session.add(
            ActualCapitalization(
                capitalization_id=str(cap_data["capitalization_id"]),
                client_id=client_id,
                amount=cap_data["amount"],
                capitalization_date=cap_data["capitalization_date"],
                source_label=cap_data.get("source_label"),
                notes=cap_data.get("notes"),
            )
        )

    db_session.commit()
    return client_id


def assemble_fixation_input(
    client_id: int | str,
    db_session: Session,
    explicit_parameters: Mapping,
) -> FixationInput:
    client_key = int(client_id)

    grants = db_session.scalars(
        select(Grant).where(Grant.client_id == client_key).order_by(Grant.grant_id)
    ).all()
    capitalizations = db_session.scalars(
        select(ActualCapitalization)
        .where(ActualCapitalization.client_id == client_key)
        .order_by(ActualCapitalization.capitalization_id)
    ).all()

    payload = {
        "calculation_id": explicit_parameters.get("calculation_id"),
        "calculation_version": explicit_parameters["calculation_version"],
        "eligibility_date": explicit_parameters["eligibility_date"],
        "eligibility_year": explicit_parameters["eligibility_year"],
        "monthly_cap": explicit_parameters["monthly_cap"],
        "exemption_percentage": explicit_parameters["exemption_percentage"],
        "capital_multiplier": explicit_parameters["capital_multiplier"],
        "grant_impact_multiplier": explicit_parameters["grant_impact_multiplier"],
        "grants": [
            {
                "grant_id": grant.grant_id,
                "employer_name": grant.employer_name,
                "nominal_amount": _as_float(grant.nominal_amount),
                "indexed_amount": float(grant.indexed_amount),
                "grant_date": grant.grant_date,
                "work_start_date": grant.work_start_date,
                "work_end_date": grant.work_end_date,
            }
            for grant in grants
        ],
        "future_grant_reserved": explicit_parameters["future_grant_reserved"],
        "actual_capitalizations": [
            {
                "capitalization_id": cap.capitalization_id,
                "amount": float(cap.amount),
                "capitalization_date": cap.capitalization_date,
                "source_label": cap.source_label,
                "notes": cap.notes,
            }
            for cap in capitalizations
        ],
        "idf": explicit_parameters["idf"],
        "metadata": explicit_parameters.get("metadata"),
    }

    return FixationInput(**payload)


def run_fixation(
    client_id: int | str,
    input_data: dict | FixationInput,
    db_session: Session,
    planner_review_context: PlannerReviewContextEnvelope | None = None,
) -> int:
    client_key = int(client_id)

    run_trace_id = _new_id("run")
    snapshot_id = _new_id("snapshot")

    try:
        input_contract_version: str | None = None

        raw_payload = (
            input_data.model_dump(mode="json")
            if isinstance(input_data, FixationInput)
            else dict(input_data)
        )
        if "calculation_version" in raw_payload:
            input_contract_version = str(raw_payload["calculation_version"])
        admitted_context, engine_input, admission_errors = parse_and_admit_fixation_payload(
            raw_payload,
            client_id=client_key,
        )
        snapshot_payload = (
            admitted_context.model_dump(mode="json")
            if admitted_context is not None
            else raw_payload
        )
        if admission_errors:
            result = admission_errors
        else:
            assert engine_input is not None
            result = calculate_fixation_engine(engine_input)

        run_calculation_version = (
            result.calculation_version
            if _is_success_result(result) and result.calculation_version is not None
            else input_contract_version
        )

        for previous_latest_run in db_session.scalars(
            select(FixationRun).where(FixationRun.client_id == client_key, FixationRun.is_latest.is_(True))
        ).all():
            previous_latest_run.is_latest = False

        run = FixationRun(
            fixation_run_id=run_trace_id,
            client_id=client_key,
            calculation_version=run_calculation_version,
            status="success" if _is_success_result(result) else "validation_failed",
            source_data_version_label=((snapshot_payload.get("metadata", {}) or {})).get(
                "source_data_version_label"
            ),
            is_latest=True,
        )
        db_session.add(run)
        db_session.flush()
        run_id = int(run.id)

        db_session.add(
            FixationInputSnapshot(
                fixation_input_snapshot_id=snapshot_id,
                fixation_run_id=run_id,
                input_contract_version=run_calculation_version,
                input_payload=snapshot_payload,
                planner_review_context=(
                    planner_review_context.model_dump(mode="json")
                    if planner_review_context is not None
                    else None
                ),
            )
        )

        if _is_success_result(result):
            db_session.add(
                FixationResultModel(
                    fixation_result_id=_new_id("result"),
                    fixation_run_id=run_id,
                    result_contract_version=run_calculation_version,
                    initial_exempt_capital=Decimal(str(result.initial_exempt_capital)),
                    grant_impact_total=Decimal(str(result.grant_impact_total)),
                    future_grant_reserved=Decimal(str(result.future_grant_reserved)),
                    future_grant_impact=Decimal(str(result.future_grant_impact)),
                    actual_capitalization_impact=Decimal(str(result.actual_capitalization_impact)),
                    idf_impact=Decimal(str(result.idf_impact)),
                    total_impact=Decimal(str(result.total_impact)),
                    remaining_exempt_capital=Decimal(str(result.remaining_exempt_capital)),
                    monthly_exempt_pension=Decimal(str(result.monthly_exempt_pension)),
                    capital_exemption_percentage=Decimal(str(result.capital_exemption_percentage)),
                    pension_exemption_percentage=Decimal(str(result.pension_exemption_percentage)),
                    result_payload=result.model_dump(mode="json"),
                )
            )

            for idx, row in enumerate(result.audit_rows or [], start=1):
                db_session.add(
                    FixationAuditRow(
                        fixation_audit_row_id=_new_id("audit"),
                        fixation_run_id=run_id,
                        row_order=idx,
                        category=row.category,
                        source_id=row.source_id,
                        label=row.label,
                        input_amount=(
                            Decimal(str(row.input_amount))
                            if row.input_amount is not None
                            else None
                        ),
                        output_amount=Decimal(str(row.output_amount)),
                        impact_amount=Decimal(str(row.impact_amount)),
                        details_payload=row.details,
                    )
                )

        if not _is_success_result(result):
            for idx, err in enumerate(result, start=1):
                db_session.add(
                    FixationValidationError(
                        fixation_validation_error_id=_new_id("valerr"),
                        fixation_run_id=run_id,
                        error_order=idx,
                        code=err.code,
                        path=err.path,
                        message=err.message,
                        severity=err.severity,
                        source_id=err.source_id,
                    )
                )

        db_session.commit()
    except Exception:
        db_session.rollback()
        raise

    return int(run_id)


def get_latest_fixation_result(client_id: int | str, db_session: Session) -> FixationRun | None:
    client_key = int(client_id)
    stmt = (
        select(FixationRun)
        .where(FixationRun.client_id == client_key, FixationRun.status == "success")
        .options(selectinload(FixationRun.fixation_result), selectinload(FixationRun.fixation_input_snapshot))
        .order_by(desc(FixationRun.created_at), desc(FixationRun.id))
    )
    return db_session.scalars(stmt).first()


def get_fixation_history(client_id: int | str, db_session: Session) -> list[FixationRun]:
    client_key = int(client_id)
    stmt = (
        select(FixationRun)
        .where(FixationRun.client_id == client_key)
        .order_by(desc(FixationRun.created_at), desc(FixationRun.id))
    )
    return list(db_session.scalars(stmt).all())


def get_fixation_run_detail(
    client_id: int | str,
    run_id: int | str,
    db_session: Session,
) -> FixationRun | None:
    client_key = int(client_id)
    run_key = int(run_id)
    stmt = (
        select(FixationRun)
        .where(FixationRun.id == run_key, FixationRun.client_id == client_key)
        .options(
            selectinload(FixationRun.fixation_input_snapshot),
            selectinload(FixationRun.fixation_result),
            selectinload(FixationRun.fixation_audit_rows),
            selectinload(FixationRun.fixation_validation_errors),
            selectinload(FixationRun.internal_planner_judgment),
        )
    )
    return db_session.scalars(stmt).first()


def create_internal_planner_judgment(
    client_id: int | str,
    run_id: int | str,
    judgment_data: InternalPlannerJudgmentCreateRequest,
    db_session: Session,
) -> InternalPlannerJudgment:
    client_key = int(client_id)
    run_key = int(run_id)
    run = db_session.scalar(
        select(FixationRun).where(
            FixationRun.id == run_key,
            FixationRun.client_id == client_key,
        )
    )
    if run is None:
        raise InternalPlannerJudgmentRunNotFoundError(f"Fixation run {run_key} was not found")

    existing_judgment = db_session.scalar(
        select(InternalPlannerJudgment).where(InternalPlannerJudgment.fixation_run_id == run_key)
    )
    if existing_judgment is not None:
        raise InternalPlannerJudgmentAlreadyExistsError(
            f"Fixation run {run_key} already has an internal planner judgment"
        )

    judgment = InternalPlannerJudgment(
        internal_planner_judgment_id=_new_id("judgment"),
        fixation_run_id=run_key,
        handling_status=judgment_data.handling_status,
        next_internal_action=judgment_data.next_internal_action,
        internal_note=judgment_data.internal_note,
    )

    try:
        db_session.add(judgment)
        db_session.commit()
        db_session.refresh(judgment)
    except Exception:
        db_session.rollback()
        raise

    return judgment
