"""P1B saved approval verification tests. No financial execution."""
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from app.services.scenario_pension_factor_admission_read_service import (
    read_current_admission, FactorAdmissionBlocked,
)
from app.services.scenario_pension_factor_contract import fingerprint_admission_preimage
from app.services.pension_monthly_basis_service import canonical_bytes

def payload():
    return dict(
        contract_version="SCENARIO_PENSION_FACTOR_ADMISSION_FINGERPRINT_V1",
        client_id=1,scenario_id="s",scenario_version=2,decision_id="d",
        admission_revision=1,manifest_fingerprint="a"*64,
        source_fingerprint="b"*64,election_fingerprint="c"*64,
        ruleset_digest="d"*64,permission_admission_fingerprint="e"*64,
        source_product_id="p",source_component_id="c",component_code="code",
        amount="100.00",statement_date="2026-09-30",
        pension_start_date="2027-09-30",factor_value="200",
        factor_original_representation="DIVISOR",
        factor_evidence_type="PLANNER_ASSUMPTION",
        factor_evidence_reference="source",survivors_option="60%",
        spouse_age_diff=0,payout_option_name="option",
        actor_id="planner",acknowledged_at_utc="2026-10-27T08:00:00.000000Z",
    )

def context(data):
    keys=("scenario_version","manifest_fingerprint","source_fingerprint",
    "election_fingerprint","source_product_id","source_component_id",
    "component_code","amount","statement_date","pension_start_date",
    "survivors_option","spouse_age_diff","payout_option_name")
    return {k:data[k] for k in keys}

def execute(data,*,change_row=None, permission_digest=None, current_context=None):
    encoded=canonical_bytes(data).decode("utf-8")
    row=dict(client_id=1,scenario_id="s",decision_id="d",scenario_version=2,
             admission_revision=1,actor_id="planner",record_fingerprint=fingerprint_admission_preimage(data),
             preimage_json=encoded)
    row.update(change_row or {})
    db=SimpleNamespace(scalars=lambda query: SimpleNamespace(all=lambda:[SimpleNamespace(**row)]))
    return db, current_context if current_context is not None else context(data)

def verify(data,**kwargs):
    db,ctx=execute(data,**kwargs)
    with patch("app.services.scenario_pension_factor_admission_read_service.derive_pension_action_permission_admission",
        return_value={"permission_admission_fingerprint":kwargs.get("permission_digest") or "e"*64,"ruleset_digest":"d"*64}):
        return read_current_admission(db,client_id=1,scenario_id="s",decision_id="d",current_context=ctx)

def test_valid_approval_remains_nonexecutable():
    result=verify(payload())
    assert result["execution_allowed"] is False
    assert result["factor_value"]=="200"

def test_permission_changed_fails():
    with pytest.raises(FactorAdmissionBlocked,match="FACTOR_PERMISSION_STALE"):
        verify(payload(),permission_digest="f"*64)

def test_row_hash_changed_fails():
    with pytest.raises(FactorAdmissionBlocked,match="FACTOR_ADMISSION_TAMPERED"):
        verify(payload(),change_row={"record_fingerprint":"f"*64})

def test_current_amount_changed_fails():
    data=payload()
    ctx=context(data)
    ctx["amount"]="101.00"
    with pytest.raises(FactorAdmissionBlocked,match="FACTOR_ADMISSION_STALE"):
        verify(data,current_context=ctx)
