"""Exact base facts only: no division, indexation, projection or persistence."""
from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
from sqlalchemy import select
from app.models.pension_product import PensionProductAuditEvent
from app.services.pension_product_service import PensionProductError

CONTRACT = 'canonical-pension-monthly-amount-basis-v1'
SEMANTIC = 'canonical-pension-monthly-amount-basis-semantic-v1'
SOURCE = 'canonical-pension-monthly-amount-basis-source-v1'
PROVENANCE = 'canonical-pension-monthly-amount-basis-conversion-provenance-v1'
REGISTRY = 'canonical-pension-monthly-amount-basis-registry-v1'
MANUAL_FIELDS = ('annuity_factor', 'balance', 'base_amount_effective_date', 'description',
    'fixed_indexation_rate', 'indexation_method', 'input_mode', 'monthly_amount', 'payer_name',
    'pension_start_date', 'source_note', 'source_reference', 'tax_treatment')
BATCH_FIELDS = ('actor', 'batch_id', 'destination_type', 'effective_date', 'matrix_version', 'source_product_id', 'status')
CONVERSION_FIELDS = ('conversion_id', 'converted_amount', 'destination_type', 'status', 'tax_treatment', 'version')
DESTINATION_FIELDS = ('annuity_factor_text', 'coefficient_catalog_version', 'coefficient_fallback_used',
    'coefficient_notes', 'coefficient_source', 'coefficient_source_keys', 'converted_balance', 'effective_date',
    'monthly_denominator', 'monthly_numerator', 'pension_destination_id', 'pension_start_date', 'status', 'tax_treatment', 'version')
ALLOCATION_FIELDS = ('allocation_id', 'amount', 'component_code_snapshot', 'conversion_id', 'matrix_version',
    'source_balance_after', 'source_balance_before', 'source_component_id', 'source_product_id', 'tax_treatment')
MONEY_FIELDS = {'balance', 'monthly_amount', 'converted_amount', 'converted_balance', 'monthly_numerator',
                'amount', 'source_balance_after', 'source_balance_before'}
FACTOR_FIELDS = {'annuity_factor', 'fixed_indexation_rate', 'annuity_factor_text', 'monthly_denominator'}


def fail(code='BASIS_SOURCE_STRUCTURE_INVALID'):
    raise PensionProductError(code, 'שלמות סמכות סכום הבסיס אינה תקינה; יש לבדוק את המקור', 409)


def canonical_bytes(value):
    """CANONICAL_BASIS_FINGERPRINT_JSON_V1, including uniform control escaping."""
    def encode(v):
        if v is None: return 'null'
        if v is True: return 'true'
        if v is False: return 'false'
        if type(v) is int: return str(v)
        if isinstance(v, str):
            return '"' + ''.join('\\"' if c == '"' else '\\\\' if c == '\\' else
                f'\\u{ord(c):04x}' if ord(c) < 32 else c for c in v) + '"'
        if isinstance(v, list): return '[' + ','.join(encode(i) for i in v) + ']'
        if isinstance(v, dict) and all(isinstance(k, str) for k in v):
            return '{' + ','.join(encode(k) + ':' + encode(v[k]) for k in sorted(v)) + '}'
        raise ValueError('Noncanonical JSON value')
    return encode(value).encode('utf-8')


