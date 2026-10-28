"""Real HTTP + disposable PostgreSQL contract for the Render synthetic Stage 6 workflow."""
import os
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from render_synthetic_workflow import initialize, router

pytestmark = pytest.mark.skipif(
    not os.getenv("SYNTHETIC_DEMO_DATABASE_URL"),
    reason="requires explicitly isolated Render-local PostgreSQL",
)

def test_postgresql_http_workflow_cas_and_canonical_estimate():
    initialize()
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    created = client.post("/demo/stage6/workflow/start", json={"balance": "1000000.00"})
    assert created.status_code == 200
    sid = created.json()["scenario_id"]
    base = f"/demo/stage6/workflow/{sid}"
    assert created.json()["version"] == 1
    assert client.get(base + "/estimate").status_code == 409
    invalid = client.put(base + "/election", json={
        "expected_version": 1, "pension_start_date": "2027-09-30",
        "survivor_option": "not-supported",
    })
    assert invalid.status_code == 422
    elected = client.put(base + "/election", json={
        "expected_version": 1, "pension_start_date": "2027-09-30",
        "survivor_option": "synthetic-standard",
    })
    assert elected.status_code == 200
    assert elected.json()["version"] == 2
    assert client.put(base + "/election", json={
        "expected_version": 1, "pension_start_date": "2027-09-30",
        "survivor_option": "synthetic-standard",
    }).status_code == 409
    assert client.post(base + "/factor", json={
        "expected_version": 2, "divisor": "200", "acknowledgement": False,
    }).status_code == 422
    recorded = client.post(base + "/factor", json={
        "expected_version": 2, "divisor": "200", "acknowledgement": True,
    })
    assert recorded.status_code == 200
    assert recorded.json()["version"] == 3
    assert recorded.json()["is_professional_admission"] is False
    assert client.post(base + "/factor", json={
        "expected_version": 2, "divisor": "201", "acknowledgement": True,
    }).status_code == 409
    final = client.get(base + "/estimate")
    assert final.status_code == 200
    outcome = final.json()
    assert outcome["synthetic_only"] is True
    assert outcome["calculation"]["result"]["result_state"] == "RESULT_READY"
    assert outcome["calculation"]["result"]["monthly_estimate_gross_ils"] == "5000.00"
    assert client.get("/demo/stage6/workflow/not-a-uuid/estimate").status_code == 404


def test_synthetic_workflow_rejects_external_client_identity():
    initialize()
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    assert client.post("/demo/stage6/workflow/start", json={
        "balance": "1000000.00", "client_id": 172,
    }).status_code == 422
