"""Merge existing migration head with independent scenario draft head.

Revision ID: f6a9c4d2e107
Revises: d2c4e6a8b031, e2f8a6c1d405

Schema-neutral merge: both predecessor migrations remain intact.
"""
revision = "f6a9c4d2e107"
down_revision = ("d2c4e6a8b031", "e2f8a6c1d405")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
