"""Explicit planning decisions and incomplete capital valuation support."""
from alembic import op
import sqlalchemy as sa

revision = "b7c3e0f6a854"
down_revision = "a6b2d9e5f743"
branch_labels = None
depends_on = None
CONSTRAINT = "ck_capital_asset_value_date_required"


def capital_constraint(*, restore):
    connection = op.get_bind()
    triggers = []
    if connection.dialect.name == "sqlite":
        triggers = connection.execute(sa.text("SELECT name, sql FROM sqlite_master WHERE type='trigger' AND sql LIKE '%capital_asset%' ORDER BY name")).all()
        for name, _ in triggers:
            connection.exec_driver_sql('DROP TRIGGER "' + name.replace('"', '""') + '"')
    with op.batch_alter_table("capital_asset") as batch:
        if restore:
            batch.create_check_constraint(CONSTRAINT, "known_value_amount IS NULL OR value_as_of_date IS NOT NULL")
        else:
            batch.drop_constraint(CONSTRAINT, type_="check")
    for _, sql in triggers:
        connection.exec_driver_sql(sql)


def upgrade():
    capital_constraint(restore=False)
    op.create_table("planning_input_decisions",
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.client_id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False), sa.Column("planning_base_date", sa.Date()),
        sa.Column("actor", sa.String(128), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("version > 0", name="ck_planning_decision_version"))
    op.create_table("pension_income_resolutions",
        sa.Column("income_id", sa.Integer(), sa.ForeignKey("recurring_income.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.client_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False), sa.Column("decision_kind", sa.String(64), nullable=False),
        sa.Column("income_fingerprint", sa.String(64), nullable=False),
        sa.Column("canonical_source_id", sa.String(128)), sa.Column("canonical_fingerprint", sa.String(64)),
        sa.Column("reference", sa.String(512), nullable=False), sa.Column("actor", sa.String(128), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("version > 0", name="ck_pension_resolution_version"),
        sa.CheckConstraint("decision_kind IN ('SAME_CANONICAL_PENSION','PENSION_NOT_YET_CANONICAL','MISCLASSIFIED_GENERAL_INCOME')", name="ck_pension_resolution_kind"))
    op.create_index("ix_pension_income_resolutions_client_id", "pension_income_resolutions", ["client_id"])


def downgrade():
    connection = op.get_bind()
    if connection.execute(sa.text("SELECT 1 FROM capital_asset WHERE known_value_amount IS NOT NULL AND value_as_of_date IS NULL LIMIT 1")).first():
        raise RuntimeError("PLANNING_DOWNGRADE_INCOMPLETE_CAPITAL")
    for table in ("planning_input_decisions", "pension_income_resolutions"):
        if connection.execute(sa.text(f"SELECT 1 FROM {table} LIMIT 1")).first():
            raise RuntimeError("PLANNING_DOWNGRADE_WOULD_LOSE_DECISIONS")
    capital_constraint(restore=True)
    op.drop_table("pension_income_resolutions")
    op.drop_table("planning_input_decisions")
