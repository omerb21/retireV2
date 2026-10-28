"""Owner-approved, non-financial allocation reconciliation: bounded contracts."""
from copy import deepcopy
from decimal import Decimal

import pytest

from app.services import scenario_input_manifest_service as manifest_owner
from app.services.scenario_allocation_evidence import reconcile_inert_manifest_allocations
from tests.test_scenario_input_manifest import fixture


def source_manifest():
    db = fixture()
    source_fingerprint = manifest_owner._source_evidence(
        db.product, db.component,
    )["source_fingerprint"]
    db.decisions[0].source_fingerprint_at_review = source_fingerprint
    return manifest_owner.build_inert_manifest(db, 7, "s")


def rehash(value):
    value = deepcopy(value)
    identity = {k: value[k] for k in manifest_owner.MANIFEST_IDENTITY_FIELDS}
    value["manifest_fingerprint"] = manifest_owner._fingerprint(identity)
    return value


def row(value):
    return reconcile_inert_manifest_allocations(value)["sources"][0]


def test_half_allocated_component_has_explicit_remaining_evidence():
    result = reconcile_inert_manifest_allocations(source_manifest())
    assert result["schema_version"] == "SCENARIO_ALLOCATION_EVIDENCE_V1"
    assert (result["client_id"], result["scenario_id"], result["scenario_version"]) == (7, "s", 1)
    assert result["execution_allowed"] is False
    assert result["financial_result"] is None
    assert result["sources"] == [{
        "product_id": "p", "component_id": "c",
        "component_code": "תגמולי_עובד_עד_2000",
        "source_fingerprint": source_manifest()["decisions"][0]["source"]["source_fingerprint"],
        "balance": "100.00", "allocated": "50.00", "unallocated": "50.00",
        "decision_ids": ["d"],
        "status": "STRUCTURAL_ONLY", "blocker_codes": [],
    }]


@pytest.mark.parametrize(("amount", "expected_remaining"), [
    ("0.01", "99.99"),
    ("0.10", "99.90"),
    ("1.00", "99.00"),
    ("50.00", "50.00"),
    ("99.99", "0.01"),
    ("100.00", "0.00"),
])
def test_exact_cent_allocation_without_rounding(amount, expected_remaining):
    m = source_manifest()
    m["decisions"][0]["amount"] = amount
    result = row(rehash(m))
    assert result["allocated"] == amount
    assert result["unallocated"] == expected_remaining
    assert result["status"] == "STRUCTURAL_ONLY"


@pytest.mark.parametrize("amount", ["100.01", "101.00", "999999.99"])
def test_any_overallocation_blocks_without_negative_remainder(amount):
    m = source_manifest()
    m["decisions"][0]["amount"] = amount
    result = row(rehash(m))
    assert result["status"] == "BLOCKED"
    assert result["unallocated"] is None
    assert result["blocker_codes"] == ["SOURCE_OVERALLOCATED"]


@pytest.mark.parametrize("action", ["pension", "capital_asset"])
def test_allocation_reconciliation_never_assumes_an_income_for_action(action):
    m = source_manifest()
    m["decisions"][0]["action"] = action
    result = reconcile_inert_manifest_allocations(rehash(m))
    assert result["financial_result"] is None
    assert result["execution_allowed"] is False
    assert result["sources"][0]["unallocated"] == "50.00"


def test_two_decisions_for_same_component_use_same_balance_once():
    m = source_manifest()
    d = deepcopy(m["decisions"][0])
    d["decision_id"] = "second"
    d["amount"] = "25.00"
    m["decisions"].append(d)
    result = row(rehash(m))
    assert result["balance"] == "100.00"
    assert result["allocated"] == "75.00"
    assert result["unallocated"] == "25.00"
    assert result["decision_ids"] == ["d", "second"]


def test_two_decisions_overallocate_in_aggregate_even_when_individually_valid():
    m = source_manifest()
    d = deepcopy(m["decisions"][0])
    d["decision_id"] = "second"
    d["amount"] = "50.01"
    m["decisions"].append(d)
    result = row(rehash(m))
    assert result["allocated"] == "100.01"
    assert result["status"] == "BLOCKED"
    assert result["unallocated"] is None


def test_missing_source_blocks_and_does_not_fabricate_balance():
    m = source_manifest()
    m["decisions"][0]["source"] = None
    result = row(rehash(m))
    assert result["balance"] is None
    assert result["unallocated"] is None
    assert result["blocker_codes"] == ["SOURCE_MISSING"]


