from copy import deepcopy

from app.services import scenario_m09_input_inventory_service as subject
from app.services import scenario_input_manifest_service as owner
from app.services.scenario_snapshot_candidate_service import (
    _build_pair_in_snapshot,
    _partition_verified_manifest,
)
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


def test_decision_inventory_preserves_exact_review_identities():
    result = subject._m09_p1_extension(None, pair())
    decision = result["decisions"][0]
    assert set(decision) == {
        "decision_id", "product_id", "component_id", "component_code",
        "action", "effective_date", "amount_principal", "validation_state",
        "source_fingerprint_at_review", "product_version_at_review",
        "ruleset_digest_at_review", "permission_preview_id_at_review",
        "input_state", "monthly_income", "periodization",
    }
    assert decision["validation_state"] == "unverified"
    assert decision["ruleset_digest_at_review"] == "a" * 64
    assert decision["permission_preview_id_at_review"] == "b" * 64
    assert decision["monthly_income"] is None
    assert decision["periodization"] is None


def test_blocked_second_source_does_not_relabel_clean_source():
    evidence = pair()
    manifest = deepcopy(evidence["manifest"])
    second = deepcopy(manifest["decisions"][0])
    second["decision_id"] = "blocked-second"
    second["product_id"] = "p2"
    second["component_id"] = "c2"
    second["source"] = None
    second["source_fingerprint_at_review"] = None
    manifest["decisions"].append(second)
    identity = {key: manifest[key] for key in owner.MANIFEST_IDENTITY_FIELDS}
    manifest["manifest_fingerprint"] = owner._fingerprint(identity)
    evidence = {
        "manifest": manifest,
        "candidate": _partition_verified_manifest(manifest),
    }

    result = subject._m09_p1_extension(None, evidence)

    assert result["inventory_state"] == "BLOCKED"
    assert result["blocker_codes"] == ["SOURCE_MISSING", "SOURCE_MISSING:blocked-second"]
    assert [(row["decision_id"], row["input_state"]) for row in result["decisions"]] == [
        ("d", "STRUCTURAL_ONLY"),
        ("blocked-second", "BLOCKED"),
    ]
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


def test_review_identity_fields_are_preserved():
    p = pair()
    original = p["manifest"]["decisions"][0]
    result = subject._m09_p1_extension(None, p)
    current = result["decisions"][0]
    for key in ("validation_state", "ruleset_digest_at_review",
                "permission_preview_id_at_review"):
        assert current[key] == original[key]


def test_only_source_with_missing_evidence_is_blocked():
    from copy import deepcopy
    p = pair()
    missing = deepcopy(p["manifest"]["decisions"][0])
    missing["decision_id"] = "missing"
    missing["product_id"] = "other-product"
    missing["component_id"] = "other-component"
    missing["source"] = None
    p["manifest"]["decisions"].append(missing)
    p["manifest"]["manifest_fingerprint"] = owner._fingerprint({
        key: p["manifest"][key] for key in owner.MANIFEST_IDENTITY_FIELDS
    })
    result = subject._m09_p1_extension(None, p)
    assert result["inventory_state"] == "BLOCKED"
    by_id = {decision["decision_id"]: decision for decision in result["decisions"]}
    assert by_id["d"]["input_state"] == "STRUCTURAL_ONLY"
    assert by_id["missing"]["input_state"] == "BLOCKED"
    assert result["monthly_cashflow"] is None
