import copy
import json
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
import pytest
from sqlalchemy import select, event
from sqlalchemy.orm import Session
from app.models.canonical_manual_pension_source import CanonicalManualPensionSource as Manual
from app.models.canonical_conversion import batches, conversions, pensions, allocations
from app.models.pension_product import PensionProductAuditEvent
from app.schemas.canonical_manual_pension_source import ManualPensionInput, ManualPensionUpdate
from app.services import pension_monthly_basis_service as basis
from app.services import canonical_manual_pension_service as manual
from app.services.pension_product_service import PensionProductError
from app.services.canonical_component_conversion_service import execute
from test_recovery_pension_products import engine
from test_professional_source_snapshot import read, facts
from test_canonical_component_conversion import seeded, request
from pension_basis_golden import PROVENANCE_BYTES, SOURCE_BYTES


@pytest.mark.parametrize('kind,representation,day,digest', [
 ('entered_monthly_amount', {'representation_kind':'exact_money','amount':'1234.50'}, '2026-09-01', '292af055cb492cbc5038e1338ccaf9bd6baf4554e9f7f82ee5264531bd2b1e1a'),
 ('manual_balance_ratio', {'representation_kind':'exact_ratio','numerator':'200000.00','denominator':'200'}, '2026-09-01', '7f8ca90b48f06bab33fc545f2482be43d5c24d84b642cefab88d267c54a60870'),
 ('persisted_conversion_ratio', {'representation_kind':'exact_ratio','numerator':'40.00','denominator':'209.35'}, '2026-09-11', '7001931c1374e6c5ae3847fb4e9449a32e6695fc325790a9f42ece5c79f5fd70'),
])
def test_semantic_goldens(kind, representation, day, digest):
    assert basis.semantic(kind,representation,day)==digest


def test_canonical_bytes_and_exact_format():
    assert basis.canonical_bytes({'z':'\n\t\b\r\f\x00/"\\','א':True,'a':None}) == '{"a":null,"z":"\\u000a\\u0009\\u0008\\u000d\\u000c\\u0000/\\"\\\\","א":true}'.encode()
    assert basis.factor('2.000E2')=='200'
    assert basis.factor('-0.00')=='0'
    assert basis.money('1.2300')=='1.23'
    for value in (1.23, Decimal('1.231'), 'NaN'):
        with pytest.raises((ValueError, ArithmeticError)): basis.money(value)
    with pytest.raises(ValueError): basis.canonical_bytes({'float':1.0})


def golden_arguments():
    fixture=json.loads(PROVENANCE_BYTES)
    b,c,p=fixture['batch'],fixture['conversion'],fixture['destination']
    for row in (b,c,p): row['client_id']=4242
    b['effective_date']=date.fromisoformat(b['effective_date'])
    p['effective_date']=date.fromisoformat(p['effective_date'])
    p['pension_start_date']=date.fromisoformat(p['pension_start_date'])
    e=fixture['audit_event']
    event=SimpleNamespace(event_id=e['event_id'],version=e['event_version'],actor=e['actor'],action=e['action'],
        client_id=e['client_id'],product_id=e['product_id'],snapshot={'operation':{'batch_id':e['operation_batch_id']},'statement_date':e['source_statement_date']})
    return b,c,p,fixture['allocations'],event


def test_conversion_golden_exact_bytes_and_identity_layers():
    b,c,p,a,e=golden_arguments()
    db=AuditSession([e])
    result=basis.conversion(db,4242,b,c,p,a)
    assert basis.canonical_bytes(result['provenance'])==PROVENANCE_BYTES
    assert len(PROVENANCE_BYTES)==1938
    assert basis.fingerprint(result['provenance'])=='eb1ac40770f2b2be0d674f9487789f5c1dd8e8f42e5858befea0f8d6d4e8ef85'
    source=json.loads(SOURCE_BYTES)
    assert basis.canonical_bytes(source)==SOURCE_BYTES and len(SOURCE_BYTES)==408
    assert result['base_amount_source_fingerprint']==basis.fingerprint(source)=='b663db23e08da7c762ba83b75dfa096e8a62eee1cb76e1ab628e45b8436752eb'
    p['coefficient_source_keys']=dict(reversed(list(p['coefficient_source_keys'].items())))
    assert basis.conversion(db,4242,b,c,p,list(reversed(a)))==result
    for row,key in ((c,'version'),(p,'version')):
        row[key]+=1
        modified=basis.conversion(db,4242,b,c,p,a)
        assert modified['base_amount_semantic_fingerprint']==result['base_amount_semantic_fingerprint']
        assert modified['base_amount_source_fingerprint']!=result['base_amount_source_fingerprint']
        row[key]-=1
    e.version+=1
    modified=basis.conversion(db,4242,b,c,p,a)
    assert modified['provenance']['audit_event']['event_version']==5
    assert modified['base_amount_source_fingerprint']!=result['base_amount_source_fingerprint']
    assert modified['base_amount_semantic_fingerprint']==result['base_amount_semantic_fingerprint']


