from __future__ import annotations

from app.schemas.fixation_contracts import (
    ActualCapitalizationReviewDomain,
    FixationInput,
    FixationInputReview,
    GrantReviewDomain,
    ValidationError,
)


BLOCKING_REVIEW_STATES = {"unknown", "not_collected"}


class FixationReviewConversionError(ValueError):
    pass


def review_readiness_errors(review: FixationInputReview) -> list[ValidationError]:
    errors: list[ValidationError] = []
    for path, domain in (
        ("grants", review.grants),
        ("actual_capitalizations", review.actual_capitalizations),
    ):
        if domain.collection_state in BLOCKING_REVIEW_STATES:
            errors.append(
                ValidationError(
                    code="UNSUPPORTED_OR_UNAPPROVED_VALUE",
                    path=f"{path}.collection_state",
                    message=(
                        f"{path} collection_state '{domain.collection_state}' blocks calculation "
                        "until source facts are explicitly reviewed"
                    ),
                    severity="error",
                    source_id=None,
                )
            )
    return errors


def _convert_grants(domain: GrantReviewDomain) -> list[dict]:
    if domain.collection_state == "confirmed_none":
        return []

    included = [
        {
            "grant_id": item.grant_id,
            "employer_name": item.employer_name,
            "nominal_amount": item.nominal_amount,
            "indexed_amount": item.indexed_amount,
            "grant_date": item.grant_date,
            "work_start_date": item.work_start_date,
            "work_end_date": item.work_end_date,
        }
        for item in domain.items
        if item.disposition == "include"
    ]
    if not included:
        raise FixationReviewConversionError("grants conversion produced no included items")
    return included


def _convert_actual_capitalizations(domain: ActualCapitalizationReviewDomain) -> list[dict]:
    if domain.collection_state == "confirmed_none":
        return []

    included = [
        {
            "capitalization_id": item.capitalization_id,
            "amount": item.amount,
            "capitalization_date": item.capitalization_date,
            "source_label": item.source_label,
            "notes": item.notes,
        }
        for item in domain.items
        if item.disposition == "include"
    ]
    if not included:
        raise FixationReviewConversionError("actual_capitalizations conversion produced no included items")
    return included


def convert_review_to_fixation_input(review: FixationInputReview) -> FixationInput:
    errors = review_readiness_errors(review)
    if errors:
        raise FixationReviewConversionError("review contains calculation-blocking collection_state values")

    payload = {
        "calculation_id": review.calculation_id,
        "calculation_version": review.calculation_version,
        "eligibility_date": review.eligibility_date,
        "eligibility_year": review.eligibility_year,
        "monthly_cap": review.monthly_cap,
        "exemption_percentage": review.exemption_percentage,
        "capital_multiplier": review.capital_multiplier,
        "grants": _convert_grants(review.grants),
        "future_grant_reserved": review.future_grant_reserved,
        "actual_capitalizations": _convert_actual_capitalizations(review.actual_capitalizations),
        "idf": review.idf,
        "metadata": review.metadata,
    }
    return FixationInput(**payload)
