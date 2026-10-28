"""SC-03C database trust, strict candidate schema and cleanup evidence."""
from copy import deepcopy
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services import scenario_input_manifest_service as manifest
from app.services import scenario_snapshot_candidate_service as subject
from tests.test_scenario_input_manifest import SOURCE_GOLDEN, fixture


def verified_db():
    db = fixture()
    db.decisions[0].source_fingerprint_at_review = SOURCE_GOLDEN
    return db


def build(db=None, claim=None):
    return subject._build_pair_in_snapshot(db or verified_db(), 7, "s", claim)


def test_database_derived_partition_still_never_admits_financial_execution():
    pair = build()
    result = pair["candidate"]
    assert result["evidence_state"] == "STRUCTURALLY_CONSISTENT_NOT_ADMITTED"
    assert result["source_facts"][0]["client_id"] == 7
    assert result["source_facts"][0]["balance"] == "100.00"
    assert result["proposed_decisions"][0]["amount"] == "50.00"
    assert result["proposed_decisions"][0]["ruleset_digest_at_review"] == "a" * 64
    assert result["execution_allowed"] is False
    assert result["planning_snapshot"] is result["financial_result"] is None


def test_external_coherent_rehash_cannot_replace_database_evidence():
    claim = build()["manifest"]
    claim["decisions"][0]["amount"] = "90.00"
    claim["decisions"][0]["source"]["balance"] = "900.00"
    source = claim["decisions"][0]["source"]
    source["source_fingerprint"] = manifest._fingerprint({
        key: value for key, value in source.items() if key != "source_fingerprint"
    })
    claim["decisions"][0]["source_fingerprint_at_review"] = source["source_fingerprint"]
    identity = {key: claim[key] for key in manifest.MANIFEST_IDENTITY_FIELDS}
    claim["manifest_fingerprint"] = manifest._fingerprint(identity)
    result = build(claim=claim)["candidate"]
    assert result["blockers"] == ["MANIFEST_DATABASE_MISMATCH"]
    assert result["execution_allowed"] is False


def test_cross_client_source_swap_is_rejected_against_addressed_database_snapshot():
    foreign = fixture()
    foreign.scenario.client_id = 8
    foreign.product.client_id = 8
    foreign.decisions[0].source_fingerprint_at_review = manifest._fingerprint({
        **{
            "schema": "scenario-draft-source-v1", "client_id": 8,
            "product_id": "p", "product_version": 1, "product_type": "קרן פנסיה",
            "source_kind": "imported", "source_identity": "source-p",
            "component_product_id": "p", "component_id": "c",
            "component_code": "תגמולי_עובד_עד_2000", "balance": "100.00",
        }
    })
    foreign_claim = manifest.build_inert_manifest(foreign, 8, "s")
    result = build(claim=foreign_claim)["candidate"]
    assert result["blockers"] == ["MANIFEST_DATABASE_MISMATCH"]
    assert result["execution_allowed"] is False


@pytest.mark.parametrize(("field", "value"), [
    ("client_id", True),
    ("scenario_version", "1"),
])
def test_type_confusion_claims_fail_closed(field, value):
    claim = build()["manifest"]
    claim[field] = value
    identity = {key: claim[key] for key in manifest.MANIFEST_IDENTITY_FIELDS}
    claim["manifest_fingerprint"] = manifest._fingerprint(identity)
    assert build(claim=claim)["candidate"]["blockers"] == ["MANIFEST_DATABASE_MISMATCH"]


@pytest.mark.parametrize(("field", "value"), [
    ("effective_date", "2026-02-30"),
    ("amount", "5E+1"),
    ("ruleset_digest_at_review", "A" * 64),
    ("permission_preview_id_at_review", "short"),
])
def test_malformed_decision_claims_fail_closed(field, value):
    claim = build()["manifest"]
    claim["decisions"][0][field] = value
    identity = {key: claim[key] for key in manifest.MANIFEST_IDENTITY_FIELDS}
    claim["manifest_fingerprint"] = manifest._fingerprint(identity)
    result = build(claim=claim)["candidate"]
    assert result["blockers"] == ["MANIFEST_DATABASE_MISMATCH"]
    assert result["execution_allowed"] is False


