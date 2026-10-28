"""Revision read is an informational CAS cursor, not financial authority."""
from types import SimpleNamespace
from unittest.mock import patch

from app.api import scenario_stage6_factor_admission_routes as route


class FakeDB:
    def __init__(self):
        self.rolled_back=0
        self.queries=0
        self.executed=[]
    def in_transaction(self):
        return False
    def get_bind(self):
        return SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))
    def execute(self,stmt):
        self.executed.append(str(stmt))
    def scalar(self,query):
        self.queries+=1
        if self.queries==1:
            return SimpleNamespace(status="draft",version=3)
        if self.queries==2:
            return SimpleNamespace(action="pension")
        if self.queries==3:
            return 7
        raise AssertionError("unexpected extra query")
    def rollback(self):
        self.rolled_back+=1


def req(preview=True,actor="planner:approved"):
    session={"actor_id":actor} if actor is not None else None
    state=SimpleNamespace(auth_session=session,trusted_professional_actor=actor)
    return SimpleNamespace(state=state,app=SimpleNamespace(
        state=SimpleNamespace(stage6_preview_enabled=preview)))


def test_cursor_does_not_claim_approval_or_execution():
    db=FakeDB()
    response=route.current_admission_revision(
        req(),scenario_id="sc",decision_id="d",client_id=1,db=db)
    import json
    result=json.loads(response.body)
    assert result == {
        "scenario_version":3,
        "latest_admission_revision":7,
        "authority_state":"NOT_EVALUATED",
    }
    assert db.rolled_back==1
    assert db.queries==3
    assert db.executed and "REPEATABLE READ, READ ONLY" in db.executed[0]


def test_disabled_preview_requires_no_database_reads():
    db=FakeDB()
    with patch.object(route,"error",return_value="disabled"):
        response=route.current_admission_revision(
            req(preview=False),scenario_id="sc",decision_id="d",client_id=1,db=db)
    assert response=="disabled"
    assert db.queries==0


def test_forged_actor_never_reaches_database():
    db=FakeDB()
    forged=req()
    forged.state.auth_session={"actor_id":"another"}
    with patch.object(route,"error",return_value="unauthorized"):
        response=route.current_admission_revision(
            forged,scenario_id="sc",decision_id="d",client_id=1,db=db)
    assert response=="unauthorized"
    assert db.queries==0
