from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.client import Client
from app.models.client_profile import ClientProfile


EMPLOYMENT_STATUSES = (
    "salaried_employee",
    "self_employed",
    "salaried_and_self_employed",
    "not_currently_working",
    "unknown",
)
COMPLETE_EMPLOYMENT_STATUSES = frozenset(EMPLOYMENT_STATUSES[:-1])
LIFECYCLE_STATUSES = (
    "draft",
    "intake",
    "analysis",
    "review",
    "delivered",
    "archived",
)
FORWARD_TRANSITIONS = {
    "draft": "intake",
    "intake": "analysis",
    "analysis": "review",
    "review": "delivered",
    "delivered": "archived",
}
BACKWARD_TRANSITIONS = {
    "intake": "draft",
    "analysis": "intake",
    "review": "analysis",
    "delivered": "review",
    "archived": "delivered",
}
MISSING_FIELD_ORDER = (
    "display_name",
    "id_number",
    "birth_date",
    "gender",
    "employment_status",
    "planned_retirement",
)


class M01CaseError(Exception):
    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        missing_field_ids: tuple[str, ...] = (),
        conflicting_field_ids: tuple[str, ...] = (),
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.missing_field_ids = missing_field_ids
        self.conflicting_field_ids = conflicting_field_ids


@dataclass(frozen=True)
class M01Completeness:
    status: str
    missing_field_ids: tuple[str, ...]
    conflicting_field_ids: tuple[str, ...]


@dataclass(frozen=True)
class M01CaseSnapshot:
    client: Client
    profile: ClientProfile | None
    lifecycle_status: str
    completeness: M01Completeness
    allowed_lifecycle_targets: tuple[str, ...]


def _has_text(value: str | None) -> bool:
    return value is not None and value.strip() != ""