def test_conversion_actor_and_technical_timestamps_stay_out_of_amount_semantics():
    b, c, p, a, e = golden_arguments()
    db = AuditSession([e])
    before = basis.conversion(db, 4242, b, c, p, a)
    e.created_at = '2099-01-01T00:00:00Z'
    for row in (b, c, p):
        row['created_at'] = '2099-01-01T00:00:00Z'
        row['updated_at'] = '2099-01-02T00:00:00Z'
    assert basis.conversion(db, 4242, b, c, p, a) == before
    e.actor = 'other actor'
    after = basis.conversion(db, 4242, b, c, p, a)
    assert after['base_amount_semantic_fingerprint'] == before['base_amount_semantic_fingerprint']
    assert after['base_amount_source_fingerprint'] != before['base_amount_source_fingerprint']
    e.snapshot['statement_date'] = '2025-01-01'
    p['pension_start_date'] = date(2040, 1, 1)
    assert basis.conversion(db, 4242, b, c, p, a)['base_amount_semantic_fingerprint'] == before['base_amount_semantic_fingerprint']


@pytest.mark.parametrize('mode',['entered','calculated'])
def test_tristate_persistence(engine,mode):
    data=dict(input_mode=mode,payer_name='משלם',pension_start_date='2040-01-01',tax_treatment='taxable',indexation_method='none')
    data.update(dict(monthly_amount='1234.50') if mode=='entered' else dict(balance='200000.00',annuity_factor='200.00'))
    with Session(engine) as db,db.begin(): row=manual.create(db,1,ManualPensionInput(**data))
    sid=row['manual_pension_source_id']
    def current(): return next(s for s in read(engine)['pension_sources'] if s['source_id']=='manual:'+sid)['monthly_amount_basis']
    assert not current()['basis_authority_ready']
    assert current()['base_amount_semantic_fingerprint'] is None
    assert len(current()['base_amount_source_fingerprint'])==64
    version=1
    for change,expected in [({'base_amount_effective_date':'2026-09-01'},'2026-09-01'),
        ({'description':'unrelated'},'2026-09-01'),
        ({'monthly_amount':'2000.00'} if mode=='entered' else {'balance':'123.45'},'2026-09-01'),
        ({'base_amount_effective_date':None},None),({'base_amount_effective_date':'2025-01-01'},'2025-01-01')]:
        with Session(engine) as db,db.begin():
            manual.change(db,1,sid,ManualPensionUpdate(**(data|change),expected_version=version))
        version+=1
        value=current()
        assert value['base_amount_effective_date']==expected
        assert value['basis_authority_ready']==(expected is not None)
        assert value['pension_start_date']=='2040-01-01'
    with Session(engine) as db:
        with pytest.raises(PensionProductError): manual.change(db,1,sid,ManualPensionUpdate(**data,expected_version=1))


def test_manual_identity_and_incomplete_semantics(engine):
    with Session(engine) as db,db.begin():
        for _ in range(2): manual.create(db,1,facts(base_amount_effective_date=date(2026,9,1)))
    items=[s['monthly_amount_basis'] for s in read(engine)['pension_sources']]
    assert items[0]['base_amount_semantic_fingerprint']==items[1]['base_amount_semantic_fingerprint']
    assert items[0]['base_amount_source_fingerprint']!=items[1]['base_amount_source_fingerprint']
    assert basis.registry(1,items)==basis.registry(1,list(reversed(items)))
    with pytest.raises(PensionProductError): basis.registry(1,items+[items[0]])
    with Session(engine) as db:
        m=db.scalars(select(Manual)).first()
        original=basis.manual(m,1)
        m.pension_start_date=date(2050,1,1); m.source_note='new'; m.version+=1
        changed=basis.manual(m,1)
        assert original['base_amount_semantic_fingerprint']==changed['base_amount_semantic_fingerprint']
        assert original['base_amount_source_fingerprint']!=changed['base_amount_source_fingerprint']
        m.base_amount_effective_date=None
        assert basis.manual(m,1)['base_amount_semantic_fingerprint'] is None


