"""SC-05C isolated draft pension election, never professional authority."""
from datetime import date
from sqlalchemy import Date, ForeignKey, Integer, String, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class ScenarioDraftPensionElection(Base):
    __tablename__ = "scenario_draft_pension_elections"
    __table_args__ = (
        UniqueConstraint("scenario_id", "decision_id", name="uq_scenario_pension_election_decision"),
        CheckConstraint("scenario_version > 0", name="ck_scenario_pension_election_version"),
        CheckConstraint("coefficient_selection IN ('catalog_candidate','manual_review_required')", name="ck_scenario_pension_election_selection"),
    )

    election_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenario_drafts.scenario_id", ondelete="RESTRICT"), nullable=False, index=True)
    decision_id: Mapped[str] = mapped_column(String(64), nullable=False)
    scenario_version: Mapped[int] = mapped_column(Integer, nullable=False)
    pension_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    target_year: Mapped[int] = mapped_column(Integer, nullable=False)
    survivors_option: Mapped[str] = mapped_column(String(128), nullable=False)
    spouse_age_diff: Mapped[int] = mapped_column(Integer, nullable=False)
    coefficient_selection: Mapped[str] = mapped_column(String(32), nullable=False)
    company_name: Mapped[str | None] = mapped_column(String(255))
    option_name: Mapped[str | None] = mapped_column(String(255))
