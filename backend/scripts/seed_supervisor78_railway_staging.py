"""Supervisor 78 fixture ONLY for the existing RETIRE V2 Railway staging DB.

Not part of application startup. No professional factor admission or fixation
approval is created. Run only after separate supervisory authorization.
"""
from __future__ import annotations

import argparse
import os
from datetime import date
from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.engine import make_url

from app.db.base import load_all_models
from app.db.session import get_session_factory
from app.models.client import Client
from app.models.client_profile import ClientProfile
from app.models.pension_product import COMPONENT_CODES, PensionProduct, PensionProductComponent
from app.models.planning_input_decision import PlanningInputDecision
from app.models.scenario_draft import ScenarioDraft, ScenarioDraftDecision
from app.models.scenario_draft_pension_election import ScenarioDraftPensionElection
from app.services.pension_product_service import component_balances, product_response
from app.services.scenario_draft_service import _source_evidence, _revision
from app.services.scenario_permission_preview_service import ruleset_digest

PROJECT_ID = "7e49d0ff-a760-4a03-be57-4ee88a4b892c"
ENVIRONMENT_ID = "025871e4-2c84-427b-b37c-1d5b2c7b4d3c"
APPLICATION_SERVICE_ID = "328ec58c-da05-48e7-b959-bd5d3cd2bba3"
DATABASE_SERVICE_ID = "ecf868e3-3b17-4de9-b004-fcee73207c31"
DATABASE_NAME = "retire_v2_staging"
CLIENT_ID = 410078
SCENARIO_A = "supervisor78-scenario-a"
SCENARIO_B = "supervisor78-scenario-b"
PRODUCT_ID = "supervisor78-product"
PROFILE_ID = "supervisor78-profile"
PENSION_COMPONENT_ID = "supervisor78-pension-component"
DECISION_ID = "supervisor78-pension-decision"
ELECTION_ID = "supervisor78-pension-election"
SOURCE_IDENTITY = "imported:supervisor78:synthetic"
IDENTITY_NUMBER = "SYNTHETIC-SUPERVISOR78"
ACTOR = "supervisor78-staging-fixture"

def validate_target(env: dict[str, str]) -> None:
    """Fail closed before opening a database connection, without printing credentials."""
    try:
        url = make_url(env.get("DATABASE_URL", ""))
        valid = (
            url.drivername in {"postgresql", "postgresql+psycopg", "postgresql+psycopg2"}
            and url.host is not None
            and url.host.lower() == "retire-v2-postgres.railway.internal"
            and url.database == DATABASE_NAME
            and bool(url.username)
            and bool(url.password)
        )
    except Exception:
        valid = False
    if not (
        valid
        and env.get("RAILWAY_PROJECT_ID") == PROJECT_ID
        and env.get("RAILWAY_ENVIRONMENT_ID") == ENVIRONMENT_ID
        and env.get("RAILWAY_ENVIRONMENT_NAME") == "staging"
        and env.get("RAILWAY_SERVICE_ID") == APPLICATION_SERVICE_ID
        and env.get("APP_ENV") == "production"
        and env.get("AUTH_INGRESS_MODE") == "railway_public_edge"
        and env.get("CRTISBA_APPLICATION_DB_ROLE") == "retire_v2_staging_app"
    ):
        raise RuntimeError("SUPERVISOR78_RAILWAY_STAGING_TARGET_INVALID")

def _assert_no_collision(db) -> None:
    """Any preexisting marker, including a cross-client marker, blocks the whole seed."""
    ids = (
        (Client, CLIENT_ID),
        (ClientProfile, PROFILE_ID),
        (PensionProduct, PRODUCT_ID),
        (PlanningInputDecision, CLIENT_ID),
        (ScenarioDraft, SCENARIO_A),
        (ScenarioDraft, SCENARIO_B),
        (ScenarioDraftDecision, DECISION_ID),
        (ScenarioDraftPensionElection, ELECTION_ID),
    )
    if any(db.get(model, pk) is not None for model, pk in ids):
        raise RuntimeError("SUPERVISOR78_FIXTURE_COLLISION")
    for i in range(len(COMPONENT_CODES)):
        component_id = PENSION_COMPONENT_ID if i == 1 else f"supervisor78-zero-{i:02d}"
        if db.get(PensionProductComponent, component_id) is not None:
            raise RuntimeError("SUPERVISOR78_FIXTURE_COLLISION")
    if db.scalar(select(ClientProfile.client_profile_id).where(
        ClientProfile.client_id == CLIENT_ID
    )) is not None:
        raise RuntimeError("SUPERVISOR78_FIXTURE_COLLISION")
    if db.scalar(select(Client.client_id).where(Client.id_number == IDENTITY_NUMBER)) is not None:
        raise RuntimeError("SUPERVISOR78_FIXTURE_COLLISION")
    if db.scalar(select(PensionProduct.product_id).where(
        PensionProduct.source_identity == SOURCE_IDENTITY
    )) is not None:
        raise RuntimeError("SUPERVISOR78_FIXTURE_COLLISION")

