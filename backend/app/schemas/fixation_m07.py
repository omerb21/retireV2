from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

class FixationEligibilityRevisionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eligibility_date: str = Field(min_length=10, max_length=10)

    @field_validator("eligibility_date")
    @classmethod
    def validate_exact_date(cls, value: str) -> str:
        try:
            normalized = date.fromisoformat(value).isoformat()
        except ValueError as error:
            raise ValueError(
                "eligibility_date must be a valid calendar date in exact "
                "YYYY-MM-DD format"
            ) from error
        if normalized != value:
            raise ValueError(
                "eligibility_date must be a valid calendar date in exact "
                "YYYY-MM-DD format"
            )
        return normalized


class FixationEligibilityRevisionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revision_id: str
    profile_id: str
    revision_number: int
    status: Literal["finalized"]
    finalized_at: datetime
    eligibility_outcome: Literal[
        "resolved",
        "missing_inputs",
        "ambiguous_inputs",
    ]
    eligibility_dates: list[str]


class FixationEligibilityRevisionList(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[FixationEligibilityRevisionSummary]
    offset: int
    limit: int
    total: int


class FixationEligibilityRevisionCreated(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revision_id: str
    status: Literal["finalized"]
    finalized_at: datetime
    eligibility_date: str
    technical_actor: str
