"""Opt-in PostgreSQL 16 evidence using an isolated disposable database only."""
from __future__ import annotations

from decimal import Decimal
import os
from pathlib import Path
import subprocess
import sys

from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import sessionmaker

from app.db.base import load_all_models
from app.models.client import Client
from app.models.scenario_draft import ScenarioDraftDecision
from app.schemas.scenario_draft import DraftDecisionWrite, DraftReplace
from app.services import scenario_draft_service as service
from test_recovery_migration_postgresql import postgres_url

BACKEND = Path(__file__).resolve().parents[1]
APPLICATION_ROLE = "scenario_draft_test_app"


def test_postgresql_draft_migration_and_cas(postgres_url):
    # postgres_url fixture creates a fresh disposable PostgreSQL 16 instance.
    # Never read the caller's DATABASE_URL; only the fixture URL is used.
    load_all_models()
    engine = create_engine(postgres_url)
    try:
        with engine.begin() as connection:
            connection.execute(text(f"CREATE ROLE {APPLICATION_ROLE} NOLOGIN"))
        completed = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "e2f8a6c1d405"],
            cwd=BACKEND,
            env={**os.environ, "DATABASE_URL": postgres_url,
                 "CRTISBA_APPLICATION_DB_ROLE": APPLICATION_ROLE,
                 "PYTHONIOENCODING": "utf-8"},
            capture_output=True, text=True, encoding="utf-8", timeout=180,
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr
        inspector = inspect(engine)
        assert {"scenario_drafts", "scenario_draft_decisions", "scenario_draft_revisions"} <= set(inspector.get_table_names())
        amount_type = str(next(
            column["type"] for column in inspector.get_columns("scenario_draft_decisions")
            if column["name"] == "amount"
        )).upper()
        assert "NUMERIC(20, 2)" in amount_type

        with engine.connect() as connection:
            connection.execute(text(f"SET ROLE {APPLICATION_ROLE}"))
            for table in ("scenario_drafts", "scenario_draft_decisions", "scenario_draft_revisions"):
                assert connection.scalar(text(
                    "SELECT has_table_privilege(current_user, :tbl, 'SELECT')"
                ), {"tbl": table})
            assert not connection.scalar(text(
                "SELECT has_table_privilege(current_user, 'scenario_draft_revisions', 'UPDATE')"
            ))
            assert not connection.scalar(text(
                "SELECT has_table_privilege(current_user, 'scenario_draft_revisions', 'DELETE')"
            ))
            connection.rollback()
        factory = sessionmaker(bind=engine, autoflush=False)
        with factory.begin() as db:
            db.add(Client(client_id=1, display_name="Synthetic A", id_number="scenario-pg-a"))
            db.add(Client(client_id=2, display_name="Synthetic B", id_number="scenario-pg-b"))
        with factory.begin() as db:
            created = service.create(db, 1, "חלופה א", "test-actor")
        scenario_id = created["scenario_id"]
        decision = DraftDecisionWrite(
            source_product_id="synthetic-product",
            source_component_id="synthetic-component",
            component_code="תגמולי_עובד_עד_2000",
            amount=Decimal("100.25"),
            action="pension", effective_date="2026-10-24",
        )
        with factory.begin() as db:
            updated = service.replace(
                db, 1, scenario_id,
                DraftReplace(name="חלופה א", expected_version=1, decisions=[decision]),
                "test-actor",
            )
        assert updated["version"] == 2
        assert updated["decisions"][0]["amount"] == "100.25"
        with factory() as db:
            assert service.read(db, 1, scenario_id)["decisions"][0]["amount"] == "100.25"
            try:
                service.read(db, 2, scenario_id)
            except service.DraftError as exc:
                assert (exc.code, exc.status) == ("SCENARIO_NOT_FOUND", 404)
            else:
                raise AssertionError("foreign client accessed scenario")
            amount = db.scalar(select(ScenarioDraftDecision.amount).where(
                ScenarioDraftDecision.scenario_id == scenario_id,
            ))
            assert amount == Decimal("100.25")
        with factory() as db:
            try:
                service.replace(db, 1, scenario_id,
                    DraftReplace(name="stale", expected_version=1, decisions=[decision]), "test-actor")
            except service.DraftError as exc:
                assert exc.code == "SCENARIO_VERSION_CONFLICT"
            else:
                raise AssertionError("stale version accepted")
            db.rollback()
        # Two genuinely distinct database transactions contend on one version.
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        gate = Barrier(2)
        def contender(label):
            with factory() as db:
                existing = service.read(db, 1, scenario_id)
                assert existing["version"] == 2
                gate.wait(timeout=10)
                try:
                    result = service.replace(
                        db, 1, scenario_id,
                        DraftReplace(name=label, expected_version=2, decisions=[decision]),
                        label,
                    )
                    db.commit()
                    return ("ok", result["version"])
                except service.DraftError as exc:
                    db.rollback()
                    return (exc.code, None)
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(contender, "writer-1")
            second = pool.submit(contender, "writer-2")
            outcomes = [first.result(timeout=25), second.result(timeout=25)]
        assert sorted(outcomes) == [("SCENARIO_VERSION_CONFLICT", None), ("ok", 3)]
        with factory() as db:
            assert service.read(db, 1, scenario_id)["version"] == 3
            assert len(service.read(db, 1, scenario_id)["decisions"]) == 1
            assert db.scalar(text(
                "SELECT count(*) FROM scenario_draft_revisions WHERE scenario_id = :id"
            ), {"id": scenario_id}) == 3
        with factory() as db:
            assert service.read(db, 1, scenario_id)["version"] == 3
    finally:
        engine.dispose()
