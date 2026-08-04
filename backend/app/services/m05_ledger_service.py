from __future__ import annotations

import calendar
from dataclasses import dataclass, replace
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.models.client import Client
from app.models.m02_intake import M02IntakeRecord
from app.models.m04_classification import M04ClassificationRevision, M04ComponentDecision
from app.models.m05_ledger import (
    M05_ALGORITHM_VERSION,
    M05_CURRENCY,
    M05_TARGET_KIND,
    M05_WORKFLOW_ACTOR,
    M05AdjustmentEvidence,
    M05CandidateLink,
    M05LedgerRevision,
    M05LedgerSubject,
    M05LedgerValue,
    authorize_m05_insert,
    m05_server_timestamp,
)
from app.schemas.m05_ledger import (
    MONEY_PATTERN,
    M05AdjustmentRequest,
    M05AdjustmentResponse,
    M05CandidateResponse,
    M05EligibilityResponse,
    M05ReasonRequest,
    M05RevisionResponse,
    M05ReviewWarningRequest,
    M05SubjectResponse,
    M05ValueResponse,
)
from app.services.m01_case_service import effective_lifecycle_status
from app.services.m03_review_service import M03ReviewError, target_response as m03_target
from app.services.m04_classification_service import (
    M04ClassificationError,
    eligibility as m04_eligibility,
    target_response as m04_target,
)


MAX_MONEY = Decimal("999999999999999999.99")
CENT = Decimal("0.01")
TOLERANCE = Decimal("0.50")
MUTATION_ELIGIBLE_M01 = {"draft", "intake", "analysis", "review", "delivered"}
MANDATORY_WARNINGS = {
    "reconciliation_difference_review_required",
    "negative_value_review_required",
}
INFORMATIONAL_WARNINGS = {"stale_warning", "newer_ineligible_candidate_exists"}
REVISION_PATTERN = re.compile(r"^M05-R-[0-9a-f]{32}$")
CANDIDATE_PATTERN = re.compile(r"^M05-CAND-[0-9a-f]{40}$")


class M05LedgerError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def _not_found() -> M05LedgerError:
    return M05LedgerError(404, "M05_RESOURCE_NOT_FOUND", "Resource not found")


