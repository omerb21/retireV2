from concurrent.futures import ThreadPoolExecutor
from threading import Event, Barrier, get_ident
from datetime import date
import pytest
from sqlalchemy import create_engine, event, text, inspect
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from app.models.client import Client
from app.models.retirement_facts import RetirementTimingWorkIntention as Timing
from app.schemas.planning_input import BaseDateDecision
from app.services import planning_input_service as planning
from app.services import retirement_target_service as target
from app.services.pension_product_service import PensionProductError
from test_recovery_migration_postgresql import postgres_url
from test_canonical_conversion_migration import migrate
from test_planning_input_postgresql import pg_engine
from test_retirement_target import payload, save
from test_planning_input import view, choose


def migration_contract(url):
    migrate(url, 'upgrade', 'b7c3e0f6a854')
    engine = create_engine(url)
    try:
        with engine.begin() as db:
            db.execute(text("INSERT INTO clients(client_id,display_name,id_number,planned_retirement_date) VALUES(1,'test','123','2040-01-01')"))
            db.execute(text("INSERT INTO planning_input_decisions(client_id,version,planning_base_date,actor) VALUES(1,7,'2030-01-01','legacy')"))
        with engine.connect() as db:
            before = db.execute(text('SELECT * FROM planning_input_decisions')).mappings().one()
            client_before = db.execute(text('SELECT * FROM clients')).one()
        old_columns = {c['name'] for c in inspect(engine).get_columns('planning_input_decisions')}
        migrate(url, 'upgrade', 'c8d4f1a7b965')
        added = {c['name'] for c in inspect(engine).get_columns('planning_input_decisions')} - old_columns
        assert added == {'retirement_target_date','retirement_target_decision_actor','retirement_target_decided_at','retirement_target_reference_fingerprint'}
        with engine.connect() as db:
            after = db.execute(text('SELECT * FROM planning_input_decisions')).mappings().one()
            assert {k: after[k] for k in before} == dict(before)
            assert all(after[k] is None for k in added)
            assert db.execute(text('SELECT * FROM clients')).one() == client_before
        migrate(url, 'downgrade', 'b7c3e0f6a854')
        assert {c['name'] for c in inspect(engine).get_columns('planning_input_decisions')} == old_columns
        migrate(url, 'upgrade', 'c8d4f1a7b965')
        migrate(url, 'upgrade', 'f1a7c4d0e298')
        save(engine, payload(engine, date(2029, 1, 1)))
        before_failure = view(engine)
        assert before_failure['retirement_target']['relation_to_planning_base'] == 'before_base'
        failure = migrate(url, 'downgrade', 'b7c3e0f6a854', success=False)
        assert 'TARGET_DOWNGRADE_WOULD_LOSE_DECISION' in failure
        # SQLite may commit earlier additive-schema downgrades before the historical guard.
        with engine.connect() as db:
            assert str(db.scalar(text('SELECT retirement_target_date FROM planning_input_decisions'))) == '2029-01-01'
        migrate(url, 'upgrade', 'f1a7c4d0e298')
        assert view(engine) == before_failure
        save(engine, payload(engine, None))
        migrate(url, 'downgrade', 'b7c3e0f6a854')
    finally: engine.dispose()


def test_pg_target_migration(postgres_url): migration_contract(postgres_url)


def seed_timing(engine):
    with engine.begin() as db:
        db.execute(text("INSERT INTO retirement_timing_work_intention(client_id,timing_confidence,work_after_retirement_intention,planned_work_end_date) VALUES(1,'known','undecided','2040-01-01')"))


def test_pg_reference_change_before_snapshot_is_stale(pg_engine):
    old = payload(pg_engine)
    with Session(pg_engine) as db, db.begin(): db.get(Client, 1).planned_retirement_date = date(2040, 1, 1)
    before = view(pg_engine)
    with pytest.raises(PensionProductError) as error: save(pg_engine, old)
    assert error.value.code == 'TARGET_REFERENCE_STATE_STALE'
    assert view(pg_engine) == before


