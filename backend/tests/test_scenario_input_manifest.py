"""SC-03A manifest identity, source evidence and fixed-golden tests."""
from copy import deepcopy
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services import scenario_input_manifest_service as manifest
from app.services.scenario_draft_service import DraftError


HASH_A = "a" * 64
HASH_B = "b" * 64
MANIFEST_GOLDEN = "4a7039c15645264778621393027265f5a6a04a036a1b8f1ade4e0c87aa34fb47"
SOURCE_GOLDEN = "e70422b7467e68a9f5624f1e3d00acd9cacc865e7ca79772e10243d4bcb90928"


class FakeDb:
    def __init__(self, scenario, decisions, product=None, component=None):
        self.scenario, self.decisions = scenario, decisions
        self.product, self.component = product, component
        self.calls = 0

    def scalar(self, _statement):
        self.calls += 1
        if self.calls == 1:
            return self.scenario
        return self.product if self.calls % 2 == 0 else self.component

    def scalars(self, _statement):
        return SimpleNamespace(all=lambda: self.decisions)


def fixture():
    scenario = SimpleNamespace(scenario_id="s", client_id=7, version=1, status="draft")
    row = SimpleNamespace(
        decision_id="d", source_product_id="p", source_component_id="c",
        component_code="תגמולי_עובד_עד_2000", amount=Decimal("50.00"),
        action="pension", effective_date=date(2026, 10, 25),
        validation_state="unverified", product_version_at_review=1,
        source_fingerprint_at_review=HASH_A,
        ruleset_digest_at_review=HASH_A,
        permission_preview_id_at_review=HASH_B,
    )
    product = SimpleNamespace(
        client_id=7, product_id="p", version=1, product_type="קרן פנסיה",
        source_kind="imported", source_identity="source-p",
    )
    component = SimpleNamespace(
        product_id="p", component_id="c", component_code="תגמולי_עובד_עד_2000",
        balance=Decimal("100.00"),
    )
    return FakeDb(scenario, [row], product, component)


def test_fixed_manifest_and_source_goldens_include_review_identities():
    result = manifest.build_inert_manifest(fixture(), 7, "s")
    assert result["manifest_fingerprint"] == MANIFEST_GOLDEN
    decision = result["decisions"][0]
    assert decision["source"]["source_fingerprint"] == SOURCE_GOLDEN
    assert decision["source"]["client_id"] == 7
    assert decision["ruleset_digest_at_review"] == HASH_A
    assert decision["permission_preview_id_at_review"] == HASH_B
    assert result["execution_allowed"] is False
    assert result["planning_snapshot"] is result["financial_result"] is None


@pytest.mark.parametrize("mutation", [
    "scenario_version", "amount", "effective_date", "ruleset_digest",
    "permission_preview_id", "product_version", "source_balance",
])
def test_each_material_field_changes_manifest_fingerprint_independently(mutation):
    baseline = manifest.build_inert_manifest(fixture(), 7, "s")
    changed = fixture()
    if mutation == "scenario_version":
        changed.scenario.version = 2
    elif mutation == "amount":
        changed.decisions[0].amount = Decimal("50.01")
    elif mutation == "effective_date":
        changed.decisions[0].effective_date = date(2026, 10, 26)
    elif mutation == "ruleset_digest":
        changed.decisions[0].ruleset_digest_at_review = "c" * 64
    elif mutation == "permission_preview_id":
        changed.decisions[0].permission_preview_id_at_review = "d" * 64
    elif mutation == "product_version":
        changed.product.version = 2
    else:
        changed.component.balance = Decimal("100.01")
    result = manifest.build_inert_manifest(changed, 7, "s")
    assert result["manifest_fingerprint"] != baseline["manifest_fingerprint"]


def test_source_digest_is_recomputable_but_not_permission_preview_identity():
    result = manifest.build_inert_manifest(fixture(), 7, "s")
    source = result["decisions"][0]["source"]
    preimage = {key: value for key, value in source.items() if key != "source_fingerprint"}
    assert manifest._fingerprint(preimage) == source["source_fingerprint"]
    assert source["schema"] == "scenario-draft-source-v1"
    assert "ruleset_digest" not in source and "permission_preview_id" not in source


@pytest.mark.parametrize("mutation", [
    "client_id", "product_id", "product_version", "product_type", "source_kind",
    "source_identity", "component_id", "component_code", "balance",
])
def test_each_source_preimage_field_is_bound_independently(mutation):
    baseline = manifest.build_inert_manifest(fixture(), 7, "s")["decisions"][0]["source"]
    changed = fixture()
    if mutation == "client_id":
        changed.product.client_id = 8
    elif mutation == "product_id":
        changed.product.product_id = changed.component.product_id = "p2"
    elif mutation == "product_version":
        changed.product.version = 2
    elif mutation == "product_type":
        changed.product.product_type = "קופת גמל"
    elif mutation == "source_kind":
        changed.product.source_kind = "manual"
    elif mutation == "source_identity":
        changed.product.source_identity = "source-p2"
    elif mutation == "component_id":
        changed.component.component_id = "c2"
    elif mutation == "component_code":
        changed.component.component_code = "תגמולי_עובד_אחרי_2000"
    else:
        changed.component.balance = Decimal("100.01")
    source = manifest._source_evidence(changed.product, changed.component)
    assert source["source_fingerprint"] != baseline["source_fingerprint"]


def test_strict_validator_rejects_coherent_but_malformed_source_evidence():
    result = manifest.build_inert_manifest(fixture(), 7, "s")
    malformed = deepcopy(result)
    malformed["decisions"][0]["source"]["balance"] = "1E+2"
    source = malformed["decisions"][0]["source"]
    source["source_fingerprint"] = manifest._fingerprint({
        key: value for key, value in source.items() if key != "source_fingerprint"
    })
    identity = {key: malformed[key] for key in manifest.MANIFEST_IDENTITY_FIELDS}
    malformed["manifest_fingerprint"] = manifest._fingerprint(identity)
    with pytest.raises(manifest.ManifestValidationError, match="SOURCE_EVIDENCE_INVALID"):
        manifest.validate_inert_manifest(malformed)


def test_missing_source_is_explicit_and_not_filled_in():
    db = fixture()
    db.product = None
    result = manifest.build_inert_manifest(db, 7, "s")
    assert result["decisions"][0]["source"] is None
    assert result["execution_allowed"] is False


def test_missing_scenario_never_returns_manifest():
    db = fixture()
    db.scenario = None
    with pytest.raises(DraftError):
        manifest.build_inert_manifest(db, 7, "s")
