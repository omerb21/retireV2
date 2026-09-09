import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

BACKEND = Path(__file__).resolve().parents[1]
PARENT = "c2d8f5a1b309"
HEAD = "d3e9a6b2c410"


def alembic(path, *args, check=True):
    env = dict(os.environ, DATABASE_URL=f"sqlite:///{path.as_posix()}", PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, "-m", "alembic", *args], cwd=BACKEND, env=env, capture_output=True, text=True, encoding="utf-8", check=check)


def seed(path, duplicate=False):
    with sqlite3.connect(path) as db:
        db.execute("INSERT INTO clients(client_id,display_name,id_number) VALUES(1,'Test','123')")
        for identifier in (["A", "B"] if duplicate else ["A"]):
            db.execute("""INSERT INTO m02_intake_records(intake_id,client_id,record_kind,manual_technical_reference,declared_provider_name,declared_account_reference,product_name,declared_product_type,declared_total_balance_amount,declared_component_values,source_type,lifecycle_status,preservation_status,diagnostics,created_by_actor,updated_by_actor,lifecycle_decided_by_actor) VALUES(?,1,'manual',?,'Provider','Account','Product','provident_fund',100,'[]','manual','accepted_for_review','not_applicable','[]','test','test','test')""", (identifier, "manual-" + identifier))


def test_upgrade_from_authoritative_schema_with_data_and_archive_preservation(tmp_path):
    path = tmp_path / "cutover.db"
    alembic(path, "upgrade", PARENT)
    seed(path)
    result = alembic(path, "upgrade", HEAD)
    assert '"products": 1' in result.stdout
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT COUNT(*) FROM pension_products").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM pension_product_components").fetchone()[0] == 11
        assert db.execute("SELECT COUNT(*) FROM m02_intake_records").fetchone()[0] == 1
        assert db.execute("SELECT reported_product_total FROM pension_products").fetchone()[0] == "100.00"
        assert db.execute("SELECT COUNT(*) FROM pension_product_source_links").fetchone()[0] == 1
        with pytest.raises(sqlite3.IntegrityError, match="canonical_evidence_immutable"):
            db.execute("DELETE FROM pension_product_source_links")
    assert alembic(path, "downgrade", PARENT, check=False).returncode != 0
    assert alembic(path, "current").stdout.strip().startswith(HEAD)


def test_ambiguous_authority_aborts_before_schema_or_version_change(tmp_path):
    path = tmp_path / "ambiguous.db"
    alembic(path, "upgrade", PARENT)
    seed(path, duplicate=True)
    result = alembic(path, "upgrade", HEAD, check=False)
    assert result.returncode != 0
    assert "competing_active_intakes" in result.stderr
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT version_num FROM alembic_version").fetchone()[0] == PARENT
        assert db.execute("SELECT COUNT(*) FROM sqlite_master WHERE name='pension_products'").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM m02_intake_records").fetchone()[0] == 2


def test_single_head_and_online_preflight_required(tmp_path):
    path = tmp_path / "empty.db"
    assert alembic(path, "heads").stdout.strip() == "e4f0b7c3d521 (head)"
    result = alembic(path, "upgrade", f"{PARENT}:{HEAD}", "--sql", check=False)
    assert result.returncode != 0
    assert "CANONICAL_CUTOVER_REQUIRES_ONLINE_PREFLIGHT" in result.stderr


def test_canonical_schema_compiles_for_postgresql_with_exact_decimal_ddl():
    import importlib.util
    from io import StringIO
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    spec = importlib.util.spec_from_file_location("canonical_migration_ddl", BACKEND / "alembic/versions/d3e9a6b2c410_canonical_pension_source.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    output = StringIO()
    context = MigrationContext.configure(dialect_name="postgresql", opts={"as_sql": True, "output_buffer": output})
    with Operations.context(context):
        module._create_schema()
    ddl = output.getvalue()
    assert ddl.count("CREATE TABLE ") == 4
    assert ddl.count("NUMERIC(20, 2)") == 4
    assert "UNIQUE (product_id, component_code)" in ddl
    assert "VARCHAR(22)" not in ddl and "FLOAT" not in ddl and "DOUBLE" not in ddl
