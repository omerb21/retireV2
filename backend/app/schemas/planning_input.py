from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class BaseDateDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=0)
    planning_base_date: date | None


class IncomeResolutionDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    expected_version: int = Field(ge=0)
    expected_income_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    decision_kind: Literal["SAME_CANONICAL_PENSION", "PENSION_NOT_YET_CANONICAL", "MISCLASSIFIED_GENERAL_INCOME"]
    canonical_source_id: str | None = Field(default=None, min_length=1, max_length=128)
    expected_canonical_fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    income_category: Literal["employment", "rental", "business", "benefit", "other"] | None = None
    reference: str = Field(min_length=1, max_length=512)

    @model_validator(mode="after")
    def validate_action(self):
        if self.decision_kind == "MISCLASSIFIED_GENERAL_INCOME":
            if self.income_category is None or self.canonical_source_id or self.expected_canonical_fingerprint:
                raise ValueError("נדרשת קטגוריית הכנסה שאינה קצבה, ללא קישור לקצבה")
        elif not self.canonical_source_id or not self.expected_canonical_fingerprint or self.income_category:
            raise ValueError("נדרש מקור קצבה קנוני קיים וטביעת המקור שלו")
        return self


class TargetDateDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=0)
    expected_target_reference_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    retirement_target_date: date | None
