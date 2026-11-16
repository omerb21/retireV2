"""M11 real PostgreSQL 16 and Alembic-chain acceptance. CI-only synthetic data.

The GitHub Actions runner migrates its disposable localhost database from empty
before running these tests. This file must never target Railway or external DB.
"""
from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from urllib.parse import urlsplit

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import IntegrityError, DBAPIError
from sqlalchemy.orm import Session

from app.db.base import load_all_models
from app.models.client import Client
from app.models.scenario_draft import ScenarioDraft
from app.models.m11_preferred_scenario import M11PreferredScenarioRevision
from app.services.scenario_draft_service import DraftError
from app.services import m11_preferred_scenario_service as m11

DB_NAME = "retire_v2_scenario_test"
EXPECTED_HEAD = "b2d7e4c9f108"


def _engine():
    assert os.getenv("APP_ENV") == "test"
    url = os.environ["DATABASE_URL"]
    normalized = url.replace("postgresql+psycopg2://", "postgresql://", 1)
    parsed = urlsplit(normalized)
    assert parsed.scheme == "postgresql"
    assert parsed.hostname == "127.0.0.1" and parsed.port == 5432
    assert parsed.path == "/" + DB_NAME
    engine = create_engine(url, pool_pre_ping=True)
    with engine.connect() as con:
        assert con.scalar(text("SELECT current_database()")) == DB_NAME
        assert con.scalar(text("SHOW server_version")).startswith("16.")
        assert con.scalar(text("SELECT version_num FROM alembic_version")) == EXPECTED_HEAD
    return engine


@pytest.fixture(scope="module")
def engine():
    load_all_models()
    value = _engine()
    try:
        yield value
    finally:
        value.dispose()


@pytest.fixture(scope="module", autouse=True)
def synthetic_fixture(engine):
    with Session(engine) as session:
        assert session.scalar(select(Client.client_id).where(Client.client_id.in_([970101, 970202]))) is None
        session.add_all([
            Client(client_id=970101, display_name="M11 Synthetic A", id_number="M11PG-970101"),
            Client(client_id=970202, display_name="M11 Synthetic B", id_number="M11PG-970202"),
        ])
        session.flush()
        session.add_all([
            ScenarioDraft(scenario_id="m11-pg-a", client_id=970101, name="A", status="draft",
                          version=1, created_by="synthetic", updated_by="synthetic"),
            ScenarioDraft(scenario_id="m11-pg-a2", client_id=970101, name="A2", status="needs_revalidation",
                          version=3, created_by="synthetic", updated_by="synthetic"),
            ScenarioDraft(scenario_id="m11-pg-b", client_id=970202, name="B", status="draft",
                          version=1, created_by="synthetic", updated_by="synthetic"),
        ])
        session.commit()


def _save(session, scenario="m11-pg-a", version=1, revision=0, rationale=""):
    return m11.save(
        session, client_id=970101, scenario_id=scenario,
        expected_scenario_version=version,
        expected_selection_revision=revision, rationale=rationale, actor_id="synthetic-owner",
    )


def test_01_migration_schema_and_postgresql_16(engine):
    with engine.connect() as con:
        assert con.scalar(text("SELECT version_num FROM alembic_version")) == EXPECTED_HEAD
        assert con.scalar(text("SELECT COUNT(*) FROM pg_trigger WHERE tgname='trg_m11_selection_immutable'")) == 1
        assert con.scalar(text("""
            SELECT COUNT(*) FROM pg_constraint
            WHERE conname IN ('uq_m11_scenario_identity_client', 'uq_m11_client_revision')
        """)) == 2


def test_02_commit_and_reload_with_fresh_session(engine):
    with Session(engine, autoflush=False) as session:
        result = _save(session, rationale="Professional choice")
        assert result["revision"] == 1
        assert result["current"]["scenario_id"] == "m11-pg-a"
        assert result["current"]["rationale"] == "Professional choice"
        assert result["current"]["saved_at"] is not None
        assert result["current"]["calculation_references"] == []
        assert result["calculation_authorized"] is False
        assert result["report_authorized"] is False
        session.commit()
    with Session(engine, autoflush=False) as session:
        again = m11.read(session, 970101)
        assert again["current"]["scenario_id"] == "m11-pg-a"
        assert again["current"]["revision"] == 1
        assert again["current"]["rationale"] == "Professional choice"
        assert m11.read(session, 970202)["current"] is None


