from datetime import date, datetime, timezone
from decimal import Decimal
import copy
import inspect
import pytest
from sqlalchemy import select, text, event, create_engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, IntegrityError
from pydantic import ValidationError
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import get_db
from app.models.retirement_facts import CapitalAsset
from app.models.capital_projection_basis import CapitalProjectionBasisDecision as Decision, parse_rate, rate_string
from app.models.planning_input_decision import PlanningInputDecision
from app.schemas.capital_projection_basis import ProjectionDecisionWrite, ProjectionExpectations
from app.schemas.planning_input import BaseDateDecision
from app.services import capital_projection_basis_service as basis
from app.services import planning_input_service as planning
from app.services.pension_product_service import PensionProductError
from test_recovery_pension_products import engine
from test_planning_input import choose, income, view as plan_view
from test_retirement_target import save as save_target, payload as target_payload


def read(engine, client=1):
    with Session(engine) as db: return basis.read(db, client)


def context(engine):
    choose(engine)
    save_target(engine, target_payload(engine, date(2030, 1, 1)))


def capital(engine, **changes):
    with Session(engine) as db, db.begin():
        row = CapitalAsset(**(dict(client_id=1, asset_category='other', asset_description='source',
            known_value_amount=Decimal('100.00'), value_as_of_date=date(2020, 1, 1)) | changes))
        db.add(row); db.flush()
        return row.id


def expectations(current, asset):
    source = next(s for s in current['covered_capital_sources'] if s['capital_asset_id'] == asset)
    return dict(expected_version=current['decision_version'],
        expected_planning_calculation_input_fingerprint=current['planning_calculation_input_fingerprint'],
        expected_source_semantic_fingerprint=source['source_semantic_fingerprint'],
        expected_timing_context_fingerprint=source['projection_timing_context_fingerprint'])


def payload(engine, asset, **changes):
    return ProjectionDecisionWrite(**(expectations(read(engine), asset) |
        dict(annual_rate='0', return_basis='NET', price_basis='NOMINAL') | changes))


def save(engine, asset, request, *, clear=False, client=1):
    with Session(engine) as db:
        result = basis.write(db, client, asset, request, clear=clear)
        db.commit()
        return result


@pytest.mark.parametrize('rate', ['0','0.03','-0.5','-0.9999999999999999999999999999999999999',
    '1234567890123456789012345678901234567890.12345678901234567890123456789'])
def test_exact_rate_round_trip_no_cap(engine, rate):
    context(engine); asset = capital(engine)
    before = plan_view(engine)
    request = payload(engine, asset, annual_rate=rate)
    save(engine, asset, request)
    current = read(engine)
    assert current['projection_basis_ready']
    source = current['covered_capital_sources'][0]
    assert source['annual_rate'] == rate
    with Session(engine) as db:
        assert db.get(Decision, asset).annual_rate == Decimal(rate)
        assert isinstance(db.get(Decision, asset).annual_rate, Decimal)
    after = plan_view(engine)
    assert after['decision_version'] == before['decision_version'] + 1
    for key in ('planning_input_fingerprint','planning_calculation_input_fingerprint'):
        assert after[key] == before[key]
    save(engine, asset, payload(engine, asset, annual_rate=rate))
    resaved = read(engine)
    assert resaved['decision_version'] == current['decision_version'] + 1
    assert resaved['projection_basis_admission_fingerprint'] == current['projection_basis_admission_fingerprint']


@pytest.mark.parametrize('rate', ['', ' ', ' 0','0 ','+0.1','-0','00','01','0.0','1.00','.5','1.',
    '1e2','NaN','Infinity','-Infinity','-1','-2','-1.0001',0,0.03,None])
def test_invalid_rates_rejected(rate):
    with pytest.raises(ValidationError):
        ProjectionDecisionWrite(expected_version=0, expected_planning_calculation_input_fingerprint='a'*64,
            expected_source_semantic_fingerprint='b'*64, expected_timing_context_fingerprint='c'*64,
            annual_rate=rate, return_basis='NET', price_basis='REAL')


