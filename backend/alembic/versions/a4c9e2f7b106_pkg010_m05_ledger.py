"""add PKG-010 M05 manual ledger persistence

Revision ID: a4c9e2f7b106
Revises: 95222c79dce8
Create Date: 2026-08-03

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "a4c9e2f7b106"
down_revision: str | None = "95222c79dce8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "m05_ledger_subjects",
        sa.Column("subject_id", sa.String(64), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.client_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("provider_name", sa.String(255), nullable=False),
        sa.Column("account_reference", sa.String(255), nullable=False),
        sa.Column("provider_identity_digest", sa.String(64), nullable=False),
        sa.Column("account_identity_digest", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("length(provider_name) > 0", name="ck_m05_subject_provider"),
        sa.CheckConstraint("length(account_reference) > 0", name="ck_m05_subject_account"),
        sa.CheckConstraint("length(provider_identity_digest) = 64 AND provider_identity_digest = lower(provider_identity_digest)", name="ck_m05_subject_provider_digest"),
        sa.CheckConstraint("length(account_identity_digest) = 64 AND account_identity_digest = lower(account_identity_digest)", name="ck_m05_subject_account_digest"),
        sa.UniqueConstraint("client_id", "provider_identity_digest", "account_identity_digest", name="uq_m05_subject_exact_account"),
        sa.UniqueConstraint("subject_id", "client_id", name="uq_m05_subject_identity_client"),
    )
    op.create_index("ix_m05_subject_client", "m05_ledger_subjects", ["client_id", "created_at"])

    op.create_table(
        "m05_candidate_links",
        sa.Column("candidate_id", sa.String(72), primary_key=True),
        sa.Column("subject_id", sa.String(64), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("intake_id", sa.String(64), nullable=False),
        sa.Column("target_kind", sa.String(32), nullable=False),
        sa.Column("m03_revision_id", sa.String(64), nullable=False),
        sa.Column("m04_revision_id", sa.String(64), nullable=False),
        sa.Column("statement_date", sa.Date(), nullable=False),
        sa.Column("m03_decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_snapshot_digest", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("target_kind = 'manual_record_review'", name="ck_m05_candidate_target_kind"),
        sa.CheckConstraint("length(source_snapshot_digest) = 64 AND source_snapshot_digest = lower(source_snapshot_digest)", name="ck_m05_candidate_source_digest"),
        sa.ForeignKeyConstraint(["subject_id", "client_id"], ["m05_ledger_subjects.subject_id", "m05_ledger_subjects.client_id"], name="fk_m05_candidate_subject_client", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["intake_id", "client_id"], ["m02_intake_records.intake_id", "m02_intake_records.client_id"], name="fk_m05_candidate_intake_client", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["m03_revision_id", "client_id"], ["m03_review_revisions.revision_id", "m03_review_revisions.client_id"], name="fk_m05_candidate_m03_client", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["m04_revision_id", "client_id", "intake_id", "target_kind"], ["m04_classification_revisions.revision_id", "m04_classification_revisions.client_id", "m04_classification_revisions.intake_id", "m04_classification_revisions.target_kind"], name="fk_m05_candidate_m04_target", ondelete="RESTRICT"),
        sa.UniqueConstraint("client_id", "intake_id", "target_kind", "m03_revision_id", "m04_revision_id", name="uq_m05_candidate_tuple"),
        sa.UniqueConstraint("candidate_id", "client_id", "subject_id", name="uq_m05_candidate_identity_subject"),
    )
    op.create_index("ix_m05_candidate_subject_precedence", "m05_candidate_links", ["subject_id", "statement_date", "m03_decided_at"])

    op.create_table(
        "m05_ledger_revisions",
        sa.Column("revision_id", sa.String(64), primary_key=True),
        sa.Column("subject_id", sa.String(64), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("candidate_id", sa.String(72), nullable=False),
        sa.Column("intake_id", sa.String(64), nullable=False),
        sa.Column("target_kind", sa.String(32), nullable=False),
        sa.Column("m03_revision_id", sa.String(64), nullable=False),
        sa.Column("m04_revision_id", sa.String(64), nullable=False),
        sa.Column("predecessor_revision_id", sa.String(64), nullable=True),
        sa.Column("revision_sequence", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("action_type", sa.String(32), nullable=False),
        sa.Column("provider_name", sa.String(255), nullable=False),
        sa.Column("account_reference", sa.String(255), nullable=False),
        sa.Column("product_context", sa.JSON(), nullable=False),
        sa.Column("statement_date", sa.Date(), nullable=False),
        sa.Column("evaluation_date", sa.Date(), nullable=False),
        sa.Column("is_stale", sa.Boolean(), nullable=False),
        sa.Column("source_snapshot_digest", sa.String(64), nullable=False),
        sa.Column("mapping_digest", sa.String(64), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("currency_confirmed", sa.Boolean(), nullable=False),
        sa.Column("currency_confirmation_evidence", sa.JSON(), nullable=False),
        sa.Column("source_total_state", sa.String(32), nullable=False),
        sa.Column("source_total_value", sa.Numeric(20, 2), nullable=True),
        sa.Column("effective_total_state", sa.String(32), nullable=False),
        sa.Column("effective_total_value", sa.Numeric(20, 2), nullable=True),
        sa.Column("signed_discrepancy", sa.Numeric(20, 2), nullable=True),
        sa.Column("absolute_discrepancy", sa.Numeric(20, 2), nullable=True),
        sa.Column("tolerance_satisfied", sa.Boolean(), nullable=True),
        sa.Column("algorithm_version", sa.String(64), nullable=False),
        sa.Column("included_evidence", sa.JSON(), nullable=False),
        sa.Column("excluded_evidence", sa.JSON(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("warning_dispositions", sa.JSON(), nullable=False),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("evidence_digest", sa.String(64), nullable=False),
        sa.Column("reason_code", sa.String(128), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("actor", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("state IN ('draft','reconciled','warning_reviewed','blocked','superseded')", name="ck_m05_revision_state"),
        sa.CheckConstraint("action_type IN ('start','reconcile','review_warning','mark_blocked','adjust','supersede','revalidate')", name="ck_m05_revision_action"),
        sa.CheckConstraint("target_kind = 'manual_record_review'", name="ck_m05_revision_target_kind"),
        sa.CheckConstraint("currency = 'ILS'", name="ck_m05_revision_currency"),
        sa.CheckConstraint("(revision_sequence = 1 AND predecessor_revision_id IS NULL AND action_type = 'start' AND state = 'draft') OR (revision_sequence > 1 AND predecessor_revision_id IS NOT NULL)", name="ck_m05_revision_shape"),
        sa.CheckConstraint("absolute_discrepancy IS NULL OR absolute_discrepancy >= 0", name="ck_m05_revision_absolute_discrepancy"),
        sa.CheckConstraint("length(evidence_digest) = 64 AND evidence_digest = lower(evidence_digest)", name="ck_m05_revision_evidence_digest"),
        sa.ForeignKeyConstraint(["subject_id", "client_id"], ["m05_ledger_subjects.subject_id", "m05_ledger_subjects.client_id"], name="fk_m05_revision_subject_client", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["candidate_id", "client_id", "subject_id"], ["m05_candidate_links.candidate_id", "m05_candidate_links.client_id", "m05_candidate_links.subject_id"], name="fk_m05_revision_candidate_subject", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["predecessor_revision_id", "client_id", "subject_id"], ["m05_ledger_revisions.revision_id", "m05_ledger_revisions.client_id", "m05_ledger_revisions.subject_id"], name="fk_m05_revision_predecessor_subject", ondelete="RESTRICT"),
        sa.UniqueConstraint("subject_id", "revision_sequence", name="uq_m05_revision_subject_sequence"),
        sa.UniqueConstraint("predecessor_revision_id", name="uq_m05_revision_predecessor_child"),
        sa.UniqueConstraint("revision_id", "client_id", "subject_id", name="uq_m05_revision_identity_subject"),
    )
    op.create_index("ix_m05_revision_client_subject", "m05_ledger_revisions", ["client_id", "subject_id", "revision_sequence"])

    op.create_table(
        "m05_ledger_values",
        sa.Column("value_id", sa.String(64), primary_key=True),
        sa.Column("revision_id", sa.String(64), nullable=False),
        sa.Column("subject_id", sa.String(64), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("evidence_identity", sa.String(255), nullable=False),
        sa.Column("component_index", sa.Integer(), nullable=True),
        sa.Column("original_label", sa.String(255), nullable=True),
        sa.Column("original_code", sa.String(128), nullable=True),
        sa.Column("component_kind", sa.String(64), nullable=False),
        sa.Column("source_state", sa.String(32), nullable=False),
        sa.Column("source_value", sa.Numeric(20, 2), nullable=True),
        sa.Column("effective_state", sa.String(32), nullable=False),
        sa.Column("effective_value", sa.Numeric(20, 2), nullable=True),
        sa.Column("included_in_reconciliation", sa.Boolean(), nullable=False),
        sa.Column("exclusion_reason", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("component_kind IN ('total_balance','contribution_component','severance_component','unknown_component')", name="ck_m05_value_component_kind"),
        sa.CheckConstraint("source_state IN ('recorded_value','recorded_zero','missing','excluded','malformed')", name="ck_m05_value_source_state"),
        sa.CheckConstraint("effective_state IN ('recorded_value','recorded_zero','missing','excluded','malformed')", name="ck_m05_value_effective_state"),
        sa.CheckConstraint("(source_state IN ('recorded_value','recorded_zero') AND source_value IS NOT NULL) OR (source_state NOT IN ('recorded_value','recorded_zero') AND source_value IS NULL)", name="ck_m05_value_source_shape"),
        sa.CheckConstraint("(effective_state IN ('recorded_value','recorded_zero') AND effective_value IS NOT NULL) OR (effective_state NOT IN ('recorded_value','recorded_zero') AND effective_value IS NULL)", name="ck_m05_value_effective_shape"),
        sa.ForeignKeyConstraint(["revision_id", "client_id", "subject_id"], ["m05_ledger_revisions.revision_id", "m05_ledger_revisions.client_id", "m05_ledger_revisions.subject_id"], name="fk_m05_value_revision_subject", ondelete="RESTRICT"),
        sa.UniqueConstraint("revision_id", "evidence_identity", name="uq_m05_value_revision_identity"),
        sa.UniqueConstraint("value_id", "client_id", "subject_id", name="uq_m05_value_identity_subject"),
    )
    op.create_index("ix_m05_value_revision", "m05_ledger_values", ["revision_id", "component_index"])

    op.create_table(
        "m05_adjustment_evidence",
        sa.Column("adjustment_id", sa.String(64), primary_key=True),
        sa.Column("revision_id", sa.String(64), nullable=False),
        sa.Column("subject_id", sa.String(64), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("evidence_identity", sa.String(255), nullable=False),
        sa.Column("previous_effective_value", sa.Numeric(20, 2), nullable=False),
        sa.Column("new_effective_value", sa.Numeric(20, 2), nullable=False),
        sa.Column("reason_code", sa.String(128), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("confirmed", sa.Boolean(), nullable=False),
        sa.Column("actor", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["revision_id", "client_id", "subject_id"], ["m05_ledger_revisions.revision_id", "m05_ledger_revisions.client_id", "m05_ledger_revisions.subject_id"], name="fk_m05_adjustment_revision_subject", ondelete="RESTRICT"),
        sa.UniqueConstraint("revision_id", name="uq_m05_adjustment_revision"),
    )
    op.create_index("ix_m05_adjustment_subject", "m05_adjustment_evidence", ["subject_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_m05_adjustment_subject", table_name="m05_adjustment_evidence")
    op.drop_table("m05_adjustment_evidence")
    op.drop_index("ix_m05_value_revision", table_name="m05_ledger_values")
    op.drop_table("m05_ledger_values")
    op.drop_index("ix_m05_revision_client_subject", table_name="m05_ledger_revisions")
    op.drop_table("m05_ledger_revisions")
    op.drop_index("ix_m05_candidate_subject_precedence", table_name="m05_candidate_links")
    op.drop_table("m05_candidate_links")
    op.drop_index("ix_m05_subject_client", table_name="m05_ledger_subjects")
    op.drop_table("m05_ledger_subjects")
