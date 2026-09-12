"""M06 historical evidence reads only.

The original calculation primitives remain unchanged for historical integrity.
The old M02/M03/M04/M05 source binding and mutation paths are removed. No new
conversion uses these archival records as current authority.
"""
from __future__ import annotations
from datetime import date
from decimal import Decimal, DecimalException, InvalidOperation, ROUND_HALF_UP, localcontext
import hashlib
import json
from typing import Any
from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.m06_conversion import (
    M06CalculationManifest, M06CoefficientEvidence, M06ConversionRevision,
    M06ConversionSubject, M06WarningDisposition,
)
from app.schemas.m06_conversion import (
    DECIMAL_PATTERN, M06CoefficientResponse, M06EligibilityResponse,
    M06ManifestResponse, M06RevisionResponse, M06SubjectResponse,
)

FORMULAS = {
    "balance_to_monthly_pension": ("m06.balance_to_monthly_pension.v1", "ILS/month"),
    "monthly_pension_to_capital_equivalent": ("m06.monthly_pension_to_capital_equivalent.v1", "ILS capital equivalent"),
}
REFERENCE_CODE = "reference_unavailable"
REFERENCE_MESSAGE = "referenced conversion evidence is unavailable"

class M06ConversionError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        self.status_code, self.code, self.message = status_code, code, message
        super().__init__(message)


def _error(
    code: str, message: str, status_code: int = status.HTTP_409_CONFLICT
) -> M06ConversionError:
    return M06ConversionError(status_code, code, message)


def _unavailable() -> M06ConversionError:
    return M06ConversionError(
        status.HTTP_404_NOT_FOUND, REFERENCE_CODE, REFERENCE_MESSAGE
    )


def _canonical(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (date,)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _canonical(value[k]) for k in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    return value


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            _canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
    ).hexdigest()