@pytest.mark.parametrize('changes,blocker', [
    ({'known_value_amount':None}, 'SOURCE_VALUE_UNRESOLVED'),
    ({'value_as_of_date':None}, 'VALUATION_DATE_MISSING'),
    ({'value_as_of_date':date(2030,1,2)}, 'VALUATION_DATE_AFTER_PLANNING_BASE'),
    ({'value_as_of_date':date(2031,1,1)}, 'VALUATION_DATE_AFTER_RETIREMENT_TARGET'),
])
def test_incomplete_sources_never_disappear(engine, changes, blocker):
    context(engine)
    good = capital(engine); bad = capital(engine, **changes)
    save(engine, good, payload(engine, good))
    current = read(engine)
    assert current['covered_source_count'] == 2 and not current['projection_basis_ready']
    item = next(s for s in current['covered_capital_sources'] if s['capital_asset_id'] == bad)
    assert blocker in item['blockers']
    assert 'RATE_MISSING' in item['blockers']
    assert 'RETURN_BASIS_MISSING_OR_INVALID' in item['blockers']
    assert 'PRICE_BASIS_MISSING_OR_INVALID' in item['blockers']
    assert item['annual_rate'] is None and item['projection_basis_decision'] is None
    assert item['economic_projection_start_date'] == (changes.get('value_as_of_date',date(2020,1,1)).isoformat() if changes.get('value_as_of_date',date(2020,1,1)) else None)
    save(engine, bad, payload(engine, bad))
    assert blocker in read(engine)['aggregate_blockers']


def test_zero_coverage_and_missing_decision(engine):
    before = read(engine)
    assert before['covered_source_count'] == 0 and not before['projection_basis_ready']
    assert before == read(engine)
    context(engine)
    zero = read(engine)
    assert zero['projection_basis_ready'] and zero['aggregate_blockers'] == []
    asset = capital(engine)
    one = read(engine)
    assert one['covered_source_count'] == 1 and not one['projection_basis_ready']
    assert one['projection_basis_admission_fingerprint'] != zero['projection_basis_admission_fingerprint']
    save(engine, asset, payload(engine, asset))
    assert read(engine)['projection_basis_ready']


@pytest.mark.parametrize('change', ['base','target','amount','valuation','unrelated'])
def test_separate_fingerprints_and_staleness(engine, change):
    context(engine); asset = capital(engine)
    save(engine, asset, payload(engine, asset, annual_rate='0.07'))
    before = read(engine); old = before['covered_capital_sources'][0]
    if change == 'target': save_target(engine, target_payload(engine, date(2031,1,1)))
    elif change == 'base':
        with Session(engine) as db, db.begin():
            planning.set_base_date(db,1,BaseDateDecision(expected_version=before['decision_version'],planning_base_date=date(2029,1,1)))
    elif change == 'unrelated': income(engine)
    else:
        with Session(engine) as db, db.begin():
            row=db.get(CapitalAsset,asset)
            if change == 'amount': row.known_value_amount=Decimal('101.01')
            else: row.value_as_of_date=date(2021,1,1)
    after=read(engine); new=after['covered_capital_sources'][0]
    assert new['annual_rate']=='0.07'
    assert old['projection_basis_decision_fingerprint']==new['projection_basis_decision_fingerprint']
    assert old['projection_basis_decision']==new['projection_basis_decision']
    assert old['projection_basis_source_admission_fingerprint'] != new['projection_basis_source_admission_fingerprint']
    assert (old['source_semantic_fingerprint'] != new['source_semantic_fingerprint']) == (change in ('amount','valuation'))
    assert (old['projection_timing_context_fingerprint'] != new['projection_timing_context_fingerprint']) == (change in ('base','target'))
    if change=='unrelated': assert new['projection_basis_source_readiness']
    else:
        assert not new['projection_basis_source_readiness']
        assert ('TIMING_CONTEXT_CHANGED_SINCE_DECISION' if change in ('base','target') else 'SOURCE_STATE_CHANGED_SINCE_DECISION') in new['blockers']
    save(engine, asset, payload(engine, asset, annual_rate='0.07'))
    assert read(engine)['projection_basis_ready']


