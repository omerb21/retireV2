"""Persist historical employment exempt-grant review status without changing grants.

Revision ID: d2c4e6a8b031
Revises: c4e8a2f6b731
"""
import sqlalchemy as sa
from alembic import op

revision = "d2c4e6a8b031"
down_revision = "c4e8a2f6b731"
branch_labels = None
depends_on = None

STATES = ("not_reviewed", "none", "recorded", "requires_reconciliation")


def upgrade():
    with op.batch_alter_table("employment_records") as batch:
        batch.add_column(sa.Column(
            "exempt_grant_status", sa.String(32), nullable=False,
            server_default="not_reviewed"))
        batch.create_check_constraint(
            "ck_employment_exempt_grant_status",
            "exempt_grant_status IN ('not_reviewed', 'none', 'recorded', 'requires_reconciliation')",
        )
    # Never infer 'none' from missing evidence. Existing duplicate grants stay intact.
    op.execute(sa.text("""
        UPDATE employment_records SET exempt_grant_status =
          CASE WHEN (SELECT COUNT(*) FROM grants g
                     WHERE g.employment_record_id = employment_records.employment_record_id) > 1
               THEN 'requires_reconciliation'
               WHEN (SELECT COUNT(*) FROM grants g
                     WHERE g.employment_record_id = employment_records.employment_record_id) = 1
               THEN 'recorded'
               ELSE 'not_reviewed' END
        WHERE is_current = false
    """))


def downgrade():
    with op.batch_alter_table("employment_records") as batch:
        batch.drop_constraint("ck_employment_exempt_grant_status", type_="check")
        batch.drop_column("exempt_grant_status")
