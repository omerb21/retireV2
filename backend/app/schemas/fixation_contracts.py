from __future__ import annotations

from datetime import date
from decimal import Decimal
import math
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    RootModel,
    SerializerFunctionWrapHandler,
    ValidationError as PydanticValidationError,
    field_validator,
    model_serializer,
    model_validator,
)

from app.schemas.m07_calculation_input_resolution import (
    CalculationInputResolutionResult,
)


def _require_non_empty(value: str, field_name: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{field_name} must be non-empty")
    return stripped


def _require_valid_source_item_id(value: str) -> str:
    source_item_id = _require_non_empty(value, "source_item_id")
    if len(source_item_id) > 64:
        raise ValueError("source_item_id must be 64 characters or fewer")
    if not source_item_id[0].isalnum():
        raise ValueError("source_item_id must start with a letter or number")
    if not all(char.isalnum() or char in {"-", "_"} for char in source_item_id):
        raise ValueError("source_item_id must contain only letters, numbers, hyphen, or underscore")
    return source_item_id


ValidationCode = Literal[
    "MISSING_REQUIRED_VALUE",
    "INVALID_DATE",
    "INVALID_NUMBER",
    "INVALID_NESTED_ITEM",
    "INVALID_GLOBAL_INPUT",
    "UNSUPPORTED_OR_UNAPPROVED_VALUE",
    "CBS_CALCULATION_FAILED",
    "CBS_UNSUPPORTED_CALCULATION",
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
    if any(token in normalized_type for token in ("literal", "enum", "union")):
        return "UNSUPPORTED_OR_UNAPPROVED_VALUE"
    if (
        path.startswith("grants[")
        or path.startswith("grants.")
        or path.startswith("actual_capitalizations[")
        or path.startswith("actual_capitalizations.")
        or path.startswith("idf")
    ):
        return "INVALID_NESTED_ITEM"
    if "value_error" in normalized_type:
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
    client_id: int | None = None
    employer_name: str | None = None
    employer_withholding_file_number: str | None = None
    nominal_amount: Decimal | None = None
    indexed_amount: Decimal
    grant_date: date
    work_start_date: date
    work_end_date: date
    parameter_set_id: str | None = None
    cbs_request_evidence: dict[str, Any] | None = None
    cbs_response_evidence: dict[str, Any] | None = None

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
    def validate_nominal_amount(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return value
        if not value.is_finite() or value < 0:
            raise ValueError("nominal_amount must be >= 0")
        return value

    @field_validator("indexed_amount")
    @classmethod
    def validate_indexed_amount(cls, value: Decimal) -> Decimal:
        if not value.is_finite() or value < 0:
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


ReviewCollectionState = Literal["unknown", "not_collected", "confirmed_none", "items_recorded"]
ReviewDisposition = Literal["include", "exclude"]


class GrantReviewItem(BaseModel):
    source_item_id: str
    grant_id: str
    employer_name: str | None = None
    nominal_amount: float | None = None
    indexed_amount: float
    grant_date: date
    work_start_date: date
    work_end_date: date
    disposition: ReviewDisposition

    @field_validator("source_item_id")
    @classmethod
    def validate_source_item_id(cls, value: str) -> str:
        return _require_valid_source_item_id(value)

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
    def validate_work_date_range(self) -> "GrantReviewItem":
        if self.work_start_date >= self.work_end_date:
            raise ValueError("work_start_date must be before work_end_date")
        return self


class ActualCapitalizationReviewItem(BaseModel):
    source_item_id: str
    capitalization_id: str
    amount: float
    capitalization_date: date
    source_label: str | None = None
    source_basis: str | None = None
    planner_assertion: str | None = None
    planner_assertion_basis: str | None = None
    notes: str | None = None
    disposition: ReviewDisposition

    @field_validator("source_item_id")
    @classmethod
    def validate_source_item_id(cls, value: str) -> str:
        return _require_valid_source_item_id(value)

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

    @field_validator("source_label", "source_basis", "planner_assertion", "planner_assertion_basis", "notes")
    @classmethod
    def validate_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _require_non_empty(value, "review text field")

    @model_validator(mode="after")
    def validate_planner_assertion_basis(self) -> "ActualCapitalizationReviewItem":
        if self.planner_assertion is not None and self.planner_assertion_basis is None:
            raise ValueError("planner_assertion_basis is required when planner_assertion is supplied")
        return self


class GrantReviewDomain(BaseModel):
    collection_state: ReviewCollectionState
    items: list[GrantReviewItem]

    @model_validator(mode="after")
    def validate_collection_state_items(self) -> "GrantReviewDomain":
        if self.collection_state in {"unknown", "not_collected", "confirmed_none"} and self.items:
            raise ValueError(f"{self.collection_state} requires an empty grants items array")
        if self.collection_state == "items_recorded" and not self.items:
            raise ValueError("items_recorded requires one or more grants items")
        return self


class ActualCapitalizationReviewDomain(BaseModel):
    collection_state: ReviewCollectionState
    items: list[ActualCapitalizationReviewItem]

    @model_validator(mode="after")
    def validate_collection_state_items(self) -> "ActualCapitalizationReviewDomain":
        if self.collection_state in {"unknown", "not_collected", "confirmed_none"} and self.items:
            raise ValueError(f"{self.collection_state} requires an empty actual_capitalizations items array")
        if self.collection_state == "items_recorded" and not self.items:
            raise ValueError("items_recorded requires one or more actual_capitalizations items")
        return self


class PlannerReviewContextDomain(BaseModel):
    model_config = ConfigDict(extra="forbid")

    collection_state: ReviewCollectionState
    included_source_reference_ids: list[str]
    excluded_source_reference_ids: list[str]

    @field_validator("included_source_reference_ids", "excluded_source_reference_ids")
    @classmethod
    def validate_source_reference_ids(cls, value: list[str]) -> list[str]:
        return [_require_valid_source_item_id(source_id) for source_id in value]


class PlannerReviewContextEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    grants: PlannerReviewContextDomain
    actual_capitalizations: PlannerReviewContextDomain


InternalPlannerHandlingStatus = Literal[
    "not_used_for_decision",
    "continue_internal_review",
    "internal_action_identified",
]


class InternalPlannerJudgmentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    handling_status: InternalPlannerHandlingStatus
    next_internal_action: str
    internal_note: str | None = None

    @field_validator("next_internal_action")
    @classmethod
    def validate_next_internal_action(cls, value: str) -> str:
        return _require_non_empty(value, "next_internal_action")

    @field_validator("internal_note")
    @classmethod
    def validate_internal_note(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _require_non_empty(value, "internal_note")


class InternalPlannerJudgmentResponse(BaseModel):
    saved_run_id: int
    handling_status: InternalPlannerHandlingStatus
    next_internal_action: str
    internal_note: str | None = None


class FixationInputReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    calculation_id: str | None = None
    calculation_version: str
    eligibility_date: date
    eligibility_year: int
    monthly_cap: float
    exemption_percentage: float
    capital_multiplier: float
    grant_impact_multiplier: float
    grants: GrantReviewDomain
    future_grant_reserved: float
    actual_capitalizations: ActualCapitalizationReviewDomain
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

    @field_validator("grant_impact_multiplier")
    @classmethod
    def validate_grant_impact_multiplier(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("grant_impact_multiplier must be > 0")
        return value

    @field_validator("future_grant_reserved")
    @classmethod
    def validate_future_grant_reserved(cls, value: float) -> float:
        if value < 0:
            raise ValueError("future_grant_reserved must be >= 0")
        return value

    @model_validator(mode="after")
    def validate_cross_field_rules(self) -> "FixationInputReview":
        if self.eligibility_year != self.eligibility_date.year:
            raise ValueError("eligibility_year must match eligibility_date year")

        if self.idf is not None:
            later_date = max(self.idf.commutation_date, self.eligibility_date)
            if self.idf.promoter_age_date <= later_date:
                raise ValueError(
                    "idf.promoter_age_date must be after later of idf.commutation_date and eligibility_date"
                )

        return self


class FixationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    calculation_id: str | None = None
    calculation_version: str
    eligibility_date: date
    eligibility_year: int
    monthly_cap: float
    exemption_percentage: float
    capital_multiplier: float
    grant_impact_multiplier: float
    grants: list[GrantInput]
    future_grant_reserved: float
    actual_capitalizations: list[ActualCapitalizationInput]
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

    @field_validator("grant_impact_multiplier")
    @classmethod
    def validate_grant_impact_multiplier(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("grant_impact_multiplier must be > 0")
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

        if self.idf is not None:
            later_date = max(self.idf.commutation_date, self.eligibility_date)
            if self.idf.promoter_age_date <= later_date:
                raise ValueError(
                    "idf.promoter_age_date must be after later of idf.commutation_date and eligibility_date"
                )

        return self


class GrantResult(BaseModel):
    grant_id: str
    client_id: int | None = None
    employer_name: str | None = None
    employer_withholding_file_number: str | None = None
    employment_start_date: date | None = None
    employment_end_date: date | None = None
    grant_receipt_date: date | None = None
    exempt_grant_amount: Decimal | None = None
    indexed_amount: Decimal
    limited_indexed_amount: Decimal
    impact_amount: Decimal
    exclusion_reason: str | None
    years_difference: float | None = None
    relevant: bool | None = None
    window_start: date | None = None
    total_employment_days: int | None = None
    overlap_start: date | None = None
    overlap_end: date | None = None
    overlap_days: int | None = None
    ratio: Decimal | None = None
    formula_contract_version: str | None = None
    parameter_set_id: str | None = None
    cbs_request_evidence: dict[str, Any] | None = None
    cbs_response_evidence: dict[str, Any] | None = None

    @field_validator("grant_id")
    @classmethod
    def validate_grant_result_id(cls, value: str) -> str:
        return _require_non_empty(value, "grant_id")

    @field_validator("indexed_amount", "limited_indexed_amount", "impact_amount")
    @classmethod
    def validate_grant_result_amounts(cls, value: Decimal) -> Decimal:
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

LEGACY_AUDIT_CATEGORY_MAP: dict[str, AuditCategory] = {
    "input_validation": "initial_entitlement",
    "grant_impact": "grant",
    "15_year_exclusion": "grant",
    "32_year_ratio": "grant",
    "idf_treatment": "idf",
    "total_impact": "total",
    "exempt_pension": "remaining_exemption",
}


class AuditRow(BaseModel):
    row_id: str
    category: AuditCategory
    source_id: str | None
    label: str
    input_amount: float | None
    output_amount: float
    impact_amount: float
    details: dict[str, Any]

    @field_validator("category", mode="before")
    @classmethod
    def normalize_internal_category(cls, value: str) -> str:
        return LEGACY_AUDIT_CATEGORY_MAP.get(value, value)

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

    @model_validator(mode="after")
    def validate_audit_dependencies(self) -> "AuditRow":
        requires_source_id = {"actual_capitalization", "idf"}
        if self.category in requires_source_id and not self.source_id:
            raise ValueError("source_id is required for actual_capitalization and idf categories")

        input_required_categories = {"future_grant_reserve", "actual_capitalization", "idf"}
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


class FixationValidationErrors(RootModel[list[ValidationError]]):
    root: list[ValidationError]

    @model_validator(mode="after")
    def validate_non_empty(self) -> "FixationValidationErrors":
        if not self.root:
            raise ValueError("validation failure output must contain at least one ValidationError")
        return self


class FixationResult(BaseModel):
    calculation_id: str | None = None
    calculation_version: str | None = None
    status: Literal[
        "success",
        "validation_failed",
        "unsupported",
        "requires_special_handling",
        "calculation_failed",
        "unsupported_calculation",
    ]
    validation_errors: list[ValidationError]
    m07_resolution: CalculationInputResolutionResult | None = None
    eligibility_date: date | None = None
    eligibility_year: int | None = None
    monthly_cap: float | None = None
    exemption_percentage: float | None = None
    capital_multiplier: float | None = None
    initial_exempt_capital: float | None = None
    grant_impact_total: Decimal | None = None
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
    grant_offset_handoff: dict[str, Any] | None = None
    actual_capitalization_results: list[ActualCapitalizationResult] | None = None
    idf_result: IDFResult | None = None
    audit_rows: list[AuditRow] | None = None

    @model_serializer(mode="wrap")
    def serialize_result(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        serialized = handler(self)
        if self.status != "success":
            allowed_fields = {
                "calculation_id",
                "calculation_version",
                "status",
                "validation_errors",
                "m07_resolution",
            }
            return {
                key: value
                for key, value in serialized.items()
                if key in allowed_fields and (value is not None or key in {"status", "validation_errors"})
            }
        serialized.pop("m07_resolution", None)
        return serialized

    @model_validator(mode="after")
    def validate_status_behavior(self) -> "FixationResult":
        if self.status != "success":
            if not self.validation_errors:
                raise ValueError("validation_errors must be present when status is not success")

            forbidden_failure_fields = (
                "initial_exempt_capital",
                "grant_impact_total",
                "future_grant_impact",
                "actual_capitalization_impact",
                "idf_impact",
                "total_impact",
                "remaining_exempt_capital",
                "monthly_exempt_pension",
                "capital_exemption_percentage",
                "pension_exemption_percentage",
                "grant_results",
                "grant_offset_handoff",
                "actual_capitalization_results",
                "idf_result",
                "audit_rows",
            )
            for field_name in forbidden_failure_fields:
                if getattr(self, field_name) is not None:
                    raise ValueError(f"{field_name} must be omitted when status is not success")
            return self

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

        return self
