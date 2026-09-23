"""Certified real-power enclosures and CANONICAL_DECIMAL34_V1 (no money rounding).

Decimal ln/exp are correctly rounded HALF_EVEN, not directed transcendental
operations. Their adjacent representable neighbours enclose the exact result;
monotonicity then composes these bounds. See the proof in specs/runtime/CPX_evidence.md.
"""
from decimal import (
    Decimal, Context, DecimalException, ROUND_FLOOR, ROUND_CEILING,
    ROUND_HALF_EVEN, InvalidOperation, DivisionByZero, Overflow, Underflow,
    Subnormal, Clamped,
)

INITIAL_WORKING_PRECISION = 80
PRECISION_ESCALATION_FACTOR = 2
MAX_WORKING_PRECISION = 5120
MAX_REFINEMENT_STEPS = 7
PRECISIONS = (80, 160, 320, 640, 1280, 2560, 5120)
NUMERIC_CONTRACT = 'canonical-decimal34-half-even-v1'


class NumericFailure(ValueError):
    code = 'PROJECTION_EXECUTION_NUMERIC_DOMAIN_FAILURE'


def canonical_decimal34(value):
    """Exact integer-digit half-even rounding, independent of ambient context."""
    if not isinstance(value, Decimal) or not value.is_finite():
        raise NumericFailure('A finite Decimal is required')
    if not value:
        return '0'
    sign, digits, exponent = value.as_tuple()
    digits = list(digits)
    if len(digits) > 34:
        discarded = digits[34:]
        exponent += len(discarded)
        digits = digits[:34]
        if discarded[0] > 5 or (discarded[0] == 5 and (any(discarded[1:]) or digits[-1] % 2)):
            i = len(digits) - 1
            while i >= 0 and digits[i] == 9:
                digits[i] = 0
                i -= 1
            if i < 0:
                digits.insert(0, 1)
            else:
                digits[i] += 1
    adjusted = exponent + len(digits) - 1
    while len(digits) > 1 and digits[-1] == 0:
        digits.pop()
    coefficient = str(digits[0]) + ('.' + ''.join(map(str, digits[1:])) if len(digits) > 1 else '')
    return ('-' if sign else '') + coefficient + (f'E{adjusted}' if adjusted else '')


def working_context(precision, rounding):
    # Fixed common technical exponent range, never a professional magnitude cap.
    # Non-representability fails the step; no subnormal/zero/infinity substitute.
    return Context(prec=precision, rounding=rounding, Emin=-999999999, Emax=999999999,
                   traps=[InvalidOperation, DivisionByZero, Overflow, Underflow, Subnormal, Clamped])


def factor_enclosure(rate, days, precision):
    down = working_context(precision, ROUND_FLOOR)
    up = working_context(precision, ROUND_CEILING)
    nearest = working_context(precision, ROUND_HALF_EVEN)
    # Both additions restart from the exact Decimal input, enclosing exact 1+r.
    lo_base, hi_base = down.add(Decimal(1), rate), up.add(Decimal(1), rate)
    if lo_base <= 0:
        raise NumericFailure('Base not certified positive at this precision')
    lo_log = nearest.next_minus(nearest.ln(lo_base))
    hi_log = nearest.next_plus(nearest.ln(hi_base))
    numerator, denominator = Decimal(days * 4), Decimal(1461)
    lo_power = down.divide(down.multiply(lo_log, numerator), denominator)
    hi_power = up.divide(up.multiply(hi_log, numerator), denominator)
    lo = nearest.next_minus(nearest.exp(lo_power))
    hi = nearest.next_plus(nearest.exp(hi_power))
    if not lo.is_finite() or not hi.is_finite() or not 0 < lo <= hi:
        raise NumericFailure('Invalid factor enclosure')
    return lo, hi


def amount_enclosure(amount, factor_lower, factor_upper, precision):
    if amount < 0:
        raise NumericFailure('Negative amount is not admitted')
    if amount == 0:
        return Decimal(0), Decimal(0)
    lo = working_context(precision, ROUND_FLOOR).multiply(amount, factor_lower)
    hi = working_context(precision, ROUND_CEILING).multiply(amount, factor_upper)
    if not lo.is_finite() or not hi.is_finite() or not 0 < lo <= hi:
        raise NumericFailure('Invalid amount enclosure')
    return lo, hi


def calculate(amount, rate, days):
    if (not isinstance(amount, Decimal) or not isinstance(rate, Decimal)
            or not amount.is_finite() or not rate.is_finite()
            or amount < 0 or rate <= -1 or type(days) is not int or days < 0):
        raise NumericFailure('Inputs outside admitted numeric domain')
    if days == 0 or rate == 0:
        return '1', canonical_decimal34(amount)
    for precision in PRECISIONS:
        try:
            lo, hi = factor_enclosure(rate, days, precision)
            alo, ahi = amount_enclosure(amount, lo, hi, precision)
            flo, fhi = canonical_decimal34(lo), canonical_decimal34(hi)
            plo, phi = canonical_decimal34(alo), canonical_decimal34(ahi)
            if flo == fhi and plo == phi:
                return flo, plo
        except (DecimalException, NumericFailure, OverflowError, ValueError):
            # A failed enclosure is not evidence. Restart at the next fixed step.
            continue
    raise NumericFailure('Both rounding cells were not certified within the seven-step boundary')
