"""add PKG-011 M06 conversion persistence

Revision ID: d7e3a6b9c204
Revises: a4c9e2f7b106
Create Date: 2026-08-09
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "d7e3a6b9c204"
down_revision: str | None = "a4c9e2f7b106"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "m06_conversion_subjects",
        sa.Column("subject_id", sa.String(64), primary_key=True),
        sa.Column(
            "client_id",
            sa.Integer(),
            sa.ForeignKey("clients.client_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("m05_subject_id", sa.String(64), nullable=False),
        sa.Column("mode", sa.String(64), nullable=False),
        sa.Column("input_identity", sa.String(255), nullable=False),
        sa.Column("provider_identity_digest", sa.String(64), nullable=False),
        sa.Column("account_identity_digest", sa.String(64), nullable=False),
        sa.Column("product_context_digest", sa.String(64), nullable=False),
        sa.Column("semantic_digest", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "mode IN ('balance_to_monthly_pension','monthly_pension_to_capital_equivalent')",
            name="ck_m06_subject_mode",
        ),
        sa.CheckConstraint(
            "length(semantic_digest) = 64 AND length(provider_identity_digest) = 64 AND length(account_identity_digest) = 64 AND length(product_context_digest) = 64",
            name="ck_m06_subject_digests",
        ),
        sa.ForeignKeyConstraint(
            ["m05_subject_id", "client_id"],
            ["m05_ledger_subjects.subject_id", "m05_ledger_subjects.client_id"],
            name="fk_m06_subject_m05_client",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("semantic_digest", name="uq_m06_subject_semantic_digest"),
        sa.UniqueConstraint(
            "subject_id", "client_id", name="uq_m06_subject_identity_client"
        ),
    )
    op.create_index(
        "ix_m06_subject_client", "m06_conversion_subjects", ["client_id", "created_at"]
    )

    op.create_table(
        "m06_conversion_revisions",
        sa.Column("revision_id", sa.String(64), primary_key=True),
        sa.Column("subject_id", sa.String(64), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("predecessor_revision_id", sa.String(64), nullable=True),
        sa.Column("revision_sequence", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("action_type", sa.String(32), nullable=False),
        sa.Column("mode", sa.String(64), nullable=False),
        sa.Column("formula_id", sa.String(96), nullable=False),
        sa.Column("input_identity", sa.String(255), nullable=False),
        sa.Column("input_amount", sa.Text(), nullable=True),
        sa.Column("input_date", sa.Date(), nullable=True),
        sa.Column("m02_intake_id", sa.String(64), nullable=False),
        sa.Column("m03_revision_id", sa.String(64), nullable=False),
        sa.Column("m04_revision_id", sa.String(64), nullable=False),
        sa.Column("m05_revision_id", sa.String(64), nullable=False),
        sa.Column("predecessor_snapshot", sa.JSON(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("blocking_reasons", sa.JSON(), nullable=False),
        sa.Column("informational_warnings", sa.JSON(), nullable=False),
        sa.Column("reason_code", sa.String(128), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("evidence_digest", sa.String(64), nullable=False),
        sa.Column("actor", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "state IN ('draft','resolved','warning_reviewed','blocked','superseded')",
            name="ck_m06_revision_state",
        ),
        sa.CheckConstraint(
            "action_type IN ('start','resolve','review_warnings','correct_coefficient','supersede')",
            name="ck_m06_revision_action",
        ),
        sa.CheckConstraint(
            "(revision_sequence = 1 AND predecessor_revision_id IS NULL AND action_type = 'start') OR (revision_sequence > 1 AND predecessor_revision_id IS NOT NULL)",
            name="ck_m06_revision_shape",
        ),
        sa.CheckConstraint(
            "length(evidence_digest) = 64", name="ck_m06_revision_digest"
        ),
        sa.ForeignKeyConstraint(
            ["subject_id", "client_id"],
            ["m06_conversion_subjects.subject_id", "m06_conversion_subjects.client_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["predecessor_revision_id", "client_id", "subject_id"],
            [
                "m06_conversion_revisions.revision_id",
                "m06_conversion_revisions.client_id",
                "m06_conversion_revisions.subject_id",
            ],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["m02_intake_id", "client_id"],
            ["m02_intake_records.intake_id", "m02_intake_records.client_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["m03_revision_id", "client_id"],
            ["m03_review_revisions.revision_id", "m03_review_revisions.client_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["m04_revision_id"],
            ["m04_classification_revisions.revision_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["m05_revision_id"],
            ["m05_ledger_revisions.revision_id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "subject_id", "revision_sequence", name="uq_m06_revision_subject_sequence"
        ),
        sa.UniqueConstraint(
            "predecessor_revision_id", name="uq_m06_revision_predecessor_child"
        ),
        sa.UniqueConstraint(
            "revision_id",
            "client_id",
            "subject_id",
            name="uq_m06_revision_identity_subject",
        ),
    )
    op.create_index(
        "ix_m06_revision_subject",
        "m06_conversion_revisions",
        ["client_id", "subject_id", "revision_sequence"],
    )

    op.create_table(
        "m06_coefficient_evidence",
        sa.Column("evidence_id", sa.String(64), primary_key=True),
        sa.Column("revision_id", sa.String(64), nullable=False),
        sa.Column("subject_id", sa.String(64), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("authority_class", sa.String(32), nullable=False),
        sa.Column("coefficient_text", sa.Text(), nullable=False),
        sa.Column("decimal_precision", sa.Integer(), nullable=False),
        sa.Column("decimal_exponent", sa.Integer(), nullable=False),
        sa.Column("source_intake_id", sa.String(64), nullable=True),
        sa.Column("source_locator", sa.Text(), nullable=True),
        sa.Column("source_note", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("provider_context", sa.Text(), nullable=False),
        sa.Column("product_context", sa.JSON(), nullable=False),
        sa.Column("mode", sa.String(64), nullable=False),
        sa.Column("unit_semantics", sa.String(128), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("applicability_declared", sa.Boolean(), nullable=False),
        sa.Column("metadata_snapshot", sa.JSON(), nullable=False),
        sa.Column("evidence_digest", sa.String(64), nullable=False),
        sa.Column("actor", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "authority_class IN ('documentary','planner_declared')",
            name="ck_m06_coefficient_authority",
        ),
        sa.CheckConstraint(
            "length(coefficient_text) > 0 AND length(evidence_digest) = 64",
            name="ck_m06_coefficient_digest",
        ),
        sa.CheckConstraint(
            "(authority_class = 'documentary' AND source_intake_id IS NOT NULL AND (source_locator IS NOT NULL OR source_note IS NOT NULL)) OR (authority_class = 'planner_declared' AND source_note IS NOT NULL AND applicability_declared = true)",
            name="ck_m06_coefficient_shape",
        ),
        sa.ForeignKeyConstraint(
            ["revision_id", "client_id", "subject_id"],
            [
                "m06_conversion_revisions.revision_id",
                "m06_conversion_revisions.client_id",
                "m06_conversion_revisions.subject_id",
            ],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_intake_id", "client_id"],
            ["m02_intake_records.intake_id", "m02_intake_records.client_id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("revision_id", name="uq_m06_coefficient_revision"),
    )
    op.create_table(
        "m06_calculation_manifests",
        sa.Column("manifest_id", sa.String(64), primary_key=True),
        sa.Column("revision_id", sa.String(64), nullable=False),
        sa.Column("subject_id", sa.String(64), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("manifest", sa.JSON(), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("raw_result_kind", sa.String(32), nullable=True),
        sa.Column("raw_decimal", sa.Text(), nullable=True),
        sa.Column("raw_numerator", sa.Text(), nullable=True),
        sa.Column("raw_denominator", sa.Text(), nullable=True),
        sa.Column("display_result", sa.String(96), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "length(fingerprint) = 64", name="ck_m06_manifest_fingerprint"
        ),
        sa.CheckConstraint(
            "(raw_result_kind IS NULL AND raw_decimal IS NULL AND raw_numerator IS NULL AND raw_denominator IS NULL AND display_result IS NULL) OR (raw_result_kind = 'exact_ratio' AND raw_decimal IS NULL AND raw_numerator IS NOT NULL AND raw_denominator IS NOT NULL AND display_result IS NOT NULL) OR (raw_result_kind = 'exact_decimal' AND raw_decimal IS NOT NULL AND raw_numerator IS NULL AND raw_denominator IS NULL AND display_result IS NOT NULL)",
            name="ck_m06_manifest_result_shape",
        ),
        sa.ForeignKeyConstraint(
            ["revision_id", "client_id", "subject_id"],
            [
                "m06_conversion_revisions.revision_id",
                "m06_conversion_revisions.client_id",
                "m06_conversion_revisions.subject_id",
            ],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("revision_id", name="uq_m06_manifest_revision"),
    )
    op.create_table(
        "m06_warning_dispositions",
        sa.Column("disposition_id", sa.String(64), primary_key=True),
        sa.Column("revision_id", sa.String(64), nullable=False),
        sa.Column("subject_id", sa.String(64), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("warning_id", sa.String(128), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("confirmed", sa.Boolean(), nullable=False),
        sa.Column("actor", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["revision_id", "client_id", "subject_id"],
            [
                "m06_conversion_revisions.revision_id",
                "m06_conversion_revisions.client_id",
                "m06_conversion_revisions.subject_id",
            ],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "revision_id", "warning_id", name="uq_m06_warning_revision"
        ),
    )


def downgrade() -> None:
    op.drop_table("m06_warning_dispositions")
    op.drop_table("m06_calculation_manifests")
    op.drop_table("m06_coefficient_evidence")
    op.drop_index("ix_m06_revision_subject", table_name="m06_conversion_revisions")
    op.drop_table("m06_conversion_revisions")
    op.drop_index("ix_m06_subject_client", table_name="m06_conversion_subjects")
    op.drop_table("m06_conversion_subjects")
