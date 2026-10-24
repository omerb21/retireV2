from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ScenarioPermissionPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: str = Field(min_length=1, max_length=64)
    action: Literal["pension", "capital_asset"]
    effective_date: date

    @field_validator("product_id")
    @classmethod
    def canonical_product_id(cls, value: str) -> str:
        if value != value.strip() or any(ord(char) < 32 for char in value):
            raise ValueError("product_id must be canonical")
        return value
