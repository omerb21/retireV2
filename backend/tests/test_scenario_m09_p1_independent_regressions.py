"""Independent M09-P1 regression cases to integrate after locally verified fixes.

Deliberately isolated in a new test module: does not touch the M09-P1
service or the test module already modified by Codex on an unpushed branch.
"""
from copy import deepcopy

from app.services import scenario_m09_input_inventory_service as subject
from app.services import scenario_input_manifest_service as manifest
from app.services.scenario_snapshot_candidate_service import _build_pair_in_snapshot
from tests.test_scenario_input_manifest import fixture


def verified_pair():
    db = fixture()
    db.decisions[0].source_fingerprint_at_review = manifest._source_evidence(
        db.product, db.component,
    )["source_fingerprint"]
    return _build_pair_in_snapshot(db, 7, "s", None)


def rehash(value):
    value["manifest_fingerprint"] = manifest._fingerprint({
        field: value[field] for field in manifest.MANIFEST_IDENTITY_FIELDS
    })
    return value


def test_stable_input_inventory_does_not_change_accepted_snapshot():
    pair = verified_pair()
    before = deepcopy(pair)
    first = subject._m09_p1_extension(None, pair)
    second = subject._m09_p1_extension(None, pair)
    assert pair == before
    assert first == second
    assert first["inventory_fingerprint"] == second["inventory_fingerprint"]
    assert first["financial_result"] is None
    assert first["monthly_cashflow"] is None
    assert first["execution_allowed"] is False


def test_change_in_decision_amount_invalidates_inventory_hash():
    pair = verified_pair()
    first = subject._m09_p1_extension(None, pair)
    altered = deepcopy(pair)
    altered["manifest"]["decisions"][0]["amount"] = "49.99"
    rehash(altered["manifest"])
    second = subject._m09_p1_extension(None, altered)
    assert first["inventory_fingerprint"] != second["inventory_fingerprint"]
    assert second["decisions"][0]["amount_principal"] == "49.99"
    assert second["monthly_cashflow"] is None


def test_change_of_scenario_version_changes_inventory_identity():
    pair = verified_pair()
    first = subject._m09_p1_extension(None, pair)
    altered = deepcopy(pair)
    altered["manifest"]["scenario_version"] += 1
    rehash(altered["manifest"])
    second = subject._m09_p1_extension(None, altered)
    assert first["inventory_fingerprint"] != second["inventory_fingerprint"]
    assert second["scenario_version"] == 2


def test_mixed_capital_and_pension_are_only_source_principal():
    pair = verified_pair()
    second = deepcopy(pair["manifest"]["decisions"][0])
    second["decision_id"] = "capital"
    second["action"] = "capital_asset"
    second["amount"] = "25.01"
    pair["manifest"]["decisions"].append(second)
    rehash(pair["manifest"])
    result = subject._m09_p1_extension(None, pair)
    assert result["source_allocations"][0]["allocation_by_action"] == {
        "pension": "50.00", "capital_asset": "25.01",
    }
    assert result["source_allocations"][0]["unallocated"] == "24.99"
    assert all(item["monthly_income"] is None for item in result["decisions"])
    assert result["financial_result"] is None


def test_aggregate_overallocation_blocks_instead_of_negative_available_balance():
    pair = verified_pair()
    second = deepcopy(pair["manifest"]["decisions"][0])
    second["decision_id"] = "over"
    second["amount"] = "50.01"
    pair["manifest"]["decisions"].append(second)
    rehash(pair["manifest"])
    result = subject._m09_p1_extension(None, pair)
    assert result["inventory_state"] == "BLOCKED"
    assert "SOURCE_OVERALLOCATED" in result["blocker_codes"]
    assert result["source_allocations"][0]["unallocated"] is None
    assert result["execution_allowed"] is False


def test_archived_draft_never_earns_input_readiness():
    pair = verified_pair()
    pair["manifest"]["scenario_status"] = "archived"
    rehash(pair["manifest"])
    result = subject._m09_p1_extension(None, pair)
    assert result["inventory_state"] == "BLOCKED"
    assert "SCENARIO_NOT_ACTIVE_DRAFT" in result["blocker_codes"]
    assert result["monthly_cashflow"] is None


def test_snapshot_candidate_blocker_is_not_hidden_by_clean_allocation():
    pair = verified_pair()
    pair["candidate"]["blockers"] = ["OWNER_BLOCKED"]
    result = subject._m09_p1_extension(None, pair)
    assert result["inventory_state"] == "BLOCKED"
    assert result["blocker_codes"] == ["OWNER_BLOCKED"]
    assert result["financial_result"] is None


def test_authority_fields_provenance_preserved_in_decisions():
    pair = verified_pair()
    source = pair["manifest"]["decisions"][0]
    result = subject._m09_p1_extension(None, pair)
    row = result["decisions"][0]
    for field in ("validation_state", "ruleset_digest_at_review",
                  "permission_preview_id_at_review"):
        assert row[field] == source[field]


def test_input_status_is_source_granular_with_global_block():
    pair = verified_pair()
    blocked = deepcopy(pair["manifest"]["decisions"][0])
    blocked["decision_id"] = "another"
    blocked["product_id"] = "p2"
    blocked["component_id"] = "c2"
    blocked["source"] = None
    pair["manifest"]["decisions"].append(blocked)
    rehash(pair["manifest"])
    result = subject._m09_p1_extension(None, pair)
    statuses = {row["decision_id"]: row["input_state"] for row in result["decisions"]}
    assert result["inventory_state"] == "BLOCKED"
    assert statuses["d"] == "STRUCTURAL_ONLY"
    assert statuses["another"] == "BLOCKED"
    assert result["execution_allowed"] is False
