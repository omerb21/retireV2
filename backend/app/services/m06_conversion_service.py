from __future__ import annotations

from datetime import date
from decimal import (
    Decimal,
    DecimalException,
    InvalidOperation,
    ROUND_HALF_UP,
    localcontext,
)
import hashlib
import json
from typing import Any

from fastapi import status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.models.m02_intake import M02IntakeRecord
from app.models.m04_classification import (
    M04ClassificationRevision,
    M04ComponentDecision,
)
from app.models.m05_ledger import M05LedgerSubject
from app.models.m06_conversion import (
    M06CalculationManifest,
    M06CoefficientEvidence,
    M06ConversionRevision,
    M06ConversionSubject,
    M06WarningDisposition,
    M06_WORKFLOW_ACTOR,
    authorize_m06_insert,
    m06_server_timestamp,
)
from app.schemas.m06_conversion import (
    DECIMAL_PATTERN,
    M06CandidateResponse,
    M06CoefficientCorrectionRequest,
    M06CoefficientIntent,
    M06CoefficientResponse,
    M06EligibilityResponse,
    M06ManifestResponse,
    M06RevisionResponse,
    M06StartRequest,
    M06SubjectResponse,
    M06SupersedeRequest,
    M06WarningReviewRequest,
)
from app.services.m05_ledger_service import eligibility as m05_eligibility
from app.services.m05_ledger_service import list_subjects as m05_list_subjects
from app.services.m05_ledger_service import subject_response as m05_subject_response
from app.services.m03_review_service import target_response as m03_target_response
from app.services.m04_classification_service import eligibility as m04_eligibility


