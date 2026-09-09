"""Additive batch identity migration; live PostgreSQL is disposable and opt-in."""
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import psycopg2
import pytest
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session

from app.db.base import load_all_models
from app.models.pension_product import PensionProductSourceLink
from app.services.pension_product_import_service import import_source_batch
from app.services.pension_product_service import PensionProductError
from test_recovery_migration import alembic, seed, PARENT
from test_recovery_migration_postgresql import postgres_url
from test_recovery_pension_products import source

PREVIOUS = "d3e9a6b2c410"
HEAD = "e4f0b7c3d521"
BACKEND = Path(__file__).resolve().parents[1]


def verify_new_batch_and_legacy_overlap(url, historical_checksum=None):
    load_all_models()
    engine = create_engine(url)
    try:
        columns = {column["name"]: column for column in inspect(engine).get_columns("pension_product_source_links")}
        assert columns["batch_identity"]["nullable"]
        assert columns["batch_identity"]["type"].length == 64
        assert any(index["name"] == "ix_pension_source_client_batch" and index["column_names"] == ["client_id", "batch_identity"]
                   for index in inspect(engine).get_indexes("pension_product_source_links"))
        with Session(engine) as db, db.begin():
            result = import_source_batch(db, 1, [("new-a.xml", source(account="new-A")), ("new-b.xml", source(account="new-B"))], "migration-test")
        with Session(engine) as db:
            rows = db.scalars(select(PensionProductSourceLink).where(PensionProductSourceLink.batch_identity == result["batch_identity"])).all()
            assert len(rows) == 2 and all(row.raw_content for row in rows)
        if historical_checksum:
            # A pre-batch checksum remains known, but cannot be silently adopted
            # as an exact batch identity or rewritten through immutable evidence.
            with Session(engine) as db, db.begin(), pytest.raises(PensionProductError) as failure:
                import_source_batch(db, 1, [("legacy.xml", source(account="historical"))], "test")
            assert failure.value.code == "PARTIAL_OVERLAP_SOURCE_BATCH"
    finally:
        engine.dispose()


def test_sqlite_additive_migration_preserves_historical_rows_and_guards(tmp_path):
    import hashlib
    path = tmp_path / "batch-migration.db"
    alembic(path, "upgrade", PARENT)
    seed(path)
    alembic(path, "upgrade", PREVIOUS)
    with sqlite3.connect(path) as db:
        # Seed legacy evidence with a recognized checksum before new migration.
        checksum = hashlib.sha256(source(account="historical")).hexdigest()
        db.execute("INSERT INTO pension_product_source_links(source_link_id,client_id,product_id,source_identity,checksum,filename,raw_content,statement_date,diagnostics) SELECT 'historical-import',client_id,product_id,'historical-identity',?,'legacy.xml',?,'2026-09-01','[]' FROM pension_products", (checksum, source(account="historical")))
        before = db.execute("SELECT * FROM pension_product_source_links ORDER BY source_link_id").fetchall()
        triggers = db.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger' ORDER BY name").fetchall()
    alembic(path, "upgrade", HEAD)
    assert alembic(path, "heads").stdout.strip() == f"{HEAD} (head)"
    with sqlite3.connect(path) as db:
        after = db.execute("SELECT * FROM pension_product_source_links ORDER BY source_link_id").fetchall()
        assert [row[:-1] for row in after] == before and all(row[-1] is None for row in after)
        assert db.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger' ORDER BY name").fetchall() == triggers
        with pytest.raises(sqlite3.IntegrityError, match="canonical_evidence_immutable"):
            db.execute("UPDATE pension_product_source_links SET batch_identity='rewritten'")
        with pytest.raises(sqlite3.IntegrityError, match="LEGACY_PENSION_WORKFLOW_ARCHIVE_ONLY"):
            db.execute("UPDATE m02_intake_records SET product_name='rewritten'")
    verify_new_batch_and_legacy_overlap(f"sqlite:///{path.as_posix()}", checksum)


def test_live_postgresql_batch_migration_and_archive_guards(postgres_url):
    import hashlib
    def migrate(*args):
        result = subprocess.run([sys.executable, "-m", "alembic", *args], cwd=BACKEND,
                                env=dict(os.environ, DATABASE_URL=postgres_url, PYTHONIOENCODING="utf-8"),
                                capture_output=True, text=True, encoding="utf-8", timeout=120)
        assert result.returncode == 0, result.stdout + result.stderr
        return result.stdout.strip()
    migrate("upgrade", PARENT)
    with psycopg2.connect(postgres_url) as db, db.cursor() as cursor:
        cursor.execute("INSERT INTO clients(client_id,display_name,id_number) VALUES(1,'Test','123')")
        cursor.execute("INSERT INTO m05_ledger_subjects(subject_id,client_id,provider_name,account_reference,provider_identity_digest,account_identity_digest) VALUES('S',1,'Provider','Account',%s,%s)", ("a" * 64, "b" * 64))
    migrate("upgrade", PREVIOUS)
    checksum = hashlib.sha256(source(account="historical")).hexdigest()
    with psycopg2.connect(postgres_url) as db, db.cursor() as cursor:
        assert db.server_version // 10000 == 16
        cursor.execute("INSERT INTO pension_product_source_links(source_link_id,client_id,product_id,source_identity,checksum,filename,raw_content,statement_date,diagnostics) VALUES('old',1,'deleted-historical-product','historical-identity',%s,'legacy.xml',%s,'2026-09-01','[]')", (checksum, source(account="historical")))
        cursor.execute("SELECT source_link_id,client_id,product_id,source_identity,checksum,filename,raw_content,statement_date,diagnostics,created_at FROM pension_product_source_links")
        before = cursor.fetchall()
    migrate("upgrade", HEAD)
    assert migrate("heads") == f"{HEAD} (head)" and migrate("current").startswith(HEAD)
    with psycopg2.connect(postgres_url) as db, db.cursor() as cursor:
        cursor.execute("SELECT source_link_id,client_id,product_id,source_identity,checksum,filename,raw_content,statement_date,diagnostics,created_at FROM pension_product_source_links")
        assert cursor.fetchall() == before
        cursor.execute("SELECT batch_identity FROM pension_product_source_links")
        assert cursor.fetchall() == [(None,)]
        cursor.execute("SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal AND tgname LIKE 'trg_m05_%%_archive'")
        assert cursor.fetchone()[0] == 5
    for sql, message in [
        ("UPDATE pension_product_source_links SET batch_identity='rewritten'", "canonical_evidence_immutable"),
        ("DELETE FROM pension_product_source_links", "canonical_evidence_immutable"),
        ("UPDATE m05_ledger_subjects SET provider_name='rewritten'", "LEGACY_PENSION_WORKFLOW_ARCHIVE_ONLY"),
        ("DELETE FROM m05_ledger_subjects", "LEGACY_PENSION_WORKFLOW_ARCHIVE_ONLY"),
        ("INSERT INTO m05_ledger_subjects(subject_id,client_id,provider_name,account_reference,provider_identity_digest,account_identity_digest) VALUES('S',1,'P','A','a','b')", "LEGACY_PENSION_WORKFLOW_ARCHIVE_ONLY"),
    ]:
        with psycopg2.connect(postgres_url) as db, db.cursor() as cursor:
            with pytest.raises(psycopg2.Error, match=message):
                cursor.execute(sql)
            db.rollback()
    verify_new_batch_and_legacy_overlap(postgres_url, checksum)
