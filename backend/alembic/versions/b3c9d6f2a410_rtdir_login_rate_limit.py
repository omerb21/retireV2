"""RTDIR durable login rate-limit buckets."""
from alembic import op
import sqlalchemy as sa

revision = "b3c9d6f2a410"
down_revision = "a2b8c5e1f309"
branch_labels = None
depends_on = None


def upgrade() -> None:
    postgres = op.get_bind().dialect.name == "postgresql"
    key_check = "bucket_key ~ '^[0-9a-f]{64}$'" if postgres else "length(bucket_key) = 64 AND bucket_key NOT GLOB '*[^0-9a-f]*'"
    lock_check = (
        "locked_until IS NULL OR locked_until = window_started_at + INTERVAL '900 seconds'"
        if postgres else
        "locked_until IS NULL OR locked_until = datetime(window_started_at, '+900 seconds')"
    )
    op.create_table(
        "rtdir_login_rate_limit_buckets",
        sa.Column("bucket_key", sa.CHAR(64), primary_key=True, nullable=False),
        sa.Column("bucket_kind", sa.String(8), nullable=False),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("failure_count", sa.Integer(), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            key_check,
            name="ck_rtdir_login_bucket_key_hex",
        ),
        sa.CheckConstraint(
            "bucket_kind IN ('GLOBAL','USER','IP')",
            name="ck_rtdir_login_bucket_kind",
        ),
        sa.CheckConstraint(
            "failure_count >= 0 AND failure_count <= 2147483647",
            name="ck_rtdir_login_failure_count",
        ),
        sa.CheckConstraint(
            lock_check,
            name="ck_rtdir_login_lock_window",
        ),
    )
    op.create_index(
        "ix_rtdir_login_rate_limit_buckets_updated_at",
        "rtdir_login_rate_limit_buckets",
        ["updated_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_rtdir_login_rate_limit_buckets_updated_at",
        table_name="rtdir_login_rate_limit_buckets",
    )
    op.drop_table("rtdir_login_rate_limit_buckets")
