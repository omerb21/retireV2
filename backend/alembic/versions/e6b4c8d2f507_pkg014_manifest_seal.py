"""seal PKG-014 adjustment manifests against later membership growth

Revision ID: e6b4c8d2f507
Revises: d5f9b2a7c406
Create Date: 2026-08-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e6b4c8d2f507"
down_revision: str | None = "d5f9b2a7c406"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "m09_scenario_subject_seals",
        sa.Column("scenario_subject_id", sa.String(64), primary_key=True),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("adjustment_count", sa.Integer(), nullable=False),
        sa.Column("adjustment_manifest_fingerprint", sa.String(64), nullable=False),
        sa.Column("actor", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("adjustment_count >= 0", name="ck_m09_subject_seal_count"),
        sa.CheckConstraint("length(adjustment_manifest_fingerprint) = 64", name="ck_m09_subject_seal_fingerprint"),
        sa.ForeignKeyConstraint(
            ["scenario_subject_id", "client_id"],
            ["m09_scenario_subjects.scenario_subject_id", "m09_scenario_subjects.client_id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("scenario_subject_id", "client_id", name="uq_m09_subject_seal_client"),
    )
    op.execute(
        """
        INSERT INTO m09_scenario_subject_seals (
            scenario_subject_id, client_id, adjustment_count,
            adjustment_manifest_fingerprint, actor, created_at
        )
        SELECT s.scenario_subject_id, s.client_id, COUNT(a.adjustment_id),
               s.adjustment_manifest_fingerprint,
               'system:m09-cashflow:M09 cashflow workflow', CURRENT_TIMESTAMP
        FROM m09_scenario_subjects s
        LEFT JOIN m09_scenario_adjustments a
          ON a.scenario_subject_id = s.scenario_subject_id
         AND a.client_id = s.client_id
        GROUP BY s.scenario_subject_id, s.client_id,
                 s.adjustment_manifest_fingerprint
        """
    )
    dialect = op.get_context().dialect.name
    if dialect == "postgresql":
        op.execute(
            """
            CREATE FUNCTION m09_reject_adjustment_after_seal()
            RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM m09_scenario_subject_seals
                    WHERE scenario_subject_id = NEW.scenario_subject_id
                      AND client_id = NEW.client_id
                ) THEN
                    RAISE EXCEPTION 'm09_subject_manifest_sealed' USING ERRCODE = '55000';
                END IF;
                RETURN NEW;
            END;
            $$
            """
        )
        op.execute(
            """
            CREATE FUNCTION m09_validate_subject_seal()
            RETURNS trigger LANGUAGE plpgsql AS $$
            DECLARE actual_count integer; subject_type_value varchar; manifest_fp varchar;
            BEGIN
                SELECT subject_type, adjustment_manifest_fingerprint
                  INTO subject_type_value, manifest_fp
                  FROM m09_scenario_subjects
                 WHERE scenario_subject_id = NEW.scenario_subject_id
                   AND client_id = NEW.client_id;
                SELECT COUNT(*) INTO actual_count FROM m09_scenario_adjustments
                 WHERE scenario_subject_id = NEW.scenario_subject_id
                   AND client_id = NEW.client_id;
                IF subject_type_value IS NULL
                   OR actual_count <> NEW.adjustment_count
                   OR manifest_fp <> NEW.adjustment_manifest_fingerprint
                   OR (subject_type_value = 'baseline' AND actual_count <> 0)
                   OR (subject_type_value = 'adjusted' AND actual_count < 1) THEN
                    RAISE EXCEPTION 'm09_subject_manifest_seal_invalid' USING ERRCODE = '23514';
                END IF;
                RETURN NEW;
            END;
            $$
            """
        )
        op.execute("CREATE TRIGGER trg_m09_adjustment_reject_after_seal BEFORE INSERT ON m09_scenario_adjustments FOR EACH ROW EXECUTE FUNCTION m09_reject_adjustment_after_seal()")
        op.execute("CREATE TRIGGER trg_m09_subject_seal_validate BEFORE INSERT ON m09_scenario_subject_seals FOR EACH ROW EXECUTE FUNCTION m09_validate_subject_seal()")
        op.execute("CREATE TRIGGER trg_m09_scenario_subject_seals_append_only BEFORE UPDATE OR DELETE ON m09_scenario_subject_seals FOR EACH ROW EXECUTE FUNCTION m09_subject_reject_mutation()")
    else:
        op.execute(
            """
            CREATE TRIGGER trg_m09_adjustment_reject_after_seal
            BEFORE INSERT ON m09_scenario_adjustments
            WHEN EXISTS (
                SELECT 1 FROM m09_scenario_subject_seals
                 WHERE scenario_subject_id = NEW.scenario_subject_id
                   AND client_id = NEW.client_id
            )
            BEGIN SELECT RAISE(ABORT, 'm09_subject_manifest_sealed'); END
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_m09_subject_seal_validate
            BEFORE INSERT ON m09_scenario_subject_seals
            WHEN NOT EXISTS (
                SELECT 1 FROM m09_scenario_subjects s
                 WHERE s.scenario_subject_id = NEW.scenario_subject_id
                   AND s.client_id = NEW.client_id
                   AND s.adjustment_manifest_fingerprint = NEW.adjustment_manifest_fingerprint
                   AND ((s.subject_type = 'baseline' AND NEW.adjustment_count = 0)
                     OR (s.subject_type = 'adjusted' AND NEW.adjustment_count > 0))
                   AND NEW.adjustment_count = (
                       SELECT COUNT(*) FROM m09_scenario_adjustments a
                        WHERE a.scenario_subject_id = NEW.scenario_subject_id
                          AND a.client_id = NEW.client_id
                   )
            )
            BEGIN SELECT RAISE(ABORT, 'm09_subject_manifest_seal_invalid'); END
            """
        )
        for operation in ("UPDATE", "DELETE"):
            op.execute(
                f"CREATE TRIGGER trg_m09_scenario_subject_seals_no_{operation.lower()} "
                f"BEFORE {operation} ON m09_scenario_subject_seals "
                "BEGIN SELECT RAISE(ABORT, 'm09_subject_append_only_violation'); END"
            )


def downgrade() -> None:
    dialect = op.get_context().dialect.name
    if dialect == "postgresql":
        op.execute("DROP TRIGGER trg_m09_scenario_subject_seals_append_only ON m09_scenario_subject_seals")
        op.execute("DROP TRIGGER trg_m09_subject_seal_validate ON m09_scenario_subject_seals")
        op.execute("DROP TRIGGER trg_m09_adjustment_reject_after_seal ON m09_scenario_adjustments")
        op.execute("DROP FUNCTION m09_validate_subject_seal()")
        op.execute("DROP FUNCTION m09_reject_adjustment_after_seal()")
    else:
        op.execute("DROP TRIGGER trg_m09_scenario_subject_seals_no_delete")
        op.execute("DROP TRIGGER trg_m09_scenario_subject_seals_no_update")
        op.execute("DROP TRIGGER trg_m09_subject_seal_validate")
        op.execute("DROP TRIGGER trg_m09_adjustment_reject_after_seal")
    op.drop_table("m09_scenario_subject_seals")
