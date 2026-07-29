"""add PKG-008 M03 review persistence

Revision ID: e4a7c3d9b802
Revises: b6d8e2f4a701
Create Date: 2026-07-29
"""

from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision: str = "e4a7c3d9b802"
down_revision: str | None = "b6d8e2f4a701"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "m03_review_revisions",
        sa.Column("revision_id", sa.String(64), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.client_id"), nullable=False),
        sa.Column("target_kind", sa.String(32), nullable=False),
        sa.Column("intake_id", sa.String(64), sa.ForeignKey("m02_intake_records.intake_id"), nullable=False),
        sa.Column("source_id", sa.String(64), sa.ForeignKey("m02_preserved_sources.source_id"), nullable=True),
        sa.Column("predecessor_revision_id", sa.String(64), sa.ForeignKey("m03_review_revisions.revision_id"), nullable=True),
        sa.Column("revision_sequence", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("actor", sa.String(128), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("target_kind IN ('source_evidence_review','manual_record_review')", name="ck_m03_review_target_kind"),
        sa.CheckConstraint("state IN ('under_review','accepted','rejected')", name="ck_m03_review_state"),
        sa.CheckConstraint("(target_kind = 'source_evidence_review' AND source_id IS NOT NULL) OR (target_kind = 'manual_record_review' AND source_id IS NULL)", name="ck_m03_review_target_provenance"),
        sa.CheckConstraint("(revision_sequence = 1 AND predecessor_revision_id IS NULL AND state = 'under_review') OR (revision_sequence > 1 AND predecessor_revision_id IS NOT NULL)", name="ck_m03_review_revision_shape"),
        sa.UniqueConstraint("client_id", "intake_id", "revision_sequence", name="uq_m03_review_target_sequence"),
        sa.UniqueConstraint("predecessor_revision_id", name="uq_m03_review_predecessor_child"),
        sa.UniqueConstraint("revision_id", "client_id", name="uq_m03_review_revision_client"),
    )
    op.create_index("ix_m03_review_client_target", "m03_review_revisions", ["client_id", "intake_id", "revision_sequence"])
    op.create_table(
        "m03_annotations",
        sa.Column("annotation_id", sa.String(64), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.client_id"), nullable=False),
        sa.Column("intake_id", sa.String(64), sa.ForeignKey("m02_intake_records.intake_id"), nullable=False),
        sa.Column("source_id", sa.String(64), sa.ForeignKey("m02_preserved_sources.source_id"), nullable=True),
        sa.Column("review_revision_id", sa.String(64), sa.ForeignKey("m03_review_revisions.revision_id"), nullable=False),
        sa.Column("topic", sa.String(255), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("actor", sa.String(128), nullable=False),
        sa.Column("supersedes_annotation_id", sa.String(64), sa.ForeignKey("m03_annotations.annotation_id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("length(trim(topic)) > 0", name="ck_m03_annotation_topic"),
        sa.CheckConstraint("length(trim(note)) > 0", name="ck_m03_annotation_note"),
        sa.CheckConstraint("length(trim(reason)) > 0", name="ck_m03_annotation_reason"),
        sa.CheckConstraint("supersedes_annotation_id IS NULL OR supersedes_annotation_id != annotation_id", name="ck_m03_annotation_not_self"),
        sa.UniqueConstraint("supersedes_annotation_id", name="uq_m03_annotation_superseded_once"),
    )
    op.create_index("ix_m03_annotation_client_target", "m03_annotations", ["client_id", "intake_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_m03_annotation_client_target", table_name="m03_annotations")
    op.drop_table("m03_annotations")
    op.drop_index("ix_m03_review_client_target", table_name="m03_review_revisions")
    op.drop_table("m03_review_revisions")
