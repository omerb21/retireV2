"""SC-05C isolated pension election drafts.

Revision ID: b7c5e1a90342
Revises: f6a9c4d2e107
"""
from alembic import op
import os
import re
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
    if op.get_bind().dialect.name == "postgresql":
        role = os.environ.get("CRTISBA_APPLICATION_DB_ROLE")
        if not role or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,62}", role) is None:
            raise RuntimeError("CRTISBA_APPLICATION_DB_ROLE must be a valid explicit PostgreSQL role")
        quoted = op.get_bind().dialect.identifier_preparer.quote_identifier(role)
        op.execute(f"REVOKE ALL PRIVILEGES ON TABLE scenario_draft_pension_elections FROM {quoted}")
        op.execute(f"GRANT SELECT, INSERT, DELETE ON TABLE scenario_draft_pension_elections TO {quoted}")



def downgrade():
    op.drop_index("ix_scenario_draft_pension_elections_scenario_id",
                  table_name="scenario_draft_pension_elections")
    op.drop_table("scenario_draft_pension_elections")
