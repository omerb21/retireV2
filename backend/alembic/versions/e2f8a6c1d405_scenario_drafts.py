"""Independent non-authoritative retirement scenario drafts.

Revision ID: e2f8a6c1d405
Revises: c4e8a2f6b731
"""
from alembic import op
import sqlalchemy as sa

revision = "e2f8a6c1d405"
down_revision = "c4e8a2f6b731"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "scenario_drafts",
        sa.Column("scenario_id", sa.String(64), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.client_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.String(128), nullable=False),
        sa.Column("updated_by", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("version > 0", name="ck_scenario_draft_version"),
        sa.CheckConstraint("status IN ('draft','needs_revalidation','archived')", name="ck_scenario_draft_status"),
    )
    op.create_index("ix_scenario_drafts_client_id", "scenario_drafts", ["client_id"])
    op.create_table(
        "scenario_draft_decisions",
        sa.Column("decision_id", sa.String(64), primary_key=True),
        sa.Column("scenario_id", sa.String(64), sa.ForeignKey("scenario_drafts.scenario_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("source_product_id", sa.String(64), nullable=False),
        sa.Column("source_component_id", sa.String(64), nullable=False),
        sa.Column("component_code", sa.String(128), nullable=False),
        sa.Column("amount", sa.Numeric(20, 2), nullable=False),
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("validation_state", sa.String(32), nullable=False),
        sa.Column("product_version_at_review", sa.Integer()),
        sa.Column("source_fingerprint_at_review", sa.String(64)),
        sa.Column("ruleset_digest_at_review", sa.String(64)),
        sa.Column("permission_preview_id_at_review", sa.String(64)),
        sa.CheckConstraint("amount > 0", name="ck_scenario_draft_decision_positive"),
        sa.CheckConstraint("action IN ('pension','capital_asset')", name="ck_scenario_draft_decision_action"),
        sa.CheckConstraint("validation_state IN ('unverified','needs_revalidation')", name="ck_scenario_draft_decision_validation"),
        sa.CheckConstraint("component_code IN (" + ",".join("'" + code + "'" for code in (
            "פיצויים_מעסיק_נוכחי", "פיצויים_לאחר_התחשבנות",
            "פיצויים_שלא_עברו_התחשבנות", "פיצויים_ממעסיקים_קודמים_רצף_זכויות",
            "פיצויים_ממעסיקים_קודמים_רצף_קצבה", "תגמולי_עובד_עד_2000",
            "תגמולי_עובד_אחרי_2000", "תגמולי_עובד_אחרי_2008_לא_משלמת",
            "תגמולי_מעביד_עד_2000", "תגמולי_מעביד_אחרי_2000",
            "תגמולי_מעביד_אחרי_2008_לא_משלמת",
        )) + ")", name="ck_scenario_draft_decision_component"),
    )
    op.create_index("ix_scenario_draft_decisions_scenario_id", "scenario_draft_decisions", ["scenario_id"])
    op.create_table(
        "scenario_draft_revisions",
        sa.Column("revision_id", sa.String(64), primary_key=True),
        sa.Column("scenario_id", sa.String(64), sa.ForeignKey("scenario_drafts.scenario_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("snapshot_json", sa.String(), nullable=False),
        sa.Column("actor", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("scenario_id", "version", name="uq_scenario_draft_revision_version"),
    )
    op.create_index("ix_scenario_draft_revisions_scenario_id", "scenario_draft_revisions", ["scenario_id"])


def downgrade():
    op.drop_index("ix_scenario_draft_revisions_scenario_id", table_name="scenario_draft_revisions")
    op.drop_table("scenario_draft_revisions")
    op.drop_index("ix_scenario_draft_decisions_scenario_id", table_name="scenario_draft_decisions")
    op.drop_table("scenario_draft_decisions")
    op.drop_index("ix_scenario_drafts_client_id", table_name="scenario_drafts")
    op.drop_table("scenario_drafts")
