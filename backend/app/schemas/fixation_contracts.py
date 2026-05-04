from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, StrictBool, ValidationError as PydanticValidationError, field_validator, model_validator


def _require_non_empty(value: str, field_name: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{field_name} must be non-empty")
    return stripped


ValidationCode = Literal[
    "MISSING_REQUIRED_VALUE",
    "INVALID_DATE",
    "INVALID_NUMBER",
    "INVALID_NESTED_ITEM",
    "INVALID_GLOBAL_INPUT",
    "UNSUPPORTED_OR_UNAPPROVED_VALUE",
]

GLOBAL_INPUT_PATH = "fixation_input"
LEGACY_VALIDATION_CODE_MAP: dict[str, ValidationCode] = {
    "ERR_REQUIRED_FIELD_MISSING": "MISSING_REQUIRED_VALUE",
    "ERR_INVALID_DATE": "INVALID_DATE",
    "ERR_INVALID_NUMERIC_VALUE": "INVALID_NUMBER",
    "ERR_INVALID_INPUT": "INVALID_GLOBAL_INPUT",
}


def validation_path_from_loc(loc: tuple[Any, ...]) -> str:
    if not loc:
        return GLOBAL_INPUT_PATH

    path = ""
    for item in loc:
        if item in {"__root__", "root"}:
            return GLOBAL_INPUT_PATH
        if isinstance(item, int):
            path += f"[{item}]"
            continue
        if not isinstance(item, str):
            continue
        if item in {"body", "query", "path"}:
            continue
        if path:
            path += "."
        path += item

    return path or GLOBAL_INPUT_PATH


def validation_code_from_error(error_type: str, path: str) -> ValidationCode:
    normalized_type = error_type.lower()
    if "missing" in normalized_type:
        return "MISSING_REQUIRED_VALUE"
    if "date" in normalized_type:
        return "INVALID_DATE"
    if any(token in normalized_type for token in ("float", "int", "number", "greater", "less", "finite")):
        return "INVALID_NUMBER"
    if path == GLOBAL_INPUT_PATH:
        return "INVALID_GLOBAL_INPUT"
    if path.startswith("grants[") or path.startswith("actual_capitalizations[") or path.startswith("idf"):
        return "INVALID_NESTED_ITEM"
    if any(token in normalized_type for token in ("literal", "enum", "union", "value_error")):
        return "UNSUPPORTED_OR_UNAPPROVED_VALUE"
    return "UNSUPPORTED_OR_UNAPPROVED_VALUE"


def map_contract_validation_errors(exc: PydanticValidationError) -> list["ValidationError"]:
    mapped_errors: list[ValidationError] = []
    for error in exc.errors():
        path = validation_path_from_loc(tuple(error.get("loc", ())))
        mapped_errors.append(
            ValidationError(
                code=validation_code_from_error(str(error.get("type", "validation_error")), path),
                path=path,
                message=str(error.get("msg", "Invalid input")),
                severity="error",
                source_id=None,
            )
        )

    return mapped_errors


class GrantInput(BaseModel):
    grant_id: str
    employer_name: str | None = None
    nominal_amount: float | None = None
    indexed_amount: float
    grant_date: date
    work_start_date: date
    work_end_date: date

    @field_validator("grant_id")
    @classmethod
    def validate_grant_id(cls, value: str) -> str:
        return _require_non_empty(value, "grant_id")

    @field_validator("employer_name")
    @classmethod
    def validate_employer_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _require_non_empty(value, "employer_name")

    @field_validator("nominal_amount")
    @classmethod
    def validate_nominal_amount(cls, value: float | None) -> float | None:
        if value is None:
            return value
        if value < 0:
            raise ValueError("nominal_amount must be >= 0")
        return value

    @field_validator("indexed_amount")
    @classmethod
    def validate_indexed_amount(cls, value: float) -> float:
        if value < 0:
            raise ValueError("indexed_amount must be >= 0")
        return value

    @model_validator(mode="after")
    def validate_work_date_range(self) -> "GrantInput":
        if self.work_start_date >= self.work_end_date:
            raise ValueError("work_start_date must be before work_end_date")
        return self


class ActualCapitalizationInput(BaseModel):
    capitalization_id: str
    amount: float
    capitalization_date: date
    source_label: str | None = None
    notes: str | None = None

    @field_validator("capitalization_id")
    @classmethod
    def validate_capitalization_id(cls, value: str) -> str:
        return _require_non_empty(value, "capitalization_id")

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: float) -> float:
        if value < 0:
            raise ValueError("amount must be >= 0")
        return value

    @field_validator("source_label")
    @classmethod
    def validate_source_label(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _require_non_empty(value, "source_label")


class IDFInput(BaseModel):
    idf_id: str
    reduction_amount: float
    original_commutation_percent: float
    current_commutation_percent: float
    commutation_date: date
    promoter_age_date: date
    source_label: str | None = None

    @field_validator("idf_id")
    @classmethod
    def validate_idf_id(cls, value: str) -> str:
        return _require_non_empty(value, "idf_id")

    @field_validator("reduction_amount")
    @classmethod
    def validate_reduction_amount(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("reduction_amount must be > 0")
        return value

    @field_validator("original_commutation_percent", "current_commutation_percent")
    @classmethod
    def validate_commutation_percent(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("commutation percent must be > 0")
        if 0 < value < 1:
            raise ValueError("commutation percent must be in percent points, not decimal format")
        return value

    @field_validator("source_label")
    @classmethod
    def validate_idf_source_label(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _require_non_empty(value, "source_label")


class FixationInput(BaseModel):
    calculation_id: str | None = None
    calculation_version: str
    eligibility_date: date
    eligibility_year: int
    monthly_cap: float
    exemption_percentage: float
    capital_multiplier: float
    grants: list[GrantInput]
    future_grant_reserved: float
    actual_capitalizations: list[ActualCapitalizationInput]
    idf_relevant: StrictBool
    idf: IDFInput | None
    metadata: dict[str, Any] | None = None

    @field_validator("calculation_id")
    @classmethod
    def validate_calculation_id(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _require_non_empty(value, "calculation_id")

    @field_validator("calculation_version")
    @classmethod
    def validate_calculation_version(cls, value: str) -> str:
        return _require_non_empty(value, "calculation_version")

    @field_validator("monthly_cap")
    @classmethod
    def validate_monthly_cap(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("monthly_cap must be > 0")
        return value

    @field_validator("exemption_percentage")
    @classmethod
    def validate_exemption_percentage(cls, value: float) -> float:
        if value < 0 or value > 1:
            raise ValueError("exemption_percentage must be between 0 and 1")
        return value

    @field_validator("capital_multiplier")
    @classmethod
    def validate_capital_multiplier(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("capital_multiplier must be > 0")
        return value

    @field_validator("future_grant_reserved")
    @classmethod
    def validate_future_grant_reserved(cls, value: float) -> float:
        if value < 0:
            raise ValueError("future_grant_reserved must be >= 0")
        return value

    @model_validator(mode="after")
    def validate_cross_field_rules(self) -> "FixationInput":
        if self.eligibility_year != self.eligibility_date.year:
            raise ValueError("eligibility_year must match eligibility_date year")

        if self.idf_relevant and self.idf is None:
            raise ValueError("idf is required when idf_relevant is true")

        if self.idf is not None:
            later_date = max(self.idf.commutation_date, self.eligibility_date)
            if self.idf.promoter_age_date <= later_date:
                raise ValueError(
                    "idf.promoter_age_date must be after later of idf.commutation_date and eligibility_date"
                )

        return self


class GrantResult(BaseModel):
    grant_id: str
    indexed_amount: float
    limited_indexed_amount: float
    impact_amount: float
    exclusion_reason: str | None

    @field_validator("grant_id")
    @classmethod
    def validate_grant_result_id(cls, value: str) -> str:
        return _require_non_empty(value, "grant_id")

    @field_validator("indexed_amount", "limited_indexed_amount", "impact_amount")
    @classmethod
    def validate_grant_result_amounts(cls, value: float) -> float:
        if value < 0:
            raise ValueError("grant result amounts must be >= 0")
        return value


class ActualCapitalizationResult(BaseModel):
    capitalization_id: str
    amount: float
    impact_amount: float

    @field_validator("capitalization_id")
    @classmethod
    def validate_capitalization_result_id(cls, value: str) -> str:
        return _require_non_empty(value, "capitalization_id")

    @field_validator("amount", "impact_amount")
    @classmethod
    def validate_capitalization_result_amounts(cls, value: float) -> float:
        if value < 0:
            raise ValueError("actual capitalization result amounts must be >= 0")
        return value


class IDFResult(BaseModel):
    idf_id: str
    base_reduction: float
    monthly_reduction_for_calc: float
    overlap_months: float
    impact_amount: float
    informational_only: Literal[True]

    @field_validator("idf_id")
    @classmethod
    def validate_idf_result_id(cls, value: str) -> str:
        return _require_non_empty(value, "idf_id")

    @field_validator("base_reduction", "monthly_reduction_for_calc")
    @classmethod
    def validate_positive_idf_result_fields(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("idf result base_reduction and monthly_reduction_for_calc must be > 0")
        return value

    @field_validator("overlap_months")
    @classmethod
    def validate_overlap_months(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("idf result overlap_months must be > 0")
        return value

    @field_validator("impact_amount")
    @classmethod
    def validate_idf_impact_amount(cls, value: float) -> float:
        if value < 0:
            raise ValueError("impact_amount must be >= 0")
        return value


AuditCategory = Literal[
    "initial_entitlement",
    "grant",
    "future_grant_reserve",
    "actual_capitalization",
    "idf",
    "total",
    "remaining_exemption",
]


class AuditRow(BaseModel):
    row_id: str
    stage_order: int
    category: AuditCategory
    source_id: str | None
    label: str
    input_amount: float | None
    output_amount: float
    impact_amount: float
    details: dict[str, Any]

    @field_validator("row_id", "label")
    @classmethod
    def validate_non_empty_fields(cls, value: str, info: Any) -> str:
        return _require_non_empty(value, str(info.field_name))

    @field_validator("impact_amount")
    @classmethod
    def validate_impact_amount(cls, value: float) -> float:
        if value < 0:
            raise ValueError("impact_amount must be >= 0")
        return value

    @field_validator("stage_order")
    @classmethod
    def validate_stage_order(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("stage_order must be > 0")
        return value

    @model_validator(mode="after")
    def validate_audit_dependencies(self) -> "AuditRow":
        requires_source_id = {"grant", "actual_capitalization", "idf"}
        if self.category in requires_source_id and not self.source_id:
            raise ValueError("source_id is required for grant, actual_capitalization, and idf categories")

        input_required_categories = {"grant", "future_grant_reserve", "actual_capitalization", "idf"}
        if self.category in input_required_categories and self.input_amount is None:
            raise ValueError("input_amount may be null only when not applicable")

        return self


class ValidationError(BaseModel):
    code: ValidationCode
    path: str
    message: str
    severity: Literal["error"]
    source_id: str | None

    @field_validator("code", mode="before")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        normalized_value = _require_non_empty(value, "code")
        return LEGACY_VALIDATION_CODE_MAP.get(normalized_value, normalized_value)

    @field_validator("path", "message")
    @classmethod
    def validate_non_empty_strings(cls, value: str, info: Any) -> str:
        return _require_non_empty(value, str(info.field_name))


class FixationResult(BaseModel):
    calculation_id: str | None = None
    calculation_version: str | None = None
    status: Literal["success", "validation_failed"]
    validation_errors: list[ValidationError]
    eligibility_date: date | None = None
    eligibility_year: int | None = None
    monthly_cap: float | None = None
    exemption_percentage: float | None = None
    capital_multiplier: float | None = None
    initial_exempt_capital: float | None = None
    grant_impact_total: float | None = None
    future_grant_reserved: float | None = None
    future_grant_impact: float | None = None
    actual_capitalization_impact: float | None = None
    idf_impact: float | None = None
    total_impact: float | None = None
    remaining_exempt_capital: float | None = None
    monthly_exempt_pension: float | None = None
    capital_exemption_percentage: float | None = None
    pension_exemption_percentage: float | None = None
    grant_results: list[GrantResult] | None = None
    actual_capitalization_results: list[ActualCapitalizationResult] | None = None
    idf_result: IDFResult | None = None
    audit_rows: list[AuditRow] | None = None

    @model_validator(mode="after")
    def validate_status_behavior(self) -> "FixationResult":
        numeric_fields = (
            "eligibility_year",
            "monthly_cap",
            "exemption_percentage",
            "capital_multiplier",
            "initial_exempt_capital",
            "grant_impact_total",
            "future_grant_reserved",
            "future_grant_impact",
            "actual_capitalization_impact",
            "idf_impact",
            "total_impact",
            "remaining_exempt_capital",
            "monthly_exempt_pension",
            "capital_exemption_percentage",
            "pension_exemption_percentage",
        )

        if self.status == "success":
            if self.validation_errors:
                raise ValueError("validation_errors must be empty when status is success")

            required_success_fields = (
                "calculation_version",
                "eligibility_date",
                "eligibility_year",
                "monthly_cap",
                "exemption_percentage",
                "capital_multiplier",
                "initial_exempt_capital",
                "grant_impact_total",
                "future_grant_reserved",
                "future_grant_impact",
                "actual_capitalization_impact",
                "idf_impact",
                "total_impact",
                "remaining_exempt_capital",
                "monthly_exempt_pension",
                "capital_exemption_percentage",
                "pension_exemption_percentage",
                "grant_results",
                "actual_capitalization_results",
                "audit_rows",
            )
            for field_name in required_success_fields:
                if getattr(self, field_name) is None:
                    raise ValueError(f"{field_name} must be present when status is success")

        if self.status == "validation_failed":
            if not self.validation_errors:
                raise ValueError("validation_errors must be non-empty when status is validation_failed")

            for field_name in numeric_fields:
                if getattr(self, field_name) is not None:
                    raise ValueError(f"{field_name} must be omitted when status is validation_failed")

        return self
