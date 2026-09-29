"""CPX acceptance: numerical oracle is certified by exact rational power inequalities."""
import copy
from datetime import date, datetime, timezone
from decimal import Decimal, localcontext, ROUND_DOWN, ROUND_UP
from fractions import Fraction
from math import gcd
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, event
from sqlalchemy.orm import Session
from app.main import app
from app.db.session import get_db
from app.db.base import Base
from app.models.retirement_facts import CapitalAsset
from app.models.capital_projection_basis import CapitalProjectionBasisDecision as Decision
from app.services import capital_projection_execution_numeric as num
from app.services import capital_projection_execution_service as run
from app.services import capital_projection_basis_service as basis
from app.services import planning_input_service as planning
from app.services.pension_product_service import PensionProductError
from test_recovery_pension_products import engine
from test_projection_basis import context, capital, payload, save
from test_retirement_target import payload as target_payload, save as save_target


GOLDENS = [
    ('100.00','0.07',1,'1.000185256441835912721330554738641','1.000185256441835912721330554738641E2'),
    ('100.00','-0.2',1,'9.993892528344145695353220857764381E-1','9.993892528344145695353220857764381E1'),
    ('123.45','0.03',365,'1.029979161356382560309690112308564','1.271509274694454270702312443644923E2'),
    ('123.45','0.03',366,'1.030062518460543838965856646655035','1.271612179039541369203350030295641E2'),
    ('98765.43','0.05',2001,'1.306424425030785336543433542181043','1.290295701006682770014069274699338E5'),
    ('100.00','-0.99999999999999999999',1,'8.81541950664984456600562381328999E-1','8.81541950664984456600562381328999E1'),
    ('999999999999999999.99','123456789',365,'1.218924034668949758732244602762924E8','1.218924034668949758720055362416235E26'),
    ('0.00','0.03',1,'1.000080930864709442706281419619957','0'),
    ('1.04','0.07',1,'1.000185256441835912721330554738641','1.040192666699509349230183776928186'),
]


def oracle_round(value):
    """Independent integer/rational nearest-even, not production canonicalizer."""
    value = Fraction(value)
    if not value: return '0'
    sign = '-' if value < 0 else ''
    value = abs(value)
    exponent = 0
    while value >= 10:
        value /= 10; exponent += 1
    while value < 1:
        value *= 10; exponent -= 1
    scaled = value * 10**33
    integer, remainder = divmod(scaled.numerator, scaled.denominator)
    if remainder * 2 > scaled.denominator or (remainder * 2 == scaled.denominator and integer % 2):
        integer += 1
    if integer == 10**34:
        integer //= 10; exponent += 1
    digits = str(integer).rstrip('0')
    return sign + digits[0] + ('.'+digits[1:] if len(digits)>1 else '') + (f'E{exponent}' if exponent else '')


def oracle_enclosure(rate, days):
    """Approximation proposes bounds; exact integer inequalities certify them.

    Unlike production's ln/exp-neighbour proof, certification here uses
    L**denominator < (1+r)**numerator < U**denominator, in Fraction arithmetic.
    This proof does not trust the approximation or production implementation.
    """
    divisor = gcd(days * 4, 1461)
    n, q = days * 4 // divisor, 1461 // divisor
    with localcontext() as ctx:
        ctx.prec = 140
        estimate = ((Decimal(1)+Decimal(rate)).ln()*Decimal(n)/Decimal(q)).exp()
        radius = Decimal((0, (1,), estimate.adjusted()-130))
        low, high = Fraction(estimate-radius), Fraction(estimate+radius)
    exact_power = (Fraction(1)+Fraction(rate))**n
    assert low**q < exact_power < high**q
    return low, high


@pytest.mark.parametrize('amount,rate,days,factor,projected', GOLDENS)
def test_golden_certified_independent_oracle(amount, rate, days, factor, projected):
    # AC001/003/004/005/006/024/025/033/034/035/039/055/056/057/058
    low, high = oracle_enclosure(rate, days)
    assert oracle_round(low) == oracle_round(high) == factor
    assert oracle_round(Fraction(amount)*low) == oracle_round(Fraction(amount)*high) == projected
    lo, hi = num.factor_enclosure(Decimal(rate), days, 80)
    assert Fraction(lo) <= low < high <= Fraction(hi)
    alo, ahi = num.amount_enclosure(Decimal(amount), lo, hi, 80)
    assert Fraction(alo) <= Fraction(amount)*low <= Fraction(amount)*high <= Fraction(ahi)
    assert num.canonical_decimal34(lo) == num.canonical_decimal34(hi) == factor
    assert num.canonical_decimal34(alo) == num.canonical_decimal34(ahi) == projected
    assert num.calculate(Decimal(amount), Decimal(rate), days) == (factor, projected)


