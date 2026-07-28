from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    event,
    func,
    inspect,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


M02_LIFECYCLE_STATUSES = (
    "uploaded",
    "metadata_review",
    "accepted_for_review",
    "rejected",
    "superseded",
)
M02_PRESERVATION_STATUSES = ("not_applicable", "pending", "preserved", "failed")
M02_ALLOWED_EXTENSIONS = (".pdf", ".xml", ".dat", ".csv", ".xlsx")


class M02IntakeRecord(Base):
    __tablename__ = "m02_intake_records"
    __table_args__ = (
        CheckConstraint(
            "lifecycle_status IN "
            "('uploaded','metadata_review','accepted_for_review','rejected','superseded')",
            name="ck_m02_intake_records_lifecycle_status",
        ),
        CheckConstraint(
            "preservation_status IN ('not_applicable','pending','preserved','failed')",
            name="ck_m02_intake_records_preservation_status",
        ),
        CheckConstraint(
            "record_kind IN ('manual','uploaded_source')",
            name="ck_m02_intake_records_record_kind",
        ),
        CheckConstraint(
            "(record_kind = 'manual' AND manual_technical_reference IS NOT NULL "
            "AND preservation_status = 'not_applicable') OR "
            "(record_kind = 'uploaded_source' AND manual_technical_reference IS NULL "
            "AND preservation_status != 'not_applicable')",
            name="ck_m02_intake_records_creation_path",
        ),
        CheckConstraint(
            "(duplicate_candidate = 0 AND duplicate_of_intake_id IS NULL) OR "
            "(duplicate_candidate = 1 AND duplicate_of_intake_id IS NOT NULL "
            "AND duplicate_of_intake_id != intake_id)",
            name="ck_m02_intake_records_duplicate_consistency",
        ),
        CheckConstraint(
            "(superseding_candidate = 0 AND superseding_intake_id IS NULL) OR "
            "(superseding_candidate = 1 AND superseding_intake_id IS NOT NULL "
            "AND superseding_intake_id != intake_id)",
            name="ck_m02_intake_records_superseding_consistency",
        ),
        ForeignKeyConstraint(
            ["duplicate_of_intake_id", "client_id"],
            ["m02_intake_records.intake_id", "m02_intake_records.client_id"],
            name="fk_m02_intake_records_duplicate_client",
        ),
        ForeignKeyConstraint(
            ["superseding_intake_id", "client_id"],
            ["m02_intake_records.intake_id", "m02_intake_records.client_id"],
            name="fk_m02_intake_records_superseding_client",
        ),
        UniqueConstraint(
            "intake_id", "client_id", name="uq_m02_intake_records_id_client"
        ),
        Index(
            "ix_m02_intake_records_client_created",
            "client_id",
            "created_at",
        ),
        Index(
            "ix_m02_intake_records_client_lifecycle",
            "client_id",
            "lifecycle_status",
        ),
        Index(
            "ix_m02_intake_records_client_source_date",
            "client_id",
            "source_type",
            "declared_statement_date",
        ),
    )

    intake_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clients.client_id"), nullable=False
    )
    record_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    declared_provider_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    product_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    product_identifier: Mapped[str | None] = mapped_column(String(128), nullable=True)
    declared_account_reference: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    manual_technical_reference: Mapped[str | None] = mapped_column(
        String(64), nullable=True, unique=True
    )
    declared_total_balance_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 2), nullable=True
    )
    declared_monthly_pension_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 2), nullable=True
    )
    declared_component_values: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSON, nullable=True
    )
    declared_statement_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    declared_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    declared_product_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_type: Mapped[str] = mapped_column(String(128), nullable=False)
    declared_basis: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    lifecycle_status: Mapped[str] = mapped_column(String(32), nullable=False)
    preservation_status: Mapped[str] = mapped_column(String(32), nullable=False)
    preservation_failure_code: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    rejection_reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    diagnostics: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    duplicate_candidate: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    duplicate_of_intake_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    superseding_candidate: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    superseding_intake_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_by_actor: Mapped[str] = mapped_column(String(128), nullable=False)
    updated_by_actor: Mapped[str] = mapped_column(String(128), nullable=False)
    lifecycle_decided_by_actor: Mapped[str] = mapped_column(String(128), nullable=False)
    lifecycle_decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    preserved_source: Mapped["M02PreservedSource | None"] = relationship(
        "M02PreservedSource",
        back_populates="intake",
        uselist=False,
        overlaps="blob,sources",
    )


