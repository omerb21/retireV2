"""Explicit retirement target decision; no inference or backfill."""
from alembic import op
import sqlalchemy as sa

revision = "c8d4f1a7b965"
down_revision = "b7c3e0f6a854"
branch_labels = None
depends_on = None
FIELDS = ("retirement_target_date", "retirement_target_decision_actor",
          "retirement_target_decided_at", "retirement_target_reference_fingerprint")


def upgrade():
    for name, datatype in zip(FIELDS, (sa.Date(), sa.String(128), sa.DateTime(timezone=True), sa.String(64))):
        op.add_column("planning_input_decisions", sa.Column(name, datatype, nullable=True))


def downgrade():
    condition = " OR ".join(f"{name} IS NOT NULL" for name in FIELDS)
    if op.get_bind().execute(sa.text(f"SELECT 1 FROM planning_input_decisions WHERE {condition} LIMIT 1")).first():
        raise RuntimeError("TARGET_DOWNGRADE_WOULD_LOSE_DECISION")
    with op.batch_alter_table("planning_input_decisions") as batch:
        for name in reversed(FIELDS):
            batch.drop_column(name)
