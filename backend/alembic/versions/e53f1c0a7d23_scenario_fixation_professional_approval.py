"""Supervisor 53: versioned scenario fixation professional review drafts.

Revision ID: e53f1c0a7d23
Revises: d6f1a9c3b704
"""
from alembic import op
import sqlalchemy as sa

revision = "e53f1c0a7d23"
down_revision = "d6f1a9c3b704"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "scenario_fixation_approval_heads",
        sa.Column("approval_id", sa.String(64), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.client_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("scenario_id", sa.String(64), sa.ForeignKey("scenario_drafts.scenario_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("current_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("updated_by", sa.String(128), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("client_id", "scenario_id", name="uq_fixation_approval_client_scenario"),
        sa.CheckConstraint("current_version > 0", name="ck_fixation_approval_head_version"),
        sa.CheckConstraint("status IN ('DRAFT','BLOCKED')", name="ck_fixation_approval_head_status"),
    )
    op.create_table(
        "scenario_fixation_approval_revisions",
        sa.Column("revision_id", sa.String(64), primary_key=True),
        sa.Column("approval_id", sa.String(64), sa.ForeignKey("scenario_fixation_approval_heads.approval_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.client_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("scenario_id", sa.String(64), sa.ForeignKey("scenario_drafts.scenario_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("approval_version", sa.Integer(), nullable=False),
        sa.Column("scenario_version", sa.Integer(), nullable=False),
        sa.Column("manifest_fingerprint", sa.String(64), nullable=False),
        sa.Column("readiness_fingerprint", sa.String(64), nullable=False),
        sa.Column("dependency_fingerprint", sa.String(64), nullable=False),
        sa.Column("approval_fingerprint", sa.String(64), nullable=False),
        sa.Column("decisions_json", sa.JSON(), nullable=False),
        sa.Column("blockers_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("actor_id", sa.String(128), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("approval_id", "approval_version", name="uq_fixation_approval_revision"),
        sa.CheckConstraint("approval_version > 0", name="ck_fixation_approval_revision_version"),
        sa.CheckConstraint("scenario_version > 0", name="ck_fixation_approval_revision_scenario_version"),
        sa.CheckConstraint("status IN ('DRAFT','BLOCKED')", name="ck_fixation_approval_revision_status"),
    )
    op.create_index("ix_fixation_approval_revision_audit", "scenario_fixation_approval_revisions", ["client_id", "scenario_id", "approval_version"])
    if op.get_bind().dialect.name == "postgresql":
        op.execute("""
            CREATE FUNCTION prevent_scenario_fixation_approval_revision_mutation()
            RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                RAISE EXCEPTION 'fixation approval revisions are append-only';
            END; $$
        """)
        op.execute("""
            CREATE TRIGGER trg_scenario_fixation_approval_revision_immutable
            BEFORE UPDATE OR DELETE ON scenario_fixation_approval_revisions
            FOR EACH ROW EXECUTE FUNCTION prevent_scenario_fixation_approval_revision_mutation()
        """)


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_scenario_fixation_approval_revision_immutable ON scenario_fixation_approval_revisions")
        op.execute("DROP FUNCTION IF EXISTS prevent_scenario_fixation_approval_revision_mutation()")
    op.drop_index("ix_fixation_approval_revision_audit", table_name="scenario_fixation_approval_revisions")
    op.drop_table("scenario_fixation_approval_revisions")
    op.drop_table("scenario_fixation_approval_heads")
