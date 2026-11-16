"""PKG-02 atomic optimistic row versions for the four supplementary fact tables.

Revision ID: c194e2f0a816
Revises: b2d7e4c9f108

Only adds server-default version columns; preserves every existing fact value and identity.
"""
from alembic import op
import sqlalchemy as sa

revision = "c194e2f0a816"
down_revision = "b2d7e4c9f108"
branch_labels = None
depends_on = None

TABLES = ("actual_capitalizations", "capital_asset", "recurring_income", "recurring_expense")


def upgrade() -> None:
    for table in TABLES:
        op.add_column(table, sa.Column("version", sa.BigInteger(), nullable=False, server_default=sa.text("1")))
        op.create_check_constraint(f"ck_{table}_version_positive", table, "version >= 1")


def downgrade() -> None:
    bind = op.get_bind()
    for table in TABLES:
        if bind.scalar(sa.text(f"SELECT COUNT(*) FROM {table} WHERE version <> 1 OR version IS NULL")):
            raise RuntimeError("PKG02_CAS_DOWNGRADE_WOULD_LOSE_VERSION_HISTORY")
    for table in reversed(TABLES):
        op.drop_constraint(f"ck_{table}_version_positive", table, type_="check")
        op.drop_column(table, "version")
