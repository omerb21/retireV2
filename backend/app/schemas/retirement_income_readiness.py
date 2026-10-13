from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, field_validator


class TargetConfirmationBody(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    expected_record_version: StrictInt = Field(ge=0, le=9223372036854775807)
    expected_planning_calculation_input_fingerprint: StrictStr = Field(pattern=r"^[0-9a-f]{64}$")
    expected_retirement_target_date: StrictStr = Field(pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
    monthly_amount: StrictStr
    income_basis: Literal["GROSS", "NET"]
    price_basis: Literal["NOMINAL_AT_RETIREMENT_TARGET_DATE", "REAL_AT_REFERENCE_DATE"]
    price_reference_date: StrictStr | None = Field(pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
    source_kind: Literal["CLIENT_SUPPLIED", "PLANNER_SUPPLIED", "CLIENT_SUPPLIED_PLANNER_CONFIRMED"]

    @field_validator("price_reference_date")
    @classmethod
    def canonical_price_reference_date(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            if date.fromisoformat(value).isoformat() != value:
                raise ValueError("date must be canonical ISO format")
        except ValueError as exc:
            raise ValueError("date must be canonical ISO format") from exc
        return value


class ComparisonBody(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    expected_planning_calculation_input_fingerprint: StrictStr = Field(pattern=r"^[0-9a-f]{64}$")
    expected_retirement_target_date: StrictStr = Field(pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
