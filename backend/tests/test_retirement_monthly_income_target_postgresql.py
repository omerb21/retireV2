from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from decimal import Decimal
from threading import Event, get_ident

import pytest
from sqlalchemy import create_engine, event, inspect, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.models.planning_input_decision import PlanningInputDecision
from app.models.retirement_facts import RecurringIncome
from app.models.retirement_monthly_income_target import RetirementMonthlyIncomeTargetElection as Election
from app.services import retirement_monthly_income_target_service as rit
from app.services.pension_product_service import PensionProductError
from test_canonical_conversion_migration import migrate
from test_planning_input import choose, income, view
from test_recovery_migration_postgresql import postgres_url
from test_retirement_target import payload as target_payload, save as save_target


@pytest.fixture
def pg_engine(postgres_url):
    migrate(postgres_url,"upgrade","a2b8c5e1f309")
    engine=create_engine(postgres_url)
    with engine.begin() as db:
        db.execute(text("INSERT INTO clients(client_id,display_name,id_number) VALUES(1,'test','123'),(2,'other','456')"))
    yield engine
    engine.dispose()


def prepare(engine):
    choose(engine); save_target(engine,target_payload(engine)); return view(engine)


def command(engine,**changes):
    plan=view(engine)
    return dict(client_id=1,expected_record_version=0,
        expected_planning_calculation_input_fingerprint=plan['planning_calculation_input_fingerprint'],
        expected_retirement_target_date=plan['retirement_target']['retirement_target_date'],monthly_amount='24000',
        income_basis='NET',price_basis='NOMINAL_AT_RETIREMENT_TARGET_DATE',price_reference_date=None,
        source_kind='PLANNER_SUPPLIED')|changes


def confirm(engine,request,actor='planner:pg'):
    with Session(engine) as db: return rit.confirm(db,request,actor)


def assess(engine):
    with Session(engine) as db: return rit.assess(db,1)


def test_postgresql_migration_shape_constraints_and_downgrade(postgres_url):
    migrate(postgres_url,'upgrade','f1a7c4d0e298'); engine=create_engine(postgres_url)
    try:
        with engine.begin() as db: db.execute(text("INSERT INTO clients(client_id,display_name,id_number) VALUES(1,'test','123')"))
        old=set(inspect(engine).get_table_names())
        migrate(postgres_url,'upgrade','a2b8c5e1f309')
        assert set(inspect(engine).get_table_names())-old=={'retirement_monthly_income_target_elections'}
        columns={c['name']:c for c in inspect(engine).get_columns('retirement_monthly_income_target_elections')}
        assert set(columns)=={'client_id','version','lifecycle_state','planning_calculation_input_fingerprint','retirement_target_date',
            'monthly_amount_text','currency','income_basis','price_basis','price_reference_date','source_kind','confirmation_state',
            'confirmation_actor','confirmed_at','target_semantic_fingerprint','created_at','updated_at'}
        with engine.connect() as db: assert db.scalar(text('SELECT count(*) FROM retirement_monthly_income_target_elections'))==0
        migrate(postgres_url,'downgrade','f1a7c4d0e298')
        assert set(inspect(engine).get_table_names())==old
    finally: engine.dispose()


def test_postgresql_confirm_assess_isolation_and_row_lock(pg_engine):
    prepare(pg_engine); request=command(pg_engine); statements=[]
    def capture(conn,cursor,sql,*args): statements.append(sql.strip().upper())
    event.listen(pg_engine,'before_cursor_execute',capture)
    try: result=confirm(pg_engine,request)
    finally: event.remove(pg_engine,'before_cursor_execute',capture)
    assert result['target_ready']
    assert statements[0]=='SET TRANSACTION ISOLATION LEVEL REPEATABLE READ'
    assert any('FROM CLIENTS' in sql and 'FOR UPDATE' in sql for sql in statements)
    assert any('RETIREMENT_MONTHLY_INCOME_TARGET_ELECTIONS' in sql and 'FOR UPDATE' in sql for sql in statements)
    statements.clear(); event.listen(pg_engine,'before_cursor_execute',capture)
    try: assert assess(pg_engine)['target_ready']
    finally: event.remove(pg_engine,'before_cursor_execute',capture)
    assert statements[0]=='SET TRANSACTION ISOLATION LEVEL REPEATABLE READ'


