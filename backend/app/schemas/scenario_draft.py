"""Draft-only scenario API contracts; no financial admission."""
from datetime import date
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.models.pension_product import COMPONENT_CODES

class DraftWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=255)
    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str) -> str:
        if not value.strip() or value != value.strip():
            raise ValueError("scenario name is not canonical")
        return value

class DraftDecisionWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision_id: str | None = Field(default=None, min_length=1, max_length=64)
    source_product_id: str = Field(min_length=1, max_length=64)
    source_component_id: str = Field(min_length=1, max_length=64)
    component_code: str
    amount: Decimal = Field(gt=0, max_digits=20, decimal_places=2)
    action: Literal["pension", "capital_asset"]
    effective_date: date
    @field_validator("component_code")
    @classmethod
    def known_component(cls, value: str) -> str:
        if value not in COMPONENT_CODES:
            raise ValueError("unknown canonical component")
        return value

class DraftReplace(DraftWrite):
    expected_version: int = Field(ge=1)
    decisions: list[DraftDecisionWrite] = Field(max_length=500)

class DraftVersion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
