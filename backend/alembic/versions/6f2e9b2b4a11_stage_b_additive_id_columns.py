"""stage b additive id columns and backfill

Revision ID: 6f2e9b2b4a11
Revises: eb25e18b9fcd
Create Date: 2026-04-30 20:48:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6f2e9b2b4a11"
down_revision: Union[str, None] = "eb25e18b9fcd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("clients") as batch_op:
        batch_op.add_column(sa.Column("id_number", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("birth_date", sa.Date(), nullable=True))

    with op.batch_alter_table("fixation_runs") as batch_op:
        batch_op.add_column(sa.Column("id", sa.Integer(), nullable=True))

    with op.batch_alter_table("fixation_input_snapshots") as batch_op:
        batch_op.add_column(sa.Column("fixation_run_id_int", sa.Integer(), nullable=True))

    with op.batch_alter_table("fixation_results") as batch_op:
        batch_op.add_column(sa.Column("fixation_run_id_int", sa.Integer(), nullable=True))

    with op.batch_alter_table("fixation_audit_rows") as batch_op:
        batch_op.add_column(sa.Column("fixation_run_id_int", sa.Integer(), nullable=True))

    with op.batch_alter_table("fixation_validation_errors") as batch_op:
        batch_op.add_column(sa.Column("fixation_run_id_int", sa.Integer(), nullable=True))

    op.execute(
        """
        UPDATE clients
        SET id_number = client_id
        WHERE id_number IS NULL
        """
    )

    op.execute(
        """
        UPDATE clients
        SET birth_date = (
            SELECT cp.birth_date
            FROM client_profiles cp
            WHERE cp.client_id = clients.client_id
            LIMIT 1
        )
        WHERE birth_date IS NULL
        """
    )

    op.execute(
        """
        WITH ordered_runs AS (
            SELECT fixation_run_id, ROW_NUMBER() OVER (ORDER BY created_at, fixation_run_id) AS rn
            FROM fixation_runs
        )
        UPDATE fixation_runs
        SET id = (
            SELECT ordered_runs.rn
            FROM ordered_runs
            WHERE ordered_runs.fixation_run_id = fixation_runs.fixation_run_id
        )
        """
    )

    op.execute(
        """
        UPDATE fixation_input_snapshots
        SET fixation_run_id_int = (
            SELECT fr.id
            FROM fixation_runs fr
            WHERE fr.fixation_run_id = fixation_input_snapshots.fixation_run_id
        )
        """
    )
    op.execute(
        """
        UPDATE fixation_results
        SET fixation_run_id_int = (
            SELECT fr.id
            FROM fixation_runs fr
            WHERE fr.fixation_run_id = fixation_results.fixation_run_id
        )
        """
    )
    op.execute(
        """
        UPDATE fixation_audit_rows
        SET fixation_run_id_int = (
            SELECT fr.id
            FROM fixation_runs fr
            WHERE fr.fixation_run_id = fixation_audit_rows.fixation_run_id
        )
        """
    )
    op.execute(
        """
        UPDATE fixation_validation_errors
        SET fixation_run_id_int = (
            SELECT fr.id
            FROM fixation_runs fr
            WHERE fr.fixation_run_id = fixation_validation_errors.fixation_run_id
        )
        """
    )

    op.create_index("ix_clients_id_number", "clients", ["id_number"], unique=False)
    op.create_index("ix_fixation_runs_id", "fixation_runs", ["id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_fixation_runs_id", table_name="fixation_runs")
    op.drop_index("ix_clients_id_number", table_name="clients")

    with op.batch_alter_table("fixation_validation_errors") as batch_op:
        batch_op.drop_column("fixation_run_id_int")

    with op.batch_alter_table("fixation_audit_rows") as batch_op:
        batch_op.drop_column("fixation_run_id_int")

    with op.batch_alter_table("fixation_results") as batch_op:
        batch_op.drop_column("fixation_run_id_int")

    with op.batch_alter_table("fixation_input_snapshots") as batch_op:
        batch_op.drop_column("fixation_run_id_int")

    with op.batch_alter_table("fixation_runs") as batch_op:
        batch_op.drop_column("id")

    with op.batch_alter_table("clients") as batch_op:
        batch_op.drop_column("birth_date")
        batch_op.drop_column("id_number")
