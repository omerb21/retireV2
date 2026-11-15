"""M11 client isolation, concurrent revision, durable selection and no financial authority."""
from __future__ import annotations
import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from app.db.base import Base, load_all_models
from app.models.client import Client
from app.models.scenario_draft import ScenarioDraft
from app.models.m11_preferred_scenario import M11PreferredScenarioRevision
from app.services.scenario_draft_service import DraftError
from app.services import m11_preferred_scenario_service as selection

@pytest.fixture
def db():
    load_all_models()
    engine = create_engine("sqlite+pysqlite:///:memory:")
    @event.listens_for(engine, "connect")
    def enable_foreign_keys(conn, record):
        conn.execute("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(engine, tables=[
        Client.__table__, ScenarioDraft.__table__, M11PreferredScenarioRevision.__table__,
    ])
    with Session(engine, autoflush=False) as session:
        session.add_all([
            Client(client_id=101, display_name="Synthetic A", id_number="M11-A"),
            Client(client_id=202, display_name="Synthetic B", id_number="M11-B"),
            ScenarioDraft(scenario_id="a1", client_id=101, name="A1", status="draft", version=2,
                          created_by="owner", updated_by="owner"),
            ScenarioDraft(scenario_id="a2", client_id=101, name="A2", status="needs_revalidation", version=3,
                          created_by="owner", updated_by="owner"),
            ScenarioDraft(scenario_id="b1", client_id=202, name="B1", status="draft", version=1,
                          created_by="owner", updated_by="owner"),
        ])
        session.commit()
        yield session
    engine.dispose()

def write(db, client=101, scenario="a1", version=2, revision=0, rationale=""):
    return selection.save(db, client_id=client, scenario_id=scenario,
                          expected_scenario_version=version,
                          expected_selection_revision=revision,
                          rationale=rationale, actor_id="owner")

def test_save_reload_and_change_history(db):
    a = write(db, rationale="Initial professional reason")
    assert a["revision"] == 1
    assert a["current"]["scenario_id"] == "a1"
    assert a["current"]["scenario_version"] == 2
    assert a["current"]["rationale"] == "Initial professional reason"
    assert a["current"]["saved_at"]
    assert a["current"]["calculation_references"] == []
    assert a["current"]["professional_approval"] is False
    assert a["calculation_authorized"] is False
    assert a["report_authorized"] is False
    db.commit()
    db.expire_all()
    assert selection.read(db, 101)["current"]["scenario_id"] == "a1"
    b = write(db, scenario="a2", version=3, revision=1)
    assert b["revision"] == 2
    assert [h["scenario_id"] for h in b["history"]] == ["a2", "a1"]
    assert b["current"]["rationale"] == ""
    assert b["outdated"] is True   # needs_revalidation remains visibly unverified
    assert db.scalar(select(M11PreferredScenarioRevision).where(
        M11PreferredScenarioRevision.client_id == 101,
        M11PreferredScenarioRevision.revision == 1
    )).rationale == "Initial professional reason"

def test_stale_scenario_version_no_write(db):
    with pytest.raises(DraftError, match="M11_SCENARIO_VERSION_CONFLICT"):
        write(db, version=1)
    assert selection.read(db, 101)["history"] == []

def test_stale_selection_revision_no_overwrite(db):
    write(db)
    db.commit()
    with pytest.raises(DraftError, match="M11_SELECTION_VERSION_CONFLICT"):
        write(db, scenario="a2", version=3, revision=0)
    assert selection.read(db, 101)["revision"] == 1

def test_foreign_client_scenario_blocked_and_isolated(db):
    with pytest.raises(DraftError, match="M11_SCENARIO_NOT_ACTIVE"):
        write(db, client=202, scenario="a1")
    assert selection.read(db, 202)["history"] == []
    write(db)
    db.commit()
    assert selection.read(db, 202)["history"] == []

def test_archived_selection_blocked(db):
    row = db.get(ScenarioDraft, "a1")
    row.status = "archived"
    db.commit()
    with pytest.raises(DraftError, match="M11_SCENARIO_NOT_ACTIVE"):
        write(db)
    assert selection.read(db, 101)["history"] == []

def test_saved_choice_marked_outdated_when_scenario_changes(db):
    write(db)
    db.commit()
    row = db.get(ScenarioDraft, "a1")
    row.version = 3
    db.commit()
    result = selection.read(db, 101)
    assert result["outdated"] is True
    assert result["current"]["scenario_version"] == 2

def test_invalid_actor_and_rationale_are_rejected(db):
    with pytest.raises(DraftError, match="M11_SELECTION_INVALID"):
        selection.save(db, client_id=101, scenario_id="a1",
            expected_scenario_version=2, expected_selection_revision=0,
            rationale="x" * 5001, actor_id="owner")
    with pytest.raises(DraftError, match="M11_SELECTION_INVALID"):
        selection.save(db, client_id=101, scenario_id="a1",
            expected_scenario_version=2, expected_selection_revision=0,
            rationale="", actor_id="")
    assert selection.read(db, 101)["history"] == []