def conversion_arguments(engine):
    product=seeded(engine)
    with Session(engine) as db,db.begin(): execute(db,1,request(product,amount='40.00',destination='pension'), 'basis-test')
    with Session(engine) as db:
        b=dict(db.execute(select(batches)).mappings().one())
        c=dict(db.execute(select(conversions)).mappings().one())
        p=dict(db.execute(select(pensions)).mappings().one())
        a=[dict(r) for r in db.execute(select(allocations)).mappings()]
        e=db.scalars(select(PensionProductAuditEvent).where(PensionProductAuditEvent.action=='conversion')).one()
        audit=SimpleNamespace(**{k:getattr(e,k) for k in ('event_id','version','action','actor','client_id','product_id','snapshot')})
    return b,c,p,a,audit


class AuditSession:
    def __init__(self,events): self.events=events
    def scalars(self,query): return self
    def all(self): return self.events


@pytest.mark.parametrize('state',['value','null','zero','multiple','missing','invalid'])
def test_audit_cardinality_and_date_boundary(engine,state):
    b,c,p,a,e=conversion_arguments(engine)
    e.snapshot=copy.deepcopy(e.snapshot)
    e.snapshot['statement_date']='2026-08-31'
    events=[e]
    if state=='null': e.snapshot['statement_date']=None
    if state=='zero': events=[]
    if state=='multiple': events=[e,e]
    if state=='missing': del e.snapshot['statement_date']
    if state=='invalid': e.snapshot['statement_date']='bad'
    if state in ('value','null'):
        result=basis.conversion(AuditSession(events),1,b,c,p,a)
        assert result['base_amount_effective_date']==b['effective_date'].isoformat()
        assert result['source_statement_date']==e.snapshot['statement_date']
        assert result['provenance']['audit_event']['statement_date_evidence_state']==('MATCHED_VALUE' if state=='value' else 'MATCHED_NULL')
        assert result['provenance']['audit_event']['event_version']==e.version
        assert result['base_amount_representation']['numerator']=='40.00'
    else:
        with pytest.raises(PensionProductError) as error: basis.conversion(AuditSession(events),1,b,c,p,a)
        assert error.value.code=='BASIS_CONVERSION_PROVENANCE_INVALID'


def test_conversion_date_integrity_and_metadata(engine):
    b,c,p,a,e=conversion_arguments(engine)
    db=AuditSession([e]); result=basis.conversion(db,1,b,c,p,a)
    p['monthly_display_amount']='999.00'
    assert basis.conversion(db,1,b,c,p,a)==result
    p['version']+=1
    assert basis.conversion(db,1,b,c,p,a)['base_amount_source_fingerprint']!=result['base_amount_source_fingerprint']
    p['effective_date']=date(1900,1,1)
    with pytest.raises(PensionProductError) as error: basis.conversion(db,1,b,c,p,a)
    assert error.value.code=='CONVERSION_EFFECTIVE_DATE_MISMATCH'


