"""SC-PERM real PostgreSQL 16 snapshot evidence (opt-in and isolated)."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
import os
from pathlib import Path
import subprocess
import sys
from threading import Event, get_ident

import pytest
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import load_all_models
from app.models.client import Client
from app.models.pension_product import COMPONENT_CODES, PensionProduct, PensionProductComponent
from app.services import scenario_permission_preview_service as subject
from test_recovery_migration_postgresql import postgres_url


BACKEND = Path(__file__).resolve().parents[1]
APPLICATION_ROLE = "sc_perm_test_app"


def _migrate(url):
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND,
        env={
            **os.environ,
            "DATABASE_URL": url,
            "PYTHONIOENCODING": "utf-8",
            "CRTISBA_APPLICATION_DB_ROLE": APPLICATION_ROLE,
        },
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=180,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def _seed(engine):
    with Session(engine) as db, db.begin():
        db.add(Client(client_id=1, display_name="SC-PERM PostgreSQL", id_number="sc-perm-pg"))
        db.add(PensionProduct(
            product_id="pg-fund",
            client_id=1,
            source_kind="imported",
            source_identity="pg-source",
            provider_name="גוף סינתטי",
            provider_identifier=None,
            product_name="מוצר בדיקה",
            product_type="קרן פנסיה",
            account_reference="pg-account",
            start_date=None,
            statement_date=None,
            historical_employers=[],
            reported_product_total=Decimal("66.00"),
            reported_rewards_total=Decimal("51.00"),
            reported_severance_total=Decimal("15.00"),
            version=1,
            created_by="test",
            updated_by="test",
        ))
        db.add_all([
            PensionProductComponent(
                component_id=f"pg-{position:02d}",
                product_id="pg-fund",
                component_code=code,
                balance=Decimal(position),
            )
            for position, code in enumerate(COMPONENT_CODES, start=1)
        ])


def _preview(factory):
    return subject.preview(
        factory,
        client_id=1,
        product_id="pg-fund",
        action="pension",
        effective_date=date(2026, 10, 24),
    )


def test_postgresql_16_read_only_snapshot_concurrency_and_failure_cleanup(
    postgres_url, monkeypatch,
):
    load_all_models()
    engine = create_engine(postgres_url)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    try:
        with engine.begin() as connection:
            connection.execute(text(f"CREATE ROLE {APPLICATION_ROLE} NOLOGIN"))
        _migrate(postgres_url)
        with engine.connect() as connection:
            assert connection.scalar(text("SHOW server_version")).startswith("16.")
        _seed(engine)

        statements: list[str] = []
        observed: dict[str, str] = {}
        original_read = subject._read_snapshot

        def inspect_transaction(db, *args):
            observed["isolation"] = db.scalar(text("SHOW transaction_isolation"))
            observed["read_only"] = db.scalar(text("SHOW transaction_read_only"))
            return original_read(db, *args)

        def capture(_connection, _cursor, statement, _parameters, _context, _many):
            statements.append(statement.strip().upper())

        monkeypatch.setattr(subject, "_read_snapshot", inspect_transaction)
        event.listen(engine, "before_cursor_execute", capture)
        try:
            result = _preview(factory)
        finally:
            event.remove(engine, "before_cursor_execute", capture)
        assert result["components"][0]["balance"] == "1.00"
        assert observed == {"isolation": "repeatable read", "read_only": "on"}
        assert statements and all(
            statement.startswith(("SELECT", "SHOW")) for statement in statements
        ), statements
        assert not any(
            marker in statement
            for statement in statements
            for marker in ("INSERT ", "UPDATE ", "DELETE ", "COMMIT", "FOR UPDATE", "ADVISORY")
        )

        monkeypatch.setattr(subject, "_read_snapshot", original_read)
        paused, resume = Event(), Event()
        reader_thread = [None]

        def pause_reader(_connection, _cursor, statement, _parameters, _context, _many):
            upper = statement.upper()
            if (
                get_ident() == reader_thread[0]
                and "FROM PENSION_PRODUCTS" in upper
                and "PENSION_PRODUCT_COMPONENTS" not in upper
                and not paused.is_set()
            ):
                paused.set()
                assert resume.wait(20)

        event.listen(engine, "after_cursor_execute", pause_reader)

        def read_old():
            reader_thread[0] = get_ident()
            return _preview(factory)

        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                pending = pool.submit(read_old)
                assert paused.wait(20)
                with factory.begin() as writer:
                    row = writer.scalar(select(PensionProductComponent).where(
                        PensionProductComponent.product_id == "pg-fund",
                        PensionProductComponent.component_code == COMPONENT_CODES[0],
                    ))
                    row.balance = Decimal("999.00")
                resume.set()
                old = pending.result(timeout=20)
        finally:
            resume.set()
            event.remove(engine, "after_cursor_execute", pause_reader)
        assert old["components"][0]["balance"] == "1.00"
        fresh = _preview(factory)
        assert fresh["components"][0]["balance"] == "999.00"
        assert fresh["source_fingerprint"] != old["source_fingerprint"]

        def database_failure(db, *_args):
            db.execute(text("SELECT * FROM sc_perm_deliberately_missing_relation"))

        monkeypatch.setattr(subject, "_read_snapshot", database_failure)
        with pytest.raises(subject.ScenarioPermissionError) as caught:
            _preview(factory)
        assert caught.value.code == "PREVIEW_DATABASE_UNAVAILABLE"
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT 1")) == 1
            connection.rollback()
    finally:
        engine.dispose()