def _semantic_list_key(value: Any) -> str:
    return json.dumps(
        _canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def _canonical_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    result = _canonical(manifest)
    for key in ("warnings", "informational_warnings", "blocking_reasons"):
        values = result.get(key)
        if isinstance(values, list):
            result[key] = sorted(values, key=_semantic_list_key)
    predecessors = result.get("predecessors")
    if isinstance(predecessors, dict):
        for key in ("m05_warning_snapshot", "m05_warning_dispositions"):
            values = predecessors.get(key)
            if isinstance(values, list):
                predecessors[key] = sorted(values, key=_semantic_list_key)
    return result


def _manifest_fingerprint(manifest: dict[str, Any]) -> str:
    return _digest(
        _canonical_manifest(
            {key: value for key, value in manifest.items() if key != "fingerprint"}
        )
    )


def _identity(value: str) -> str:
    return hashlib.sha256(value.strip().casefold().encode()).hexdigest()


def _subject_digest(row: M06ConversionSubject) -> str:
    return _digest(
        {
            "client_id": row.client_id,
            "m05_subject_id": row.m05_subject_id,
            "provider": row.provider_identity_digest,
            "account": row.account_identity_digest,
            "product": row.product_context_digest,
            "mode": row.mode,
            "input_identity": row.input_identity,
        }
    )


def _revision_digest(row: M06ConversionRevision) -> str:
    return _digest(
        {
            "subject_id": row.subject_id,
            "client_id": row.client_id,
            "predecessor_revision_id": row.predecessor_revision_id,
            "revision_sequence": row.revision_sequence,
            "state": row.state,
            "action_type": row.action_type,
            "mode": row.mode,
            "formula_id": row.formula_id,
            "input_identity": row.input_identity,
            "input_amount": row.input_amount,
            "input_date": row.input_date,
            "m02_intake_id": row.m02_intake_id,
            "m03_revision_id": row.m03_revision_id,
            "m04_revision_id": row.m04_revision_id,
            "m05_revision_id": row.m05_revision_id,
            "predecessor_snapshot": row.predecessor_snapshot,
            "warnings": row.warnings,
            "blocking_reasons": row.blocking_reasons,
            "informational_warnings": row.informational_warnings,
            "reason_code": row.reason_code,
            "explanation": row.explanation,
            "actor": row.actor,
        }
    )


def _decimal_text(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _coefficient(value: Any) -> Decimal:
    if value is None:
        raise _error("coefficient_missing", "coefficient is required", 422)
    if not isinstance(value, str) or DECIMAL_PATTERN.fullmatch(value) is None:
        raise _error(
            "coefficient_invalid",
            "coefficient must be a canonical plain decimal string",
            422,
        )
    if len(value) > 512:
        raise _error(
            "numeric_value_out_of_supported_range",
            "coefficient exceeds supported precision",
            422,
        )
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise _error("coefficient_invalid", "coefficient is invalid", 422) from exc
    if not result.is_finite():
        raise _error("coefficient_invalid", "coefficient must be finite", 422)
    if result == 0:
        raise _error("coefficient_zero", "coefficient must be greater than zero", 422)
    if result < 0:
        raise _error(
            "coefficient_negative", "coefficient must be greater than zero", 422
        )
    if len(result.as_tuple().digits) > 500:
        raise _error(
            "numeric_value_out_of_supported_range",
            "coefficient exceeds supported precision",
            422,
        )
    return result


def _subject(db: Session, client_id: int, subject_id: str) -> M06ConversionSubject:
    row = db.scalar(
        select(M06ConversionSubject).where(
            M06ConversionSubject.subject_id == subject_id,
            M06ConversionSubject.client_id == client_id,
        )
    )
    if row is None:
        raise _unavailable()
    return row


def _history(db: Session, subject: M06ConversionSubject) -> list[M06ConversionRevision]:
    if subject.semantic_digest != _subject_digest(subject):
        raise _error(
            "conversion_chain_inconsistent",
            "conversion subject identity is inconsistent",
        )
    rows = list(
        db.scalars(
            select(M06ConversionRevision)
            .where(
                M06ConversionRevision.subject_id == subject.subject_id,
                M06ConversionRevision.client_id == subject.client_id,
            )
            .order_by(M06ConversionRevision.revision_sequence)
        )
    )
    for index, row in enumerate(rows):
        if (
            row.revision_sequence != index + 1
            or (index and row.predecessor_revision_id != rows[index - 1].revision_id)
            or row.mode != subject.mode
            or row.input_identity != subject.input_identity
            or FORMULAS.get(row.mode, (None,))[0] != row.formula_id
            or row.evidence_digest != _revision_digest(row)
        ):
            raise _error(
                "conversion_chain_inconsistent",
                "conversion revision chain is inconsistent",
            )
    return rows


def _current(db: Session, subject: M06ConversionSubject) -> M06ConversionRevision:
    rows = _history(db, subject)
    if not rows:
        raise _unavailable()
    return rows[-1]


def _coefficient_row(db: Session, revision_id: str) -> M06CoefficientEvidence:
    row = db.scalar(
        select(M06CoefficientEvidence).where(
            M06CoefficientEvidence.revision_id == revision_id
        )
    )
    if row is None:
        raise _error("manifest_integrity_invalid", "coefficient evidence is incomplete")
    return row


def _manifest_row(db: Session, revision_id: str) -> M06CalculationManifest | None:
    return db.scalar(
        select(M06CalculationManifest).where(
            M06CalculationManifest.revision_id == revision_id
        )
    )


def _calculate(
    row: M06ConversionRevision, evidence: M06CoefficientEvidence
) -> tuple[str, str | None, str | None, str | None, str]:
    if row.input_amount is None:
        raise _error("input_amount_missing", "authoritative input is missing")
    try:
        amount = Decimal(row.input_amount)
        coefficient = _coefficient(evidence.coefficient_text)
        if not amount.is_finite():
            raise _error(
                "numeric_value_out_of_supported_range",
                "authoritative input is not finite",
                422,
            )
        if amount < 0:
            raise _error("input_amount_negative", "authoritative input is negative")
        precision = (
            len(amount.as_tuple().digits) + len(coefficient.as_tuple().digits) + 20
        )
        if precision > 1000:
            raise _error(
                "numeric_value_out_of_supported_range",
                "calculation exceeds supported exact numeric limits",
                422,
            )
        if row.mode == "balance_to_monthly_pension":
            raw_kind, raw_decimal, numerator, denominator = (
                "exact_ratio",
                None,
                format(amount, "f"),
                evidence.coefficient_text,
            )
            with localcontext() as context:
                context.prec = max(50, precision)
                display_source = amount / coefficient
                display = format(
                    display_source.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                    "f",
                )
        else:
            with localcontext() as context:
                context.prec = max(50, precision)
                exact = amount * coefficient
                raw_kind, raw_decimal, numerator, denominator = (
                    "exact_decimal",
                    _decimal_text(exact),
                    None,
                    None,
                )
                display = format(
                    exact.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), "f"
                )
    except M06ConversionError:
        raise
    except (DecimalException, OverflowError) as exc:
        raise _error(
            "numeric_value_out_of_supported_range",
            "calculation exceeds supported exact numeric limits",
            422,
        ) from exc
    if len(display) > 96:
        raise _error(
            "numeric_value_out_of_supported_range",
            "display result exceeds supported storage limits",
            422,
        )
    return raw_kind, raw_decimal, numerator, denominator, display


def _coefficient_digest(evidence: M06CoefficientEvidence) -> str:
    intent = _intent_from_evidence(evidence)
    payload = intent.model_dump(mode="json") | {
        "client_id": evidence.client_id,
        "subject_id": evidence.subject_id,
        "revision_id": evidence.revision_id,
        "mode": evidence.mode,
        "provider": evidence.provider_context,
        "product": evidence.product_context,
        "actor": evidence.actor,
    }
    return _digest(payload)


def _manifest_integrity_reasons(
    leaf: M06ConversionRevision,
    coefficient: M06CoefficientEvidence,
    manifest: M06CalculationManifest | None,
) -> list[str]:
    if manifest is None:
        return ["manifest_integrity_invalid"]
    if (
        manifest.fingerprint != _manifest_fingerprint(manifest.manifest)
        or manifest.manifest.get("fingerprint") != manifest.fingerprint
        or manifest.manifest.get("formula_id") != leaf.formula_id
        or manifest.manifest.get("input_identity") != leaf.input_identity
        or manifest.manifest.get("coefficient_evidence_id") != coefficient.evidence_id
        or manifest.manifest.get("predecessors") != leaf.predecessor_snapshot
    ):
        return ["manifest_integrity_invalid"]
    handoff = manifest.manifest.get("authoritative_downstream_handoff")
    fingerprinted_amount = handoff.get("amount") if isinstance(handoff, dict) else None
    if manifest.authoritative_monthly_amount != fingerprinted_amount:
        return ["authoritative_downstream_handoff_integrity_invalid"]
    return []


def _eligibility_response(
    db: Session,
    subject: M06ConversionSubject,
    assessed: M06ConversionRevision,
    current: M06ConversionRevision,
) -> M06EligibilityResponse:
    if assessed.revision_id != current.revision_id:
        return M06EligibilityResponse(
            subject_id=subject.subject_id,
            assessed_revision_id=assessed.revision_id,
            eligible_for_downstream=False,
            current_revision_id=current.revision_id,
            exclusion_reasons=["conversion_not_current"],
            informational_warnings=assessed.informational_warnings,
        )
    reasons: list[str] = []
    if assessed.state == "draft":
        reasons.append("conversion_draft")
        if assessed.action_type == "resolve" and any(
            item.get("classification") == "mandatory" for item in assessed.warnings
        ):
            reasons.append("warning_not_reviewed")
    elif assessed.state == "blocked":
        reasons.append("conversion_blocked")
    elif assessed.state == "superseded":
        reasons.append("conversion_superseded")
    elif assessed.state not in {"resolved", "warning_reviewed"}:
        reasons.append("conversion_chain_inconsistent")
    upstream, info = _revalidation_reasons(db, subject, assessed)
    reasons.extend(upstream)
    return M06EligibilityResponse(
        subject_id=subject.subject_id,
        assessed_revision_id=assessed.revision_id,
        eligible_for_downstream=not reasons,
        current_revision_id=current.revision_id,
        exclusion_reasons=list(dict.fromkeys(reasons)),
        informational_warnings=info,
    )


def eligibility(db: Session, client_id: int, subject_id: str) -> M06EligibilityResponse:
    subject = _subject(db, client_id, subject_id)
    leaf = _current(db, subject)
    return _eligibility_response(db, subject, leaf, leaf)


def revision_eligibility(
    db: Session, client_id: int, subject_id: str, revision_id: str
) -> M06EligibilityResponse:
    subject = _subject(db, client_id, subject_id)
    rows = _history(db, subject)
    assessed = next((row for row in rows if row.revision_id == revision_id), None)
    if assessed is None or not rows:
        raise _unavailable()
    return _eligibility_response(db, subject, assessed, rows[-1])


def revision_response(db: Session, row: M06ConversionRevision) -> M06RevisionResponse:
    evidence = _coefficient_row(db, row.revision_id)
    if evidence.evidence_digest != _coefficient_digest(evidence):
        raise _error(
            "conversion_chain_inconsistent", "coefficient evidence is inconsistent"
        )
    manifest = _manifest_row(db, row.revision_id)
    dispositions = list(
        db.scalars(
            select(M06WarningDisposition)
            .where(M06WarningDisposition.revision_id == row.revision_id)
            .order_by(M06WarningDisposition.warning_id)
        )
    )
    return M06RevisionResponse(
        revision_id=row.revision_id,
        subject_id=row.subject_id,
        predecessor_revision_id=row.predecessor_revision_id,
        revision_sequence=row.revision_sequence,
        state=row.state,
        action_type=row.action_type,
        mode=row.mode,
        formula_id=row.formula_id,
        input_identity=row.input_identity,
        input_amount=row.input_amount,
        input_date=row.input_date,
        predecessor_snapshot=row.predecessor_snapshot,
        warnings=row.warnings,
        blocking_reasons=row.blocking_reasons,
        informational_warnings=row.informational_warnings,
        coefficient=M06CoefficientResponse(
            evidence_id=evidence.evidence_id,
            authority_class=evidence.authority_class,
            coefficient=evidence.coefficient_text,
            decimal_precision=evidence.decimal_precision,
            decimal_exponent=evidence.decimal_exponent,
            source_intake_id=evidence.source_intake_id,
            source_locator=evidence.source_locator,
            source_note=evidence.source_note,
            reason=evidence.reason,
            effective_from=evidence.effective_from,
            effective_to=evidence.effective_to,
            applicability_declared=evidence.applicability_declared,
            metadata=evidence.metadata_snapshot,
            actor=evidence.actor,
            created_at=evidence.created_at,
        ),
        manifest=(
            M06ManifestResponse(
                manifest_id=manifest.manifest_id,
                fingerprint=manifest.fingerprint,
                raw_result_kind=manifest.raw_result_kind,
                raw_decimal=manifest.raw_decimal,
                raw_numerator=manifest.raw_numerator,
                raw_denominator=manifest.raw_denominator,
                display_result=manifest.display_result,
                authoritative_monthly_amount=getattr(
                    manifest, "authoritative_monthly_amount", None
                ),
                evidence=manifest.manifest,
            )
            if manifest
            else None
        ),
        warning_dispositions=[
            {
                "disposition_id": item.disposition_id,
                "warning_id": item.warning_id,
                "reason": item.reason,
                "confirmed": item.confirmed,
                "actor": item.actor,
                "actor_is_authentication": False,
                "created_at": item.created_at,
            }
            for item in dispositions
        ],
        actor=row.actor,
        created_at=row.created_at,
    )


def history(db: Session, client_id: int, subject_id: str) -> list[M06RevisionResponse]:
    subject = _subject(db, client_id, subject_id)
    return [revision_response(db, row) for row in _history(db, subject)]


def subject_response(
    db: Session, client_id: int, subject_id: str
) -> M06SubjectResponse:
    subject = _subject(db, client_id, subject_id)
    leaf = _current(db, subject)
    return M06SubjectResponse(
        subject_id=subject.subject_id,
        client_id=client_id,
        m05_subject_id=subject.m05_subject_id,
        mode=subject.mode,
        input_identity=subject.input_identity,
        current_revision=revision_response(db, leaf),
        eligibility=eligibility(db, client_id, subject_id),
    )


def list_subjects(db: Session, client_id: int) -> list[M06SubjectResponse]:
    rows = list(
        db.scalars(
            select(M06ConversionSubject)
            .where(M06ConversionSubject.client_id == client_id)
            .order_by(M06ConversionSubject.created_at)
        )
    )
    return [subject_response(db, client_id, row.subject_id) for row in rows]

def _revalidation_reasons(db, subject, leaf):
    return ["LEGACY_CONVERSION_ARCHIVE_ONLY"], []
