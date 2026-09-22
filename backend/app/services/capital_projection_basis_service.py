"""Closed assumption authority. No projection arithmetic or legacy fallback."""
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import select, or_
from app.models.capital_projection_basis import CapitalProjectionBasisDecision as Decision, CONTRACT, PROVENANCE, parse_rate, rate_string
from app.models.retirement_facts import CapitalAsset
from app.models.planning_input_decision import PlanningInputDecision
from app.services import planning_input_service as planning
from app.services.professional_source_snapshot_service import begin_read, record, serialize
from app.services.pension_product_service import PensionProductError, lock_client

COMPOUNDING = 'ANNUAL_EFFECTIVE'
DAY_COUNT = 'ACTUAL_365_25'


def fail(code):
    raise PensionProductError(code, 'המקור או ההחלטה אינם עדכניים או תקינים; יש לרענן ולאשר במפורש', 409)


def source_fingerprint(source):
    return planning.fingerprint(dict(contract=CONTRACT, adapter='canonical_capital_input_v1',
        client_id=source['client_id'], source_id=source['source_id'], capital_asset_id=source['id'],
        lifecycle_status=source['lifecycle_status'], known_value_amount=source['known_value_amount'],
        value_as_of_date=source['value_as_of_date'], origin_kind=source['origin_kind'], conversion_id=source['conversion_id']))


def timing_fingerprint(plan):
    return planning.fingerprint(dict(planning_base_date=plan['planning_base_date'],
        retirement_target_date=plan['retirement_target']['retirement_target_date']))


def decision_data(row):
    if row is None: return None
    result = serialize(record(row))
    try:
        result['annual_rate'] = rate_string(row.annual_rate) if row.annual_rate is not None else None
    except ValueError:
        # Corrupt/nonfinite stored data remains visible and RATE_INVALID; never default it.
        result['annual_rate'] = str(row.annual_rate)
    return result


def decision_fingerprint(decision):
    if decision is None: return None
    return planning.fingerprint(dict(contract=CONTRACT, annual_rate=decision['annual_rate'],
        return_basis=decision['return_basis'], price_basis=decision['price_basis'],
        compounding_convention=COMPOUNDING, day_count_convention=DAY_COUNT))


def covered_capital_source_registry(plan, assets, client_id):
    sources = plan['capital_inputs']
    identities = [s.get('source_id') for s in sources]
    if len(set(identities)) != len(identities): fail('PROJECTION_COVERAGE_STRUCTURE_INVALID')
    current = {row.id: row for row in assets if row.lifecycle_status == 'current'}
    if set(identities) != {f'capital:{key}' for key in current}: fail('PROJECTION_COVERAGE_STRUCTURE_INVALID')
    for source in sources:
        row = current.get(source.get('id'))
        if row is None or source['source_id'] != f'capital:{row.id}' or source.get('client_id') != client_id or row.client_id != client_id:
            fail('PROJECTION_COVERAGE_STRUCTURE_INVALID')
        if source.get('lifecycle_status') != 'current': fail('PROJECTION_COVERAGE_STRUCTURE_INVALID')
    return sorted(sources, key=lambda source: source['source_id'])