def fingerprint(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def decimal(value):
    if isinstance(value, bool) or not isinstance(value, (Decimal, str, int)):
        raise ValueError('Exact decimal required')
    result = Decimal(value)
    if not result.is_finite(): raise ValueError('Finite decimal required')
    return result


def factor(value):
    number = decimal(value)
    if not number: return '0'
    text = format(number, 'f')
    return text.rstrip('0').rstrip('.') if '.' in text else text


def money(value):
    text = format(decimal(value), 'f')
    whole, _, fraction = text.partition('.')
    if any(c != '0' for c in fraction[2:]): raise ValueError('Money scale loss forbidden')
    if not decimal(value): whole = '0'
    return whole + '.' + (fraction + '00')[:2]


def fields(row, names):
    output = {}
    for key in names:
        value = row[key]
        if value is not None:
            if key in MONEY_FIELDS: value = money(value)
            elif key in FACTOR_FIELDS: value = factor(value)
            elif isinstance(value, date): value = value.isoformat()
        output[key] = value
    return output


def semantic(kind, representation, effective_date):
    return fingerprint(dict(contract_version=SEMANTIC, authority_kind=kind,
        base_amount_representation=representation, base_amount_effective_date=effective_date))


def manual(row, client_id):
    if row.client_id != client_id: fail('BASIS_SOURCE_OWNERSHIP_INVALID')
    if row.lifecycle_status != 'current': fail('BASIS_SOURCE_NOT_CURRENT')
    if row.input_mode not in ('entered', 'calculated'): fail()
    blockers = []
    effective = row.base_amount_effective_date.isoformat() if row.base_amount_effective_date else None
    if effective is None: blockers.append('BASE_AMOUNT_EFFECTIVE_DATE_MISSING')
    values = {key: getattr(row, key) for key in MANUAL_FIELDS}
    # Invalid stored factor facts remain visible, never become parsed authority.
    provenance = {}
    for key in MANUAL_FIELDS:
        try:
            provenance.update(fields(values, (key,)))
        except (ValueError, ArithmeticError):
            if key not in FACTOR_FIELDS: fail()
            provenance[key] = values[key]
    entered = row.input_mode == 'entered'
    kind = 'entered_monthly_amount' if entered else 'manual_balance_ratio'
    amount = row.monthly_amount if entered else row.balance
    prefix = 'ENTERED_MONTHLY_AMOUNT' if entered else 'MANUAL_BALANCE'
    if amount is None: blockers.append(prefix + '_MISSING')
    elif decimal(amount) <= 0: blockers.append(prefix + '_NOT_POSITIVE')
    if entered:
        representation = dict(representation_kind='exact_money', amount=provenance['monthly_amount'])
    else:
        if row.annuity_factor is None: blockers.append('MANUAL_ANNUITY_FACTOR_MISSING')
        else:
            try:
                if decimal(row.annuity_factor) <= 0: blockers.append('MANUAL_ANNUITY_FACTOR_NOT_POSITIVE')
            except (InvalidOperation, ValueError): blockers.append('MANUAL_ANNUITY_FACTOR_INVALID')
        representation = dict(representation_kind='exact_ratio', numerator=provenance['balance'], denominator=provenance['annuity_factor'])
    sfp = None if blockers else semantic(kind, representation, effective)
    source_id = 'manual:' + row.manual_pension_source_id
    source_fp = fingerprint(dict(contract_version=SOURCE, source_id=source_id, source_kind='manual',
        source_version=row.version, client_id=client_id, lifecycle_status='current',
        base_amount_semantic_fingerprint=sfp, current_provenance=provenance))
    return dict(contract_version=CONTRACT, source_id=source_id, source_kind='manual', authority_kind=kind,
        base_amount_representation=representation, base_amount_effective_date=effective,
        pension_start_date=provenance['pension_start_date'], source_statement_date=None,
        provenance=provenance, basis_authority_ready=not blockers, basis_blockers=sorted(set(blockers)),
        base_amount_semantic_fingerprint=sfp, base_amount_source_fingerprint=source_fp)


def conversion(db, client_id, batch, converted, destination, trace):
    if any(r['client_id'] != client_id for r in (batch, converted, destination)):
        fail('BASIS_SOURCE_OWNERSHIP_INVALID')
    if converted['status'] != 'active' or destination['status'] != 'active': fail('BASIS_SOURCE_NOT_CURRENT')
    if batch['effective_date'] is None or destination['effective_date'] is None:
        fail('CONVERSION_EFFECTIVE_DATE_MISSING')
    if batch['effective_date'] != destination['effective_date']: fail('CONVERSION_EFFECTIVE_DATE_MISMATCH')
    events = db.scalars(select(PensionProductAuditEvent).where(
        PensionProductAuditEvent.action == 'conversion', PensionProductAuditEvent.client_id == batch['client_id'],
        PensionProductAuditEvent.product_id == batch['source_product_id'])).all()
    matches = [e for e in events if isinstance(e.snapshot, dict) and isinstance(e.snapshot.get('operation'), dict)
               and e.snapshot['operation'].get('batch_id') == batch['batch_id']]
    if len(matches) != 1 or 'statement_date' not in matches[0].snapshot: fail('BASIS_CONVERSION_PROVENANCE_INVALID')
    event = matches[0]
    statement = event.snapshot['statement_date']
    if statement is not None:
        try:
            if not isinstance(statement, str) or date.fromisoformat(statement).isoformat() != statement:
                fail('BASIS_CONVERSION_PROVENANCE_INVALID')
        except (ValueError, TypeError): fail('BASIS_CONVERSION_PROVENANCE_INVALID')
    try:
        if decimal(destination['monthly_numerator']) <= 0 or decimal(destination['monthly_denominator']) <= 0:
            fail('PERSISTED_CONVERSION_RATIO_INVALID')
        representation = dict(representation_kind='exact_ratio', numerator=money(destination['monthly_numerator']),
                              denominator=factor(destination['monthly_denominator']))
        provenance = dict(contract_version=PROVENANCE, batch=fields(batch, BATCH_FIELDS),
            conversion=fields(converted, CONVERSION_FIELDS), destination=fields(destination, DESTINATION_FIELDS),
            allocations=[fields(a, ALLOCATION_FIELDS) for a in sorted(trace, key=lambda a: a['allocation_id'])],
            audit_event=dict(action=event.action, actor=event.actor, client_id=event.client_id,
                event_id=event.event_id, event_version=event.version, product_id=event.product_id,
                operation_batch_id=event.snapshot['operation']['batch_id'], source_statement_date=statement,
                statement_date_evidence_state='MATCHED_NULL' if statement is None else 'MATCHED_VALUE'))
        immutable = fingerprint(provenance)
    except PensionProductError: raise
    except (ValueError, TypeError, KeyError, ArithmeticError): fail('BASIS_CONVERSION_PROVENANCE_INVALID')
    effective = batch['effective_date'].isoformat()
    sfp = semantic('persisted_conversion_ratio', representation, effective)
    source_id = 'conversion:' + destination['pension_destination_id']
    source_fp = fingerprint(dict(contract_version=SOURCE, source_id=source_id, source_kind='conversion',
        source_version=destination['version'], client_id=client_id, lifecycle_status='current',
        base_amount_semantic_fingerprint=sfp, immutable_provenance_fingerprint=immutable))
    return dict(contract_version=CONTRACT, source_id=source_id, source_kind='conversion',
        authority_kind='persisted_conversion_ratio', base_amount_representation=representation,
        base_amount_effective_date=effective, pension_start_date=destination['pension_start_date'].isoformat(),
        source_statement_date=statement, provenance=provenance, basis_authority_ready=True, basis_blockers=[],
        base_amount_semantic_fingerprint=sfp, base_amount_source_fingerprint=source_fp)


def registry(client_id, sources):
    if len({s['source_id'] for s in sources}) != len(sources): fail()
    return fingerprint(dict(contract_version=REGISTRY, client_id=client_id, sources=[dict(
        source_id=s['source_id'], base_amount_source_fingerprint=s['base_amount_source_fingerprint'],
        basis_authority_ready=s['basis_authority_ready'], basis_blockers=sorted(set(s['basis_blockers'])))
        for s in sorted(sources, key=lambda s: s['source_id'])]))