def test_internal_factor_not_serialized_factor():
    a,r,d,f,p = GOLDENS[-1]
    assert oracle_round(Fraction(a)*Fraction(f)) != p
    assert num.calculate(Decimal(a),Decimal(r),d) == (f,p)


@pytest.mark.parametrize('value', ['0','-0','-0.000','1','100','123.4500','0.0100','-0.000975',
    '1234567890123456789012345678901234','12345678901234567890123456789012345',
    '12345678901234567890123456789012344.9999','12345678901234567890123456789012345.0001',
    '12345678901234567890123456789012355','9.9999999999999999999999999999999995'])
def test_c34_independent_half_even(value):
    # AC033/036/037/038/046/047/048
    with localcontext() as ctx:
        ctx.prec=2; ctx.rounding=ROUND_UP
        assert num.canonical_decimal34(Decimal(value)) == oracle_round(Fraction(value))


@pytest.mark.parametrize('amount,rate,days', [('123.45','0',365),('123.45','0.5',0)])
def test_exact_branches_no_transcendental(monkeypatch,amount,rate,days):
    def forbidden(*args): pytest.fail('Exact branch used transcendental')
    monkeypatch.setattr(num,'factor_enclosure',forbidden)
    assert num.calculate(Decimal(amount),Decimal(rate),days)==('1','1.2345E2')


def test_zero_amount_factor_not_shortcut():
    assert num.amount_enclosure(Decimal(0),Decimal('1.1'),Decimal('1.2'),80)==(Decimal(0),Decimal(0))
    assert num.calculate(Decimal(0),Decimal('0.07'),1)==(GOLDENS[0][3],'0')


def test_fixed_schedule_rejects_matching_approximations(monkeypatch):
    # AC045/049/050/052/062/064: both naive midpoint approximations agree,
    # but the certified amount interval crosses a rounding boundary.
    seen=[]
    lower=Decimal('1.23456789012345678901234567890123449')
    upper=Decimal('1.23456789012345678901234567890123451')
    midpoint=Decimal('1.2345678901234567890123456789012345')
    assert num.canonical_decimal34(midpoint)==num.canonical_decimal34(midpoint)
    def factors(r,d,p): seen.append(p); return Decimal(1),Decimal(1)
    monkeypatch.setattr(num,'factor_enclosure',factors)
    monkeypatch.setattr(num,'amount_enclosure',lambda *args:(lower,upper))
    with pytest.raises(num.NumericFailure,match='seven-step'): num.calculate(Decimal(1),Decimal('.1'),1)
    assert seen==[80,160,320,640,1280,2560,5120]
    assert (num.INITIAL_WORKING_PRECISION,num.PRECISION_ESCALATION_FACTOR,num.MAX_WORKING_PRECISION,num.MAX_REFINEMENT_STEPS)==(80,2,5120,7)


def test_first_success_restarts_exact_inputs(monkeypatch):
    seen=[]
    def factors(r,d,p):
        seen.append((r,d,p))
        return (Decimal('1'),Decimal('2')) if p==80 else (Decimal('1.25'),Decimal('1.25'))
    monkeypatch.setattr(num,'factor_enclosure',factors)
    assert num.calculate(Decimal('2'),Decimal('.1'),1)==('1.25','2.5')
    assert seen==[(Decimal('.1'),1,80),(Decimal('.1'),1,160)]


def test_real_valid_input_halfway_unproven_at_limit(monkeypatch):
    # (500000005)^4 is a 35-digit integer ending in 5: exact Decimal34 tie.
    exact=500000005**4
    assert len(str(exact))==35 and exact % 10==5
    seen=[]; original=num.factor_enclosure
    def wrapped(r,d,p):
        seen.append(p); lo,hi=original(r,d,p)
        assert Fraction(lo)<exact<Fraction(hi)
        return lo,hi
    monkeypatch.setattr(num,'factor_enclosure',wrapped)
    with pytest.raises(num.NumericFailure): num.calculate(Decimal('1.00'),Decimal('500000004'),1461)
    assert seen==list(num.PRECISIONS)