FORMULAS = {
    "balance_to_monthly_pension": ("m06.balance_to_monthly_pension.v1", "ILS/month"),
    "monthly_pension_to_capital_equivalent": (
        "m06.monthly_pension_to_capital_equivalent.v1",
        "ILS capital equivalent",
    ),
}
SUPPORTED_FAMILIES = {"pension_fund", "insurance_policy"}
MANDATORY_WARNINGS = {
    "planner_declared_coefficient_authority",
    "coefficient_applicability_not_documented",
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


def _manifest_fingerprint(manifest: dict[str, Any]) -> str:
    return _digest(
        {key: value for key, value in manifest.items() if key != "fingerprint"}
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


def _current_m04_component(
    db: Session, revision_id: str, identity: str
) -> M04ComponentDecision | None:
    return db.scalar(
        select(M04ComponentDecision).where(
            M04ComponentDecision.revision_id == revision_id,
            M04ComponentDecision.evidence_identity == identity,
        )
    )


def _candidate_rows(db: Session, client_id: int) -> list[M06CandidateResponse]:
    result: list[M06CandidateResponse] = []
    try:
        subjects = m05_list_subjects(db, client_id)
    except Exception as exc:
        raise _unavailable() from exc
    for subject in subjects:
        current = subject.current_revision
        if current is None or not subject.eligibility.eligible_for_m06:
            continue
        family = str(current.product_context.get("m04_product_family") or "")
        if (
            family not in SUPPORTED_FAMILIES
            or current.product_context.get("m04_aggregate_interpretation") != "pension"
        ):
            continue
        for component in current.values:
            if (
                component.component_kind != "contribution_component"
                or not component.included_in_reconciliation
            ):
                continue
            decision = _current_m04_component(
                db, current.m04_revision_id, component.evidence_identity
            )
            if (
                decision is None
                or decision.interpretation != "pension"
                or decision.current_employer_related != "no"
            ):
                continue
            intake = db.scalar(
                select(M02IntakeRecord).where(
                    M02IntakeRecord.intake_id == current.intake_id,
                    M02IntakeRecord.client_id == client_id,
                )
            )
            if (
                intake is None
                or intake.record_kind != "manual"
                or intake.lifecycle_status != "accepted_for_review"
            ):
                continue
            for mode, (formula, _unit) in FORMULAS.items():
                if mode == "balance_to_monthly_pension":
                    amount = component.effective_value
                    input_identity = component.evidence_identity
                    input_date = current.statement_date
                else:
                    amount = intake.declared_monthly_pension_amount
                    input_identity = (
                        f"{intake.intake_id}:declared_monthly_pension_amount"
                    )
                    input_date = intake.declared_statement_date
                reasons: list[str] = []
                if amount is None:
                    reasons.append("input_amount_missing")
                elif amount < 0:
                    reasons.append("input_amount_negative")
                if input_date is None:
                    reasons.append("relevant_source_date_missing")
                candidate_payload = {
                    "m05_subject_id": subject.subject_id,
                    "m05_revision_id": current.revision_id,
                    "mode": mode,
                    "input_identity": input_identity,
                }
                result.append(
                    M06CandidateResponse(
                        candidate_id=f"M06-CAND-{_digest(candidate_payload)[:40]}",
                        m05_subject_id=subject.subject_id,
                        m05_revision_id=current.revision_id,
                        m02_intake_id=current.intake_id,
                        provider_name=current.provider_name,
                        account_reference=current.account_reference,
                        product_family=family,
                        mode=mode,
                        input_identity=input_identity,
                        input_amount=None if amount is None else format(amount, "f"),
                        input_date=input_date,
                        formula_id=formula,
                        eligible=not reasons,
                        exclusion_reasons=reasons,
                        informational_warnings=list(
                            subject.eligibility.informational_warnings
                        ),
                    )
                )
    return result


def list_candidates(db: Session, client_id: int) -> list[M06CandidateResponse]:
    return _candidate_rows(db, client_id)


def _candidate(
    db: Session, client_id: int, request: M06StartRequest
) -> M06CandidateResponse:
    row = next(
        (
            item
            for item in _candidate_rows(db, client_id)
            if item.m05_subject_id == request.m05_subject_id
            and item.mode == request.mode
            and item.input_identity == request.input_identity
        ),
        None,
    )
    if row is None:
        raise _unavailable()
    return row


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


def _assert_expected(row: M06ConversionRevision, expected: str) -> None:
    if row.revision_id != expected:
        raise _error(
            "conversion_revision_stale", "expected current conversion revision is stale"
        )


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


def _documentary_valid(
    db: Session, client_id: int, intent: M06CoefficientIntent
) -> bool:
    intake = db.scalar(
        select(M02IntakeRecord).where(
            M02IntakeRecord.intake_id == intent.source_intake_id,
            M02IntakeRecord.client_id == client_id,
            M02IntakeRecord.record_kind == "uploaded_source",
            M02IntakeRecord.lifecycle_status == "accepted_for_review",
        )
    )
    if intake is None:
        return False
    try:
        target = m03_target_response(db, client_id, intake.intake_id)
    except Exception:
        return False
    return bool(
        target.eligible
        and target.target_kind == "source_evidence_review"
        and target.accepted_revision_id
        and target.source_id
        and target.blob_id
        and target.sha256_checksum
    )


def _evidence_values(
    db: Session,
    client_id: int,
    candidate: M06CandidateResponse,
    intent: M06CoefficientIntent,
) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[dict[str, Any]] = []
    blockers: list[str] = list(candidate.exclusion_reasons)
    coeff = _coefficient(intent.coefficient)
    if (
        intent.effective_from
        and intent.effective_to
        and intent.effective_from > intent.effective_to
    ):
        blockers.append("coefficient_date_contradiction")
    if candidate.input_date is None:
        blockers.append("relevant_source_date_missing")
    elif intent.effective_from and candidate.input_date < intent.effective_from:
        blockers.append("coefficient_date_contradiction")
    elif intent.effective_to and candidate.input_date > intent.effective_to:
        blockers.append("coefficient_date_contradiction")
    if intent.authority_class == "documentary":
        if not _documentary_valid(db, client_id, intent):
            blockers.append("coefficient_provenance_missing")
        if not intent.effective_from and not intent.effective_to:
            if intent.applicability_declared:
                warnings.append(
                    {
                        "warning_id": "coefficient_applicability_not_documented",
                        "classification": "mandatory",
                    }
                )
            else:
                blockers.append("coefficient_applicability_missing")
    else:
        warnings.append(
            {
                "warning_id": "planner_declared_coefficient_authority",
                "classification": "mandatory",
            }
        )
        warnings.append(
            {
                "warning_id": "coefficient_applicability_not_documented",
                "classification": "mandatory",
            }
        )
    del coeff
    return warnings, list(dict.fromkeys(blockers))


def _predecessor_snapshot(
    db: Session, client_id: int, candidate: M06CandidateResponse
) -> dict[str, Any]:
    current = m05_subject_response(
        db, client_id, candidate.m05_subject_id
    ).current_revision
    if current is None or current.revision_id != candidate.m05_revision_id:
        raise _unavailable()
    m04 = db.scalar(
        select(M04ClassificationRevision).where(
            M04ClassificationRevision.revision_id == current.m04_revision_id,
            M04ClassificationRevision.client_id == client_id,
        )
    )
    if m04 is None:
        raise _unavailable()
    return {
        "client_id": client_id,
        "m02_intake_id": current.intake_id,
        "m03_revision_id": current.m03_revision_id,
        "m03_provenance_digest": _digest(
            {"revision_id": current.m03_revision_id, "intake_id": current.intake_id}
        ),
        "m04_revision_id": current.m04_revision_id,
        "m04_evidence_digest": m04.evidence_digest,
        "m04_catalogue_version": m04.catalogue_version,
        "m04_input_snapshot_digest": _digest(m04.input_snapshot),
        "m05_subject_id": current.subject_id,
        "m05_revision_id": current.revision_id,
        "m05_candidate_id": current.candidate_id,
        "m05_source_snapshot_digest": current.source_snapshot_digest,
        "m05_mapping_digest": current.mapping_digest,
        "product_context": current.product_context,
        "provider_name": current.provider_name,
        "account_reference": current.account_reference,
        "m05_warning_snapshot": current.warnings,
        "m05_warning_dispositions": current.warning_dispositions,
        "currency_confirmation": current.currency_confirmation_evidence,
        "statement_date": current.statement_date,
        "evaluation_date": current.evaluation_date,
    }


def _make_evidence(
    revision: M06ConversionRevision,
    intent: M06CoefficientIntent,
    provider: str,
    product: dict[str, Any],
) -> M06CoefficientEvidence:
    decimal = _coefficient(intent.coefficient)
    payload = intent.model_dump(mode="json") | {
        "client_id": revision.client_id,
        "subject_id": revision.subject_id,
        "revision_id": revision.revision_id,
        "mode": revision.mode,
        "provider": provider,
        "product": product,
        "actor": M06_WORKFLOW_ACTOR,
    }
    row = M06CoefficientEvidence(
        revision_id=revision.revision_id,
        subject_id=revision.subject_id,
        client_id=revision.client_id,
        authority_class=intent.authority_class,
        coefficient_text=intent.coefficient,
        decimal_precision=len(decimal.as_tuple().digits),
        decimal_exponent=decimal.as_tuple().exponent,
        source_intake_id=intent.source_intake_id,
        source_locator=intent.source_locator,
        source_note=intent.source_note,
        reason=intent.reason,
        provider_context=provider,
        product_context=product,
        mode=revision.mode,
        unit_semantics=FORMULAS[revision.mode][1],
        effective_from=intent.effective_from,
        effective_to=intent.effective_to,
        applicability_declared=intent.applicability_declared,
        metadata_snapshot=intent.metadata.model_dump(mode="json", exclude_none=True),
        evidence_digest=_digest(payload),
        actor=M06_WORKFLOW_ACTOR,
        created_at=m06_server_timestamp(),
    )
    authorize_m06_insert(row)
    return row


def _revision(
    subject: M06ConversionSubject,
    predecessor: M06ConversionRevision | None,
    *,
    state: str,
    action: str,
    candidate: M06CandidateResponse,
    snapshot: dict[str, Any],
    warnings: list[dict[str, Any]],
    blockers: list[str],
    reason: str | None = None,
) -> M06ConversionRevision:
    row = M06ConversionRevision(
        subject_id=subject.subject_id,
        client_id=subject.client_id,
        predecessor_revision_id=predecessor.revision_id if predecessor else None,
        revision_sequence=(predecessor.revision_sequence + 1 if predecessor else 1),
        state=state,
        action_type=action,
        mode=candidate.mode,
        formula_id=candidate.formula_id,
        input_identity=candidate.input_identity,
        input_amount=candidate.input_amount,
        input_date=candidate.input_date,
        m02_intake_id=candidate.m02_intake_id,
        m03_revision_id=snapshot["m03_revision_id"],
        m04_revision_id=snapshot["m04_revision_id"],
        m05_revision_id=snapshot["m05_revision_id"],
        predecessor_snapshot=_canonical(snapshot),
        warnings=warnings,
        blocking_reasons=blockers,
        informational_warnings=candidate.informational_warnings,
        reason_code=reason,
        explanation=reason,
        evidence_digest="0" * 64,
        actor=M06_WORKFLOW_ACTOR,
        created_at=m06_server_timestamp(),
    )
    row.evidence_digest = _revision_digest(row)
    authorize_m06_insert(row)
    return row


def start_conversion(
    db: Session, client_id: int, request: M06StartRequest
) -> M06ConversionRevision:
    candidate = _candidate(db, client_id, request)
    snapshot = _predecessor_snapshot(db, client_id, candidate)
    m05_subject = db.scalar(
        select(M05LedgerSubject).where(
            M05LedgerSubject.subject_id == candidate.m05_subject_id,
            M05LedgerSubject.client_id == client_id,
        )
    )
    if m05_subject is None:
        raise _unavailable()
    product_digest = _digest(snapshot["product_context"])
    semantic = _digest(
        {
            "client_id": client_id,
            "m05_subject_id": candidate.m05_subject_id,
            "provider": m05_subject.provider_identity_digest,
            "account": m05_subject.account_identity_digest,
            "product": product_digest,
            "mode": candidate.mode,
            "input_identity": candidate.input_identity,
        }
    )
    if db.scalar(
        select(M06ConversionSubject).where(
            M06ConversionSubject.semantic_digest == semantic
        )
    ):
        raise _error("conversion_subject_conflict", "conversion subject already exists")
    warnings, blockers = _evidence_values(db, client_id, candidate, request.coefficient)
    subject = M06ConversionSubject(
        client_id=client_id,
        m05_subject_id=candidate.m05_subject_id,
        mode=candidate.mode,
        input_identity=candidate.input_identity,
        provider_identity_digest=m05_subject.provider_identity_digest,
        account_identity_digest=m05_subject.account_identity_digest,
        product_context_digest=product_digest,
        semantic_digest=semantic,
        created_at=m06_server_timestamp(),
    )
    authorize_m06_insert(subject)
    try:
        db.add(subject)
        db.flush()
        revision = _revision(
            subject,
            None,
            state="draft",
            action="start",
            candidate=candidate,
            snapshot=snapshot,
            warnings=warnings,
            blockers=blockers,
        )
        db.add(revision)
        db.flush()
        db.add(
            _make_evidence(
                revision,
                request.coefficient,
                candidate.provider_name,
                snapshot["product_context"],
            )
        )
        db.commit()
        db.refresh(revision)
        return revision
    except (IntegrityError, OperationalError) as exc:
        db.rollback()
        raise _error(
            "conversion_subject_conflict", "conversion subject already exists"
        ) from exc
    except Exception:
        db.rollback()
        raise


def _candidate_from_revision(row: M06ConversionRevision) -> M06CandidateResponse:
    snapshot = row.predecessor_snapshot
    return M06CandidateResponse(
        candidate_id="snapshot",
        m05_subject_id=snapshot["m05_subject_id"],
        m05_revision_id=snapshot["m05_revision_id"],
        m02_intake_id=row.m02_intake_id,
        provider_name="snapshot",
        account_reference="snapshot",
        product_family=str(snapshot["product_context"].get("m04_product_family") or ""),
        mode=row.mode,
        input_identity=row.input_identity,
        input_amount=row.input_amount,
        input_date=row.input_date,
        formula_id=row.formula_id,
        eligible=not row.blocking_reasons,
        exclusion_reasons=row.blocking_reasons,
        informational_warnings=row.informational_warnings,
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


def _intent_from_evidence(evidence: M06CoefficientEvidence) -> M06CoefficientIntent:
    return M06CoefficientIntent(
        authority_class=evidence.authority_class,
        coefficient=evidence.coefficient_text,
        source_intake_id=evidence.source_intake_id,
        source_locator=evidence.source_locator,
        source_note=evidence.source_note,
        reason=evidence.reason,
        effective_from=evidence.effective_from,
        effective_to=evidence.effective_to,
        applicability_declared=evidence.applicability_declared,
        metadata=evidence.metadata_snapshot,
    )


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


def _manifest(
    revision: M06ConversionRevision,
    evidence: M06CoefficientEvidence,
    *,
    calculate: bool = True,
) -> M06CalculationManifest:
    if calculate:
        raw_kind, raw_decimal, numerator, denominator, display = _calculate(
            revision, evidence
        )
    else:
        raw_kind = raw_decimal = numerator = denominator = display = None
    manifest = {
        "manifest_schema_version": "m06-manifest-v1",
        "calculation_contract_version": "pkg-011-v1",
        "algorithm_version": "m06-conversion-v1",
        "subject_id": revision.subject_id,
        "revision_id": revision.revision_id,
        "predecessor_revision_id": revision.predecessor_revision_id,
        "revision_sequence": revision.revision_sequence,
        "client_id": revision.client_id,
        "formula_id": revision.formula_id,
        "mode": revision.mode,
        "input_identity": revision.input_identity,
        "input_amount": revision.input_amount,
        "input_unit": (
            "ILS/month"
            if revision.mode == "monthly_pension_to_capital_equivalent"
            else "ILS balance"
        ),
        "input_date": revision.input_date,
        "coefficient_evidence_id": evidence.evidence_id,
        "coefficient": evidence.coefficient_text,
        "coefficient_precision": evidence.decimal_precision,
        "coefficient_exponent": evidence.decimal_exponent,
        "coefficient_authority_class": evidence.authority_class,
        "coefficient_digest": evidence.evidence_digest,
        "coefficient_provenance": {
            "source_intake_id": evidence.source_intake_id,
            "source_locator": evidence.source_locator,
            "source_note": evidence.source_note,
            "reason": evidence.reason,
            "effective_from": evidence.effective_from,
            "effective_to": evidence.effective_to,
            "applicability_declared": evidence.applicability_declared,
            "provider_context": evidence.provider_context,
            "product_context": evidence.product_context,
            "dimensions": evidence.metadata_snapshot,
            "unit_semantics": evidence.unit_semantics,
        },
        "predecessors": revision.predecessor_snapshot,
        "warnings": sorted(revision.warnings, key=lambda item: item["warning_id"]),
        "informational_warnings": sorted(revision.informational_warnings),
        "blocking_reasons": sorted(revision.blocking_reasons),
        "raw_result": {
            "kind": raw_kind,
            "decimal": raw_decimal,
            "numerator": numerator,
            "denominator": denominator,
        },
        "display": {
            "value": display,
            "scale": 2,
            "rounding": "ROUND_HALF_UP",
            "unit": FORMULAS[revision.mode][1],
        },
        "actor": M06_WORKFLOW_ACTOR,
        "timestamp": revision.created_at,
    }
    manifest = _canonical(manifest)
    fingerprint = _manifest_fingerprint(manifest)
    manifest["fingerprint"] = fingerprint
    row = M06CalculationManifest(
        revision_id=revision.revision_id,
        subject_id=revision.subject_id,
        client_id=revision.client_id,
        manifest=manifest,
        fingerprint=fingerprint,
        raw_result_kind=raw_kind,
        raw_decimal=raw_decimal,
        raw_numerator=numerator,
        raw_denominator=denominator,
        display_result=display,
        created_at=m06_server_timestamp(),
    )
    authorize_m06_insert(row)
    return row


def resolve_conversion(
    db: Session, client_id: int, subject_id: str, expected: str
) -> M06ConversionRevision:
    subject = _subject(db, client_id, subject_id)
    leaf = _current(db, subject)
    _assert_expected(leaf, expected)
    if leaf.state != "draft":
        raise _error(
            "conversion_state_invalid", "only a draft conversion may be resolved"
        )
    evidence = _coefficient_row(db, leaf.revision_id)
    candidate = next(
        (
            item
            for item in _candidate_rows(db, client_id)
            if item.m05_subject_id == subject.m05_subject_id
            and item.mode == subject.mode
            and item.input_identity == subject.input_identity
        ),
        None,
    )
    blockers = list(leaf.blocking_reasons)
    warnings = list(leaf.warnings)
    if candidate is None:
        candidate = _candidate_from_revision(leaf)
        blockers.append("m05_not_eligible")
    else:
        warnings, current_blockers = _evidence_values(
            db, client_id, candidate, _intent_from_evidence(evidence)
        )
        blockers.extend(current_blockers)
        if candidate.m05_revision_id != leaf.m05_revision_id:
            blockers.append("predecessor_not_current")
    blockers = list(dict.fromkeys(blockers))
    state = "blocked" if blockers else ("draft" if warnings else "resolved")
    successor = _revision(
        subject,
        leaf,
        state=state,
        action="resolve",
        candidate=_candidate_from_revision(leaf),
        snapshot=leaf.predecessor_snapshot,
        warnings=warnings,
        blockers=blockers,
    )
    try:
        db.add(successor)
        db.flush()
        copied = _intent_from_evidence(evidence)
        next_evidence = _make_evidence(
            successor, copied, evidence.provider_context, evidence.product_context
        )
        db.add(next_evidence)
        db.flush()
        db.add(_manifest(successor, next_evidence, calculate=state != "blocked"))
        db.commit()
        db.refresh(successor)
        return successor
    except (IntegrityError, OperationalError) as exc:
        db.rollback()
        raise _error(
            "conversion_revision_stale", "another conversion action already won"
        ) from exc
    except Exception:
        db.rollback()
        raise


def review_warnings(
    db: Session, client_id: int, subject_id: str, request: M06WarningReviewRequest
) -> M06ConversionRevision:
    subject = _subject(db, client_id, subject_id)
    leaf = _current(db, subject)
    _assert_expected(leaf, request.expected_current_revision_id)
    evidence = _coefficient_row(db, leaf.revision_id)
    candidate = next(
        (
            item
            for item in _candidate_rows(db, client_id)
            if item.m05_subject_id == subject.m05_subject_id
            and item.mode == subject.mode
            and item.input_identity == subject.input_identity
        ),
        None,
    )
    recomputed_warnings: list[dict[str, Any]] = []
    recomputed_blockers = ["m05_not_eligible"] if candidate is None else []
    if candidate is not None:
        recomputed_warnings, recomputed_blockers = _evidence_values(
            db, client_id, candidate, _intent_from_evidence(evidence)
        )
        if candidate.m05_revision_id != leaf.m05_revision_id:
            recomputed_blockers.append("predecessor_not_current")
    expected = sorted(
        {
            item["warning_id"]
            for item in recomputed_warnings
            if item.get("classification") == "mandatory"
        }
    )
    if (
        leaf.state != "draft"
        or leaf.action_type != "resolve"
        or leaf.blocking_reasons
        or recomputed_blockers
        or not expected
        or leaf.warnings != recomputed_warnings
        or sorted(request.warning_ids) != expected
        or len(request.warning_ids) != len(set(request.warning_ids))
    ):
        raise _error(
            "warning_disposition_invalid",
            "warning review must match the exact current mandatory-warning set",
        )
    reason = f"{request.reason_code}: {request.explanation}"
    successor = _revision(
        subject,
        leaf,
        state="warning_reviewed",
        action="review_warnings",
        candidate=_candidate_from_revision(leaf),
        snapshot=leaf.predecessor_snapshot,
        warnings=leaf.warnings,
        blockers=[],
        reason=reason,
    )
    try:
        db.add(successor)
        db.flush()
        copied = _intent_from_evidence(evidence)
        next_evidence = _make_evidence(
            successor, copied, evidence.provider_context, evidence.product_context
        )
        db.add(next_evidence)
        db.flush()
        db.add(_manifest(successor, next_evidence))
        for warning_id in expected:
            item = M06WarningDisposition(
                revision_id=successor.revision_id,
                subject_id=subject.subject_id,
                client_id=client_id,
                warning_id=warning_id,
                reason=reason,
                confirmed=True,
                actor=M06_WORKFLOW_ACTOR,
                created_at=m06_server_timestamp(),
            )
            authorize_m06_insert(item)
            db.add(item)
        db.commit()
        db.refresh(successor)
        return successor
    except (IntegrityError, OperationalError) as exc:
        db.rollback()
        raise _error(
            "conversion_revision_stale", "another conversion action already won"
        ) from exc
    except Exception:
        db.rollback()
        raise


def correct_coefficient(
    db: Session,
    client_id: int,
    subject_id: str,
    request: M06CoefficientCorrectionRequest,
) -> M06ConversionRevision:
    subject = _subject(db, client_id, subject_id)
    leaf = _current(db, subject)
    _assert_expected(leaf, request.expected_current_revision_id)
    if leaf.state == "superseded":
        raise _error(
            "conversion_state_invalid", "a superseded conversion cannot be corrected"
        )
    candidate = _candidate(
        db,
        client_id,
        M06StartRequest(
            m05_subject_id=subject.m05_subject_id,
            mode=subject.mode,
            input_identity=subject.input_identity,
            coefficient=request.coefficient,
        ),
    )
    snapshot = _predecessor_snapshot(db, client_id, candidate)
    warnings, blockers = _evidence_values(db, client_id, candidate, request.coefficient)
    successor = _revision(
        subject,
        leaf,
        state="draft",
        action="correct_coefficient",
        candidate=candidate,
        snapshot=snapshot,
        warnings=warnings,
        blockers=blockers,
        reason=request.correction_reason,
    )
    try:
        db.add(successor)
        db.flush()
        db.add(
            _make_evidence(
                successor,
                request.coefficient,
                candidate.provider_name,
                snapshot["product_context"],
            )
        )
        db.commit()
        db.refresh(successor)
        return successor
    except (IntegrityError, OperationalError) as exc:
        db.rollback()
        raise _error(
            "conversion_revision_stale", "another conversion action already won"
        ) from exc
    except Exception:
        db.rollback()
        raise


def supersede_conversion(
    db: Session, client_id: int, subject_id: str, request: M06SupersedeRequest
) -> M06ConversionRevision:
    subject = _subject(db, client_id, subject_id)
    leaf = _current(db, subject)
    _assert_expected(leaf, request.expected_current_revision_id)
    if leaf.state == "superseded":
        raise _error("conversion_state_invalid", "conversion is already superseded")
    successor = _revision(
        subject,
        leaf,
        state="superseded",
        action="supersede",
        candidate=_candidate_from_revision(leaf),
        snapshot=leaf.predecessor_snapshot,
        warnings=leaf.warnings,
        blockers=[],
        reason=request.reason,
    )
    evidence = _coefficient_row(db, leaf.revision_id)
    copied = _intent_from_evidence(evidence)
    try:
        db.add(successor)
        db.flush()
        db.add(
            _make_evidence(
                successor, copied, evidence.provider_context, evidence.product_context
            )
        )
        db.commit()
        db.refresh(successor)
        return successor
    except (IntegrityError, OperationalError) as exc:
        db.rollback()
        raise _error(
            "conversion_revision_stale", "another conversion action already won"
        ) from exc
    except Exception:
        db.rollback()
        raise


def _revalidation_reasons(
    db: Session, subject: M06ConversionSubject, leaf: M06ConversionRevision
) -> tuple[list[str], list[str]]:
    reasons: list[str] = []
    try:
        current = m05_subject_response(db, subject.client_id, subject.m05_subject_id)
        current_eligibility = m05_eligibility(
            db, subject.client_id, subject.m05_subject_id
        )
    except Exception:
        return ["m05_predecessor_ineligible"], []
    if (
        current.current_revision is None
        or current.current_revision.revision_id != leaf.m05_revision_id
    ):
        reasons.append("m05_predecessor_changed")
    if not current_eligibility.eligible_for_m06:
        reasons.append("m05_predecessor_ineligible")
    if "archived_case" in current_eligibility.exclusion_reasons:
        reasons.append("m01_case_ineligible")
    intake = db.scalar(
        select(M02IntakeRecord).where(
            M02IntakeRecord.intake_id == leaf.m02_intake_id,
            M02IntakeRecord.client_id == subject.client_id,
        )
    )
    if (
        intake is None
        or intake.record_kind != "manual"
        or intake.lifecycle_status != "accepted_for_review"
    ):
        reasons.append("m02_predecessor_changed")
    if current.current_revision:
        if current.current_revision.m03_revision_id != leaf.m03_revision_id:
            reasons.append("m03_predecessor_changed")
        if current.current_revision.m04_revision_id != leaf.m04_revision_id:
            reasons.append("m04_predecessor_changed")
    try:
        m03 = m03_target_response(db, subject.client_id, leaf.m02_intake_id)
        if not m03.eligible:
            reasons.append("m03_predecessor_ineligible")
        if m03.accepted_revision_id != leaf.m03_revision_id:
            reasons.append("m03_predecessor_changed")
        m04 = m04_eligibility(db, subject.client_id, leaf.m02_intake_id)
        if not m04.eligible_for_m05:
            reasons.append("m04_predecessor_ineligible")
        if m04.current_revision_id != leaf.m04_revision_id:
            reasons.append("m04_predecessor_changed")
    except Exception:
        reasons.extend(["m03_predecessor_ineligible", "m04_predecessor_ineligible"])
    coefficient = _coefficient_row(db, leaf.revision_id)
    if coefficient.evidence_digest != _coefficient_digest(coefficient):
        reasons.append("provenance_invalid")
    if coefficient.authority_class == "documentary":
        intent = M06CoefficientIntent(
            authority_class="documentary",
            coefficient=coefficient.coefficient_text,
            source_intake_id=coefficient.source_intake_id,
            source_locator=coefficient.source_locator,
            source_note=coefficient.source_note,
            reason=coefficient.reason,
            effective_from=coefficient.effective_from,
            effective_to=coefficient.effective_to,
            applicability_declared=coefficient.applicability_declared,
            metadata=coefficient.metadata_snapshot,
        )
        if not _documentary_valid(db, subject.client_id, intent):
            reasons.append("coefficient_evidence_replaced")
    manifest = _manifest_row(db, leaf.revision_id)
    if leaf.state in {"resolved", "warning_reviewed"}:
        if (
            manifest is None
            or manifest.fingerprint != _manifest_fingerprint(manifest.manifest)
            or manifest.manifest.get("fingerprint") != manifest.fingerprint
        ):
            reasons.append("manifest_integrity_invalid")
        elif (
            manifest.manifest.get("formula_id") != leaf.formula_id
            or manifest.manifest.get("input_identity") != leaf.input_identity
            or manifest.manifest.get("coefficient_evidence_id")
            != coefficient.evidence_id
            or manifest.manifest.get("predecessors") != leaf.predecessor_snapshot
        ):
            reasons.append("manifest_integrity_invalid")
    return list(dict.fromkeys(reasons)), list(
        current_eligibility.informational_warnings
    )


def eligibility(db: Session, client_id: int, subject_id: str) -> M06EligibilityResponse:
    subject = _subject(db, client_id, subject_id)
    leaf = _current(db, subject)
    reasons: list[str] = []
    if leaf.state == "draft":
        reasons.append("conversion_draft")
        if leaf.action_type == "resolve" and any(
            item.get("classification") == "mandatory" for item in leaf.warnings
        ):
            reasons.append("warning_not_reviewed")
    elif leaf.state == "blocked":
        reasons.append("conversion_blocked")
    elif leaf.state == "superseded":
        reasons.append("conversion_superseded")
    elif leaf.state not in {"resolved", "warning_reviewed"}:
        reasons.append("conversion_chain_inconsistent")
    upstream, info = _revalidation_reasons(db, subject, leaf)
    reasons.extend(upstream)
    return M06EligibilityResponse(
        subject_id=subject_id,
        eligible_for_downstream=not reasons,
        current_revision_id=leaf.revision_id,
        exclusion_reasons=list(dict.fromkeys(reasons)),
        informational_warnings=info,
    )


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
