"""P1B contract validation unit tests; no database mutations."""
import pytest
from app.services.scenario_pension_factor_contract import (
    validate_admission_preimage, fingerprint_admission_preimage,
)

def valid():
    return {
        "contract_version":"SCENARIO_PENSION_FACTOR_ADMISSION_FINGERPRINT_V1",
        "client_id":1,"scenario_id":"s","scenario_version":2,"decision_id":"d",
        "admission_revision":1,"manifest_fingerprint":"a"*64,
        "source_fingerprint":"b"*64,"election_fingerprint":"c"*64,
        "ruleset_digest":"d"*64,"permission_admission_fingerprint":"e"*64,
        "source_product_id":"p","source_component_id":"c","component_code":"code",
        "amount":"100.00","statement_date":"2026-09-30",
        "pension_start_date":"2027-09-30","factor_value":"200",
        "factor_original_representation":"DIVISOR",
        "factor_evidence_type":"PLANNER_ASSUMPTION",
        "factor_evidence_reference":"manual estimate","survivors_option":"60%",
        "spouse_age_diff":0,"payout_option_name":"option","actor_id":"planner",
        "acknowledged_at_utc":"2026-10-27T08:00:00.000000Z",
    }

def test_valid_fingerprint_stable():
    a = valid()
    assert validate_admission_preimage(a) == a
    assert fingerprint_admission_preimage(a) == fingerprint_admission_preimage(dict(reversed(list(a.items()))))
    assert len(fingerprint_admission_preimage(a)) == 64

@pytest.mark.parametrize("field,replacement", [
    ("factor_value","200.00"),("factor_value","0"),("factor_value","1e2"),
    ("amount","100.001"),("client_id",True),("ruleset_digest","x"),
    ("actor_id",""),("factor_original_representation","PER_10000"),
    ("pension_start_date","2025-01-01"),
    ("acknowledged_at_utc","2026-10-27T08:00:00Z"),
    ("factor_evidence_type","GUARANTEED"),
])
def test_bad_preimage_rejected(field,replacement):
    entry=valid();entry[field]=replacement
    with pytest.raises(ValueError):
        validate_admission_preimage(entry)

def test_unrecognized_field_rejected():
    entry=valid();entry["execution_allowed"]=True
    with pytest.raises(ValueError):
        validate_admission_preimage(entry)

def test_change_in_rule_or_option_invalidates_hash():
    original=valid()
    new=dict(original, permission_admission_fingerprint="f"*64)
    assert fingerprint_admission_preimage(new)!=fingerprint_admission_preimage(original)
    changed=dict(original, survivors_option="100%")
    assert fingerprint_admission_preimage(changed)!=fingerprint_admission_preimage(original)
