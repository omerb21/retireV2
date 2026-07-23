"""add non-null PKG-004B1 fact identity key

Revision ID: f7b2d4e6a913
Revises: e6f1a9c3b702
Create Date: 2026-07-23 22:00:00.000000

Existing PKG-004B1 rows, if any, receive the same deterministic identity key
used by the service. This is an evidence-preserving technical derivation from
their existing revision, field, and basis identity; no product data is seeded
or inferred. A pre-existing duplicate identity aborts the migration rather
than selecting or deleting evidence.
"""

import hashlib
import json
from typing import Any, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f7b2d4e6a913"
down_revision: Union[str, None] = "e6f1a9c3b702"
branch_labels: Union[str, tuple[str, ...], None] = None
depends_on: Union[str, tuple[str, ...], None] = None


def _fingerprint(value: dict[str, Any]) -> str:
    rendered = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def _basis_identity(row) -> str:
    if row.verification_state == "planner_asserted":
        return f"assertion:{row.assertion_id}"
    if row.source_record_id is not None:
        return f"record:{row.source_record_type}:{row.source_record_id}"
    if row.source_document_reference is not None:
        return f"document:{row.source_type}:{row.source_document_reference}"
    return f"state:{row.collection_state}"


def upgrade() -> None:
    op.add_column(
        "m07_fact_evidence",
        sa.Column("fact_identity_key", sa.String(length=64), nullable=True),
    )
    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            """
            SELECT fact_evidence_id, client_id, m07_evidence_revision_id,
                   field_code, collection_state, verification_state,
                   source_type, source_record_type, source_record_id,
                   source_document_reference, assertion_id
            FROM m07_fact_evidence
            ORDER BY client_id, m07_evidence_revision_id, fact_evidence_id
            """
        )
    ).mappings()
    seen: set[tuple[int, str, str]] = set()
    for row in rows:
        identity_key = _fingerprint(
            {
                "revision_id": row.m07_evidence_revision_id,
                "field_code": row.field_code,
                "basis_identity": _basis_identity(row),
            }
        )
        scoped_key = (
            row.client_id,
            row.m07_evidence_revision_id,
            identity_key,
        )
        if scoped_key in seen:
            raise RuntimeError(
                "Cannot add PKG-004B1 fact identity key while duplicate "
                "logical fact evidence exists"
            )
        seen.add(scoped_key)
        connection.execute(
            sa.text(
                """
                UPDATE m07_fact_evidence
                SET fact_identity_key = :identity_key
                WHERE fact_evidence_id = :fact_evidence_id
                """
            ),
            {
                "identity_key": identity_key,
                "fact_evidence_id": row.fact_evidence_id,
            },
        )

    with op.batch_alter_table("m07_fact_evidence") as batch_op:
        batch_op.alter_column(
            "fact_identity_key",
            existing_type=sa.String(length=64),
            nullable=False,
        )
        batch_op.create_unique_constraint(
            "uq_m07_fact_evidence_identity_key",
            ["client_id", "m07_evidence_revision_id", "fact_identity_key"],
        )


def downgrade() -> None:
    with op.batch_alter_table("m07_fact_evidence") as batch_op:
        batch_op.drop_constraint(
            "uq_m07_fact_evidence_identity_key",
            type_="unique",
        )
        batch_op.drop_column("fact_identity_key")