def normalize_required_text(value: str, field_id: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise M01CaseError(
            status_code=422,
            code=f"{field_id.upper()}_REQUIRED",
            message=f"{field_id} must not be empty",
            missing_field_ids=(field_id,),
        )
    return normalized


def normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def effective_lifecycle_status(stored_status: str | None) -> str:
    if stored_status in (None, "active"):
        return "draft"
    if stored_status in LIFECYCLE_STATUSES:
        return stored_status
    raise M01CaseError(
        status_code=409,
        code="unsupported_client_status",
        message="The stored client status is not supported by the M01 lifecycle",
    )


def derive_completeness(client: Client, profile: ClientProfile | None) -> M01Completeness:
    missing: list[str] = []
    conflicts: list[str] = []

    if not _has_text(client.display_name):
        missing.append("display_name")
    if not _has_text(client.id_number):
        missing.append("id_number")
    if client.birth_date is None:
        missing.append("birth_date")
    if profile is None or not _has_text(profile.gender):
        missing.append("gender")
    if client.employment_status not in COMPLETE_EMPLOYMENT_STATUSES:
        missing.append("employment_status")

    has_age = client.planned_retirement_age is not None
    has_date = client.planned_retirement_date is not None
    if not has_age and not has_date:
        missing.append("planned_retirement")
    elif has_age and has_date:
        conflicts.extend(("planned_retirement_age", "planned_retirement_date"))

    return M01Completeness(
        status="complete" if not missing and not conflicts else "incomplete",
        missing_field_ids=tuple(field_id for field_id in MISSING_FIELD_ORDER if field_id in missing),
        conflicting_field_ids=tuple(conflicts),
    )


def allowed_lifecycle_targets(
    lifecycle_status: str,
    completeness: M01Completeness,
) -> tuple[str, ...]:
    if lifecycle_status == "archived":
        return ("delivered",)

    targets: list[str] = []
    backward = BACKWARD_TRANSITIONS.get(lifecycle_status)
    if backward is not None:
        targets.append(backward)
    forward = FORWARD_TRANSITIONS.get(lifecycle_status)
    if forward is not None and completeness.status == "complete":
        targets.append(forward)
    return tuple(targets)


def get_client_profile(db: Session, client_id: int) -> ClientProfile | None:
    return db.scalar(select(ClientProfile).where(ClientProfile.client_id == client_id))


def build_case_snapshot(
    client: Client,
    profile: ClientProfile | None = None,
) -> M01CaseSnapshot:
    resolved_profile = profile if profile is not None else client.client_profile
    lifecycle_status = effective_lifecycle_status(client.status)
    completeness = derive_completeness(client, resolved_profile)
    return M01CaseSnapshot(
        client=client,
        profile=resolved_profile,
        lifecycle_status=lifecycle_status,
        completeness=completeness,
        allowed_lifecycle_targets=allowed_lifecycle_targets(lifecycle_status, completeness),
    )


def ensure_m01_editable(client: Client) -> None:
    if effective_lifecycle_status(client.status) == "archived":
        raise M01CaseError(
            status_code=409,
            code="archived_case_read_only",
            message="Archived client cases are read-only until explicitly reopened",
        )


def update_minimum_facts(
    db: Session,
    *,
    client: Client,
    payload: Any,
) -> M01CaseSnapshot:
    ensure_m01_editable(client)

    display_name = normalize_required_text(payload.display_name, "display_name")
    id_number = normalize_required_text(payload.id_number, "id_number")
    gender = normalize_optional_text(payload.gender)
    if payload.birth_date is not None and payload.birth_date > date.today():
        raise M01CaseError(
            status_code=422,
            code="BIRTH_DATE_IN_FUTURE",
            message="birth_date must not be in the future",
        )
    if (
        payload.planned_retirement_age is not None
        and payload.planned_retirement_date is not None
    ):
        raise M01CaseError(
            status_code=422,
            code="M01_PLANNED_RETIREMENT_CONFLICT",
            message="planned_retirement_age and planned_retirement_date are mutually exclusive",
            conflicting_field_ids=("planned_retirement_age", "planned_retirement_date"),
        )
    if (
        payload.planned_retirement_date is not None
        and payload.birth_date is not None
        and payload.planned_retirement_date <= payload.birth_date
    ):
        raise M01CaseError(
            status_code=422,
            code="PLANNED_RETIREMENT_DATE_NOT_AFTER_BIRTH",
            message="planned_retirement_date must be later than birth_date",
        )

    profile = get_client_profile(db, client.client_id)
    if profile is None:
        profile = ClientProfile(
            client_profile_id=f"CP-{client.client_id}",
            client_id=client.client_id,
            birth_date=None,
        )
        db.add(profile)

    client.display_name = display_name
    client.id_number = id_number
    client.birth_date = payload.birth_date
    client.employment_status = payload.employment_status
    client.planned_retirement_date = payload.planned_retirement_date
    client.planned_retirement_age = payload.planned_retirement_age
    profile.gender = gender
    db.flush()
    return build_case_snapshot(client, profile)


def transition_lifecycle(
    db: Session,
    *,
    client: Client,
    target_status: str,
) -> M01CaseSnapshot:
    profile = get_client_profile(db, client.client_id)
    snapshot = build_case_snapshot(client, profile)
    current = snapshot.lifecycle_status

    if target_status == current or (
        FORWARD_TRANSITIONS.get(current) != target_status
        and BACKWARD_TRANSITIONS.get(current) != target_status
    ):
        raise M01CaseError(
            status_code=409,
            code="invalid_lifecycle_transition",
            message=f"Transition from {current} to {target_status} is not allowed",
        )

    if FORWARD_TRANSITIONS.get(current) == target_status:
        if snapshot.completeness.conflicting_field_ids:
            raise M01CaseError(
                status_code=409,
                code="case_has_conflicting_fields",
                message="The client case has conflicting minimum facts",
                conflicting_field_ids=snapshot.completeness.conflicting_field_ids,
            )
        if snapshot.completeness.status != "complete":
            raise M01CaseError(
                status_code=409,
                code="case_incomplete",
                message="The client case is incomplete and cannot move forward",
                missing_field_ids=snapshot.completeness.missing_field_ids,
            )

    client.status = target_status
    db.flush()
    return build_case_snapshot(client, profile)