def test_t33_consistent_update_snapshot_and_fresh_stale(pg_engine):
    prepare(pg_engine); iid=income(pg_engine); request=command(pg_engine)
    paused,resume=Event(),Event(); worker=[None]; seen=[]
    def intercept(conn,cursor,sql,params,context,many):
        if get_ident()!=worker[0]: return
        upper=sql.strip().upper(); seen.append(upper)
        if 'FROM RECURRING_INCOME' in upper and not paused.is_set():
            paused.set(); assert resume.wait(20)
    def operation(): worker[0]=get_ident(); return confirm(pg_engine,request)
    event.listen(pg_engine,'after_cursor_execute',intercept)
    try:
        with ThreadPoolExecutor(1) as pool:
            pending=pool.submit(operation); assert paused.wait(20)
            try:
                with Session(pg_engine) as db,db.begin(): db.get(RecurringIncome,iid).amount=Decimal('99')
            finally: resume.set()
            first=pending.result(timeout=20)
    finally: resume.set(); event.remove(pg_engine,'after_cursor_execute',intercept)
    assert first['target_ready'] and seen[0]=='SET TRANSACTION ISOLATION LEVEL REPEATABLE READ'
    later=assess(pg_engine)
    assert later['authority_state']=='STALE' and 'RIT_PLANNING_IDENTITY_STALE' in later['blockers']
    assert later['authority']['record_version']==2 and assess(pg_engine)['authority']['record_version']==2


@pytest.mark.parametrize('mutation',['insert','delete','membership'])
def test_t33_row_universe_variants(pg_engine,mutation):
    prepare(pg_engine)
    existing=income(pg_engine) if mutation in {'delete','membership'} else None
    request=command(pg_engine); paused,resume=Event(),Event(); worker=[None]
    def intercept(conn,cursor,sql,params,context,many):
        if get_ident()==worker[0] and 'PG_ADVISORY_XACT_LOCK' in sql.upper() and not paused.is_set():
            paused.set(); assert resume.wait(20)
    def operation(): worker[0]=get_ident(); return confirm(pg_engine,request)
    event.listen(pg_engine,'after_cursor_execute',intercept)
    try:
        with ThreadPoolExecutor(1) as pool:
            pending=pool.submit(operation); assert paused.wait(20)
            try:
                with Session(pg_engine) as db,db.begin():
                    if mutation=='insert':
                        db.add(RecurringIncome(client_id=1,income_category='rental',description='insert',amount=Decimal('1'),frequency='monthly',amount_basis='gross',start_date=date(2020,1,1),continuation_status='ongoing'))
                    elif mutation=='delete': db.delete(db.get(RecurringIncome,existing))
                    else: db.get(RecurringIncome,existing).lifecycle_status='superseded'
            finally: resume.set()
            assert pending.result(timeout=20)['target_ready']
    finally: resume.set(); event.remove(pg_engine,'after_cursor_execute',intercept)
    assert assess(pg_engine)['authority_state']=='STALE'


def _competing_election(request, amount):
    target=rit._target_from_values(
        client_id=1,
        planning_fingerprint=request['expected_planning_calculation_input_fingerprint'],
        target_date=date.fromisoformat(request['expected_retirement_target_date']),
        amount=amount,
        income_basis=request['income_basis'],
        price_basis=request['price_basis'],
        reference_date=request['price_reference_date'],
    )
    now=datetime(2026,10,4,13,49,54,tzinfo=timezone.utc)
    return Election(
        client_id=1,version=1,lifecycle_state='CONFIRMED',
        planning_calculation_input_fingerprint=target['planning_calculation_input_fingerprint'],
        retirement_target_date=date.fromisoformat(target['retirement_target_date']),
        monthly_amount_text=amount,currency='ILS',income_basis=target['income_basis'],
        price_basis=target['price_basis'],price_reference_date=None,
        source_kind='PLANNER_SUPPLIED',confirmation_state='CONFIRMED',
        confirmation_actor='planner:competitor',confirmed_at=now,
        target_semantic_fingerprint=rit._semantic_fingerprint(target),created_at=now,updated_at=now,
    )


def test_t34_create_race_is_snapshot_ordered_and_fails_closed(pg_engine,monkeypatch):
    prepare(pg_engine); request=command(pg_engine); paused,resume=Event(),Event(); worker=[None]; observations=[]
    # Exercise the target uniqueness layer independently of the already-covered
    # client lock, so a bypassing writer can create the snapshot-invisible row.
    monkeypatch.setattr(rit,'_lock_client',lambda db,client_id: None)
    original=rit._locked_row
    def controlled(db,client_id):
        if get_ident()==worker[0] and not paused.is_set():
            observations.append(db.scalar(select(Election.version).where(Election.client_id==client_id)))
            paused.set(); assert resume.wait(20)
        return original(db,client_id)
    monkeypatch.setattr(rit,'_locked_row',controlled)
    def operation():
        worker[0]=get_ident()
        try: return confirm(pg_engine,request)
        except PensionProductError as exc: return exc.code
    with ThreadPoolExecutor(1) as pool:
        pending=pool.submit(operation); assert paused.wait(20)
        try:
            with Session(pg_engine) as competitor,competitor.begin():
                competitor.add(_competing_election(request,'24001'))
        finally: resume.set()
        outcome=pending.result(timeout=20)
    assert observations==[None]
    assert outcome=='RIT_RECORD_VERSION_CONFLICT'
    with Session(pg_engine) as db:
        row=db.get(Election,1)
        assert db.query(Election).count()==1 and row.version==1 and row.monthly_amount_text=='24001'


