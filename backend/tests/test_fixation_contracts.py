from decimal import Decimal

import pytest
from pydantic import ValidationError as PydanticValidationError

from app.schemas.fixation_contracts import (
    AuditRow,
    FixationInput,
    FixationInputReview,
    FixationResult,
    FixationValidationErrors,
    GLOBAL_INPUT_PATH,
    IDFResult,
    ValidationError,
    map_contract_validation_errors,
    validation_code_from_error,
    validation_path_from_loc,
)
from app.schemas.fixation_review import (
    FixationReviewConversionError,
    convert_review_to_fixation_input,
)


def valid_fixation_input_payload() -> dict:
    return {
        "calculation_id": "calc-1",
        "calculation_version": "v1",
        "eligibility_date": "2025-01-01",
        "eligibility_year": 2025,
        "monthly_cap": 9430,
        "exemption_percentage": 0.57,
        "capital_multiplier": 180,
        "grant_impact_multiplier": 1.35,
        "grants": [
            {
                "grant_id": "G1",
                "employer_name": "Employer",
                "nominal_amount": 100000,
                "indexed_amount": 100000,
                "grant_date": "2024-01-01",
                "work_start_date": "2020-01-01",
                "work_end_date": "2021-01-01",
            }
        ],
        "future_grant_reserved": 0,
        "actual_capitalizations": [
            {
                "capitalization_id": "C1",
                "amount": 1000,
                "capitalization_date": "2023-01-01",
                "source_label": "source",
            }
        ],
        "idf": {
            "idf_id": "I1",
            "reduction_amount": 1000,
            "original_commutation_percent": 25,
            "current_commutation_percent": 20,
            "commutation_date": "2025-01-01",
            "promoter_age_date": "2026-01-01",
            "source_label": "idf-source",
        },
        "metadata": {"trace": "x"},
    }


def valid_success_result_payload() -> dict:
    return {
        "calculation_id": "calc-1",
        "calculation_version": "v1",
        "status": "success",
        "validation_errors": [],
        "eligibility_date": "2025-01-01",
        "eligibility_year": 2025,
        "monthly_cap": 9430,
        "exemption_percentage": 0.57,
        "capital_multiplier": 180,
        "initial_exempt_capital": 1000,
        "grant_impact_total": 0,
        "future_grant_reserved": 0,
        "future_grant_impact": 0,
        "actual_capitalization_impact": 0,
        "idf_impact": 0,
        "total_impact": 0,
        "remaining_exempt_capital": 1000,
        "monthly_exempt_pension": 5.56,
        "capital_exemption_percentage": 1,
        "pension_exemption_percentage": 0.57,
        "grant_results": [],
        "actual_capitalization_results": [],
        "idf_result": None,
        "audit_rows": [
            {
                "row_id": "R1",
                "category": "total",
                "source_id": None,
                "label": "Total",
                "input_amount": None,
                "output_amount": 0,
                "impact_amount": 0,
                "details": {"x": 1},
            }
        ],
    }


def valid_fixation_review_payload() -> dict:
    payload = valid_fixation_input_payload()
    payload["grants"] = {
        "collection_state": "items_recorded",
        "items": [
            {
                **payload["grants"][0],
                "source_item_id": "GR-1",
                "disposition": "include",
            }
        ],
    }
    payload["actual_capitalizations"] = {
        "collection_state": "items_recorded",
        "items": [
            {
                **payload["actual_capitalizations"][0],
                "source_item_id": "AC-1",
                "source_basis": "capitalization certificate",
                "planner_assertion": "advisor confirmed amount",
                "planner_assertion_basis": "reviewed certificate",
                "disposition": "include",
            }
        ],
    }
    return payload


@pytest.mark.parametrize("state", ["unknown", "not_collected", "confirmed_none"])
def test_fixation_review_empty_non_item_states_are_structurally_accepted(state: str) -> None:
    payload = valid_fixation_review_payload()
    payload["grants"] = {"collection_state": state, "items": []}
    payload["actual_capitalizations"] = {"collection_state": state, "items": []}

    review = FixationInputReview(**payload)

    assert review.grants.collection_state == state
    assert review.grants.items == []
    assert review.actual_capitalizations.collection_state == state
    assert review.actual_capitalizations.items == []


