from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.db.session import get_db
from test_recovery_pension_products import engine
from test_canonical_component_conversion import seeded, request

ROOT = Path(__file__).resolve().parents[2]


def test_old_professional_routes_removed_archive_is_get_only():
    paths = {route.path: getattr(route, "methods", set()) for route in app.routes}
    archive = {path: methods for path, methods in paths.items() if "/m06" in path}
    assert archive == {
        "/api/clients/{client_id}/m06/subjects": {"GET"},
        "/api/clients/{client_id}/m06/subjects/{subject_id}": {"GET"},
        "/api/clients/{client_id}/m06/subjects/{subject_id}/history": {"GET"},
    }
    assert not any(any(prefix in path for prefix in ("/m02", "/m03", "/m04", "/m05")) for path in paths)
    from app.services import m06_conversion_service as legacy
    for name in ("list_candidates", "start_conversion", "resolve_conversion", "review_warnings", "correct_coefficient", "supersede_conversion"):
        assert not hasattr(legacy, name)
    for path in ("frontend/src/pages/M06ConversionScreen.tsx", "frontend/src/api/m06ConversionApi.ts"):
        assert not (ROOT / path).exists()
    source = (ROOT / "backend/app/services/canonical_component_conversion_service.py").read_text(encoding="utf-8")
    assert not any(name in source for name in ("PensionHolding", "m02_", "m03_", "m04_", "m05_", "m06_"))
    for path in (ROOT / "frontend/src").rglob("*.tsx"):
        if ".test." not in path.name:
            assert "localStorage.conversion_rules" not in path.read_text(encoding="utf-8")


def test_public_api_roundtrip_isolation_manual_assets_and_readonly_destination(engine):
    source = seeded(engine)
    def session():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[get_db] = session
    try:
        with TestClient(app) as client:
            root = "/api/clients/1/canonical-conversions"
            payload = request(source).model_dump(mode="json")
            assert client.post(root + "/preview", json=payload).status_code == 200
            assert client.post(root, json={**payload, "tax_treatment": "exempt"}).status_code == 422
            assert client.post("/api/clients/2/canonical-conversions", json=payload).status_code == 404
            result = client.post(root, json=payload)
            assert result.status_code == 200, result.text
            assert client.post(root, json=payload).json() == result.json()
            cid = result.json()["conversions"][0]["conversion_id"]
            aid = result.json()["conversions"][0]["destination_id"]
            assert len(client.get(root).json()) == 1
            assert client.get("/api/clients/2/canonical-conversions").json() == []
            assert client.put(f"/api/clients/1/capital-assets/{aid}", json={"known_value_amount": "1.00"}).status_code == 409
            manual = client.post("/api/clients/1/capital-assets", json={"asset_category": "other", "asset_description": "ידני", "known_value_amount": "123.45", "value_as_of_date": "2026-01-01"})
            assert manual.status_code == 200, manual.text
            mid = manual.json()["id"]
            updated = client.put(f"/api/clients/1/capital-assets/{mid}", json={"known_value_amount": "999999999999999999.99"})
            assert updated.status_code == 200, updated.text
            assert updated.json()["known_value_amount"] == "999999999999999999.99"
            assert client.put(f"/api/clients/1/capital-assets/{mid}", json={"known_value_amount": "0.001"}).status_code == 422
            undo = {"expected_conversion_version": 1, "expected_product_version": 3, "idempotency_key": "reverse", "reason": "בדיקה"}
            assert client.post(root + f"/{cid}/reverse", json={**undo, "amount": "1"}).status_code == 422
            assert client.post(root + f"/{cid}/reverse", json=undo).status_code == 200
            assert client.get(root).json()[0]["status"] == "reversed"
            current = client.get("/api/clients/1/capital-assets").json()
            assert aid not in {row["id"] for row in current}
    finally:
        app.dependency_overrides.clear()