def test_t34_replacement_race_is_snapshot_ordered_and_cannot_overwrite(pg_engine,monkeypatch):
    prepare(pg_engine); confirm(pg_engine,command(pg_engine)); request=command(pg_engine,expected_record_version=1,monthly_amount='26000')
    # Isolate the target FOR UPDATE/CAS layer from the separately verified
    # client serialization lock.
    monkeypatch.setattr(rit,'_lock_client',lambda db,client_id: None)
    paused,resume=Event(),Event(); worker=[None]; observations=[]; original=rit._locked_row
    def controlled(db,client_id):
        if get_ident()==worker[0] and not paused.is_set():
            observations.append(db.scalar(select(Election.version).where(Election.client_id==client_id)))
            paused.set(); assert resume.wait(20)
        return original(db,client_id)
    monkeypatch.setattr(rit,'_locked_row',controlled)
    def operation():
        worker[0]=get_ident()
        try: return confirm(pg_engine,request)
        except PensionProductError as exc: return exc.code
    with ThreadPoolExecutor(1) as pool:
        pending=pool.submit(operation); assert paused.wait(20)
        try:
            with Session(pg_engine) as competitor,competitor.begin():
                row=competitor.get(Election,1)
                row.version=2; row.monthly_amount_text='25000'; row.updated_at=datetime.now(timezone.utc)
                target=rit._target_from_values(client_id=1,planning_fingerprint=row.planning_calculation_input_fingerprint,
                    target_date=row.retirement_target_date,amount='25000',income_basis=row.income_basis,
                    price_basis=row.price_basis,reference_date=row.price_reference_date)
                row.target_semantic_fingerprint=rit._semantic_fingerprint(target)
        finally: resume.set()
        outcome=pending.result(timeout=20)
    assert observations==[1]
    assert outcome=='RIT_RECORD_VERSION_CONFLICT'
    with Session(pg_engine) as db:
        row=db.get(Election,1)
        assert row.version==2 and row.monthly_amount_text=='25000'


class SerializationFailure(Exception):
    pgcode='40001'


def _count_attempt_boundaries(monkeypatch):
    calls={name:[] for name in ('begin','prepare','lock','derive','target')}
    bindings=(
        ('begin',rit,'_begin'),('prepare',rit,'_prepare_authoritative_state'),
        ('lock',rit,'_lock_client'),('derive',rit.planning,'derive'),('target',rit,'_locked_row'),
    )
    originals={name:getattr(owner,attribute) for name,owner,attribute in bindings}
    for name,owner,attribute in bindings:
        original=originals[name]
        def wrapper(*args,_name=name,_original=original,**kwargs):
            calls[_name].append(args[0] if args else None)
            return _original(*args,**kwargs)
        monkeypatch.setattr(owner,attribute,wrapper)
    return calls,originals


def test_t35_confirm_retry_reloads_after_context_and_target_were_loaded(pg_engine,monkeypatch):
    prepare(pg_engine); request=command(pg_engine); calls,originals=_count_attempt_boundaries(monkeypatch); failures=[]; target_calls=[]
    def controlled(db,client_id):
        target_calls.append(client_id)
        row=originals['target'](db,client_id)
        if not failures:
            failures.append(row)
            with Session(pg_engine) as other,other.begin():
                other.get(PlanningInputDecision,1).planning_base_date=date(2029,12,31)
            raise OperationalError('controlled after target load',{},SerializationFailure())
        return row
    monkeypatch.setattr(rit,'_locked_row',controlled)
    with Session(pg_engine) as db,pytest.raises(PensionProductError) as error:
        rit.confirm(db,request,'planner:pg')
    assert error.value.code=='RIT_CONFIRMATION_CONTEXT_STALE' and failures==[None]
    assert all(len(calls[name])>=2 for name in ('begin','prepare','lock','derive'))
    assert target_calls==[1,1]
    with Session(pg_engine) as db: assert db.get(Election,1) is None


def test_t35_assess_retry_reloads_context_and_target_and_fails_closed(pg_engine,monkeypatch):
    prepare(pg_engine); confirm(pg_engine,command(pg_engine)); calls,originals=_count_attempt_boundaries(monkeypatch); failures=[]; target_calls=[]
    def controlled(db,client_id):
        target_calls.append(client_id)
        row=originals['target'](db,client_id)
        if not failures:
            failures.append(row.version)
            with Session(pg_engine) as other,other.begin():
                other.get(PlanningInputDecision,1).planning_base_date=date(2029,12,31)
            raise OperationalError('controlled after target load',{},SerializationFailure())
        return row
    monkeypatch.setattr(rit,'_locked_row',controlled)
    with Session(pg_engine) as db: result=rit.assess(db,1)
    assert failures==[1] and result['authority_state']=='STALE' and not result['target_ready']
    assert 'RIT_PLANNING_IDENTITY_STALE' in result['blockers']
    assert all(len(calls[name])>=2 for name in ('begin','prepare','lock','derive'))
    assert target_calls==[1,1]
    with Session(pg_engine) as db:
        row=db.get(Election,1)
        assert row.version==2 and row.lifecycle_state=='STALE'
