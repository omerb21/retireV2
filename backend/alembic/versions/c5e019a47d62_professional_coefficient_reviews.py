"""SC-05E documentary professional coefficient reviews, no authority.

Revision ID: c5e019a47d62
Revises: b7c5e1a90342
"""
from alembic import op
import os
import re
import sqlalchemy as sa

revision = "c5e019a47d62"
down_revision = "b7c5e1a90342"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "scenario_coefficient_professional_reviews",
        sa.Column("review_id", sa.String(64), primary_key=True),
        sa.Column("scenario_id", sa.String(64),
                  sa.ForeignKey("scenario_drafts.scenario_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("client_id", sa.Integer(),
                  sa.ForeignKey("clients.client_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("scenario_version", sa.Integer(), nullable=False),
        sa.Column("decision_id", sa.String(64), nullable=False),
        sa.Column("product_id", sa.String(64), nullable=False),
        sa.Column("component_id", sa.String(64), nullable=False),
        sa.Column("product_version", sa.Integer(), nullable=False),
        sa.Column("manifest_fingerprint", sa.String(64), nullable=False),
        sa.Column("inventory_fingerprint", sa.String(64), nullable=False),
        sa.Column("election_fingerprint", sa.String(64), nullable=False),
        sa.Column("source_fingerprint", sa.String(64), nullable=False),
        sa.Column("professional_actor_id", sa.String(128), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("review_reference", sa.String(128), nullable=False),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("record_fingerprint", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.UniqueConstraint("scenario_id", "decision_id", "scenario_version",
                            "record_fingerprint", name="uq_scenario_coefficient_review_evidence"),
        sa.CheckConstraint("scenario_version > 0", name="ck_scenario_coefficient_review_version"),
        sa.CheckConstraint("product_version > 0", name="ck_scenario_coefficient_review_product_version"),
        sa.CheckConstraint("decision IN ('reviewed_for_candidate','rejected')",
                           name="ck_scenario_coefficient_review_decision"),
    )
    op.create_index("ix_scenario_coefficient_professional_reviews_scenario_id",
                    "scenario_coefficient_professional_reviews", ["scenario_id"])
    if op.get_bind().dialect.name == "postgresql":
        role = os.environ.get("CRTISBA_APPLICATION_DB_ROLE")
        if not role or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,62}", role) is None:
            raise RuntimeError("CRTISBA_APPLICATION_DB_ROLE must be a valid explicit PostgreSQL role")
        quoted = op.get_bind().dialect.identifier_preparer.quote_identifier(role)
        op.execute(f"REVOKE ALL PRIVILEGES ON TABLE scenario_coefficient_professional_reviews FROM {quoted}")
        op.execute(f"GRANT SELECT, INSERT ON TABLE scenario_coefficient_professional_reviews TO {quoted}")



def downgrade():
    op.drop_index("ix_scenario_coefficient_professional_reviews_scenario_id",
                  table_name="scenario_coefficient_professional_reviews")
    op.drop_table("scenario_coefficient_professional_reviews")
