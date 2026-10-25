"""SC-03B compatibility matrix must never admit financial execution."""
from app.services.scenario_engine_compatibility_service import assess_engine_compatibility


def sample():
    return {
        "schema_version": "SCENARIO_INERT_MANIFEST_V1", "scenario_id": "s",
        "scenario_version": 3, "scenario_status": "draft",
        "manifest_fingerprint": "a" * 64, "execution_allowed": False,
        "planning_snapshot": None, "financial_result": None,
        "authority_state": "NOT_EVALUATED",
        "decisions": [{"decision_id": "d", "source": {"product_id": "p"}}],
    }


def test_three_engines_explicitly_blocked():
    result = assess_engine_compatibility(sample())
    assert result["execution_allowed"] is False
    assert set(result["engines"]) == {"pension_target_date", "capital_projection", "monthly_income_gap"}
    for engine in result["engines"].values():
        assert engine["execution_allowed"] is False
        assert engine["result"] is None
        assert engine["missing_verified_contract_fields"]
        assert "PERMISSION_NOT_ADMITTED" in engine["blockers"]


def test_forged_input_fields_never_grant_execution():
    forged = sample()
    forged.update(scenario_planning_snapshot={"fake": "ready"},
                  permission_admitted=True, professional_eligibility=True, tax_admitted=True)
    assert all(not e["execution_allowed"] for e in assess_engine_compatibility(forged)["engines"].values())


def test_missing_source_and_archived_draft_report_specific_blockers():
    payload = sample()
    payload["scenario_status"] = "archived"
    payload["decisions"][0]["source"] = None
    result = assess_engine_compatibility(payload)
    assert "SCENARIO_STATUS_NOT_DRAFT" in result["blockers"]
    assert "SCENARIO_SOURCE_EVIDENCE_INCOMPLETE" in result["blockers"]


def test_invalid_manifest_fails_closed():
    invalid = assess_engine_compatibility({"schema_version": "other"})
    assert invalid["engines"] == {}
    assert invalid["execution_allowed"] is False
