from concurrent.futures import ThreadPoolExecutor
from threading import Event, Barrier, get_ident
from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy import create_engine, text, inspect, event
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from app.models.retirement_facts import CapitalAsset
from app.models.planning_input_decision import PlanningInputDecision
from app.services import capital_projection_basis_service as basis
from app.services.pension_product_service import PensionProductError
from test_planning_input_postgresql import pg_engine
from test_recovery_migration_postgresql import postgres_url
from test_canonical_conversion_migration import migrate
from test_projection_basis import read, context, capital, payload, save
from test_planning_input import income


def migration_contract(url):
    migrate(url,'upgrade','c8d4f1a7b965')
    engine=create_engine(url)
    try:
        with engine.begin() as db:
            db.execute(text("INSERT INTO clients(client_id,display_name,id_number) VALUES(1,'test','123')"))
            db.execute(text("INSERT INTO capital_asset(client_id,asset_category,asset_description,known_value_amount,value_as_of_date) VALUES(1,'other','legacy',123.45,'2020-01-01')"))
        with engine.connect() as db: before=db.execute(text('SELECT * FROM capital_asset')).all()
        old_tables=set(inspect(engine).get_table_names())
        migrate(url,'upgrade','d9e5a2b8c076')
        assert set(inspect(engine).get_table_names())-old_tables=={'capital_projection_basis_decisions'}
        with engine.connect() as db:
            assert db.execute(text('SELECT * FROM capital_asset')).all()==before
            assert db.scalar(text('SELECT COUNT(*) FROM capital_projection_basis_decisions'))==0
        migrate(url,'downgrade','c8d4f1a7b965')
        assert set(inspect(engine).get_table_names())==old_tables
        migrate(url,'upgrade','d9e5a2b8c076')
        # Historical schema assertions above remain pinned; current reads need the current schema.
        migrate(url,'upgrade','f1a7c4d0e298')
        context(engine)
        rate='12345678901234567890123456789012345678901234567890.123456789012345678901234567890123456789'
        save(engine,1,payload(engine,1,annual_rate=rate))
        assert read(engine)['covered_capital_sources'][0]['annual_rate']==rate
        if engine.dialect.name=='postgresql':
            with engine.connect() as db:
                assert db.scalar(text('SELECT annual_rate FROM capital_projection_basis_decisions'))==Decimal(rate)
                spec=db.execute(text("SELECT numeric_precision,numeric_scale FROM information_schema.columns WHERE table_name='capital_projection_basis_decisions' AND column_name='annual_rate'")).one()
                assert spec==(None,None)
        before=read(engine)
        assert 'PROJECTION_DOWNGRADE_WOULD_LOSE_DECISIONS' in migrate(url,'downgrade','c8d4f1a7b965',success=False)
        # SQLite may commit earlier additive-schema downgrades before the historical guard.
        # Check the protected decision before returning to the current application's schema.
        with engine.connect() as db:
            assert str(db.scalar(text('SELECT annual_rate FROM capital_projection_basis_decisions'))) == rate
        migrate(url,'upgrade','f1a7c4d0e298')
        assert read(engine)==before
    finally: engine.dispose()


def test_pg_projection_migration_exact_unconstrained_numeric(postgres_url): migration_contract(postgres_url)


def test_pg_source_change_before_write_stale(pg_engine):
    context(pg_engine); asset=capital(pg_engine); request=payload(pg_engine,asset)
    with Session(pg_engine) as db,db.begin(): db.get(CapitalAsset,asset).known_value_amount=Decimal('200.01')
    before=read(pg_engine)
    with pytest.raises(PensionProductError) as error: save(pg_engine,asset,request)
    assert error.value.code=='PROJECTION_SOURCE_STATE_STALE'
    assert read(pg_engine)==before


