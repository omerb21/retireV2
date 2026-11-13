"""Synthetic-only browser acceptance seed; never accepts a remote database."""
from __future__ import annotations

import json
import os
from datetime import date, datetime, timezone
from types import SimpleNamespace
from decimal import Decimal
from urllib.parse import urlsplit

from sqlalchemy import select

from app.db.base import load_all_models
from app.db.session import get_session_factory
from app.models.client import Client
from app.models.employment_record import EmploymentRecord
from app.models.grant import Grant
from app.models.pension_product import COMPONENT_CODES, PensionProduct, PensionProductComponent
from app.services.pension_product_service import component_balances, product_response
from app.models.scenario_draft import ScenarioDraft
from app.services import scenario_draft_service as drafts
from app.models.scenario_draft import ScenarioDraftDecision
from app.models.scenario_draft_pension_election import ScenarioDraftPensionElection
from app.models.m07_evidence import M07EvidenceRevision, M07FactEvidence
from app.schemas.m07_evidence import AssessmentRun
from app.services.m07_evidence_service import finalize_revision as finalize_m07_revision
from app.schemas.scenario_fixation_approval import (
    FixationAdmissionControls, FixationProfessionalDecision, FixationProfessionalDraftReplace,
)
from app.services import scenario_fixation_approval_service as fixation_review
from app.services.scenario_unified_engine_binding_service import build_unified_scenario_engine_bindings
from app.models.planning_input_decision import PlanningInputDecision
from app.services.scenario_draft_service import _source_evidence
from app.services.scenario_permission_preview_service import ruleset_digest
from app.schemas.official_parameter_sets import (
    OfficialParameterSetCreate, OfficialParameterValues,
    OfficialParameterVerificationRequest, OfficialParameterActivationRequest,
)
from app.services.official_parameter_service import (
    create_official_parameter_set_draft, verify_official_parameter_set,
    activate_official_parameter_set,
)
from app.services import scenario_fixation_admission_preparation_service as admission_preparation
from app.services import scenario_fixation_admission_eligibility_service as admission_eligibility

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


# Dedicated data for Supervisor 78. It intentionally does not modify client
# 410041 or either previously accepted Supervisor 65 scenario.
REVIEW_CLIENT = 410078
REVIEW_A = "supervisor78-scenario-a"
REVIEW_B = "supervisor78-scenario-b"
REVIEW_PRODUCT = "supervisor78-product"
REVIEW_COMPONENT = "supervisor78-pension-component"
REVIEW_DECISION = "supervisor78-pension-decision"
REVIEW_M07 = "supervisor78-m07"
REVIEW_PARAMETERS = "supervisor78-parameters-2026"


