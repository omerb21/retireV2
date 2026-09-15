from datetime import date, datetime, timezone
from types import SimpleNamespace
import inspect
import pytest
from sqlalchemy import event, select
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import get_db
from app.models.client import Client
from app.models.employment_record import EmploymentRecord
from app.models.planning_input_decision import PlanningInputDecision
from app.schemas.planning_input import TargetDateDecision, BaseDateDecision
from app.services import retirement_target_service as target
from app.services import planning_input_service as planning
from app.services.pension_product_service import PensionProductError
from test_recovery_pension_products import engine
from test_planning_input import view, choose, income


def payload(engine, value=date(2030, 1, 1), **overrides):
    current = view(engine)
    return TargetDateDecision(**(dict(expected_version=current['decision_version'],
        expected_target_reference_fingerprint=current['retirement_target']['current_reference_fingerprint'],
        retirement_target_date=value) | overrides))


def save(engine, request):
    with Session(engine) as db:
        result = target.set_target(db, 1, request)
        db.commit()
        return result


@pytest.mark.parametrize('base,value,relation,ready', [
    (False, None, 'base_and_target_missing', False),
    (False, date(2030, 1, 1), 'base_missing', False),
    (True, None, 'target_missing', False),
    (True, date(2029, 12, 31), 'before_base', False),
    (True, date(2030, 1, 1), 'equal_to_base', True),
    (True, date(2030, 1, 2), 'after_base', True),
])
def test_relations_persist_without_minimum_horizon(engine, base, value, relation, ready):
    if base: choose(engine)
    save(engine, payload(engine, value))
    result = view(engine)
    authority = result['retirement_target']
    assert authority['retirement_target_date'] == (value.isoformat() if value else None)
    assert authority['relation_to_planning_base'] == relation
    assert authority['retirement_target_ready'] is ready
    assert result['ready_for_next_planning_calculation'] is ready
    assert authority['blockers'] == sorted(authority['blockers'])
    if value:
        assert authority['decision_actor'] and authority['decided_at']
        assert authority['reference_fingerprint_at_decision'] == authority['current_reference_fingerprint']
    else:
        assert authority['decision_actor'] is authority['decided_at'] is authority['reference_fingerprint_at_decision'] is None


def test_closed_decision_projection_and_semantic_identity(engine):
    empty = view(engine)
    assert empty['retirement_target']['retirement_target_date'] is None
    with Session(engine) as db:
        assert db.scalar(select(PlanningInputDecision)) is None
    first_payload = payload(engine)
    save(engine, first_payload)
    first = view(engine)
    assert first['planning_input_fingerprint'] == empty['planning_input_fingerprint']
    assert first['planning_calculation_input_fingerprint'] != empty['planning_calculation_input_fingerprint']
    save(engine, payload(engine))
    second = view(engine)
    assert second['decision_version'] == 2
    for key in ('planning_input_fingerprint', 'planning_calculation_input_fingerprint'):
        assert first[key] == second[key]
    with pytest.raises(PensionProductError, match='') as error:
        save(engine, first_payload)
    assert error.value.code == 'PLANNING_DECISION_STALE'
    with Session(engine) as db, db.begin():
        row = db.scalar(select(PlanningInputDecision))
        row.retirement_target_decision_actor = 'other server actor'
        row.retirement_target_decided_at = datetime(2000, 1, 1, tzinfo=timezone.utc)
        row.retirement_target_reference_fingerprint = 'a' * 64
        row.version += 1
    metadata = view(engine)
    assert metadata['planning_calculation_input_fingerprint'] == second['planning_calculation_input_fingerprint']
    assert metadata['planning_input_fingerprint'] == empty['planning_input_fingerprint']
    assert 'target_reference_state_changed_since_decision' in metadata['retirement_target']['warnings']
    save(engine, payload(engine, date(2031, 1, 1)))
    assert view(engine)['retirement_target']['decision_fingerprint'] != first['retirement_target']['decision_fingerprint']
    save(engine, payload(engine, None))
    cleared = view(engine)
    assert cleared['retirement_target']['decision_fingerprint'] == empty['retirement_target']['decision_fingerprint']
    assert cleared['planning_calculation_input_fingerprint'] == empty['planning_calculation_input_fingerprint']
    choose(engine, cleared['decision_version'])
    assert view(engine)['planning_input_fingerprint'] != empty['planning_input_fingerprint']
    assert planning.planning_decision_semantics(SimpleNamespace(planning_base_date=None, future_column='ignored')) == {'planning_base_date': None}
    assert 'record(decision)' not in inspect.getsource(planning.derive)


