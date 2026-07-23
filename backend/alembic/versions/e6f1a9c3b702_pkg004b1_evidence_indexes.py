"""add PKG-004B1 evidence query and identity indexes

Revision ID: e6f1a9c3b702
Revises: b4e7c1d8f203
Create Date: 2026-07-23 20:00:00.000000

This migration adds indexes only. It performs no seed, backfill, or data
rewrite and its downgrade removes only these indexes.
"""

from typing import Union

from alembic import op


revision: str = "e6f1a9c3b702"
down_revision: Union[str, None] = "b4e7c1d8f203"
branch_labels: Union[str, tuple[str, ...], None] = None
depends_on: Union[str, tuple[str, ...], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_m07_evidence_revisions_client_tax_event_year",
        "m07_evidence_revisions",
        ["client_id", "tax_year", "event_year"],
        unique=False,
    )
    op.create_index(
        "ix_m07_evidence_revisions_client_status",
        "m07_evidence_revisions",
        ["client_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_m07_evidence_revisions_client_event_reference",
        "m07_evidence_revisions",
        ["client_id", "event_type", "event_id"],
        unique=False,
    )
    op.create_index(
        "uq_m07_fact_evidence_persisted_source_identity",
        "m07_fact_evidence",
        [
            "client_id",
            "m07_evidence_revision_id",
            "field_code",
            "source_record_type",
            "source_record_id",
        ],
        unique=True,
    )
    op.create_index(
        "uq_m07_fact_evidence_document_identity",
        "m07_fact_evidence",
        [
            "client_id",
            "m07_evidence_revision_id",
            "field_code",
            "source_document_reference",
        ],
        unique=True,
    )
    op.create_index(
        "uq_m07_fact_evidence_assertion_identity",
        "m07_fact_evidence",
        [
            "client_id",
            "m07_evidence_revision_id",
            "field_code",
            "assertion_id",
        ],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_m07_fact_evidence_assertion_identity",
        table_name="m07_fact_evidence",
    )
    op.drop_index(
        "uq_m07_fact_evidence_document_identity",
        table_name="m07_fact_evidence",
    )
    op.drop_index(
        "uq_m07_fact_evidence_persisted_source_identity",
        table_name="m07_fact_evidence",
    )
    op.drop_index(
        "ix_m07_evidence_revisions_client_event_reference",
        table_name="m07_evidence_revisions",
    )
    op.drop_index(
        "ix_m07_evidence_revisions_client_status",
        table_name="m07_evidence_revisions",
    )
    op.drop_index(
        "ix_m07_evidence_revisions_client_tax_event_year",
        table_name="m07_evidence_revisions",
    )