def test_pg_write_snapshot_no_torn_source_and_income(pg_engine):
    context(pg_engine); asset=capital(pg_engine); income(pg_engine)
    request=payload(pg_engine,asset)
    paused,resume=Event(),Event(); writer_id=[None]; sqls=[]
    def intercept(conn,cursor,sql,params,ctx,many):
        if get_ident()!=writer_id[0]: return
        sqls.append(sql.strip().upper())
        if 'FROM capital_asset' in sql and 'FOR UPDATE' in sql and not paused.is_set():
            paused.set(); assert resume.wait(20)
    def writer(): writer_id[0]=get_ident(); return save(pg_engine,asset,request)
    event.listen(pg_engine,'after_cursor_execute',intercept)
    try:
        with ThreadPoolExecutor(1) as pool:
            pending=pool.submit(writer); assert paused.wait(20)
            try:
                # A separate, unrelated source commits after the writer's snapshot.
                with pg_engine.begin() as db: db.execute(text("UPDATE recurring_income SET amount=22 WHERE client_id=1"))
            finally: resume.set()
            assert pending.result(timeout=20)['decision_version']==3
    finally: resume.set(); event.remove(pg_engine,'after_cursor_execute',intercept)
    assert sqls[0]=='SET TRANSACTION ISOLATION LEVEL REPEATABLE READ'
    assert any('PLANNING_INPUT_DECISIONS' in sql and 'FOR UPDATE' in sql for sql in sqls)
    assert any('CAPITAL_ASSET' in sql and 'FOR UPDATE' in sql for sql in sqls)
    after=read(pg_engine); source=after['covered_capital_sources'][0]
    assert source['projection_basis_decision']['planning_calculation_input_fingerprint_at_decision']==request.expected_planning_calculation_input_fingerprint
    assert after['planning_calculation_input_fingerprint']!=request.expected_planning_calculation_input_fingerprint
    assert source['projection_basis_source_readiness']


@pytest.mark.parametrize('other_kind',['projection','base','target'])
def test_pg_competing_writes_one_winner(pg_engine, other_kind):
    context(pg_engine); asset=capital(pg_engine); request=payload(pg_engine,asset)
    barrier=Barrier(2)
    def writer(kind):
        barrier.wait(20)
        try:
            if kind=='projection': save(pg_engine,asset,request)
            elif kind=='base':
                from app.services.planning_input_service import set_base_date
                from app.schemas.planning_input import BaseDateDecision
                with Session(pg_engine) as db,db.begin():
                    set_base_date(db,1,BaseDateDecision(expected_version=2,planning_base_date=date(2029,1,1)))
            else:
                from test_retirement_target import payload as target_payload, save as target_save
                target_save(pg_engine,target_request)
            return 'ok'
        except PensionProductError as error: return error.code
        except OperationalError as error:
            assert error.orig.pgcode=='40001'
            return 'retry'
    from test_retirement_target import payload as target_payload
    target_request=target_payload(pg_engine,date(2031,1,1))
    with ThreadPoolExecutor(2) as pool: results=list(pool.map(writer,['projection',other_kind]))
    assert results.count('ok')==1
    assert set(results)-{'ok'} <= {'retry','PLANNING_DECISION_STALE'}
    assert read(pg_engine)['decision_version']==3


def test_pg_serialization_abort_rolls_back_everything(pg_engine):
    context(pg_engine); asset=capital(pg_engine); request=payload(pg_engine,asset); before=read(pg_engine)
    with pytest.raises(OperationalError):
        with Session(pg_engine) as db:
            basis.write(db,1,asset,request)
            db.execute(text("DO $$ BEGIN RAISE EXCEPTION 'abort' USING ERRCODE='40001'; END $$"))
            db.commit()
    assert read(pg_engine)==before


def test_pg_repeatable_read_contains_source_and_decision(pg_engine):
    context(pg_engine); asset=capital(pg_engine); request=payload(pg_engine,asset); before=read(pg_engine)
    paused,resume=Event(),Event(); reader_id=[None]; sqls=[]
    def intercept(conn,cursor,sql,params,ctx,many):
        if get_ident()!=reader_id[0]: return
        sqls.append(sql.strip().upper())
        if sql.strip().upper().startswith('SELECT') and not paused.is_set():
            paused.set(); assert resume.wait(20)
    def reader(): reader_id[0]=get_ident(); return read(pg_engine)
    event.listen(pg_engine,'after_cursor_execute',intercept)
    try:
        with ThreadPoolExecutor(1) as pool:
            pending=pool.submit(reader); assert paused.wait(20)
            try: save(pg_engine,asset,request)
            finally: resume.set()
            assert pending.result(timeout=20)==before
    finally: resume.set(); event.remove(pg_engine,'after_cursor_execute',intercept)
    assert sqls[0]==('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY' if pg_engine.dialect.name=='postgresql' else 'BEGIN')
    assert all(sql.startswith(('SELECT','SET TRANSACTION','BEGIN')) for sql in sqls)
    assert read(pg_engine)['projection_basis_ready']
