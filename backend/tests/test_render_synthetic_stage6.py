"""Synthetic-only canonical PTE smoke tests."""
from render_synthetic_stage6 import SyntheticInput, estimate

def test_one_million_divided_by_two_hundred():
    result = estimate(SyntheticInput(balance="1000000.00", divisor="200"))
    assert result["result"]["result_state"] == "RESULT_READY"
    assert result["result"]["monthly_estimate_gross_ils"] == "5000.00"

def test_two_million_divided_by_two_hundred():
    result = estimate(SyntheticInput(balance="2000000.00", divisor="200"))
    assert result["result"]["result_state"] == "RESULT_READY"
    assert result["result"]["monthly_estimate_gross_ils"] == "10000.00"

from fastapi import FastAPI
from fastapi.testclient import TestClient
from render_synthetic_stage6 import router


def test_http_endpoint_validates_amounts_and_never_accepts_nonpositive_values():
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client:
        valid = client.post("/demo/stage6/estimate", json={
            "balance": "1500000.00", "divisor": "300",
        })
        assert valid.status_code == 200
        assert valid.json()["result"]["monthly_estimate_gross_ils"] == "5000.00"
        for balance, divisor in (
            ("0.00", "200"), ("100.00", "0"),
            ("-5.00", "200"), ("100.00", "1.5"),
            ("100", "200"), ("999999999999999.00", "200"),
        ):
            response = client.post("/demo/stage6/estimate", json={
                "balance": balance, "divisor": divisor,
            })
            assert response.status_code == 422, (balance, divisor)


def test_public_synthetic_endpoint_is_pinned_to_synthetic_identity():
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client:
        response = client.post("/demo/stage6/estimate", json={
            "balance": "1000000.00", "divisor": "200", "client_id": 993,
        })
    assert response.status_code == 200
    assert response.json()["result"]["client_id"] == 1
    assert response.json()["result"]["scenario_id"] == "synthetic"