def test_pg_two_source_tables_no_torn_write_snapshot(pg_engine):
    seed_timing(pg_engine)
    from app.services.canonical_manual_pension_service import create
    from app.models.canonical_manual_pension_source import CanonicalManualPensionSource
    from test_professional_source_snapshot import facts
    with Session(pg_engine) as db, db.begin(): create(db, 1, facts())
    choose(pg_engine)
    request = payload(pg_engine)
    paused, resume = Event(), Event()
    writer_thread = [None]
    statements = []
    def intercept(conn, cursor, sql, params, context, many):
        if get_ident() != writer_thread[0]: return
        statements.append(sql.strip().upper())
        # Timing has been read, but canonical pension adapter has not been read.
        if sql.strip().upper().startswith('SELECT') and 'FROM retirement_timing_work_intention' in sql and not paused.is_set():
            paused.set()
            assert resume.wait(20)
    def writer():
        writer_thread[0] = get_ident()
        return save(pg_engine, request)
    event.listen(pg_engine, 'after_cursor_execute', intercept)
    try:
        with ThreadPoolExecutor(1) as pool:
            pending = pool.submit(writer)
            assert paused.wait(20)
            try:
                with Session(pg_engine) as db, db.begin():
                    db.query(Timing).filter_by(client_id=1).update({'planned_work_end_date': date(2041, 1, 1)})
                    db.query(CanonicalManualPensionSource).filter_by(client_id=1).update({'pension_start_date': date(2042, 1, 1)})
            finally: resume.set()
            assert pending.result(timeout=20)['decision_version'] == 2
    finally:
        resume.set()
        event.remove(pg_engine, 'after_cursor_execute', intercept)
    assert statements[0] == 'SET TRANSACTION ISOLATION LEVEL REPEATABLE READ'
    assert any('FOR UPDATE' in sql and 'planning_input_decisions' in sql.lower() for sql in statements)
    after = view(pg_engine)
    authority = after['retirement_target']
    assert authority['reference_fingerprint_at_decision'] == request.expected_target_reference_fingerprint
    assert authority['current_reference_fingerprint'] != authority['reference_fingerprint_at_decision']
    assert authority['retirement_target_date'] == '2030-01-01'
    assert authority['retirement_target_ready']
    assert 'target_reference_state_changed_since_decision' in authority['warnings']


def test_pg_base_target_race_full_rollback(pg_engine):
    choose(pg_engine)
    request = payload(pg_engine)
    barrier = Barrier(2)
    def writer(kind):
        barrier.wait(15)
        try:
            if kind == 'target': save(pg_engine, request)
            else:
                with Session(pg_engine) as db, db.begin():
                    planning.set_base_date(db, 1, BaseDateDecision(expected_version=1, planning_base_date=date(2031, 1, 1)))
            return kind
        except PensionProductError as error: return error.code
        except OperationalError as error:
            assert error.orig.pgcode == '40001'
            return 'serialization_retry'
    with ThreadPoolExecutor(2) as pool: results = list(pool.map(writer, ['base','target']))
    assert len(set(results) & {'base','target'}) == 1
    assert len(set(results) & {'PLANNING_DECISION_STALE','serialization_retry'}) == 1
    result = view(pg_engine)
    assert result['decision_version'] == 2
    if 'base' in results:
        assert result['retirement_target']['retirement_target_date'] is None
        assert result['retirement_target']['decision_actor'] is None
    else: assert result['planning_base_date'] == '2030-01-01'


def test_pg_real_serialization_failure_rolls_back_target_and_version(pg_engine):
    choose(pg_engine)
    request = payload(pg_engine)
    before = view(pg_engine)
    with pytest.raises(OperationalError) as error:
        with Session(pg_engine) as db:
            target.set_target(db, 1, request)
            db.execute(text("DO $$ BEGIN RAISE EXCEPTION 'test serialization abort' USING ERRCODE = '40001'; END $$"))
            db.commit()
    assert error.value.orig.pgcode == '40001'
    assert view(pg_engine) == before


def test_pg_consistent_read_includes_target(pg_engine):
    choose(pg_engine)
    before = view(pg_engine)
    request = payload(pg_engine)
    paused, resume = Event(), Event()
    reader_thread = [None]
    def intercept(conn, cursor, sql, params, context, many):
        if get_ident() == reader_thread[0] and sql.strip().upper().startswith('SELECT') and not paused.is_set():
            paused.set()
            assert resume.wait(20)
    def reader():
        reader_thread[0] = get_ident()
        return view(pg_engine)
    event.listen(pg_engine, 'after_cursor_execute', intercept)
    try:
        with ThreadPoolExecutor(1) as pool:
            pending = pool.submit(reader)
            assert paused.wait(20)
            try: save(pg_engine, request)
            finally: resume.set()
            assert pending.result(timeout=20) == before
    finally:
        resume.set()
        event.remove(pg_engine, 'after_cursor_execute', intercept)
    assert view(pg_engine)['retirement_target']['retirement_target_date'] == '2030-01-01'
