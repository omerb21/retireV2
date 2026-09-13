"""Public application evidence, distinct from the private historical harness."""
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.db.session import get_db
from test_pkg013_m09_cashflow import api, REQUEST, income

ROOT = Path(__file__).resolve().parents[2]


def test_current_snapshot_and_ui_have_no_legacy_authority_or_execution():
    reader = (ROOT / "backend/app/services/professional_source_snapshot_service.py").read_text(encoding="utf-8")
    for term in ("PensionHolding", "pension_holding", "m02_", "m03_", "m04_", "m05_", "m06_", "RecurringIncome", "monthly_display_amount", "lock_client", "current_products"):
        assert term not in reader
    routes = {r.path: getattr(r, "methods", set()) for r in app.routes}
    assert all(methods == {"GET"} for path, methods in routes.items() if "/m09/" in path)
    assert not any("/m10/" in path for path in routes)
    for path in (ROOT / "backend/app").rglob("*.py"):
        assert "legacy_m09_m10_test_app" not in path.read_text(encoding="utf-8")
    for path in (ROOT / "frontend/src").rglob("*"):
        if path.suffix not in {".tsx", ".ts"} or ".test." in path.name:
            continue
        source = path.read_text(encoding="utf-8")
        for term in ("m09CashflowApi", "m10ComparisonApi", "M09CashflowScreen", "M10ComparisonScreen", "monthly-cashflow", "scenario-comparison"):
            assert term not in source, (path, term)
    for path in ("pages/M09CashflowScreen.tsx", "pages/M09ScenarioSubjects.tsx", "pages/M10ComparisonScreen.tsx",
                 "api/m09CashflowApi.ts", "api/m10ComparisonApi.ts"):
        assert not (ROOT / "frontend/src" / path).exists()


def test_real_public_archive_preserves_saved_results_without_live_recalculation(api, monkeypatch):
    historical, sessions = api
    engine = sessions.kw["bind"]
    with sessions() as db:
        db.add(income())
        db.commit()
    saved = historical.post("/api/clients/1/m09/runs", json=REQUEST)
    assert saved.status_code == 201, saved.text
    rid = saved.json()["run_id"]
    baseline = historical.post("/api/clients/1/m09/subjects/baseline").json()
    sid = baseline["scenario_subject_id"]
    saved_subject = historical.post(f"/api/clients/1/m09/subjects/{sid}/runs", json={
        "start_month": "2026-01", "end_month": "2026-02"})
    assert saved_subject.status_code == 201, saved_subject.text
    srid = saved_subject.json()["run_id"]
    from app.services import m09_cashflow_service, m09_scenario_subject_service, m10_comparison_service
    def forbidden(*args, **kwargs):
        raise AssertionError("archive attempted professional execution/currentness")
    for module, names in ((m09_cashflow_service, ("execute_run", "currentness", "m10_eligibility", "assess_inventory")),
                          (m09_scenario_subject_service, ("execute_subject_run", "subject_currentness", "subject_eligibility")),
                          (m10_comparison_service, ("compare_runs",))):
        for name in names:
            monkeypatch.setattr(module, name, forbidden)
    def session():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[get_db] = session
    try:
        with TestClient(app) as client:
            for path in (f"runs/{rid}", f"subjects/{sid}", f"subjects/{sid}/runs/{srid}",
                         "runs", "subjects", f"subjects/{sid}/runs"):
                response = client.get("/api/clients/1/m09/" + path)
                assert response.status_code == 200, response.text
                assert response.json()["authority"] == "archive_only"
                assert response.headers["X-Professional-Authority"] == "archive-only"
                foreign = client.get("/api/clients/2/m09/" + path)
                if path not in ("runs", "subjects"):
                    assert foreign.status_code == 404
            assert client.get(f"/api/clients/1/m09/runs/{rid}").json()["record"]["run_id"] == rid
            for path in ("m09/inventories", "m09/runs", "m09/subjects/baseline", "m09/subjects",
                         f"m09/subjects/{sid}/runs", "m10/compare"):
                assert client.post("/api/clients/1/" + path, json={}).status_code in (404, 405)
    finally:
        app.dependency_overrides.clear()
