"""SC-05C draft-only pension elections. No coefficient or financial authority.

A future persisted election MUST be bound to decision identity and scenario
revision by the DB-owned writer; this schema alone grants no permissions.
"""
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ScenarioPensionElection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    decision_id: str = Field(min_length=1, max_length=64)
    pension_start_date: date
    target_year: int = Field(ge=1900, le=2300)
    survivors_option: str = Field(min_length=1, max_length=128)
    spouse_age_diff: int = Field(ge=-100, le=100)
    coefficient_selection: Literal["catalog_candidate", "manual_review_required"]
    company_name: str | None = Field(default=None, max_length=255)
    option_name: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def require_explicit_nonblank_election(self):
        if self.survivors_option != self.survivors_option.strip() or not self.survivors_option.strip():
            raise ValueError("SCENARIO_PENSION_ELECTION_NOT_CANONICAL")
        for value in (self.company_name, self.option_name):
            if value is not None and (not value.strip() or value != value.strip()):
                raise ValueError("SCENARIO_PENSION_ELECTION_NOT_CANONICAL")
        if (self.company_name is None) != (self.option_name is None):
            raise ValueError("SCENARIO_PENSION_INSURANCE_OPTIONS_INCOMPLETE")
        return self


class ScenarioPensionElectionSet(BaseModel):
    """Closed input for a future atomic, version-checked draft writer."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    expected_scenario_version: int = Field(ge=1)
    elections: list[ScenarioPensionElection] = Field(max_length=500)

    @model_validator(mode="after")
    def unique_decisions(self):
        ids = [row.decision_id for row in self.elections]
        if len(ids) != len(set(ids)):
            raise ValueError("SCENARIO_PENSION_ELECTION_DUPLICATE_DECISION")
        return self
