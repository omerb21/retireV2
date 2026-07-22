"""add PKG-003 fixation dependency manifests

Revision ID: d7a3c9e5f102
Revises: c2f8a4d1e706
Create Date: 2026-07-22 18:00:00.000000

Existing runs remain unchanged and have no fabricated manifest. Downgrade is
refused while manifests exist because dropping the table would destroy the
immutable dependency evidence.
"""

from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "d7a3c9e5f102"
down_revision: Union[str, None] = "c2f8a4d1e706"
branch_labels: Union[str, tuple[str, ...], None] = None
depends_on: Union[str, tuple[str, ...], None] = None


def upgrade() -> None:
    op.create_table(
        "fixation_dependency_manifests",
        sa.Column("fixation_dependency_manifest_id", sa.String(length=64), nullable=False),
        sa.Column("fixation_run_id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("manifest_schema_version", sa.String(length=64), nullable=False),
        sa.Column("fingerprint_algorithm_version", sa.String(length=64), nullable=False),
        sa.Column("manifest_fingerprint", sa.String(length=64), nullable=True),
        sa.Column("manifest_payload", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["client_id"], ["clients.client_id"]),
        sa.ForeignKeyConstraint(["fixation_run_id"], ["fixation_runs.id"]),
        sa.PrimaryKeyConstraint("fixation_dependency_manifest_id"),
        sa.UniqueConstraint("fixation_run_id"),
    )


def downgrade() -> None:
    connection = op.get_bind()
    manifest_count = connection.execute(
        sa.text("SELECT COUNT(*) FROM fixation_dependency_manifests")
    ).scalar_one()
    if manifest_count:
        raise RuntimeError("Cannot downgrade while PKG-003 dependency manifests are present")
    op.drop_table("fixation_dependency_manifests")
