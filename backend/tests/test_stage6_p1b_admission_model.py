"""P1B schema contract tests: model only, no migrations or financial execution."""
from sqlalchemy import CheckConstraint, UniqueConstraint, inspect
from app.models.scenario_pension_factor_admission import ScenarioPensionFactorAdmission
from app.services.scenario_pension_factor_contract import (
    validate_admission_preimage, fingerprint_admission_preimage,
)
import pytest


def sample():
    return {
        "contract_version": "SCENARIO_PENSION_FACTOR_ADMISSION_FINGERPRINT_V1",
        "client_id": 1, "scenario_id": "s", "scenario_version": 1,
        "decision_id": "d", "admission_revision": 1,
        "manifest_fingerprint": "a" * 64, "source_fingerprint": "b" * 64,
        "election_fingerprint": "c" * 64,
        "ruleset_digest": "d" * 64,
        "permission_admission_fingerprint": "e" * 64,
        "source_product_id": "p", "source_component_id": "c",
        "component_code": "sample", "amount": "123.00",
        "statement_date": "2026-09-30", "pension_start_date": "2027-09-30",
        "factor_value": "200", "factor_original_representation": "DIVISOR",
        "factor_evidence_type": "PLANNER_ASSUMPTION",
        "factor_evidence_reference": "professional estimate",
        "survivors_option": "60%", "spouse_age_diff": 0,
        "payout_option_name": "standard", "actor_id": "authenticated-planner",
        "acknowledged_at_utc": "2026-10-27T08:00:00.000000Z",
    }


def test_model_registers_closed_revision_and_provenance():
    model = inspect(ScenarioPensionFactorAdmission)
    assert model.local_table.name == "scenario_pension_factor_admissions"
    columns = model.columns
    assert all(key in columns for key in (
        "client_id", "scenario_id", "decision_id", "scenario_version",
        "admission_revision", "preimage_json", "record_fingerprint",
        "actor_id", "permission_admission_fingerprint"
    ))
    constraints = list(model.local_table.constraints)
    assert any(isinstance(x, UniqueConstraint) and
               x.name == "uq_s6_factor_admission_revision" for x in constraints)
    assert any(isinstance(x, CheckConstraint) and
               x.name == "ck_s6_factor_revision" for x in constraints)


def test_exact_contract_stable_and_revision_sensitive():
    preimage = sample()
    assert validate_admission_preimage(preimage) == preimage
    a = fingerprint_admission_preimage(preimage)
    assert a == fingerprint_admission_preimage(dict(reversed(list(preimage.items()))))
    assert a != fingerprint_admission_preimage(dict(preimage, admission_revision=2))
    assert a != fingerprint_admission_preimage(dict(preimage, permission_admission_fingerprint="f" * 64))


@pytest.mark.parametrize("key,value", [
    ("factor_value", "0"),
    ("factor_value", "200.0"),
    ("amount", "123.001"),
    ("client_id", True),
    ("pension_start_date", "2025-01-01"),
    ("actor_id", ""),
    ("ruleset_digest", "not-a-digest"),
])
def test_bad_authority_fails_closed(key, value):
    payload = sample()
    payload[key] = value
    with pytest.raises(ValueError):
        validate_admission_preimage(payload)
