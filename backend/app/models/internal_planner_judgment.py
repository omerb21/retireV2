from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class InternalPlannerJudgment(Base):
    __tablename__ = "internal_planner_judgments"
    __table_args__ = (
        CheckConstraint(
            "handling_status IN ("
            "'not_used_for_decision', "
            "'continue_internal_review', "
            "'internal_action_identified'"
            ")",
            name="ck_internal_planner_judgments_handling_status",
        ),
    )

    internal_planner_judgment_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    fixation_run_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("fixation_runs.id"),
        nullable=False,
        unique=True,
    )
    handling_status: Mapped[str] = mapped_column(String(64), nullable=False)
    next_internal_action: Mapped[str] = mapped_column(Text, nullable=False)
    internal_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    fixation_run: Mapped["FixationRun"] = relationship(
        "FixationRun",
        back_populates="internal_planner_judgment",
    )