def test_identical_decisions_share_fingerprint_but_sources_remain_distinct(engine):
    context(engine)
    first = capital(engine)
    second = capital(engine, known_value_amount=Decimal('250.25'), value_as_of_date=date(2021,1,1))
    for asset in (first, second):
        save(engine, asset, payload(engine, asset, annual_rate='0.07'))
    current = read(engine)
    sources = current['covered_capital_sources']
    assert current['covered_source_count'] == 2 and current['projection_basis_ready']
    assert [s['source_id'] for s in sources] == sorted([f'capital:{first}', f'capital:{second}'])
    expected_decision = planning.fingerprint(dict(contract=basis.CONTRACT, annual_rate='0.07',
        return_basis='NET', price_basis='NOMINAL', compounding_convention='ANNUAL_EFFECTIVE',
        day_count_convention='ACTUAL_365_25'))
    assert all(s['projection_basis_decision_fingerprint'] == expected_decision for s in sources)
    assert sources[0]['source_semantic_fingerprint'] != sources[1]['source_semantic_fingerprint']
    assert sources[0]['projection_basis_source_admission_fingerprint'] != sources[1]['projection_basis_source_admission_fingerprint']
    envelope = dict(contract=basis.CONTRACT,
        planning_calculation_input_fingerprint=current['planning_calculation_input_fingerprint'],
        covered_source_count=2,
        sources=[dict(source_id=s['source_id'], admission=s['projection_basis_source_admission_fingerprint']) for s in sources],
        ready=True, blockers=[])
    assert current['projection_basis_admission_fingerprint'] == planning.fingerprint(envelope)
    for retained in envelope['sources']:
        collapsed = dict(envelope, covered_source_count=1, sources=[retained])
        assert current['projection_basis_admission_fingerprint'] != planning.fingerprint(collapsed)
    plan = plan_view(engine)
    plan['capital_inputs'].reverse()
    with Session(engine) as db:
        assert basis.derive(db, 1, plan)['projection_basis_admission_fingerprint'] == current['projection_basis_admission_fingerprint']


@pytest.mark.parametrize('field,value', [
    ('source_id', 'capital:999'), ('client_id', 999), ('capital_asset_id', 999),
])
def test_decision_fingerprint_excludes_source_identity(field, value):
    decision = dict(source_id='capital:1', client_id=1, capital_asset_id=1,
        annual_rate='0.07', return_basis='NET', price_basis='NOMINAL')
    assert basis.decision_fingerprint(decision) == basis.decision_fingerprint(dict(decision, **{field:value}))


@pytest.mark.parametrize('field,value', [
    ('actor', 'different server actor'),
    ('decided_at', datetime(2000,1,1,tzinfo=timezone.utc)),
    ('planning_calculation_input_fingerprint_at_decision', 'f'*64),
])
def test_each_metadata_field_excluded_from_decision_fingerprint(engine, field, value):
    context(engine); asset = capital(engine)
    save(engine, asset, payload(engine, asset))
    before = read(engine)
    with Session(engine) as db, db.begin():
        setattr(db.get(Decision, asset), field, value)
    after = read(engine)
    old, new = before['covered_capital_sources'][0], after['covered_capital_sources'][0]
    assert old['projection_basis_decision'][field] != new['projection_basis_decision'][field]
    for key in ('projection_basis_decision_fingerprint', 'source_semantic_fingerprint',
        'projection_timing_context_fingerprint', 'projection_basis_source_admission_fingerprint'):
        assert old[key] == new[key]
    assert before['projection_basis_admission_fingerprint'] == after['projection_basis_admission_fingerprint']
    assert after['projection_basis_ready']


@pytest.mark.parametrize('field,value', [
    ('annual_rate', '0.08'), ('return_basis', 'GROSS'), ('price_basis', 'REAL'),
    ('CONTRACT', 'test-contract-v2'), ('COMPOUNDING', 'test-compounding'), ('DAY_COUNT', 'test-day-count'),
])
def test_decision_fingerprint_retains_all_professional_fields(monkeypatch, field, value):
    decision = dict(annual_rate='0.07', return_basis='NET', price_basis='NOMINAL')
    before = basis.decision_fingerprint(decision)
    if field in decision:
        decision[field] = value
    else:
        monkeypatch.setattr(basis, field, value)
    assert basis.decision_fingerprint(decision) != before


