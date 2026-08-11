"""add PKG-013 deterministic monthly cashflow persistence

Revision ID: a7c9e1f3b805
Revises: f9a1c3e5b702
Create Date: 2026-08-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op


revision: str = "a7c9e1f3b805"
down_revision: str | None = "f9a1c3e5b702"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("m06_calculation_manifests") as batch_op:
        batch_op.add_column(
            sa.Column("authoritative_monthly_amount", sa.Text(), nullable=True)
        )

    op.create_table(
        "m09_resolved_component_inventories",
        sa.Column("inventory_id", sa.String(64), primary_key=True),
        sa.Column(
            "client_id",
            sa.Integer(),
            sa.ForeignKey("clients.client_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("scenario_family", sa.String(64), nullable=False),
        sa.Column("scenario_contract_version", sa.String(32), nullable=False),
        sa.Column("start_month", sa.String(7), nullable=False),
        sa.Column("end_month", sa.String(7), nullable=False),
        sa.Column("component_domain_contract_version", sa.String(64), nullable=False),
        sa.Column("assessment_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor", sa.String(128), nullable=False),
        sa.Column("inventory_payload", sa.JSON(), nullable=False),
        sa.Column("inventory_fingerprint", sa.String(64), nullable=False),
        sa.Column("complete", sa.Boolean(), nullable=False),
        sa.Column("blocker_codes", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            "scenario_family = 'deterministic_monthly_cashflow'",
            name="ck_m09_inventory_family",
        ),
        sa.CheckConstraint(
            "scenario_contract_version = 'v1'",
            name="ck_m09_inventory_version",
        ),
        sa.CheckConstraint(
            "length(inventory_fingerprint) = 64",
            name="ck_m09_inventory_fingerprint",
        ),
        sa.UniqueConstraint(
            "inventory_id", "client_id", name="uq_m09_inventory_identity_client"
        ),
    )
    op.create_index(
        "ix_m09_inventory_client",
        "m09_resolved_component_inventories",
        ["client_id", "assessment_timestamp"],
    )

    op.create_table(
        "m09_scenario_runs",
        sa.Column("run_id", sa.String(64), primary_key=True),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("predecessor_run_id", sa.String(64), nullable=True),
        sa.Column("run_sequence", sa.Integer(), nullable=False),
        sa.Column("scenario_family", sa.String(64), nullable=False),
        sa.Column("scenario_contract_version", sa.String(32), nullable=False),
        sa.Column("start_month", sa.String(7), nullable=False),
        sa.Column("end_month", sa.String(7), nullable=False),
        sa.Column("inventory_id", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("assumption_manifest", sa.JSON(), nullable=False),
        sa.Column("assumption_manifest_fingerprint", sa.String(64), nullable=False),
        sa.Column("upstream_snapshot", sa.JSON(), nullable=False),
        sa.Column("upstream_snapshot_fingerprint", sa.String(64), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("blocker_codes", sa.JSON(), nullable=False),
        sa.Column("range_totals", sa.JSON(none_as_null=True), nullable=True),
        sa.Column("semantic_result_fingerprint", sa.String(64), nullable=True),
        sa.Column("result_integrity_fingerprint", sa.String(64), nullable=True),
        sa.Column("actor", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "scenario_family = 'deterministic_monthly_cashflow'",
            name="ck_m09_run_family",
        ),
        sa.CheckConstraint(
            "scenario_contract_version = 'v1'",
            name="ck_m09_run_version",
        ),
        sa.CheckConstraint(
            "status IN ('success_complete','validation_failed','dependency_failed','calculation_failed','unsupported')",
            name="ck_m09_run_status",
        ),
        sa.CheckConstraint(
            "length(assumption_manifest_fingerprint) = 64 AND length(upstream_snapshot_fingerprint) = 64",
            name="ck_m09_run_required_fingerprints",
        ),
        sa.CheckConstraint(
            "(status = 'success_complete' AND range_totals IS NOT NULL AND semantic_result_fingerprint IS NOT NULL AND result_integrity_fingerprint IS NOT NULL) OR (status <> 'success_complete' AND range_totals IS NULL AND semantic_result_fingerprint IS NULL AND result_integrity_fingerprint IS NULL)",
            name="ck_m09_run_result_shape",
        ),
        sa.ForeignKeyConstraint(
            ["inventory_id", "client_id"],
            [
                "m09_resolved_component_inventories.inventory_id",
                "m09_resolved_component_inventories.client_id",
            ],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["predecessor_run_id", "client_id"],
            ["m09_scenario_runs.run_id", "m09_scenario_runs.client_id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("run_id", "client_id", name="uq_m09_run_identity_client"),
        sa.UniqueConstraint(
            "client_id",
            "scenario_family",
            "scenario_contract_version",
            "run_sequence",
            name="uq_m09_run_client_family_sequence",
        ),
        sa.UniqueConstraint(
            "predecessor_run_id", name="uq_m09_run_predecessor_child"
        ),
    )
    op.create_index(
        "ix_m09_run_client", "m09_scenario_runs", ["client_id", "created_at"]
    )

    op.create_table(
        "m09_monthly_results",
        sa.Column("monthly_result_id", sa.String(64), primary_key=True),
        sa.Column("run_id", sa.String(64), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("month", sa.String(7), nullable=False),
        sa.Column("gross_inflow_total", sa.Numeric(20, 2), nullable=False),
        sa.Column("gross_outflow_total", sa.Numeric(20, 2), nullable=False),
        sa.Column("period_net", sa.Numeric(20, 2), nullable=False),
        sa.Column("component_evidence", sa.JSON(), nullable=False),
        sa.Column("result_fingerprint", sa.String(64), nullable=False),
        sa.CheckConstraint(
            "length(result_fingerprint) = 64",
            name="ck_m09_month_result_fingerprint",
        ),
        sa.ForeignKeyConstraint(
            ["run_id", "client_id"],
            ["m09_scenario_runs.run_id", "m09_scenario_runs.client_id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("run_id", "month", name="uq_m09_run_month"),
    )
    op.create_index(
        "ix_m09_monthly_run",
        "m09_monthly_results",
        ["client_id", "run_id", "month"],
    )


def downgrade() -> None:
    if not context.get_context().as_sql:
        connection = op.get_bind()
        inventory_count = connection.execute(
            sa.text("SELECT COUNT(*) FROM m09_resolved_component_inventories")
        ).scalar_one()
        run_count = connection.execute(
            sa.text("SELECT COUNT(*) FROM m09_scenario_runs")
        ).scalar_one()
        if inventory_count or run_count:
            raise RuntimeError(
                "cannot downgrade while PKG-013 inventory or run evidence exists"
            )

    op.drop_index("ix_m09_monthly_run", table_name="m09_monthly_results")
    op.drop_table("m09_monthly_results")
    op.drop_index("ix_m09_run_client", table_name="m09_scenario_runs")
    op.drop_table("m09_scenario_runs")
    op.drop_index(
        "ix_m09_inventory_client",
        table_name="m09_resolved_component_inventories",
    )
    op.drop_table("m09_resolved_component_inventories")
    if context.get_context().as_sql:
        op.drop_column("m06_calculation_manifests", "authoritative_monthly_amount")
    else:
        with op.batch_alter_table("m06_calculation_manifests") as batch_op:
            batch_op.drop_column("authoritative_monthly_amount")
