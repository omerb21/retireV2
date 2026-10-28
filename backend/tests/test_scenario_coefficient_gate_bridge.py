"""SC-05D bridge must never call coefficient lookup or produce financial authority."""
from app.services import scenario_coefficient_gate_bridge_service as bridge
from app.services import annuity_coefficient_service as coefficient


def test_current_election_requires_professional_authority(monkeypatch):
    monkeypatch.setattr(coefficient, "coefficient", lambda *a, **k:
                        (_ for _ in ()).throw(AssertionError("coefficient lookup forbidden")))
    def inventory(*args, **kwargs):
        return dict(client_id=7, scenario_id="s", scenario_version=3,
                    manifest_fingerprint="a"*64, inventory_fingerprint="b"*64,
                    inventory_state="UNRESOLVED", entries=[
                        dict(decision_id="d", product_id="p", component_id="c",
                             state="UNRESOLVED", election_state="CURRENT_DRAFT_NOT_ADMITTED",
                             blockers=["SCENARIO_COEFFICIENT_PERMISSION_NOT_EVALUATED"])])
    monkeypatch.setattr(bridge, "build_coefficient_input_inventory", inventory)
    result = bridge.build_coefficient_gate_bridge(object(), client_id=7, scenario_id="s")
    assert result["entries"][0]["handoff_state"] == "PROFESSIONAL_AUTHORITY_REQUIRED"
    assert result["entries"][0]["coefficient_candidate"] is None
    assert result["execution_allowed"] is False
    assert result["financial_result"] is None
    assert result["planning_snapshot"] is None


def test_missing_or_stale_election_never_handoffs(monkeypatch):
    monkeypatch.setattr(bridge, "build_coefficient_input_inventory", lambda *a, **kw:
        dict(client_id=7, scenario_id="s", scenario_version=4,
             manifest_fingerprint="a"*64, inventory_fingerprint="b"*64,
             inventory_state="BLOCKED", entries=[
                dict(decision_id="d", product_id="p", component_id="c",
                     state="BLOCKED", election_state="MISSING_OR_STALE",
                     blockers=["SCENARIO_PENSION_ELECTION_MISSING_OR_STALE"])]))
    result = bridge.build_coefficient_gate_bridge(object(), client_id=7, scenario_id="s")
    assert result["bridge_state"] == "BLOCKED"
    assert result["entries"][0]["handoff_state"] == "INPUTS_UNRESOLVED"
    assert result["authority_state"] == "NOT_EVALUATED"
