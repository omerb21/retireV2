"""Supervisor 108: extend existing fixation review ledger with bounded internal approval.

Revision ID: a108c7e5d2b9
Revises: e53f1c0a7d23
No new approval tables. Existing append-only revision trigger is retained.
"""
from alembic import op

revision = "a108c7e5d2b9"
down_revision = "e53f1c0a7d23"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("ck_fixation_approval_head_status",
                       "scenario_fixation_approval_heads", type_="check")
    op.create_check_constraint(
        "ck_fixation_approval_head_status", "scenario_fixation_approval_heads",
        "status IN ('DRAFT','BLOCKED','APPROVED_INTERNAL')")
    op.drop_constraint("ck_fixation_approval_revision_status",
                       "scenario_fixation_approval_revisions", type_="check")
    op.create_check_constraint(
        "ck_fixation_approval_revision_status", "scenario_fixation_approval_revisions",
        "status IN ('DRAFT','BLOCKED','APPROVED_INTERNAL')")


def downgrade():
    # Never discard immutable decisions or silently reinterpret approved records.
    op.execute("""
        DO $$ BEGIN
          IF EXISTS (SELECT 1 FROM scenario_fixation_approval_revisions
                     WHERE status = 'APPROVED_INTERNAL')
             OR EXISTS (SELECT 1 FROM scenario_fixation_approval_heads
                        WHERE status = 'APPROVED_INTERNAL') THEN
            RAISE EXCEPTION 'FIXATION_INTERNAL_APPROVAL_DOWNGRADE_BLOCKED';
          END IF;
        END $$;
    """)
    op.drop_constraint("ck_fixation_approval_revision_status",
                       "scenario_fixation_approval_revisions", type_="check")
    op.create_check_constraint(
        "ck_fixation_approval_revision_status", "scenario_fixation_approval_revisions",
        "status IN ('DRAFT','BLOCKED')")
    op.drop_constraint("ck_fixation_approval_head_status",
                       "scenario_fixation_approval_heads", type_="check")
    op.create_check_constraint(
        "ck_fixation_approval_head_status", "scenario_fixation_approval_heads",
        "status IN ('DRAFT','BLOCKED')")
