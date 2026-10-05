from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path

import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.models.retirement_monthly_income_target import RetirementMonthlyIncomeTargetElection as Election
from app.services import retirement_monthly_income_target_service as rit
from app.services.pension_product_service import PensionProductError
from test_canonical_conversion_migration import migrate
from test_planning_input import choose, view
from test_recovery_pension_products import engine
from test_retirement_target import payload as target_payload, save as save_target

FIXED_TIME = datetime(2026, 10, 4, 13, 49, 54, tzinfo=timezone.utc)


def prepare(engine):
    choose(engine)
    save_target(engine, target_payload(engine))
    return view(engine)


def command(engine, **changes):
    plan = view(engine)
    base = dict(
        client_id=1,
        expected_record_version=0,
        expected_planning_calculation_input_fingerprint=plan["planning_calculation_input_fingerprint"],
        expected_retirement_target_date=plan["retirement_target"]["retirement_target_date"],
        monthly_amount="24000",
        income_basis="NET",
        price_basis="NOMINAL_AT_RETIREMENT_TARGET_DATE",
        price_reference_date=None,
        source_kind="PLANNER_SUPPLIED",
    )
    return base | changes


def confirm(engine, request, actor="planner:golden"):
    with Session(engine) as db:
        return rit.confirm(db, request, actor)


def assess(engine):
    with Session(engine) as db:
        return rit.assess(db, 1)


