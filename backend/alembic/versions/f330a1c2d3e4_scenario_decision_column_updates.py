"""Permit bounded updates of current scenario decision values.

Revision ID: f330a1c2d3e4
Revises: d277e1a6f003
"""
import os
import re

from alembic import op


revision = "f330a1c2d3e4"
down_revision = "d277e1a6f003"
branch_labels = None
depends_on = None


TABLE = "scenario_draft_decisions"
MUTABLE_COLUMNS = (
    "amount",
    "action",
    "effective_date",
    "validation_state",
    "product_version_at_review",
    "source_fingerprint_at_review",
    "ruleset_digest_at_review",
    "permission_preview_id_at_review",
)


def _quoted_role():
    role = os.environ.get("CRTISBA_APPLICATION_DB_ROLE")
    if not role or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,62}", role) is None:
        raise RuntimeError("CRTISBA_APPLICATION_DB_ROLE must be a valid explicit PostgreSQL role")
    return op.get_bind().dialect.identifier_preparer.quote_identifier(role)


def upgrade():
    if op.get_bind().dialect.name != "postgresql":
        return
    columns = ", ".join(MUTABLE_COLUMNS)
    op.execute(f"GRANT UPDATE ({columns}) ON TABLE {TABLE} TO {_quoted_role()}")


def downgrade():
    if op.get_bind().dialect.name != "postgresql":
        return
    columns = ", ".join(MUTABLE_COLUMNS)
    op.execute(f"REVOKE UPDATE ({columns}) ON TABLE {TABLE} FROM {_quoted_role()}")
