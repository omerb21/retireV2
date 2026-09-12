from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class PensionInputs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pension_start_date: date
    retirement_age: int | None = Field(default=None, ge=0, le=130)
    company_name: str | None = Field(default=None, max_length=255)
    option_name: str | None = Field(default=None, max_length=255)
    survivors_option: str = Field(default="תקנוני", min_length=1, max_length=128)
    spouse_age_diff: int = Field(default=0, ge=-100, le=100)
    target_year: int | None = Field(default=None, ge=1900, le=2300)


class Selection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    component_id: str = Field(min_length=1, max_length=64)
    component_code: str = Field(min_length=1, max_length=128)
    amount: str | None = None  # None means full locked balance, not a client total.


class ConversionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_id: str = Field(min_length=1, max_length=64)
    expected_product_version: int = Field(ge=1)
    destination_type: Literal["pension", "capital"]
    effective_date: date
    idempotency_key: str = Field(min_length=1, max_length=128)
    whole_product: bool = False
    selections: list[Selection] = Field(default_factory=list, max_length=11)
    pension: PensionInputs | None = None


class ReversalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_conversion_version: int = Field(ge=1)
    expected_product_version: int = Field(ge=1)
    idempotency_key: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=1, max_length=1024)