@pytest.mark.parametrize('mode', ['entered', 'calculated'])
@pytest.mark.parametrize('creation_date', [{}, {'base_amount_effective_date': None}])
def test_api_date_presence_survives_request_validation_and_reload(engine, mode, creation_date):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.db.session import get_db

    def session():
        with Session(engine) as db:
            yield db

    data = dict(input_mode=mode, payer_name='משלם', pension_start_date='2040-01-01',
                tax_treatment='taxable', indexation_method='none')
    data.update(dict(monthly_amount='1234.50') if mode == 'entered' else
                dict(balance='1.00', annuity_factor='3'))
    root = '/api/clients/1/canonical-pension-sources/manual'
    app.dependency_overrides[get_db] = session
    try:
        with TestClient(app) as client:
            response = client.post(root, json=data | creation_date)
            assert response.status_code == 200, response.text
            sid = response.json()['manual_pension_source_id']
            assert response.json()['base_amount_effective_date'] is None
            updates = [({'base_amount_effective_date': '2026-09-01'}, '2026-09-01'),
                       ({'description': 'unrelated'}, '2026-09-01'),
                       ({'base_amount_effective_date': None}, None),
                       ({'base_amount_effective_date': '2040-01-01'}, '2040-01-01')]
            for version, (change, expected) in enumerate(updates, 1):
                response = client.put(root + '/' + sid,
                                      json=data | change | {'expected_version': version})
                assert response.status_code == 200, response.text
                assert response.json()['base_amount_effective_date'] == expected
                view = client.get('/api/clients/1/professional-source-snapshot')
                assert view.status_code == 200, view.text
                source = next(s for s in view.json()['pension_sources']
                              if s['source_id'] == 'manual:' + sid)
                authority = source['monthly_amount_basis']
                assert authority['base_amount_effective_date'] == expected
                assert authority['pension_start_date'] == '2040-01-01'
                assert authority['basis_authority_ready'] == (expected is not None)
                assert authority['basis_blockers'] == ([] if expected else
                                                      ['BASE_AMOUNT_EFFECTIVE_DATE_MISSING'])
                if mode == 'calculated':
                    assert authority['base_amount_representation'] == {
                        'representation_kind': 'exact_ratio', 'numerator': '1.00', 'denominator': '3'}
                    assert source['monthly_amount'] is None
            stale = client.put(root + '/' + sid, json=data | {'expected_version': 1})
            assert stale.status_code == 409
            with Session(engine) as db:
                persisted = db.get(Manual, sid)
                assert persisted.base_amount_effective_date == date(2040, 1, 1)
                assert persisted.version == 5
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize('mode,changes,code', [
    ('entered', {'monthly_amount': None}, 'ENTERED_MONTHLY_AMOUNT_MISSING'),
    ('entered', {'monthly_amount': Decimal('0.00')}, 'ENTERED_MONTHLY_AMOUNT_NOT_POSITIVE'),
    ('calculated', {'balance': None}, 'MANUAL_BALANCE_MISSING'),
    ('calculated', {'balance': Decimal('0.00')}, 'MANUAL_BALANCE_NOT_POSITIVE'),
    ('calculated', {'annuity_factor': None}, 'MANUAL_ANNUITY_FACTOR_MISSING'),
    ('calculated', {'annuity_factor': '0'}, 'MANUAL_ANNUITY_FACTOR_NOT_POSITIVE'),
    ('calculated', {'annuity_factor': '-1'}, 'MANUAL_ANNUITY_FACTOR_NOT_POSITIVE'),
    ('calculated', {'annuity_factor': 'NaN'}, 'MANUAL_ANNUITY_FACTOR_INVALID'),
    ('calculated', {'annuity_factor': 'invalid'}, 'MANUAL_ANNUITY_FACTOR_INVALID'),
])
def test_incomplete_manual_facts_remain_visible_without_pseudo_semantics(mode, changes, code):
    # Read-boundary facts test: invalid historical data does not weaken write validators.
    values = dict.fromkeys(basis.MANUAL_FIELDS)
    values.update(input_mode=mode, base_amount_effective_date=date(2026, 9, 1))
    values.update(dict(monthly_amount=Decimal('1234.50')) if mode == 'entered' else
                  dict(balance=Decimal('1.00'), annuity_factor='3'))
    row = SimpleNamespace(**(values | changes), client_id=1, manual_pension_source_id='partial',
                          version=1, lifecycle_status='current')
    result = basis.manual(row, 1)
    assert result['basis_blockers'] == [code]
    assert not result['basis_authority_ready']
    assert result['base_amount_semantic_fingerprint'] is None
    assert len(result['base_amount_source_fingerprint']) == 64