def test_fixation_review_items_recorded_with_explicit_dispositions_is_structurally_accepted() -> None:
    review = FixationInputReview(**valid_fixation_review_payload())

    assert review.grants.items[0].source_item_id == "GR-1"
    assert review.grants.items[0].disposition == "include"
    assert review.actual_capitalizations.items[0].source_item_id == "AC-1"
    assert review.actual_capitalizations.items[0].disposition == "include"


@pytest.mark.parametrize("state", ["unknown", "not_collected", "confirmed_none"])
def test_fixation_review_non_item_states_reject_items_with_stable_error(state: str) -> None:
    payload = valid_fixation_review_payload()
    payload["grants"]["collection_state"] = state

    with pytest.raises(PydanticValidationError) as exc_info:
        FixationInputReview(**payload)

    errors = map_contract_validation_errors(exc_info.value)
    assert errors[0].path == "grants"
    assert errors[0].code == "UNSUPPORTED_OR_UNAPPROVED_VALUE"


def test_fixation_review_items_recorded_rejects_empty_items_with_stable_error() -> None:
    payload = valid_fixation_review_payload()
    payload["actual_capitalizations"] = {"collection_state": "items_recorded", "items": []}

    with pytest.raises(PydanticValidationError) as exc_info:
        FixationInputReview(**payload)

    errors = map_contract_validation_errors(exc_info.value)
    assert errors[0].path == "actual_capitalizations"
    assert errors[0].code == "UNSUPPORTED_OR_UNAPPROVED_VALUE"


def test_fixation_review_item_without_disposition_is_rejected() -> None:
    payload = valid_fixation_review_payload()
    del payload["grants"]["items"][0]["disposition"]

    with pytest.raises(PydanticValidationError) as exc_info:
        FixationInputReview(**payload)

    errors = map_contract_validation_errors(exc_info.value)
    assert errors[0].path == "grants.items[0].disposition"
    assert errors[0].code == "MISSING_REQUIRED_VALUE"


def test_fixation_review_item_unsupported_disposition_is_rejected() -> None:
    payload = valid_fixation_review_payload()
    payload["grants"]["items"][0]["disposition"] = "auto_include"

    with pytest.raises(PydanticValidationError) as exc_info:
        FixationInputReview(**payload)

    errors = map_contract_validation_errors(exc_info.value)
    assert errors[0].path == "grants.items[0].disposition"
    assert errors[0].code == "UNSUPPORTED_OR_UNAPPROVED_VALUE"


@pytest.mark.parametrize(
    ("source_item_id", "expected_code"),
    [
        (None, "MISSING_REQUIRED_VALUE"),
        ("   ", "INVALID_NESTED_ITEM"),
        ("bad/source", "INVALID_NESTED_ITEM"),
    ],
)
def test_fixation_review_source_item_id_is_required_and_stable(
    source_item_id: str | None,
    expected_code: str,
) -> None:
    payload = valid_fixation_review_payload()
    if source_item_id is None:
        del payload["actual_capitalizations"]["items"][0]["source_item_id"]
    else:
        payload["actual_capitalizations"]["items"][0]["source_item_id"] = source_item_id

    with pytest.raises(PydanticValidationError) as exc_info:
        FixationInputReview(**payload)

    errors = map_contract_validation_errors(exc_info.value)
    assert errors[0].path == "actual_capitalizations.items[0].source_item_id"
    assert errors[0].code == expected_code


def test_fixation_review_structural_parsing_does_not_infer_readiness_or_zero() -> None:
    payload = valid_fixation_review_payload()
    payload["grants"] = {"collection_state": "unknown", "items": []}
    payload["actual_capitalizations"] = {"collection_state": "not_collected", "items": []}

    review = FixationInputReview(**payload)

    assert review.grants.collection_state == "unknown"
    assert review.grants.items == []
    assert review.actual_capitalizations.collection_state == "not_collected"
    assert review.actual_capitalizations.items == []
    with pytest.raises(FixationReviewConversionError):
        convert_review_to_fixation_input(review)


