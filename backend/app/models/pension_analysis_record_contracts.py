from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class PensionAnalysisRecordCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_record_text: str

    @field_validator("analysis_record_text")
    @classmethod
    def validate_analysis_record_text(cls, value: str) -> str:
        if value.strip() == "":
            raise ValueError("analysis_record_text is required")
        return value


class PensionAnalysisRecordUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_record_text: str

    @field_validator("analysis_record_text")
    @classmethod
    def validate_analysis_record_text(cls, value: str) -> str:
        if value.strip() == "":
            raise ValueError("analysis_record_text is required")
        return value


class PensionAnalysisRecordResponse(BaseModel):
    id: int
    client_id: int
    pension_holding_id: int
    analysis_record_text: str
    created_at: datetime
    updated_at: datetime
