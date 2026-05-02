"""stage a preflight audit for id alignment

Revision ID: eb25e18b9fcd
Revises: a2f36c3147d2
Create Date: 2026-04-30 19:24:02.070877

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'eb25e18b9fcd'
down_revision: Union[str, None] = 'a2f36c3147d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    def _count(sql: str) -> int:
        return int(bind.exec_driver_sql(sql).scalar_one())

    client_count = _count("SELECT COUNT(*) FROM clients")
    run_count = _count("SELECT COUNT(*) FROM fixation_runs")

    risks: list[str] = []

    empty_client_ids = _count(
        "SELECT COUNT(*) FROM clients WHERE client_id IS NULL OR client_id = '' OR TRIM(client_id) = ''"
    )
    if empty_client_ids > 0:
        risks.append(f"clients.client_id has {empty_client_ids} empty/null values")

    non_numeric_client_ids = _count(
        """
        SELECT COUNT(*)
        FROM clients
        WHERE client_id IS NOT NULL
          AND client_id <> ''
          AND TRIM(client_id) <> ''
          AND client_id GLOB '*[^0-9]*'
        """
    )
    if non_numeric_client_ids > 0:
        risks.append(
            f"clients.client_id has {non_numeric_client_ids} values containing non-digit characters"
        )

    cast_changed_client_ids = _count(
        """
        SELECT COUNT(*)
        FROM clients
        WHERE client_id IS NOT NULL
          AND client_id <> ''
          AND TRIM(client_id) <> ''
          AND client_id NOT GLOB '*[^0-9]*'
          AND client_id != CAST(CAST(client_id AS INTEGER) AS TEXT)
        """
    )
    if cast_changed_client_ids > 0:
        risks.append(
            f"clients.client_id has {cast_changed_client_ids} values that would change under CAST(... AS INTEGER)"
        )

    normalized_client_collisions = _count(
        """
        SELECT COUNT(*)
        FROM (
            SELECT CAST(client_id AS INTEGER) AS normalized_client_id, COUNT(*) AS row_count
            FROM clients
            WHERE client_id IS NOT NULL
              AND client_id <> ''
              AND TRIM(client_id) <> ''
              AND client_id NOT GLOB '*[^0-9]*'
            GROUP BY CAST(client_id AS INTEGER)
            HAVING COUNT(*) > 1
        ) collision_groups
        """
    )
    if normalized_client_collisions > 0:
        risks.append(
            f"clients.client_id has {normalized_client_collisions} colliding normalized integer values"
        )

    planned_id_number_empty = _count(
        "SELECT COUNT(*) FROM clients WHERE client_id IS NULL OR client_id = '' OR TRIM(client_id) = ''"
    )
    if planned_id_number_empty > 0:
        risks.append(
            f"planned clients.id_number backfill from clients.client_id has {planned_id_number_empty} null/empty values"
        )

    planned_id_number_duplicates = _count(
        """
        SELECT COUNT(*)
        FROM (
            SELECT client_id AS planned_id_number, COUNT(*) AS row_count
            FROM clients
            GROUP BY client_id
            HAVING COUNT(*) > 1
        ) duplicate_groups
        """
    )
    if planned_id_number_duplicates > 0:
        risks.append(
            f"planned clients.id_number backfill from clients.client_id has {planned_id_number_duplicates} duplicate values"
        )

    empty_run_ids = _count(
        "SELECT COUNT(*) FROM fixation_runs WHERE fixation_run_id IS NULL OR TRIM(fixation_run_id) = ''"
    )
    if empty_run_ids > 0:
        risks.append(f"fixation_runs.fixation_run_id has {empty_run_ids} empty/null values")

    orphan_checks = {
        "client_profiles->clients": """
            SELECT COUNT(*)
            FROM client_profiles cp
            LEFT JOIN clients c ON c.client_id = cp.client_id
            WHERE c.client_id IS NULL
        """,
        "employment_records->clients": """
            SELECT COUNT(*)
            FROM employment_records er
            LEFT JOIN clients c ON c.client_id = er.client_id
            WHERE c.client_id IS NULL
        """,
        "grants->clients": """
            SELECT COUNT(*)
            FROM grants g
            LEFT JOIN clients c ON c.client_id = g.client_id
            WHERE c.client_id IS NULL
        """,
        "actual_capitalizations->clients": """
            SELECT COUNT(*)
            FROM actual_capitalizations ac
            LEFT JOIN clients c ON c.client_id = ac.client_id
            WHERE c.client_id IS NULL
        """,
        "fixation_runs->clients": """
            SELECT COUNT(*)
            FROM fixation_runs fr
            LEFT JOIN clients c ON c.client_id = fr.client_id
            WHERE c.client_id IS NULL
        """,
        "fixation_input_snapshots->fixation_runs": """
            SELECT COUNT(*)
            FROM fixation_input_snapshots s
            LEFT JOIN fixation_runs fr ON fr.fixation_run_id = s.fixation_run_id
            WHERE fr.fixation_run_id IS NULL
        """,
        "fixation_results->fixation_runs": """
            SELECT COUNT(*)
            FROM fixation_results r
            LEFT JOIN fixation_runs fr ON fr.fixation_run_id = r.fixation_run_id
            WHERE fr.fixation_run_id IS NULL
        """,
        "fixation_audit_rows->fixation_runs": """
            SELECT COUNT(*)
            FROM fixation_audit_rows a
            LEFT JOIN fixation_runs fr ON fr.fixation_run_id = a.fixation_run_id
            WHERE fr.fixation_run_id IS NULL
        """,
        "fixation_validation_errors->fixation_runs": """
            SELECT COUNT(*)
            FROM fixation_validation_errors e
            LEFT JOIN fixation_runs fr ON fr.fixation_run_id = e.fixation_run_id
            WHERE fr.fixation_run_id IS NULL
        """,
    }
    for label, sql in orphan_checks.items():
        orphan_count = _count(sql)
        if orphan_count > 0:
            risks.append(f"{label} has {orphan_count} orphan rows")

    if client_count == 0 and run_count == 0:
        print("[stage-a-preflight] No existing data detected in clients/fixation_runs.")

    if risks:
        message = "Stage A preflight failed; data cleanup/approval required before schema cutover:\n- "
        raise RuntimeError(message + "\n- ".join(risks))

    print("[stage-a-preflight] Completed read-only audit with no blocking risks.")


def downgrade() -> None:
    # Stage A is read-only.
    pass