def test_fixation_review_converter_includes_only_included_items_and_omits_review_fields() -> None:
    payload = valid_fixation_review_payload()
    payload["grants"]["items"].append(
        {
            **payload["grants"]["items"][0],
            "source_item_id": "GR-2",
            "grant_id": "G2",
            "disposition": "exclude",
        }
    )
    payload["actual_capitalizations"]["items"].append(
        {
            **payload["actual_capitalizations"]["items"][0],
            "source_item_id": "AC-2",
            "capitalization_id": "C2",
            "amount": 250,
            "disposition": "exclude",
        }
    )
    review = FixationInputReview(**payload)

    converted = convert_review_to_fixation_input(review)
    dumped = converted.model_dump(mode="json")

    assert isinstance(converted, FixationInput)
    assert [grant["grant_id"] for grant in dumped["grants"]] == ["G1"]
    assert [cap["capitalization_id"] for cap in dumped["actual_capitalizations"]] == ["C1"]
    assert Decimal(dumped["grants"][0]["indexed_amount"]) == Decimal(
        str(payload["grants"]["items"][0]["indexed_amount"])
    )
    assert dumped["actual_capitalizations"][0]["amount"] == payload["actual_capitalizations"]["items"][0]["amount"]
    assert "source_item_id" not in dumped["grants"][0]
    assert "disposition" not in dumped["grants"][0]
    assert "collection_state" not in dumped["grants"][0]
    assert "source_item_id" not in dumped["actual_capitalizations"][0]
    assert "disposition" not in dumped["actual_capitalizations"][0]
    assert "source_basis" not in dumped["actual_capitalizations"][0]
    assert "planner_assertion" not in dumped["actual_capitalizations"][0]
    assert "planner_assertion_basis" not in dumped["actual_capitalizations"][0]


@pytest.mark.parametrize("state", ["unknown", "not_collected"])
def test_fixation_review_converter_refuses_blocking_states(state: str) -> None:
    payload = valid_fixation_review_payload()
    payload["grants"] = {"collection_state": state, "items": []}

    with pytest.raises(FixationReviewConversionError):
        convert_review_to_fixation_input(FixationInputReview(**payload))


def test_fixation_review_converter_permits_empty_collections_only_for_confirmed_none() -> None:
    payload = valid_fixation_review_payload()
    payload["grants"] = {"collection_state": "confirmed_none", "items": []}
    payload["actual_capitalizations"] = {"collection_state": "confirmed_none", "items": []}

    converted = convert_review_to_fixation_input(FixationInputReview(**payload))

    assert converted.grants == []
    assert converted.actual_capitalizations == []


def test_fixation_review_converter_treats_all_excluded_items_as_reviewed_zero() -> None:
    payload = valid_fixation_review_payload()
    payload["grants"]["items"][0]["disposition"] = "exclude"

    converted = convert_review_to_fixation_input(FixationInputReview(**payload))

    assert converted.grants == []


def test_missing_required_calculation_version_fails() -> None:
    payload = valid_fixation_input_payload()
    del payload["calculation_version"]

    with pytest.raises(PydanticValidationError):
        FixationInput(**payload)


def test_missing_monthly_cap_fails() -> None:
    payload = valid_fixation_input_payload()
    del payload["monthly_cap"]

    with pytest.raises(PydanticValidationError):
        FixationInput(**payload)


def test_missing_indexed_amount_fails() -> None:
    payload = valid_fixation_input_payload()
    del payload["grants"][0]["indexed_amount"]

    with pytest.raises(PydanticValidationError):
        FixationInput(**payload)


def test_missing_idf_field_fails() -> None:
    payload = valid_fixation_input_payload()
    del payload["idf"]

    with pytest.raises(PydanticValidationError):
        FixationInput(**payload)


def test_idf_null_means_not_applicable() -> None:
    payload = valid_fixation_input_payload()
    payload["idf"] = None

    parsed = FixationInput(**payload)

    assert parsed.idf is None


def test_idf_relevant_marker_is_rejected() -> None:
    payload = valid_fixation_input_payload()
    payload["idf_relevant"] = False

    with pytest.raises(PydanticValidationError):
        FixationInput(**payload)


