from app.services import scenario_m09_input_inventory_service as subject
from app.services import scenario_input_manifest_service as owner
from app.services.scenario_snapshot_candidate_service import _build_pair_in_snapshot
from tests.test_scenario_input_manifest import fixture


def pair():
    db = fixture()
    db.decisions[0].source_fingerprint_at_review = owner._source_evidence(
        db.product, db.component,
    )["source_fingerprint"]
    return _build_pair_in_snapshot(db, 7, "s", None)


def test_readonly_inventory():
    result = subject._m09_p1_extension(None, pair())
    assert result["inventory_state"] == "STRUCTURAL_ONLY"
    assert result["decisions"][0]["amount_principal"] == "50.00"
    assert result["source_allocations"][0]["unallocated"] == "50.00"
    assert result["monthly_cashflow"] is None
    assert result["execution_allowed"] is False


def test_candidate_blocker():
    p = pair()
    p["candidate"]["blockers"] = ["OWNER_BLOCKED"]
    result = subject._m09_p1_extension(None, p)
    assert result["inventory_state"] == "BLOCKED"
    assert result["blocker_codes"] == ["OWNER_BLOCKED"]


def test_inventory_digest():
    result = subject._m09_p1_extension(None, pair())
    original = {k: v for k, v in result.items() if k != "inventory_fingerprint"}
    assert result["inventory_fingerprint"] == owner._fingerprint(original)


def test_snapshot_owner_reuse(monkeypatch):
    seen = []
    def fake(factory, *, client_id, scenario_id, _snapshot_extension):
        seen.append((factory, client_id, scenario_id))
        return _snapshot_extension(None, pair())
    monkeypatch.setattr(subject, "build_manifest_candidate_snapshot", fake)
    token = object()
    result = subject.build_m09_current_input_inventory(token, client_id=7, scenario_id="s")
    assert seen == [(token, 7, "s")]
    assert result["monthly_cashflow"] is None
