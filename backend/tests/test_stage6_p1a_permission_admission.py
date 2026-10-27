"""Stage6-P1A rule admission tests. No financial calculation or DB writes."""
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.services import scenario_permission_preview_service as permissions


class StubReadSnapshot:
    new = ()
    dirty = ()
    deleted = ()
    no_autoflush = nullcontext()

    def get_bind(self):
        return SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))

    def in_transaction(self):
        return True

    def execute(self, statement):
        value = "repeatable read" if "isolation" in str(statement) else "on"
        return SimpleNamespace(scalar_one=lambda: value)


def sample_manifest(component_code, *, reviewed_digest=None, amount="100.00"):
    return {
        "scenario_version": 3,
        "decisions": [{
            "decision_id": "d1", "action": "pension",
            "amount": amount, "effective_date": "2026-10-27",
            "component_code": component_code,
            "ruleset_digest_at_review": reviewed_digest,
            "source": {
                "product_id": "p1", "product_version": 2,
                "component_id": "c1", "source_fingerprint": "a" * 64,
                "source_kind": "imported", "product_type": "קרן פנסיה",
            },
        }],
    }


def calculate(manifest, *, partition_state="STRUCTURALLY_CONSISTENT_NOT_ADMITTED"):
    with patch("app.services.scenario_input_manifest_service.build_inert_manifest", return_value=manifest), patch(
        "app.services.scenario_snapshot_candidate_service._partition_verified_manifest",
        return_value={"evidence_state": partition_state}
    ):
        return permissions.derive_pension_action_permission_admission(
            StubReadSnapshot(), client_id=1, scenario_id="s1", decision_id="d1"
        )


def test_allowed_component_is_deterministic():
    component = permissions.COMPONENT_CODES[1]  # standard-component-02: pension allowed
    one = calculate(sample_manifest(component))
    two = calculate(sample_manifest(component))
    assert one == two
    assert one["permission_status"] == "allowed"
    assert len(one["permission_admission_fingerprint"]) == 64


def test_missing_documentary_preview_digest_does_not_replace_current_rules():
    component = permissions.COMPONENT_CODES[1]
    result = calculate(sample_manifest(component, reviewed_digest=None))
    assert result["ruleset_digest"] == permissions.ruleset_digest()


def test_blocked_component_never_gets_admission():
    with pytest.raises(permissions.ScenarioPermissionError) as exc:
        calculate(sample_manifest(permissions.COMPONENT_CODES[0]))
    assert exc.value.code == "PENSION_PERMISSION_NOT_ALLOWED"


def test_changed_amount_changes_permission_fingerprint():
    component = permissions.COMPONENT_CODES[1]
    old = calculate(sample_manifest(component, amount="100.00"))
    new = calculate(sample_manifest(component, amount="101.00"))
    assert old["permission_admission_fingerprint"] != new["permission_admission_fingerprint"]


def test_stale_ruleset_is_rejected():
    with pytest.raises(permissions.ScenarioPermissionError) as exc:
        calculate(sample_manifest(permissions.COMPONENT_CODES[1], reviewed_digest="b" * 64))
    assert exc.value.code == "PENSION_PERMISSION_RULESET_STALE"


def test_unverified_manifest_partition_is_rejected():
    with pytest.raises(permissions.ScenarioPermissionError) as exc:
        calculate(sample_manifest(permissions.COMPONENT_CODES[1]), partition_state="BLOCKED")
    assert exc.value.code == "PENSION_PERMISSION_SOURCE_STALE"


def test_requires_postgres_readonly_repeatable_read():
    db = StubReadSnapshot()
    db.execute = lambda statement: SimpleNamespace(scalar_one=lambda: "off" if "read_only" in str(statement) else "repeatable read")
    with pytest.raises(permissions.ScenarioPermissionError) as exc:
        permissions.derive_pension_action_permission_admission(
            db, client_id=1, scenario_id="s1", decision_id="d1"
        )
    assert exc.value.code == "PENSION_PERMISSION_SNAPSHOT_REQUIRED"
