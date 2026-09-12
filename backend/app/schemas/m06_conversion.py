from __future__ import annotations

from datetime import date, datetime
import re
from typing import Any, Literal

from pydantic import BaseModel


DECIMAL_PATTERN = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")
Mode = Literal["balance_to_monthly_pension", "monthly_pension_to_capital_equivalent"]
Authority = Literal["documentary", "planner_declared"]


class M06CoefficientResponse(BaseModel):
    evidence_id: str
    authority_class: Authority
    coefficient: str
    decimal_precision: int
    decimal_exponent: int
    source_intake_id: str | None
    source_locator: str | None
    source_note: str | None
    reason: str
    effective_from: date | None
    effective_to: date | None
    applicability_declared: bool
    metadata: dict[str, Any]
    actor: str
    actor_is_authentication: Literal[False] = False
    created_at: datetime


class M06ManifestResponse(BaseModel):
    manifest_id: str
    fingerprint: str
    raw_result_kind: str | None
    raw_decimal: str | None
    raw_numerator: str | None
    raw_denominator: str | None
    display_result: str | None
    authoritative_monthly_amount: str | None
    evidence: dict[str, Any]


class M06RevisionResponse(BaseModel):
    revision_id: str
    subject_id: str
    predecessor_revision_id: str | None
    revision_sequence: int
    state: Literal["draft", "resolved", "warning_reviewed", "blocked", "superseded"]
    action_type: str
    mode: Mode
    formula_id: str
    input_identity: str
    input_amount: str | None
    input_date: date | None
    predecessor_snapshot: dict[str, Any]
    warnings: list[dict[str, Any]]
    blocking_reasons: list[str]
    informational_warnings: list[str]
    coefficient: M06CoefficientResponse
    manifest: M06ManifestResponse | None
    warning_dispositions: list[dict[str, Any]]
    actor: str
    actor_is_authentication: Literal[False] = False
    created_at: datetime


class M06EligibilityResponse(BaseModel):
    subject_id: str
    assessed_revision_id: str
    eligible_for_downstream: bool
    current_revision_id: str | None
    exclusion_reasons: list[str]
    informational_warnings: list[str]
    meaning: Literal["technically eligible under the bounded PKG-011 M06 contract"] = (
        "technically eligible under the bounded PKG-011 M06 contract"
    )


class M06SubjectResponse(BaseModel):
    subject_id: str
    client_id: int
    m05_subject_id: str
    mode: Mode
    input_identity: str
    current_revision: M06RevisionResponse | None
    eligibility: M06EligibilityResponse