def create_fixture(db) -> None:
    """Caller owns ONE transaction. Never commits, updates or deletes records."""
    if db.bind.dialect.name != "postgresql":
        raise RuntimeError("SUPERVISOR78_POSTGRESQL_REQUIRED")
    # Serialize repeated/concurrent fixture attempts. No persistent lock or schema change.
    db.execute(text("SELECT pg_advisory_xact_lock(410078, 78)"))
    _assert_no_collision(db)
    db.add(Client(client_id=CLIENT_ID, display_name="לקוח סינתטי קבילות 78",
                  id_number=IDENTITY_NUMBER, birth_date=date(1965, 5, 12)))
    db.flush()
    db.add(ClientProfile(
        client_profile_id=PROFILE_ID, client_id=CLIENT_ID,
        birth_date=date(1965, 5, 12), gender="female",
    ))
    db.add(PensionProduct(
        product_id=PRODUCT_ID, client_id=CLIENT_ID, source_kind="imported",
        source_identity=SOURCE_IDENTITY, product_name="קרן פנסיה סינתטית 78",
        product_type="קרן פנסיה", account_reference="SYNTHETIC-78",
        statement_date=date(2026, 9, 30),
        version=1, historical_employers=[], created_by=ACTOR, updated_by=ACTOR,
        reported_product_total=Decimal("200.00"),
        reported_rewards_total=Decimal("200.00"),
        reported_severance_total=Decimal("0.00"),
    ))
    db.flush()
    pension_code = COMPONENT_CODES[1]  # Same accepted fixture as local Supervisor 78.
    for i, code in enumerate(COMPONENT_CODES):
        db.add(PensionProductComponent(
            component_id=PENSION_COMPONENT_ID if i == 1 else f"supervisor78-zero-{i:02d}",
            product_id=PRODUCT_ID, component_code=code,
            balance=Decimal("200.00") if i == 1 else Decimal("0.00"),
        ))
    db.flush()
    balances = component_balances(db, PRODUCT_ID)
    api_product = product_response(db, db.get(PensionProduct, PRODUCT_ID))
    if (
        len(balances) != len(COMPONENT_CODES)
        or set(balances) != set(COMPONENT_CODES)
        or balances[pension_code] != Decimal("200.00")
        or any(v != Decimal("0.00") for k, v in balances.items() if k != pension_code)
        or api_product["client_id"] != CLIENT_ID
        or len(api_product["conversion_components"]) != len(COMPONENT_CODES)
    ):
        raise RuntimeError("SUPERVISOR78_COMPONENT_VALIDATION_FAILED")
    db.add(PlanningInputDecision(
        client_id=CLIENT_ID, version=1, planning_base_date=date(2026, 11, 1),
        retirement_target_date=date(2032, 1, 1), actor=ACTOR,
    ))
    for scenario_id, name in (
        (SCENARIO_A, "חלופת קבילות א"), (SCENARIO_B, "חלופת קבילות ב")
    ):
        db.add(ScenarioDraft(
            scenario_id=scenario_id, client_id=CLIENT_ID, name=name,
            status="draft", version=1, created_by=ACTOR, updated_by=ACTOR,
        ))
    db.flush()
    product = db.get(PensionProduct, PRODUCT_ID)
    component = db.get(PensionProductComponent, PENSION_COMPONENT_ID)
    source = _source_evidence(product, component)
    db.add(ScenarioDraftDecision(
        decision_id=DECISION_ID, scenario_id=SCENARIO_A,
        source_product_id=PRODUCT_ID, source_component_id=PENSION_COMPONENT_ID,
        component_code=component.component_code, amount=Decimal("40.00"),
        action="pension", effective_date=date(2027, 1, 1),
        validation_state="unverified", product_version_at_review=1,
        source_fingerprint_at_review=source["source_fingerprint"],
        ruleset_digest_at_review=ruleset_digest(),
    ))
    db.add(ScenarioDraftPensionElection(
        election_id=ELECTION_ID, scenario_id=SCENARIO_A,
        decision_id=DECISION_ID, scenario_version=1,
        pension_start_date=date(2032, 1, 1), target_year=2032,
        survivors_option="60%", spouse_age_diff=0,
        coefficient_selection="manual_review_required",
        company_name="מבטח סינתטי 78", option_name="standard",
    ))
    db.flush()
    for scenario_id in (SCENARIO_A, SCENARIO_B):
        _revision(db, db.get(ScenarioDraft, scenario_id), "create", ACTOR)
    # NO fixation professional decisions, NO factor admissions, NO calculations.

def run(env: dict[str, str], factory) -> None:
    validate_target(env)
    load_all_models()
    # Failures anywhere in the block roll back the entire fixture atomically.
    with factory.begin() as db:
        create_fixture(db)

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Explicit, separately authorized one-time write")
    parser.add_argument("--confirm", default="", help="Must equal supervisor78:410078:railway-staging")
    args = parser.parse_args()
    if not args.execute or args.confirm != "supervisor78:410078:railway-staging":
        parser.error("NO WRITE: requires --execute and exact --confirm after supervisory approval")
    validate_target(os.environ)
    run(dict(os.environ), get_session_factory())
    print("SUPERVISOR78_STAGING_FIXTURE_CREATED: client=410078, no professional admissions")

if __name__ == "__main__":
    main()