def derive(db, client_id, plan):
    assets = db.scalars(select(CapitalAsset).where(CapitalAsset.client_id == client_id).order_by(CapitalAsset.id)).all()
    asset_map = {row.id: row for row in assets}
    decisions = db.scalars(select(Decision).where(or_(Decision.client_id == client_id,
        Decision.capital_asset_id.in_(asset_map))).order_by(Decision.capital_asset_id)).all()
    for row in decisions:
        if row.client_id != client_id or row.capital_asset_id not in asset_map:
            fail('PROJECTION_COVERAGE_STRUCTURE_INVALID')
        if row.contract_version != CONTRACT or row.provenance != PROVENANCE:
            fail('PROJECTION_COVERAGE_STRUCTURE_INVALID')
    by_asset = {row.capital_asset_id: row for row in decisions}
    registry = covered_capital_source_registry(plan, assets, client_id)
    covered = []
    ready_context = plan['planning_input_ready'] and plan['retirement_target']['retirement_target_ready']
    timing = timing_fingerprint(plan)
    base = plan['planning_base_date']
    target = plan['retirement_target']['retirement_target_date']
    for source in registry:
        sfp = source_fingerprint(source)
        decision = decision_data(by_asset.get(source['id']))
        blockers = []
        if not ready_context: blockers.append('PLANNING_OR_TARGET_NOT_READY')
        amount = source['known_value_amount']
        if amount is None or not Decimal(amount).is_finite() or Decimal(amount) < 0:
            blockers.append('SOURCE_VALUE_UNRESOLVED')
        value_date = source['value_as_of_date']
        if value_date is None: blockers.append('VALUATION_DATE_MISSING')
        else:
            if base is not None and value_date > base: blockers.append('VALUATION_DATE_AFTER_PLANNING_BASE')
            if target is not None and value_date > target: blockers.append('VALUATION_DATE_AFTER_RETIREMENT_TARGET')
        rate = decision['annual_rate'] if decision else None
        if rate is None: blockers.append('RATE_MISSING')
        else:
            try: parse_rate(rate)
            except ValueError: blockers.append('RATE_INVALID')
        return_basis = decision['return_basis'] if decision else None
        price_basis = decision['price_basis'] if decision else None
        if return_basis not in ('NET', 'GROSS'): blockers.append('RETURN_BASIS_MISSING_OR_INVALID')
        if price_basis not in ('NOMINAL', 'REAL'): blockers.append('PRICE_BASIS_MISSING_OR_INVALID')
        if decision:
            if sfp != decision['source_semantic_fingerprint_at_decision']: blockers.append('SOURCE_STATE_CHANGED_SINCE_DECISION')
            if timing != decision['timing_context_fingerprint_at_decision']: blockers.append('TIMING_CONTEXT_CHANGED_SINCE_DECISION')
        blockers.sort()
        dfp = decision_fingerprint(decision)
        admission = planning.fingerprint(dict(planning_calculation_input_fingerprint=plan['planning_calculation_input_fingerprint'],
            projection_source_semantic_fingerprint=sfp, projection_timing_context_fingerprint=timing,
            decision=dfp if decision else {'state': 'MISSING_DECISION', 'source_id': source['source_id']},
            ready=not blockers, blockers=blockers))
        covered.append(dict(source_id=source['source_id'], capital_asset_id=source['id'],
            source_semantic_fingerprint=sfp, known_value_amount=amount, value_as_of_date=value_date,
            economic_projection_start_date=value_date, retirement_target_date=target,
            projection_basis_decision=decision, annual_rate=rate, return_basis=return_basis, price_basis=price_basis,
            compounding_convention=COMPOUNDING, day_count_convention=DAY_COUNT,
            projection_basis_source_readiness=not blockers, blockers=blockers, warnings=[],
            projection_basis_decision_fingerprint=dfp, projection_timing_context_fingerprint=timing,
            projection_basis_source_admission_fingerprint=admission))
    aggregate = sorted({b for source in covered for b in source['blockers']} | (set() if ready_context else {'PLANNING_OR_TARGET_NOT_READY'}))
    ready = ready_context and not aggregate
    historical = [dict(source_id=f'capital:{row.capital_asset_id}', reason='SOURCE_NOT_ELIGIBLE',
        authority='historical_non_authoritative', projection_basis_decision=decision_data(row))
        for row in decisions if asset_map[row.capital_asset_id].lifecycle_status != 'current']
    historical.sort(key=lambda item: item['source_id'])
    aggregate_fp = planning.fingerprint(dict(contract=CONTRACT,
        planning_calculation_input_fingerprint=plan['planning_calculation_input_fingerprint'], covered_source_count=len(covered),
        sources=[{'source_id': s['source_id'], 'admission': s['projection_basis_source_admission_fingerprint']} for s in covered],
        ready=ready, blockers=aggregate))
    return dict(contract_version=CONTRACT, client_id=client_id, decision_version=plan['decision_version'],
        planning_base_date=base, retirement_target_date=target,
        planning_calculation_input_fingerprint=plan['planning_calculation_input_fingerprint'],
        covered_source_count=len(covered), covered_capital_sources=covered,
        noncurrent_or_historical_bound_decisions=historical, projection_basis_ready=ready,
        aggregate_blockers=aggregate, projection_basis_admission_fingerprint=aggregate_fp)


def read(db, client_id):
    begin_read(db)
    with db.no_autoflush:
        return derive(db, client_id, planning.derive(db, client_id))


def write(db, client_id, asset_id, payload, *, clear=False):
    if db.in_transaction() or db.new or db.dirty or db.deleted: fail('PROJECTION_REQUIRES_FRESH_TRANSACTION')
    dialect = db.get_bind().dialect.name
    connection = db.connection()
    if dialect == 'postgresql': connection.exec_driver_sql('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
    elif dialect == 'sqlite': connection.exec_driver_sql('BEGIN IMMEDIATE')
    else: fail('UNSUPPORTED_DATABASE')
    lock_client(db, client_id)
    shared = db.scalar(select(PlanningInputDecision).where(PlanningInputDecision.client_id == client_id).with_for_update())
    asset = db.scalar(select(CapitalAsset).where(CapitalAsset.id == asset_id, CapitalAsset.client_id == client_id).with_for_update())
    if asset is None or asset.lifecycle_status != 'current': fail('SOURCE_NOT_ELIGIBLE')
    if (shared.version if shared else 0) != payload.expected_version: fail('PLANNING_DECISION_STALE')
    plan = planning.derive(db, client_id)
    current = derive(db, client_id, plan)
    source = next((s for s in current['covered_capital_sources'] if s['capital_asset_id'] == asset_id), None)
    if source is None: fail('SOURCE_NOT_ELIGIBLE')
    for expected, actual, code in (
        (payload.expected_source_semantic_fingerprint, source['source_semantic_fingerprint'], 'PROJECTION_SOURCE_STATE_STALE'),
        (payload.expected_timing_context_fingerprint, source['projection_timing_context_fingerprint'], 'PROJECTION_TIMING_CONTEXT_STALE'),
        (payload.expected_planning_calculation_input_fingerprint, current['planning_calculation_input_fingerprint'], 'PROJECTION_PLANNING_INPUT_STALE')):
        if expected != actual: fail(code)
    decision = db.get(Decision, asset_id)
    if clear:
        if decision is not None: db.delete(decision)
    else:
        if decision is None:
            decision = Decision(capital_asset_id=asset_id, client_id=client_id)
            db.add(decision)
        decision.annual_rate = parse_rate(payload.annual_rate)
        decision.return_basis = payload.return_basis
        decision.price_basis = payload.price_basis
        decision.contract_version = CONTRACT
        decision.source_semantic_fingerprint_at_decision = source['source_semantic_fingerprint']
        decision.timing_context_fingerprint_at_decision = source['projection_timing_context_fingerprint']
        decision.planning_calculation_input_fingerprint_at_decision = current['planning_calculation_input_fingerprint']
        decision.actor = 'planner:planning-input'
        decision.provenance = PROVENANCE
        decision.decided_at = datetime.now(timezone.utc)
    if shared is None:
        shared = PlanningInputDecision(client_id=client_id, version=0, actor='planner:planning-input')
        db.add(shared)
    shared.version += 1
    db.flush()
    return {'decision_version': shared.version}