@pytest.mark.parametrize(
    "path,value",
    [
        (("eligibility_date",), "not-a-date"),
        (("grants", 0, "grant_date"), "not-a-date"),
        (("actual_capitalizations", 0, "capitalization_date"), "not-a-date"),
        (("idf", "commutation_date"), "not-a-date"),
    ],
)
def test_invalid_dates_fail(path: tuple, value: str) -> None:
    payload = valid_fixation_input_payload()
    target = payload
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value

    with pytest.raises(PydanticValidationError):
        FixationInput(**payload)


@pytest.mark.parametrize(
    "path,value",
    [
        (("monthly_cap",), 0),
        (("monthly_cap",), -1),
        (("exemption_percentage",), -0.1),
        (("exemption_percentage",), 1.1),
        (("capital_multiplier",), 0),
        (("capital_multiplier",), -1),
        (("indexed_amount",), -1),
        (("future_grant_reserved",), -1),
        (("amount",), -1),
        (("reduction_amount",), 0),
        (("reduction_amount",), -1),
    ],
)
def test_invalid_numeric_values_fail(path: tuple, value: float) -> None:
    payload = valid_fixation_input_payload()
    if path[0] == "indexed_amount":
        payload["grants"][0]["indexed_amount"] = value
    elif path[0] == "amount":
        payload["actual_capitalizations"][0]["amount"] = value
    elif path[0] == "reduction_amount":
        payload["idf"]["reduction_amount"] = value
    else:
        payload[path[0]] = value

    with pytest.raises(PydanticValidationError):
        FixationInput(**payload)


def test_empty_grant_id_fails() -> None:
    payload = valid_fixation_input_payload()
    payload["grants"][0]["grant_id"] = "   "

    with pytest.raises(PydanticValidationError):
        FixationInput(**payload)


def test_empty_employer_name_when_present_fails() -> None:
    payload = valid_fixation_input_payload()
    payload["grants"][0]["employer_name"] = "   "

    with pytest.raises(PydanticValidationError):
        FixationInput(**payload)


def test_work_start_date_not_before_work_end_date_fails() -> None:
    payload = valid_fixation_input_payload()
    payload["grants"][0]["work_start_date"] = "2021-01-01"
    payload["grants"][0]["work_end_date"] = "2021-01-01"

    with pytest.raises(PydanticValidationError):
        FixationInput(**payload)


def test_work_start_date_after_work_end_date_fails() -> None:
    payload = valid_fixation_input_payload()
    payload["grants"][0]["work_start_date"] = "2021-01-02"
    payload["grants"][0]["work_end_date"] = "2021-01-01"

    with pytest.raises(PydanticValidationError):
        FixationInput(**payload)


def test_nominal_present_indexed_missing_fails() -> None:
    payload = valid_fixation_input_payload()
    payload["grants"][0]["nominal_amount"] = 100
    del payload["grants"][0]["indexed_amount"]

    with pytest.raises(PydanticValidationError):
        FixationInput(**payload)


def test_empty_capitalization_id_fails() -> None:
    payload = valid_fixation_input_payload()
    payload["actual_capitalizations"][0]["capitalization_id"] = ""

    with pytest.raises(PydanticValidationError):
        FixationInput(**payload)


def test_empty_source_label_when_present_fails() -> None:
    payload = valid_fixation_input_payload()
    payload["actual_capitalizations"][0]["source_label"] = "   "

    with pytest.raises(PydanticValidationError):
        FixationInput(**payload)


def test_empty_idf_id_fails() -> None:
    payload = valid_fixation_input_payload()
    payload["idf"]["idf_id"] = " "

    with pytest.raises(PydanticValidationError):
        FixationInput(**payload)


def test_idf_decimal_percent_format_fails() -> None:
    payload = valid_fixation_input_payload()
    payload["idf"]["original_commutation_percent"] = 0.25

    with pytest.raises(PydanticValidationError):
        FixationInput(**payload)


