"""M11 append-only single-planner selection record.

Revision ID: b2d7e4c9f108
Revises: a108c7e5d2b9

PREPARED ONLY: must not be executed without separate supervisory approval.
"""
from alembic import op
import sqlalchemy as sa

revision = "b2d7e4c9f108"
down_revision = "a108c7e5d2b9"
branch_labels = None
depends_on = None

TABLE = "m11_preferred_scenario_revisions"

def upgrade():
    op.create_unique_constraint("uq_m11_scenario_identity_client", "scenario_drafts", ["scenario_id", "client_id"])
    op.create_table(
        TABLE,
        sa.Column("selection_id", sa.String(64), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.client_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("scenario_id", sa.String(64), nullable=False),
        sa.Column("scenario_version", sa.Integer(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False, server_default=""),
        sa.Column("calculation_references", sa.JSON(), nullable=False),
        sa.Column("actor_id", sa.String(128), nullable=False),
        sa.Column("saved_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["scenario_id", "client_id"], ["scenario_drafts.scenario_id", "scenario_drafts.client_id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("client_id", "revision", name="uq_m11_client_revision"),
        sa.CheckConstraint("revision > 0", name="ck_m11_revision_positive"),
        sa.CheckConstraint("scenario_version > 0", name="ck_m11_scenario_version_positive"),
    )
    op.create_index("ix_m11_preferred_scenario_revisions_client_id", TABLE, ["client_id"])
    if op.get_bind().dialect.name == "postgresql":
        op.execute("""
            CREATE FUNCTION m11_reject_selection_mutation()
            RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
              RAISE EXCEPTION 'M11 selections are append-only';
            END; $$
        """)
        op.execute(f"""
            CREATE TRIGGER trg_m11_selection_immutable
            BEFORE UPDATE OR DELETE ON {TABLE}
            FOR EACH ROW EXECUTE FUNCTION m11_reject_selection_mutation()
        """)

def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.execute(f"DROP TRIGGER IF EXISTS trg_m11_selection_immutable ON {TABLE}")
        op.execute("DROP FUNCTION IF EXISTS m11_reject_selection_mutation()")
    op.drop_index("ix_m11_preferred_scenario_revisions_client_id", table_name=TABLE)
    op.drop_table(TABLE)
    op.drop_constraint("uq_m11_scenario_identity_client", "scenario_drafts", type_="unique")
