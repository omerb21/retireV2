"""Stage 6 P1B append-only pension factor admissions.

Revision ID: d6f1a9c3b704
Revises: c5e019a47d62
"""
from alembic import op
import os
import re
import sqlalchemy as sa


revision = "d6f1a9c3b704"
down_revision = "c5e019a47d62"
branch_labels = None
depends_on = None

TABLE = "scenario_pension_factor_admissions"


def upgrade():
    op.create_table(
        TABLE,
        sa.Column("admission_id", sa.String(64), primary_key=True),
        sa.Column("client_id", sa.Integer(),
                  sa.ForeignKey("clients.client_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("scenario_id", sa.String(64),
                  sa.ForeignKey("scenario_drafts.scenario_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("decision_id", sa.String(64), nullable=False),
        sa.Column("scenario_version", sa.Integer(), nullable=False),
        sa.Column("admission_revision", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.String(128), nullable=False),
        sa.Column("preimage_json", sa.Text(), nullable=False),
        sa.Column("record_fingerprint", sa.String(64), nullable=False),
        sa.Column("permission_admission_fingerprint", sa.String(64), nullable=False),
        sa.Column("manifest_fingerprint", sa.String(64), nullable=False),
        sa.Column("source_fingerprint", sa.String(64), nullable=False),
        sa.Column("election_fingerprint", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.UniqueConstraint("client_id", "scenario_id", "decision_id", "admission_revision",
                            name="uq_s6_factor_admission_revision"),
        sa.CheckConstraint("scenario_version > 0", name="ck_s6_factor_scenario_version"),
        sa.CheckConstraint("admission_revision > 0", name="ck_s6_factor_revision"),
        sa.CheckConstraint("length(actor_id) BETWEEN 1 AND 128", name="ck_s6_factor_actor"),
        sa.CheckConstraint("length(record_fingerprint) = 64", name="ck_s6_factor_fingerprint_length"),
        sa.CheckConstraint("length(permission_admission_fingerprint) = 64",
                           name="ck_s6_factor_permission_fingerprint_length"),
        sa.CheckConstraint("length(manifest_fingerprint) = 64",
                           name="ck_s6_factor_manifest_fingerprint_length"),
        sa.CheckConstraint("length(source_fingerprint) = 64",
                           name="ck_s6_factor_source_fingerprint_length"),
        sa.CheckConstraint("length(election_fingerprint) = 64",
                           name="ck_s6_factor_election_fingerprint_length"),
    )
    op.create_index("ix_s6_factor_admission_current", TABLE,
                    ["client_id", "scenario_id", "decision_id", "admission_revision"])
    if op.get_bind().dialect.name == "postgresql":
        op.execute("""
            CREATE FUNCTION prevent_s6_factor_admission_mutation()
            RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
              RAISE EXCEPTION USING
                ERRCODE = 'P7501',
                CONSTRAINT = 'ck_s6_factor_admission_immutable',
                MESSAGE = 'scenario pension factor admissions are append-only';
            END;
            $$
        """)
        op.execute(f"""
            CREATE TRIGGER trg_s6_factor_admission_immutable
            BEFORE UPDATE OR DELETE ON {TABLE}
            FOR EACH ROW EXECUTE FUNCTION prevent_s6_factor_admission_mutation()
        """)
        role = os.environ.get("CRTISBA_APPLICATION_DB_ROLE")
        if not role or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,62}", role) is None:
            raise RuntimeError("CRTISBA_APPLICATION_DB_ROLE must be a valid explicit PostgreSQL role")
        quoted = op.get_bind().dialect.identifier_preparer.quote_identifier(role)
        op.execute(f"REVOKE ALL PRIVILEGES ON TABLE {TABLE} FROM {quoted}")
        op.execute(f"GRANT SELECT, INSERT ON TABLE {TABLE} TO {quoted}")


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.execute(f"DROP TRIGGER IF EXISTS trg_s6_factor_admission_immutable ON {TABLE}")
        op.execute("DROP FUNCTION IF EXISTS prevent_s6_factor_admission_mutation()")
    op.drop_index("ix_s6_factor_admission_current", table_name=TABLE)
    op.drop_table(TABLE)
