from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.official_parameter_set import OfficialParameterSet
from app.schemas.official_parameter_sets import (
    OFFICIAL_PARAMETER_FINGERPRINT_ALGORITHM,
    OFFICIAL_PARAMETER_RESOLVER_VERSION,
    OfficialParameterAdmissionContext,
    OfficialParameterActivationRequest,
    OfficialParameterEvidenceSummary,
    OfficialParameterRejectionRequest,
    OfficialParameterResolution,
    OfficialParameterSetCreate,
    OfficialParameterSetResponse,
    OfficialParameterSupersessionRequest,
    OfficialParameterValues,
    OfficialParameterVerificationRequest,
)


class OfficialParameterSetNotFoundError(LookupError):
    pass


class OfficialParameterLifecycleError(ValueError):
    pass


class OfficialParameterOverlapError(ValueError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _canonical_decimal(value: Decimal) -> str:
    if not value.is_finite():
        raise ValueError("non-finite decimals cannot be fingerprinted")
    normalized = format(value, "f")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")
    return "0" if normalized in {"", "-0"} else normalized


def canonicalize_official_parameter_value(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="python")
    if isinstance(value, dict):
        return {
            str(key): canonicalize_official_parameter_value(value[key])
            for key in sorted(value, key=lambda item: str(item))
        }
    if isinstance(value, (list, tuple)):
        return [canonicalize_official_parameter_value(item) for item in value]
    if isinstance(value, Decimal):
        return _canonical_decimal(value)
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.isoformat(timespec="microseconds")
        return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace(
            "+00:00", "Z"
        )
    if isinstance(value, date):
        return value.isoformat()
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise TypeError(f"unsupported official parameter value: {type(value).__name__}")


def canonical_official_parameter_json(value: Any) -> str:
    return json.dumps(
        canonicalize_official_parameter_value(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def official_parameter_fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_official_parameter_json(value).encode("utf-8")).hexdigest()


def official_parameter_content(
    *,
    tax_year: int,
    effective_from: date,
    effective_to: date | None,
    schema_version: str,
    parameter_set_version: str,
    values: OfficialParameterValues,
    source_type: str,
    source_title: str,
    official_source_reference: str,
    source_publication_date: date | None,
    source_evidence_metadata: dict[str, Any],
) -> dict[str, Any]:
    return {
        "tax_year": tax_year,
        "effective_from": effective_from,
        "effective_to": effective_to,
        "schema_version": schema_version,
        "parameter_set_version": parameter_set_version,
        "values": values,
        "source": {
            "source_type": source_type,
            "source_title": source_title,
            "official_source_reference": official_source_reference,
            "source_publication_date": source_publication_date,
            "source_evidence_metadata": source_evidence_metadata,
        },
    }


def _row_values(row: OfficialParameterSet) -> OfficialParameterValues:
    return OfficialParameterValues(
        monthly_cap=row.monthly_cap,
        exemption_percentage=row.exemption_percentage,
        capital_multiplier=row.capital_multiplier,
        grant_impact_multiplier=row.grant_impact_multiplier,
    )


def _row_content(row: OfficialParameterSet) -> dict[str, Any]:
    return official_parameter_content(
        tax_year=row.tax_year,
        effective_from=row.effective_from,
        effective_to=row.effective_to,
        schema_version=row.schema_version,
        parameter_set_version=row.parameter_set_version,
        values=_row_values(row),
        source_type=row.source_type,
        source_title=row.source_title,
        official_source_reference=row.official_source_reference,
        source_publication_date=row.source_publication_date,
        source_evidence_metadata=row.source_evidence_metadata,
    )


def create_official_parameter_set_draft(
    *,
    db_session: Session,
    request: OfficialParameterSetCreate,
    timestamp: datetime | None = None,
) -> OfficialParameterSet:
    now = timestamp or _utc_now()
    values = request.values
    content = official_parameter_content(
        tax_year=request.tax_year,
        effective_from=request.effective_from,
        effective_to=request.effective_to,
        schema_version=request.schema_version,
        parameter_set_version=request.parameter_set_version,
        values=values,
        source_type=request.source_type,
        source_title=request.source_title,
        official_source_reference=request.official_source_reference,
        source_publication_date=request.source_publication_date,
        source_evidence_metadata=request.source_evidence_metadata,
    )
    parameter_set_id = request.parameter_set_id or f"official-params-{uuid4().hex}"
    row = OfficialParameterSet(
        parameter_set_id=parameter_set_id,
        tax_year=request.tax_year,
        effective_from=request.effective_from,
        effective_to=request.effective_to,
        schema_version=request.schema_version,
        parameter_set_version=request.parameter_set_version,
        status="draft",
        monthly_cap=values.monthly_cap,
        exemption_percentage=values.exemption_percentage,
        capital_multiplier=values.capital_multiplier,
        grant_impact_multiplier=values.grant_impact_multiplier,
        source_type=request.source_type,
        source_title=request.source_title,
        official_source_reference=request.official_source_reference,
        source_publication_date=request.source_publication_date,
        source_recorded_at=request.source_recorded_at or now,
        source_evidence_metadata=request.source_evidence_metadata,
        verification_note=None,
        parameter_payload=canonicalize_official_parameter_value(content),
        content_fingerprint=official_parameter_fingerprint(content),
        fingerprint_algorithm_version=OFFICIAL_PARAMETER_FINGERPRINT_ALGORITHM,
        created_at=now,
        created_by=request.created_by,
        verified_at=None,
        verified_by=None,
        activated_at=None,
        activated_by=None,
        rejected_at=None,
        rejected_by=None,
        rejection_note=None,
        superseded_at=None,
        superseded_by=None,
    )
    db_session.add(row)
    db_session.flush()
    return row


def get_official_parameter_set(
    *,
    db_session: Session,
    parameter_set_id: str,
) -> OfficialParameterSet:
    row = db_session.get(OfficialParameterSet, parameter_set_id)
    if row is None:
        raise OfficialParameterSetNotFoundError(parameter_set_id)
    return row


def list_official_parameter_sets(
    *,
    db_session: Session,
    tax_year: int | None = None,
    status: str | None = None,
) -> list[OfficialParameterSet]:
    statement = select(OfficialParameterSet)
    if tax_year is not None:
        statement = statement.where(OfficialParameterSet.tax_year == tax_year)
    if status is not None:
        statement = statement.where(OfficialParameterSet.status == status)
    return list(
        db_session.scalars(
            statement.order_by(
                OfficialParameterSet.tax_year,
                OfficialParameterSet.effective_from,
                OfficialParameterSet.parameter_set_id,
            )
        ).all()
    )


def verify_official_parameter_set(
    *,
    db_session: Session,
    parameter_set_id: str,
    request: OfficialParameterVerificationRequest,
    timestamp: datetime | None = None,
) -> OfficialParameterSet:
    row = get_official_parameter_set(db_session=db_session, parameter_set_id=parameter_set_id)
    if row.status != "draft":
        raise OfficialParameterLifecycleError("only draft parameter sets may be verified")
    content = _row_content(row)
    row.parameter_payload = canonicalize_official_parameter_value(content)
    row.content_fingerprint = official_parameter_fingerprint(content)
    row.verification_note = request.verification_note
    row.verified_at = timestamp or _utc_now()
    row.verified_by = request.verified_by
    row.status = "verified"
    db_session.flush()
    return row


def activate_official_parameter_set(
    *,
    db_session: Session,
    parameter_set_id: str,
    request: OfficialParameterActivationRequest,
    timestamp: datetime | None = None,
) -> OfficialParameterSet:
    row = get_official_parameter_set(db_session=db_session, parameter_set_id=parameter_set_id)
    if row.status != "verified":
        raise OfficialParameterLifecycleError("only verified parameter sets may be activated")
    if official_parameter_fingerprint(_row_content(row)) != row.content_fingerprint:
        raise OfficialParameterLifecycleError(
            "verified parameter content changed; verify the revision again before activation"
        )

    overlap_conditions = [
        OfficialParameterSet.status == "active",
        OfficialParameterSet.tax_year == row.tax_year,
        OfficialParameterSet.parameter_set_id != row.parameter_set_id,
        or_(
            OfficialParameterSet.effective_to.is_(None),
            OfficialParameterSet.effective_to >= row.effective_from,
        ),
    ]
    if row.effective_to is not None:
        overlap_conditions.append(
            OfficialParameterSet.effective_from <= row.effective_to
        )
    overlap = db_session.scalar(
        select(OfficialParameterSet.parameter_set_id)
        .where(*overlap_conditions)
        .order_by(OfficialParameterSet.parameter_set_id)
        .limit(1)
    )
    if overlap is not None:
        raise OfficialParameterOverlapError(
            f"active effective period overlaps parameter set {overlap}"
        )

    row.activated_at = timestamp or _utc_now()
    row.activated_by = request.activated_by
    row.status = "active"
    db_session.flush()
    return row


def reject_official_parameter_set(
    *,
    db_session: Session,
    parameter_set_id: str,
    request: OfficialParameterRejectionRequest,
    timestamp: datetime | None = None,
) -> OfficialParameterSet:
    row = get_official_parameter_set(db_session=db_session, parameter_set_id=parameter_set_id)
    if row.status not in {"draft", "verified"}:
        raise OfficialParameterLifecycleError(
            "only draft or verified parameter sets may be rejected"
        )
    row.rejected_at = timestamp or _utc_now()
    row.rejected_by = request.rejected_by
    row.rejection_note = request.rejection_note
    row.status = "rejected"
    db_session.flush()
    return row


def supersede_official_parameter_set(
    *,
    db_session: Session,
    parameter_set_id: str,
    request: OfficialParameterSupersessionRequest,
    timestamp: datetime | None = None,
) -> OfficialParameterSet:
    row = get_official_parameter_set(db_session=db_session, parameter_set_id=parameter_set_id)
    if row.status != "active":
        raise OfficialParameterLifecycleError("only active parameter sets may be superseded")
    row.superseded_at = timestamp or _utc_now()
    row.superseded_by = request.superseded_by
    row.status = "superseded"
    db_session.flush()
    return row


def resolve_official_parameter_set(
    *,
    db_session: Session,
    tax_year: int,
    effective_date: date,
    resolution_timestamp: datetime | None = None,
) -> OfficialParameterResolution:
    now = resolution_timestamp or _utc_now()
    candidates = list(
        db_session.scalars(
            select(OfficialParameterSet)
            .where(
                OfficialParameterSet.status == "active",
                OfficialParameterSet.tax_year == tax_year,
                OfficialParameterSet.effective_from <= effective_date,
                or_(
                    OfficialParameterSet.effective_to.is_(None),
                    OfficialParameterSet.effective_to >= effective_date,
                ),
            )
            .order_by(OfficialParameterSet.parameter_set_id)
        ).all()
    )
    if not candidates:
        return OfficialParameterResolution(
            result="unavailable",
            requested_tax_year=tax_year,
            requested_effective_date=effective_date,
            reason_codes=["official_parameter_set_unavailable"],
            resolution_timestamp=now,
        )
    if len(candidates) > 1:
        return OfficialParameterResolution(
            result="ambiguous",
            requested_tax_year=tax_year,
            requested_effective_date=effective_date,
            reason_codes=["multiple_official_parameter_sets_applicable"],
            candidate_ids=[candidate.parameter_set_id for candidate in candidates],
            resolution_timestamp=now,
        )

    selected = candidates[0]
    return OfficialParameterResolution(
        result="resolved",
        requested_tax_year=tax_year,
        requested_effective_date=effective_date,
        selected_parameter_set_id=selected.parameter_set_id,
        values=_row_values(selected),
        evidence=OfficialParameterEvidenceSummary(
            source_type=selected.source_type,
            source_title=selected.source_title,
            official_source_reference=selected.official_source_reference,
            source_publication_date=selected.source_publication_date,
            source_recorded_at=selected.source_recorded_at,
            content_fingerprint=selected.content_fingerprint,
            fingerprint_algorithm_version=selected.fingerprint_algorithm_version,
        ),
        parameter_set_version=selected.parameter_set_version,
        schema_version=selected.schema_version,
        resolution_timestamp=now,
    )


def resolve_official_parameter_admission_context(
    *,
    db_session: Session,
    tax_year: int,
    effective_date: date,
    resolution_timestamp: datetime | None = None,
) -> OfficialParameterAdmissionContext | None:
    resolution = resolve_official_parameter_set(
        db_session=db_session,
        tax_year=tax_year,
        effective_date=effective_date,
        resolution_timestamp=resolution_timestamp,
    )
    if resolution.result != "resolved" or resolution.selected_parameter_set_id is None:
        return None
    row = get_official_parameter_set(
        db_session=db_session,
        parameter_set_id=resolution.selected_parameter_set_id,
    )
    return OfficialParameterAdmissionContext(
        parameter_set_id=row.parameter_set_id,
        tax_year=row.tax_year,
        effective_from=row.effective_from,
        effective_to=row.effective_to,
        values=_row_values(row),
        source_basis=f"{row.source_type}: {row.official_source_reference}",
        schema_version=row.schema_version,
        parameter_set_version=row.parameter_set_version,
        content_fingerprint=row.content_fingerprint,
        resolver_contract_version=OFFICIAL_PARAMETER_RESOLVER_VERSION,
    )


def official_parameter_set_response(row: OfficialParameterSet) -> OfficialParameterSetResponse:
    return OfficialParameterSetResponse(
        parameter_set_id=row.parameter_set_id,
        tax_year=row.tax_year,
        effective_from=row.effective_from,
        effective_to=row.effective_to,
        schema_version=row.schema_version,
        parameter_set_version=row.parameter_set_version,
        status=row.status,
        values=_row_values(row),
        source_type=row.source_type,
        source_title=row.source_title,
        official_source_reference=row.official_source_reference,
        source_publication_date=row.source_publication_date,
        source_recorded_at=row.source_recorded_at,
        source_evidence_metadata=row.source_evidence_metadata,
        verification_note=row.verification_note,
        content_fingerprint=row.content_fingerprint,
        fingerprint_algorithm_version=row.fingerprint_algorithm_version,
        created_at=row.created_at,
        created_by=row.created_by,
        verified_at=row.verified_at,
        verified_by=row.verified_by,
        activated_at=row.activated_at,
        activated_by=row.activated_by,
        rejected_at=row.rejected_at,
        rejected_by=row.rejected_by,
        rejection_note=row.rejection_note,
        superseded_at=row.superseded_at,
        superseded_by=row.superseded_by,
    )
