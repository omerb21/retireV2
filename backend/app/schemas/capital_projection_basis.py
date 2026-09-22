from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.models.capital_projection_basis import parse_rate


class ProjectionExpectations(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_version: int = Field(ge=0)
    expected_planning_calculation_input_fingerprint: str = Field(pattern=r'^[0-9a-f]{64}$')
    expected_source_semantic_fingerprint: str = Field(pattern=r'^[0-9a-f]{64}$')
    expected_timing_context_fingerprint: str = Field(pattern=r'^[0-9a-f]{64}$')


class ProjectionDecisionWrite(ProjectionExpectations):
    annual_rate: str = Field(strict=True)
    return_basis: Literal['NET', 'GROSS']
    price_basis: Literal['NOMINAL', 'REAL']

    @field_validator('annual_rate')
    @classmethod
    def exact_rate(cls, value):
        parse_rate(value)
        return value
