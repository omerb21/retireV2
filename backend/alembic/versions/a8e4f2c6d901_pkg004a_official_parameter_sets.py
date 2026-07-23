"""add PKG-004A global official parameter sets

Revision ID: a8e4f2c6d901
Revises: d7a3c9e5f102
Create Date: 2026-07-23 10:00:00.000000

The migration is infrastructure-only: it creates no official parameter rows,
does not backfill historical fixation evidence, and refuses downgrade while
official parameter evidence exists.
"""

from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "a8e4f2c6d901"
down_revision: Union[str, None] = "d7a3c9e5f102"
branch_labels: Union[str, tuple[str, ...], None] = None
depends_on: Union[str, tuple[str, ...], None] = None


def upgrade() -> None:
    op.create_table(
        "official_parameter_sets",
        sa.Column("parameter_set_id", sa.String(length=64), nullable=False),
        sa.Column("tax_year", sa.Integer(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("parameter_set_version", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("monthly_cap", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column(
            "exemption_percentage",
            sa.Numeric(precision=18, scale=10),
            nullable=False,
        ),
        sa.Column("capital_multiplier", sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column(
            "grant_impact_multiplier",
            sa.Numeric(precision=18, scale=8),
            nullable=False,
        ),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_title", sa.String(length=512), nullable=False),
        sa.Column("official_source_reference", sa.String(length=2048), nullable=False),
        sa.Column("source_publication_date", sa.Date(), nullable=True),
        sa.Column("source_recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_evidence_metadata", sa.JSON(), nullable=False),
        sa.Column("verification_note", sa.Text(), nullable=True),
        sa.Column("parameter_payload", sa.JSON(), nullable=False),
        sa.Column("content_fingerprint", sa.String(length=64), nullable=False),
        sa.Column(
            "fingerprint_algorithm_version",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_by", sa.String(length=128), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_by", sa.String(length=128), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_by", sa.String(length=128), nullable=True),
        sa.Column("rejection_note", sa.Text(), nullable=True),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("superseded_by", sa.String(length=128), nullable=True),
        sa.CheckConstraint(
            "status IN ('draft', 'verified', 'active', 'superseded', 'rejected')",
            name="ck_official_parameter_sets_status",
        ),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_official_parameter_sets_effective_period",
        ),
        sa.CheckConstraint(
            "monthly_cap > 0",
            name="ck_official_parameter_sets_monthly_cap_positive",
        ),
        sa.CheckConstraint(
            "exemption_percentage >= 0 AND exemption_percentage <= 1",
            name="ck_official_parameter_sets_exemption_percentage_range",
        ),
        sa.CheckConstraint(
            "capital_multiplier > 0",
            name="ck_official_parameter_sets_capital_multiplier_positive",
        ),
        sa.CheckConstraint(
            "grant_impact_multiplier > 0",
            name="ck_official_parameter_sets_grant_impact_multiplier_positive",
        ),
        sa.CheckConstraint(
            "status NOT IN ('verified', 'active', 'superseded') "
            "OR (verified_at IS NOT NULL AND verified_by IS NOT NULL)",
            name="ck_official_parameter_sets_verification_evidence",
        ),
        sa.CheckConstraint(
            "status NOT IN ('active', 'superseded') "
            "OR (activated_at IS NOT NULL AND activated_by IS NOT NULL)",
            name="ck_official_parameter_sets_activation_evidence",
        ),
        sa.CheckConstraint(
            "status != 'rejected' OR (rejected_at IS NOT NULL AND rejected_by IS NOT NULL)",
            name="ck_official_parameter_sets_rejection_evidence",
        ),
        sa.CheckConstraint(
            "status != 'superseded' "
            "OR (superseded_at IS NOT NULL AND superseded_by IS NOT NULL)",
            name="ck_official_parameter_sets_supersession_evidence",
        ),
        sa.PrimaryKeyConstraint("parameter_set_id"),
        sa.UniqueConstraint(
            "tax_year",
            "parameter_set_version",
            name="uq_official_parameter_sets_year_version",
        ),
    )
    op.create_index(
        "ix_official_parameter_sets_resolution",
        "official_parameter_sets",
        ["status", "tax_year", "effective_from", "effective_to"],
        unique=False,
    )


def downgrade() -> None:
    connection = op.get_bind()
    parameter_set_count = connection.execute(
        sa.text("SELECT COUNT(*) FROM official_parameter_sets")
    ).scalar_one()
    if parameter_set_count:
        raise RuntimeError(
            "Cannot downgrade while PKG-004A official parameter sets are present"
        )
    op.drop_index(
        "ix_official_parameter_sets_resolution",
        table_name="official_parameter_sets",
    )
    op.drop_table("official_parameter_sets")
