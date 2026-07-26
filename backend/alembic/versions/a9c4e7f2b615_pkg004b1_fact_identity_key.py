"""add preflight-safe PKG-004B1 fact identity key

Revision ID: a9c4e7f2b615
Revises: e6f1a9c3b702
Create Date: 2026-07-26 12:00:00.000000

This replaces the unaccepted review-branch revision f7b2d4e6a913. No
accepted/master migration is rewritten. Existing PKG-004B1 rows receive the
same canonical SHA-256 identity used by the application service, but all
legacy basis and duplicate validation completes before any schema mutation.
"""

import hashlib
import json
from typing import Any, Mapping, Union

from alembic import context, op
import sqlalchemy as sa


revision: str = "a9c4e7f2b615"
down_revision: Union[str, None] = "e6f1a9c3b702"
branch_labels: Union[str, tuple[str, ...], None] = None
depends_on: Union[str, tuple[str, ...], None] = None


_DOCUMENT_SOURCE_TYPES = {
    "external_document",
    "official_document",
    "client_document",
    "clearinghouse",
}
_SELECT_EXISTING_FACTS = sa.text(
    """
    SELECT fact_evidence_id, client_id, m07_evidence_revision_id,
           field_code, collection_state, collection_basis,
           verification_state, source_type, source_record_type,
           source_record_id, source_document_reference, assertion_id
    FROM m07_fact_evidence
    ORDER BY client_id, m07_evidence_revision_id, fact_evidence_id
    """
)

# PostgreSQL's to_json(text)::text produces the same JSON string escaping used
# by canonical_m07_json for these string-only identity inputs. The object keys
# and separators below are already in the service's sorted canonical order.
_POSTGRES_BASIS_SQL = """
CASE
    WHEN assertion_id IS NOT NULL
        THEN 'assertion:' || assertion_id
    WHEN source_record_id IS NOT NULL
        THEN 'record:' || source_record_type || ':' || source_record_id
    WHEN source_document_reference IS NOT NULL
        THEN 'document:' || source_type || ':' || source_document_reference
    ELSE 'state:' || collection_state
END
"""
_POSTGRES_IDENTITY_SQL = f"""
encode(
    sha256(
        convert_to(
            '{{"basis_identity":' || to_json(({_POSTGRES_BASIS_SQL})::text)::text ||
            ',"field_code":' || to_json(field_code::text)::text ||
            ',"revision_id":' ||
                to_json(m07_evidence_revision_id::text)::text || '}}',
            'UTF8'
        )
    ),
    'hex'
)
"""
_POSTGRES_MALFORMED_PREDICATE = """
    ((source_record_type IS NULL) <> (source_record_id IS NULL))
 OR ((source_record_type IS NOT NULL OR source_record_id IS NOT NULL)
     AND source_document_reference IS NOT NULL)
 OR (assertion_id IS NOT NULL
     AND (source_record_type IS NOT NULL OR source_record_id IS NOT NULL
          OR source_document_reference IS NOT NULL OR source_type IS NOT NULL))
 OR (assertion_id IS NOT NULL
     AND verification_state <> 'planner_asserted')
 OR (verification_state = 'planner_asserted' AND assertion_id IS NULL)
 OR (source_record_type IS NOT NULL AND source_record_id IS NOT NULL
     AND source_type <> 'persisted_record')
 OR (source_document_reference IS NOT NULL
     AND (source_type IS NULL OR source_type NOT IN
          ('external_document', 'official_document',
           'client_document', 'clearinghouse')))
 OR (source_record_type IS NULL AND source_record_id IS NULL
     AND source_document_reference IS NULL AND assertion_id IS NULL
     AND source_type IS NOT NULL)
 OR (source_record_type IS NULL AND source_record_id IS NULL
     AND source_document_reference IS NULL AND assertion_id IS NULL
     AND collection_state = 'recorded')
 OR (source_record_type IS NULL AND source_record_id IS NULL
     AND source_document_reference IS NULL AND assertion_id IS NULL
     AND collection_state <> 'recorded'
     AND (collection_basis IS NULL OR btrim(collection_basis) = ''))
"""
_POSTGRES_PREFLIGHT_SQL = f"""
DO $pkg004b1$
DECLARE
    malformed_fact_id text;
    duplicate_fact_id text;
BEGIN
    SELECT fact_evidence_id
      INTO malformed_fact_id
      FROM m07_fact_evidence
     WHERE {_POSTGRES_MALFORMED_PREDICATE}
     ORDER BY fact_evidence_id
     LIMIT 1;

    IF malformed_fact_id IS NOT NULL THEN
        RAISE EXCEPTION
            'Malformed PKG-004B1 evidence must be corrected before upgrade'
            USING DETAIL = 'B1 fact id: ' || malformed_fact_id;
    END IF;

    WITH identities AS (
        SELECT fact_evidence_id, client_id, m07_evidence_revision_id,
               {_POSTGRES_IDENTITY_SQL} AS identity_key
          FROM m07_fact_evidence
    ),
    duplicates AS (
        SELECT min(fact_evidence_id) AS fact_evidence_id
          FROM identities
         GROUP BY client_id, m07_evidence_revision_id, identity_key
        HAVING count(*) > 1
    )
    SELECT fact_evidence_id
      INTO duplicate_fact_id
      FROM duplicates
     ORDER BY fact_evidence_id
     LIMIT 1;

    IF duplicate_fact_id IS NOT NULL THEN
        RAISE EXCEPTION
            'Duplicate PKG-004B1 fact identity must be corrected before upgrade'
            USING DETAIL = 'B1 fact id: ' || duplicate_fact_id;
    END IF;
END
$pkg004b1$;
"""


