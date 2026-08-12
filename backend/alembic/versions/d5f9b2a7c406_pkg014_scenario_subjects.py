"""add PKG-014 immutable scenario subjects

Revision ID: d5f9b2a7c406
Revises: c4e8a1f6d203
Create Date: 2026-08-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op

revision: str = "d5f9b2a7c406"
down_revision: str | None = "c4e8a1f6d203"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ("m09_scenario_subjects", "m09_scenario_adjustments", "m09_subject_runs", "m09_subject_monthly_results")


def upgrade() -> None:
    op.create_table(
        "m09_scenario_subjects",
        sa.Column("scenario_subject_id", sa.String(64), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.client_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("scenario_family", sa.String(64), nullable=False),
        sa.Column("scenario_contract_version", sa.String(32), nullable=False),
        sa.Column("subject_type", sa.String(16), nullable=False),
        sa.Column("display_label", sa.String(160)),
        sa.Column("adjustment_manifest", sa.JSON(), nullable=False),
        sa.Column("adjustment_manifest_fingerprint", sa.String(64), nullable=False),
        sa.Column("calculation_semantic_fingerprint", sa.String(64), nullable=False),
        sa.Column("integrity_fingerprint", sa.String(64), nullable=False),
        sa.Column("provenance", sa.String(64), nullable=False),
        sa.Column("actor", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("scenario_family = 'declared_retirement_cashflow_adjustments'", name="ck_m09_subject_family"),
        sa.CheckConstraint("scenario_contract_version = 'v1'", name="ck_m09_subject_version"),
        sa.CheckConstraint("subject_type IN ('baseline','adjusted')", name="ck_m09_subject_type"),
        sa.CheckConstraint("length(calculation_semantic_fingerprint) = 64 AND length(integrity_fingerprint) = 64 AND length(adjustment_manifest_fingerprint) = 64", name="ck_m09_subject_fingerprints"),
        sa.UniqueConstraint("scenario_subject_id", "client_id", name="uq_m09_subject_identity_client"),
        sa.UniqueConstraint("client_id", "scenario_family", "scenario_contract_version", "calculation_semantic_fingerprint", name="uq_m09_subject_semantics"),
    )
    op.create_index("ix_m09_subject_client", "m09_scenario_subjects", ["client_id", "created_at"])
    op.create_index("uq_m09_subject_baseline", "m09_scenario_subjects", ["client_id", "scenario_family", "scenario_contract_version"], unique=True, sqlite_where=sa.text("subject_type = 'baseline'"), postgresql_where=sa.text("subject_type = 'baseline'"))
    op.create_table(
        "m09_scenario_adjustments",
        sa.Column("adjustment_id", sa.String(64), primary_key=True),
        sa.Column("scenario_subject_id", sa.String(64), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("adjustment_type", sa.String(64), nullable=False),
        sa.Column("amount", sa.Numeric(20, 2), nullable=False),
        sa.Column("amount_text", sa.String(32), nullable=False),
        sa.Column("start_month", sa.String(7), nullable=False),
        sa.Column("end_month", sa.String(7), nullable=False),
        sa.Column("provenance", sa.String(64), nullable=False),
        sa.Column("semantic_fingerprint", sa.String(64), nullable=False),
        sa.Column("actor", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("adjustment_type IN ('declared_additional_monthly_income','declared_additional_monthly_expense')", name="ck_m09_adjustment_type"),
        sa.CheckConstraint("amount >= 0.01 AND amount <= 999999999999999999.99", name="ck_m09_adjustment_amount"),
        sa.CheckConstraint("length(semantic_fingerprint) = 64", name="ck_m09_adjustment_fingerprint"),
        sa.ForeignKeyConstraint(["scenario_subject_id", "client_id"], ["m09_scenario_subjects.scenario_subject_id", "m09_scenario_subjects.client_id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("scenario_subject_id", "adjustment_id", name="uq_m09_subject_adjustment"),
        sa.UniqueConstraint("scenario_subject_id", "ordinal", name="uq_m09_subject_adjustment_ordinal"),
    )
    op.create_index("ix_m09_adjustment_subject", "m09_scenario_adjustments", ["client_id", "scenario_subject_id", "ordinal"])
    op.create_table(
        "m09_subject_runs",
        sa.Column("run_id", sa.String(64), primary_key=True),
        sa.Column("scenario_subject_id", sa.String(64), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("predecessor_run_id", sa.String(64)),
        sa.Column("run_sequence", sa.Integer(), nullable=False),
        sa.Column("scenario_family", sa.String(64), nullable=False),
        sa.Column("scenario_contract_version", sa.String(32), nullable=False),
        sa.Column("start_month", sa.String(7), nullable=False),
        sa.Column("end_month", sa.String(7), nullable=False),
        sa.Column("component_domain_contract_version", sa.String(64), nullable=False),
        sa.Column("factual_inventory", sa.JSON(), nullable=False),
        sa.Column("factual_inventory_fingerprint", sa.String(64), nullable=False),
        sa.Column("factual_baseline_material_fingerprint", sa.String(64), nullable=False),
        sa.Column("adjustment_manifest", sa.JSON(), nullable=False),
        sa.Column("adjustment_manifest_fingerprint", sa.String(64), nullable=False),
        sa.Column("upstream_snapshot", sa.JSON(), nullable=False),
        sa.Column("upstream_snapshot_fingerprint", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("blocker_codes", sa.JSON(), nullable=False),
        sa.Column("range_totals", sa.JSON(none_as_null=True)),
        sa.Column("semantic_result_fingerprint", sa.String(64)),
        sa.Column("result_integrity_fingerprint", sa.String(64)),
        sa.Column("actor", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("scenario_family = 'declared_retirement_cashflow_adjustments'", name="ck_m09_subject_run_family"),
        sa.CheckConstraint("scenario_contract_version = 'v1'", name="ck_m09_subject_run_version"),
        sa.CheckConstraint("status IN ('success_complete','validation_failed','dependency_failed','calculation_failed','unsupported')", name="ck_m09_subject_run_status"),
        sa.CheckConstraint("length(factual_inventory_fingerprint) = 64 AND length(factual_baseline_material_fingerprint) = 64 AND length(adjustment_manifest_fingerprint) = 64 AND length(upstream_snapshot_fingerprint) = 64", name="ck_m09_subject_run_fingerprints"),
        sa.CheckConstraint("(status = 'success_complete' AND range_totals IS NOT NULL AND semantic_result_fingerprint IS NOT NULL AND result_integrity_fingerprint IS NOT NULL) OR (status <> 'success_complete' AND range_totals IS NULL AND semantic_result_fingerprint IS NULL AND result_integrity_fingerprint IS NULL)", name="ck_m09_subject_run_shape"),
        sa.ForeignKeyConstraint(["scenario_subject_id", "client_id"], ["m09_scenario_subjects.scenario_subject_id", "m09_scenario_subjects.client_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["predecessor_run_id", "scenario_subject_id", "client_id"], ["m09_subject_runs.run_id", "m09_subject_runs.scenario_subject_id", "m09_subject_runs.client_id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("run_id", "scenario_subject_id", "client_id", name="uq_m09_subject_run_identity"),
        sa.UniqueConstraint("scenario_subject_id", "run_sequence", name="uq_m09_subject_run_sequence"),
        sa.UniqueConstraint("predecessor_run_id", name="uq_m09_subject_run_predecessor"),
    )
    op.create_index("ix_m09_subject_run_client", "m09_subject_runs", ["client_id", "scenario_subject_id", "created_at"])
    op.create_table(
        "m09_subject_monthly_results",
        sa.Column("monthly_result_id", sa.String(64), primary_key=True),
        sa.Column("run_id", sa.String(64), nullable=False),
        sa.Column("scenario_subject_id", sa.String(64), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("month", sa.String(7), nullable=False),
        sa.Column("gross_inflow_total", sa.Numeric(20, 2), nullable=False),
        sa.Column("gross_outflow_total", sa.Numeric(20, 2), nullable=False),
        sa.Column("period_net", sa.Numeric(20, 2), nullable=False),
        sa.Column("component_evidence", sa.JSON(), nullable=False),
        sa.Column("result_fingerprint", sa.String(64), nullable=False),
        sa.CheckConstraint("length(result_fingerprint) = 64", name="ck_m09_subject_month_fingerprint"),
        sa.ForeignKeyConstraint(["run_id", "scenario_subject_id", "client_id"], ["m09_subject_runs.run_id", "m09_subject_runs.scenario_subject_id", "m09_subject_runs.client_id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("run_id", "month", name="uq_m09_subject_run_month"),
    )
    dialect = op.get_context().dialect.name
    if dialect == "postgresql":
        op.execute("CREATE FUNCTION m09_subject_reject_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'm09_subject_append_only_violation' USING ERRCODE = '55000'; END; $$")
        for table in TABLES:
            op.execute(f"CREATE TRIGGER trg_{table}_append_only BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION m09_subject_reject_mutation()")
    else:
        for table in TABLES:
            op.execute(f"CREATE TRIGGER trg_{table}_no_update BEFORE UPDATE ON {table} BEGIN SELECT RAISE(ABORT, 'm09_subject_append_only_violation'); END")
            op.execute(f"CREATE TRIGGER trg_{table}_no_delete BEFORE DELETE ON {table} BEGIN SELECT RAISE(ABORT, 'm09_subject_append_only_violation'); END")


def downgrade() -> None:
    if not context.get_context().as_sql:
        connection = op.get_bind()
        if any(connection.execute(sa.text(f"SELECT COUNT(*) FROM {table}")).scalar_one() for table in TABLES):
            raise RuntimeError("cannot downgrade while PKG-014 subject or run evidence exists")
    dialect = op.get_context().dialect.name
    if dialect == "postgresql":
        for table in reversed(TABLES):
            op.execute(f"DROP TRIGGER trg_{table}_append_only ON {table}")
        op.execute("DROP FUNCTION m09_subject_reject_mutation()")
    else:
        for table in reversed(TABLES):
            op.execute(f"DROP TRIGGER trg_{table}_no_delete")
            op.execute(f"DROP TRIGGER trg_{table}_no_update")
    op.drop_table("m09_subject_monthly_results")
    op.drop_index("ix_m09_subject_run_client", table_name="m09_subject_runs")
    op.drop_table("m09_subject_runs")
    op.drop_index("ix_m09_adjustment_subject", table_name="m09_scenario_adjustments")
    op.drop_table("m09_scenario_adjustments")
    op.drop_index("ix_m09_subject_client", table_name="m09_scenario_subjects")
    op.drop_index("uq_m09_subject_baseline", table_name="m09_scenario_subjects")
    op.drop_table("m09_scenario_subjects")