def test_registry_binds_membership_readiness_and_deduplicated_blockers():
    source = dict(source_id='manual:a', base_amount_source_fingerprint='a' * 64,
                  basis_authority_ready=True, basis_blockers=[])
    initial = basis.registry(1, [source])
    assert initial != basis.registry(1, [])
    assert initial != basis.registry(1, [source, source | {'source_id': 'manual:b'}])
    assert initial != basis.registry(1, [source | {'basis_authority_ready': False}])
    assert initial != basis.registry(1, [source | {'basis_blockers': ['B']}])
    assert basis.registry(1, [source | {'basis_blockers': ['B', 'A', 'B']}]) == \
        basis.registry(1, [source | {'basis_blockers': ['A', 'B']}])


def migration_contract(url):
    from sqlalchemy import create_engine, inspect, text
    from test_canonical_conversion_migration import migrate
    migrate(url, 'upgrade', 'd9e5a2b8c076')
    db_engine = create_engine(url)
    try:
        with db_engine.begin() as db:
            db.execute(text("INSERT INTO clients(client_id,display_name,id_number) VALUES(1,'test','123')"))
            db.execute(text("INSERT INTO canonical_manual_pension_sources "
                "(manual_pension_source_id,client_id,input_mode,monthly_amount,pension_start_date) "
                "VALUES('legacy',1,'entered',1234.50,'2040-01-01')"))
        with db_engine.connect() as db:
            before = dict(db.execute(text('SELECT * FROM canonical_manual_pension_sources')).mappings().one())
        tables = set(inspect(db_engine).get_table_names())
        migrate(url, 'upgrade', 'e0f6b3c9d187')
        assert set(inspect(db_engine).get_table_names()) == tables
        column = next(c for c in inspect(db_engine).get_columns('canonical_manual_pension_sources')
                      if c['name'] == 'base_amount_effective_date')
        assert column['nullable'] and column['default'] is None
        assert str(column['type']) == 'DATE'
        with db_engine.connect() as db:
            after = dict(db.execute(text('SELECT * FROM canonical_manual_pension_sources')).mappings().one())
        assert after.pop('base_amount_effective_date') is None
        assert after == before
        migrate(url, 'downgrade', 'd9e5a2b8c076')
        with db_engine.connect() as db:
            assert dict(db.execute(text('SELECT * FROM canonical_manual_pension_sources')).mappings().one()) == before
        migrate(url, 'upgrade', 'e0f6b3c9d187')
        with Session(db_engine) as db, db.begin():
            db.get(Manual, 'legacy').base_amount_effective_date = date(2026, 9, 1)
        failure = migrate(url, 'downgrade', 'd9e5a2b8c076', success=False)
        assert 'PENSION_BASIS_DOWNGRADE_WOULD_LOSE_DATES' in failure
        with Session(db_engine) as db:
            row = db.get(Manual, 'legacy')
            assert row.base_amount_effective_date == date(2026, 9, 1)
            assert row.monthly_amount == Decimal('1234.50')
            assert row.pension_start_date == date(2040, 1, 1)
        with db_engine.connect() as db:
            assert db.scalar(text('SELECT version_num FROM alembic_version')) == 'e0f6b3c9d187'
    finally:
        db_engine.dispose()


def test_sqlite_additive_migration_and_lossless_downgrade_guard(tmp_path):
    migration_contract('sqlite:///' + (tmp_path / 'basis.db').as_posix())


def test_snapshot_planning_preserve_basis_without_writes_or_target_inference(engine):
    from test_planning_input import choose, view
    choose(engine)
    with Session(engine) as db, db.begin():
        row = manual.create(db, 1, facts(base_amount_effective_date=None))
    initial = view(engine)
    assert not initial['planning_input_ready']
    assert {'source_id': 'manual:' + row['manual_pension_source_id'],
            'code': 'BASE_AMOUNT_EFFECTIVE_DATE_MISSING'} in initial['blocking_facts']
    with Session(engine) as db, db.begin():
        manual.change(db, 1, row['manual_pension_source_id'], ManualPensionUpdate(
            **facts(base_amount_effective_date=date(2090, 9, 1)).model_dump(), expected_version=1))
    statements = []
    def capture(conn, cursor, sql, params, context, many):
        statements.append(sql.strip().upper())
    event.listen(engine, 'before_cursor_execute', capture)
    try:
        snapshot = read(engine)
        result = view(engine)
        assert result == view(engine)
    finally:
        event.remove(engine, 'before_cursor_execute', capture)
    authority = snapshot['pension_sources'][0]['monthly_amount_basis']
    assert result['pension_inputs'][0]['monthly_amount_basis'] == authority
    assert result['pension_monthly_amount_basis_fingerprint'] == snapshot['pension_monthly_amount_basis_fingerprint']
    assert result['planning_input_ready']
    assert result['pension_inputs'][0]['applicability'] == 'future_start'
    assert all(f['field'] != 'base_amount_effective_date' for f in result['date_candidates'])
    assert all(f['source_field'] != 'base_amount_effective_date' for f in result['target_reference_facts'])
    assert statements and all(sql.startswith(('SELECT', 'BEGIN')) or
        (engine.dialect.name == 'postgresql' and
         sql == 'SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY') for sql in statements)