def test_exact_cent_aggregate_overallocation_is_blocked_and_fingerprint_binds_state():
    db = verified_db()
    second = deepcopy(db.decisions[0])
    second.decision_id = "d2"
    second.amount = Decimal("50.01")
    db.decisions.append(second)
    result = build(db)["candidate"]
    assert "SOURCE_OVERALLOCATED:p:c" in result["blockers"]
    assert result["evidence_state"] == "BLOCKED"
    payload = {key: value for key, value in result.items() if key != "partition_fingerprint"}
    assert result["partition_fingerprint"] == manifest._fingerprint(payload)


def test_snapshot_owner_applies_options_before_work_and_invalidates_on_rollback_failure(monkeypatch):
    reached = []

    class Transaction:
        is_active = True
        def rollback(self):
            reached.append("rollback")
            raise RuntimeError("rollback failed")

    class Connection:
        dialect = SimpleNamespace(name="postgresql")
        def execution_options(self, **options):
            reached.append(("options", options))
            return self
        def begin(self):
            reached.append("begin")
            return Transaction()
        def in_transaction(self): return True
        def invalidate(self): reached.append("invalidate")
        def close(self): reached.append("connection_close")

    class Engine:
        def connect(self):
            reached.append("connect")
            return Connection()

    class FakeSession:
        def __init__(self, **_kwargs): reached.append("session")
        def close(self): reached.append("session_close")

    monkeypatch.setattr(subject, "_engine", lambda _factory: Engine())
    monkeypatch.setattr(subject, "Session", FakeSession)
    monkeypatch.setattr(
        subject, "_build_pair_in_snapshot",
        lambda *_args: reached.append("build") or {"manifest": {}, "candidate": {}},
    )
    with pytest.raises(subject.ScenarioSnapshotError, match="SCENARIO_SNAPSHOT_CLEANUP_FAILED"):
        subject.build_manifest_candidate_snapshot(
            object(), client_id=7, scenario_id="s",
        )
    assert reached[:5] == [
        "connect",
        ("options", {"isolation_level": "REPEATABLE READ", "postgresql_readonly": True}),
        "begin", "session", "build",
    ]
    assert reached[-4:] == ["rollback", "session_close", "invalidate", "connection_close"]


@pytest.mark.parametrize(("client_id", "scenario_id"), [
    (True, "s"), (0, "s"), (7, ""), (7, "s" * 65),
])
def test_snapshot_owner_rejects_type_confused_request_before_database_use(
    client_id, scenario_id,
):
    with pytest.raises(subject.ScenarioSnapshotError, match="SCENARIO_SNAPSHOT_REQUEST_INVALID"):
        subject.build_manifest_candidate_snapshot(
            object(), client_id=client_id, scenario_id=scenario_id,
        )


def test_snapshot_owner_rolls_back_and_closes_after_primary_failure(monkeypatch):
    reached = []

    class Transaction:
        is_active = True
        def rollback(self): reached.append("rollback")

    class Connection:
        dialect = SimpleNamespace(name="postgresql")
        def execution_options(self, **_options): return self
        def begin(self): return Transaction()
        def in_transaction(self): return True
        def close(self): reached.append("connection_close")

    class Engine:
        def connect(self): return Connection()

    class FakeSession:
        def __init__(self, **_kwargs): pass
        def close(self): reached.append("session_close")

    monkeypatch.setattr(subject, "_engine", lambda _factory: Engine())
    monkeypatch.setattr(subject, "Session", FakeSession)
    monkeypatch.setattr(
        subject, "_build_pair_in_snapshot",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("database failed")),
    )
    with pytest.raises(subject.ScenarioSnapshotError, match="SCENARIO_SNAPSHOT_DATABASE_UNAVAILABLE"):
        subject.build_manifest_candidate_snapshot(
            object(), client_id=7, scenario_id="s",
        )
    assert reached == ["rollback", "session_close", "connection_close"]