@pytest.mark.parametrize('rate', ['1E999999999999999999','-0.999999999999999999'])
def test_representation_failure_never_fallback(rate,monkeypatch):
    # Actual overflow and injected underflow exercise the same fail-closed boundary.
    if rate.startswith('-'):
        from decimal import Underflow
        monkeypatch.setattr(num,'factor_enclosure',lambda *args: (_ for _ in ()).throw(Underflow()))
    with pytest.raises(num.NumericFailure): num.calculate(Decimal('1'),Decimal(rate),1)


def view(engine):
    with Session(engine) as db: return run.read(db,1)


def pair(engine):
    with Session(engine) as db:
        planning.begin_read(db)
        plan=planning.derive(db,1)
        return plan,basis.derive(db,1,plan)


def ready(engine, **changes):
    context(engine)
    asset=capital(engine,**changes)
    save(engine,asset,payload(engine,asset,annual_rate='0.07'))
    return asset


def test_empty_and_unready_context(engine):
    blocked=view(engine)
    assert blocked['execution_status']=='BLOCKED_NO_RESULT' and blocked['execution_fingerprint'] is None
    context(engine)
    result=view(engine)
    assert result['execution_status']=='AUTHORITATIVE_EMPTY_RESULT' and result['execution_ready']
    assert result['covered_source_count']==0 and result['projected_sources']==[]
    assert result==view(engine)
    assert result['execution_fingerprint']==run.aggregate_fingerprint(result)
    assert not any('amount' in key for key in result)


@pytest.mark.parametrize('change', ['missing','source','timing','negative'])
def test_registry_fail_closed_before_any_calculation(engine,monkeypatch,change):
    asset=ready(engine)
    other=capital(engine)
    if change!='missing': save(engine,other,payload(engine,other))
    if change in ('source','negative'):
        with Session(engine) as db,db.begin(): db.get(CapitalAsset,other).known_value_amount=Decimal('-1' if change=='negative' else '200')
    if change=='timing': save_target(engine,target_payload(engine,date(2031,1,1)))
    monkeypatch.setattr(run,'calculate',lambda *args:pytest.fail('Blocked registry executed arithmetic'))
    result=view(engine)
    assert result['covered_source_count']==2
    assert result['execution_status']=='BLOCKED_NO_RESULT'
    assert result['projected_sources']==[] and result['execution_fingerprint'] is None
    if change=='negative': assert 'SOURCE_VALUE_UNRESOLVED' in result['aggregate_blockers']


def test_order_bases_fingerprints_and_metadata(engine):
    asset=ready(engine)
    other=capital(engine,known_value_amount=Decimal('200.01'))
    save(engine,other,payload(engine,other,annual_rate='-0.1',return_basis='GROSS',price_basis='REAL'))
    plan,authority=pair(engine)
    result=run.execute(1,plan,authority)
    assert [(s['return_basis'],s['price_basis']) for s in result['projected_sources']]==[('NET','NOMINAL'),('GROSS','REAL')]
    assert not any('amount' in key for key in result)
    authority['covered_capital_sources'].reverse(); plan['capital_inputs'].reverse()
    assert run.execute(1,plan,authority)==result
    for s in authority['covered_capital_sources']:
        s['projection_basis_decision']['actor']='different'
        s['projection_basis_decision']['decided_at']='1900-01-01'
        s['projection_basis_decision']['planning_calculation_input_fingerprint_at_decision']='f'*64
    assert run.execute(1,plan,authority)==result
    source=result['projected_sources'][0]
    altered=source|dict(factor_lower='0',working_precision=5120,refinements=7,actor='other',request_timestamp='now')
    assert run.result_fingerprint(altered)==source['projection_result_fingerprint']
    with Session(engine) as db,db.begin(): db.get(CapitalAsset,asset).known_value_amount=Decimal('101.01')
    save(engine,asset,payload(engine,asset,annual_rate='0.07'))
    changed=view(engine)['projected_sources'][0]
    assert changed['projection_basis_source_admission_fingerprint']!=source['projection_basis_source_admission_fingerprint']
    assert changed['projection_result_fingerprint']!=source['projection_result_fingerprint']


