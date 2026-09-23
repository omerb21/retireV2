"""Read-only current canonical capital execution; no downstream execution path."""
from datetime import date
from decimal import Decimal, InvalidOperation
import re

from app.services import capital_projection_basis_service as basis
from app.services import planning_input_service as planning
from app.services.capital_projection_execution_numeric import calculate, NumericFailure, NUMERIC_CONTRACT
from app.services.professional_source_snapshot_service import begin_read
from app.services.pension_product_service import PensionProductError

CONTRACT = 'canonical-pre-retirement-capital-projection-execution-v1'
RESULT_FIELDS = (
    'calculation_contract_version', 'numeric_contract_version', 'source_id',
    'projection_basis_source_admission_fingerprint', 'known_value_amount',
    'economic_projection_start_date', 'retirement_target_date', 'elapsed_days',
    'year_fraction_numerator', 'year_fraction_denominator', 'annual_rate',
    'return_basis', 'price_basis', 'compounding_convention', 'day_count_convention',
    'projection_factor', 'projected_amount',
)


def fail(code='PROJECTION_EXECUTION_STRUCTURE_INVALID'):
    raise PensionProductError(code, 'לא ניתן לחשב הקרנת הון סמכותית; יש לבדוק את המקורות וההחלטות', 409)


def is_fingerprint(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def result_fingerprint(result):
    return planning.fingerprint({key: result[key] for key in RESULT_FIELDS})


def aggregate_fingerprint(result):
    return planning.fingerprint(dict(calculation_contract_version=CONTRACT,
        numeric_contract_version=NUMERIC_CONTRACT,
        planning_calculation_input_fingerprint=result['planning_calculation_input_fingerprint'],
        projection_basis_admission_fingerprint=result['projection_basis_admission_fingerprint'],
        execution_status=result['execution_status'], covered_source_count=result['covered_source_count'],
        sources=[dict(source_id=s['source_id'], projection_result_fingerprint=s['projection_result_fingerprint'])
                 for s in sorted(result['projected_sources'], key=lambda s: s['source_id'])]))


def execute(client_id, plan, authority):
    """Consume a single current upstream snapshot, never client-supplied decisions."""
    try:
        return _execute(client_id, plan, authority)
    except PensionProductError:
        raise
    except (KeyError, TypeError, ValueError, InvalidOperation) as error:
        if isinstance(error, NumericFailure):
            fail(error.code)
        fail()


def _execute(client_id, plan, authority):
    if authority['client_id'] != client_id or authority['contract_version'] != basis.CONTRACT:
        fail()
    sources = sorted(authority['covered_capital_sources'], key=lambda s: s['source_id'])
    capitals = sorted(plan['capital_inputs'], key=lambda s: s['source_id'])
    ids = [s['source_id'] for s in sources]
    if (len(set(ids)) != len(ids) or ids != [s['source_id'] for s in capitals]
            or type(authority['covered_source_count']) is not int or authority['covered_source_count'] != len(ids)):
        fail()
    for flag in (plan['planning_input_ready'], plan['retirement_target']['retirement_target_ready'], authority['projection_basis_ready']):
        if type(flag) is not bool:
            fail()
    pfp = plan['planning_calculation_input_fingerprint']
    afp = authority['projection_basis_admission_fingerprint']
    if not is_fingerprint(pfp) or not is_fingerprint(afp) or authority['planning_calculation_input_fingerprint'] != pfp:
        fail()
    timing = basis.timing_fingerprint(plan)
    target = plan['retirement_target']['retirement_target_date']
    if authority['retirement_target_date'] != target or authority['planning_base_date'] != plan['planning_base_date']:
        fail()
    blockers = set(authority['aggregate_blockers'])
    if not plan['planning_input_ready'] or not plan['retirement_target']['retirement_target_ready']:
        blockers.add('PLANNING_OR_TARGET_NOT_READY')
    admitted = []
    for source, capital in zip(sources, capitals):
        if (capital['client_id'] != client_id or capital['lifecycle_status'] != 'current'
                or capital['source_id'] != f"capital:{capital['id']}"
                or source['capital_asset_id'] != capital['id']):
            fail()
        ready = source['projection_basis_source_readiness']
        if type(ready) is not bool:
            fail()
        amount = source['known_value_amount']
        if ready and isinstance(amount, str) and Decimal(amount).is_finite() and Decimal(amount) < 0:
            fail()  # Forged ready-negative payload never reaches interval multiplication.
        if (source['source_semantic_fingerprint'] != basis.source_fingerprint(capital)
                or amount != capital['known_value_amount']
                or source['economic_projection_start_date'] != capital['value_as_of_date']
                or source['value_as_of_date'] != capital['value_as_of_date']
                or source['retirement_target_date'] != target
                or source['projection_timing_context_fingerprint'] != timing
                or source['compounding_convention'] != basis.COMPOUNDING
                or source['day_count_convention'] != basis.DAY_COUNT):
            fail()
        decision = source['projection_basis_decision']
        dfp = basis.decision_fingerprint(decision)
        if source['projection_basis_decision_fingerprint'] != dfp:
            fail()
        expected_admission = planning.fingerprint(dict(planning_calculation_input_fingerprint=pfp,
            projection_source_semantic_fingerprint=source['source_semantic_fingerprint'],
            projection_timing_context_fingerprint=timing,
            decision=dfp if decision else {'state': 'MISSING_DECISION', 'source_id': source['source_id']},
            ready=ready, blockers=source['blockers']))
        if source['projection_basis_source_admission_fingerprint'] != expected_admission:
            fail()
        blockers.update(source['blockers'])
        if not ready:
            blockers.add('PROJECTION_SOURCE_NOT_READY')
            continue
        if decision is None or source['blockers']:
            fail()
        if (decision['client_id'] != client_id or decision['capital_asset_id'] != capital['id']):
            fail()
        if (decision['source_semantic_fingerprint_at_decision'] != source['source_semantic_fingerprint']
                or decision['timing_context_fingerprint_at_decision'] != timing):
            blockers.add('PROJECTION_DECISION_STALE')
        if any(source[k] != decision[k] for k in ('annual_rate', 'return_basis', 'price_basis')):
            fail()
        if source['return_basis'] not in ('NET', 'GROSS') or source['price_basis'] not in ('NOMINAL', 'REAL'):
            fail()
        if not isinstance(amount, str) or not isinstance(source['annual_rate'], str):
            fail()  # Never accept binary floats as exact input authority.
        a, r = Decimal(amount), Decimal(source['annual_rate'])
        if not a.is_finite() or not r.is_finite():
            fail('PROJECTION_EXECUTION_NUMERIC_NONFINITE')
        if r <= -1:
            fail('PROJECTION_EXECUTION_RATE_INVALID')
        if basis.rate_string(r) != source['annual_rate']:
            fail()
        start, end = date.fromisoformat(source['economic_projection_start_date']), date.fromisoformat(target)
        days = (end - start).days
        if days < 0:
            fail('PROJECTION_EXECUTION_INVALID_DATE_ORDER')
        admitted.append((source, a, r, days))
    expected_aggregate = planning.fingerprint(dict(contract=basis.CONTRACT,
        planning_calculation_input_fingerprint=pfp, covered_source_count=len(sources),
        sources=[{'source_id': s['source_id'], 'admission': s['projection_basis_source_admission_fingerprint']} for s in sources],
        ready=authority['projection_basis_ready'], blockers=authority['aggregate_blockers']))
    if afp != expected_aggregate:
        fail()
    if not authority['projection_basis_ready']:
        blockers.add('PROJECTION_BASIS_NOT_READY')
    response = dict(contract_version=CONTRACT, numeric_contract_version=NUMERIC_CONTRACT, client_id=client_id,
        planning_calculation_input_fingerprint=pfp, projection_basis_admission_fingerprint=afp,
        covered_source_count=len(sources), projected_sources=[], aggregate_blockers=sorted(blockers),
        execution_ready=not blockers, execution_status='BLOCKED_NO_RESULT' if blockers else
            ('AUTHORITATIVE_RESULT' if sources else 'AUTHORITATIVE_EMPTY_RESULT'), execution_fingerprint=None)
    if blockers:
        return response
    # Admission completes for the entire registry before any numeric execution.
    results = []
    for source, a, r, days in admitted:
        factor, amount = calculate(a, r, days)
        result = {key: source[key] for key in (
            'source_id', 'known_value_amount', 'economic_projection_start_date', 'retirement_target_date',
            'annual_rate', 'return_basis', 'price_basis', 'compounding_convention', 'day_count_convention',
            'source_semantic_fingerprint', 'projection_timing_context_fingerprint',
            'projection_basis_decision_fingerprint', 'projection_basis_source_admission_fingerprint')}
        result.update(elapsed_days=days, year_fraction_numerator=days * 4, year_fraction_denominator=1461,
            projection_factor=factor, projected_amount=amount, calculation_contract_version=CONTRACT,
            numeric_contract_version=NUMERIC_CONTRACT)
        result['projection_result_fingerprint'] = result_fingerprint(result)
        results.append(result)
    response['projected_sources'] = results
    response['execution_fingerprint'] = aggregate_fingerprint(response)
    return response


def read(db, client_id):
    begin_read(db)
    with db.no_autoflush:
        plan = planning.derive(db, client_id)
        authority = basis.derive(db, client_id, plan)
        return execute(client_id, plan, authority)
