"""add PKG-009 M04 classification persistence

Revision ID: 95222c79dce8
Revises: e4a7c3d9b802
Create Date: 2026-07-31 01:29:31.392411

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "95222c79dce8"
down_revision: str | None = "e4a7c3d9b802"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "m04_classification_subjects",
        sa.Column("subject_id", sa.String(64), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.client_id"), nullable=False),
        sa.Column("intake_id", sa.String(64), nullable=False),
        sa.Column("target_kind", sa.String(32), nullable=False),
        sa.Column("archive_generation", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "target_kind IN ('source_evidence_review','manual_record_review')",
            name="ck_m04_subject_target_kind",
        ),
        sa.CheckConstraint("archive_generation >= 0", name="ck_m04_subject_archive_generation"),
        sa.ForeignKeyConstraint(
            ["intake_id", "client_id"],
            ["m02_intake_records.intake_id", "m02_intake_records.client_id"],
            name="fk_m04_subject_intake_client",
        ),
        sa.UniqueConstraint("client_id", "intake_id", "target_kind", name="uq_m04_subject_target"),
        sa.UniqueConstraint(
            "subject_id", "client_id", "intake_id", "target_kind",
            name="uq_m04_subject_identity_target",
        ),
    )
    op.create_index(
        "ix_m04_subject_client_target",
        "m04_classification_subjects",
        ["client_id", "intake_id"],
    )

    op.create_table(
        "m04_classification_revisions",
        sa.Column("revision_id", sa.String(64), primary_key=True),
        sa.Column("subject_id", sa.String(64), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("intake_id", sa.String(64), nullable=False),
        sa.Column("target_kind", sa.String(32), nullable=False),
        sa.Column("source_id", sa.String(64), sa.ForeignKey("m02_preserved_sources.source_id"), nullable=True),
        sa.Column("m03_revision_id", sa.String(64), nullable=False),
        sa.Column("predecessor_revision_id", sa.String(64), nullable=True),
        sa.Column("revision_sequence", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("action_type", sa.String(32), nullable=False),
        sa.Column("product_family", sa.String(64), nullable=True),
        sa.Column("pension_subtype", sa.String(128), nullable=True),
        sa.Column("aggregate_interpretation", sa.String(32), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("reason_code", sa.String(128), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("input_snapshot", sa.JSON(), nullable=False),
        sa.Column("catalogue_version", sa.String(64), nullable=False),
        sa.Column("matched_rule_evidence", sa.JSON(), nullable=False),
        sa.Column("match_basis", sa.String(64), nullable=False),
        sa.Column("action_evidence", sa.JSON(), nullable=False),
        sa.Column("evidence_digest", sa.String(64), nullable=False),
        sa.Column("historical_revision_id", sa.String(64), sa.ForeignKey("m04_classification_revisions.revision_id"), nullable=True),
        sa.Column("actor", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "target_kind IN ('source_evidence_review','manual_record_review')",
            name="ck_m04_revision_target_kind",
        ),
        sa.CheckConstraint(
            "state IN ('under_review','proposed','accepted','unresolved','rejected')",
            name="ck_m04_revision_state",
        ),
        sa.CheckConstraint(
            "action_type IN ('start','proposal','unresolved','accept','reject','reopen','override','undo','start_revalidation')",
            name="ck_m04_revision_action_type",
        ),
        sa.CheckConstraint(
            "product_family IS NULL OR product_family IN ('insurance_policy','savings_policy','provident_fund','investment_provident_fund','education_fund','pension_fund','unknown_or_unresolved')",
            name="ck_m04_revision_product_family",
        ),
        sa.CheckConstraint(
            "aggregate_interpretation IS NULL OR aggregate_interpretation IN ('pension','capital','mixed','unresolved')",
            name="ck_m04_revision_aggregate_interpretation",
        ),
        sa.CheckConstraint(
            "length(evidence_digest) = 64 AND evidence_digest = lower(evidence_digest)",
            name="ck_m04_revision_evidence_digest",
        ),
        sa.CheckConstraint(
            "(revision_sequence = 1 AND predecessor_revision_id IS NULL AND action_type = 'start' AND state = 'under_review') OR (revision_sequence > 1 AND predecessor_revision_id IS NOT NULL)",
            name="ck_m04_revision_shape",
        ),
        sa.ForeignKeyConstraint(
            ["subject_id", "client_id", "intake_id", "target_kind"],
            [
                "m04_classification_subjects.subject_id",
                "m04_classification_subjects.client_id",
                "m04_classification_subjects.intake_id",
                "m04_classification_subjects.target_kind",
            ],
            name="fk_m04_revision_subject_target",
        ),
        sa.ForeignKeyConstraint(
            ["predecessor_revision_id", "client_id", "intake_id", "target_kind"],
            [
                "m04_classification_revisions.revision_id",
                "m04_classification_revisions.client_id",
                "m04_classification_revisions.intake_id",
                "m04_classification_revisions.target_kind",
            ],
            name="fk_m04_revision_predecessor_target",
        ),
        sa.ForeignKeyConstraint(
            ["m03_revision_id", "client_id"],
            ["m03_review_revisions.revision_id", "m03_review_revisions.client_id"],
            name="fk_m04_revision_m03_client",
        ),
        sa.UniqueConstraint("subject_id", "revision_sequence", name="uq_m04_revision_subject_sequence"),
        sa.UniqueConstraint("predecessor_revision_id", name="uq_m04_revision_predecessor_child"),
        sa.UniqueConstraint(
            "revision_id", "client_id", "intake_id", "target_kind",
            name="uq_m04_revision_identity_target",
        ),
    )
    op.create_index(
        "ix_m04_revision_client_target",
        "m04_classification_revisions",
        ["client_id", "intake_id", "target_kind", "revision_sequence"],
    )

    op.create_table(
        "m04_component_decisions",
        sa.Column("component_decision_id", sa.String(64), primary_key=True),
        sa.Column("revision_id", sa.String(64), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("intake_id", sa.String(64), nullable=False),
        sa.Column("target_kind", sa.String(32), nullable=False),
        sa.Column("evidence_identity", sa.String(255), nullable=False),
        sa.Column("original_label", sa.String(255), nullable=True),
        sa.Column("original_code", sa.String(128), nullable=True),
        sa.Column("component_kind", sa.String(64), nullable=False),
        sa.Column("interpretation", sa.String(32), nullable=False),
        sa.Column("matched_rule_evidence", sa.JSON(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("current_employer_related", sa.String(16), nullable=False, server_default="unknown"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "component_kind IN ('severance_component','contribution_component','unknown_component')",
            name="ck_m04_component_kind",
        ),
        sa.CheckConstraint(
            "interpretation IN ('pension','capital','unresolved')",
            name="ck_m04_component_interpretation",
        ),
        sa.CheckConstraint(
            "current_employer_related IN ('yes','no','unknown')",
            name="ck_m04_component_employer_related",
        ),
        sa.ForeignKeyConstraint(
            ["revision_id", "client_id", "intake_id", "target_kind"],
            [
                "m04_classification_revisions.revision_id",
                "m04_classification_revisions.client_id",
                "m04_classification_revisions.intake_id",
                "m04_classification_revisions.target_kind",
            ],
            name="fk_m04_component_revision_target",
        ),
        sa.UniqueConstraint(
            "revision_id", "evidence_identity",
            name="uq_m04_component_revision_evidence",
        ),
    )
    op.create_index(
        "ix_m04_component_revision",
        "m04_component_decisions",
        ["revision_id", "evidence_identity"],
    )


def downgrade() -> None:
    op.drop_index("ix_m04_component_revision", table_name="m04_component_decisions")
    op.drop_table("m04_component_decisions")
    op.drop_index("ix_m04_revision_client_target", table_name="m04_classification_revisions")
    op.drop_table("m04_classification_revisions")
    op.drop_index("ix_m04_subject_client_target", table_name="m04_classification_subjects")
    op.drop_table("m04_classification_subjects")