def test_four_closed_adapters_multiplicity_types_and_order():
    client = SimpleNamespace(client_id=1, planned_retirement_date=date(2040, 1, 1), planned_retirement_age=67)
    def timing(i, state='current'):
        return SimpleNamespace(id=i, lifecycle_status=state, **{f: date(2040, 1, 1) for f in target.TIMING_FIELDS})
    def pension(sid, visible=True, state='current'):
        return dict(source_id=sid, pension_start_date=date(2040, 1, 1), lifecycle_status=state,
            visible=visible, version=2, missing_or_blocking_facts=[])
    sources = [pension('manual:1'), pension('conversion:2'), pension('manual:3', False), pension('manual:4', state='superseded')]
    facts = target.references(client, [timing(2), timing(1), timing(3, 'superseded')], {'pension_sources': sources})
    assert len(facts) == 12
    assert {f['source_kind'] for f in facts} == set(target.ADAPTERS)
    assert len(target.ADAPTERS) == 4
    assert facts == sorted(facts, key=lambda f: f['reference_id'])
    assert facts[0]['reference_id'] == 'client:1:planned_retirement_age'
    assert facts[0]['age_value'] == 67 and facts[0]['date_value'] is None
    assert facts[1]['reference_id'] == 'client:1:planned_retirement_date'
    for fact in facts:
        assert set(fact) == {'reference_id','source_id','source_kind','source_field','value_kind','date_value','age_value',
            'source_semantic_fingerprint','source_version','lifecycle_state','unresolved_state'}
        assert (fact['date_value'] is None) != (fact['age_value'] is None)
        if fact['source_kind'] == target.ADAPTERS[2]:
            assert fact['reference_id'] == fact['source_id'] + ':' + fact['source_field']
        if fact['source_kind'] == target.ADAPTERS[3]:
            assert fact['reference_id'] == 'pension:' + fact['source_id'] + ':pension_start_date'
            assert fact['source_version'] == 2 and fact['source_semantic_fingerprint'] is None
    fp = target.reference_fingerprint(1, facts)
    assert fp == target.reference_fingerprint(1, list(reversed(facts)))
    for fact in facts:
        assert fp != target.reference_fingerprint(1, [f for f in facts if f is not fact])
    with pytest.raises(PensionProductError) as error:
        target.canonical_references(facts + [facts[0]])
    assert error.value.code == 'TARGET_REFERENCE_STRUCTURE_INVALID'


@pytest.mark.parametrize('age', [False, True])
def test_client_reference_never_selects_target_and_stale_fails_before_write(engine, age):
    old = payload(engine)
    with Session(engine) as db, db.begin():
        client = db.get(Client, 1)
        if age: client.planned_retirement_age = 67
        else: client.planned_retirement_date = date(2040, 1, 1)
    result = view(engine)
    assert len(result['target_reference_facts']) == 1
    assert result['retirement_target']['retirement_target_date'] is None
    with pytest.raises(PensionProductError) as error: save(engine, old)
    assert error.value.code == 'TARGET_REFERENCE_STATE_STALE'
    assert view(engine)['decision_version'] == 0
    save(engine, payload(engine))
    choose(engine, 1)
    assert view(engine)['retirement_target']['retirement_target_date'] == '2030-01-01'


def test_excluded_employment_income_and_unregistered_dates(engine):
    before = view(engine)
    with Session(engine) as db, db.begin():
        db.add(EmploymentRecord(employment_record_id='e1', client_id=1, employer_name='employer',
            work_start_date=date(2000, 1, 1), work_end_date=date(2040, 1, 1), is_current=False))
    income(engine, income_category='pension')
    after = view(engine)
    assert before['retirement_target'] == after['retirement_target']
    assert after['target_reference_facts'] == []
    client = SimpleNamespace(client_id=1, planned_retirement_age=None, planned_retirement_date=None,
        statutory_date=date(2040, 1, 1), eligibility_date=date(2041, 1, 1))
    assert target.references(client, [], {'pension_sources': [], 'm07': {'date': '2040-01-01'},
        'm09': {'date': '2040-01-01'}, 'm10': {'date': '2040-01-01'}, 'archive': [{'date': '2040-01-01'}]}) == []


def test_sqlite_explicit_transaction_failure_rollback_and_readiness(engine):
    choose(engine)
    income(engine, amount_basis='unknown')
    request = payload(engine)
    statements = []
    def capture(conn, cursor, sql, *args): statements.append(sql.strip().upper())
    event.listen(engine, 'before_cursor_execute', capture)
    try:
        with pytest.raises(RuntimeError):
            with Session(engine) as db:
                target.set_target(db, 1, request)
                raise RuntimeError('late failure before commit')
    finally: event.remove(engine, 'before_cursor_execute', capture)
    assert statements[0] == 'BEGIN IMMEDIATE'
    assert view(engine)['decision_version'] == 1
    save(engine, request)
    result = view(engine)
    assert result['retirement_target']['retirement_target_ready']
    assert not result['ready_for_next_planning_calculation']
    with Session(engine) as db:
        db.get(Client, 1)
        with pytest.raises(PensionProductError) as error: target.set_target(db, 1, request)
        assert error.value.code == 'TARGET_REQUIRES_FRESH_TRANSACTION'


