"""Closed request shape for draft-only severance planning choices."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class SeverancePlanningChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_kind: Literal["grant", "pension_component"]
    source_id: str = Field(min_length=1, max_length=64)
    choice: Literal[
        "UNDECIDED", "PLANNED_WITHDRAWAL",
        "PLANNED_PENSION_CONTINUITY", "PLANNED_SEVERANCE_CONTINUITY",
    ]
    planned_amount_ils: str | None = None


class SeverancePlanningReplace(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    choices: list[SeverancePlanningChoice] = Field(max_length=500)
