"""SC-05E: non-executable professional review audit evidence.

Never a permission grant. Hashes bind a review to an exact scenario preimage;
authorization must be re-established independently from a trusted snapshot.
"""
from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class ScenarioCoefficientProfessionalReview(Base):
    __tablename__ = "scenario_coefficient_professional_reviews"
    __table_args__ = (
        UniqueConstraint("scenario_id", "decision_id", "scenario_version",
                         "record_fingerprint", name="uq_scenario_coefficient_review_evidence"),
        CheckConstraint("scenario_version > 0", name="ck_scenario_coefficient_review_version"),
        CheckConstraint("product_version > 0", name="ck_scenario_coefficient_review_product_version"),
        CheckConstraint("decision IN ('reviewed_for_candidate','rejected')",
                        name="ck_scenario_coefficient_review_decision"),
    )
    review_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenario_drafts.scenario_id", ondelete="RESTRICT"), nullable=False, index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.client_id", ondelete="RESTRICT"), nullable=False)
    scenario_version: Mapped[int] = mapped_column(Integer, nullable=False)
    decision_id: Mapped[str] = mapped_column(String(64), nullable=False)
    product_id: Mapped[str] = mapped_column(String(64), nullable=False)
    component_id: Mapped[str] = mapped_column(String(64), nullable=False)
    product_version: Mapped[int] = mapped_column(Integer, nullable=False)
    manifest_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    inventory_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    election_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    source_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    professional_actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    review_reference: Mapped[str] = mapped_column(String(128), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    record_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
