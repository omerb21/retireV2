from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class FixationDependencyManifest(Base):
    __tablename__ = "fixation_dependency_manifests"

    fixation_dependency_manifest_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    fixation_run_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("fixation_runs.id"),
        nullable=False,
        unique=True,
    )
    client_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("clients.client_id"),
        nullable=False,
    )
    manifest_schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    fingerprint_algorithm_version: Mapped[str] = mapped_column(String(64), nullable=False)
    manifest_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    manifest_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    fixation_run: Mapped["FixationRun"] = relationship(
        "FixationRun",
        back_populates="fixation_dependency_manifest",
    )
