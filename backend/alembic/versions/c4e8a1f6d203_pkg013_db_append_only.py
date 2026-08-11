"""enforce PKG-013 append-only evidence in the database

Revision ID: c4e8a1f6d203
Revises: a7c9e1f3b805
Create Date: 2026-08-12
"""

from collections.abc import Sequence

from alembic import op


revision: str = "c4e8a1f6d203"
down_revision: str | None = "a7c9e1f3b805"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = (
    "m09_resolved_component_inventories",
    "m09_scenario_runs",
    "m09_monthly_results",
)


def _dialect() -> str:
    return op.get_context().dialect.name


def upgrade() -> None:
    if _dialect() == "postgresql":
        op.execute(
            """
            CREATE FUNCTION m09_reject_immutable_mutation()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $$
            BEGIN
                RAISE EXCEPTION 'm09_append_only_violation' USING ERRCODE = '55000';
            END;
            $$
            """
        )
        for table in TABLES:
            op.execute(
                f"""
                CREATE TRIGGER trg_{table}_append_only
                BEFORE UPDATE OR DELETE ON {table}
                FOR EACH ROW EXECUTE FUNCTION m09_reject_immutable_mutation()
                """
            )
        return

    for table in TABLES:
        op.execute(
            f"""
            CREATE TRIGGER trg_{table}_no_update
            BEFORE UPDATE ON {table}
            BEGIN
                SELECT RAISE(ABORT, 'm09_append_only_violation');
            END
            """
        )
        op.execute(
            f"""
            CREATE TRIGGER trg_{table}_no_delete
            BEFORE DELETE ON {table}
            BEGIN
                SELECT RAISE(ABORT, 'm09_append_only_violation');
            END
            """
        )


def downgrade() -> None:
    if _dialect() == "postgresql":
        for table in reversed(TABLES):
            op.execute(f"DROP TRIGGER trg_{table}_append_only ON {table}")
        op.execute("DROP FUNCTION m09_reject_immutable_mutation()")
        return

    for table in reversed(TABLES):
        op.execute(f"DROP TRIGGER trg_{table}_no_delete")
        op.execute(f"DROP TRIGGER trg_{table}_no_update")
