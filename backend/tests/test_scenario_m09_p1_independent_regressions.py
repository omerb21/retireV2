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


def test_changed_source_review_blocks_only_that_evidence():
    pair = verified_pair()
    pair["manifest"]["decisions"][0]["source_fingerprint_at_review"] = "0" * 64
    rehash(pair["manifest"])
    result = subject._m09_p1_extension(None, pair)
    assert result["inventory_state"] == "BLOCKED"
    assert result["decisions"][0]["input_state"] == "BLOCKED"
    assert result["source_allocations"][0]["unallocated"] is None
    assert result["financial_result"] is None


def test_readonly_inventory_never_exposes_historical_m09_run_identity():
    result = subject._m09_p1_extension(None, verified_pair())
    for prohibited in (
        "run_id", "monthly_results", "tax_net", "pension_net",
        "gross_inflow_total", "gross_outflow_total", "period_net",
        "comparison_result", "recommended_scenario",
    ):
        assert prohibited not in result
    assert result["periodization"] is None
    assert result["execution_allowed"] is False


def test_identity_fields_appear_only_as_input_evidence_not_authority():
    result = subject._m09_p1_extension(None, verified_pair())
    row = result["decisions"][0]
    assert row["amount_principal"] == "50.00"
    assert row["periodization"] is None
    assert row["monthly_income"] is None
    assert result["financial_result"] is None
    assert result["inventory_fingerprint"] != result["manifest_fingerprint"]


def test_two_source_same_decision_id_is_rejected_by_manifest_validator():
    pair = verified_pair()
    cloned = deepcopy(pair["manifest"]["decisions"][0])
    cloned["amount"] = "10.00"
    pair["manifest"]["decisions"].append(cloned)
    rehash(pair["manifest"])
    import pytest
    from app.services.scenario_input_manifest_service import ManifestValidationError
    with pytest.raises(ManifestValidationError, match="DECISION_CONTRACT_INVALID"):
        subject._m09_p1_extension(None, pair)


def test_missing_source_never_receives_invented_amount_or_monthly_stream():
    pair = verified_pair()
    pair["manifest"]["decisions"][0]["source"] = None
    rehash(pair["manifest"])
    result = subject._m09_p1_extension(None, pair)
    assert result["inventory_state"] == "BLOCKED"
    assert "SOURCE_MISSING" in result["blocker_codes"]
    assert result["source_allocations"][0]["balance"] is None
    assert result["source_allocations"][0]["unallocated"] is None
    assert result["decisions"][0]["monthly_income"] is None


def test_explicit_source_identity_remains_stable_across_other_source_failure():
    pair = verified_pair()
    first = subject._m09_p1_extension(None, pair)
    missing = deepcopy(pair["manifest"]["decisions"][0])
    missing["decision_id"] = "missing-id"
    missing["product_id"] = "other"
    missing["component_id"] = "other-component"
    missing["source"] = None
    pair["manifest"]["decisions"].append(missing)
    rehash(pair["manifest"])
    second = subject._m09_p1_extension(None, pair)
    assert second["inventory_state"] == "BLOCKED"
    assert first["decisions"][0]["source_fingerprint_at_review"] == second["decisions"][0]["source_fingerprint_at_review"]
    assert second["decisions"][0]["input_state"] == "STRUCTURAL_ONLY"
    assert second["decisions"][1]["input_state"] == "BLOCKED"


def test_revised_ruleset_fingerprint_changes_input_receipt():
    pair = verified_pair()
    baseline = subject._m09_p1_extension(None, pair)
    pair["manifest"]["decisions"][0]["ruleset_digest_at_review"] = "f" * 64
    rehash(pair["manifest"])
    updated = subject._m09_p1_extension(None, pair)
    assert baseline["inventory_fingerprint"] != updated["inventory_fingerprint"]
    assert updated["decisions"][0]["ruleset_digest_at_review"] == "f" * 64
    assert updated["monthly_cashflow"] is None


def test_revised_permission_preview_identity_changes_input_receipt():
    pair = verified_pair()
    baseline = subject._m09_p1_extension(None, pair)
    pair["manifest"]["decisions"][0]["permission_preview_id_at_review"] = "e" * 64
    rehash(pair["manifest"])
    updated = subject._m09_p1_extension(None, pair)
    assert baseline["inventory_fingerprint"] != updated["inventory_fingerprint"]
    assert updated["decisions"][0]["permission_preview_id_at_review"] == "e" * 64
    assert updated["financial_result"] is None


def test_m09_p1_does_not_use_business_pension_factor_or_tax_fallback():
    pair = verified_pair()
    result = subject._m09_p1_extension(None, pair)
    decision = result["decisions"][0]
    for forbidden in (
        "pension_factor", "monthly_pension_gross", "monthly_pension_net",
        "tax_amount", "capital_gains_tax", "annuity_start_month",
        "cpi_adjustment", "discount_rate", "social_security",
    ):
        assert forbidden not in decision
        assert forbidden not in result
    assert decision["periodization"] is None
    assert decision["monthly_income"] is None
