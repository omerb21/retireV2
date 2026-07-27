from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Iterable
from uuid import uuid4

from sqlalchemy.orm import Session

from app.schemas.m07_evidence import (
    AssessmentRun,
    FactEvidenceWrite,
    RevisionDraftCreate,
)
from app.services.m07_evidence_service import (
    create_revision_draft,
    finalize_revision,
    write_fact_evidence,
)


NOW = datetime(2026, 7, 27, 12, 0, tzinfo=timezone.utc)


def seed_eligibility_revision(
    session: Session,
    *,
    client_id: int,
    eligibility_dates: Iterable[str] = ("2026-01-01",),
) -> tuple[str, list[str]]:
    identity = uuid4().hex
    revision = create_revision_draft(
        db_session=session,
        client_id=client_id,
        request=RevisionDraftCreate(
            profile_id=f"pkg004d-profile-{identity}",
            tax_year=2026,
            event_year=2026,
            event_type="retirement_event",
            event_id=f"pkg004d-event-{identity}",
            schema_version="pkg004b1.m07-evidence.v1",
            rule_version="pkg004b1.technical-assessment.v1",
        ),
        actor="pkg004d-test",
        timestamp=NOW,
    )
    fact_ids: list[str] = []
    for index, value in enumerate(eligibility_dates, start=1):
        row = write_fact_evidence(
            db_session=session,
            client_id=client_id,
            revision_id=revision.m07_evidence_revision_id,
            request=FactEvidenceWrite(
                field_code="eligibility_date",
                structured_value=value,
                collection_state="recorded",
                verification_state="unverified",
                source_type="external_document",
                source_document_reference=(
                    f"document://pkg004d/{identity}/{index}"
                ),
            ),
            recorded_actor="pkg004d-test",
            timestamp=NOW,
        )
        fact_ids.append(row.fact_evidence_id)
    finalize_revision(
        db_session=session,
        client_id=client_id,
        revision_id=revision.m07_evidence_revision_id,
        actor="pkg004d-test",
        assessment=AssessmentRun(),
        timestamp=NOW,
    )
    return revision.m07_evidence_revision_id, fact_ids


def resolver_payload(
    legacy_payload: dict,
    *,
    revision_id: str,
    selections: list[dict] | None = None,
) -> dict:
    payload = deepcopy(legacy_payload)
    payload.pop("eligibility_date", None)
    payload.pop("eligibility_year", None)
    payload.pop("upstream_context", None)
    payload["m07_input_reference"] = {
        "b1_evidence_revision_id": revision_id,
        "selections": selections or [],
    }
    return payload
