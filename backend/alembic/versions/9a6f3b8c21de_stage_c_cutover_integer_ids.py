"""stage c cutover to integer ids and tighten constraints

Revision ID: 9a6f3b8c21de
Revises: 6f2e9b2b4a11
Create Date: 2026-04-30 20:55:00.000000

SQLite note:
This revision performs explicit table rebuilds because SQLite cannot alter
primary keys/foreign keys in place.
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "9a6f3b8c21de"
down_revision: Union[str, None] = "6f2e9b2b4a11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        _upgrade_postgresql()
        return

    _upgrade_sqlite()


def _upgrade_postgresql() -> None:
    bind = op.get_bind()

    invalid_client_ids = int(
        bind.exec_driver_sql(
            """
            SELECT COUNT(*)
            FROM clients
            WHERE client_id IS NULL
               OR client_id = ''
               OR TRIM(client_id) = ''
               OR client_id !~ '^[0-9]+$'
               OR client_id != CAST(CAST(client_id AS INTEGER) AS TEXT)
            """
        ).scalar_one()
    )
    if invalid_client_ids > 0:
        raise RuntimeError(
            "Stage C cutover blocked: clients.client_id contains non-canonical numeric values; "
            "resolve Stage A/B audit violations before CAST-based PK/FK cutover."
        )

    for table_name, constraint_name in (
        ("client_profiles", "client_profiles_client_id_fkey"),
        ("employment_records", "employment_records_client_id_fkey"),
        ("actual_capitalizations", "actual_capitalizations_client_id_fkey"),
        ("grants", "grants_client_id_fkey"),
        ("grants", "grants_employment_record_id_fkey"),
        ("fixation_runs", "fixation_runs_client_id_fkey"),
        ("fixation_input_snapshots", "fixation_input_snapshots_fixation_run_id_fkey"),
        ("fixation_results", "fixation_results_fixation_run_id_fkey"),
        ("fixation_audit_rows", "fixation_audit_rows_fixation_run_id_fkey"),
        ("fixation_validation_errors", "fixation_validation_errors_fixation_run_id_fkey"),
        ("client_profiles", "client_profiles_client_id_key"),
        ("fixation_input_snapshots", "fixation_input_snapshots_fixation_run_id_key"),
        ("fixation_results", "fixation_results_fixation_run_id_key"),
        ("fixation_audit_rows", "uq_fixation_audit_rows_run_order"),
        ("fixation_validation_errors", "uq_fixation_validation_errors_run_order"),
        ("clients", "clients_pkey"),
        ("fixation_runs", "fixation_runs_pkey"),
    ):
        op.execute(f"ALTER TABLE {table_name} DROP CONSTRAINT IF EXISTS {constraint_name}")

    op.drop_index("ix_fixation_runs_id", table_name="fixation_runs")
    op.drop_index("ix_clients_id_number", table_name="clients")

    op.execute("ALTER TABLE clients ALTER COLUMN client_id TYPE INTEGER USING client_id::integer")
    op.execute("ALTER TABLE clients ALTER COLUMN id_number SET NOT NULL")
    op.execute("ALTER TABLE clients ALTER COLUMN status DROP NOT NULL")
    op.execute("CREATE SEQUENCE IF NOT EXISTS clients_client_id_seq OWNED BY clients.client_id")
    op.execute("ALTER TABLE clients ALTER COLUMN client_id SET DEFAULT nextval('clients_client_id_seq')")
    op.execute("SELECT setval('clients_client_id_seq', COALESCE((SELECT MAX(client_id) FROM clients), 0) + 1, false)")
    op.execute("ALTER TABLE clients ADD CONSTRAINT clients_pkey PRIMARY KEY (client_id)")
    op.create_unique_constraint("clients_id_number_key", "clients", ["id_number"])

    for table_name in (
        "client_profiles",
        "employment_records",
        "grants",
        "actual_capitalizations",
        "fixation_runs",
    ):
        op.execute(f"ALTER TABLE {table_name} ALTER COLUMN client_id TYPE INTEGER USING client_id::integer")

    op.execute("ALTER TABLE fixation_runs ALTER COLUMN id SET NOT NULL")
    op.execute("ALTER TABLE fixation_runs ALTER COLUMN fixation_run_id DROP NOT NULL")
    op.execute("CREATE SEQUENCE IF NOT EXISTS fixation_runs_id_seq OWNED BY fixation_runs.id")
    op.execute("ALTER TABLE fixation_runs ALTER COLUMN id SET DEFAULT nextval('fixation_runs_id_seq')")
    op.execute("SELECT setval('fixation_runs_id_seq', COALESCE((SELECT MAX(id) FROM fixation_runs), 0) + 1, false)")
    op.execute("ALTER TABLE fixation_runs ADD CONSTRAINT fixation_runs_pkey PRIMARY KEY (id)")
    op.create_unique_constraint("fixation_runs_fixation_run_id_key", "fixation_runs", ["fixation_run_id"])

    for table_name in (
        "fixation_input_snapshots",
        "fixation_results",
        "fixation_audit_rows",
        "fixation_validation_errors",
    ):
        op.drop_column(table_name, "fixation_run_id")
        op.alter_column(table_name, "fixation_run_id_int", new_column_name="fixation_run_id")
        op.execute(f"ALTER TABLE {table_name} ALTER COLUMN fixation_run_id SET NOT NULL")

    op.create_unique_constraint("client_profiles_client_id_key", "client_profiles", ["client_id"])
    op.create_foreign_key(
        "client_profiles_client_id_fkey",
        "client_profiles",
        "clients",
        ["client_id"],
        ["client_id"],
    )
    op.create_foreign_key(
        "employment_records_client_id_fkey",
        "employment_records",
        "clients",
        ["client_id"],
        ["client_id"],
    )
    op.create_foreign_key(
        "actual_capitalizations_client_id_fkey",
        "actual_capitalizations",
        "clients",
        ["client_id"],
        ["client_id"],
    )
    op.create_foreign_key("grants_client_id_fkey", "grants", "clients", ["client_id"], ["client_id"])
    op.create_foreign_key(
        "grants_employment_record_id_fkey",
        "grants",
        "employment_records",
        ["employment_record_id"],
        ["employment_record_id"],
    )
    op.create_foreign_key(
        "fixation_runs_client_id_fkey",
        "fixation_runs",
        "clients",
        ["client_id"],
        ["client_id"],
    )
    op.create_unique_constraint(
        "fixation_input_snapshots_fixation_run_id_key",
        "fixation_input_snapshots",
        ["fixation_run_id"],
    )
    op.create_foreign_key(
        "fixation_input_snapshots_fixation_run_id_fkey",
        "fixation_input_snapshots",
        "fixation_runs",
        ["fixation_run_id"],
        ["id"],
    )
    op.create_unique_constraint("fixation_results_fixation_run_id_key", "fixation_results", ["fixation_run_id"])
    op.create_foreign_key(
        "fixation_results_fixation_run_id_fkey",
        "fixation_results",
        "fixation_runs",
        ["fixation_run_id"],
        ["id"],
    )
    op.create_unique_constraint(
        "uq_fixation_audit_rows_run_order",
        "fixation_audit_rows",
        ["fixation_run_id", "row_order"],
    )
    op.create_foreign_key(
        "fixation_audit_rows_fixation_run_id_fkey",
        "fixation_audit_rows",
        "fixation_runs",
        ["fixation_run_id"],
        ["id"],
    )
    op.create_unique_constraint(
        "uq_fixation_validation_errors_run_order",
        "fixation_validation_errors",
        ["fixation_run_id", "error_order"],
    )
    op.create_foreign_key(
        "fixation_validation_errors_fixation_run_id_fkey",
        "fixation_validation_errors",
        "fixation_runs",
        ["fixation_run_id"],
        ["id"],
    )


def _upgrade_sqlite() -> None:
    op.execute("PRAGMA foreign_keys=OFF")

    bind = op.get_bind()

    # CAST(...) operations below are safe only if legacy client_id values are strict
    # canonical integer strings. This guard prevents silent coercion during cutover.
    invalid_client_ids = int(
        bind.exec_driver_sql(
            """
            SELECT COUNT(*)
            FROM clients
            WHERE client_id IS NULL
               OR client_id = ''
               OR TRIM(client_id) = ''
               OR client_id GLOB '*[^0-9]*'
               OR client_id != CAST(CAST(client_id AS INTEGER) AS TEXT)
            """
        ).scalar_one()
    )
    if invalid_client_ids > 0:
        raise RuntimeError(
            "Stage C cutover blocked: clients.client_id contains non-canonical numeric values; "
            "resolve Stage A/B audit violations before CAST-based PK/FK cutover."
        )

    op.execute(
        """
        CREATE TABLE clients_new (
            client_id INTEGER NOT NULL PRIMARY KEY,
            display_name VARCHAR(255) NOT NULL,
            id_number VARCHAR(64) NOT NULL UNIQUE,
            birth_date DATE,
            status VARCHAR(50),
            created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
            updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL
        )
        """
    )
    op.execute(
        """
        INSERT INTO clients_new (client_id, display_name, id_number, birth_date, status, created_at, updated_at)
        SELECT CAST(client_id AS INTEGER), display_name, id_number, birth_date, status, created_at, updated_at
        FROM clients
        """
    )

    op.execute(
        """
        CREATE TABLE client_profiles_new (
            client_profile_id VARCHAR(64) NOT NULL PRIMARY KEY,
            client_id INTEGER NOT NULL UNIQUE,
            birth_date DATE,
            gender VARCHAR(50),
            notes TEXT,
            created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
            updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
            FOREIGN KEY(client_id) REFERENCES clients_new (client_id)
        )
        """
    )
    op.execute(
        """
        INSERT INTO client_profiles_new (client_profile_id, client_id, birth_date, gender, notes, created_at, updated_at)
        SELECT client_profile_id, CAST(client_id AS INTEGER), birth_date, gender, notes, created_at, updated_at
        FROM client_profiles
        """
    )

    op.execute(
        """
        CREATE TABLE employment_records_new (
            employment_record_id VARCHAR(64) NOT NULL PRIMARY KEY,
            client_id INTEGER NOT NULL,
            employer_name VARCHAR(255) NOT NULL,
            work_start_date DATE NOT NULL,
            work_end_date DATE,
            is_current BOOLEAN NOT NULL,
            notes TEXT,
            created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
            updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
            CONSTRAINT ck_employment_dates_order CHECK (work_end_date IS NULL OR work_end_date >= work_start_date),
            FOREIGN KEY(client_id) REFERENCES clients_new (client_id)
        )
        """
    )
    op.execute(
        """
        INSERT INTO employment_records_new
            (employment_record_id, client_id, employer_name, work_start_date, work_end_date, is_current, notes, created_at, updated_at)
        SELECT employment_record_id, CAST(client_id AS INTEGER), employer_name, work_start_date, work_end_date, is_current, notes, created_at, updated_at
        FROM employment_records
        """
    )

    op.execute(
        """
        CREATE TABLE grants_new (
            grant_id VARCHAR(64) NOT NULL PRIMARY KEY,
            client_id INTEGER NOT NULL,
            employment_record_id VARCHAR(64),
            employer_name VARCHAR(255),
            nominal_amount NUMERIC(14, 2),
            indexed_amount NUMERIC(14, 2) NOT NULL,
            grant_date DATE NOT NULL,
            work_start_date DATE NOT NULL,
            work_end_date DATE NOT NULL,
            notes TEXT,
            created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
            updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
            CONSTRAINT ck_grants_indexed_amount_non_negative CHECK (indexed_amount >= 0),
            CONSTRAINT ck_grants_nominal_amount_non_negative CHECK (nominal_amount IS NULL OR nominal_amount >= 0),
            CONSTRAINT ck_grants_work_dates_order CHECK (work_end_date >= work_start_date),
            FOREIGN KEY(client_id) REFERENCES clients_new (client_id),
            FOREIGN KEY(employment_record_id) REFERENCES employment_records_new (employment_record_id)
        )
        """
    )
    op.execute(
        """
        INSERT INTO grants_new
            (grant_id, client_id, employment_record_id, employer_name, nominal_amount, indexed_amount, grant_date, work_start_date, work_end_date, notes, created_at, updated_at)
        SELECT grant_id, CAST(client_id AS INTEGER), employment_record_id, employer_name, nominal_amount, indexed_amount, grant_date, work_start_date, work_end_date, notes, created_at, updated_at
        FROM grants
        """
    )

    op.execute(
        """
        CREATE TABLE actual_capitalizations_new (
            capitalization_id VARCHAR(64) NOT NULL PRIMARY KEY,
            client_id INTEGER NOT NULL,
            amount NUMERIC(14, 2) NOT NULL,
            capitalization_date DATE NOT NULL,
            source_label VARCHAR(255),
            notes TEXT,
            created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
            updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
            CONSTRAINT ck_actual_caps_amount_non_negative CHECK (amount >= 0),
            FOREIGN KEY(client_id) REFERENCES clients_new (client_id)
        )
        """
    )
    op.execute(
        """
        INSERT INTO actual_capitalizations_new
            (capitalization_id, client_id, amount, capitalization_date, source_label, notes, created_at, updated_at)
        SELECT capitalization_id, CAST(client_id AS INTEGER), amount, capitalization_date, source_label, notes, created_at, updated_at
        FROM actual_capitalizations
        """
    )

    op.execute(
        """
        CREATE TABLE fixation_runs_new (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            fixation_run_id VARCHAR(64) UNIQUE,
            client_id INTEGER NOT NULL,
            calculation_version VARCHAR(64) NOT NULL,
            status VARCHAR(32) NOT NULL,
            created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
            created_by VARCHAR(128),
            source_data_version_label VARCHAR(128),
            is_latest BOOLEAN NOT NULL,
            notes TEXT,
            CONSTRAINT ck_fixation_runs_status CHECK (status IN ('success', 'validation_failed')),
            FOREIGN KEY(client_id) REFERENCES clients_new (client_id)
        )
        """
    )
    op.execute(
        """
        INSERT INTO fixation_runs_new
            (id, fixation_run_id, client_id, calculation_version, status, created_at, created_by, source_data_version_label, is_latest, notes)
        SELECT id, fixation_run_id, CAST(client_id AS INTEGER), calculation_version, status, created_at, created_by, source_data_version_label, is_latest, notes
        FROM fixation_runs
        """
    )

    op.execute(
        """
        CREATE TABLE fixation_input_snapshots_new (
            fixation_input_snapshot_id VARCHAR(64) NOT NULL PRIMARY KEY,
            fixation_run_id INTEGER NOT NULL UNIQUE,
            input_contract_version VARCHAR(64) NOT NULL,
            input_payload JSON NOT NULL,
            created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
            FOREIGN KEY(fixation_run_id) REFERENCES fixation_runs_new (id)
        )
        """
    )
    op.execute(
        """
        INSERT INTO fixation_input_snapshots_new
            (fixation_input_snapshot_id, fixation_run_id, input_contract_version, input_payload, created_at)
        SELECT fixation_input_snapshot_id, fixation_run_id_int, input_contract_version, input_payload, created_at
        FROM fixation_input_snapshots
        """
    )

    op.execute(
        """
        CREATE TABLE fixation_results_new (
            fixation_result_id VARCHAR(64) NOT NULL PRIMARY KEY,
            fixation_run_id INTEGER NOT NULL UNIQUE,
            result_contract_version VARCHAR(64) NOT NULL,
            initial_exempt_capital NUMERIC(14, 2) NOT NULL,
            grant_impact_total NUMERIC(14, 2) NOT NULL,
            future_grant_reserved NUMERIC(14, 2) NOT NULL,
            future_grant_impact NUMERIC(14, 2) NOT NULL,
            actual_capitalization_impact NUMERIC(14, 2) NOT NULL,
            idf_impact NUMERIC(14, 2) NOT NULL,
            total_impact NUMERIC(14, 2) NOT NULL,
            remaining_exempt_capital NUMERIC(14, 2) NOT NULL,
            monthly_exempt_pension NUMERIC(14, 2) NOT NULL,
            capital_exemption_percentage NUMERIC(10, 6) NOT NULL,
            pension_exemption_percentage NUMERIC(10, 6) NOT NULL,
            result_payload JSON NOT NULL,
            created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
            CONSTRAINT ck_fixation_results_non_negative_money CHECK (
                initial_exempt_capital >= 0 AND grant_impact_total >= 0 AND future_grant_reserved >= 0 AND
                future_grant_impact >= 0 AND actual_capitalization_impact >= 0 AND idf_impact >= 0 AND
                total_impact >= 0 AND remaining_exempt_capital >= 0 AND monthly_exempt_pension >= 0
            ),
            FOREIGN KEY(fixation_run_id) REFERENCES fixation_runs_new (id)
        )
        """
    )
    op.execute(
        """
        INSERT INTO fixation_results_new
            (fixation_result_id, fixation_run_id, result_contract_version, initial_exempt_capital, grant_impact_total, future_grant_reserved, future_grant_impact,
             actual_capitalization_impact, idf_impact, total_impact, remaining_exempt_capital, monthly_exempt_pension, capital_exemption_percentage,
             pension_exemption_percentage, result_payload, created_at)
        SELECT fixation_result_id, fixation_run_id_int, result_contract_version, initial_exempt_capital, grant_impact_total, future_grant_reserved, future_grant_impact,
               actual_capitalization_impact, idf_impact, total_impact, remaining_exempt_capital, monthly_exempt_pension, capital_exemption_percentage,
               pension_exemption_percentage, result_payload, created_at
        FROM fixation_results
        """
    )

    op.execute(
        """
        CREATE TABLE fixation_audit_rows_new (
            fixation_audit_row_id VARCHAR(64) NOT NULL PRIMARY KEY,
            fixation_run_id INTEGER NOT NULL,
            row_order INTEGER NOT NULL,
            category VARCHAR(64) NOT NULL,
            source_id VARCHAR(64),
            label TEXT NOT NULL,
            input_amount NUMERIC(14, 2),
            output_amount NUMERIC(14, 2) NOT NULL,
            impact_amount NUMERIC(14, 2) NOT NULL,
            details_payload JSON NOT NULL,
            CONSTRAINT uq_fixation_audit_rows_run_order UNIQUE (fixation_run_id, row_order),
            CONSTRAINT ck_fixation_audit_rows_impact_non_negative CHECK (impact_amount >= 0),
            FOREIGN KEY(fixation_run_id) REFERENCES fixation_runs_new (id)
        )
        """
    )
    op.execute(
        """
        INSERT INTO fixation_audit_rows_new
            (fixation_audit_row_id, fixation_run_id, row_order, category, source_id, label, input_amount, output_amount, impact_amount, details_payload)
        SELECT fixation_audit_row_id, fixation_run_id_int, row_order, category, source_id, label, input_amount, output_amount, impact_amount, details_payload
        FROM fixation_audit_rows
        """
    )

    op.execute(
        """
        CREATE TABLE fixation_validation_errors_new (
            fixation_validation_error_id VARCHAR(64) NOT NULL PRIMARY KEY,
            fixation_run_id INTEGER NOT NULL,
            error_order INTEGER NOT NULL,
            code VARCHAR(64) NOT NULL,
            path VARCHAR(255) NOT NULL,
            message TEXT NOT NULL,
            severity VARCHAR(16) NOT NULL,
            source_id VARCHAR(64),
            CONSTRAINT uq_fixation_validation_errors_run_order UNIQUE (fixation_run_id, error_order),
            CONSTRAINT ck_fixation_validation_errors_severity CHECK (severity = 'error'),
            FOREIGN KEY(fixation_run_id) REFERENCES fixation_runs_new (id)
        )
        """
    )
    op.execute(
        """
        INSERT INTO fixation_validation_errors_new
            (fixation_validation_error_id, fixation_run_id, error_order, code, path, message, severity, source_id)
        SELECT fixation_validation_error_id, fixation_run_id_int, error_order, code, path, message, severity, source_id
        FROM fixation_validation_errors
        """
    )

    op.drop_index("ix_fixation_runs_id", table_name="fixation_runs")
    op.drop_index("ix_clients_id_number", table_name="clients")

    op.drop_table("fixation_validation_errors")
    op.drop_table("fixation_audit_rows")
    op.drop_table("fixation_results")
    op.drop_table("fixation_input_snapshots")
    op.drop_table("fixation_runs")
    op.drop_table("actual_capitalizations")
    op.drop_table("grants")
    op.drop_table("employment_records")
    op.drop_table("client_profiles")
    op.drop_table("clients")

    op.rename_table("clients_new", "clients")
    op.rename_table("client_profiles_new", "client_profiles")
    op.rename_table("employment_records_new", "employment_records")
    op.rename_table("grants_new", "grants")
    op.rename_table("actual_capitalizations_new", "actual_capitalizations")
    op.rename_table("fixation_runs_new", "fixation_runs")
    op.rename_table("fixation_input_snapshots_new", "fixation_input_snapshots")
    op.rename_table("fixation_results_new", "fixation_results")
    op.rename_table("fixation_audit_rows_new", "fixation_audit_rows")
    op.rename_table("fixation_validation_errors_new", "fixation_validation_errors")

    op.execute("PRAGMA foreign_keys=ON")


def downgrade() -> None:
    op.execute("PRAGMA foreign_keys=OFF")

    op.execute(
        """
        CREATE TABLE clients_old (
            client_id VARCHAR(64) NOT NULL PRIMARY KEY,
            display_name VARCHAR(255) NOT NULL,
            status VARCHAR(50) NOT NULL,
            created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
            updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
            id_number VARCHAR(64),
            birth_date DATE
        )
        """
    )
    op.execute(
        """
        INSERT INTO clients_old (client_id, display_name, status, created_at, updated_at, id_number, birth_date)
        SELECT CAST(client_id AS TEXT), display_name, COALESCE(status, 'active'), created_at, updated_at, id_number, birth_date
        FROM clients
        """
    )

    op.execute(
        """
        CREATE TABLE run_id_back_map (
            new_run_id INTEGER PRIMARY KEY,
            old_fixation_run_id VARCHAR(64) NOT NULL UNIQUE
        )
        """
    )
    op.execute(
        """
        INSERT INTO run_id_back_map (new_run_id, old_fixation_run_id)
        SELECT id, COALESCE(fixation_run_id, 'RUN-' || CAST(id AS TEXT))
        FROM fixation_runs
        """
    )

    op.execute(
        """
        CREATE TABLE client_profiles_old (
            client_profile_id VARCHAR(64) NOT NULL PRIMARY KEY,
            client_id VARCHAR(64) NOT NULL UNIQUE,
            birth_date DATE,
            gender VARCHAR(50),
            notes TEXT,
            created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
            updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
            FOREIGN KEY(client_id) REFERENCES clients_old (client_id)
        )
        """
    )
    op.execute(
        """
        INSERT INTO client_profiles_old (client_profile_id, client_id, birth_date, gender, notes, created_at, updated_at)
        SELECT client_profile_id, CAST(client_id AS TEXT), birth_date, gender, notes, created_at, updated_at
        FROM client_profiles
        """
    )

    op.execute(
        """
        CREATE TABLE employment_records_old (
            employment_record_id VARCHAR(64) NOT NULL PRIMARY KEY,
            client_id VARCHAR(64) NOT NULL,
            employer_name VARCHAR(255) NOT NULL,
            work_start_date DATE NOT NULL,
            work_end_date DATE,
            is_current BOOLEAN NOT NULL,
            notes TEXT,
            created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
            updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
            CONSTRAINT ck_employment_dates_order CHECK (work_end_date IS NULL OR work_end_date >= work_start_date),
            FOREIGN KEY(client_id) REFERENCES clients_old (client_id)
        )
        """
    )
    op.execute(
        """
        INSERT INTO employment_records_old
            (employment_record_id, client_id, employer_name, work_start_date, work_end_date, is_current, notes, created_at, updated_at)
        SELECT employment_record_id, CAST(client_id AS TEXT), employer_name, work_start_date, work_end_date, is_current, notes, created_at, updated_at
        FROM employment_records
        """
    )

    op.execute(
        """
        CREATE TABLE grants_old (
            grant_id VARCHAR(64) NOT NULL PRIMARY KEY,
            client_id VARCHAR(64) NOT NULL,
            employment_record_id VARCHAR(64),
            employer_name VARCHAR(255),
            nominal_amount NUMERIC(14, 2),
            indexed_amount NUMERIC(14, 2) NOT NULL,
            grant_date DATE NOT NULL,
            work_start_date DATE NOT NULL,
            work_end_date DATE NOT NULL,
            notes TEXT,
            created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
            updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
            CONSTRAINT ck_grants_indexed_amount_non_negative CHECK (indexed_amount >= 0),
            CONSTRAINT ck_grants_nominal_amount_non_negative CHECK (nominal_amount IS NULL OR nominal_amount >= 0),
            CONSTRAINT ck_grants_work_dates_order CHECK (work_end_date >= work_start_date),
            FOREIGN KEY(client_id) REFERENCES clients_old (client_id),
            FOREIGN KEY(employment_record_id) REFERENCES employment_records_old (employment_record_id)
        )
        """
    )
    op.execute(
        """
        INSERT INTO grants_old
            (grant_id, client_id, employment_record_id, employer_name, nominal_amount, indexed_amount, grant_date, work_start_date, work_end_date, notes, created_at, updated_at)
        SELECT grant_id, CAST(client_id AS TEXT), employment_record_id, employer_name, nominal_amount, indexed_amount, grant_date, work_start_date, work_end_date, notes, created_at, updated_at
        FROM grants
        """
    )

    op.execute(
        """
        CREATE TABLE actual_capitalizations_old (
            capitalization_id VARCHAR(64) NOT NULL PRIMARY KEY,
            client_id VARCHAR(64) NOT NULL,
            amount NUMERIC(14, 2) NOT NULL,
            capitalization_date DATE NOT NULL,
            source_label VARCHAR(255),
            notes TEXT,
            created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
            updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
            CONSTRAINT ck_actual_caps_amount_non_negative CHECK (amount >= 0),
            FOREIGN KEY(client_id) REFERENCES clients_old (client_id)
        )
        """
    )
    op.execute(
        """
        INSERT INTO actual_capitalizations_old
            (capitalization_id, client_id, amount, capitalization_date, source_label, notes, created_at, updated_at)
        SELECT capitalization_id, CAST(client_id AS TEXT), amount, capitalization_date, source_label, notes, created_at, updated_at
        FROM actual_capitalizations
        """
    )

    op.execute(
        """
        CREATE TABLE fixation_runs_old (
            fixation_run_id VARCHAR(64) NOT NULL PRIMARY KEY,
            client_id VARCHAR(64) NOT NULL,
            calculation_version VARCHAR(64) NOT NULL,
            status VARCHAR(32) NOT NULL,
            created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
            created_by VARCHAR(128),
            source_data_version_label VARCHAR(128),
            is_latest BOOLEAN NOT NULL,
            notes TEXT,
            id INTEGER,
            CONSTRAINT ck_fixation_runs_status CHECK (status IN ('success', 'validation_failed')),
            FOREIGN KEY(client_id) REFERENCES clients_old (client_id)
        )
        """
    )
    op.execute(
        """
        INSERT INTO fixation_runs_old
            (fixation_run_id, client_id, calculation_version, status, created_at, created_by, source_data_version_label, is_latest, notes, id)
        SELECT m.old_fixation_run_id, CAST(fr.client_id AS TEXT), fr.calculation_version, fr.status, fr.created_at, fr.created_by, fr.source_data_version_label, fr.is_latest, fr.notes, fr.id
        FROM fixation_runs fr
        JOIN run_id_back_map m ON m.new_run_id = fr.id
        """
    )

    op.execute(
        """
        CREATE TABLE fixation_input_snapshots_old (
            fixation_input_snapshot_id VARCHAR(64) NOT NULL PRIMARY KEY,
            fixation_run_id VARCHAR(64) NOT NULL,
            input_contract_version VARCHAR(64) NOT NULL,
            input_payload JSON NOT NULL,
            created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
            fixation_run_id_int INTEGER,
            FOREIGN KEY(fixation_run_id) REFERENCES fixation_runs_old (fixation_run_id),
            UNIQUE(fixation_run_id)
        )
        """
    )
    op.execute(
        """
        INSERT INTO fixation_input_snapshots_old
            (fixation_input_snapshot_id, fixation_run_id, input_contract_version, input_payload, created_at, fixation_run_id_int)
        SELECT s.fixation_input_snapshot_id, m.old_fixation_run_id, s.input_contract_version, s.input_payload, s.created_at, s.fixation_run_id
        FROM fixation_input_snapshots s
        JOIN run_id_back_map m ON m.new_run_id = s.fixation_run_id
        """
    )

    op.execute(
        """
        CREATE TABLE fixation_results_old (
            fixation_result_id VARCHAR(64) NOT NULL PRIMARY KEY,
            fixation_run_id VARCHAR(64) NOT NULL,
            result_contract_version VARCHAR(64) NOT NULL,
            initial_exempt_capital NUMERIC(14, 2) NOT NULL,
            grant_impact_total NUMERIC(14, 2) NOT NULL,
            future_grant_reserved NUMERIC(14, 2) NOT NULL,
            future_grant_impact NUMERIC(14, 2) NOT NULL,
            actual_capitalization_impact NUMERIC(14, 2) NOT NULL,
            idf_impact NUMERIC(14, 2) NOT NULL,
            total_impact NUMERIC(14, 2) NOT NULL,
            remaining_exempt_capital NUMERIC(14, 2) NOT NULL,
            monthly_exempt_pension NUMERIC(14, 2) NOT NULL,
            capital_exemption_percentage NUMERIC(10, 6) NOT NULL,
            pension_exemption_percentage NUMERIC(10, 6) NOT NULL,
            result_payload JSON NOT NULL,
            created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
            fixation_run_id_int INTEGER,
            CONSTRAINT ck_fixation_results_non_negative_money CHECK (
                initial_exempt_capital >= 0 AND grant_impact_total >= 0 AND future_grant_reserved >= 0 AND
                future_grant_impact >= 0 AND actual_capitalization_impact >= 0 AND idf_impact >= 0 AND
                total_impact >= 0 AND remaining_exempt_capital >= 0 AND monthly_exempt_pension >= 0
            ),
            FOREIGN KEY(fixation_run_id) REFERENCES fixation_runs_old (fixation_run_id),
            UNIQUE(fixation_run_id)
        )
        """
    )
    op.execute(
        """
        INSERT INTO fixation_results_old
            (fixation_result_id, fixation_run_id, result_contract_version, initial_exempt_capital, grant_impact_total, future_grant_reserved, future_grant_impact,
             actual_capitalization_impact, idf_impact, total_impact, remaining_exempt_capital, monthly_exempt_pension, capital_exemption_percentage,
             pension_exemption_percentage, result_payload, created_at, fixation_run_id_int)
        SELECT r.fixation_result_id, m.old_fixation_run_id, r.result_contract_version, r.initial_exempt_capital, r.grant_impact_total, r.future_grant_reserved, r.future_grant_impact,
               r.actual_capitalization_impact, r.idf_impact, r.total_impact, r.remaining_exempt_capital, r.monthly_exempt_pension, r.capital_exemption_percentage,
               r.pension_exemption_percentage, r.result_payload, r.created_at, r.fixation_run_id
        FROM fixation_results r
        JOIN run_id_back_map m ON m.new_run_id = r.fixation_run_id
        """
    )

    op.execute(
        """
        CREATE TABLE fixation_audit_rows_old (
            fixation_audit_row_id VARCHAR(64) NOT NULL PRIMARY KEY,
            fixation_run_id VARCHAR(64) NOT NULL,
            row_order INTEGER NOT NULL,
            category VARCHAR(64) NOT NULL,
            source_id VARCHAR(64),
            label TEXT NOT NULL,
            input_amount NUMERIC(14, 2),
            output_amount NUMERIC(14, 2) NOT NULL,
            impact_amount NUMERIC(14, 2) NOT NULL,
            details_payload JSON NOT NULL,
            fixation_run_id_int INTEGER,
            CONSTRAINT uq_fixation_audit_rows_run_order UNIQUE (fixation_run_id, row_order),
            CONSTRAINT ck_fixation_audit_rows_impact_non_negative CHECK (impact_amount >= 0),
            FOREIGN KEY(fixation_run_id) REFERENCES fixation_runs_old (fixation_run_id)
        )
        """
    )
    op.execute(
        """
        INSERT INTO fixation_audit_rows_old
            (fixation_audit_row_id, fixation_run_id, row_order, category, source_id, label, input_amount, output_amount, impact_amount, details_payload, fixation_run_id_int)
        SELECT a.fixation_audit_row_id, m.old_fixation_run_id, a.row_order, a.category, a.source_id, a.label, a.input_amount, a.output_amount, a.impact_amount, a.details_payload, a.fixation_run_id
        FROM fixation_audit_rows a
        JOIN run_id_back_map m ON m.new_run_id = a.fixation_run_id
        """
    )

    op.execute(
        """
        CREATE TABLE fixation_validation_errors_old (
            fixation_validation_error_id VARCHAR(64) NOT NULL PRIMARY KEY,
            fixation_run_id VARCHAR(64) NOT NULL,
            error_order INTEGER NOT NULL,
            code VARCHAR(64) NOT NULL,
            path VARCHAR(255) NOT NULL,
            message TEXT NOT NULL,
            severity VARCHAR(16) NOT NULL,
            source_id VARCHAR(64),
            fixation_run_id_int INTEGER,
            CONSTRAINT uq_fixation_validation_errors_run_order UNIQUE (fixation_run_id, error_order),
            CONSTRAINT ck_fixation_validation_errors_severity CHECK (severity = 'error'),
            FOREIGN KEY(fixation_run_id) REFERENCES fixation_runs_old (fixation_run_id)
        )
        """
    )
    op.execute(
        """
        INSERT INTO fixation_validation_errors_old
            (fixation_validation_error_id, fixation_run_id, error_order, code, path, message, severity, source_id, fixation_run_id_int)
        SELECT e.fixation_validation_error_id, m.old_fixation_run_id, e.error_order, e.code, e.path, e.message, e.severity, e.source_id, e.fixation_run_id
        FROM fixation_validation_errors e
        JOIN run_id_back_map m ON m.new_run_id = e.fixation_run_id
        """
    )

    op.drop_table("fixation_validation_errors")
    op.drop_table("fixation_audit_rows")
    op.drop_table("fixation_results")
    op.drop_table("fixation_input_snapshots")
    op.drop_table("fixation_runs")
    op.drop_table("actual_capitalizations")
    op.drop_table("grants")
    op.drop_table("employment_records")
    op.drop_table("client_profiles")
    op.drop_table("clients")

    op.rename_table("clients_old", "clients")
    op.rename_table("client_profiles_old", "client_profiles")
    op.rename_table("employment_records_old", "employment_records")
    op.rename_table("grants_old", "grants")
    op.rename_table("actual_capitalizations_old", "actual_capitalizations")
    op.rename_table("fixation_runs_old", "fixation_runs")
    op.rename_table("fixation_input_snapshots_old", "fixation_input_snapshots")
    op.rename_table("fixation_results_old", "fixation_results")
    op.rename_table("fixation_audit_rows_old", "fixation_audit_rows")
    op.rename_table("fixation_validation_errors_old", "fixation_validation_errors")

    op.drop_table("run_id_back_map")

    op.create_index("ix_clients_id_number", "clients", ["id_number"], unique=False)
    op.create_index("ix_fixation_runs_id", "fixation_runs", ["id"], unique=True)

    op.execute("PRAGMA foreign_keys=ON")