def test_real_audit_selection_requires_action_client_product_and_batch(engine):
    b, c, p, a, original = conversion_arguments(engine)
    with Session(engine) as db:
        baseline = basis.conversion(db, 1, b, c, p, a)
    for key, value in [('action', 'update'), ('client_id', 2), ('product_id', 'other-product'), ('batch_id', 'other-batch')]:
        values = {k: getattr(original, k) for k in ('action', 'actor', 'client_id', 'product_id', 'version')}
        snapshot = copy.deepcopy(original.snapshot)
        if key == 'batch_id': snapshot['operation']['batch_id'] = value
        else: values[key] = value
        with Session(engine) as db, db.begin():
            db.add(PensionProductAuditEvent(event_id='unmatched-' + key, snapshot=snapshot, **values))
    with Session(engine) as db:
        assert basis.conversion(db, 1, b, c, p, a) == baseline
    with Session(engine) as db, db.begin():
        db.add(PensionProductAuditEvent(event_id='duplicate', snapshot=copy.deepcopy(original.snapshot),
            **{k: getattr(original, k) for k in ('action', 'actor', 'client_id', 'product_id', 'version')}))
    with Session(engine) as db:
        with pytest.raises(PensionProductError) as error:
            basis.conversion(db, 1, b, c, p, a)
        assert error.value.code == 'BASIS_CONVERSION_PROVENANCE_INVALID'


def test_database_roundtrip_produces_exact_conversion_golden_bytes(engine):
    from sqlalchemy import Table, Column, MetaData, JSON, Date, String
    from app.models.client import Client
    from app.models.pension_product import ExactMoney
    # Synthetic typed storage isolates cross-dialect serialization from random conversion IDs.
    fixture = Table('basis_golden_inputs', MetaData(), Column('payload', JSON),
                    Column('effective_date', Date), Column('numerator', ExactMoney()),
                    Column('denominator', String(128)))
    fixture.create(engine)
    b, c, p, a, e = golden_arguments()
    with Session(engine) as db, db.begin():
        db.add(Client(client_id=4242, display_name='golden', id_number='4242'))
        db.flush()
        db.add(PensionProductAuditEvent(event_id=e.event_id, client_id=4242, product_id=e.product_id,
            action=e.action, version=e.version, actor=e.actor, snapshot=e.snapshot))
        db.execute(fixture.insert().values(payload=json.loads(PROVENANCE_BYTES),
            effective_date=date(2026, 9, 11), numerator=Decimal('40.00'), denominator='209.35'))
    with Session(engine) as db:
        stored = db.execute(select(fixture)).mappings().one()
        data = stored['payload']
        b, c, p = data['batch'], data['conversion'], data['destination']
        for row in (b, c, p): row['client_id'] = 4242
        b['effective_date'] = p['effective_date'] = stored['effective_date']
        p['pension_start_date'] = date.fromisoformat(p['pension_start_date'])
        p['monthly_numerator'] = stored['numerator']
        p['monthly_denominator'] = stored['denominator']
        result = basis.conversion(db, 4242, b, c, p, list(reversed(data['allocations'])))
    assert basis.canonical_bytes(result['provenance']) == PROVENANCE_BYTES
    assert basis.fingerprint(result['provenance']) == 'eb1ac40770f2b2be0d674f9487789f5c1dd8e8f42e5858befea0f8d6d4e8ef85'
    assert result['base_amount_source_fingerprint'] == 'b663db23e08da7c762ba83b75dfa096e8a62eee1cb76e1ab628e45b8436752eb'
