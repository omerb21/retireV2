"""Synthetic isolated draft workflow acceptance tests."""
from decimal import Decimal
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.scenario_draft_routes import get_db
from app.db.base import Base, load_all_models
from app.main import create_app
from app.models.client import Client
from app.models.scenario_draft import ScenarioDraft, ScenarioDraftRevision
from app.security.config import AuthConfig

@pytest.fixture
def env(tmp_path):
    load_all_models()
    engine = create_engine(f"sqlite:///{tmp_path / 'draft.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False)
    with factory.begin() as db:
        db.add_all([
            Client(client_id=1, display_name="A", id_number="scenario-A"),
            Client(client_id=2, display_name="B", id_number="scenario-B"),
        ])
    def override():
        with factory() as db:
            yield db
    app = create_app(AuthConfig(production=False))
    app.dependency_overrides[get_db] = override
    try:
        yield TestClient(app), factory
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_create_edit_reload_copy_and_client_isolation(env):
    client, factory = env
    created = client.post("/api/clients/1/scenario-drafts", json={"name":"חלופה א"})
    assert created.status_code == 200, created.text
    scenario = created.json()
    assert scenario["version"] == 1 and scenario["decisions"] == []
    ident = scenario["scenario_id"]
    url = f"/api/clients/1/scenario-drafts/{ident}"
    payload = {"name":"חלופה א", "expected_version":1, "decisions":[{
        "source_product_id":"synthetic-fund", "source_component_id":"synthetic-row",
        "component_code":"תגמולי_עובד_עד_2000", "amount":"10.25",
        "action":"capital_asset", "effective_date":"2026-10-24"
    }]}
    result = client.put(url, json=payload)
    assert result.status_code == 200, result.text
    assert result.json()["version"] == 2
    assert result.json()["decisions"][0]["amount"] == "10.25"
    assert result.json()["decisions"][0]["validation_state"] == "unverified"
    assert client.get(url).json()["decisions"][0]["amount"] == "10.25"
    assert client.get(f"/api/clients/2/scenario-drafts/{ident}").status_code == 404
    assert client.get("/api/clients/2/scenario-drafts").json() == []
    assert client.put(url, json=payload).json()["code"] == "SCENARIO_VERSION_CONFLICT"
    copied = client.post(url + "/duplicate", json={"name":"חלופה ב"})
    assert copied.status_code == 200 and copied.json()["scenario_id"] != ident
    assert copied.json()["decisions"][0]["validation_state"] == "unverified"
    archived = client.post(url + "/archive", json={"expected_version":2})
    assert archived.status_code == 200 and archived.json()["status"] == "archived"
    assert client.put(url, json={**payload,"expected_version":3}).status_code == 409
    with factory() as db:
        revisions = db.scalars(select(ScenarioDraftRevision).where(ScenarioDraftRevision.scenario_id == ident)).all()
        assert [r.version for r in revisions] == [1,2,3]
        assert db.get(ScenarioDraft, ident).client_id == 1


def test_invalid_precision_rejected_without_draft_creation(env):
    client, _factory = env
    created = client.post("/api/clients/1/scenario-drafts", json={"name":"טיוטה"})
    ident = created.json()["scenario_id"]
    response = client.put(f"/api/clients/1/scenario-drafts/{ident}",json={
        "name":"טיוטה", "expected_version":1, "decisions":[{
            "source_product_id":"p","source_component_id":"c",
            "component_code":"תגמולי_עובד_עד_2000",
            "amount":"1.001","action":"pension","effective_date":"2026-10-24"
        }]
    })
    assert response.status_code == 422
    assert client.get(f"/api/clients/1/scenario-drafts/{ident}").json()["version"] == 1


def test_rename_preserves_stable_decision_id_and_revision(env):
    client, factory = env
    created = client.post("/api/clients/1/scenario-drafts", json={"name":"טיוטה"}).json()
    url = f"/api/clients/1/scenario-drafts/{created['scenario_id']}"
    row = {
        "source_product_id":"test-source", "source_component_id":"test-row",
        "component_code":"תגמולי_עובד_עד_2000", "amount":"123.45",
        "action":"pension", "effective_date":"2026-10-24",
    }
    first = client.put(url, json={"name":"טיוטה","expected_version":1,"decisions":[row]})
    assert first.status_code == 200, first.text
    decision_id = first.json()["decisions"][0]["decision_id"]
    renamed = client.put(url, json={
        "name":"טיוטה שנערכה","expected_version":2,
        "decisions":[{"decision_id":decision_id, **row}],
    })
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["name"] == "טיוטה שנערכה"
    assert renamed.json()["decisions"][0]["decision_id"] == decision_id
    forged = client.put(url, json={
        "name":"לא תקין","expected_version":3,
        "decisions":[{"decision_id":"foreign-decision-id", **row}],
    })
    assert (forged.status_code, forged.json()["code"]) == (422, "SCENARIO_DECISION_ID_MISMATCH")
    assert client.get(url).json()["version"] == 3
    with factory() as db:
        revisions = db.scalars(select(ScenarioDraftRevision).where(
            ScenarioDraftRevision.scenario_id == created["scenario_id"]
        )).all()
        assert len(revisions) == 3
