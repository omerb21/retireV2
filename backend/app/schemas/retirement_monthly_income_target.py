from typing import Literal

from pydantic import BaseModel, ConfigDict, StrictInt, StrictStr


class RetirementMonthlyIncomeTargetCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    client_id: StrictInt
    expected_record_version: StrictInt
    expected_planning_calculation_input_fingerprint: StrictStr
    expected_retirement_target_date: StrictStr
    monthly_amount: StrictStr
    income_basis: Literal["GROSS", "NET"]
    price_basis: Literal["NOMINAL_AT_RETIREMENT_TARGET_DATE", "REAL_AT_REFERENCE_DATE"]
    price_reference_date: StrictStr | None
    source_kind: Literal[
        "CLIENT_SUPPLIED", "PLANNER_SUPPLIED", "CLIENT_SUPPLIED_PLANNER_CONFIRMED"
    ]


class RetirementMonthlyIncomeTargetResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal["CANONICAL_RETIREMENT_MONTHLY_INCOME_TARGET_AUTHORITY_RESULT_V1"]
    client_id: int | None
    planning_calculation_input_fingerprint: str | None
    retirement_target_date: str | None
    target: dict | None
    authority: dict | None
    authority_state: Literal["UNAVAILABLE", "AMBIGUOUS", "MISSING", "INVALID", "STALE", "CURRENT"]
    target_readiness_state: Literal["READY", "NOT_READY"]
    target_ready: bool
    blockers: list[str]
    target_semantic_fingerprint: str | None
    target_result_fingerprint: str
