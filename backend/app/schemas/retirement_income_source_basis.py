from __future__ import annotations

from datetime import date
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, field_validator, model_validator

SHA_PATTERN = r"^[0-9a-f]{64}$"


class _Command(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    operation: Literal["CLASSIFY", "CLEAR"]
    source_kind: Literal["PENSION", "RECURRING_INCOME"]
    expected_decision_version: StrictInt = Field(ge=0, le=9223372036854775807)
    expected_planning_calculation_input_fingerprint: StrictStr = Field(pattern=SHA_PATTERN)
    expected_source_version: StrictInt | StrictStr
    expected_source_fingerprint: StrictStr = Field(pattern=SHA_PATTERN)
    expected_amount_authority_fingerprint: StrictStr = Field(pattern=SHA_PATTERN)

    @field_validator("expected_decision_version")
    @classmethod
    def no_bool_version(cls, value):
        if isinstance(value, bool):
            raise ValueError("boolean is not an integer")
        return value


class PensionClassifyCommand(_Command):
    schema_version: Literal["CRTISBA_PENSION_CLASSIFY_COMMAND_V1"]
    operation: Literal["CLASSIFY"]
    source_kind: Literal["PENSION"]
    expected_source_version: StrictInt = Field(ge=1)
    income_basis: Literal["GROSS", "NET"]


class PensionClearCommand(_Command):
    schema_version: Literal["CRTISBA_PENSION_CLEAR_COMMAND_V1"]
    operation: Literal["CLEAR"]
    source_kind: Literal["PENSION"]
    expected_source_version: StrictInt = Field(ge=1)


class RecurringClassifyCommand(_Command):
    schema_version: Literal["CRTISBA_RECURRING_CLASSIFY_COMMAND_V1"]
    operation: Literal["CLASSIFY"]
    source_kind: Literal["RECURRING_INCOME"]
    expected_source_version: StrictStr = Field(pattern=SHA_PATTERN)
    price_basis: Literal["NOMINAL_AT_RETIREMENT_TARGET_DATE", "REAL_AT_REFERENCE_DATE"]
    price_reference_date: StrictStr | None

    @field_validator("price_reference_date")
    @classmethod
    def canonical_date(cls, value):
        if value is not None:
            try:
                if date.fromisoformat(value).isoformat() != value:
                    raise ValueError
            except ValueError as exc:
                raise ValueError("price reference date must be canonical ISO date") from exc
        return value

    @model_validator(mode="after")
    def validate_price_reference(self):
        if self.expected_source_version != self.expected_source_fingerprint:
            raise ValueError("recurring source version must equal source fingerprint")
        if (self.price_basis == "REAL_AT_REFERENCE_DATE") != (self.price_reference_date is not None):
            raise ValueError("price reference date does not match price basis")
        return self


class RecurringClearCommand(_Command):
    schema_version: Literal["CRTISBA_RECURRING_CLEAR_COMMAND_V1"]
    operation: Literal["CLEAR"]
    source_kind: Literal["RECURRING_INCOME"]
    expected_source_version: StrictStr = Field(pattern=SHA_PATTERN)

    @model_validator(mode="after")
    def validate_source_version(self):
        if self.expected_source_version != self.expected_source_fingerprint:
            raise ValueError("recurring source version must equal source fingerprint")
        return self


CRTISBACommand = Annotated[
    Union[PensionClassifyCommand, PensionClearCommand, RecurringClassifyCommand, RecurringClearCommand],
    Field(discriminator="schema_version"),
]
