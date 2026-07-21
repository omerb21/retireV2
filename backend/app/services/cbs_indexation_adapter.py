from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from app.schemas.cbs_indexation import (
    CBS_CALCULATOR_ENDPOINT,
    CBS_CPI_CODE,
    CbsIndexationFailure,
    CbsIndexationFailureEvidence,
    CbsIndexationOutcome,
    CbsIndexationRequestEvidence,
    CbsIndexationResponseEvidence,
    CbsIndexationSuccess,
    IndexationBaseDateSource,
)


CBS_CONNECT_TIMEOUT_SECONDS = 3.0
CBS_READ_TIMEOUT_SECONDS = 10.0
CBS_MAX_TRANSPORT_RETRIES = 1

_OPTIONAL_RESPONSE_FIELDS: dict[str, tuple[str, ...]] = {
    "from_index_period": ("from_index_period", "from_period"),
    "to_index_period": ("to_index_period", "to_period"),
    "from_index_value": ("from_index_value", "from_value"),
    "to_index_value": ("to_index_value",),
    "base_year": ("base_year",),
    "chaining_coefficient": ("chaining_coefficient", "coefficient"),
    "change_percentage": ("change_percentage", "change_percent"),
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _failure(
    *,
    category: str,
    timestamp: datetime,
    message: str,
    request: CbsIndexationRequestEvidence | None = None,
    http_status: int | None = None,
    timeout: bool = False,
    malformed: bool = False,
    missing_to_value: bool = False,
    outcome_status: str = "calculation_failed",
) -> CbsIndexationFailure:
    return CbsIndexationFailure(
        request=request,
        failure=CbsIndexationFailureEvidence(
            outcome_status=outcome_status,
            failure_category=category,
            http_status=http_status,
            timeout=timeout,
            malformed_response=malformed,
            missing_to_value=missing_to_value,
            calculation_timestamp=timestamp,
            safe_technical_message=message,
        ),
    )


def build_cbs_indexation_request(
    *,
    amount: Decimal,
    grant_date: date | None,
    work_end_date: date | None,
    eligibility_date: date,
    calculation_timestamp: datetime | None = None,
) -> CbsIndexationRequestEvidence | CbsIndexationFailure:
    timestamp = calculation_timestamp or _now()
    if amount <= 0:
        return _failure(
            category="unsupported_calculation",
            timestamp=timestamp,
            message="CBS calculator requires a positive linkage amount",
            outcome_status="unsupported_calculation",
        )
    resolved_base_date: date | None = grant_date or work_end_date
    base_date_source: IndexationBaseDateSource | None = (
        "grant_date" if grant_date is not None else "work_end_date" if work_end_date is not None else None
    )
    if resolved_base_date is None or base_date_source is None:
        return _failure(
            category="missing_base_date",
            timestamp=timestamp,
            message="CBS indexation requires grant_date or recorded work_end_date",
        )

    return CbsIndexationRequestEvidence(
        amount=amount,
        resolved_base_date=resolved_base_date,
        base_date_source=base_date_source,
        target_date=eligibility_date,
        calculation_timestamp=timestamp,
    )


def _first_present(payload: dict[str, Any], aliases: tuple[str, ...]) -> Any:
    for alias in aliases:
        if alias in payload:
            return payload[alias]
    return None


def _optional_decimal(payload: dict[str, Any], aliases: tuple[str, ...]) -> Decimal | None:
    value = _first_present(payload, aliases)
    if value is None:
        return None
    return Decimal(str(value))


def calculate_cbs_indexation(
    *,
    amount: Decimal,
    grant_date: date | None,
    work_end_date: date | None,
    eligibility_date: date,
    client: httpx.Client | None = None,
) -> CbsIndexationOutcome:
    request_or_failure = build_cbs_indexation_request(
        amount=amount,
        grant_date=grant_date,
        work_end_date=work_end_date,
        eligibility_date=eligibility_date,
    )
    if isinstance(request_or_failure, CbsIndexationFailure):
        return request_or_failure
    request = request_or_failure

    params = {
        "value": str(request.amount),
        "date": request.resolved_base_date.isoformat(),
        "toDate": request.target_date.isoformat(),
        "format": "json",
        "download": "false",
        "lang": "en",
    }
    owns_client = client is None
    http_client = client or httpx.Client(
        timeout=httpx.Timeout(
            connect=CBS_CONNECT_TIMEOUT_SECONDS,
            read=CBS_READ_TIMEOUT_SECONDS,
            write=CBS_READ_TIMEOUT_SECONDS,
            pool=CBS_CONNECT_TIMEOUT_SECONDS,
        )
    )
    response: httpx.Response | None = None
    try:
        for attempt in range(CBS_MAX_TRANSPORT_RETRIES + 1):
            try:
                response = http_client.get(CBS_CALCULATOR_ENDPOINT, params=params)
                break
            except httpx.TimeoutException:
                if attempt >= CBS_MAX_TRANSPORT_RETRIES:
                    return _failure(
                        category="timeout",
                        timestamp=request.calculation_timestamp,
                        message="CBS calculator request timed out",
                        request=request,
                        timeout=True,
                    )
            except httpx.TransportError:
                if attempt >= CBS_MAX_TRANSPORT_RETRIES:
                    return _failure(
                        category="transport_error",
                        timestamp=request.calculation_timestamp,
                        message="CBS calculator transport failed",
                        request=request,
                    )

        assert response is not None
        if not response.is_success:
            return _failure(
                category="http_error",
                timestamp=request.calculation_timestamp,
                message="CBS calculator returned a non-success HTTP status",
                request=request,
                http_status=response.status_code,
            )

        try:
            payload = response.json()
        except ValueError:
            return _failure(
                category="malformed_response",
                timestamp=request.calculation_timestamp,
                message="CBS calculator response was not valid JSON",
                request=request,
                http_status=response.status_code,
                malformed=True,
            )
        if not isinstance(payload, dict):
            return _failure(
                category="malformed_response",
                timestamp=request.calculation_timestamp,
                message="CBS calculator response must be an object",
                request=request,
                http_status=response.status_code,
                malformed=True,
            )
        answer = payload.get("answer")
        if not isinstance(answer, dict):
            return _failure(
                category="missing_answer",
                timestamp=request.calculation_timestamp,
                message="CBS calculator response did not contain an answer object",
                request=request,
                http_status=response.status_code,
                malformed=True,
            )
        if answer.get("to_value") is None:
            return _failure(
                category="missing_to_value",
                timestamp=request.calculation_timestamp,
                message="CBS calculator answer did not contain to_value",
                request=request,
                http_status=response.status_code,
                malformed=True,
                missing_to_value=True,
            )

        try:
            raw_to_value = Decimal(str(answer["to_value"]))
            optional_values = {
                "from_index_period": _first_present(answer, _OPTIONAL_RESPONSE_FIELDS["from_index_period"]),
                "to_index_period": _first_present(answer, _OPTIONAL_RESPONSE_FIELDS["to_index_period"]),
                "from_index_value": _optional_decimal(answer, _OPTIONAL_RESPONSE_FIELDS["from_index_value"]),
                "to_index_value": _optional_decimal(answer, _OPTIONAL_RESPONSE_FIELDS["to_index_value"]),
                "base_year": _first_present(answer, _OPTIONAL_RESPONSE_FIELDS["base_year"]),
                "chaining_coefficient": _optional_decimal(answer, _OPTIONAL_RESPONSE_FIELDS["chaining_coefficient"]),
                "change_percentage": _optional_decimal(answer, _OPTIONAL_RESPONSE_FIELDS["change_percentage"]),
            }
        except (InvalidOperation, TypeError, ValueError):
            return _failure(
                category="malformed_response",
                timestamp=request.calculation_timestamp,
                message="CBS calculator response contained an invalid numeric value",
                request=request,
                http_status=response.status_code,
                malformed=True,
            )

        missing_optional = [key for key, value in optional_values.items() if value is None]
        return CbsIndexationSuccess(
            request=request,
            response=CbsIndexationResponseEvidence(
                raw_to_value=raw_to_value,
                missing_optional_fields=missing_optional,
                calculation_timestamp=request.calculation_timestamp,
                response_status=response.status_code,
                cpi_code=CBS_CPI_CODE,
                endpoint=CBS_CALCULATOR_ENDPOINT,
                **optional_values,
            ),
        )
    finally:
        if owns_client:
            http_client.close()
