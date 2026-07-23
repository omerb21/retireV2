"""add PKG-004B1 M07 evidence foundation

Revision ID: b4e7c1d8f203
Revises: a8e4f2c6d901
Create Date: 2026-07-23 16:00:00.000000

The migration is additive and unseeded. Downgrade refuses to discard any
closed evidence revision that the package contract requires to be retained.
"""

from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "b4e7c1d8f203"
down_revision: Union[str, None] = "a8e4f2c6d901"
branch_labels: Union[str, tuple[str, ...], None] = None
depends_on: Union[str, tuple[str, ...], None] = None


def upgrade() -> None:
    op.create_table(
        "m07_evidence_revisions",
        sa.Column("m07_evidence_revision_id", sa.String(64), nullable=False),
        sa.Column("profile_id", sa.String(64), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("predecessor_revision_id", sa.String(64), nullable=True),
        sa.Column("superseded_by_revision_id", sa.String(64), nullable=True),
        sa.Column("tax_year", sa.Integer(), nullable=False),
        sa.Column("event_year", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=True),
        sa.Column("event_id", sa.String(64), nullable=True),
        sa.Column("schema_version", sa.String(64), nullable=False),
        sa.Column("rule_version", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("authority_classification", sa.String(64), nullable=False),
        sa.Column("technical_outcomes", sa.JSON(), nullable=False),
        sa.Column("assessment_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("canonical_payload", sa.JSON(), nullable=True),
        sa.Column("evidence_fingerprint", sa.String(64), nullable=True),
        sa.Column("fingerprint_algorithm_version", sa.String(64), nullable=False),
        sa.Column("source_snapshot_fingerprint", sa.String(64), nullable=True),
        sa.Column("parameter_set_id", sa.String(64), nullable=True),
        sa.Column("parameter_set_fingerprint", sa.String(64), nullable=True),
        sa.Column("parameter_resolution_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("parameter_requested_tax_year", sa.Integer(), nullable=True),
        sa.Column("parameter_effective_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(128), nullable=False),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finalized_by", sa.String(128), nullable=True),
        sa.Column("abandoned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("abandoned_by", sa.String(128), nullable=True),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("superseded_by", sa.String(128), nullable=True),
        sa.CheckConstraint(
            "status IN ('draft','finalized','superseded','abandoned')",
            name="ck_m07_evidence_revisions_status",
        ),
        sa.CheckConstraint(
            "authority_classification = 'EVIDENCE_ONLY_NOT_PROFESSIONAL_AUTHORITY'",
            name="ck_m07_evidence_revisions_authority",
        ),
        sa.CheckConstraint(
            "revision_number > 0",
            name="ck_m07_evidence_revisions_number_positive",
        ),
        sa.CheckConstraint(
            "status NOT IN ('finalized','superseded') OR "
            "(finalized_at IS NOT NULL AND finalized_by IS NOT NULL "
            "AND canonical_payload IS NOT NULL AND evidence_fingerprint IS NOT NULL "
            "AND source_snapshot_fingerprint IS NOT NULL)",
            name="ck_m07_evidence_revisions_finalization_evidence",
        ),
        sa.CheckConstraint(
            "status != 'abandoned' OR "
            "(abandoned_at IS NOT NULL AND abandoned_by IS NOT NULL)",
            name="ck_m07_evidence_revisions_abandonment_evidence",
        ),
        sa.CheckConstraint(
            "status != 'superseded' OR "
            "(superseded_at IS NOT NULL AND superseded_by IS NOT NULL "
            "AND superseded_by_revision_id IS NOT NULL)",
            name="ck_m07_evidence_revisions_supersession_evidence",
        ),
        sa.ForeignKeyConstraint(["client_id"], ["clients.client_id"]),
        sa.ForeignKeyConstraint(
            ["parameter_set_id"], ["official_parameter_sets.parameter_set_id"]
        ),
        sa.ForeignKeyConstraint(
            ["predecessor_revision_id", "client_id"],
            [
                "m07_evidence_revisions.m07_evidence_revision_id",
                "m07_evidence_revisions.client_id",
            ],
            name="fk_m07_evidence_revisions_predecessor_client",
        ),
        sa.ForeignKeyConstraint(
            ["superseded_by_revision_id", "client_id"],
            [
                "m07_evidence_revisions.m07_evidence_revision_id",
                "m07_evidence_revisions.client_id",
            ],
            name="fk_m07_evidence_revisions_successor_client",
        ),
        sa.PrimaryKeyConstraint("m07_evidence_revision_id"),
        sa.UniqueConstraint(
            "client_id",
            "profile_id",
            "revision_number",
            name="uq_m07_evidence_revisions_client_profile_number",
        ),
        sa.UniqueConstraint(
            "m07_evidence_revision_id",
            "client_id",
            name="uq_m07_evidence_revisions_id_client",
        ),
    )
    op.create_index(
        "ix_m07_evidence_revisions_client_profile",
        "m07_evidence_revisions",
        ["client_id", "profile_id", "revision_number"],
    )
    op.create_table(
        "m07_planner_assertions",
        sa.Column("assertion_id", sa.String(64), nullable=False),
        sa.Column("m07_evidence_revision_id", sa.String(64), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("field_code", sa.String(128), nullable=False),
        sa.Column("asserted_value", sa.JSON(), nullable=False),
        sa.Column("authority_classification", sa.String(64), nullable=False),
        sa.Column("assertion_basis", sa.Text(), nullable=False),
        sa.Column("assertion_reason", sa.Text(), nullable=False),
        sa.Column("source_note", sa.String(2048), nullable=True),
        sa.Column("asserted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("asserted_by", sa.String(128), nullable=False),
        sa.Column("predecessor_assertion_id", sa.String(64), nullable=True),
        sa.Column("content_fingerprint", sa.String(64), nullable=False),
        sa.CheckConstraint(
            "authority_classification = "
            "'ASSERTION_EVIDENCE_ONLY_NOT_PROFESSIONAL_AUTHORITY'",
            name="ck_m07_planner_assertions_authority",
        ),
        sa.ForeignKeyConstraint(["client_id"], ["clients.client_id"]),
        sa.ForeignKeyConstraint(
            ["m07_evidence_revision_id", "client_id"],
            [
                "m07_evidence_revisions.m07_evidence_revision_id",
                "m07_evidence_revisions.client_id",
            ],
            name="fk_m07_planner_assertions_revision_client",
        ),
        sa.ForeignKeyConstraint(
            [
                "predecessor_assertion_id",
                "m07_evidence_revision_id",
                "client_id",
            ],
            [
                "m07_planner_assertions.assertion_id",
                "m07_planner_assertions.m07_evidence_revision_id",
                "m07_planner_assertions.client_id",
            ],
            name="fk_m07_planner_assertions_predecessor_scope",
        ),
        sa.PrimaryKeyConstraint("assertion_id"),
        sa.UniqueConstraint(
            "assertion_id",
            "m07_evidence_revision_id",
            "client_id",
            name="uq_m07_planner_assertions_scope",
        ),
    )
    op.create_index(
        "ix_m07_planner_assertions_revision_field",
        "m07_planner_assertions",
        ["client_id", "m07_evidence_revision_id", "field_code"],
    )
    op.create_table(
        "m07_fact_evidence",
        sa.Column("fact_evidence_id", sa.String(64), nullable=False),
        sa.Column("m07_evidence_revision_id", sa.String(64), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("field_code", sa.String(128), nullable=False),
        sa.Column("structured_value", sa.JSON(), nullable=True),
        sa.Column("collection_state", sa.String(32), nullable=False),
        sa.Column("collection_basis", sa.Text(), nullable=True),
        sa.Column("verification_state", sa.String(32), nullable=False),
        sa.Column("authority_classification", sa.String(64), nullable=False),
        sa.Column("source_type", sa.String(64), nullable=True),
        sa.Column("source_record_type", sa.String(64), nullable=True),
        sa.Column("source_record_id", sa.String(128), nullable=True),
        sa.Column("source_document_reference", sa.String(512), nullable=True),
        sa.Column("source_date", sa.Date(), nullable=True),
        sa.Column("source_excerpt", sa.String(2048), nullable=True),
        sa.Column("source_metadata", sa.JSON(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_by", sa.String(128), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_by", sa.String(128), nullable=True),
        sa.Column("verification_basis", sa.Text(), nullable=True),
        sa.Column("assertion_id", sa.String(64), nullable=True),
        sa.Column("content_fingerprint", sa.String(64), nullable=False),
        sa.CheckConstraint(
            "collection_state IN "
            "('recorded','confirmed_none','unknown','not_collected','unresolved','not_applicable')",
            name="ck_m07_fact_evidence_collection_state",
        ),
        sa.CheckConstraint(
            "verification_state IN "
            "('unverified','partly_verified','verified','planner_asserted',"
            "'source_conflict','rejected','superseded')",
            name="ck_m07_fact_evidence_verification_state",
        ),
        sa.CheckConstraint(
            "authority_classification = 'EVIDENCE_ONLY_NOT_PROFESSIONAL_AUTHORITY'",
            name="ck_m07_fact_evidence_authority",
        ),
        sa.CheckConstraint(
            "collection_state != 'recorded' OR structured_value IS NOT NULL",
            name="ck_m07_fact_evidence_recorded_value",
        ),
        sa.CheckConstraint(
            "collection_state NOT IN ('confirmed_none','not_applicable') OR "
            "collection_basis IS NOT NULL",
            name="ck_m07_fact_evidence_collection_basis",
        ),
        sa.CheckConstraint(
            "verification_state NOT IN ('verified','partly_verified') OR "
            "(verified_at IS NOT NULL AND verified_by IS NOT NULL "
            "AND verification_basis IS NOT NULL)",
            name="ck_m07_fact_evidence_verification_evidence",
        ),
        sa.CheckConstraint(
            "verification_state != 'planner_asserted' OR assertion_id IS NOT NULL",
            name="ck_m07_fact_evidence_assertion_link",
        ),
        sa.ForeignKeyConstraint(["client_id"], ["clients.client_id"]),
        sa.ForeignKeyConstraint(
            ["m07_evidence_revision_id", "client_id"],
            [
                "m07_evidence_revisions.m07_evidence_revision_id",
                "m07_evidence_revisions.client_id",
            ],
            name="fk_m07_fact_evidence_revision_client",
        ),
        sa.ForeignKeyConstraint(
            ["assertion_id", "m07_evidence_revision_id", "client_id"],
            [
                "m07_planner_assertions.assertion_id",
                "m07_planner_assertions.m07_evidence_revision_id",
                "m07_planner_assertions.client_id",
            ],
            name="fk_m07_fact_evidence_assertion_scope",
        ),
        sa.PrimaryKeyConstraint("fact_evidence_id"),
    )
    op.create_index(
        "ix_m07_fact_evidence_revision_field",
        "m07_fact_evidence",
        ["client_id", "m07_evidence_revision_id", "field_code"],
    )
    op.create_table(
        "m07_assessment_findings",
        sa.Column("finding_id", sa.String(64), nullable=False),
        sa.Column("m07_evidence_revision_id", sa.String(64), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("finding_kind", sa.String(64), nullable=False),
        sa.Column("finding_code", sa.String(128), nullable=False),
        sa.Column("authority_classification", sa.String(64), nullable=False),
        sa.Column("category", sa.String(128), nullable=False),
        sa.Column("field_references", sa.JSON(), nullable=False),
        sa.Column("fact_references", sa.JSON(), nullable=False),
        sa.Column("assertion_references", sa.JSON(), nullable=False),
        sa.Column("source_references", sa.JSON(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("rule_version", sa.String(64), nullable=False),
        sa.Column("assessment_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("technical_blocking_effect", sa.Boolean(), nullable=False),
        sa.Column("content_fingerprint", sa.String(64), nullable=False),
        sa.CheckConstraint(
            "finding_kind IN "
            "('missing_required_field','not_collected','unknown','unresolved',"
            "'source_conflict','rejected_evidence','confirmed_none','not_applicable',"
            "'incompatible_evidence','technical_warning','technical_rule_outcome')",
            name="ck_m07_assessment_findings_kind",
        ),
        sa.CheckConstraint(
            "authority_classification = "
            "'TECHNICAL_ASSESSMENT_ONLY_NOT_PROFESSIONAL_AUTHORITY'",
            name="ck_m07_assessment_findings_authority",
        ),
        sa.ForeignKeyConstraint(["client_id"], ["clients.client_id"]),
        sa.ForeignKeyConstraint(
            ["m07_evidence_revision_id", "client_id"],
            [
                "m07_evidence_revisions.m07_evidence_revision_id",
                "m07_evidence_revisions.client_id",
            ],
            name="fk_m07_assessment_findings_revision_client",
        ),
        sa.PrimaryKeyConstraint("finding_id"),
    )
    op.create_index(
        "ix_m07_assessment_findings_revision_code",
        "m07_assessment_findings",
        ["client_id", "m07_evidence_revision_id", "finding_code"],
    )


def downgrade() -> None:
    connection = op.get_bind()
    retained_count = connection.execute(
        sa.text(
            "SELECT COUNT(*) FROM m07_evidence_revisions "
            "WHERE status IN ('finalized','superseded','abandoned')"
        )
    ).scalar_one()
    if retained_count:
        raise RuntimeError(
            "Cannot downgrade while retained PKG-004B1 M07 evidence exists"
        )
    op.drop_index(
        "ix_m07_assessment_findings_revision_code",
        table_name="m07_assessment_findings",
    )
    op.drop_table("m07_assessment_findings")
    op.drop_index(
        "ix_m07_fact_evidence_revision_field", table_name="m07_fact_evidence"
    )
    op.drop_table("m07_fact_evidence")
    op.drop_index(
        "ix_m07_planner_assertions_revision_field",
        table_name="m07_planner_assertions",
    )
    op.drop_table("m07_planner_assertions")
    op.drop_index(
        "ix_m07_evidence_revisions_client_profile",
        table_name="m07_evidence_revisions",
    )
    op.drop_table("m07_evidence_revisions")
