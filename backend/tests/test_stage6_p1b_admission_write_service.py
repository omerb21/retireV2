"""P1B writer behavioral contract (unit only; PostgreSQL integration still required)."""
from types import SimpleNamespace
from unittest.mock import patch
import pytest

from app.services.scenario_pension_factor_admission_write_service import (
    _save_factor_admission, _AUTHENTICATED_FACTOR_WRITE_CAPABILITY,
    append_authenticated_serializable_factor_admission,
    PensionFactorWriteBlocked,
)
from app.db.base import load_all_models

load_all_models()

class DB:
    def __init__(self, previous_revision=None, statement_date=None):
        self._n=0
        self.previous_revision=previous_revision
        self.statement_date=statement_date
        self.added=[]
    def get_bind(self):
        return SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))
    def in_transaction(self):
        return True
    new=dirty=deleted=()
    def execute(self, stmt):
        return SimpleNamespace(scalar_one=lambda: "serializable" if "isolation" in str(stmt) else "off")
    def scalar(self, query):
        self._n+=1
        if self._n==1:
            return SimpleNamespace(client_id=1,scenario_id="s",version=2,status="draft")
        if self._n==2:
            return self.previous_revision
        if self._n==3:
            return SimpleNamespace(statement_date=self.statement_date or __import__("datetime").date(2026,9,30))
        if self._n==4:
            return SimpleNamespace(
                coefficient_selection="manual_review_required",
                pension_start_date=__import__("datetime").date(2027,9,30),
                survivors_option="60%",spouse_age_diff=0,option_name="standard")
        raise AssertionError("unexpected query")
    def add(self, row):
        self.added.append(row)
    def flush(self):
        pass

MANIFEST={
    "manifest_fingerprint":"a"*64,
    "decisions":[{"decision_id":"d","action":"pension","product_id":"p",
                  "component_id":"c","component_code":"code","amount":"100.00",
                  "source":{"source_fingerprint":"b"*64}}]}
REVIEW={"manifest_fingerprint":"a"*64,"election_fingerprint":"c"*64}
PERMISSION={"permission_admission_fingerprint":"e"*64,"ruleset_digest":"d"*64}

def call(db,**overrides):
    arguments=dict(client_id=1,scenario_id="s",decision_id="d",
        expected_scenario_version=2,expected_admission_revision=0,
        actor_id="authenticated-planner",factor_value="200",
        factor_evidence_type="PLANNER_ASSUMPTION",
        factor_evidence_reference="professional assumption",
        _capability=_AUTHENTICATED_FACTOR_WRITE_CAPABILITY)
    arguments.update(overrides)
    with patch("app.services.scenario_pension_factor_admission_write_service._derive_pension_action_permission_in_transaction",return_value=PERMISSION),patch(
         "app.services.scenario_pension_factor_admission_write_service.derive_documentary_review_context",return_value=REVIEW),patch(
         "app.services.scenario_pension_factor_admission_write_service.build_inert_manifest",return_value=MANIFEST):
        return _save_factor_admission(db,**arguments)

def test_append_only_new_revision_is_not_executable():
    db=DB()
    result=call(db)
    assert result["admission_revision"]==1
    assert result["execution_allowed"] is False
    assert len(db.added)==1
    assert db.added[0].admission_revision==1

def test_stale_scenario_rejected_before_permission():
    db=DB()
    with pytest.raises(PensionFactorWriteBlocked,match="FACTOR_ADMISSION_SCENARIO_STALE"):
        call(db,expected_scenario_version=3)
    assert not db.added

def test_missing_authenticated_actor_rejected():
    db=DB()
    with pytest.raises(PensionFactorWriteBlocked,match="FACTOR_ADMISSION_REQUEST_INVALID"):
        call(db,actor_id="")
    assert not db.added

def test_bad_factor_rejected_before_append():
    db=DB()
    with pytest.raises(PensionFactorWriteBlocked,match="FACTOR_ADMISSION_PREIMAGE_INVALID"):
        call(db,factor_value="0")
    assert not db.added

def test_direct_internal_call_without_capability_is_rejected():
    db=DB()
    with pytest.raises(PensionFactorWriteBlocked,match="FACTOR_ADMISSION_AUTHENTICATED_ENTRYPOINT_REQUIRED"):
        call(db,_capability=None)
    assert not db.added

def test_cas_rejects_competing_revision_before_any_write():
    db=DB(previous_revision=1)
    with pytest.raises(PensionFactorWriteBlocked,match="FACTOR_ADMISSION_REVISION_CONFLICT"):
        call(db,expected_admission_revision=0)
    assert not db.added

def test_cas_accepts_the_latest_revision():
    db=DB(previous_revision=1)
    outcome=call(db,expected_admission_revision=1)
    assert outcome["admission_revision"]==2
    assert db.added[0].admission_revision==2
    assert outcome["execution_allowed"] is False

def test_factor_approval_does_not_commit_transaction():
    db=DB()
    db.commit=lambda: (_ for _ in ()).throw(AssertionError("service must never commit"))
    call(db)
    assert len(db.added)==1

def test_payout_date_earlier_than_statement_fails_closed():
    from datetime import date
    db=DB(statement_date=date(2028,1,1))
    with pytest.raises(PensionFactorWriteBlocked,match="FACTOR_ADMISSION_PAYOUT_BEFORE_STATEMENT"):
        call(db)
    assert not db.added


def test_public_writer_requires_verified_session_actor_before_database_use():
    request=SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(
            auth_config=SimpleNamespace(production=True))),
        state=SimpleNamespace(
            trusted_professional_actor="forged",
            auth_session={"actor_id":"trusted"}),
    )
    with pytest.raises(PensionFactorWriteBlocked,match="FACTOR_ADMISSION_AUTHENTICATED_ACTOR_REQUIRED"):
        append_authenticated_serializable_factor_admission(
            object(),request=request,client_id=1,scenario_id="s",decision_id="d",
            expected_scenario_version=2,expected_admission_revision=0,
            factor_value="200",factor_evidence_type="PLANNER_ASSUMPTION",
            factor_evidence_reference="professional assumption")
