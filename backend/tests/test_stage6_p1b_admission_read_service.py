"""P1B saved approval verification tests. No financial execution."""
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from app.services.scenario_pension_factor_admission_read_service import (
    read_current_admission, FactorAdmissionBlocked,
)
from app.services.scenario_pension_factor_contract import fingerprint_admission_preimage
from app.services.pension_monthly_basis_service import canonical_bytes
from app.db.base import load_all_models

load_all_models()

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

def execute(data,*,change_row=None, statement_date=None, pension_start_date=None,
            payout_option_name="option", coefficient_selection="manual_review_required"):
    encoded=canonical_bytes(data).decode("utf-8")
    row=dict(client_id=1,scenario_id="s",decision_id="d",scenario_version=2,
             admission_revision=1,actor_id="planner",record_fingerprint=fingerprint_admission_preimage(data),
             preimage_json=encoded,permission_admission_fingerprint=data["permission_admission_fingerprint"],
             manifest_fingerprint=data["manifest_fingerprint"],source_fingerprint=data["source_fingerprint"],
             election_fingerprint=data["election_fingerprint"])
    row.update(change_row or {})
    class FakeDb:
        def __init__(self): self.counter=0
        def scalars(self, q): return SimpleNamespace(all=lambda:[SimpleNamespace(**row)])
        def scalar(self, q):
            from datetime import date
            self.counter+=1
            if self.counter==1: return SimpleNamespace(
                statement_date=statement_date or date(2026,9,30))
            if self.counter==2: return SimpleNamespace(
                pension_start_date=pension_start_date or date(2027,9,30),
                survivors_option="60%",spouse_age_diff=0,
                option_name=payout_option_name,
                coefficient_selection=coefficient_selection)
            raise AssertionError("unexpected query")
    db=FakeDb()
    return db

def verify(data,*,permission_digest=None,manifest_amount="100.00",
           manifest_version=2,manifest_source_fingerprint=None,**kwargs):
    db=execute(data,**kwargs)
    with patch("app.services.scenario_pension_factor_admission_read_service.derive_documentary_review_context",return_value={"election_fingerprint":"c"*64}), patch("app.services.scenario_pension_factor_admission_read_service.build_inert_manifest",return_value={"scenario_version":manifest_version,"manifest_fingerprint":"a"*64,"decisions":[{"decision_id":"d","product_id":"p","component_id":"c","component_code":"code","amount":manifest_amount,"source":{"source_fingerprint":manifest_source_fingerprint or "b"*64}}]}), patch("app.services.scenario_pension_factor_admission_read_service.derive_pension_action_permission_admission",
        return_value={"permission_admission_fingerprint":permission_digest or "e"*64,"ruleset_digest":"d"*64}):
        return read_current_admission(db,client_id=1,scenario_id="s",decision_id="d")

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
    data["amount"]="101.00"
    with pytest.raises(FactorAdmissionBlocked,match="FACTOR_ADMISSION_STALE"):
        verify(data)

def test_indexed_provenance_tampering_fails():
    with pytest.raises(FactorAdmissionBlocked, match="FACTOR_ADMISSION_INDEXED_PROVENANCE_MISMATCH"):
        verify(payload(), change_row={"election_fingerprint": "f" * 64})


@pytest.mark.parametrize("kwargs", [
    {"manifest_amount": "101.00"},
    {"manifest_version": 3},
    {"manifest_source_fingerprint": "f" * 64},
    {"payout_option_name": "changed-option"},
    {"pension_start_date": __import__("datetime").date(2028, 1, 1)},
])
def test_current_source_amount_version_or_election_change_invalidates(kwargs):
    with pytest.raises(FactorAdmissionBlocked, match="FACTOR_ADMISSION_STALE"):
        verify(payload(), **kwargs)


def test_nonmanual_or_payout_before_statement_is_not_current_authority():
    with pytest.raises(FactorAdmissionBlocked, match="FACTOR_CURRENT_CONTEXT_MISSING"):
        verify(payload(), coefficient_selection="catalog_candidate")
    with pytest.raises(FactorAdmissionBlocked, match="FACTOR_CURRENT_CONTEXT_MISSING"):
        verify(payload(), statement_date=__import__("datetime").date(2028,1,1))
