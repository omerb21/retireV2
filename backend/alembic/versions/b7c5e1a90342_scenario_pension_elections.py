"""SC-05C isolated pension election drafts.

Revision ID: b7c5e1a90342
Revises: f6a9c4d2e107
"""
from alembic import op
import sqlalchemy as sa

revision = "b7c5e1a90342"
down_revision = "f6a9c4d2e107"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "scenario_draft_pension_elections",
        sa.Column("election_id", sa.String(64), primary_key=True),
        sa.Column("scenario_id", sa.String(64),
                  sa.ForeignKey("scenario_drafts.scenario_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("decision_id", sa.String(64), nullable=False),
        sa.Column("scenario_version", sa.Integer(), nullable=False),
        sa.Column("pension_start_date", sa.Date(), nullable=False),
        sa.Column("target_year", sa.Integer(), nullable=False),
        sa.Column("survivors_option", sa.String(128), nullable=False),
        sa.Column("spouse_age_diff", sa.Integer(), nullable=False),
        sa.Column("coefficient_selection", sa.String(32), nullable=False),
        sa.Column("company_name", sa.String(255)),
        sa.Column("option_name", sa.String(255)),
        sa.UniqueConstraint("scenario_id", "decision_id", name="uq_scenario_pension_election_decision"),
        sa.CheckConstraint("scenario_version > 0", name="ck_scenario_pension_election_version"),
        sa.CheckConstraint("coefficient_selection IN ('catalog_candidate','manual_review_required')",
                           name="ck_scenario_pension_election_selection"),
    )
    op.create_index("ix_scenario_draft_pension_elections_scenario_id",
                    "scenario_draft_pension_elections", ["scenario_id"])


def downgrade():
    op.drop_index("ix_scenario_draft_pension_elections_scenario_id",
                  table_name="scenario_draft_pension_elections")
    op.drop_table("scenario_draft_pension_elections")