def test_03_change_and_history_survive_commit(engine):
    with Session(engine, autoflush=False) as session:
        result = _save(session, "m11-pg-a2", 3, 1, "Alternative rationale")
        assert result["revision"] == 2
        assert result["outdated"] is True
        session.commit()
    with Session(engine, autoflush=False) as session:
        history = m11.read(session, 970101)["history"]
        assert [(row["scenario_id"], row["revision"]) for row in history] == [
            ("m11-pg-a2", 2), ("m11-pg-a", 1)
        ]
        assert history[1]["rationale"] == "Professional choice"


def test_04_stale_cas_and_cross_client_blocking(engine):
    with Session(engine, autoflush=False) as session:
        for args, code in [
            (("m11-pg-a", 99, 2), "M11_SCENARIO_VERSION_CONFLICT"),
            (("m11-pg-a", 1, 1), "M11_SELECTION_VERSION_CONFLICT"),
            (("m11-pg-b", 1, 2), "M11_SCENARIO_NOT_ACTIVE"),
        ]:
            with pytest.raises(DraftError) as exc:
                _save(session, *args)
            assert exc.value.code == code
            session.rollback()
        assert m11.read(session, 970101)["revision"] == 2
        assert m11.read(session, 970202)["revision"] == 0


def test_05_database_rejects_foreign_client_scenario(engine):
    with Session(engine) as session:
        row = M11PreferredScenarioRevision(
            selection_id="m11-pg-forged", client_id=970202, scenario_id="m11-pg-a",
            scenario_version=1, revision=1, rationale="", calculation_references=[],
            actor_id="synthetic-owner",
        )
        session.add(row)
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()
    with Session(engine) as session:
        assert session.scalar(select(M11PreferredScenarioRevision).where(
            M11PreferredScenarioRevision.selection_id == "m11-pg-forged"
        )) is None


def test_06_immutable_update_and_delete(engine):
    with Session(engine) as session:
        for sql in (
            "UPDATE m11_preferred_scenario_revisions SET rationale='tampered' WHERE client_id=970101",
            "DELETE FROM m11_preferred_scenario_revisions WHERE client_id=970101",
        ):
            with pytest.raises(DBAPIError) as exc:
                session.execute(text(sql))
            assert "M11 selections are append-only" in str(exc.value)
            session.rollback()
    with Session(engine) as session:
        assert m11.read(session, 970101)["revision"] == 2


def test_07_two_concurrent_writes_have_one_winner(engine):
    gate = Barrier(2)
    def writer(label):
        with Session(engine, autoflush=False) as session:
            gate.wait(timeout=10)
            try:
                data = _save(session, "m11-pg-a", 1, 2, label)
                session.commit()
                return ("saved", data["revision"])
            except DraftError as exc:
                session.rollback()
                return ("blocked", exc.code)
    with ThreadPoolExecutor(max_workers=2) as pool:
        one = pool.submit(writer, "thread-one")
        two = pool.submit(writer, "thread-two")
        outcomes = [one.result(timeout=30), two.result(timeout=30)]
    assert sorted(x[0] for x in outcomes) == ["blocked", "saved"]
    assert ("saved", 3) in outcomes
    assert ("blocked", "M11_SELECTION_VERSION_CONFLICT") in outcomes
    with Session(engine) as session:
        rows = session.scalars(select(M11PreferredScenarioRevision).where(
            M11PreferredScenarioRevision.client_id == 970101
        )).all()
        assert sorted(row.revision for row in rows) == [1, 2, 3]


def test_08_failed_write_rolls_back_without_partial_state(engine):
    with Session(engine, autoflush=False) as session:
        # Current selection is rev 3. Attempt a duplicate revision, which the
        # PostgreSQL unique constraint must reject atomically.
        row = M11PreferredScenarioRevision(
            selection_id="m11-pg-duplicate-revision", client_id=970101,
            scenario_id="m11-pg-a", scenario_version=1, revision=3,
            rationale="must rollback", calculation_references=[],
            actor_id="synthetic-owner",
        )
        session.add(row)
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()
    with Session(engine) as session:
        assert m11.read(session, 970101)["revision"] == 3
        assert session.scalar(select(M11PreferredScenarioRevision).where(
            M11PreferredScenarioRevision.selection_id == "m11-pg-duplicate-revision"
        )) is None