def _fingerprint(value: dict[str, Any]) -> str:
    rendered = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def _malformed_fact(row: Mapping[str, Any]) -> RuntimeError:
    return RuntimeError(
        "Malformed PKG-004B1 evidence must be corrected before upgrade "
        f"(B1 fact id: {row['fact_evidence_id']})"
    )


def _basis_identity(row: Mapping[str, Any]) -> str:
    has_record_type = row["source_record_type"] is not None
    has_record_id = row["source_record_id"] is not None
    has_record = has_record_type or has_record_id
    has_document = row["source_document_reference"] is not None
    has_assertion = row["assertion_id"] is not None

    if has_record_type != has_record_id:
        raise _malformed_fact(row)
    if has_record and has_document:
        raise _malformed_fact(row)
    if has_assertion and (
        has_record or has_document or row["source_type"] is not None
    ):
        raise _malformed_fact(row)
    if has_assertion:
        if row["verification_state"] != "planner_asserted":
            raise _malformed_fact(row)
        return f"assertion:{row['assertion_id']}"
    if row["verification_state"] == "planner_asserted":
        raise _malformed_fact(row)
    if has_record:
        if row["source_type"] != "persisted_record":
            raise _malformed_fact(row)
        return f"record:{row['source_record_type']}:{row['source_record_id']}"
    if has_document:
        if row["source_type"] not in _DOCUMENT_SOURCE_TYPES:
            raise _malformed_fact(row)
        return (
            f"document:{row['source_type']}:"
            f"{row['source_document_reference']}"
        )
    if row["source_type"] is not None:
        raise _malformed_fact(row)
    if row["collection_state"] == "recorded":
        raise _malformed_fact(row)
    collection_basis = row["collection_basis"]
    if collection_basis is None or not collection_basis.strip():
        raise _malformed_fact(row)
    return f"state:{row['collection_state']}"


def _identity_key(row: Mapping[str, Any]) -> str:
    return _fingerprint(
        {
            "revision_id": row["m07_evidence_revision_id"],
            "field_code": row["field_code"],
            "basis_identity": _basis_identity(row),
        }
    )


def _online_preflight(connection) -> list[tuple[str, str]]:
    derived: list[tuple[str, str]] = []
    seen: set[tuple[int, str, str]] = set()
    for row in connection.execute(_SELECT_EXISTING_FACTS).mappings():
        identity_key = _identity_key(row)
        scoped_key = (
            row["client_id"],
            row["m07_evidence_revision_id"],
            identity_key,
        )
        if scoped_key in seen:
            raise RuntimeError(
                "Duplicate PKG-004B1 fact identity must be corrected before "
                f"upgrade (B1 fact id: {row['fact_evidence_id']})"
            )
        seen.add(scoped_key)
        derived.append((row["fact_evidence_id"], identity_key))
    return derived


def _offline_postgresql_upgrade() -> None:
    op.execute(sa.text(_POSTGRES_PREFLIGHT_SQL))
    op.add_column(
        "m07_fact_evidence",
        sa.Column("fact_identity_key", sa.String(length=64), nullable=True),
    )
    op.execute(
        sa.text(
            f"""
            UPDATE m07_fact_evidence
               SET fact_identity_key = {_POSTGRES_IDENTITY_SQL}
            """
        )
    )
    op.alter_column(
        "m07_fact_evidence",
        "fact_identity_key",
        existing_type=sa.String(length=64),
        nullable=False,
    )
    op.create_unique_constraint(
        "uq_m07_fact_evidence_identity_key",
        "m07_fact_evidence",
        ["client_id", "m07_evidence_revision_id", "fact_identity_key"],
    )


def upgrade() -> None:
    if context.is_offline_mode():
        if context.get_context().dialect.name != "postgresql":
            raise RuntimeError(
                "PKG-004B1 offline migration SQL is supported for PostgreSQL"
            )
        _offline_postgresql_upgrade()
        return

    connection = op.get_bind()
    derived = _online_preflight(connection)
    op.add_column(
        "m07_fact_evidence",
        sa.Column("fact_identity_key", sa.String(length=64), nullable=True),
    )
    for fact_evidence_id, identity_key in derived:
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
                "fact_evidence_id": fact_evidence_id,
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
    if context.is_offline_mode():
        op.drop_constraint(
            "uq_m07_fact_evidence_identity_key",
            "m07_fact_evidence",
            type_="unique",
        )
        op.drop_column("m07_fact_evidence", "fact_identity_key")
        return
    with op.batch_alter_table("m07_fact_evidence") as batch_op:
        batch_op.drop_constraint(
            "uq_m07_fact_evidence_identity_key",
            type_="unique",
        )
        batch_op.drop_column("fact_identity_key")