def seed_admission_review() -> None:
    _assert_local_database()
    now = datetime(2026, 1, 2, 8, 0, tzinfo=timezone.utc)
    factory = get_session_factory()
    with factory.begin() as db:
        if db.get(Client, REVIEW_CLIENT):
            raise RuntimeError("SUPERVISOR78_REVIEW_SEED_NOT_EMPTY")
        db.add(Client(
            client_id=REVIEW_CLIENT, display_name="לקוח סינתטי קבילות 78",
            id_number="SYNTHETIC-SUPERVISOR78", birth_date=date(1965, 5, 12),
        ))
        db.flush()
        db.add(PensionProduct(
            product_id=REVIEW_PRODUCT, client_id=REVIEW_CLIENT,
            source_kind="imported", source_identity="imported:supervisor78:synthetic",
            product_name="קרן פנסיה סינתטית 78", product_type="קרן פנסיה",
            account_reference="SYNTHETIC-78", version=1,
            historical_employers=[], created_by="supervisor78-test",
            updated_by="supervisor78-test",
            reported_product_total=Decimal("200.00"),
            reported_rewards_total=Decimal("200.00"),
            reported_severance_total=Decimal("0.00"),
        ))
        db.flush()
        # Canonical product reads require all 11 component codes, including
        # explicit zero balances. Only the single pension component carries value.
        pension_code = COMPONENT_CODES[1]
        for code in COMPONENT_CODES:
            db.add(PensionProductComponent(
                component_id=REVIEW_COMPONENT if code == pension_code
                    else f"supervisor78-zero-{COMPONENT_CODES.index(code):02d}",
                product_id=REVIEW_PRODUCT, component_code=code,
                balance=Decimal("200.00") if code == pension_code else Decimal("0.00"),
            ))
        db.flush()
        # Focused seed acceptance at the exact canonical API serialization
        # boundary. A missing, repeated or unsupported component fails here.
        balances = component_balances(db, REVIEW_PRODUCT)
        api_product = product_response(db, db.get(PensionProduct, REVIEW_PRODUCT))
        if (len(balances) != len(COMPONENT_CODES)
                or set(balances) != set(COMPONENT_CODES)
                or balances[pension_code] != Decimal("200.00")
                or any(value != Decimal("0.00") for code, value in balances.items()
                       if code != pension_code)
                or api_product["client_id"] != REVIEW_CLIENT
                or api_product["product_id"] != REVIEW_PRODUCT
                or len(api_product["conversion_components"]) != len(COMPONENT_CODES)
                or set(api_product["components"]) != set(COMPONENT_CODES)):
            raise RuntimeError("SUPERVISOR78_CANONICAL_COMPONENTS_INVALID")
        db.add(PlanningInputDecision(
            client_id=REVIEW_CLIENT, version=1, planning_base_date=date(2026, 11, 1),
            retirement_target_date=date(2032, 1, 1), actor="supervisor78-test",
        ))
        for scenario_id, scenario_name in (
            (REVIEW_A, "חלופת קבילות א"),
            (REVIEW_B, "חלופת קבילות ב"),
        ):
            db.add(ScenarioDraft(
                scenario_id=scenario_id, client_id=REVIEW_CLIENT,
                name=scenario_name, status="draft", version=1,
                created_by="supervisor78-test", updated_by="supervisor78-test",
            ))
        db.flush()
        product = db.get(PensionProduct, REVIEW_PRODUCT)
        component = db.get(PensionProductComponent, REVIEW_COMPONENT)
        source = _source_evidence(product, component)
        db.add(ScenarioDraftDecision(
            decision_id=REVIEW_DECISION, scenario_id=REVIEW_A,
            source_product_id=REVIEW_PRODUCT, source_component_id=REVIEW_COMPONENT,
            component_code=component.component_code,
            amount=Decimal("40.00"), action="pension", effective_date=date(2027, 1, 1),
            validation_state="unverified", product_version_at_review=1,
            source_fingerprint_at_review=source["source_fingerprint"],
            ruleset_digest_at_review=ruleset_digest(),
        ))
        db.add(ScenarioDraftPensionElection(
            election_id="supervisor78-pension-election",
            scenario_id=REVIEW_A,
            decision_id=REVIEW_DECISION,
            scenario_version=1,
            pension_start_date=date(2032, 1, 1),
            target_year=2032,
            survivors_option="60%",
            spouse_age_diff=0,
            coefficient_selection="manual_review_required",
        ))
        db.flush()
        for scenario_id in (REVIEW_A, REVIEW_B):
            drafts._revision(db, db.get(ScenarioDraft, scenario_id),
                             "create", "supervisor78-test")

    # Match the accepted real-PG16 M07 and official parameter setup used in
    # test_pg16_fixation_admission_review_real_basic_path_without_calculation_or_writes.
    with factory.begin() as db:
        parameter = create_official_parameter_set_draft(
            db_session=db,
            request=OfficialParameterSetCreate(
                parameter_set_id=REVIEW_PARAMETERS, tax_year=2026,
                effective_from=date(2026, 1, 1), effective_to=date(2026, 12, 31),
                parameter_set_version="2026-r1",
                values=OfficialParameterValues(
                    monthly_cap="1000", exemption_percentage="0.5",
                    capital_multiplier="180", grant_impact_multiplier="1.35"),
                source_type="official_publication", source_title="Synthetic official source",
                official_source_reference="official://supervisor78/2026",
                source_publication_date=date(2025, 12, 15),
                source_recorded_at=now, source_evidence_metadata={"synthetic": True},
                created_by="supervisor78-test",
            ), timestamp=now,
        )
        verify_official_parameter_set(
            db_session=db, parameter_set_id=parameter.parameter_set_id,
            request=OfficialParameterVerificationRequest(
                verified_by="supervisor78-verifier",
                verification_note="Synthetic verified evidence only"),
            timestamp=now,
        )
        activate_official_parameter_set(
            db_session=db, parameter_set_id=parameter.parameter_set_id,
            request=OfficialParameterActivationRequest(
                activated_by="supervisor78-activator"), timestamp=now,
        )
        db.add(M07EvidenceRevision(
            m07_evidence_revision_id=REVIEW_M07,
            profile_id="supervisor78-profile", client_id=REVIEW_CLIENT,
            revision_number=1, tax_year=2026, event_year=2026,
            event_type="fixation", schema_version="pkg004b1.m07-evidence.v1",
            rule_version="pkg004b1.technical-assessment.v1",
            status="draft", authority_classification="EVIDENCE_ONLY_NOT_PROFESSIONAL_AUTHORITY",
            technical_outcomes=[], canonical_payload={"eligibility_date": "2026-10-01"},
            evidence_fingerprint="1" * 64, source_snapshot_fingerprint="2" * 64,
            fingerprint_algorithm_version="sha256-v1",
            created_at=now, created_by="supervisor78-test",
        ))
        db.flush()
        db.add(M07FactEvidence(
            fact_evidence_id="supervisor78-eligibility", m07_evidence_revision_id=REVIEW_M07,
            client_id=REVIEW_CLIENT, field_code="eligibility_date",
            fact_identity_key="3" * 64, structured_value="2026-10-01",
            collection_state="recorded", collection_basis=None,
            verification_state="verified",
            authority_classification="EVIDENCE_ONLY_NOT_PROFESSIONAL_AUTHORITY",
            source_type="official_document", source_record_type="document",
            source_record_id="supervisor78-eligibility-document",
            source_document_reference="document://supervisor78/eligibility",
            source_date=date(2026, 10, 1), source_excerpt=None,
            source_metadata={}, recorded_at=now, recorded_by="supervisor78-test",
            verified_at=now, verified_by="supervisor78-test",
            verification_basis="Synthetic verified document",
            assertion_id=None, content_fingerprint="4" * 64,
        ))
        db.flush()
        finalize_m07_revision(
            db_session=db, client_id=REVIEW_CLIENT, revision_id=REVIEW_M07,
            actor="supervisor78-test", assessment=AssessmentRun(), timestamp=now,
        )

    bound = build_unified_scenario_engine_bindings(
        factory, client_id=REVIEW_CLIENT, scenario_id=REVIEW_A,
    )
    readiness = bound["domain_results"]["fixation_tax"]["readiness"]
    if bound["base"]["blockers"]:
        raise RuntimeError(
            "SUPERVISOR78_SCENARIO_BASE_NOT_CURRENT:" +
            str(bound["base"]["blockers"])
        )
    req = FixationProfessionalDraftReplace(
        expected_approval_version=0,
        expected_scenario_version=readiness["scenario_version"],
        expected_manifest_fingerprint=readiness["manifest_fingerprint"],
        expected_readiness_fingerprint=readiness["readiness_fingerprint"],
        decisions=[
            FixationProfessionalDecision(
                group="eligibility", source_id=REVIEW_M07,
                determination="PLANNER_ASSERTED",
                reason="Synthetic verified M07 eligibility evidence",
                evidence_references=["document://supervisor78/eligibility"],
                eligibility_date=date(2026, 10, 1),
            ),
            FixationProfessionalDecision(
                group="tax_year_and_parameters", source_id=REVIEW_PARAMETERS,
                determination="PLANNER_ASSERTED",
                reason="Synthetic active parameter set for tax year",
                evidence_references=["official://supervisor78/2026"],
                tax_year=2026, parameter_set_id=REVIEW_PARAMETERS,
            ),
            FixationProfessionalDecision(
                group="pension_classification", source_id=REVIEW_DECISION,
                determination="PLANNER_ASSERTED",
                reason="Synthetic professional pension classification for review only",
                evidence_references=["document://supervisor78/pension"],
                tax_classification="QUALIFYING_PENSION_FOR_FIXATION",
            ),
        ],
        admission_controls=FixationAdmissionControls(
            calculation_version="pkg-012-m08d-v1",
            grants_collection={
                "state": "confirmed_none",
                "evidence_references": ["review://supervisor78/grants-none"],
            },
            actual_capitalizations_collection={
                "state": "confirmed_none",
                "evidence_references": ["review://supervisor78/capitalizations-none"],
            },
            idf={
                "applicability": "NOT_APPLICABLE",
                "evidence_references": ["review://supervisor78/idf-none"],
                "input": None,
            },
        ),
    )
    with factory.begin() as db:
        fixation_review.save_draft(db, REVIEW_CLIENT, REVIEW_A, req,
                                   "supervisor78-synthetic-planner")

    with factory() as db:
        preparation = admission_preparation.prepare(db, REVIEW_CLIENT, REVIEW_A)
        eligibility = admission_eligibility.assess(db, REVIEW_CLIENT, REVIEW_A)
        other = admission_preparation.prepare(db, REVIEW_CLIENT, REVIEW_B)
    if preparation["state"] != "PREPARED":
        raise RuntimeError(
            "SUPERVISOR78_PREPARATION_NOT_READY:" +
            str((preparation["blockers"], preparation["incomplete_reasons"]))
        )
    if eligibility["state"] != "ELIGIBLE_FOR_ADMISSION_REVIEW":
        raise RuntimeError("SUPERVISOR78_ELIGIBILITY_NOT_READY:" + str(eligibility["reasons"]))
    if eligibility["preparation_fingerprint"] != preparation["preparation_fingerprint"]:
        raise RuntimeError("SUPERVISOR78_SOURCE_FINGERPRINT_CONFLICT")
    if other["state"] == "PREPARED":
        raise RuntimeError("SUPERVISOR78_OTHER_SCENARIO_UNEXPECTEDLY_PREPARED")
    if eligibility["professional_authority"] or eligibility["execution_allowed"]:
        raise RuntimeError("SUPERVISOR78_AUTHORITY_NOT_BLOCKED")
    print(json.dumps({
        "client_id": REVIEW_CLIENT, "scenario_a": REVIEW_A, "scenario_b": REVIEW_B,
        "preparation": preparation["state"], "eligibility": eligibility["state"],
        "fingerprint": preparation["preparation_fingerprint"],
        "synthetic": True, "professional_authority": False,
    }, ensure_ascii=False))



def main() -> None:
    _assert_local_database()
    load_all_models()
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
    seed_admission_review()
    print(json.dumps({
        "client_id": CLIENT_ID, "scenario_a": SCENARIO_A,
        "scenario_b": SCENARIO_B, "grant_id": GRANT_ID,
        "employment_id": EMPLOYMENT_ID, "component_id": COMPONENT_ID,
        "synthetic": True,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