def test_metadata_excluded_and_clear_stale_recreate(engine):
    context(engine); asset=capital(engine)
    save(engine,asset,payload(engine,asset))
    before=read(engine)
    with Session(engine) as db, db.begin():
        row=db.get(Decision,asset)
        row.actor='different server actor'; row.decided_at=datetime(2000,1,1,tzinfo=timezone.utc)
        row.planning_calculation_input_fingerprint_at_decision='f'*64
        db.get(PlanningInputDecision,1).version+=1
    after=read(engine)
    assert before['projection_basis_admission_fingerprint']==after['projection_basis_admission_fingerprint']
    stale=payload(engine,asset)
    save(engine,asset,ProjectionExpectations(**expectations(after,asset)),clear=True)
    cleared=read(engine)
    assert cleared['decision_version']==after['decision_version']+1
    assert cleared['covered_capital_sources'][0]['annual_rate'] is None
    assert not cleared['projection_basis_ready']
    with pytest.raises(PensionProductError) as error: save(engine,asset,stale)
    assert error.value.code=='PLANNING_DECISION_STALE'
    with Session(engine) as db: assert db.get(CapitalAsset,asset).known_value_amount==Decimal('100.00')


@pytest.mark.parametrize('field,code', [
    ('expected_version','PLANNING_DECISION_STALE'),
    ('expected_source_semantic_fingerprint','PROJECTION_SOURCE_STATE_STALE'),
    ('expected_timing_context_fingerprint','PROJECTION_TIMING_CONTEXT_STALE'),
    ('expected_planning_calculation_input_fingerprint','PROJECTION_PLANNING_INPUT_STALE')])
def test_stale_expectations_before_mutation(engine,field,code):
    context(engine); asset=capital(engine)
    before=read(engine)
    request=payload(engine,asset,**{field:999 if field=='expected_version' else 'f'*64})
    with pytest.raises(PensionProductError) as error: save(engine,asset,request)
    assert error.value.code==code
    assert read(engine)==before


def test_noncurrent_decisions_historical_never_rebound(engine):
    context(engine); asset=capital(engine)
    save(engine,asset,payload(engine,asset))
    with Session(engine) as db, db.begin(): db.get(CapitalAsset,asset).lifecycle_status='superseded'
    result=read(engine)
    assert result['covered_source_count']==0 and result['projection_basis_ready']
    assert result['noncurrent_or_historical_bound_decisions'][0]['source_id']==f'capital:{asset}'
    new=capital(engine)
    assert read(engine)['covered_capital_sources'][0]['projection_basis_decision'] is None
    with pytest.raises(PensionProductError) as error: save(engine,asset,payload(engine,new))
    assert error.value.code=='SOURCE_NOT_ELIGIBLE'
    with pytest.raises(IntegrityError):
        with Session(engine) as db, db.begin(): db.delete(db.get(CapitalAsset,asset))


def test_structural_integrity_order_and_cross_client(engine):
    context(engine); a=capital(engine); b=capital(engine); foreign=capital(engine,client_id=2)
    with pytest.raises(PensionProductError) as error: save(engine,foreign,payload(engine,a))
    assert error.value.code=='SOURCE_NOT_ELIGIBLE'
    plan=plan_view(engine)
    with Session(engine) as db:
        assets=db.scalars(select(CapitalAsset).where(CapitalAsset.client_id==1)).all()
        first=basis.covered_capital_source_registry(plan,assets,1)
        reversed_plan=copy.deepcopy(plan); reversed_plan['capital_inputs'].reverse()
        assert first==basis.covered_capital_source_registry(reversed_plan,list(reversed(assets)),1)
        for bad in ([plan['capital_inputs'][0]]*2, [], [dict(plan['capital_inputs'][0],client_id=2),plan['capital_inputs'][1]]):
            malformed=copy.deepcopy(plan); malformed['capital_inputs']=bad
            with pytest.raises(PensionProductError) as error: basis.covered_capital_source_registry(malformed,assets,1)
            assert error.value.code=='PROJECTION_COVERAGE_STRUCTURE_INVALID'
    save(engine,a,payload(engine,a))
    with engine.begin() as db: db.execute(text('UPDATE capital_projection_basis_decisions SET client_id=2 WHERE capital_asset_id=:id'),{'id':a})
    for client in (1,2):
        with pytest.raises(PensionProductError) as error: read(engine,client)
        assert error.value.code=='PROJECTION_COVERAGE_STRUCTURE_INVALID'