def recertify(plan,authority):
    """Adversarial fixture only: recalculate hashes, not production validation."""
    for s,c in zip(authority['covered_capital_sources'],plan['capital_inputs']):
        s['source_semantic_fingerprint']=basis.source_fingerprint(c)
        s['projection_timing_context_fingerprint']=basis.timing_fingerprint(plan)
        s['projection_basis_decision']['source_semantic_fingerprint_at_decision']=s['source_semantic_fingerprint']
        s['projection_basis_decision']['timing_context_fingerprint_at_decision']=s['projection_timing_context_fingerprint']
        s['projection_basis_decision_fingerprint']=basis.decision_fingerprint(s['projection_basis_decision'])
        s['projection_basis_source_admission_fingerprint']=planning.fingerprint(dict(
            planning_calculation_input_fingerprint=plan['planning_calculation_input_fingerprint'],
            projection_source_semantic_fingerprint=s['source_semantic_fingerprint'],
            projection_timing_context_fingerprint=s['projection_timing_context_fingerprint'],
            decision=s['projection_basis_decision_fingerprint'],ready=s['projection_basis_source_readiness'],blockers=s['blockers']))
    authority['projection_basis_admission_fingerprint']=planning.fingerprint(dict(contract=basis.CONTRACT,
        planning_calculation_input_fingerprint=plan['planning_calculation_input_fingerprint'],
        covered_source_count=authority['covered_source_count'],
        sources=[dict(source_id=s['source_id'],admission=s['projection_basis_source_admission_fingerprint']) for s in authority['covered_capital_sources']],
        ready=authority['projection_basis_ready'],blockers=authority['aggregate_blockers']))


@pytest.mark.parametrize('tamper,code', [('duplicate','STRUCTURE_INVALID'),('count','STRUCTURE_INVALID'),
    ('fingerprint','STRUCTURE_INVALID'),('negative','STRUCTURE_INVALID'),('float','STRUCTURE_INVALID'),
    ('date','INVALID_DATE_ORDER'),('rate','RATE_INVALID'),('nonfinite','NUMERIC_NONFINITE')])
def test_forged_ready_structure(engine,tamper,code):
    ready(engine); plan,authority=pair(engine); s=authority['covered_capital_sources'][0]
    if tamper=='duplicate': authority['covered_capital_sources'].append(copy.deepcopy(s))
    elif tamper=='count': authority['covered_source_count']=0
    elif tamper=='fingerprint': authority['projection_basis_admission_fingerprint']='a'*64
    else:
        if tamper in ('negative','float','nonfinite'):
            value={'negative':'-1.00','float':100.0,'nonfinite':'NaN'}[tamper]
            s['known_value_amount']=plan['capital_inputs'][0]['known_value_amount']=value
        elif tamper=='date':
            s['economic_projection_start_date']=s['value_as_of_date']=plan['capital_inputs'][0]['value_as_of_date']='2031-01-01'
        elif tamper=='rate': s['annual_rate']=s['projection_basis_decision']['annual_rate']='-1'
        recertify(plan,authority)
    with pytest.raises(PensionProductError) as error: run.execute(1,plan,authority)
    assert error.value.code=='PROJECTION_EXECUTION_'+code


def database_snapshot(engine):
    with engine.connect() as conn:
        return {t.name:conn.execute(select(t)).all() for t in Base.metadata.sorted_tables}


def test_api_read_only_stable_and_conflict(engine):
    asset=ready(engine); before=database_snapshot(engine); statements=[]
    def listen(conn,cursor,sql,*args): statements.append(sql.strip().upper())
    def override():
        with Session(engine) as db: yield db
    app.dependency_overrides[get_db]=override
    event.listen(engine,'before_cursor_execute',listen)
    try:
        client=TestClient(app); url='/api/clients/1/retirement-planning-input/capital-projection'
        one=client.get(url); two=client.get(url)
        assert one.status_code==200 and one.content==two.content
        assert client.post(url).status_code==405
        assert all(s.startswith(('SELECT','BEGIN','SET TRANSACTION')) for s in statements)
        assert not any(any(f+'(' in s for f in ('POWER','LN','EXP')) for s in statements)
        assert before==database_snapshot(engine)
        with Session(engine) as db,db.begin(): db.get(CapitalAsset,asset).known_value_amount=Decimal('-1')
        blocked=client.get(url)
        assert blocked.status_code==409 and blocked.json()['projected_sources']==[]
    finally:
        app.dependency_overrides.clear(); event.remove(engine,'before_cursor_execute',listen)


def test_fresh_read_transaction_required(engine):
    with Session(engine) as db:
        db.execute(select(CapitalAsset))
        with pytest.raises(PensionProductError,match='טרנזקציית'): run.read(db,1)


