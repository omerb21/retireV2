"""SC-05E: a documentary review is never an execution permission."""
from copy import deepcopy

from app.services.scenario_input_manifest_service import _fingerprint
from app.services.scenario_coefficient_professional_review_contract import validate_documentary_review


def review():
    record = {
        "schema_version": "SCENARIO_COEFFICIENT_REVIEW_V1",
        "client_id": 7, "scenario_id": "s", "scenario_version": 3,
        "decision_id": "d", "product_id": "p", "component_id": "c",
        "product_version": 2,
        "manifest_fingerprint": "a" * 64,
        "inventory_fingerprint": "b" * 64,
        "election_fingerprint": "c" * 64,
        "source_fingerprint": "d" * 64,
        "professional_actor_id": "professional-7",
        "reviewed_at": "2026-10-25T19:00:00+00:00",
        "review_reference": "review-1",
        "decision": "reviewed_for_candidate",
    }
    record["record_fingerprint"] = _fingerprint(record)
    expected = {k: record[k] for k in (
        "client_id", "scenario_id", "scenario_version", "decision_id",
        "product_id", "component_id", "product_version",
        "manifest_fingerprint", "inventory_fingerprint",
        "election_fingerprint", "source_fingerprint",
    )}
    return record, expected


def test_matched_documentary_review_remains_non_authoritative():
    record, expected = review()
    result = validate_documentary_review(record, expected)
    assert result["state"] == "DOCUMENTARY_REVIEW_MATCHED_NOT_AUTHORIZED"
    assert result["execution_allowed"] is False
    assert result["coefficient_candidate"] is None
    assert result["financial_result"] is None
    assert result["authority_state"] == "NOT_EVALUATED"


def test_fails_closed_when_scenario_version_changes():
    record, expected = review()
    expected["scenario_version"] += 1
    assert validate_documentary_review(record, expected)["blockers"] == ["REVIEW_PROVENANCE_STALE"]


def test_fails_closed_when_source_or_election_changes():
    for key in ("source_fingerprint", "election_fingerprint", "inventory_fingerprint",
                "manifest_fingerprint", "decision_id", "product_version"):
        record, expected = review()
        expected[key] = "e"*64 if key.endswith("fingerprint") else ("other" if key == "decision_id" else 4)
        assert validate_documentary_review(record, expected)["blockers"] == ["REVIEW_PROVENANCE_STALE"]


def test_fails_closed_when_record_is_tampered_or_untrusted_context():
    record, expected = review()
    bad = deepcopy(record)
    bad["decision"] = "rejected"
    assert validate_documentary_review(bad, expected)["blockers"] == ["REVIEW_INTEGRITY_INVALID"]
    assert validate_documentary_review(record, dict(record))["blockers"] == ["TRUSTED_CONTEXT_MISSING"]


def test_rejected_review_does_not_authorize():
    record, expected = review()
    record["decision"] = "rejected"
    record["record_fingerprint"] = _fingerprint({k: v for k, v in record.items() if k != "record_fingerprint"})
    result = validate_documentary_review(record, expected)
    assert result["review_decision"] == "rejected"
    assert result["execution_allowed"] is False