def _conflict(code: str, message: str) -> M05LedgerError:
    return M05LedgerError(409, code, message)


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _digest(value: Any) -> str:
    encoded = json.dumps(
        _json_value(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _identity_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _canonical_numeric(value: Any) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise _conflict("required_value_missing", "A canonical predecessor value is required")
    if abs(value) > MAX_MONEY or value.quantize(CENT) != value:
        raise _conflict("required_value_missing", "Canonical predecessor value is out of range")
    result = value.quantize(CENT)
    return Decimal("0.00") if result == 0 else result


def parse_component_money(value: Any) -> Decimal:
    if not isinstance(value, str) or MONEY_PATTERN.fullmatch(value) is None:
        raise _conflict("component_mapping_invalid", "Component value is malformed")
    try:
        parsed = Decimal(value)
    except InvalidOperation as error:
        raise _conflict("component_mapping_invalid", "Component value is malformed") from error
    if not parsed.is_finite() or abs(parsed) > MAX_MONEY:
        raise _conflict("component_mapping_invalid", "Component value is out of range")
    result = parsed.quantize(CENT)
    return Decimal("0.00") if result == 0 else result


def parse_authored_money(value: str) -> Decimal:
    if not isinstance(value, str) or MONEY_PATTERN.fullmatch(value) is None:
        raise M05LedgerError(422, "M05_INVALID_MONETARY_VALUE", "A plain scale-2 decimal string is required")
    parsed = Decimal(value)
    if not parsed.is_finite() or abs(parsed) > MAX_MONEY:
        raise M05LedgerError(422, "M05_INVALID_MONETARY_VALUE", "Monetary value is out of range")
    result = parsed.quantize(CENT)
    return Decimal("0.00") if result == 0 else result


def stale_threshold(evaluation_date: date) -> date:
    year = evaluation_date.year - 1
    day = min(evaluation_date.day, calendar.monthrange(year, evaluation_date.month)[1])
    return date(year, evaluation_date.month, day)


def is_stale(statement_date: date, evaluation_date: date) -> bool:
    if statement_date > evaluation_date:
        raise _conflict("statement_date_invalid", "Statement date cannot be in the future")
    return statement_date < stale_threshold(evaluation_date)


@dataclass(frozen=True)
class CandidateContext:
    client: Client
    intake: M02IntakeRecord
    candidate_id: str
    provider_name: str
    account_reference: str
    provider_digest: str
    account_digest: str
    m03_revision_id: str
    m03_decided_at: datetime
    m04_revision_id: str
    product_context: dict[str, Any]
    statement_date: date
    source_total: Decimal
    values: tuple[dict[str, Any], ...]
    source_snapshot_digest: str
    mapping_digest: str
    evaluation_date: date
    stale: bool
    newer_ineligible: bool = False


@dataclass(frozen=True)
class CandidateEvaluation:
    candidate_id: str
    intake: M02IntakeRecord
    context: CandidateContext | None
    exclusion_reason: str | None
    authoritative: bool = False
    informational_warnings: tuple[str, ...] = ()


def _client(db: Session, client_id: int) -> Client:
    row = db.scalar(select(Client).where(Client.client_id == client_id))
    if row is None:
        raise _not_found()
    return row


def _generic_candidate_id(client_id: int, intake_id: str) -> str:
    return f"M05-CAND-{_digest({'client_id': client_id, 'intake_id': intake_id})[:40]}"


def _candidate_identity_payload(
    client_id: int,
    intake_id: str,
    target_kind: str,
    m03_revision_id: str,
    m04_revision_id: str,
) -> dict[str, Any]:
    return {
        "client_id": client_id,
        "intake_id": intake_id,
        "target_kind": target_kind,
        "m03_revision_id": m03_revision_id,
        "m04_revision_id": m04_revision_id,
    }


def _candidate_snapshot(
    candidate: M05CandidateLink, subject: M05LedgerSubject
) -> dict[str, Any]:
    identity = _candidate_identity_payload(
        candidate.client_id,
        candidate.intake_id,
        candidate.target_kind,
        candidate.m03_revision_id,
        candidate.m04_revision_id,
    )
    return {
        "candidate_id": candidate.candidate_id,
        "candidate_identity_digest": _digest(identity),
        "client_id": candidate.client_id,
        "subject_id": candidate.subject_id,
        "intake_id": candidate.intake_id,
        "target_kind": candidate.target_kind,
        "m03_revision_id": candidate.m03_revision_id,
        "m04_revision_id": candidate.m04_revision_id,
        "provider_identity_digest": subject.provider_identity_digest,
        "account_identity_digest": subject.account_identity_digest,
        "statement_date": candidate.statement_date.isoformat(),
        "m03_decided_at": _utc(candidate.m03_decided_at).isoformat(),
        "source_snapshot_digest": candidate.source_snapshot_digest,
    }


def _candidate_context(
    db: Session,
    client: Client,
    intake: M02IntakeRecord,
    *,
    evaluation_date: date | None = None,
) -> CandidateContext:
    if effective_lifecycle_status(client.status) not in MUTATION_ELIGIBLE_M01:
        raise _conflict("archived_case", "Archived client cases are read-only")
    if intake.client_id != client.client_id or intake.record_kind != "manual":
        raise _conflict("upstream_source_ineligible", "Only same-client manual records are supported")
    if intake.lifecycle_status != "accepted_for_review":
        raise _conflict("upstream_source_ineligible", "M02 intake is not accepted for review")
    provider = intake.declared_provider_name
    account = intake.declared_account_reference
    if not isinstance(provider, str) or not provider or not isinstance(account, str) or not account:
        raise _conflict("required_value_missing", "Provider and account identity are required")
    if intake.declared_statement_date is None:
        raise _conflict("required_value_missing", "Statement date is required")
    today = evaluation_date or date.today()
    stale = is_stale(intake.declared_statement_date, today)
    total = _canonical_numeric(intake.declared_total_balance_amount)

    try:
        m03 = m03_target(db, client.client_id, intake.intake_id)
    except M03ReviewError as error:
        raise _conflict("m03_ineligible", "Current M03 authority is unavailable") from error
    if (
        not m03.eligible
        or m03.target_kind != M05_TARGET_KIND
        or not m03.accepted_revision_id
        or m03.current_revision is None
        or m03.current_revision.state != "accepted"
    ):
        raise _conflict("m03_ineligible", "Current M03 authority is unavailable")

    try:
        m04_gate = m04_eligibility(db, client.client_id, intake.intake_id)
        target = m04_target(db, client.client_id, intake.intake_id)
    except M04ClassificationError as error:
        raise _conflict("m04_ineligible", "Current M04 authority is unavailable") from error
    revision = target.current_revision
    if (
        not m04_gate.eligible_for_m05
        or not m04_gate.accepted_revision_id
        or revision is None
        or revision.revision_id != m04_gate.accepted_revision_id
        or revision.state != "accepted"
        or target.target_kind != M05_TARGET_KIND
    ):
        raise _conflict("m04_ineligible", "Current M04 authority is unavailable")

    raw_components = intake.declared_component_values
    snapshot_components = revision.input_snapshot.get("components")
    decisions = revision.components
    if (
        not isinstance(raw_components, list)
        or not raw_components
        or not isinstance(snapshot_components, list)
        or len(raw_components) != len(snapshot_components)
        or len(decisions) != len(snapshot_components)
    ):
        raise _conflict("component_set_incomplete", "A complete non-empty component set is required")
    decision_by_identity = {item.evidence_identity: item for item in decisions}
    if len(decision_by_identity) != len(decisions):
        raise _conflict("component_mapping_invalid", "Component evidence identity is duplicated")

    values: list[dict[str, Any]] = []
    for index, (raw, snapshot) in enumerate(zip(raw_components, snapshot_components, strict=True)):
        if not isinstance(raw, dict) or not isinstance(snapshot, dict):
            raise _conflict("component_mapping_invalid", "Component evidence is malformed")
        label = next((str(raw[key]) for key in ("label", "component_label", "name") if raw.get(key) is not None), None)
        code = next((str(raw[key]) for key in ("code", "component_code") if raw.get(key) is not None), None)
        identity_seed = f"{index}|{code or ''}|{label or ''}"
        identity = f"component:{index}:{hashlib.sha256(identity_seed.encode('utf-8')).hexdigest()[:16]}"
        decision = decision_by_identity.get(identity)
        raw_value = raw.get("value", raw.get("amount"))
        if (
            decision is None
            or snapshot.get("evidence_identity") != identity
            or snapshot.get("original_label") != label
            or snapshot.get("original_code") != code
            or snapshot.get("declared_value") != _json_value(raw_value)
            or decision.original_label != label
            or decision.original_code != code
            or decision.component_kind not in {
                "contribution_component", "severance_component", "unknown_component"
            }
        ):
            raise _conflict("component_mapping_invalid", "M02 and M04 component evidence does not match")
        amount = parse_component_money(raw_value)
        state = "recorded_zero" if amount == 0 else "recorded_value"
        included = decision.component_kind in {"contribution_component", "severance_component"}
        values.append(
            {
                "evidence_identity": identity,
                "component_index": index,
                "original_label": label,
                "original_code": code,
                "component_kind": decision.component_kind,
                "source_state": state,
                "source_value": amount,
                "effective_state": state,
                "effective_value": amount,
                "included_in_reconciliation": included,
                "exclusion_reason": None if included else "unknown_component_not_reconcilable",
            }
        )
    if set(decision_by_identity) != {item["evidence_identity"] for item in values}:
        raise _conflict("component_set_incomplete", "Component mapping is incomplete")
    if not any(item["included_in_reconciliation"] for item in values):
        raise _conflict("component_set_incomplete", "No reconcilable component exists")

    product = {
        "product_name": intake.product_name,
        "product_identifier": intake.product_identifier,
        "declared_product_type": intake.declared_product_type,
        "m04_product_family": revision.product_family,
        "m04_aggregate_interpretation": revision.aggregate_interpretation,
    }
    source_snapshot = {
        "client_id": client.client_id,
        "intake_id": intake.intake_id,
        "target_kind": M05_TARGET_KIND,
        "provider_name": provider,
        "account_reference": account,
        "statement_date": intake.declared_statement_date,
        "total": total,
        "components": values,
        "m03_revision_id": m03.accepted_revision_id,
        "m04_revision_id": revision.revision_id,
    }
    source_digest = _digest(source_snapshot)
    mapping_digest = _digest(
        [
            {
                key: item[key]
                for key in (
                    "evidence_identity", "component_index", "original_label",
                    "original_code", "component_kind", "included_in_reconciliation",
                )
            }
            for item in values
        ]
    )
    candidate_tuple = _candidate_identity_payload(
        client.client_id,
        intake.intake_id,
        M05_TARGET_KIND,
        m03.accepted_revision_id,
        revision.revision_id,
    )
    return CandidateContext(
        client=client,
        intake=intake,
        candidate_id=f"M05-CAND-{_digest(candidate_tuple)[:40]}",
        provider_name=provider,
        account_reference=account,
        provider_digest=_identity_digest(provider),
        account_digest=_identity_digest(account),
        m03_revision_id=m03.accepted_revision_id,
        m03_decided_at=_utc(m03.current_revision.decided_at),
        m04_revision_id=revision.revision_id,
        product_context=product,
        statement_date=intake.declared_statement_date,
        source_total=total,
        values=tuple(values),
        source_snapshot_digest=source_digest,
        mapping_digest=mapping_digest,
        evaluation_date=today,
        stale=stale,
    )


def _evaluate_candidates(db: Session, client_id: int) -> list[CandidateEvaluation]:
    client = _client(db, client_id)
    intakes = list(
        db.scalars(
            select(M02IntakeRecord)
            .where(
                M02IntakeRecord.client_id == client_id,
                M02IntakeRecord.record_kind == "manual",
            )
            .order_by(M02IntakeRecord.intake_id)
        ).all()
    )
    rows: list[CandidateEvaluation] = []
    for intake in intakes:
        try:
            context = _candidate_context(db, client, intake)
            rows.append(CandidateEvaluation(context.candidate_id, intake, context, None))
        except M05LedgerError as error:
            rows.append(
                CandidateEvaluation(
                    _generic_candidate_id(client_id, intake.intake_id),
                    intake,
                    None,
                    error.code,
                )
            )

    groups: dict[tuple[bytes, bytes], list[int]] = {}
    for index, row in enumerate(rows):
        if row.context is not None:
            key = (
                row.context.provider_name.encode("utf-8"),
                row.context.account_reference.encode("utf-8"),
            )
            groups.setdefault(key, []).append(index)
    for key, indices in groups.items():
        _ = key
        best_date = max(rows[index].context.statement_date for index in indices if rows[index].context)
        date_indices = [index for index in indices if rows[index].context and rows[index].context.statement_date == best_date]
        best_decided = max(rows[index].context.m03_decided_at for index in date_indices if rows[index].context)
        winners = [index for index in date_indices if rows[index].context and rows[index].context.m03_decided_at == best_decided]
        if len(winners) != 1:
            for index in winners:
                rows[index] = replace(rows[index], exclusion_reason="authoritative_candidate_tie")
            continue
        winner = winners[0]
        context = rows[winner].context
        assert context is not None
        newer_ineligible = any(
            row.context is None
            and row.intake.declared_provider_name == context.provider_name
            and row.intake.declared_account_reference == context.account_reference
            and row.intake.declared_statement_date is not None
            and row.intake.declared_statement_date > context.statement_date
            for row in rows
        )
        warnings = ("newer_ineligible_candidate_exists",) if newer_ineligible else ()
        rows[winner] = replace(
            rows[winner],
            context=replace(context, newer_ineligible=newer_ineligible),
            authoritative=True,
            informational_warnings=warnings,
        )
        for index in indices:
            if index != winner:
                rows[index] = replace(rows[index], exclusion_reason="no_authoritative_candidate")
    return rows


def _subject_for_context(db: Session, context: CandidateContext) -> M05LedgerSubject | None:
    subject = db.scalar(
        select(M05LedgerSubject).where(
            M05LedgerSubject.client_id == context.client.client_id,
            M05LedgerSubject.provider_identity_digest == context.provider_digest,
            M05LedgerSubject.account_identity_digest == context.account_digest,
        )
    )
    if subject is not None and (
        subject.provider_name.encode("utf-8") != context.provider_name.encode("utf-8")
        or subject.account_reference.encode("utf-8") != context.account_reference.encode("utf-8")
    ):
        raise _conflict("ledger_chain_inconsistent", "Ledger chain is inconsistent")
    return subject


def list_candidates(db: Session, client_id: int) -> list[M05CandidateResponse]:
    rows = _evaluate_candidates(db, client_id)
    result: list[M05CandidateResponse] = []
    for row in rows:
        context = row.context
        subject = _subject_for_context(db, context) if context else None
        result.append(
            M05CandidateResponse(
                candidate_id=row.candidate_id,
                intake_id=row.intake.intake_id,
                target_kind=M05_TARGET_KIND,
                provider_name=row.intake.declared_provider_name,
                account_reference=row.intake.declared_account_reference,
                product_context=(context.product_context if context else {
                    "product_name": row.intake.product_name,
                    "product_identifier": row.intake.product_identifier,
                    "declared_product_type": row.intake.declared_product_type,
                }),
                statement_date=row.intake.declared_statement_date,
                m03_revision_id=context.m03_revision_id if context else None,
                m04_revision_id=context.m04_revision_id if context else None,
                eligible=context is not None and row.exclusion_reason is None,
                authoritative_current=row.authoritative and row.exclusion_reason is None,
                exclusion_reason=row.exclusion_reason,
                informational_warnings=list(row.informational_warnings),
                subject_id=subject.subject_id if subject else None,
            )
        )
    return result


def _resolve_candidate(db: Session, client_id: int, candidate_id: str) -> CandidateContext:
    for row in _evaluate_candidates(db, client_id):
        if row.candidate_id == candidate_id:
            if row.context is None or row.exclusion_reason is not None or not row.authoritative:
                raise _conflict("no_authoritative_candidate", "Candidate is not currently authoritative")
            return row.context
    raise _not_found()


def _values(db: Session, revision_id: str) -> list[M05LedgerValue]:
    return list(
        db.scalars(
            select(M05LedgerValue)
            .where(M05LedgerValue.revision_id == revision_id)
            .order_by(M05LedgerValue.component_index, M05LedgerValue.evidence_identity)
        ).all()
    )


def _adjustment(db: Session, revision_id: str) -> M05AdjustmentEvidence | None:
    return db.scalar(
        select(M05AdjustmentEvidence).where(M05AdjustmentEvidence.revision_id == revision_id)
    )


def _adjustment_snapshot(row: M05AdjustmentEvidence) -> dict[str, Any]:
    return _json_value({
        "adjustment_id": row.adjustment_id,
        "revision_id": row.revision_id,
        "subject_id": row.subject_id,
        "client_id": row.client_id,
        "evidence_identity": row.evidence_identity,
        "previous_effective_value": row.previous_effective_value,
        "new_effective_value": row.new_effective_value,
        "reason_code": row.reason_code,
        "explanation": row.explanation,
        "confirmed": row.confirmed,
        "actor": row.actor,
        "created_at": _utc(row.created_at).isoformat(),
    })


def _revision_digest(row: M05LedgerRevision, values: list[M05LedgerValue | dict[str, Any]]) -> str:
    value_rows = []
    for value in values:
        value_rows.append(
            {
                "evidence_identity": value.evidence_identity if isinstance(value, M05LedgerValue) else value["evidence_identity"],
                "component_index": value.component_index if isinstance(value, M05LedgerValue) else value["component_index"],
                "original_label": value.original_label if isinstance(value, M05LedgerValue) else value["original_label"],
                "original_code": value.original_code if isinstance(value, M05LedgerValue) else value["original_code"],
                "component_kind": value.component_kind if isinstance(value, M05LedgerValue) else value["component_kind"],
                "source_state": value.source_state if isinstance(value, M05LedgerValue) else value["source_state"],
                "source_value": value.source_value if isinstance(value, M05LedgerValue) else value["source_value"],
                "effective_state": value.effective_state if isinstance(value, M05LedgerValue) else value["effective_state"],
                "effective_value": value.effective_value if isinstance(value, M05LedgerValue) else value["effective_value"],
                "included_in_reconciliation": value.included_in_reconciliation if isinstance(value, M05LedgerValue) else value["included_in_reconciliation"],
                "exclusion_reason": value.exclusion_reason if isinstance(value, M05LedgerValue) else value["exclusion_reason"],
            }
        )
    value_rows.sort(key=lambda item: (item["component_index"] is None, item["component_index"] or -1, item["evidence_identity"]))
    return _digest(
        {
            "revision_id": row.revision_id,
            "subject_id": row.subject_id,
            "client_id": row.client_id,
            "candidate_id": row.candidate_id,
            "intake_id": row.intake_id,
            "target_kind": row.target_kind,
            "m03_revision_id": row.m03_revision_id,
            "m04_revision_id": row.m04_revision_id,
            "predecessor_revision_id": row.predecessor_revision_id,
            "revision_sequence": row.revision_sequence,
            "state": row.state,
            "action_type": row.action_type,
            "provider_name": row.provider_name,
            "account_reference": row.account_reference,
            "product_context": row.product_context,
            "statement_date": row.statement_date,
            "evaluation_date": row.evaluation_date,
            "is_stale": row.is_stale,
            "source_snapshot_digest": row.source_snapshot_digest,
            "mapping_digest": row.mapping_digest,
            "currency": row.currency,
            "currency_confirmed": row.currency_confirmed,
            "currency_confirmation_evidence": row.currency_confirmation_evidence,
            "source_total_state": row.source_total_state,
            "source_total_value": row.source_total_value,
            "effective_total_state": row.effective_total_state,
            "effective_total_value": row.effective_total_value,
            "signed_discrepancy": row.signed_discrepancy,
            "absolute_discrepancy": row.absolute_discrepancy,
            "tolerance_satisfied": row.tolerance_satisfied,
            "algorithm_version": row.algorithm_version,
            "included_evidence": row.included_evidence,
            "excluded_evidence": row.excluded_evidence,
            "warnings": row.warnings,
            "warning_dispositions": row.warning_dispositions,
            "provenance": row.provenance,
            "reason_code": row.reason_code,
            "explanation": row.explanation,
            "actor": row.actor,
            "created_at": _utc(row.created_at),
            "values": value_rows,
        }
    )


def _transition(previous: M05LedgerRevision | None, current: M05LedgerRevision) -> bool:
    if previous is None:
        return current.action_type == "start" and current.state == "draft" and current.revision_sequence == 1 and current.predecessor_revision_id is None
    allowed = {
        "reconcile": ({"draft"}, "reconciled"),
        "review_warning": ({"draft"}, "warning_reviewed"),
        "mark_blocked": ({"draft", "reconciled", "warning_reviewed"}, "blocked"),
        "adjust": ({"draft", "reconciled", "warning_reviewed", "blocked"}, "draft"),
        "supersede": ({"draft", "reconciled", "warning_reviewed", "blocked"}, "superseded"),
        "revalidate": ({"draft", "reconciled", "warning_reviewed", "blocked"}, "draft"),
    }
    rule = allowed.get(current.action_type)
    return bool(
        rule
        and previous.state in rule[0]
        and current.state == rule[1]
        and current.revision_sequence == previous.revision_sequence + 1
        and current.predecessor_revision_id == previous.revision_id
    )


def _history(db: Session, subject: M05LedgerSubject) -> list[M05LedgerRevision]:
    rows = list(
        db.scalars(
            select(M05LedgerRevision)
            .where(M05LedgerRevision.subject_id == subject.subject_id)
            .order_by(M05LedgerRevision.revision_sequence)
        ).all()
    )
    if not rows:
        raise _conflict("ledger_chain_inconsistent", "Ledger chain is inconsistent")
    previous: M05LedgerRevision | None = None
    for row in rows:
        values = _values(db, row.revision_id)
        adjustment = _adjustment(db, row.revision_id)
        candidate = db.scalar(
            select(M05CandidateLink).where(
                M05CandidateLink.candidate_id == row.candidate_id,
                M05CandidateLink.client_id == row.client_id,
                M05CandidateLink.subject_id == row.subject_id,
            )
        )
        identities = [value.evidence_identity for value in values]
        total_values = [value for value in values if value.component_kind == "total_balance"]
        candidate_snapshot = (
            _candidate_snapshot(candidate, subject) if candidate is not None else None
        )
        expected_candidate_id = (
            f"M05-CAND-{candidate_snapshot['candidate_identity_digest'][:40]}"
            if candidate_snapshot is not None
            else None
        )
        if (
            REVISION_PATTERN.fullmatch(row.revision_id) is None
            or row.client_id != subject.client_id
            or row.subject_id != subject.subject_id
            or row.provider_name.encode("utf-8") != subject.provider_name.encode("utf-8")
            or row.account_reference.encode("utf-8") != subject.account_reference.encode("utf-8")
            or row.actor != M05_WORKFLOW_ACTOR
            or row.algorithm_version != M05_ALGORITHM_VERSION
            or row.currency != M05_CURRENCY
            or not _transition(previous, row)
            or candidate is None
            or CANDIDATE_PATTERN.fullmatch(candidate.candidate_id) is None
            or candidate.candidate_id != expected_candidate_id
            or candidate.intake_id != row.intake_id
            or candidate.target_kind != row.target_kind
            or candidate.m03_revision_id != row.m03_revision_id
            or candidate.m04_revision_id != row.m04_revision_id
            or candidate.statement_date != row.statement_date
            or candidate.source_snapshot_digest != row.source_snapshot_digest
            or row.provenance.get("candidate_link") != candidate_snapshot
            or (
                row.provenance.get("adjustment_evidence")
                != (_adjustment_snapshot(adjustment) if adjustment is not None else None)
            )
            or ((row.action_type == "adjust") != (adjustment is not None))
            or not values
            or len(identities) != len(set(identities))
            or len(total_values) != 1
            or total_values[0].source_value != row.source_total_value
            or total_values[0].effective_value != row.effective_total_value
            or _revision_digest(row, values) != row.evidence_digest
        ):
            raise _conflict("ledger_chain_inconsistent", "Ledger chain is inconsistent")
        previous = row
    return rows


def _subject(db: Session, client_id: int, subject_id: str) -> M05LedgerSubject:
    _client(db, client_id)
    row = db.scalar(
        select(M05LedgerSubject).where(
            M05LedgerSubject.client_id == client_id,
            M05LedgerSubject.subject_id == subject_id,
        )
    )
    if row is None:
        raise _not_found()
    if (
        _identity_digest(row.provider_name) != row.provider_identity_digest
        or _identity_digest(row.account_reference) != row.account_identity_digest
    ):
        raise _conflict("ledger_chain_inconsistent", "Ledger chain is inconsistent")
    return row


def _state(value: Decimal) -> str:
    return "recorded_zero" if value == 0 else "recorded_value"


def _reconcile(values: list[dict[str, Any]]) -> tuple[Decimal, Decimal, bool, list[dict[str, Any]], list[dict[str, Any]]]:
    total = next(item for item in values if item["component_kind"] == "total_balance")
    component_rows = [item for item in values if item["included_in_reconciliation"]]
    if not component_rows:
        raise _conflict("component_set_incomplete", "A non-empty reconcilable component set is required")
    component_sum = sum((item["effective_value"] for item in component_rows), Decimal("0.00"))
    discrepancy = total["effective_value"] - component_sum
    absolute = abs(discrepancy)
    included = [
        {"evidence_identity": item["evidence_identity"], "effective_value": format(item["effective_value"], "f")}
        for item in component_rows
    ]
    excluded = [
        {"evidence_identity": item["evidence_identity"], "reason": item["exclusion_reason"]}
        for item in values
        if item["component_kind"] != "total_balance" and not item["included_in_reconciliation"]
    ]
    return discrepancy, absolute, absolute <= TOLERANCE, included, excluded


def _warnings(
    values: list[dict[str, Any]],
    absolute_discrepancy: Decimal,
    *,
    stale: bool,
    newer_ineligible: bool,
) -> list[dict[str, Any]]:
    ids: list[tuple[str, str]] = []
    if absolute_discrepancy > TOLERANCE:
        ids.append(("reconciliation_difference_review_required", "mandatory"))
    if any(
        (item["source_value"] is not None and item["source_value"] < 0)
        or (item["effective_value"] is not None and item["effective_value"] < 0)
        for item in values
    ):
        ids.append(("negative_value_review_required", "mandatory"))
    if stale:
        ids.append(("stale_warning", "informational"))
    if newer_ineligible:
        ids.append(("newer_ineligible_candidate_exists", "informational"))
    return [{"warning_id": warning_id, "classification": kind} for warning_id, kind in ids]


def _currency_evidence(context: CandidateContext, confirmed: bool) -> dict[str, Any]:
    return {
        "confirmed": confirmed,
        "currency": M05_CURRENCY,
        "candidate_id": context.candidate_id,
        "intake_id": context.intake.intake_id,
        "source_snapshot_digest": context.source_snapshot_digest,
        "actor": M05_WORKFLOW_ACTOR,
        "confirmed_at": m05_server_timestamp().isoformat() if confirmed else None,
    }


def _candidate_link(db: Session, subject: M05LedgerSubject, context: CandidateContext) -> M05CandidateLink:
    existing = db.scalar(select(M05CandidateLink).where(M05CandidateLink.candidate_id == context.candidate_id))
    if existing is not None:
        if (
            existing.client_id != context.client.client_id
            or existing.subject_id != subject.subject_id
            or existing.intake_id != context.intake.intake_id
            or existing.target_kind != M05_TARGET_KIND
            or existing.m03_revision_id != context.m03_revision_id
            or existing.m04_revision_id != context.m04_revision_id
            or existing.statement_date != context.statement_date
            or _utc(existing.m03_decided_at) != _utc(context.m03_decided_at)
            or existing.source_snapshot_digest != context.source_snapshot_digest
            or existing.candidate_id
            != f"M05-CAND-{_digest(_candidate_identity_payload(existing.client_id, existing.intake_id, existing.target_kind, existing.m03_revision_id, existing.m04_revision_id))[:40]}"
        ):
            raise _conflict("ledger_chain_inconsistent", "Ledger chain is inconsistent")
        return existing
    row = M05CandidateLink(
        candidate_id=context.candidate_id,
        subject_id=subject.subject_id,
        client_id=context.client.client_id,
        intake_id=context.intake.intake_id,
        target_kind=M05_TARGET_KIND,
        m03_revision_id=context.m03_revision_id,
        m04_revision_id=context.m04_revision_id,
        statement_date=context.statement_date,
        m03_decided_at=context.m03_decided_at,
        source_snapshot_digest=context.source_snapshot_digest,
    )
    authorize_m05_insert(row)
    db.add(row)
    db.flush()
    return row


def _dict_values(rows: list[M05LedgerValue]) -> list[dict[str, Any]]:
    return [
        {
            "evidence_identity": row.evidence_identity,
            "component_index": row.component_index,
            "original_label": row.original_label,
            "original_code": row.original_code,
            "component_kind": row.component_kind,
            "source_state": row.source_state,
            "source_value": row.source_value,
            "effective_state": row.effective_state,
            "effective_value": row.effective_value,
            "included_in_reconciliation": row.included_in_reconciliation,
            "exclusion_reason": row.exclusion_reason,
        }
        for row in rows
    ]


def _append(
    db: Session,
    subject: M05LedgerSubject,
    context: CandidateContext,
    *,
    previous: M05LedgerRevision | None,
    state: str,
    action: str,
    values: list[dict[str, Any]],
    currency_evidence: dict[str, Any],
    warning_dispositions: list[dict[str, Any]] | None = None,
    reason_code: str | None = None,
    explanation: str | None = None,
    adjustment: dict[str, Any] | None = None,
) -> M05LedgerRevision:
    candidate = _candidate_link(db, subject, context)
    discrepancy, absolute, tolerance, included, excluded = _reconcile(values)
    warnings = _warnings(
        values,
        absolute,
        stale=context.stale,
        newer_ineligible=context.newer_ineligible,
    )
    total = next(item for item in values if item["component_kind"] == "total_balance")
    created_at = m05_server_timestamp()
    revision_id = f"M05-R-{uuid4().hex}"
    adjustment_row: M05AdjustmentEvidence | None = None
    if adjustment is not None:
        adjustment_row = M05AdjustmentEvidence(
            adjustment_id=f"M05-A-{uuid4().hex}",
            revision_id=revision_id,
            subject_id=subject.subject_id,
            client_id=subject.client_id,
            created_at=created_at,
            **adjustment,
        )
    revision = M05LedgerRevision(
        revision_id=revision_id,
        subject_id=subject.subject_id,
        client_id=subject.client_id,
        candidate_id=candidate.candidate_id,
        intake_id=context.intake.intake_id,
        target_kind=M05_TARGET_KIND,
        m03_revision_id=context.m03_revision_id,
        m04_revision_id=context.m04_revision_id,
        predecessor_revision_id=previous.revision_id if previous else None,
        revision_sequence=previous.revision_sequence + 1 if previous else 1,
        state=state,
        action_type=action,
        provider_name=subject.provider_name,
        account_reference=subject.account_reference,
        product_context=context.product_context,
        statement_date=context.statement_date,
        evaluation_date=context.evaluation_date,
        is_stale=context.stale,
        source_snapshot_digest=context.source_snapshot_digest,
        mapping_digest=context.mapping_digest,
        currency=M05_CURRENCY,
        currency_confirmed=bool(currency_evidence.get("confirmed")),
        currency_confirmation_evidence=currency_evidence,
        source_total_state=total["source_state"],
        source_total_value=total["source_value"],
        effective_total_state=total["effective_state"],
        effective_total_value=total["effective_value"],
        signed_discrepancy=discrepancy,
        absolute_discrepancy=absolute,
        tolerance_satisfied=tolerance,
        algorithm_version=M05_ALGORITHM_VERSION,
        included_evidence=included,
        excluded_evidence=excluded,
        warnings=warnings,
        warning_dispositions=warning_dispositions or [],
        provenance={
            "client_id": subject.client_id,
            "intake_id": context.intake.intake_id,
            "target_kind": M05_TARGET_KIND,
            "m03_revision_id": context.m03_revision_id,
            "m04_revision_id": context.m04_revision_id,
            "source_snapshot_digest": context.source_snapshot_digest,
            "mapping_digest": context.mapping_digest,
            "candidate_link": _candidate_snapshot(candidate, subject),
            "adjustment_evidence": (
                _adjustment_snapshot(adjustment_row)
                if adjustment_row is not None
                else None
            ),
        },
        evidence_digest="",
        reason_code=reason_code,
        explanation=explanation,
        actor=M05_WORKFLOW_ACTOR,
        created_at=created_at,
    )
    revision.evidence_digest = _revision_digest(revision, values)
    authorize_m05_insert(revision)
    db.add(revision)
    try:
        db.flush()
        for item in values:
            value = M05LedgerValue(
                revision_id=revision.revision_id,
                subject_id=subject.subject_id,
                client_id=subject.client_id,
                **item,
            )
            authorize_m05_insert(value)
            db.add(value)
        if adjustment_row is not None:
            authorize_m05_insert(adjustment_row)
            db.add(adjustment_row)
        db.commit()
    except (IntegrityError, OperationalError) as error:
        db.rollback()
        raise _conflict("M05_CONCURRENT_MODIFICATION", "Ledger changed before this action") from error
    db.refresh(revision)
    return revision


def start_ledger(
    db: Session,
    client_id: int,
    candidate_id: str,
    *,
    confirm_currency_ils: bool,
) -> M05LedgerRevision:
    context = _resolve_candidate(db, client_id, candidate_id)
    subject = _subject_for_context(db, context)
    if subject is not None:
        if _history(db, subject):
            raise _conflict("M05_LEDGER_ALREADY_STARTED", "Ledger chain already exists")
        raise _conflict("ledger_chain_inconsistent", "Ledger chain is inconsistent")
    subject = M05LedgerSubject(
        client_id=client_id,
        provider_name=context.provider_name,
        account_reference=context.account_reference,
        provider_identity_digest=context.provider_digest,
        account_identity_digest=context.account_digest,
    )
    authorize_m05_insert(subject)
    db.add(subject)
    try:
        db.flush()
        values = [
            {
                "evidence_identity": "total_balance",
                "component_index": None,
                "original_label": None,
                "original_code": None,
                "component_kind": "total_balance",
                "source_state": _state(context.source_total),
                "source_value": context.source_total,
                "effective_state": _state(context.source_total),
                "effective_value": context.source_total,
                "included_in_reconciliation": False,
                "exclusion_reason": "reconciliation_total",
            },
            *[dict(item) for item in context.values],
        ]
        return _append(
            db,
            subject,
            context,
            previous=None,
            state="draft",
            action="start",
            values=values,
            currency_evidence=_currency_evidence(context, confirm_currency_ils),
        )
    except M05LedgerError:
        db.rollback()
        raise
    except (IntegrityError, OperationalError) as error:
        db.rollback()
        raise _conflict("M05_CONCURRENT_MODIFICATION", "Ledger changed before this action") from error


def _current(db: Session, client_id: int, subject_id: str, expected: str | None = None) -> tuple[M05LedgerSubject, list[M05LedgerRevision], M05LedgerRevision]:
    subject = _subject(db, client_id, subject_id)
    rows = _history(db, subject)
    if not rows:
        raise _conflict("ledger_chain_inconsistent", "Ledger chain is inconsistent")
    leaf = rows[-1]
    if expected is not None and leaf.revision_id != expected:
        raise _conflict("M05_STALE_CURRENT_REVISION", "Ledger changed before this action")
    return subject, rows, leaf


def _current_context(db: Session, leaf: M05LedgerRevision) -> CandidateContext:
    client = _client(db, leaf.client_id)
    intake = db.scalar(
        select(M02IntakeRecord).where(
            M02IntakeRecord.client_id == leaf.client_id,
            M02IntakeRecord.intake_id == leaf.intake_id,
        )
    )
    if intake is None:
        raise _conflict("upstream_source_ineligible", "Current upstream source is unavailable")
    return _candidate_context(db, client, intake)


def _same_upstream(leaf: M05LedgerRevision, context: CandidateContext) -> None:
    if (
        leaf.candidate_id != context.candidate_id
        or leaf.source_snapshot_digest != context.source_snapshot_digest
        or leaf.mapping_digest != context.mapping_digest
        or leaf.m03_revision_id != context.m03_revision_id
        or leaf.m04_revision_id != context.m04_revision_id
    ):
        raise _conflict("upstream_revalidation_required", "Current upstream authority requires revalidation")


def _carried_currency(leaf: M05LedgerRevision, context: CandidateContext, renew: bool = False) -> dict[str, Any]:
    if renew:
        return _currency_evidence(context, True)
    evidence = dict(leaf.currency_confirmation_evidence)
    valid = (
        leaf.currency_confirmed
        and evidence.get("source_snapshot_digest") == context.source_snapshot_digest
        and evidence.get("currency") == M05_CURRENCY
    )
    return evidence if valid else _currency_evidence(context, False)


def reconcile_ledger(db: Session, client_id: int, subject_id: str, expected: str, confirm: bool) -> M05LedgerRevision:
    subject, _, leaf = _current(db, client_id, subject_id, expected)
    if leaf.state != "draft":
        raise _conflict("M05_INVALID_LIFECYCLE_TRANSITION", "Reconcile is allowed only from draft")
    context = _current_context(db, leaf)
    _same_upstream(leaf, context)
    values = _dict_values(_values(db, leaf.revision_id))
    discrepancy, absolute, _, _, _ = _reconcile(values)
    _ = discrepancy
    mandatory = {item["warning_id"] for item in _warnings(values, absolute, stale=context.stale, newer_ineligible=context.newer_ineligible) if item["classification"] == "mandatory"}
    if mandatory:
        raise _conflict("M05_WARNING_REVIEW_REQUIRED", "Mandatory warnings require exact-set review")
    currency = _carried_currency(leaf, context, renew=confirm)
    if not currency.get("confirmed"):
        raise _conflict("currency_or_unit_invalid", "Explicit ILS confirmation is required")
    return _append(db, subject, context, previous=leaf, state="reconciled", action="reconcile", values=values, currency_evidence=currency)


def review_warnings(db: Session, client_id: int, subject_id: str, payload: M05ReviewWarningRequest) -> M05LedgerRevision:
    subject, _, leaf = _current(db, client_id, subject_id, payload.expected_current_revision_id)
    if leaf.state != "draft":
        raise _conflict("M05_INVALID_LIFECYCLE_TRANSITION", "Warning review is allowed only from draft")
    context = _current_context(db, leaf)
    _same_upstream(leaf, context)
    values = _dict_values(_values(db, leaf.revision_id))
    _, absolute, _, _, _ = _reconcile(values)
    warnings = _warnings(values, absolute, stale=context.stale, newer_ineligible=context.newer_ineligible)
    mandatory = {item["warning_id"] for item in warnings if item["classification"] == "mandatory"}
    submitted = payload.mandatory_warning_ids
    if not mandatory or len(submitted) != len(set(submitted)) or set(submitted) != mandatory:
        raise _conflict("warning_disposition_invalid", "Mandatory warning disposition set is invalid")
    currency = _carried_currency(leaf, context, renew=bool(payload.confirm_currency_ils))
    if not currency.get("confirmed"):
        raise _conflict("currency_or_unit_invalid", "Explicit ILS confirmation is required")
    dispositions = [
        {
            "warning_id": warning_id,
            "reason_code": payload.reason_code,
            "explanation": payload.explanation,
            "confirmed": True,
            "actor": M05_WORKFLOW_ACTOR,
            "decided_at": m05_server_timestamp().isoformat(),
        }
        for warning_id in sorted(mandatory)
    ]
    return _append(db, subject, context, previous=leaf, state="warning_reviewed", action="review_warning", values=values, currency_evidence=currency, warning_dispositions=dispositions, reason_code=payload.reason_code, explanation=payload.explanation)


def mark_blocked(db: Session, client_id: int, subject_id: str, payload: M05ReasonRequest) -> M05LedgerRevision:
    subject, _, leaf = _current(db, client_id, subject_id, payload.expected_current_revision_id)
    if leaf.state not in {"draft", "reconciled", "warning_reviewed"}:
        raise _conflict("M05_INVALID_LIFECYCLE_TRANSITION", "Mark blocked is not allowed from the current state")
    context = _current_context(db, leaf)
    _same_upstream(leaf, context)
    return _append(db, subject, context, previous=leaf, state="blocked", action="mark_blocked", values=_dict_values(_values(db, leaf.revision_id)), currency_evidence=_carried_currency(leaf, context), reason_code=payload.reason_code, explanation=payload.explanation)


def adjust_ledger(db: Session, client_id: int, subject_id: str, payload: M05AdjustmentRequest) -> M05LedgerRevision:
    subject, _, leaf = _current(db, client_id, subject_id, payload.expected_current_revision_id)
    if leaf.state == "superseded":
        raise _conflict("M05_INVALID_LIFECYCLE_TRANSITION", "Superseded ledgers are terminal")
    context = _current_context(db, leaf)
    _same_upstream(leaf, context)
    values = _dict_values(_values(db, leaf.revision_id))
    target = next((item for item in values if item["evidence_identity"] == payload.evidence_identity), None)
    if target is None or target["effective_value"] is None:
        raise _not_found()
    previous_value = target["effective_value"]
    new_value = parse_authored_money(payload.new_effective_value)
    target["effective_value"] = new_value
    target["effective_state"] = _state(new_value)
    return _append(
        db,
        subject,
        context,
        previous=leaf,
        state="draft",
        action="adjust",
        values=values,
        currency_evidence=_carried_currency(leaf, context),
        reason_code=payload.reason_code,
        explanation=payload.explanation,
        adjustment={
            "evidence_identity": payload.evidence_identity,
            "previous_effective_value": previous_value,
            "new_effective_value": new_value,
            "reason_code": payload.reason_code,
            "explanation": payload.explanation,
            "confirmed": True,
            "actor": M05_WORKFLOW_ACTOR,
        },
    )


def supersede_ledger(db: Session, client_id: int, subject_id: str, payload: M05ReasonRequest) -> M05LedgerRevision:
    subject, _, leaf = _current(db, client_id, subject_id, payload.expected_current_revision_id)
    if leaf.state == "superseded":
        raise _conflict("M05_INVALID_LIFECYCLE_TRANSITION", "Superseded ledgers are terminal")
    context = _current_context(db, leaf)
    _same_upstream(leaf, context)
    return _append(db, subject, context, previous=leaf, state="superseded", action="supersede", values=_dict_values(_values(db, leaf.revision_id)), currency_evidence=_carried_currency(leaf, context), reason_code=payload.reason_code, explanation=payload.explanation)


def revalidate_ledger(db: Session, client_id: int, subject_id: str, candidate_id: str, payload: M05ReasonRequest) -> M05LedgerRevision:
    subject, _, leaf = _current(db, client_id, subject_id, payload.expected_current_revision_id)
    if leaf.state == "superseded":
        raise _conflict("M05_INVALID_LIFECYCLE_TRANSITION", "Superseded ledgers are terminal")
    context = _resolve_candidate(db, client_id, candidate_id)
    if (
        context.provider_name.encode("utf-8") != subject.provider_name.encode("utf-8")
        or context.account_reference.encode("utf-8") != subject.account_reference.encode("utf-8")
    ):
        raise _not_found()
    changed = (
        leaf.candidate_id != context.candidate_id
        or leaf.source_snapshot_digest != context.source_snapshot_digest
        or leaf.mapping_digest != context.mapping_digest
        or leaf.m03_revision_id != context.m03_revision_id
        or leaf.m04_revision_id != context.m04_revision_id
    )
    if not changed:
        raise _conflict("M05_REVALIDATION_NOT_REQUIRED", "Upstream authority has not changed")
    values = [
        {
            "evidence_identity": "total_balance",
            "component_index": None,
            "original_label": None,
            "original_code": None,
            "component_kind": "total_balance",
            "source_state": _state(context.source_total),
            "source_value": context.source_total,
            "effective_state": _state(context.source_total),
            "effective_value": context.source_total,
            "included_in_reconciliation": False,
            "exclusion_reason": "reconciliation_total",
        },
        *[dict(item) for item in context.values],
    ]
    currency = _currency_evidence(context, False) if leaf.source_snapshot_digest != context.source_snapshot_digest else _carried_currency(leaf, context)
    return _append(db, subject, context, previous=leaf, state="draft", action="revalidate", values=values, currency_evidence=currency, reason_code=payload.reason_code, explanation=payload.explanation)


def _value_response(row: M05LedgerValue) -> M05ValueResponse:
    return M05ValueResponse(
        value_id=row.value_id,
        evidence_identity=row.evidence_identity,
        component_index=row.component_index,
        original_label=row.original_label,
        original_code=row.original_code,
        component_kind=row.component_kind,
        source_state=row.source_state,
        source_value=row.source_value,
        effective_state=row.effective_state,
        effective_value=row.effective_value,
        included_in_reconciliation=row.included_in_reconciliation,
        exclusion_reason=row.exclusion_reason,
    )


def revision_response(db: Session, row: M05LedgerRevision) -> M05RevisionResponse:
    adjustment = _adjustment(db, row.revision_id)
    return M05RevisionResponse(
        revision_id=row.revision_id,
        subject_id=row.subject_id,
        candidate_id=row.candidate_id,
        intake_id=row.intake_id,
        target_kind=row.target_kind,
        m03_revision_id=row.m03_revision_id,
        m04_revision_id=row.m04_revision_id,
        predecessor_revision_id=row.predecessor_revision_id,
        revision_sequence=row.revision_sequence,
        state=row.state,
        action_type=row.action_type,
        provider_name=row.provider_name,
        account_reference=row.account_reference,
        product_context=row.product_context,
        statement_date=row.statement_date,
        evaluation_date=row.evaluation_date,
        is_stale=row.is_stale,
        source_snapshot_digest=row.source_snapshot_digest,
        mapping_digest=row.mapping_digest,
        currency=row.currency,
        currency_confirmed=row.currency_confirmed,
        currency_confirmation_evidence=row.currency_confirmation_evidence,
        source_total_state=row.source_total_state,
        source_total_value=row.source_total_value,
        effective_total_state=row.effective_total_state,
        effective_total_value=row.effective_total_value,
        signed_discrepancy=row.signed_discrepancy,
        absolute_discrepancy=row.absolute_discrepancy,
        tolerance_satisfied=row.tolerance_satisfied,
        algorithm_version=row.algorithm_version,
        included_evidence=row.included_evidence,
        excluded_evidence=row.excluded_evidence,
        warnings=row.warnings,
        warning_dispositions=row.warning_dispositions,
        provenance=row.provenance,
        reason_code=row.reason_code,
        explanation=row.explanation,
        actor=row.actor,
        created_at=row.created_at,
        values=[_value_response(value) for value in _values(db, row.revision_id)],
        adjustment=(
            M05AdjustmentResponse(
                adjustment_id=adjustment.adjustment_id,
                evidence_identity=adjustment.evidence_identity,
                previous_effective_value=adjustment.previous_effective_value,
                new_effective_value=adjustment.new_effective_value,
                reason_code=adjustment.reason_code,
                explanation=adjustment.explanation,
                confirmed=adjustment.confirmed,
                actor=adjustment.actor,
                created_at=adjustment.created_at,
            )
            if adjustment
            else None
        ),
    )


def history(db: Session, client_id: int, subject_id: str) -> list[M05RevisionResponse]:
    subject = _subject(db, client_id, subject_id)
    return [revision_response(db, row) for row in _history(db, subject)]


def eligibility(db: Session, client_id: int, subject_id: str) -> M05EligibilityResponse:
    try:
        subject = _subject(db, client_id, subject_id)
    except M05LedgerError as error:
        if error.code != "ledger_chain_inconsistent":
            raise
        return M05EligibilityResponse(
            subject_id=subject_id,
            eligible_for_m06=False,
            current_revision_id=None,
            exclusion_reasons=["ledger_chain_inconsistent"],
            informational_warnings=[],
        )
    informational: list[str] = []
    try:
        rows = _history(db, subject)
    except M05LedgerError:
        return M05EligibilityResponse(subject_id=subject_id, eligible_for_m06=False, current_revision_id=None, exclusion_reasons=["ledger_chain_inconsistent"], informational_warnings=[])
    leaf = rows[-1] if rows else None
    reasons: list[str] = []
    client = _client(db, client_id)
    if effective_lifecycle_status(client.status) == "archived":
        reasons.append("archived_case")
    if leaf is None:
        reasons.append("no_authoritative_candidate")
    else:
        if leaf.state == "draft":
            reasons.append("ledger_draft")
        elif leaf.state == "blocked":
            reasons.append("ledger_blocked")
        elif leaf.state == "superseded":
            reasons.append("ledger_superseded")
        elif leaf.state not in {"reconciled", "warning_reviewed"}:
            reasons.append("ledger_chain_inconsistent")
        if not leaf.currency_confirmed:
            reasons.append("currency_or_unit_invalid")
        if leaf.tolerance_satisfied is False and leaf.state != "warning_reviewed":
            reasons.append("reconciliation_unresolved")
        mandatory = {item["warning_id"] for item in leaf.warnings if item.get("classification") == "mandatory"}
        disposed = {item["warning_id"] for item in leaf.warning_dispositions}
        if mandatory != disposed:
            reasons.append("warning_not_reviewed")
        informational = [item["warning_id"] for item in leaf.warnings if item.get("classification") == "informational"]
        try:
            evaluations = _evaluate_candidates(db, client_id)
            matching = next((row for row in evaluations if row.candidate_id == leaf.candidate_id), None)
            if matching is None or not matching.authoritative or matching.exclusion_reason is not None:
                reasons.append("upstream_revalidation_required")
        except M05LedgerError as error:
            reasons.append(error.code if error.code in {"archived_case", "m03_ineligible", "m04_ineligible", "upstream_source_ineligible"} else "upstream_source_ineligible")
    unique_reasons = list(dict.fromkeys(reasons))
    return M05EligibilityResponse(
        subject_id=subject_id,
        eligible_for_m06=not unique_reasons,
        current_revision_id=leaf.revision_id if leaf else None,
        exclusion_reasons=unique_reasons,
        informational_warnings=list(dict.fromkeys(informational)),
    )


def subject_response(db: Session, client_id: int, subject_id: str) -> M05SubjectResponse:
    subject = _subject(db, client_id, subject_id)
    rows = _history(db, subject)
    leaf = rows[-1] if rows else None
    return M05SubjectResponse(
        subject_id=subject.subject_id,
        client_id=subject.client_id,
        provider_name=subject.provider_name,
        account_reference=subject.account_reference,
        current_revision=revision_response(db, leaf) if leaf else None,
        eligibility=eligibility(db, client_id, subject_id),
    )


def list_subjects(db: Session, client_id: int) -> list[M05SubjectResponse]:
    _client(db, client_id)
    rows = db.scalars(
        select(M05LedgerSubject)
        .where(M05LedgerSubject.client_id == client_id)
        .order_by(M05LedgerSubject.created_at, M05LedgerSubject.subject_id)
    ).all()
    return [subject_response(db, client_id, row.subject_id) for row in rows]
