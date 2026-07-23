from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    event,
    inspect,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OfficialParameterSet(Base):
    __tablename__ = "official_parameter_sets"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'verified', 'active', 'superseded', 'rejected')",
            name="ck_official_parameter_sets_status",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_official_parameter_sets_effective_period",
        ),
        CheckConstraint(
            "monthly_cap > 0",
            name="ck_official_parameter_sets_monthly_cap_positive",
        ),
        CheckConstraint(
            "exemption_percentage >= 0 AND exemption_percentage <= 1",
            name="ck_official_parameter_sets_exemption_percentage_range",
        ),
        CheckConstraint(
            "capital_multiplier > 0",
            name="ck_official_parameter_sets_capital_multiplier_positive",
        ),
        CheckConstraint(
            "grant_impact_multiplier > 0",
            name="ck_official_parameter_sets_grant_impact_multiplier_positive",
        ),
        CheckConstraint(
            "status NOT IN ('verified', 'active', 'superseded') "
            "OR (verified_at IS NOT NULL AND verified_by IS NOT NULL)",
            name="ck_official_parameter_sets_verification_evidence",
        ),
        CheckConstraint(
            "status NOT IN ('active', 'superseded') "
            "OR (activated_at IS NOT NULL AND activated_by IS NOT NULL)",
            name="ck_official_parameter_sets_activation_evidence",
        ),
        CheckConstraint(
            "status != 'rejected' OR (rejected_at IS NOT NULL AND rejected_by IS NOT NULL)",
            name="ck_official_parameter_sets_rejection_evidence",
        ),
        CheckConstraint(
            "status != 'superseded' "
            "OR (superseded_at IS NOT NULL AND superseded_by IS NOT NULL)",
            name="ck_official_parameter_sets_supersession_evidence",
        ),
        UniqueConstraint(
            "tax_year",
            "parameter_set_version",
            name="uq_official_parameter_sets_year_version",
        ),
        Index(
            "ix_official_parameter_sets_resolution",
            "status",
            "tax_year",
            "effective_from",
            "effective_to",
        ),
    )

    parameter_set_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tax_year: Mapped[int] = mapped_column(Integer, nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    parameter_set_version: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)

    monthly_cap: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    exemption_percentage: Mapped[Decimal] = mapped_column(Numeric(18, 10), nullable=False)
    capital_multiplier: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    grant_impact_multiplier: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)

    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_title: Mapped[str] = mapped_column(String(512), nullable=False)
    official_source_reference: Mapped[str] = mapped_column(String(2048), nullable=False)
    source_publication_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_evidence_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    verification_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    parameter_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    content_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    fingerprint_algorithm_version: Mapped[str] = mapped_column(String(64), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activated_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    rejection_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    superseded_by: Mapped[str | None] = mapped_column(String(128), nullable=True)


_ACTIVE_IMMUTABLE_FIELDS = (
    "tax_year",
    "effective_from",
    "effective_to",
    "schema_version",
    "parameter_set_version",
    "monthly_cap",
    "exemption_percentage",
    "capital_multiplier",
    "grant_impact_multiplier",
    "source_type",
    "source_title",
    "official_source_reference",
    "source_publication_date",
    "source_recorded_at",
    "source_evidence_metadata",
    "verification_note",
    "parameter_payload",
    "content_fingerprint",
    "fingerprint_algorithm_version",
)


@event.listens_for(OfficialParameterSet, "before_update")
def _protect_active_official_parameter_set(_mapper, _connection, target: OfficialParameterSet) -> None:
    state = inspect(target)
    status_history = state.attrs.status.history
    previous_status = status_history.deleted[0] if status_history.deleted else target.status
    if previous_status != "active":
        return
    changed_fields = [
        field_name
        for field_name in _ACTIVE_IMMUTABLE_FIELDS
        if state.attrs[field_name].history.has_changes()
    ]
    if changed_fields:
        raise ValueError(
            "active official parameter-set content is immutable; create a new revision"
        )
    if target.status not in {"active", "superseded"}:
        raise ValueError("active official parameter sets may only remain active or be superseded")
