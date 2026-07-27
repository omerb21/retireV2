from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.schemas.fixation_m07 import (
    FixationEligibilityRevisionCreate,
    FixationEligibilityRevisionCreated,
    FixationEligibilityRevisionList,
    FixationEligibilityRevisionSummary,
)
from app.schemas.m07_calculation_input_resolution import (
    CalculationInputResolutionRequest,
)
from app.schemas.m07_evidence import (
    AssessmentRun,
    FactEvidenceWrite,
    PlannerAssertionAppend,
    RevisionDraftCreate,
)
from app.services.m07_calculation_input_manifest import (
    M08A_FIXATION_CALCULATION_SCOPE,
    M08A_FIXATION_MANIFEST_VERSION,
)
from app.services.m07_calculation_input_resolver import resolve_calculation_inputs
from app.services.m07_evidence_service import (
    append_planner_assertion,
    create_revision_draft,
    finalize_revision,
    list_client_revisions,
    write_fact_evidence,
)


FIXATION_UI_TECHNICAL_ACTOR = "system:fixation-ui:Fixation workflow"
FIXATION_UI_PROFILE_ID = "fixation-ui"
FIXATION_UI_SCHEMA_VERSION = "pkg004b1.m07-evidence.v1"
FIXATION_UI_RULE_VERSION = "pkg004b1.technical-assessment.v1"


def list_fixation_eligibility_revisions(
    *,
    db_session: Session,
    client_id: int,
    offset: int,
    limit: int,
) -> FixationEligibilityRevisionList:
    revisions, total = list_client_revisions(
        db_session=db_session,
        client_id=client_id,
        status="finalized",
        offset=offset,
        limit=limit,
    )
    items: list[FixationEligibilityRevisionSummary] = []
    for revision in revisions:
        resolution = resolve_calculation_inputs(
            db_session=db_session,
            client_id=client_id,
            request=CalculationInputResolutionRequest(
                calculation_scope=M08A_FIXATION_CALCULATION_SCOPE,
                manifest_version=M08A_FIXATION_MANIFEST_VERSION,
                b1_evidence_revision_id=revision.m07_evidence_revision_id,
            ),
        )
        dates = sorted(
            {
                str(candidate.normalized_value)
                for field in resolution.ambiguous_fields
                if field.field_code == "eligibility_date"
                for candidate in field.candidates
            }
            | {
                str(resolution.normalized_selected_values["eligibility_date"])
                for _ in [0]
                if "eligibility_date" in resolution.normalized_selected_values
            }
        )
        assert revision.finalized_at is not None
        items.append(
            FixationEligibilityRevisionSummary(
                revision_id=revision.m07_evidence_revision_id,
                profile_id=revision.profile_id,
                revision_number=revision.revision_number,
                status="finalized",
                finalized_at=revision.finalized_at,
                eligibility_outcome=resolution.outcome,
                eligibility_dates=dates,
            )
        )
    return FixationEligibilityRevisionList(
        items=items,
        offset=offset,
        limit=limit,
        total=total,
    )


def create_fixation_eligibility_revision(
    *,
    db_session: Session,
    client_id: int,
    request: FixationEligibilityRevisionCreate,
) -> FixationEligibilityRevisionCreated:
    eligibility_date = date.fromisoformat(request.eligibility_date)
    try:
        revision = create_revision_draft(
            db_session=db_session,
            client_id=client_id,
            request=RevisionDraftCreate(
                profile_id=FIXATION_UI_PROFILE_ID,
                tax_year=eligibility_date.year,
                event_year=eligibility_date.year,
                event_type="fixation",
                schema_version=FIXATION_UI_SCHEMA_VERSION,
                rule_version=FIXATION_UI_RULE_VERSION,
            ),
            actor=FIXATION_UI_TECHNICAL_ACTOR,
        )
        assertion = append_planner_assertion(
            db_session=db_session,
            client_id=client_id,
            revision_id=revision.m07_evidence_revision_id,
            request=PlannerAssertionAppend(
                field_code="eligibility_date",
                asserted_value=request.eligibility_date,
                assertion_basis="PKG-005 fixation eligibility-date entry",
                assertion_reason="Date entered through the fixation workflow",
                source_note="Operational evidence captured by the fixation UI workflow",
            ),
            actor=FIXATION_UI_TECHNICAL_ACTOR,
        )
        write_fact_evidence(
            db_session=db_session,
            client_id=client_id,
            revision_id=revision.m07_evidence_revision_id,
            request=FactEvidenceWrite(
                field_code="eligibility_date",
                structured_value=request.eligibility_date,
                collection_state="recorded",
                collection_basis="PKG-005 fixation workflow",
                verification_state="planner_asserted",
                assertion_id=assertion.assertion_id,
                source_metadata={
                    "actor_type": "system",
                    "actor_code": "fixation-ui",
                    "actor_label": "Fixation workflow",
                },
            ),
            recorded_actor=FIXATION_UI_TECHNICAL_ACTOR,
        )
        finalized = finalize_revision(
            db_session=db_session,
            client_id=client_id,
            revision_id=revision.m07_evidence_revision_id,
            actor=FIXATION_UI_TECHNICAL_ACTOR,
            assessment=AssessmentRun(),
        )
        db_session.commit()
    except Exception:
        db_session.rollback()
        raise

    assert finalized.finalized_at is not None
    return FixationEligibilityRevisionCreated(
        revision_id=finalized.m07_evidence_revision_id,
        status="finalized",
        finalized_at=finalized.finalized_at,
        eligibility_date=request.eligibility_date,
        technical_actor=FIXATION_UI_TECHNICAL_ACTOR,
    )
