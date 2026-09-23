from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from threading import Event, get_ident

import pytest
from sqlalchemy import event, text
from sqlalchemy.orm import Session
from app.models.client import Client
from app.services import capital_projection_execution_service as execution
from app.services.pension_product_service import PensionProductError
from test_recovery_pension_products import engine
from test_recovery_migration_postgresql import postgres_url
from test_planning_input_postgresql import pg_engine
from test_projection_basis import context, capital, payload, save
from test_projection_execution import view, database_snapshot, pair, recertify


def seed(db_engine, rate='0.07', start=date(2026,1,1), amount='123.45'):
    with Session(db_engine) as db,db.begin():
        for client_id in (1,2):
            c=db.get(Client,client_id); c.display_name='test'; c.id_number=str(client_id)
    context(db_engine)
    asset=capital(db_engine,known_value_amount=Decimal(amount),value_as_of_date=start)
    save(db_engine,asset,payload(db_engine,asset,annual_rate=rate))
    return asset


def test_pg_sqlite_byte_identical_and_read_only(pg_engine,engine):
    # AC016/022/023/026/041, both runtimes use exactly the same service path.
    for db_engine in (engine,pg_engine): seed(db_engine)
    before=database_snapshot(pg_engine)
    statements=[]
    def intercept(conn,cursor,sql,*args): statements.append(sql.strip().upper())
    event.listen(pg_engine,'before_cursor_execute',intercept)
    try: result=view(pg_engine)
    finally: event.remove(pg_engine,'before_cursor_execute',intercept)
    sqlite_result=view(engine)
    assert result==view(pg_engine)
    # The live upstream planning fingerprint includes database-generated source
    # and client timestamps. Independently seeded databases are NOT identical
    # admission inputs. Numeric results must nevertheless be byte-identical.
    for field in ('known_value_amount','annual_rate','elapsed_days','year_fraction_numerator',
                  'year_fraction_denominator','projection_factor','projected_amount',
                  'source_semantic_fingerprint','projection_timing_context_fingerprint',
                  'projection_basis_decision_fingerprint'):
        assert result['projected_sources'][0][field]==sqlite_result['projected_sources'][0][field]
    # Boundary-fixture proof for byte-identical full fingerprints: explicitly
    # supply ONE shared planning-input identity to both database-derived input
    # payloads, and recertify their admission envelopes. No production authority
    # is normalized, replaced or modified; these are in-memory test fixtures.
    admitted=[]
    for db_engine in (engine,pg_engine):
        plan,authority=pair(db_engine)
        plan['planning_calculation_input_fingerprint']='a'*64
        authority['planning_calculation_input_fingerprint']='a'*64
        recertify(plan,authority)
        admitted.append(execution.execute(1,plan,authority))
    assert admitted[0]==admitted[1]
    assert statements[0]=='SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'
    assert all(s.startswith(('SELECT','SET TRANSACTION')) for s in statements)
    assert database_snapshot(pg_engine)==before


def test_pg_sqlite_failure_boundary(pg_engine,engine):
    # AC053/054/064: real admitted 35-digit exact half-cell factor, not a mock.
    for db_engine in (engine,pg_engine):
        seed(db_engine,rate='500000004',amount='1.00')
        with pytest.raises(PensionProductError) as error: view(db_engine)
        assert error.value.code=='PROJECTION_EXECUTION_NUMERIC_DOMAIN_FAILURE'


def test_pg_consistent_snapshot_during_source_change(pg_engine):
    asset=seed(pg_engine); before=view(pg_engine)
    paused,resume=Event(),Event(); reader_id=[None]
    def intercept(conn,cursor,sql,*args):
        if get_ident()==reader_id[0] and sql.lstrip().upper().startswith('SELECT') and not paused.is_set():
            paused.set(); assert resume.wait(30)
    def reader(): reader_id[0]=get_ident(); return view(pg_engine)
    event.listen(pg_engine,'after_cursor_execute',intercept)
    try:
        with ThreadPoolExecutor(1) as pool:
            pending=pool.submit(reader); assert paused.wait(30)
            try:
                with pg_engine.begin() as db: db.execute(text('UPDATE capital_asset SET known_value_amount=999 WHERE id=:id'),dict(id=asset))
            finally: resume.set()
            assert pending.result(timeout=30)==before
    finally: resume.set(); event.remove(pg_engine,'after_cursor_execute',intercept)
    assert view(pg_engine)['execution_status']=='BLOCKED_NO_RESULT'