def test_idf_promoter_age_date_not_after_later_date_fails() -> None:
    payload = valid_fixation_input_payload()
    payload["idf"]["commutation_date"] = "2025-02-01"
    payload["idf"]["promoter_age_date"] = "2025-02-01"

    with pytest.raises(PydanticValidationError):
        FixationInput(**payload)


def test_idf_promoter_age_date_before_later_date_fails() -> None:
    payload = valid_fixation_input_payload()
    payload["idf"]["commutation_date"] = "2025-02-01"
    payload["idf"]["promoter_age_date"] = "2025-01-15"

    with pytest.raises(PydanticValidationError):
        FixationInput(**payload)


def test_idf_null_passes_when_not_relevant() -> None:
    payload = valid_fixation_input_payload()
    payload["idf"] = None

    parsed = FixationInput(**payload)

    assert parsed.idf is None


def test_audit_row_invalid_category_fails() -> None:
    with pytest.raises(PydanticValidationError):
        AuditRow(
            row_id="R1",
            category="bad-category",
            source_id=None,
            label="Bad",
            input_amount=None,
            output_amount=0,
            impact_amount=0,
            details={},
        )


@pytest.mark.parametrize(
    ("category", "source_id", "input_amount"),
    [
        ("initial_entitlement", None, None),
        ("grant", "G1", 100.0),
        ("future_grant_reserve", None, 100.0),
        ("actual_capitalization", "C1", 100.0),
        ("idf", "I1", 100.0),
        ("total", None, None),
        ("remaining_exemption", None, None),
    ],
)
def test_audit_row_approved_categories_are_supported(
    category: str,
    source_id: str | None,
    input_amount: float | None,
) -> None:
    parsed = AuditRow(
        row_id="R1",
        category=category,
        source_id=source_id,
        label="Label",
        input_amount=input_amount,
        output_amount=0,
        impact_amount=0,
        details={},
    )

    assert parsed.category == category


@pytest.mark.parametrize("category", ["actual_capitalization", "idf"])
def test_audit_row_missing_source_id_for_required_categories_fails(category: str) -> None:
    with pytest.raises(PydanticValidationError):
        AuditRow(
            row_id="R1",
            category=category,
            source_id=None,
            label="Label",
            input_amount=100,
            output_amount=100,
            impact_amount=10,
            details={},
        )


@pytest.mark.parametrize("category", ["future_grant_reserve", "actual_capitalization", "idf"])
def test_audit_row_missing_input_amount_for_required_categories_fails(category: str) -> None:
    source_id = "SRC1" if category in {"actual_capitalization", "idf"} else None

    with pytest.raises(PydanticValidationError):
        AuditRow(
            row_id="R1",
            category=category,
            source_id=source_id,
            label="Label",
            input_amount=None,
            output_amount=100,
            impact_amount=10,
            details={},
        )


def test_audit_row_negative_impact_fails() -> None:
    with pytest.raises(PydanticValidationError):
        AuditRow(
            row_id="R1",
            category="total",
            source_id=None,
            label="Total",
            input_amount=None,
            output_amount=0,
            impact_amount=-1,
            details={},
        )


def test_audit_row_does_not_require_or_expose_stage_order() -> None:
    parsed = AuditRow(
        row_id="R1",
        category="total",
        source_id=None,
        label="Total",
        input_amount=None,
        output_amount=0,
        impact_amount=0,
        details={},
    )

    assert "stage_order" not in parsed.model_dump()


def test_validation_error_invalid_severity_fails() -> None:
    with pytest.raises(PydanticValidationError):
        ValidationError(code="INVALID_GLOBAL_INPUT", path="x", message="m", severity="warning", source_id=None)


def test_validation_error_null_source_id_allowed() -> None:
    parsed = ValidationError(code="INVALID_GLOBAL_INPUT", path="x", message="m", severity="error", source_id=None)

    assert parsed.source_id is None


def test_fixation_validation_errors_output_accepts_non_empty_validation_error_list() -> None:
    parsed = FixationValidationErrors(
        root=[
            ValidationError(
                code="MISSING_REQUIRED_VALUE",
                path="monthly_cap",
                message="monthly_cap is required",
                severity="error",
                source_id=None,
            )
        ]
    )

    assert len(parsed.root) == 1


