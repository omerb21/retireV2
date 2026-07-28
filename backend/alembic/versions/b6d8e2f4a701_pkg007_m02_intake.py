"""add PKG-007 M02 controlled intake persistence

Revision ID: b6d8e2f4a701
Revises: f3a7c9d2e610
Create Date: 2026-07-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "b6d8e2f4a701"
down_revision: str | None = "f3a7c9d2e610"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    dialect_name = op.get_bind().dialect.name
    sha256_constraint = (
        "length(sha256_checksum) = 64 "
        "AND sha256_checksum = lower(sha256_checksum) "
        "AND sha256_checksum NOT GLOB '*[^0-9a-f]*'"
        if dialect_name == "sqlite"
        else "length(sha256_checksum) = 64 "
        "AND sha256_checksum = lower(sha256_checksum) "
        "AND sha256_checksum ~ '^[0-9a-f]{64}$'"
    )
    op.create_table(
        "m02_intake_records",
        sa.Column("intake_id", sa.String(64), primary_key=True),
        sa.Column(
            "client_id",
            sa.Integer(),
            sa.ForeignKey("clients.client_id"),
            nullable=False,
        ),
        sa.Column("record_kind", sa.String(32), nullable=False),
        sa.Column("declared_provider_name", sa.String(255), nullable=True),
        sa.Column("product_name", sa.String(255), nullable=True),
        sa.Column("product_identifier", sa.String(128), nullable=True),
        sa.Column("declared_account_reference", sa.String(255), nullable=True),
        sa.Column("manual_technical_reference", sa.String(64), nullable=True),
        sa.Column("declared_total_balance_amount", sa.Numeric(20, 2), nullable=True),
        sa.Column("declared_monthly_pension_amount", sa.Numeric(20, 2), nullable=True),
        sa.Column("declared_component_values", sa.JSON(), nullable=True),
        sa.Column("declared_statement_date", sa.Date(), nullable=True),
        sa.Column("declared_start_date", sa.Date(), nullable=True),
        sa.Column("declared_product_type", sa.String(255), nullable=True),
        sa.Column("source_type", sa.String(128), nullable=False),
        sa.Column("declared_basis", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("lifecycle_status", sa.String(32), nullable=False),
        sa.Column("preservation_status", sa.String(32), nullable=False),
        sa.Column("preservation_failure_code", sa.String(64), nullable=True),
        sa.Column("rejection_reason_code", sa.String(64), nullable=True),
        sa.Column(
            "diagnostics",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
        sa.Column(
            "duplicate_candidate",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("duplicate_of_intake_id", sa.String(64), nullable=True),
        sa.Column(
            "superseding_candidate",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("superseding_intake_id", sa.String(64), nullable=True),
        sa.Column("created_by_actor", sa.String(128), nullable=False),
        sa.Column("updated_by_actor", sa.String(128), nullable=False),
        sa.Column("lifecycle_decided_by_actor", sa.String(128), nullable=False),
        sa.Column(
            "lifecycle_decided_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "lifecycle_status IN "
            "('uploaded','metadata_review','accepted_for_review','rejected','superseded')",
            name="ck_m02_intake_records_lifecycle_status",
        ),
        sa.CheckConstraint(
            "preservation_status IN ('not_applicable','pending','preserved','failed')",
            name="ck_m02_intake_records_preservation_status",
        ),
        sa.CheckConstraint(
            "record_kind IN ('manual','uploaded_source')",
            name="ck_m02_intake_records_record_kind",
        ),
        sa.CheckConstraint(
            "(record_kind = 'manual' AND manual_technical_reference IS NOT NULL "
            "AND preservation_status = 'not_applicable') OR "
            "(record_kind = 'uploaded_source' AND manual_technical_reference IS NULL "
            "AND preservation_status != 'not_applicable')",
            name="ck_m02_intake_records_creation_path",
        ),
        sa.CheckConstraint(
            "(duplicate_candidate = 0 AND duplicate_of_intake_id IS NULL) OR "
            "(duplicate_candidate = 1 AND duplicate_of_intake_id IS NOT NULL "
            "AND duplicate_of_intake_id != intake_id)",
            name="ck_m02_intake_records_duplicate_consistency",
        ),
        sa.CheckConstraint(
            "(superseding_candidate = 0 AND superseding_intake_id IS NULL) OR "
            "(superseding_candidate = 1 AND superseding_intake_id IS NOT NULL "
            "AND superseding_intake_id != intake_id)",
            name="ck_m02_intake_records_superseding_consistency",
        ),
        sa.UniqueConstraint(
            "manual_technical_reference",
            name="uq_m02_intake_records_manual_technical_reference",
        ),
        sa.UniqueConstraint(
            "intake_id", "client_id", name="uq_m02_intake_records_id_client"
        ),
        sa.ForeignKeyConstraint(
            ["duplicate_of_intake_id", "client_id"],
            ["m02_intake_records.intake_id", "m02_intake_records.client_id"],
            name="fk_m02_intake_records_duplicate_client",
        ),
        sa.ForeignKeyConstraint(
            ["superseding_intake_id", "client_id"],
            ["m02_intake_records.intake_id", "m02_intake_records.client_id"],
            name="fk_m02_intake_records_superseding_client",
        ),
    )
    op.create_index(
        "ix_m02_intake_records_client_created",
        "m02_intake_records",
        ["client_id", "created_at"],
    )
    op.create_index(
        "ix_m02_intake_records_client_lifecycle",
        "m02_intake_records",
        ["client_id", "lifecycle_status"],
    )
    op.create_index(
        "ix_m02_intake_records_client_source_date",
        "m02_intake_records",
        ["client_id", "source_type", "declared_statement_date"],
    )

    op.create_table(
        "m02_preserved_blobs",
        sa.Column("blob_id", sa.String(64), primary_key=True),
        sa.Column(
            "client_id",
            sa.Integer(),
            sa.ForeignKey("clients.client_id"),
            nullable=False,
        ),
        sa.Column("storage_key", sa.String(255), nullable=False),
        sa.Column("sha256_checksum", sa.String(64), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("validated_media_type", sa.String(128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            sha256_constraint,
            name="ck_m02_preserved_blobs_sha256",
        ),
        sa.CheckConstraint(
            "byte_size > 0 AND byte_size <= 26214400",
            name="ck_m02_preserved_blobs_byte_size",
        ),
        sa.CheckConstraint(
            "storage_key LIKE 'objects/%' "
            "AND storage_key NOT LIKE '%..%' "
            "AND storage_key NOT LIKE '%:%' "
            "AND storage_key NOT LIKE '%\\%'",
            name="ck_m02_preserved_blobs_relative_storage_key",
        ),
        sa.UniqueConstraint(
            "client_id",
            "sha256_checksum",
            name="uq_m02_preserved_blobs_client_checksum",
        ),
        sa.UniqueConstraint(
            "storage_key", name="uq_m02_preserved_blobs_storage_key"
        ),
        sa.UniqueConstraint(
            "blob_id", "client_id", name="uq_m02_preserved_blobs_id_client"
        ),
    )

    op.create_table(
        "m02_preserved_sources",
        sa.Column("source_id", sa.String(64), primary_key=True),
        sa.Column(
            "client_id",
            sa.Integer(),
            sa.ForeignKey("clients.client_id"),
            nullable=False,
        ),
        sa.Column("intake_id", sa.String(64), nullable=False),
        sa.Column("blob_id", sa.String(64), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("sanitized_download_filename", sa.String(255), nullable=False),
        sa.Column("normalized_extension", sa.String(16), nullable=False),
        sa.Column("declared_mime_type", sa.String(255), nullable=False),
        sa.Column("validated_media_type", sa.String(128), nullable=False),
        sa.Column("detected_text_encoding", sa.String(32), nullable=True),
        sa.Column("source_type", sa.String(128), nullable=False),
        sa.Column("declared_statement_date", sa.Date(), nullable=True),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("preservation_status", sa.String(32), nullable=False),
        sa.Column(
            "validation_diagnostics",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "normalized_extension IN ('.pdf','.xml','.dat','.csv','.xlsx')",
            name="ck_m02_preserved_sources_extension",
        ),
        sa.CheckConstraint(
            "preservation_status = 'preserved'",
            name="ck_m02_preserved_sources_preservation_status",
        ),
        sa.CheckConstraint(
            "byte_size > 0 AND byte_size <= 26214400",
            name="ck_m02_preserved_sources_byte_size",
        ),
        sa.UniqueConstraint(
            "intake_id", name="uq_m02_preserved_sources_intake"
        ),
        sa.ForeignKeyConstraint(
            ["intake_id", "client_id"],
            ["m02_intake_records.intake_id", "m02_intake_records.client_id"],
            name="fk_m02_preserved_sources_intake_client",
        ),
        sa.ForeignKeyConstraint(
            ["blob_id", "client_id"],
            ["m02_preserved_blobs.blob_id", "m02_preserved_blobs.client_id"],
            name="fk_m02_preserved_sources_blob_client",
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_m02_preserved_sources_client_uploaded",
        "m02_preserved_sources",
        ["client_id", "uploaded_at"],
    )
    op.create_index(
        "ix_m02_preserved_sources_client_intake",
        "m02_preserved_sources",
        ["client_id", "intake_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_m02_preserved_sources_client_intake",
        table_name="m02_preserved_sources",
    )
    op.drop_index(
        "ix_m02_preserved_sources_client_uploaded",
        table_name="m02_preserved_sources",
    )
    op.drop_table("m02_preserved_sources")
    op.drop_table("m02_preserved_blobs")
    op.drop_index(
        "ix_m02_intake_records_client_source_date",
        table_name="m02_intake_records",
    )
    op.drop_index(
        "ix_m02_intake_records_client_lifecycle",
        table_name="m02_intake_records",
    )
    op.drop_index(
        "ix_m02_intake_records_client_created",
        table_name="m02_intake_records",
    )
    op.drop_table("m02_intake_records")