def test_api_closed_request_ownership_clear_and_stale(engine):
    def session():
        with Session(engine) as db: yield db
    app.dependency_overrides[get_db] = session
    try:
        with TestClient(app) as client:
            path = '/api/clients/1/retirement-planning-input/target-date'
            request = payload(engine).model_dump(mode='json')
            for forbidden in ('actor', 'timestamp', 'provenance', 'recommendation'):
                assert client.put(path, json=request | {forbidden: 'not allowed'}).status_code == 422
            assert client.put(path.replace('/1/', '/999/'), json=request).status_code == 404
            assert client.put(path, json=request).status_code == 200
            assert client.put(path, json=request).status_code == 409
            clear = payload(engine, None).model_dump(mode='json')
            assert client.put(path, json=clear).status_code == 200
            result = view(engine)
            assert result['decision_version'] == 2
            assert result['retirement_target']['retirement_target_date'] is None
    finally: app.dependency_overrides.clear()


def test_sqlite_migration(tmp_path):
    from test_retirement_target_postgresql import migration_contract
    migration_contract('sqlite:///' + (tmp_path / 'target.db').as_posix())


def test_real_canonical_conversion_and_manual_references_current_only(engine):
    from app.services.canonical_manual_pension_service import create
    from test_professional_source_snapshot import facts
    from test_canonical_component_conversion import seeded, request
    from app.services.canonical_component_conversion_service import execute, reverse
    from app.schemas.canonical_conversion import ReversalRequest
    with Session(engine) as db, db.begin():
        create(db, 1, facts())
    source = seeded(engine, component=5)
    with Session(engine) as db, db.begin():
        converted = execute(db, 1, request(source, component=5, destination='pension'), 'test')
    current = view(engine)
    refs = current['target_reference_facts']
    assert len(refs) == 2
    assert any(r['source_id'].startswith('conversion:') for r in refs)
    assert any(r['source_id'].startswith('manual:') for r in refs)
    assert current['retirement_target']['retirement_target_date'] is None
    assert 'target_reference_dates_conflict' in current['retirement_target']['warnings']
    save(engine, payload(engine))
    conversion = converted['conversions'][0]
    with Session(engine) as db, db.begin():
        reverse(db, 1, conversion['conversion_id'], ReversalRequest(expected_conversion_version=1,
            expected_product_version=converted['product_version'], idempotency_key='target-reverse', reason='test'), 'test')
    remaining = view(engine)
    assert len(remaining['target_reference_facts']) == 1
    assert remaining['retirement_target']['retirement_target_date'] == '2030-01-01'
    assert 'target_reference_state_changed_since_decision' in remaining['retirement_target']['warnings']


def test_sqlite_writer_excludes_concurrent_source_mutation_and_lock_failure(engine):
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import OperationalError
    request = payload(engine)
    competing = create_engine(engine.url, connect_args={'timeout': 0.01})
    try:
        with Session(engine) as db:
            target.set_target(db, 1, request)
            with pytest.raises(OperationalError):
                with competing.begin() as connection:
                    connection.execute(text("UPDATE clients SET planned_retirement_date='2040-01-01' WHERE client_id=1"))
            db.commit()
        before = view(engine)
        retry = payload(engine, date(2031, 1, 1))
        with engine.connect() as blocker:
            blocker.exec_driver_sql('BEGIN IMMEDIATE')
            with pytest.raises(OperationalError): save(competing, retry)
            blocker.rollback()
        assert view(engine) == before
    finally: competing.dispose()


def test_closed_target_boundary_no_downstream_execution():
    from pathlib import Path
    source = inspect.getsource(target)
    for forbidden in ('PensionHolding', 'pension_holding', 'm02_', 'm03_', 'm04_', 'm05_', 'm06_', 'm07_',
                      'm09_', 'm10_', 'date.today', 'timedelta', '182', 'EmploymentRecord'):
        assert forbidden not in source
    root = Path(__file__).resolve().parents[2]
    delta = (root / 'backend/alembic/versions/c8d4f1a7b965_retirement_target_date.py').read_text(encoding='utf-8')
    assert 'down_revision = "b7c3e0f6a854"' in delta
    assert 'create_table' not in delta and 'UPDATE ' not in delta
    # This endpoint extends the existing input boundary; it is not a calculation engine.
    endpoints = {route.path for route in app.routes}
    assert '/api/clients/{client_id}/retirement-planning-input/target-date' in endpoints
    assert not any('/m10' in path for path in endpoints)
    for route in app.routes:
        if '/m09' in route.path:
            assert route.methods <= {'GET', 'HEAD'}
            assert 'm09-archive-only' in route.tags
