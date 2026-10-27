"""Stage 6 P1B append-only professional factor admissions.

A row documents a specific planner acknowledgment. It never by itself
authorizes PTE execution or a pension conversion.
"""
from datetime import datetime
from sqlalchemy import (
    CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text,
    UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class ScenarioPensionFactorAdmission(Base):
    __tablename__ = "scenario_pension_factor_admissions"
    __table_args__ = (
        UniqueConstraint("client_id", "scenario_id", "decision_id", "admission_revision",
                         name="uq_s6_factor_admission_revision"),
        Index("ix_s6_factor_admission_current", "client_id", "scenario_id",
              "decision_id", "admission_revision"),
        CheckConstraint("scenario_version > 0", name="ck_s6_factor_scenario_version"),
        CheckConstraint("admission_revision > 0", name="ck_s6_factor_revision"),
        CheckConstraint("length(actor_id) BETWEEN 1 AND 128",
                        name="ck_s6_factor_actor"),
        CheckConstraint("length(record_fingerprint) = 64",
                        name="ck_s6_factor_fingerprint_length"),
        CheckConstraint("length(permission_admission_fingerprint) = 64",
                        name="ck_s6_factor_permission_fingerprint_length"),
        CheckConstraint("length(manifest_fingerprint) = 64",
                        name="ck_s6_factor_manifest_fingerprint_length"),
        CheckConstraint("length(source_fingerprint) = 64",
                        name="ck_s6_factor_source_fingerprint_length"),
        CheckConstraint("length(election_fingerprint) = 64",
                        name="ck_s6_factor_election_fingerprint_length"),
    )

    admission_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.client_id", ondelete="RESTRICT"), nullable=False)
    scenario_id: Mapped[str] = mapped_column(
        ForeignKey("scenario_drafts.scenario_id", ondelete="RESTRICT"),
        nullable=False, index=True)
    decision_id: Mapped[str] = mapped_column(String(64), nullable=False)
    scenario_version: Mapped[int] = mapped_column(Integer, nullable=False)
    admission_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    # Exact canonical JSON of the closed N1.3 preimage; never an ORM JSON float.
    preimage_json: Mapped[str] = mapped_column(Text, nullable=False)
    record_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    permission_admission_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    manifest_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    source_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    election_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now())