@pytest.mark.parametrize("field", [
    "product_version_at_review", "source_fingerprint_at_review", "validation_state",
])
def test_stale_review_blocks_remainder_as_current_fact(field):
    m = source_manifest()
    m["decisions"][0][field] = {
        "product_version_at_review": 2,
        "source_fingerprint_at_review": "f" * 64,
        "validation_state": "needs_revalidation",
    }[field]
    result = row(rehash(m))
    assert result["status"] == "BLOCKED"
    assert result["unallocated"] is None
    assert result["blocker_codes"] == ["SOURCE_STALE"]


def test_multiple_distinct_sources_do_not_cross_allocate():
    m = source_manifest()
    d = deepcopy(m["decisions"][0])
    d["decision_id"] = "second"
    d["product_id"] = "p2"
    d["component_id"] = "c2"
    d["source"]["product_id"] = "p2"
    d["source"]["component_product_id"] = "p2"
    d["source"]["component_id"] = "c2"
    d["source"]["balance"] = "200.00"
    source = d["source"]
    source["source_fingerprint"] = manifest_owner._fingerprint({
        key: value for key, value in source.items() if key != "source_fingerprint"
    })
    d["source_fingerprint_at_review"] = source["source_fingerprint"]
    m["decisions"].append(d)
    result = reconcile_inert_manifest_allocations(rehash(m))
    assert [(r["product_id"], r["balance"], r["unallocated"]) for r in result["sources"]] == [
        ("p", "100.00", "50.00"), ("p2", "200.00", "150.00"),
    ]


def test_conflicting_facts_for_same_source_block_remainder():
    m = source_manifest()
    d = deepcopy(m["decisions"][0])
    d["decision_id"] = "second"
    d["source"]["balance"] = "101.00"
    source = d["source"]
    source["source_fingerprint"] = manifest_owner._fingerprint({
        key: value for key, value in source.items() if key != "source_fingerprint"
    })
    d["source_fingerprint_at_review"] = source["source_fingerprint"]
    m["decisions"].append(d)
    result = row(rehash(m))
    assert result["status"] == "BLOCKED"
    assert "SOURCE_CONFLICT" in result["blocker_codes"]
    assert result["unallocated"] is None


def test_empty_scenario_is_not_financial_admission():
    m = source_manifest()
    m["decisions"] = []
    result = reconcile_inert_manifest_allocations(rehash(m))
    assert result["sources"] == []
    assert result["execution_allowed"] is False


def test_noncanonical_amount_rejected_even_with_coherent_rehash():
    m = source_manifest()
    m["decisions"][0]["amount"] = "5E+1"
    with pytest.raises(manifest_owner.ManifestValidationError):
        reconcile_inert_manifest_allocations(rehash(m))


def test_spoofed_manifest_digest_rejected():
    m = source_manifest()
    m["decisions"][0]["amount"] = "80.00"
    with pytest.raises(manifest_owner.ManifestValidationError):
        reconcile_inert_manifest_allocations(m)


def test_evidence_is_detached_and_does_not_mutate_manifest():
    m = source_manifest()
    snapshot = deepcopy(m)
    result = reconcile_inert_manifest_allocations(m)
    result["sources"][0]["decision_ids"].append("forged")
    assert m == snapshot
    assert "forged" not in row(m)["decision_ids"]


@pytest.mark.parametrize("status", ["archived", "needs_revalidation"])
def test_nonactive_scenario_does_not_expose_remainder_as_current(status):
    m = source_manifest()
    m["scenario_status"] = status
    result = row(rehash(m))
    assert result["status"] == "BLOCKED"
    assert result["unallocated"] is None
    assert result["blocker_codes"] == ["SCENARIO_NOT_ACTIVE_DRAFT"]


def test_status_change_changes_provenance_fingerprint():
    m = source_manifest()
    active = reconcile_inert_manifest_allocations(m)
    m["scenario_status"] = "archived"
    archived = reconcile_inert_manifest_allocations(rehash(m))
    assert active["manifest_fingerprint"] != archived["manifest_fingerprint"]
    assert archived["execution_allowed"] is False


def test_new_scenario_version_produces_distinct_evidence_identity():
    m = source_manifest()
    first = reconcile_inert_manifest_allocations(m)
    m["scenario_version"] = 2
    second = reconcile_inert_manifest_allocations(rehash(m))
    assert first["manifest_fingerprint"] != second["manifest_fingerprint"]
    assert second["scenario_version"] == 2
    assert second["financial_result"] is None
