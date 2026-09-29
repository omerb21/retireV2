from datetime import date
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.schemas.pension_product import Money


class TemporalAuthorityInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    authority_kind: Literal["none", "fixed_manual"]
    annual_rate: str | None = Field(default=None, strict=True, max_length=128)


class ManualPensionInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    input_mode: Literal["entered", "calculated"]
    payer_name: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=4096)
    source_reference: str | None = Field(default=None, max_length=255)
    monthly_amount: Money | None = None
    balance: Money | None = None
    annuity_factor: str | None = Field(default=None, max_length=128)
    pension_start_date: date | None = None
    base_amount_effective_date: date | None = None
    tax_treatment: str | None = Field(default=None, max_length=64)
    # Accepted only so the service can return the package-specific domain
    # error for direct legacy writes; never emitted by canonical model_dump.
    indexation_method: str | None = Field(default=None, max_length=64, exclude=True)
    fixed_indexation_rate: str | None = Field(default=None, max_length=128, exclude=True)
    temporal_authority: TemporalAuthorityInput | None = None
    source_note: str | None = Field(default=None, max_length=4096)

    @field_validator("monthly_amount", "balance")
    @classmethod
    def nonnegative(cls, value):
        if value is not None and value < 0:
            raise ValueError("סכום שלילי אינו מותר")
        return value

    @field_validator("annuity_factor", "fixed_indexation_rate")
    @classmethod
    def decimal_fact(cls, value, info):
        if value is None:
            return None
        try:
            number = Decimal(value)
            if not number.is_finite() or (info.field_name == "annuity_factor" and number <= 0):
                raise ValueError("נתון עשרוני לא תקין")
            if info.field_name == "fixed_indexation_rate" and number < 0:
                raise ValueError("שיעור הצמדה שלילי אינו מותר")
            # Fixed decimal text is the authority, not a binary float or a
            # rounded NUMERIC factor. Bound representation before formatting.
            if abs(number.adjusted()) > 120 or number.as_tuple().exponent < -120:
                raise ValueError("נתון עשרוני ארוך מדי")
            normalized = format(number, "f")
            if len(normalized) > 128:
                raise ValueError("נתון עשרוני ארוך מדי")
            return normalized
        except ArithmeticError as error:
            raise ValueError("נתון עשרוני לא תקין") from error

    @model_validator(mode="after")
    def exclusive(self):
        if self.input_mode == "entered" and (self.balance is not None or self.annuity_factor is not None):
            raise ValueError("אין לערבב סכום חודשי עם יתרה ומקדם")
        if self.input_mode == "calculated" and self.monthly_amount is not None:
            raise ValueError("סכום חודשי מחושב אינו סמכות נוספת")
        return self


class ManualPensionUpdate(ManualPensionInput):
    expected_version: int = Field(ge=1)


class ManualPensionSupersede(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)


class ConversionTemporalDecisionWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_source_version: int = Field(ge=1)
    expected_decision_version: int = Field(ge=0)
    temporal_authority: TemporalAuthorityInput
    actor: str = Field(min_length=1, max_length=128)