def test_owner_foundation_accepted_decision_cannot_mutate_source_records():
    db = verified_db()
    original_balance = db.component.balance
    original_amount = db.decisions[0].amount
    original_fingerprint = db.decisions[0].source_fingerprint_at_review
    first = build(db)
    db.calls = 0  # The existing FakeDb fixture models one read transaction per call.
    second = build(db)
    assert first == second
    assert db.component.balance == original_balance
    assert db.decisions[0].amount == original_amount
    assert db.decisions[0].source_fingerprint_at_review == original_fingerprint
    assert first["candidate"]["execution_allowed"] is False


def test_owner_foundation_exact_full_allocation_is_not_overallocation():
    db = verified_db()
    db.decisions[0].amount = Decimal("100.00")
    candidate = build(db)["candidate"]
    assert "SOURCE_OVERALLOCATED:p:c" not in candidate["blockers"]
    assert candidate["proposed_decisions"][0]["amount"] == "100.00"
    assert candidate["financial_result"] is None


def test_owner_foundation_same_source_two_decisions_at_limit_is_not_overallocated():
    db = verified_db()
    second = deepcopy(db.decisions[0])
    second.decision_id = "d2"
    db.decisions.append(second)
    candidate = build(db)["candidate"]
    assert "SOURCE_OVERALLOCATED:p:c" not in candidate["blockers"]
    assert len(candidate["proposed_decisions"]) == 2
    assert candidate["execution_allowed"] is False


def test_owner_foundation_one_cent_overallocation_fails_closed():
    db = verified_db()
    db.decisions[0].amount = Decimal("100.01")
    candidate = build(db)["candidate"]
    assert "SOURCE_OVERALLOCATED:p:c" in candidate["blockers"]
    assert candidate["evidence_state"] == "BLOCKED"
    assert candidate["financial_result"] is None


def test_owner_foundation_missing_professional_source_fails_closed():
    db = verified_db()
    db.product = None
    candidate = build(db)["candidate"]
    assert any(code.startswith("SOURCE_MISSING:") for code in candidate["blockers"])
    assert candidate["evidence_state"] == "BLOCKED"
    assert candidate["execution_allowed"] is False


def test_owner_foundation_changed_source_version_invalidates_prior_approval():
    db = verified_db()
    db.product.version += 1
    candidate = build(db)["candidate"]
    assert any(code.startswith("SOURCE_STALE:") for code in candidate["blockers"])
    assert candidate["execution_allowed"] is False
    assert candidate["financial_result"] is None


def test_owner_foundation_capital_action_is_inert_not_pension_income():
    db = verified_db()
    db.decisions[0].action = "capital_asset"
    candidate = build(db)["candidate"]
    assert candidate["proposed_decisions"][0]["action"] == "capital_asset"
    assert candidate["planning_snapshot"] is None
    assert candidate["financial_result"] is None
    assert candidate["execution_allowed"] is False


def test_owner_foundation_effective_date_change_changes_fingerprint_without_result():
    from datetime import date

    first = build()["candidate"]
    changed = verified_db()
    changed.decisions[0].effective_date = date(2026, 11, 1)
    second = build(changed)["candidate"]
    assert first["partition_fingerprint"] != second["partition_fingerprint"]
    assert first["financial_result"] is second["financial_result"] is None


def test_owner_foundation_source_balance_change_invalidates_approval():
    db = verified_db()
    db.component.balance = Decimal("101.00")
    candidate = build(db)["candidate"]
    assert any(code.startswith("SOURCE_STALE:") for code in candidate["blockers"])
    assert candidate["financial_result"] is None
    assert candidate["execution_allowed"] is False
