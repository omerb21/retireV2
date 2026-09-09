"""Opt-in real PostgreSQL 16 cutover, never the user's configured database.

Run with RECOVERY_POSTGRES_TEST=1 and a Docker daemon with postgres:16 available,
or RECOVERY_POSTGRES_BIN pointing to trusted portable PostgreSQL 16 binaries.
Both modes create isolated databases, never consume the normal DATABASE_URL.
"""
import json
import os
from pathlib import Path
import subprocess
import socket
import sys
import time
from uuid import uuid4

import psycopg2
import pytest
from sqlalchemy import create_engine

from app.db.base import load_all_models

BACKEND = Path(__file__).resolve().parents[1]


@pytest.fixture
def postgres_url(tmp_path):
    if os.environ.get("RECOVERY_POSTGRES_TEST") != "1":
        pytest.skip("isolated live PostgreSQL test requires RECOVERY_POSTGRES_TEST=1")
    if os.environ.get("RECOVERY_POSTGRES_BIN"):
        # Portable alternative when Docker is unavailable; no installed service,
        # shared database, external interface or pre-existing cluster is used.
        binaries = Path(os.environ["RECOVERY_POSTGRES_BIN"]).resolve(strict=True)
        cluster = tmp_path / "isolated-postgres"
        assert not cluster.exists()
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        def pg(tool, *args):
            return subprocess.run([str(binaries / tool), *map(str, args)], check=True,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
                                  timeout=90, creationflags=flags)
        pg("initdb", "-D", cluster, "-U", "postgres", "-A", "trust", "--encoding=UTF8", "--no-locale")
        assert cluster.resolve().parent == tmp_path.resolve() and not cluster.is_symlink()
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        try:
            pg("pg_ctl", "-D", cluster, "-l", tmp_path / "postgres.log",
               "-o", f"-h 127.0.0.1 -p {port}", "-w", "-t", "30", "start")
            yield f"postgresql://postgres@127.0.0.1:{port}/postgres"
        finally:
            # Only the cluster created above is ever stopped; files remain in
            # pytest's temporary directory for inspection, no recursive delete.
            if (cluster / "postmaster.pid").exists():
                pg("pg_ctl", "-D", cluster, "-m", "fast", "-w", "stop")
        return
    name = "retire-listener-test-" + uuid4().hex
    def docker(*args):
        return subprocess.check_output(["docker", *args], text=True, timeout=120).strip()
    container = docker("run", "--rm", "-d", "--name", name, "--label", "retire.listener.test=" + name,
                       "--tmpfs", "/var/lib/postgresql/data", "-p", "127.0.0.1::5432",
                       "-e", "POSTGRES_PASSWORD=isolated-test", "-e", "POSTGRES_DB=listener_test", "postgres:16")
    try:
        info = json.loads(docker("inspect", container))[0]
        assert info["Config"]["Labels"]["retire.listener.test"] == name
        port = info["NetworkSettings"]["Ports"]["5432/tcp"][0]["HostPort"]
        url = f"postgresql://postgres:isolated-test@127.0.0.1:{port}/listener_test"
        for _ in range(100):
            try:
                connection = psycopg2.connect(url)
                connection.close()
                break
            except psycopg2.OperationalError:
                time.sleep(0.2)
        else:
            pytest.fail("isolated PostgreSQL did not become ready")
        yield url
    finally:
        info = json.loads(docker("inspect", container))[0]
        assert info["Id"] == container and info["Config"]["Labels"]["retire.listener.test"] == name
        docker("stop", container)


def test_live_postgresql_cutover_and_archive_guards(postgres_url):
    def alembic(*args):
        result = subprocess.run([sys.executable, "-m", "alembic", *args], cwd=BACKEND,
                                env=dict(os.environ, DATABASE_URL=postgres_url, PYTHONIOENCODING="utf-8"),
                                capture_output=True, text=True, encoding="utf-8", timeout=120)
        assert result.returncode == 0, result.stdout + result.stderr
        return result.stdout
    alembic("upgrade", "c2d8f5a1b309")
    with psycopg2.connect(postgres_url) as db, db.cursor() as cursor:
        assert db.server_version // 10000 == 16
        cursor.execute("SELECT 1; SELECT 2")
        assert cursor.fetchone() == (2,)  # This driver really accepts stacked SQL.
        cursor.execute("INSERT INTO clients(client_id,display_name,id_number) VALUES(1,'Test','123')")
        cursor.execute("""INSERT INTO m02_intake_records(intake_id,client_id,record_kind,manual_technical_reference,declared_provider_name,declared_account_reference,product_name,declared_product_type,declared_total_balance_amount,declared_component_values,source_type,lifecycle_status,preservation_status,diagnostics,created_by_actor,updated_by_actor,lifecycle_decided_by_actor) VALUES('A',1,'manual','manual-A','Provider','Account','Product','provident_fund',100,'[]','manual','accepted_for_review','not_applicable','[]','test','test','test')""")
        cursor.execute("INSERT INTO m05_ledger_subjects(subject_id,client_id,provider_name,account_reference,provider_identity_digest,account_identity_digest) VALUES('S',1,'Provider','Account',%s,%s)", ("a" * 64, "b" * 64))
    assert '"products": 1' in alembic("upgrade", "d3e9a6b2c410")
    assert alembic("heads").strip() == "e4f0b7c3d521 (head)"
    assert alembic("current").strip().startswith("d3e9a6b2c410")
    with psycopg2.connect(postgres_url) as db, db.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM pension_products WHERE reported_product_total=100")
        assert cursor.fetchone()[0] == 1
        cursor.execute("SELECT count(*) FROM pension_product_components WHERE balance=0")
        assert cursor.fetchone()[0] == 11
        for table in ("pension_product_source_links", "pension_product_audit_events", "m05_ledger_subjects"):
            cursor.execute("SELECT count(*) FROM " + table)
            assert cursor.fetchone()[0] == 1
        cursor.execute("SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal AND tgname LIKE 'trg_m05_%%_archive'")
        assert cursor.fetchone()[0] == 5
    # Direct driver bypasses SQLAlchemy: these failures must be database triggers.
    for sql in ("INSERT INTO m05_ledger_subjects SELECT * FROM m05_ledger_subjects",
                "UPDATE m05_ledger_subjects SET provider_name='changed'",
                "DELETE FROM m05_ledger_subjects"):
        with psycopg2.connect(postgres_url) as db, db.cursor() as cursor:
            with pytest.raises(psycopg2.Error, match="LEGACY_PENSION_WORKFLOW_ARCHIVE_ONLY"):
                cursor.execute(sql)
            db.rollback()
    load_all_models()
    engine = create_engine(postgres_url)
    try:
        for sql in (
            "WITH q AS (SELECT 1) UPDATE public.m05_ledger_subjects SET provider_name='x'",
            'WITH q AS (SELECT 1) DELETE FROM ONLY public."m05_ledger_subjects"',
            "CREATE TABLE harmless(id int); UPDATE m05_ledger_subjects SET provider_name='x'",
            "CREATE TABLE harmless(id int); DELETE FROM m05_ledger_subjects",
        ):
            with engine.connect() as connection, pytest.raises(ValueError, match="M05 append-only"):
                connection.exec_driver_sql(sql)
    finally:
        engine.dispose()
