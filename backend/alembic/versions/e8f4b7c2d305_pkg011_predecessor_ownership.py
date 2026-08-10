"""enforce PKG-011 predecessor client ownership

Revision ID: e8f4b7c2d305
Revises: d7e3a6b9c204
Create Date: 2026-08-10
"""

from collections.abc import Sequence

from alembic import op


revision: str = "e8f4b7c2d305"
down_revision: str | None = "d7e3a6b9c204"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _sqlite() -> bool:
    return op.get_context().dialect.name == "sqlite"


def upgrade() -> None:
    if _sqlite():
        with op.batch_alter_table(
            "m04_classification_revisions", recreate="always"
        ) as batch_op:
            batch_op.create_unique_constraint(
                "uq_m04_revision_identity_client", ["revision_id", "client_id"]
            )
        with op.batch_alter_table(
            "m05_ledger_revisions", recreate="always"
        ) as batch_op:
            batch_op.create_unique_constraint(
                "uq_m05_revision_identity_client", ["revision_id", "client_id"]
            )
        with op.batch_alter_table(
            "m06_conversion_revisions", recreate="always"
        ) as batch_op:
            batch_op.create_foreign_key(
                "fk_m06_revision_m04_client",
                "m04_classification_revisions",
                ["m04_revision_id", "client_id"],
                ["revision_id", "client_id"],
                ondelete="RESTRICT",
            )
            batch_op.create_foreign_key(
                "fk_m06_revision_m05_client",
                "m05_ledger_revisions",
                ["m05_revision_id", "client_id"],
                ["revision_id", "client_id"],
                ondelete="RESTRICT",
            )
        return

    op.create_unique_constraint(
        "uq_m04_revision_identity_client",
        "m04_classification_revisions",
        ["revision_id", "client_id"],
    )
    op.create_unique_constraint(
        "uq_m05_revision_identity_client",
        "m05_ledger_revisions",
        ["revision_id", "client_id"],
    )
    op.create_foreign_key(
        "fk_m06_revision_m04_client",
        "m06_conversion_revisions",
        "m04_classification_revisions",
        ["m04_revision_id", "client_id"],
        ["revision_id", "client_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_m06_revision_m05_client",
        "m06_conversion_revisions",
        "m05_ledger_revisions",
        ["m05_revision_id", "client_id"],
        ["revision_id", "client_id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    if _sqlite():
        with op.batch_alter_table(
            "m06_conversion_revisions", recreate="always"
        ) as batch_op:
            batch_op.drop_constraint("fk_m06_revision_m05_client", type_="foreignkey")
            batch_op.drop_constraint("fk_m06_revision_m04_client", type_="foreignkey")
        with op.batch_alter_table(
            "m05_ledger_revisions", recreate="always"
        ) as batch_op:
            batch_op.drop_constraint("uq_m05_revision_identity_client", type_="unique")
        with op.batch_alter_table(
            "m04_classification_revisions", recreate="always"
        ) as batch_op:
            batch_op.drop_constraint("uq_m04_revision_identity_client", type_="unique")
        return

    op.drop_constraint(
        "fk_m06_revision_m05_client",
        "m06_conversion_revisions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_m06_revision_m04_client",
        "m06_conversion_revisions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "uq_m05_revision_identity_client",
        "m05_ledger_revisions",
        type_="unique",
    )
    op.drop_constraint(
        "uq_m04_revision_identity_client",
        "m04_classification_revisions",
        type_="unique",
    )
