from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


EmploymentStatus = Literal[
    "salaried_employee",
    "self_employed",
    "salaried_and_self_employed",
    "not_currently_working",
    "unknown",
]
LifecycleStatus = Literal["draft", "intake", "analysis", "review", "delivered", "archived"]


class M01CompletenessResponse(BaseModel):
    status: Literal["complete", "incomplete"]
    missing_field_ids: list[str]
    conflicting_field_ids: list[str]


class M01CaseUpdateRequest(BaseModel):
    display_name: str
    id_number: str
    birth_date: date | None = None
    gender: str | None = None
    employment_status: EmploymentStatus | None = None
    planned_retirement_date: date | None = None
    planned_retirement_age: int | None = Field(default=None, ge=18, le=120)


class M01LifecycleTransitionRequest(BaseModel):
    target_status: LifecycleStatus


class M01CaseResponse(BaseModel):
    client_id: int
    display_name: str
    id_number: str
    birth_date: date | None
    gender: str | None
    employment_status: EmploymentStatus | None
    planned_retirement_date: date | None
    planned_retirement_age: int | None
    lifecycle_status: LifecycleStatus
    completeness: M01CompletenessResponse
    allowed_lifecycle_targets: list[LifecycleStatus]
    updated_at: datetime