def test_fixation_validation_errors_output_rejects_empty_list() -> None:
    with pytest.raises(PydanticValidationError):
        FixationValidationErrors(root=[])


def test_idf_result_overlap_months_zero_fails() -> None:
    with pytest.raises(PydanticValidationError):
        IDFResult(
            idf_id="I1",
            base_reduction=100.0,
            monthly_reduction_for_calc=35.0,
            overlap_months=0,
            impact_amount=0,
        )


@pytest.mark.parametrize(
    ("loc", "expected_path"),
    [
        ((), GLOBAL_INPUT_PATH),
        (("calculation_version",), "calculation_version"),
        (("idf", "commutation_date"), "idf.commutation_date"),
        (("grants", 0, "indexed_amount"), "grants[0].indexed_amount"),
        (("actual_capitalizations", 2, "amount"), "actual_capitalizations[2].amount"),
        (("__root__",), GLOBAL_INPUT_PATH),
    ],
)
def test_validation_path_from_loc_uses_approved_convention(loc: tuple[object, ...], expected_path: str) -> None:
    assert validation_path_from_loc(loc) == expected_path


@pytest.mark.parametrize(
    ("error_type", "path", "expected_code"),
    [
        ("missing", "monthly_cap", "MISSING_REQUIRED_VALUE"),
        ("date_from_datetime_parsing", "eligibility_date", "INVALID_DATE"),
        ("greater_than", "monthly_cap", "INVALID_NUMBER"),
        ("value_error", "grants[0].indexed_amount", "INVALID_NESTED_ITEM"),
        ("value_error", GLOBAL_INPUT_PATH, "INVALID_GLOBAL_INPUT"),
        ("literal_error", "status", "UNSUPPORTED_OR_UNAPPROVED_VALUE"),
    ],
)
def test_validation_code_from_error_maps_to_approved_categories(error_type: str, path: str, expected_code: str) -> None:
    assert validation_code_from_error(error_type, path) == expected_code


def test_map_contract_validation_errors_returns_stable_paths_and_codes() -> None:
    payload = valid_fixation_input_payload()
    del payload["grants"][0]["indexed_amount"]

    with pytest.raises(PydanticValidationError) as exc_info:
        FixationInput(**payload)

    mapped_errors = map_contract_validation_errors(exc_info.value)

    assert mapped_errors[0].code == "MISSING_REQUIRED_VALUE"
    assert mapped_errors[0].path == "grants[0].indexed_amount"
    assert mapped_errors[0].severity == "error"


def test_validation_error_legacy_code_is_normalized() -> None:
    parsed = ValidationError(
        code="ERR_REQUIRED_FIELD_MISSING",
        path="monthly_cap",
        message="monthly_cap is required",
        severity="error",
        source_id=None,
    )

    assert parsed.code == "MISSING_REQUIRED_VALUE"


def test_fixation_result_success_with_validation_errors_fails() -> None:
    payload = valid_success_result_payload()
    payload["validation_errors"] = [
        {
            "code": "INVALID_GLOBAL_INPUT",
            "path": "x",
            "message": "bad",
            "severity": "error",
            "source_id": None,
        }
    ]

    with pytest.raises(PydanticValidationError):
        FixationResult(**payload)


def test_fixation_result_success_missing_numeric_fields_fails() -> None:
    payload = valid_success_result_payload()
    del payload["initial_exempt_capital"]

    with pytest.raises(PydanticValidationError):
        FixationResult(**payload)


def test_fixation_result_validation_failed_status_uses_error_shape() -> None:
    payload = {
        "calculation_id": "calc-1",
        "calculation_version": "v1",
        "status": "validation_failed",
        "validation_errors": [
        {
            "code": "MISSING_REQUIRED_VALUE",
            "path": "monthly_cap",
            "message": "monthly_cap is required",
            "severity": "error",
            "source_id": None,
        }
        ],
    }

    parsed = FixationResult(**payload)

    assert parsed.status == "validation_failed"
    assert parsed.validation_errors[0].path == "monthly_cap"
    assert parsed.initial_exempt_capital is None
