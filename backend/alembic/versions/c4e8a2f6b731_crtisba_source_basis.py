"""CRTISBA append-only source-basis decisions."""
import os
import re

from alembic import op
import sqlalchemy as sa

revision = "c4e8a2f6b731"
down_revision = "b3c9d6f2a410"
branch_labels = None
depends_on = None

TABLE = "retirement_target_date_income_source_basis_decisions"


def upgrade():
    bind = op.get_bind()
    postgres = bind.dialect.name == "postgresql"
    decision_id = (sa.Column("decision_id", sa.BigInteger(), sa.Identity(always=True), nullable=False)
                   if postgres else sa.Column("decision_id", sa.Integer(), nullable=False, autoincrement=True))
    decided_default = sa.text("transaction_timestamp()" if postgres else "CURRENT_TIMESTAMP")
    op.create_table(
        TABLE,
        decision_id,
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.String(128), nullable=False),
        sa.Column("source_kind", sa.String(32), nullable=False),
        sa.Column("decision_version", sa.BigInteger(), nullable=False),
        sa.Column("planning_calculation_input_fingerprint", sa.String(64), nullable=False),
        sa.Column("pension_source_version", sa.Integer()),
        sa.Column("recurring_source_version_fingerprint", sa.String(64)),
        sa.Column("source_fingerprint", sa.String(64), nullable=False),
        sa.Column("amount_authority_fingerprint", sa.String(64), nullable=False),
        sa.Column("pension_source_execution_fingerprint", sa.String(64)),
        sa.Column("pension_source_result_fingerprint", sa.String(64)),
        sa.Column("portfolio_source_entry_fingerprint", sa.String(64)),
        sa.Column("retirement_target_date", sa.Date()),
        sa.Column("income_basis", sa.String(16), nullable=False),
        sa.Column("income_basis_provenance", sa.String(40), nullable=False),
        sa.Column("price_basis", sa.String(64)),
        sa.Column("price_reference_date", sa.Date()),
        sa.Column("price_basis_provenance", sa.String(40)),
        sa.Column("decision_actor", sa.String(128), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False, server_default=decided_default),
        sa.Column("decision_fingerprint", sa.String(64), nullable=False),
        sa.PrimaryKeyConstraint("decision_id", name="pk_crtisba_decisions"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.client_id"], name="fk_crtisba_decision_client", ondelete="RESTRICT"),
        sa.UniqueConstraint("client_id", "source_kind", "source_id", "decision_version", name="uq_crtisba_source_decision_version"),
        sa.CheckConstraint("decision_version BETWEEN 1 AND 9223372036854775807", name="ck_crtisba_decision_version_positive"),
        sa.CheckConstraint("source_kind IN ('PENSION','RECURRING_INCOME')", name="ck_crtisba_source_kind"),
        sa.CheckConstraint("(source_kind = 'PENSION' AND (source_id LIKE 'manual:%' OR source_id LIKE 'conversion:%')) OR (source_kind = 'RECURRING_INCOME' AND source_id LIKE 'income:%')", name="ck_crtisba_source_identity_shape"),
        sa.CheckConstraint("income_basis IN ('GROSS','NET','UNKNOWN')", name="ck_crtisba_income_basis"),
        sa.CheckConstraint("income_basis_provenance IN ('EXPLICIT_PROFESSIONAL','UPSTREAM_RECURRING_AMOUNT_BASIS','MISSING')", name="ck_crtisba_income_basis_provenance"),
        sa.CheckConstraint("price_basis IS NULL OR price_basis IN ('NOMINAL_AT_RETIREMENT_TARGET_DATE','REAL_AT_REFERENCE_DATE','UNKNOWN')", name="ck_crtisba_price_basis"),
        sa.CheckConstraint("price_basis_provenance IS NULL OR price_basis_provenance IN ('EXPLICIT_PROFESSIONAL','MISSING')", name="ck_crtisba_price_basis_provenance"),
        sa.CheckConstraint("(source_kind = 'PENSION' AND pension_source_version IS NOT NULL AND recurring_source_version_fingerprint IS NULL AND pension_source_execution_fingerprint IS NOT NULL AND pension_source_result_fingerprint IS NOT NULL AND portfolio_source_entry_fingerprint IS NOT NULL AND retirement_target_date IS NOT NULL AND price_basis IS NULL AND price_reference_date IS NULL AND price_basis_provenance IS NULL) OR (source_kind = 'RECURRING_INCOME' AND pension_source_version IS NULL AND recurring_source_version_fingerprint IS NOT NULL AND pension_source_execution_fingerprint IS NULL AND pension_source_result_fingerprint IS NULL AND portfolio_source_entry_fingerprint IS NULL AND retirement_target_date IS NULL AND price_basis IS NOT NULL AND price_basis_provenance IS NOT NULL)", name="ck_crtisba_kind_payload"),
        sa.CheckConstraint("(price_basis = 'REAL_AT_REFERENCE_DATE' AND price_reference_date IS NOT NULL) OR ((price_basis IS NULL OR price_basis <> 'REAL_AT_REFERENCE_DATE') AND price_reference_date IS NULL)", name="ck_crtisba_reference_date"),
        sa.CheckConstraint("length(planning_calculation_input_fingerprint)=64 AND (recurring_source_version_fingerprint IS NULL OR length(recurring_source_version_fingerprint)=64) AND length(source_fingerprint)=64 AND length(amount_authority_fingerprint)=64 AND (pension_source_execution_fingerprint IS NULL OR length(pension_source_execution_fingerprint)=64) AND (pension_source_result_fingerprint IS NULL OR length(pension_source_result_fingerprint)=64) AND (portfolio_source_entry_fingerprint IS NULL OR length(portfolio_source_entry_fingerprint)=64) AND length(decision_fingerprint)=64", name="ck_crtisba_hash_shapes"),
    )
    op.create_index("ix_crtisba_source_latest_version", TABLE, ["client_id", "source_kind", "source_id", sa.text("decision_version DESC")])
    if bind.dialect.name == "postgresql":
        op.execute("""CREATE FUNCTION reject_crtisba_decision_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION USING ERRCODE='P7501', CONSTRAINT='trg_crtisba_decision_immutable', MESSAGE='CRTISBA_DECISION_IMMUTABLE'; END; $$""")
        op.execute(f"CREATE TRIGGER trg_crtisba_decision_immutable BEFORE UPDATE OR DELETE ON {TABLE} FOR EACH ROW EXECUTE FUNCTION reject_crtisba_decision_mutation()")
        role = os.environ.get("CRTISBA_APPLICATION_DB_ROLE")
        if role:
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,62}", role) is None:
                raise RuntimeError("CRTISBA_APPLICATION_DB_ROLE is not a valid PostgreSQL identifier")
            quoted = bind.dialect.identifier_preparer.quote_identifier(role)
            sequence = bind.scalar(sa.text("SELECT pg_get_serial_sequence(:table_name, 'decision_id')"), {"table_name": TABLE})
            if not sequence:
                raise RuntimeError("CRTISBA identity sequence was not created")
            quoted_sequence = ".".join(bind.dialect.identifier_preparer.quote_identifier(part) for part in sequence.split("."))
            op.execute(f"REVOKE ALL PRIVILEGES ON TABLE {TABLE} FROM {quoted}")
            op.execute(f"GRANT SELECT, INSERT ON TABLE {TABLE} TO {quoted}")
            op.execute(f"REVOKE ALL PRIVILEGES ON SEQUENCE {quoted_sequence} FROM {quoted}")
            op.execute(f"GRANT USAGE, SELECT ON SEQUENCE {quoted_sequence} TO {quoted}")


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(f"DROP TRIGGER IF EXISTS trg_crtisba_decision_immutable ON {TABLE}")
        op.execute("DROP FUNCTION IF EXISTS reject_crtisba_decision_mutation()")
    op.drop_index("ix_crtisba_source_latest_version", table_name=TABLE)
    op.drop_table(TABLE)
