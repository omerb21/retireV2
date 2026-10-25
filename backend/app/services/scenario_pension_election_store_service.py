"""SC-05C internal draft-only election writer; transaction owned by caller."""
from uuid import uuid4
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.scenario_draft import ScenarioDraftDecision
from app.models.scenario_draft_pension_election import ScenarioDraftPensionElection as Election
from app.schemas.scenario_pension_election import ScenarioPensionElectionSet
from app.services.scenario_draft_service import DraftError, _cas, _revision, _scenario


def replace_elections(db: Session, client_id: int, scenario_id: str,
                      payload: ScenarioPensionElectionSet, actor: str) -> dict:
    """Atomically overwrite elections after scenario-version CAS.

    Requires surrounding transaction; never commit internally. No implied
    coefficient admission, calculation, current professional approval or API.
    """
    if not isinstance(payload, ScenarioPensionElectionSet):
        raise DraftError("SCENARIO_ELECTION_PAYLOAD_INVALID", 422)
    scenario = _scenario(db, client_id, scenario_id)
    if scenario.version != payload.expected_scenario_version:
        raise DraftError("SCENARIO_VERSION_CONFLICT", 409)
    decisions = db.scalars(select(ScenarioDraftDecision).where(
        ScenarioDraftDecision.scenario_id == scenario_id)).all()
    by_id = {d.decision_id: d for d in decisions}
    for item in payload.elections:
        decision = by_id.get(item.decision_id)
        if decision is None or decision.action != "pension":
            raise DraftError("SCENARIO_PENSION_DECISION_MISMATCH", 422)
        if item.pension_start_date < decision.effective_date:
            raise DraftError("SCENARIO_PENSION_START_BEFORE_EFFECTIVE_DATE", 422)
    _cas(db, scenario, payload.expected_scenario_version, actor)
    db.execute(delete(Election).where(Election.scenario_id == scenario_id))
    for item in payload.elections:
        db.add(Election(
            election_id=uuid4().hex, scenario_id=scenario_id,
            decision_id=item.decision_id, scenario_version=scenario.version,
            pension_start_date=item.pension_start_date, target_year=item.target_year,
            survivors_option=item.survivors_option, spouse_age_diff=item.spouse_age_diff,
            coefficient_selection=item.coefficient_selection,
            company_name=item.company_name, option_name=item.option_name,
        ))
    db.flush()
    # Persist the full versioned election state in audit history, independently
    # of the stable draft read DTO. No professional/execution admission.
    election_audit = [
        {
            "decision_id": item.decision_id,
            "scenario_version": scenario.version,
            "pension_start_date": item.pension_start_date.isoformat(),
            "target_year": item.target_year,
            "survivors_option": item.survivors_option,
            "spouse_age_diff": item.spouse_age_diff,
            "coefficient_selection": item.coefficient_selection,
            "company_name": item.company_name,
            "option_name": item.option_name,
            "authority_state": "NOT_EVALUATED",
        }
        for item in sorted(payload.elections, key=lambda i: i.decision_id)
    ]
    return _revision(
        db, scenario, "replace_pension_elections", actor,
        audit_extra={"pension_elections": election_audit},
    )


def current_elections(db: Session, client_id: int, scenario_id: str) -> list[dict]:
    scenario = _scenario(db, client_id, scenario_id)
    if scenario.status != "draft":
        return []
    decisions = {d.decision_id: d for d in db.scalars(select(ScenarioDraftDecision).where(
        ScenarioDraftDecision.scenario_id == scenario_id, ScenarioDraftDecision.action == "pension"))}
    rows = db.scalars(select(Election).where(
        Election.scenario_id == scenario_id, Election.scenario_version == scenario.version
    ).order_by(Election.decision_id)).all()
    return [
        dict(decision_id=row.decision_id, pension_start_date=row.pension_start_date.isoformat(),
             target_year=row.target_year, survivors_option=row.survivors_option,
             spouse_age_diff=row.spouse_age_diff, coefficient_selection=row.coefficient_selection,
             company_name=row.company_name, option_name=row.option_name,
             authority_state="NOT_EVALUATED")
        for row in rows if row.decision_id in decisions
        and row.pension_start_date >= decisions[row.decision_id].effective_date
    ]
