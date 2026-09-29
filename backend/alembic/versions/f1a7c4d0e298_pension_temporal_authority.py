"""Canonical pension temporal/indexation basis authority."""
from alembic import op
import sqlalchemy as sa

revision = "f1a7c4d0e298"
down_revision = "e0f6b3c9d187"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("canonical_manual_pension_sources", sa.Column(
        "temporal_authority_explicit", sa.Boolean(), nullable=False, server_default=sa.false()))
    with op.batch_alter_table("canonical_manual_pension_sources") as batch:
        batch.alter_column("temporal_authority_explicit", server_default=None)
    op.create_table(
        "canonical_pension_temporal_decisions",
        sa.Column("pension_destination_id", sa.String(64),
            sa.ForeignKey("canonical_pension_destinations.pension_destination_id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.client_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("authority_kind", sa.String(32), nullable=False),
        sa.Column("annual_rate_text", sa.String(128), nullable=True),
        sa.Column("rate_basis", sa.String(32), nullable=True),
        sa.Column("source_version_at_decision", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("actor", sa.String(128), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("authority_kind IN ('none','fixed_manual')", name="ck_pension_temporal_kind"),
        sa.CheckConstraint("source_version_at_decision > 0", name="ck_pension_temporal_source_version"),
        sa.CheckConstraint("version > 0", name="ck_pension_temporal_version"),
        sa.CheckConstraint(
            "(authority_kind = 'none' AND annual_rate_text IS NULL AND rate_basis IS NULL) OR "
            "(authority_kind = 'fixed_manual' AND annual_rate_text IS NOT NULL AND rate_basis = 'ANNUAL_EFFECTIVE')",
            name="ck_pension_temporal_semantics"),
    )


def downgrade():
    bind = op.get_bind()
    if bind.execute(sa.text("SELECT 1 FROM canonical_pension_temporal_decisions LIMIT 1")).first():
        raise RuntimeError("PENSION_TEMPORAL_DOWNGRADE_WOULD_LOSE_DECISIONS")
    if bind.execute(sa.text(
        "SELECT 1 FROM canonical_manual_pension_sources WHERE temporal_authority_explicit IS TRUE LIMIT 1"
    )).first():
        raise RuntimeError("PENSION_TEMPORAL_DOWNGRADE_WOULD_LOSE_EXPLICIT_AUTHORITY")
    op.drop_table("canonical_pension_temporal_decisions")
    with op.batch_alter_table("canonical_manual_pension_sources") as batch:
        batch.drop_column("temporal_authority_explicit")