def test_end_to_end_golden_fingerprint_envelopes(engine):
    # Exact one-day API source, independently certified golden factor/amount.
    context(engine)
    asset=capital(engine,known_value_amount=Decimal('1.04'),value_as_of_date=date(2029,12,31))
    save(engine,asset,payload(engine,asset,annual_rate='0.07'))
    result=view(engine); source=result['projected_sources'][0]
    assert source['projection_factor']==GOLDENS[-1][3]
    assert source['projected_amount']==GOLDENS[-1][4]
    envelope=dict(calculation_contract_version='canonical-pre-retirement-capital-projection-execution-v1',
        numeric_contract_version='canonical-decimal34-half-even-v1',source_id=f'capital:{asset}',
        projection_basis_source_admission_fingerprint=source['projection_basis_source_admission_fingerprint'],
        known_value_amount='1.04',economic_projection_start_date='2029-12-31',retirement_target_date='2030-01-01',
        elapsed_days=1,year_fraction_numerator=4,year_fraction_denominator=1461,annual_rate='0.07',
        return_basis='NET',price_basis='NOMINAL',compounding_convention='ANNUAL_EFFECTIVE',day_count_convention='ACTUAL_365_25',
        projection_factor=GOLDENS[-1][3],projected_amount=GOLDENS[-1][4])
    def digest(obj): return hashlib.sha256(json.dumps(obj,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
    expected=digest(envelope)
    assert source['projection_result_fingerprint']==expected
    assert result['execution_fingerprint']==digest(dict(
        calculation_contract_version=envelope['calculation_contract_version'],numeric_contract_version=envelope['numeric_contract_version'],
        planning_calculation_input_fingerprint=result['planning_calculation_input_fingerprint'],
        projection_basis_admission_fingerprint=result['projection_basis_admission_fingerprint'],
        execution_status='AUTHORITATIVE_RESULT',covered_source_count=1,
        sources=[dict(source_id=f'capital:{asset}',projection_result_fingerprint=expected)]))
    assert set(source)==set(envelope)|{'source_semantic_fingerprint','projection_timing_context_fingerprint',
        'projection_basis_decision_fingerprint','projection_result_fingerprint'}


def test_numeric_failure_after_first_source_never_returns_partial(engine,monkeypatch):
    ready(engine); other=capital(engine); save(engine,other,payload(engine,other))
    calls=[]
    def calculation(*args):
        calls.append(args)
        if len(calls)==2: raise num.NumericFailure('deliberate resource boundary')
        return '1','1E2'
    monkeypatch.setattr(run,'calculate',calculation)
    with pytest.raises(PensionProductError) as error: view(engine)
    assert error.value.code=='PROJECTION_EXECUTION_NUMERIC_DOMAIN_FAILURE' and len(calls)==2


def test_pension_excluded(engine):
    from test_recovery_pension_products import create
    context(engine)
    with Session(engine) as db,db.begin(): create(db)
    result=view(engine)
    assert result['covered_source_count']==0 and result['projected_sources']==[]


def test_reachability_no_schema_frontend_or_downstream_changes():
    import ast
    root=Path(__file__).resolve().parents[2]
    modules=[root/'backend/app/services'/name for name in ('capital_projection_execution_service.py','capital_projection_execution_numeric.py')]
    for module in modules:
        code=module.read_text(); parsed=ast.parse(code)
        assert not any(token in code for token in ('quantize(', 'date.today(', 'm09_', 'm10_', 'PensionHolding', 'PlannerAssumption'))
        for node in ast.walk(parsed):
            assert not (isinstance(node,ast.Constant) and isinstance(node.value,float))
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute):
                if node.func.attr == 'add':
                    assert module.name.endswith('_numeric.py') or (isinstance(node.func.value,ast.Name) and node.func.value.id=='blockers')
                else:
                    assert node.func.attr not in {'delete','commit','flush','merge','execute','exec_driver_sql'}
    # This historical package boundary is the accepted CPX commit, not later authorized packages.
    changed=subprocess.check_output(['git','diff','--name-only','ec5d7fbb92a72d2378c514b04f07665e8da652c9',
        '846dddb0b59b59b311d90d31242c90620be487e4'],cwd=root,text=True).splitlines()
    assert not any(p.startswith(('frontend/','backend/alembic/','backend/app/models/')) for p in changed)
    heads=subprocess.check_output([sys.executable,'-m','alembic','heads'],cwd=root/'backend',text=True).strip()
    assert heads=='f1a7c4d0e298 (head)'
