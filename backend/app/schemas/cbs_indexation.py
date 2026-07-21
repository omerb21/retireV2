from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


CBS_CPI_CODE = "120010"
CBS_CALCULATOR_ENDPOINT = f"https://api.cbs.gov.il/index/data/calculator/{CBS_CPI_CODE}"

IndexationBaseDateSource = Literal["grant_date", "work_end_date"]
IndexationFailureOutcome = Literal["calculation_failed", "unsupported_calculation"]


class CbsIndexationRequestEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cpi_code: Literal["120010"] = CBS_CPI_CODE
    amount: Decimal = Field(gt=0)
    resolved_base_date: date
    base_date_source: IndexationBaseDateSource
    target_date: date
    endpoint: Literal[CBS_CALCULATOR_ENDPOINT] = CBS_CALCULATOR_ENDPOINT
    calculation_timestamp: datetime


class CbsIndexationResponseEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw_to_value: Decimal
    from_index_period: str | None = None
    to_index_period: str | None = None
    from_index_value: Decimal | None = None
    to_index_value: Decimal | None = None
    base_year: str | None = None
    chaining_coefficient: Decimal | None = None
    change_percentage: Decimal | None = None
    missing_optional_fields: list[str]
    calculation_timestamp: datetime
    response_status: int
    cpi_code: Literal["120010"] = CBS_CPI_CODE
    endpoint: Literal[CBS_CALCULATOR_ENDPOINT] = CBS_CALCULATOR_ENDPOINT


class CbsIndexationFailureEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outcome_status: IndexationFailureOutcome
    failure_category: Literal[
        "missing_base_date",
        "transport_error",
        "timeout",
        "http_error",
        "malformed_response",
        "missing_answer",
        "missing_to_value",
        "unsupported_calculation",
    ]
    http_status: int | None = None
    timeout: bool = False
    malformed_response: bool = False
    missing_to_value: bool = False
    source_endpoint: Literal[CBS_CALCULATOR_ENDPOINT] = CBS_CALCULATOR_ENDPOINT
    cpi_code: Literal["120010"] = CBS_CPI_CODE
    calculation_timestamp: datetime
    safe_technical_message: str


class CbsIndexationSuccess(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: Literal[True] = True
    request: CbsIndexationRequestEvidence
    response: CbsIndexationResponseEvidence


class CbsIndexationFailure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: Literal[False] = False
    request: CbsIndexationRequestEvidence | None = None
    failure: CbsIndexationFailureEvidence


CbsIndexationOutcome = CbsIndexationSuccess | CbsIndexationFailure
