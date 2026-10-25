"""SC-05B verifies DB-derived inventory does not invent pension elections."""
from types import SimpleNamespace
from app.services import scenario_coefficient_input_inventory_service as subject
from app.services import scenario_snapshot_candidate_service as owner


def test_verified_draft_still_has_no_coefficient_authority(monkeypatch):
    pair = {
        "manifest": dict(client_id=7, scenario_id="s", scenario_version=2,
            manifest_fingerprint="a"*64,
            decisions=[dict(decision_id="d", action="pension", product_id="p",
                            component_id="c", source=dict(product_id="p", product_version=1))]),
        "candidate": dict(evidence_state="STRUCTURALLY_CONSISTENT_NOT_ADMITTED",
                          manifest_fingerprint="a"*64),
    }
    calls = []
    class DB:
        def scalar(self, statement):
            calls.append("profile")
            return SimpleNamespace(birth_date=None, gender=None)
        def scalars(self, statement):
            if "scenario_draft_pension_elections" in str(statement):
                calls.append("elections")
                return []
            calls.append("products")
            return [SimpleNamespace(product_id="p", product_type="קרן פנסיה",
                                    version=1, start_date=None)]
    def fake_owner(factory, *, client_id, scenario_id, _snapshot_extension):
        assert client_id == 7 and scenario_id == "s"
        return _snapshot_extension(DB(), pair)
    monkeypatch.setattr(subject, "build_manifest_candidate_snapshot", fake_owner)
    result = subject.build_coefficient_input_inventory(object(), client_id=7, scenario_id="s")
    assert calls == ["profile", "products", "elections"]
    assert result["inventory_state"] == "UNRESOLVED"
    entry = result["entries"][0]
    assert entry["state"] == "UNRESOLVED"
    assert "SCENARIO_PENSION_ELECTION_MISSING_OR_STALE" in entry["blockers"]
    assert "SCENARIO_COEFFICIENT_PERMISSION_NOT_EVALUATED" in entry["blockers"]
    assert result["execution_allowed"] is False
    assert result["financial_result"] is None
    assert result["planning_snapshot"] is None


def test_blocked_candidate_cannot_be_promoted(monkeypatch):
    pair = {
        "manifest": dict(client_id=7, scenario_id="s", scenario_version=2,
            manifest_fingerprint="a"*64,
            decisions=[dict(decision_id="d", action="pension", product_id="p",
                            component_id="c", source=None)]),
        "candidate": dict(evidence_state="BLOCKED", manifest_fingerprint="a"*64),
    }
    class DB:
        def scalar(self, statement):
            return None
        def scalars(self, statement):
            return []
    monkeypatch.setattr(subject, "build_manifest_candidate_snapshot",
        lambda factory, *, client_id, scenario_id, _snapshot_extension:
            _snapshot_extension(DB(), pair))
    result = subject.build_coefficient_input_inventory(object(), client_id=7, scenario_id="s")
    assert result["inventory_state"] == "BLOCKED"
    assert result["entries"][0]["state"] == "BLOCKED"
    assert result["entries"][0]["coefficient_candidate"] is None