class M02PreservedBlob(Base):
    __tablename__ = "m02_preserved_blobs"
    __table_args__ = (
        CheckConstraint(
            "length(sha256_checksum) = 64 "
            "AND sha256_checksum = lower(sha256_checksum) "
            "AND sha256_checksum NOT GLOB '*[^0-9a-f]*'",
            name="ck_m02_preserved_blobs_sha256",
        ),
        CheckConstraint(
            "byte_size > 0 AND byte_size <= 26214400",
            name="ck_m02_preserved_blobs_byte_size",
        ),
        CheckConstraint(
            "storage_key LIKE 'objects/%' "
            "AND instr(storage_key, '..') = 0 "
            "AND instr(storage_key, ':') = 0 "
            "AND instr(storage_key, char(92)) = 0",
            name="ck_m02_preserved_blobs_relative_storage_key",
        ),
        UniqueConstraint(
            "client_id",
            "sha256_checksum",
            name="uq_m02_preserved_blobs_client_checksum",
        ),
        UniqueConstraint("storage_key", name="uq_m02_preserved_blobs_storage_key"),
        UniqueConstraint(
            "blob_id", "client_id", name="uq_m02_preserved_blobs_id_client"
        ),
    )

    blob_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clients.client_id"), nullable=False
    )
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False)
    sha256_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    validated_media_type: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    sources: Mapped[list["M02PreservedSource"]] = relationship(
        "M02PreservedSource",
        back_populates="blob",
        passive_deletes=True,
        overlaps="intake,preserved_source",
    )


class M02PreservedSource(Base):
    __tablename__ = "m02_preserved_sources"
    __table_args__ = (
        ForeignKeyConstraint(
            ["intake_id", "client_id"],
            ["m02_intake_records.intake_id", "m02_intake_records.client_id"],
            name="fk_m02_preserved_sources_intake_client",
        ),
        ForeignKeyConstraint(
            ["blob_id", "client_id"],
            ["m02_preserved_blobs.blob_id", "m02_preserved_blobs.client_id"],
            name="fk_m02_preserved_sources_blob_client",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "normalized_extension IN ('.pdf','.xml','.dat','.csv','.xlsx')",
            name="ck_m02_preserved_sources_extension",
        ),
        CheckConstraint(
            "preservation_status = 'preserved'",
            name="ck_m02_preserved_sources_preservation_status",
        ),
        CheckConstraint(
            "byte_size > 0 AND byte_size <= 26214400",
            name="ck_m02_preserved_sources_byte_size",
        ),
        UniqueConstraint(
            "intake_id", name="uq_m02_preserved_sources_intake"
        ),
        Index(
            "ix_m02_preserved_sources_client_uploaded",
            "client_id",
            "uploaded_at",
        ),
        Index(
            "ix_m02_preserved_sources_client_intake",
            "client_id",
            "intake_id",
        ),
    )

    source_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clients.client_id"), nullable=False
    )
    intake_id: Mapped[str] = mapped_column(String(64), nullable=False)
    blob_id: Mapped[str] = mapped_column(String(64), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    sanitized_download_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_extension: Mapped[str] = mapped_column(String(16), nullable=False)
    declared_mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    validated_media_type: Mapped[str] = mapped_column(String(128), nullable=False)
    detected_text_encoding: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )
    source_type: Mapped[str] = mapped_column(String(128), nullable=False)
    declared_statement_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    preservation_status: Mapped[str] = mapped_column(String(32), nullable=False)
    validation_diagnostics: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    intake: Mapped[M02IntakeRecord] = relationship(
        "M02IntakeRecord",
        back_populates="preserved_source",
        overlaps="blob,sources",
    )
    blob: Mapped[M02PreservedBlob] = relationship(
        "M02PreservedBlob",
        back_populates="sources",
        overlaps="intake,preserved_source",
    )


@event.listens_for(M02PreservedBlob, "before_update")
def _prevent_blob_identity_mutation(_mapper, _connection, target: M02PreservedBlob) -> None:
    state = inspect(target)
    immutable_fields = (
        "client_id",
        "storage_key",
        "sha256_checksum",
        "byte_size",
        "validated_media_type",
    )
    if any(state.attrs[field].history.has_changes() for field in immutable_fields):
        raise ValueError("M02 preserved blob identity is immutable")