def independent_hash(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def golden_row(**changes):
    values = dict(client_id=7, version=1, lifecycle_state="CONFIRMED",
        planning_calculation_input_fingerprint="a" * 64, retirement_target_date=date(2030, 1, 1),
        monthly_amount_text="24000", currency="ILS", income_basis="NET",
        price_basis="NOMINAL_AT_RETIREMENT_TARGET_DATE", price_reference_date=None,
        source_kind="PLANNER_SUPPLIED", confirmation_state="CONFIRMED",
        confirmation_actor="planner:golden", confirmed_at=FIXED_TIME,
        target_semantic_fingerprint="4422b9e3f246bb3d85dd0a2b1367b66dac1c1272287b71eaec17db0f37b1be9a")
    return Election(**(values | changes))


@pytest.mark.parametrize("changes,semantic,result_hash", [
    ({}, "4422b9e3f246bb3d85dd0a2b1367b66dac1c1272287b71eaec17db0f37b1be9a", "604a01349db6bfca4db5d7a0b1d099f56a8c2347237bb7b7265cdcef1ec6f622"),
    ({"monthly_amount_text":"30000", "income_basis":"GROSS", "target_semantic_fingerprint":"8822ffb940b73fd5fbe632b4773b1b9e14bce093ffdffa08406de85d083b57fd"}, "8822ffb940b73fd5fbe632b4773b1b9e14bce093ffdffa08406de85d083b57fd", "2798dc5baf90b59cedb8e023c1f487389023e906abc18239c117b7d2ca80b7a9"),
    ({"price_basis":"REAL_AT_REFERENCE_DATE", "price_reference_date":date(2026,1,1), "target_semantic_fingerprint":"d527bdb4b27bae470064270ea8d00477eff2523c18a00a3ae2ac1e347cac80f4"}, "d527bdb4b27bae470064270ea8d00477eff2523c18a00a3ae2ac1e347cac80f4", "5269abe7c32a99372f056f78e083b98ae57465ae2d133c7a265da6ee81ed1285"),
])
def test_g1_g2_g3_ready_goldens(changes, semantic, result_hash):
    row = golden_row(**changes)
    result = rit._result({"client_id":7,"fingerprint":"a"*64,"retirement_target_date":date(2030,1,1)}, row)
    assert result["target_semantic_fingerprint"] == semantic
    assert result["target_result_fingerprint"] == result_hash
    assert result["target_ready"] and result["authority_state"] == "CURRENT"


def test_g4_g5_stale_goldens():
    planning = rit._result({"client_id":7,"fingerprint":"b"*64,"retirement_target_date":date(2030,1,1)},
        golden_row(version=2,lifecycle_state="STALE"))
    target = rit._result({"client_id":7,"fingerprint":"a"*64,"retirement_target_date":date(2031,1,1)},
        golden_row(version=2,lifecycle_state="STALE"))
    assert planning["target_result_fingerprint"] == "7123d035be1d8d3d6e2d067aaca6813525d26567bd7c45d764a850c5aa73132b"
    assert target["target_result_fingerprint"] == "0d260cd7a24857b5420a91019ee60d566b6e8165f2620adea4c7a56724c5244c"


def test_g6_g7_g8_g9_goldens():
    context={"client_id":7,"fingerprint":"a"*64,"retirement_target_date":date(2030,1,1)}
    missing=rit._result(context,None)
    confirmation=rit._result(context,golden_row(confirmation_actor=None))
    zero=rit._result(context,golden_row(monthly_amount_text="0"))
    mutation=rit._result(context,golden_row(monthly_amount_text="24001", target_semantic_fingerprint="d20ff839e4ce6e342644a9b763df2b45f0fc9e89012ec44b8bc3331c6a52fde5"))
    assert missing["target_result_fingerprint"]=="5dd06803e2e669daccfd758fe7d55553d3c28f55fe49266d2e64a0c517778cb4"
    assert confirmation["target_result_fingerprint"]=="628e88fff51d1186c3fbe85f3e698b1234ba8d44096bb8066fe3932c9bbb2705"
    assert zero["target_result_fingerprint"]=="6ff8b9a494df8bbe4dee7722fecfbf823095bfd9092b72270b6e1a6d8ed81301"
    assert mutation["target_semantic_fingerprint"]=="d20ff839e4ce6e342644a9b763df2b45f0fc9e89012ec44b8bc3331c6a52fde5"
    assert mutation["target_result_fingerprint"]=="4a9395223d44375cfe53e224b0ac763928af2a43300d9c76698052a1a45f03ab"


@pytest.mark.parametrize("field,value",[
    ("client_id",8),("planning_calculation_input_fingerprint","b"*64),("retirement_target_date","2031-01-01"),
    ("monthly_amount","24001"),("currency","USD"),("income_basis","GROSS"),
    ("price_basis","REAL_AT_REFERENCE_DATE"),("price_reference_date","2026-01-01"),
])
def test_t20_each_semantic_field_changes_independent_hash(field,value):
    target=dict(client_id=7,planning_calculation_input_fingerprint="a"*64,retirement_target_date="2030-01-01",
        monthly_amount="24000",currency="ILS",income_basis="NET",price_basis="NOMINAL_AT_RETIREMENT_TARGET_DATE",
        price_reference_date=None)
    changed=target|{field:value}
    if field=="price_basis": changed["price_reference_date"]="2026-01-01"
    assert independent_hash({"contract":rit.SEMANTIC_CONTRACT,**target}) != independent_hash({"contract":rit.SEMANTIC_CONTRACT,**changed})


@pytest.mark.parametrize("raw,expected", [(" +024000.0000000 ","24000"),("0.000001","0.000001"),("0001.2300","1.23")])
def test_amount_normalization(raw,expected): assert rit._canonical_amount(raw)==(expected,None)


@pytest.mark.parametrize("raw,code", [(True,"RIT_AMOUNT_INVALID"),(1,"RIT_AMOUNT_INVALID"),(1.0,"RIT_AMOUNT_INVALID"),
    ("NaN","RIT_AMOUNT_INVALID"),("Infinity","RIT_AMOUNT_INVALID"),("0","RIT_AMOUNT_INVALID"),("-0","RIT_AMOUNT_INVALID"),
    ("-1","RIT_AMOUNT_INVALID"),(".1","RIT_AMOUNT_INVALID"),("1.","RIT_AMOUNT_INVALID"),("1e2","RIT_AMOUNT_INVALID"),
    ("١","RIT_AMOUNT_INVALID"),("0.0000001","RIT_AMOUNT_PRECISION_UNSUPPORTED"),("24000.0000001","RIT_AMOUNT_PRECISION_UNSUPPORTED"),
    ("1000000000000000000","RIT_AMOUNT_PRECISION_UNSUPPORTED")])
def test_amount_rejections(raw,code): assert rit._canonical_amount(raw)==(None,code)


def test_confirm_assess_exact_contract_and_idempotency(engine, monkeypatch):
    prepare(engine); monkeypatch.setattr(rit,"_utc_now",lambda:FIXED_TIME)
    request=command(engine,monthly_amount=" +024000.0000000 ")
    first=confirm(engine,request)
    assert set(first)=={"schema_version","client_id","planning_calculation_input_fingerprint","retirement_target_date","target","authority","authority_state","target_readiness_state","target_ready","blockers","target_semantic_fingerprint","target_result_fingerprint"}
    assert set(first["target"])=={"client_id","planning_calculation_input_fingerprint","retirement_target_date","monthly_amount","currency","income_basis","price_basis","price_reference_date"}
    assert set(first["authority"])=={"record_version","source_kind","confirmation_state","confirmation_actor","confirmed_at","lifecycle_state"}
    assert first["target"]["monthly_amount"]=="24000" and first["target"]["currency"]=="ILS"
    retry=confirm(engine,request)
    assert retry==first
    assert assess(engine)==first


@pytest.mark.parametrize("field,value,code", [
    ("monthly_amount",None,"RIT_AMOUNT_MISSING"),("monthly_amount",0,"RIT_AMOUNT_INVALID"),("income_basis",None,"RIT_INCOME_BASIS_MISSING"),
    ("income_basis","net","RIT_INCOME_BASIS_INVALID"),("price_basis",None,"RIT_PRICE_BASIS_MISSING"),
    ("price_basis","REAL","RIT_PRICE_BASIS_INVALID"),("price_reference_date","2030-01-01","RIT_NOMINAL_PRICE_REFERENCE_DATE_NOT_NULL"),
])
def test_command_field_rejections(engine,field,value,code):
    prepare(engine); request=command(engine); request[field]=value
    with pytest.raises(PensionProductError) as error: confirm(engine,request)
    assert error.value.code==code
    with Session(engine) as db: assert db.get(Election,1) is None


@pytest.mark.parametrize("field,code", [
    ("income_basis", "RIT_INCOME_BASIS_INVALID"),
    ("price_basis", "RIT_PRICE_BASIS_INVALID"),
    ("source_kind", "RIT_CONFIRMATION_INVALID"),
])
@pytest.mark.parametrize("value", [[], {}, ["NET"], 1, True, 1.0, "unsupported"])
def test_malformed_enum_and_provenance_values_are_typed(engine, field, code, value):
    prepare(engine)
    with pytest.raises(PensionProductError) as error:
        confirm(engine, command(engine) | {field: value})
    assert error.value.code == code
    with Session(engine) as db:
        assert db.get(Election, 1) is None


def test_command_shape_precedes_malformed_field_semantics(engine):
    prepare(engine)
    malformed = command(engine) | {"income_basis": [], "unknown": "value"}
    with pytest.raises(PensionProductError) as error:
        confirm(engine, malformed)
    assert error.value.code == "RIT_COMMAND_SCHEMA_INVALID"


def test_command_shape_actor_real_date_and_context(engine):
    prepare(engine); request=command(engine)
    for malformed in ({k:v for k,v in request.items() if k!="source_kind"}, request|{"currency":"ILS"}):
        with pytest.raises(PensionProductError) as error: confirm(engine,malformed)
        assert error.value.code=="RIT_COMMAND_SCHEMA_INVALID"
    with pytest.raises(PensionProductError) as error: confirm(engine,request," caller ")
    assert error.value.code=="RIT_CONFIRMATION_INVALID"
    with pytest.raises(PensionProductError) as error: confirm(engine,request,"planner\u0085actor")
    assert error.value.code=="RIT_CONFIRMATION_INVALID"
    for reference,code in [(None,"RIT_PRICE_REFERENCE_DATE_MISSING"),("2030-1-1","RIT_PRICE_REFERENCE_DATE_INVALID")]:
        with pytest.raises(PensionProductError) as error:
            confirm(engine,command(engine,price_basis="REAL_AT_REFERENCE_DATE",price_reference_date=reference))
        assert error.value.code==code
    with pytest.raises(PensionProductError) as error: confirm(engine,command(engine,expected_planning_calculation_input_fingerprint="b"*64))
    assert error.value.code=="RIT_CONFIRMATION_CONTEXT_STALE"


@pytest.mark.parametrize("forbidden",["currency","confirmation_state","confirmation_actor","confirmed_at","lifecycle_state","version","target_semantic_fingerprint","target_result_fingerprint"])
def test_caller_cannot_author_server_fields(engine,forbidden):
    prepare(engine)
    with pytest.raises(PensionProductError) as error: confirm(engine,command(engine)|{forbidden:"spoofed"})
    assert error.value.code=="RIT_COMMAND_SCHEMA_INVALID"


@pytest.mark.parametrize("field,value",[("client_id",True),("client_id","1"),("expected_record_version",True),
    ("expected_record_version",1.0),("expected_planning_calculation_input_fingerprint","A"*64),
    ("expected_retirement_target_date","2030-1-1"),("expected_retirement_target_date","2030-01-01T00:00:00Z")])
def test_t22_strict_identity_hash_and_date_types(engine,field,value):
    prepare(engine)
    with pytest.raises(PensionProductError): confirm(engine,command(engine)|{field:value})
    with Session(engine) as db: assert db.get(Election,1) is None


def test_cached_planning_decision_is_refreshed_for_confirm(engine):
    prepare(engine)
    old_command = command(engine)
    from app.models.planning_input_decision import PlanningInputDecision
    with Session(engine, expire_on_commit=False) as retained:
        cached = retained.get(PlanningInputDecision, 1)
        assert cached.planning_base_date == date(2030, 1, 1)
        retained.commit()
        with Session(engine) as writer, writer.begin():
            writer.get(PlanningInputDecision, 1).planning_base_date = date(2029, 12, 31)
        with pytest.raises(PensionProductError) as error:
            rit.confirm(retained, old_command, "planner:cached")
        assert error.value.code == "RIT_CONFIRMATION_CONTEXT_STALE"
    with Session(engine) as db:
        assert db.get(Election, 1) is None


def test_cached_planning_decision_is_refreshed_for_assess(engine):
    prepare(engine)
    confirm(engine, command(engine))
    from app.models.planning_input_decision import PlanningInputDecision
    with Session(engine, expire_on_commit=False) as retained:
        cached = retained.get(PlanningInputDecision, 1)
        assert cached.planning_base_date == date(2030, 1, 1)
        retained.commit()
        with Session(engine) as writer, writer.begin():
            writer.get(PlanningInputDecision, 1).planning_base_date = date(2029, 12, 31)
        result = rit.assess(retained, 1)
    assert result["authority_state"] == "STALE"
    assert "RIT_PLANNING_IDENTITY_STALE" in result["blockers"]


def test_sqlstate_40001_during_derivation_retries_instead_of_becoming_domain_blocker(engine, monkeypatch):
    prepare(engine)
    request = command(engine)
    original = rit.planning.derive
    calls = []
    class SerializationFailure(Exception):
        pgcode = "40001"
    def controlled(db, client_id):
        calls.append(client_id)
        if len(calls) == 1:
            raise OperationalError("derive", {}, SerializationFailure())
        return original(db, client_id)
    monkeypatch.setattr(rit.planning, "derive", controlled)
    result = confirm(engine, request)
    assert result["target_ready"] and calls == [1, 1]


class _DatabaseDiagnostic:
    def __init__(self, constraint_name=None, table_name=None):
        self.constraint_name = constraint_name
        self.table_name = table_name


class _DatabaseFailure(Exception):
    def __init__(self, sqlstate=None, *, constraint_name=None, table_name=None):
        super().__init__(sqlstate)
        self.pgcode = sqlstate
        self.diag = _DatabaseDiagnostic(constraint_name, table_name)


@pytest.mark.parametrize("sqlstate", ["40001", "40P01"])
def test_retry_classifier_accepts_only_postgresql_transaction_conflicts(sqlstate):
    error = OperationalError("statement", {}, _DatabaseFailure(sqlstate))
    assert rit._retryable(error)


def test_retry_classifier_accepts_only_target_primary_key_unique_race():
    target = IntegrityError("statement", {}, _DatabaseFailure(
        "23505",
        constraint_name="retirement_monthly_income_target_elections_pkey",
        table_name="retirement_monthly_income_target_elections",
    ))
    assert rit._retryable(target)
    cases = [
        IntegrityError("statement", {}, _DatabaseFailure("23503")),
        IntegrityError("statement", {}, _DatabaseFailure("23514")),
        IntegrityError("statement", {}, _DatabaseFailure(
            "23505", constraint_name="other_table_key", table_name="other_table"
        )),
        IntegrityError("statement", {}, _DatabaseFailure(None)),
    ]
    assert [rit._retryable(error) for error in cases] == [False, False, False, False]


def test_create_replace_conflict_different_actor_and_explicit_reconfirmation(engine,monkeypatch):
    prepare(engine); monkeypatch.setattr(rit,"_utc_now",lambda:FIXED_TIME)
    initial=command(engine); first=confirm(engine,initial)
    with pytest.raises(PensionProductError) as error: confirm(engine,initial,"planner:other")
    assert error.value.code=="RIT_RECORD_VERSION_CONFLICT"
    replacement=confirm(engine,command(engine,expected_record_version=1,monthly_amount="24001"))
    assert replacement["authority"]["record_version"]==2
    assert replacement["target"]["monthly_amount"]=="24001"
    with pytest.raises(PensionProductError) as error: confirm(engine,initial)
    assert error.value.code=="RIT_RECORD_VERSION_CONFLICT"
    assert first["authority"]["confirmed_at"]==replacement["authority"]["confirmed_at"]


def test_sticky_planning_stale_once_a_b_a_and_reconfirm(engine,monkeypatch):
    prepare(engine); monkeypatch.setattr(rit,"_utc_now",lambda:FIXED_TIME)
    first=confirm(engine,command(engine)); original=first["target"]
    with Session(engine) as db,db.begin():
        from app.models.planning_input_decision import PlanningInputDecision
        db.get(PlanningInputDecision,1).planning_base_date=date(2029,12,31)
    stale=assess(engine)
    assert stale["authority_state"]=="STALE" and stale["authority"]["record_version"]==2
    assert stale["target"]==original and "RIT_PLANNING_IDENTITY_STALE" in stale["blockers"]
    assert assess(engine)["authority"]["record_version"]==2
    with Session(engine) as db,db.begin():
        from app.models.planning_input_decision import PlanningInputDecision
        db.get(PlanningInputDecision,1).planning_base_date=date(2030,1,1)
    returned=assess(engine)
    assert returned["blockers"]==["RIT_RECONFIRMATION_REQUIRED"] and returned["authority"]["record_version"]==2
    current=confirm(engine,command(engine,expected_record_version=2))
    assert current["authority_state"]=="CURRENT" and current["authority"]["record_version"]==3


def test_target_date_stale_and_semantics_preserved(engine,monkeypatch):
    prepare(engine); monkeypatch.setattr(rit,"_utc_now",lambda:FIXED_TIME)
    before=confirm(engine,command(engine,price_basis="REAL_AT_REFERENCE_DATE",price_reference_date="2040-01-01"))
    save_target(engine,target_payload(engine,date(2031,1,1)))
    after=assess(engine)
    assert after["authority_state"]=="STALE"
    assert "RIT_RETIREMENT_TARGET_STALE" in after["blockers"]
    assert after["target"]==before["target"] and after["target_semantic_fingerprint"]==before["target_semantic_fingerprint"]


def test_missing_invalid_fingerprint_and_result_independence(engine):
    prepare(engine); missing=assess(engine)
    assert missing["authority_state"]=="MISSING" and missing["blockers"]==["RIT_TARGET_MISSING"]
    confirmed=confirm(engine,command(engine))
    with Session(engine) as db,db.begin(): db.get(Election,1).target_semantic_fingerprint="f"*64
    invalid=assess(engine)
    assert invalid["authority_state"]=="INVALID" and invalid["blockers"]==["RIT_STORED_FINGERPRINT_MISMATCH"]
    assert confirmed["target_result_fingerprint"]==independent_hash({"contract":rit.RESULT_CONTRACT,**{k:v for k,v in confirmed.items() if k!="target_result_fingerprint"}})


def test_t24_ambiguous_and_unavailable_do_not_select_candidate():
    context={"client_id":7,"fingerprint":"a"*64,"retirement_target_date":date(2030,1,1)}
    ambiguous=rit._result(context,None,["RIT_TARGET_RECORD_AMBIGUOUS"],"AMBIGUOUS")
    unavailable=rit._result(context,None,["RIT_RECORD_UNAVAILABLE"],"UNAVAILABLE")
    for result in (ambiguous,unavailable):
        assert result["target"] is result["authority"] is None and not result["target_ready"]


def test_t26_provenance_changes_result_not_semantic():
    context={"client_id":7,"fingerprint":"a"*64,"retirement_target_date":date(2030,1,1)}
    first=rit._result(context,golden_row())
    variants=(golden_row(version=2),golden_row(source_kind="CLIENT_SUPPLIED"),golden_row(confirmation_actor="planner:other"),
        golden_row(confirmed_at=datetime(2026,10,4,13,49,55,tzinfo=timezone.utc)))
    for row in variants:
        current=rit._result(context,row)
        assert current["target_semantic_fingerprint"]==first["target_semantic_fingerprint"]
        assert current["target_result_fingerprint"]!=first["target_result_fingerprint"]


def test_assess_invalid_client_and_not_ready_context_are_fail_closed(engine):
    with Session(engine) as db:
        invalid=rit.assess(db,True)
    assert invalid["authority_state"]=="UNAVAILABLE" and invalid["blockers"]==["RIT_CLIENT_ID_INVALID"]
    with Session(engine) as db:
        unavailable=rit.assess(db,1)
    assert unavailable["authority_state"]=="UNAVAILABLE"
    assert unavailable["blockers"]==["RIT_RETIREMENT_TARGET_NOT_READY"]
    assert unavailable["target"] is unavailable["authority"] is None


def test_malformed_record_diagnostics_and_version_exhaustion(engine):
    context={"client_id":7,"fingerprint":"a"*64,"retirement_target_date":date(2030,1,1)}
    bad_version=rit._result(context,golden_row(version=0))
    bad_lifecycle=rit._result(context,golden_row(lifecycle_state="DRAFT"))
    assert bad_version["blockers"]==["RIT_TARGET_RECORD_INVALID"]
    assert bad_lifecycle["blockers"]==["RIT_TARGET_RECORD_INVALID"]
    prepare(engine); confirm(engine,command(engine))
    with Session(engine) as db,db.begin(): db.get(Election,1).version=rit.MAX_VERSION
    with pytest.raises(PensionProductError) as error:
        confirm(engine,command(engine,expected_record_version=rit.MAX_VERSION))
    assert error.value.code=="RIT_RECORD_VERSION_EXHAUSTED"
    with Session(engine) as db: assert db.get(Election,1).version==rit.MAX_VERSION


@pytest.mark.parametrize("reference",["2020-01-01","2030-01-01","2040-01-01"])
def test_real_reference_has_no_ordering_policy(engine,reference):
    prepare(engine)
    result=confirm(engine,command(engine,price_basis="REAL_AT_REFERENCE_DATE",price_reference_date=reference))
    assert result["target_ready"] and result["target"]["price_reference_date"]==reference


def test_blocked_resources_do_not_block_independent_target(engine):
    from test_planning_input import income
    prepare(engine); income(engine,amount_basis="unknown")
    plan=view(engine)
    assert not plan["planning_input_ready"] and plan["retirement_target"]["retirement_target_ready"]
    result=confirm(engine,command(engine))
    assert result["target_ready"] and result["blockers"]==[]


def test_no_inference_or_downstream_surface():
    source=Path(rit.__file__).read_text(encoding="utf-8")
    for forbidden in ("income_gap","withdrawal","allocation","M09","M10","CapitalProjection","PensionHolding","scenario"):
        assert forbidden not in source
    assert source.count("_fingerprint(") >= 3
    assert "source_fingerprint" not in source and "admission_fingerprint" not in source


def test_sqlite_transaction_and_late_failure_rollback(engine,monkeypatch):
    prepare(engine); request=command(engine); statements=[]
    from sqlalchemy import event
    def capture(conn,cursor,sql,*args): statements.append(sql.strip().upper())
    event.listen(engine,"before_cursor_execute",capture)
    original=Session.commit
    def failure(self): raise RuntimeError("late commit failure")
    monkeypatch.setattr(Session,"commit",failure)
    try:
        with pytest.raises(RuntimeError),Session(engine) as db: rit.confirm(db,request,"planner")
    finally:
        monkeypatch.setattr(Session,"commit",original); event.remove(engine,"before_cursor_execute",capture)
    assert statements[0]=="BEGIN IMMEDIATE"
    with Session(engine) as db: assert db.get(Election,1) is None


def test_t30_assess_commit_failure_rolls_back_sticky_transition(engine,monkeypatch):
    prepare(engine); confirm(engine,command(engine))
    with Session(engine) as db,db.begin():
        from app.models.planning_input_decision import PlanningInputDecision
        db.get(PlanningInputDecision,1).planning_base_date=date(2029,12,31)
    original=Session.commit
    def failure(self): raise RuntimeError("controlled assess commit failure")
    monkeypatch.setattr(Session,"commit",failure)
    try:
        with pytest.raises(RuntimeError),Session(engine) as db: rit.assess(db,1)
    finally: monkeypatch.setattr(Session,"commit",original)
    with Session(engine) as db:
        row=db.get(Election,1)
        assert row.lifecycle_state=="CONFIRMED" and row.version==1


def test_t31_database_constraints(engine):
    from sqlalchemy.exc import IntegrityError
    now=FIXED_TIME
    common=dict(client_id=1,version=1,lifecycle_state="CONFIRMED",planning_calculation_input_fingerprint="a"*64,
        retirement_target_date=date(2030,1,1),monthly_amount_text="1",currency="ILS",income_basis="NET",
        price_basis="NOMINAL_AT_RETIREMENT_TARGET_DATE",price_reference_date=None,source_kind="PLANNER_SUPPLIED",
        confirmation_state="CONFIRMED",confirmation_actor="planner",confirmed_at=now,target_semantic_fingerprint="b"*64,
        created_at=now,updated_at=now)
    for changes in ({"version":0},{"currency":"USD"},{"income_basis":"UNKNOWN"},
        {"price_basis":"NOMINAL_AT_RETIREMENT_TARGET_DATE","price_reference_date":date(2020,1,1)},
        {"confirmation_state":"DRAFT"}):
        with pytest.raises(IntegrityError),Session(engine) as db,db.begin():
            db.add(Election(**(common|changes))); db.flush()


def test_t32_exact_two_fingerprint_contracts_and_no_api_frontend():
    source=Path(rit.__file__).read_text(encoding="utf-8")
    assert source.count("_FINGERPRINT_JSON_V1") == 2
    assert "APIRouter" not in source and "FastAPI" not in source


def test_sqlite_migration_contract(tmp_path):
    url="sqlite:///"+(tmp_path/"rit.db").as_posix()
    migrate(url,"upgrade","f1a7c4d0e298")
    from sqlalchemy import create_engine
    dbengine=create_engine(url)
    try:
        with dbengine.begin() as db: db.execute(text("INSERT INTO clients(client_id,display_name,id_number) VALUES(1,'test','123')"))
        migrate(url,"upgrade","a2b8c5e1f309")
        assert "retirement_monthly_income_target_elections" in inspect(dbengine).get_table_names()
        with dbengine.connect() as db: assert db.scalar(text("SELECT COUNT(*) FROM retirement_monthly_income_target_elections"))==0
        migrate(url,"downgrade","f1a7c4d0e298")
        assert "retirement_monthly_income_target_elections" not in inspect(dbengine).get_table_names()
        assert "clients" in inspect(dbengine).get_table_names()
    finally: dbengine.dispose()
