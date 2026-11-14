"""Supervisor 108: extend existing fixation review ledger with bounded internal approval.

Revision ID: a108c7e5d2b9
Revises: e53f1c0a7d23
No new approval tables. Existing append-only revision trigger is retained.
"""
from alembic import op
import sqlalchemy as sa

revision = "a108c7e5d2b9"
down_revision = "e53f1c0a7d23"
branch_labels = None
depends_on = None


def upgrade():
    # APPROVED_INTERNAL is 17 characters; the original review ledger used
    # VARCHAR(16) for DRAFT/BLOCKED and must be widened before accepting the
    # new bounded internal status.
    op.alter_column("scenario_fixation_approval_heads", "status",
                    existing_type=sa.String(length=16),
                    type_=sa.String(length=32), existing_nullable=False)
    op.alter_column("scenario_fixation_approval_revisions", "status",
                    existing_type=sa.String(length=16),
                    type_=sa.String(length=32), existing_nullable=False)
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
    op.alter_column("scenario_fixation_approval_revisions", "status",
                    existing_type=sa.String(length=32),
                    type_=sa.String(length=16), existing_nullable=False)
    op.alter_column("scenario_fixation_approval_heads", "status",
                    existing_type=sa.String(length=32),
                    type_=sa.String(length=16), existing_nullable=False)