def test_sqlite_snapshot_lock_and_rollback(engine):
    context(engine); asset=capital(engine); request=payload(engine,asset); before=read(engine)
    statements=[]
    def capture(conn,cursor,sql,*args): statements.append(sql.strip().upper())
    event.listen(engine,'before_cursor_execute',capture)
    other=create_engine(engine.url,connect_args={'timeout':0.01})
    try:
        with Session(engine) as db:
            basis.write(db,1,asset,request)
            with pytest.raises(OperationalError):
                with other.begin() as connection: connection.execute(text('UPDATE capital_asset SET known_value_amount=200 WHERE id=:id'),{'id':asset})
            db.rollback()
        assert statements[0]=='BEGIN IMMEDIATE'
        assert read(engine)==before
        with engine.connect() as locked:
            locked.exec_driver_sql('BEGIN IMMEDIATE')
            with pytest.raises(OperationalError): save(other,asset,request)
            locked.rollback()
        assert read(engine)==before
    finally:
        other.dispose(); event.remove(engine,'before_cursor_execute',capture)


def test_api_read_write_clear_and_no_calculation(engine):
    context(engine); asset=capital(engine)
    def session():
        with Session(engine) as db: yield db
    app.dependency_overrides[get_db]=session
    try:
        with TestClient(app) as client:
            path='/api/clients/1/retirement-planning-input'
            plan=client.get(path).json()
            assert plan['projection_basis']==client.get(path+'/projection-basis').json()
            request=payload(engine,asset).model_dump(mode='json')
            for extra in ('actor','provenance','capital_asset_id','client_id'):
                assert client.put(path+f'/projection-basis/{asset}',json=request|{extra:'forbidden'}).status_code==422
            assert client.put(path+f'/projection-basis/{asset}',json=request).status_code==200
            current=read(engine)
            assert client.put(path+f'/projection-basis/{asset}/clear',json=expectations(current,asset)).status_code==200
    finally: app.dependency_overrides.clear()
    source=inspect.getsource(basis)
    for forbidden in ('PensionHolding','PlannerAssumption','m06_','m09_','m10_','date.today','timedelta','**','pow('):
        assert forbidden not in source
    for key in ('future_value','projection_factor','projected_amount','npv','pension_amount','scenario_result'):
        assert key not in str(read(engine))


def test_sqlite_projection_migration(tmp_path):
    from test_projection_basis_postgresql import migration_contract
    migration_contract('sqlite:///'+(tmp_path/'projection.db').as_posix())


def test_canonical_capital_destination_included_other_families_excluded(engine):
    from test_canonical_component_conversion import seeded, request
    from app.services.canonical_component_conversion_service import execute
    from app.services.canonical_manual_pension_service import create
    from test_professional_source_snapshot import facts
    source=seeded(engine)
    with Session(engine) as db, db.begin():
        execute(db,1,request(source),'test')
        create(db,1,facts())
    income(engine)
    result=read(engine)
    assert result['covered_source_count']==1
    assert result['covered_capital_sources'][0]['source_id'].startswith('capital:')
    assert result['covered_capital_sources'][0]['annual_rate'] is None
    assert not result['projection_basis_ready']


def test_sqlite_read_snapshot_includes_decision_and_source(engine):
    from test_projection_basis_postgresql import test_pg_repeatable_read_contains_source_and_decision
    with engine.connect() as db: db.exec_driver_sql('PRAGMA journal_mode=WAL')
    test_pg_repeatable_read_contains_source_and_decision(engine)


def test_missing_planning_context_still_allows_explicit_blocked_decision(engine):
    asset=capital(engine)
    before=plan_view(engine)
    save(engine,asset,payload(engine,asset))
    after=plan_view(engine)
    assert after['decision_version']==1
    assert after['planning_calculation_input_fingerprint']==before['planning_calculation_input_fingerprint']
    assert after['planning_input_fingerprint']==before['planning_input_fingerprint']
    result=read(engine)
    assert result['covered_source_count']==1
    assert result['covered_capital_sources'][0]['annual_rate']=='0'
    assert result['aggregate_blockers']==['PLANNING_OR_TARGET_NOT_READY']
