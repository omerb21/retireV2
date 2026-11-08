"""Synthetic-only browser acceptance seed; never accepts a remote database."""
from __future__ import annotations

import json
import os
from datetime import date
from decimal import Decimal
from urllib.parse import urlsplit

from sqlalchemy import select

from app.db.session import get_session_factory
from app.models.client import Client
from app.models.employment_record import EmploymentRecord
from app.models.grant import Grant
from app.models.pension_product import PensionProduct, PensionProductComponent
from app.models.scenario_draft import ScenarioDraft
from app.services import scenario_draft_service as drafts

CLIENT_ID = 410041
EMPLOYMENT_ID = "supervisor41-employment"
GRANT_ID = "supervisor41-grant"
PRODUCT_ID = "supervisor41-product"
COMPONENT_ID = "supervisor41-severance"
SCENARIO_A = "supervisor41-scenario-a"
SCENARIO_B = "supervisor41-scenario-b"


def _assert_local_database() -> None:
    url = os.environ.get("DATABASE_URL", "")
    parsed = urlsplit(url.replace("postgresql+psycopg2://", "postgresql://", 1))
    if (os.environ.get("APP_ENV") != "test"
            or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
            or parsed.path != "/retire_v2_supervisor41_test"
            or not parsed.port):
        raise RuntimeError("SUPERVISOR41_LOCAL_DATABASE_ONLY")


def main() -> None:
    _assert_local_database()
    with get_session_factory().begin() as db:
        if db.scalar(select(Client.client_id).where(Client.client_id == CLIENT_ID)):
            raise RuntimeError("SUPERVISOR41_DATABASE_NOT_EMPTY")
        db.add(Client(
            client_id=CLIENT_ID, display_name="לקוח סינתטי לבדיקת פיצויים 41",
            id_number="SYNTHETIC-SUPERVISOR41", birth_date=date(1965, 5, 12),
        ))
        db.flush()
        db.add(EmploymentRecord(
            employment_record_id=EMPLOYMENT_ID, client_id=CLIENT_ID,
            employer_name="מעסיק סינתטי 41", work_start_date=date(2011, 1, 1),
            work_end_date=date(2025, 12, 31), is_current=False,
            exempt_grant_status="requires_reconciliation",
        ))
        db.flush()
        db.add(Grant(
            grant_id=GRANT_ID, client_id=CLIENT_ID,
            employment_record_id=EMPLOYMENT_ID, employer_name="מעסיק סינתטי 41",
            nominal_amount=Decimal("150.00"), grant_date=date(2025, 12, 31),
            work_start_date=date(2011, 1, 1),
            work_end_date=date(2025, 12, 31),
        ))
        db.add(PensionProduct(
            product_id=PRODUCT_ID, client_id=CLIENT_ID,
            source_kind="manual", source_identity="supervisor41:synthetic",
            product_name="קרן פנסיה סינתטית 41", product_type="קרן פנסיה",
            account_reference="SYNTHETIC-41", statement_date=date(2026, 11, 1),
            historical_employers=[], version=1,
            created_by="supervisor41-test", updated_by="supervisor41-test",
            reported_product_total=Decimal("200.00"),
            reported_severance_total=Decimal("200.00"),
        ))
        db.flush()
        db.add(PensionProductComponent(
            component_id=COMPONENT_ID, product_id=PRODUCT_ID,
            component_code="פיצויים_מעסיק_נוכחי", balance=Decimal("200.00"),
        ))
        for scenario_id, name in (
            (SCENARIO_A, "חלופה סינתטית א"), (SCENARIO_B, "חלופה סינתטית ב")
        ):
            db.add(ScenarioDraft(
                scenario_id=scenario_id, client_id=CLIENT_ID,
                name=name, status="draft", version=1,
                created_by="supervisor41-test", updated_by="supervisor41-test",
            ))
        db.flush()
        # Reuse the existing draft revision mechanism, never a second ledger.
        for scenario_id in (SCENARIO_A, SCENARIO_B):
            scenario = db.get(ScenarioDraft, scenario_id)
            drafts._revision(db, scenario, "create", "supervisor41-test")
    print(json.dumps({
        "client_id": CLIENT_ID, "scenario_a": SCENARIO_A,
        "scenario_b": SCENARIO_B, "grant_id": GRANT_ID,
        "employment_id": EMPLOYMENT_ID, "component_id": COMPONENT_ID,
        "synthetic": True,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
