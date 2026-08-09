from __future__ import annotations

from datetime import date
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text, update
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base, load_all_models
from app.db.session import get_db
from app.main import app
from app.models.client import Client
from app.models.m05_ledger import M05LedgerSubject, authorize_m05_insert
from app.models.m06_conversion import (
    M06CalculationManifest,
    M06CoefficientEvidence,
    M06ConversionRevision,
    M06ConversionSubject,
)
from app.schemas.m06_conversion import M06CandidateResponse, M06CoefficientIntent
from app.services import m06_conversion_service as service


@pytest.fixture
def api(tmp_path: Path, monkeypatch):
    load_all_models()
    engine = create_engine(
        f"sqlite:///{tmp_path / 'pkg011.db'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    with sessions() as db:
        db.add_all(
            [
                Client(
                    client_id=1, display_name="One", id_number="001", status="delivered"
                ),
                Client(
                    client_id=2, display_name="Two", id_number="002", status="delivered"
                ),
            ]
        )
        db.flush()
        m05 = M05LedgerSubject(
            client_id=1,
            provider_name="Exact Provider",
            account_reference="A-001",
            provider_identity_digest="a" * 64,
            account_identity_digest="b" * 64,
        )
        authorize_m05_insert(m05)
        db.add(m05)
        db.commit()
        m05_id = m05.subject_id
    candidate = M06CandidateResponse(
        candidate_id="M06-CAND-test",
        m05_subject_id=m05_id,
        m05_revision_id="M05-R-current",
        m02_intake_id="M02-I-current",
        provider_name="Exact Provider",
        account_reference="A-001",
        product_family="pension_fund",
        mode="balance_to_monthly_pension",
        input_identity="component:contribution",
        input_amount="1000.00",
        input_date=date(2026, 1, 31),
        formula_id="m06.balance_to_monthly_pension.v1",
        eligible=True,
        exclusion_reasons=[],
        informational_warnings=["stale_warning"],
    )
    monkeypatch.setattr(
        service,
        "_candidate_rows",
        lambda _db, client_id: [candidate] if client_id == 1 else [],
    )
    monkeypatch.setattr(
        service,
        "_predecessor_snapshot",
        lambda _db, client_id, row: {
            "client_id": client_id,
            "m02_intake_id": row.m02_intake_id,
            "m03_revision_id": "M03-R-current",
            "m04_revision_id": "M04-R-current",
            "m04_evidence_digest": "c" * 64,
            "m04_catalogue_version": "m04-v1",
            "m04_input_snapshot_digest": "d" * 64,
            "m05_subject_id": row.m05_subject_id,
            "m05_revision_id": row.m05_revision_id,
            "m05_candidate_id": "M05-CAND-current",
            "m05_source_snapshot_digest": "e" * 64,
            "m05_mapping_digest": "f" * 64,
            "product_context": {"m04_product_family": "pension_fund"},
            "m05_warning_snapshot": [],
            "m05_warning_dispositions": [],
            "currency_confirmation": {"currency": "ILS"},
            "statement_date": date(2026, 1, 31),
            "evaluation_date": date(2026, 2, 1),
        },
    )
    monkeypatch.setattr(
        service, "_revalidation_reasons", lambda *_args: ([], ["stale_warning"])
    )

    def override():
        with sessions() as db:
            yield db

    app.dependency_overrides[get_db] = override
    try:
        yield TestClient(app), sessions, candidate
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def planner_payload(coefficient: object = "200.000") -> dict:
    return {
        "authority_class": "planner_declared",
        "coefficient": coefficient,
        "source_note": "planner-held coefficient evidence",
        "reason": "bounded declaration",
        "applicability_declared": True,
        "metadata": {"pension_option": "recorded option"},
    }


def start(
    client: TestClient, candidate: M06CandidateResponse, coefficient: object = "200.000"
) -> dict:
    response = client.post(
        "/api/clients/1/m06/start",
        json={
            "m05_subject_id": candidate.m05_subject_id,
            "mode": candidate.mode,
            "input_identity": candidate.input_identity,
            "coefficient": planner_payload(coefficient),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.parametrize(
    "invalid", [200, True, " 200", "200 ", "2e2", "1,000", "NaN", "Infinity", "-1"]
)
def test_coefficient_rejects_noncanonical_or_nonstring(api, invalid) -> None:
    client, _, candidate = api
    response = client.post(
        "/api/clients/1/m06/start",
        json={
            "m05_subject_id": candidate.m05_subject_id,
            "mode": candidate.mode,
            "input_identity": candidate.input_identity,
            "coefficient": planner_payload(invalid),
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] in {
        "coefficient_invalid",
        "coefficient_negative",
    }


def test_missing_coefficient_has_stable_domain_code(api) -> None:
    client, _, candidate = api
    payload = planner_payload()
    payload.pop("coefficient")
    response = client.post(
        "/api/clients/1/m06/start",
        json={
            "m05_subject_id": candidate.m05_subject_id,
            "mode": candidate.mode,
            "input_identity": candidate.input_identity,
            "coefficient": payload,
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "coefficient_missing"


def test_start_preserves_precision_and_server_evidence(api) -> None:
    client, _, candidate = api
    draft = start(client, candidate, "200.000")
    assert (
        draft["state"] == "draft" and draft["coefficient"]["coefficient"] == "200.000"
    )
    assert draft["coefficient"]["decimal_exponent"] == -3
    assert draft["actor"].startswith("system:m06-conversion-ui")
    assert {item["warning_id"] for item in draft["warnings"]} == {
        "planner_declared_coefficient_authority",
        "coefficient_applicability_not_documented",
    }


def test_warning_review_calculates_exact_ratio_and_half_up_display(api) -> None:
    client, _, candidate = api
    draft = start(client, candidate, "200.000")
    resolved = client.post(
        f"/api/clients/1/m06/subjects/{draft['subject_id']}/resolve",
        json={"expected_current_revision_id": draft["revision_id"]},
    ).json()
    warnings = [item["warning_id"] for item in resolved["warnings"]]
    response = client.post(
        f"/api/clients/1/m06/subjects/{draft['subject_id']}/review-warning",
        json={
            "expected_current_revision_id": resolved["revision_id"],
            "warning_ids": warnings,
            "reason_code": "planner_warning_review",
            "explanation": "reviewed exact warnings",
            "confirmed": True,
        },
    )
    assert response.status_code == 201, response.text
    reviewed = response.json()
    assert reviewed["state"] == "warning_reviewed"
    assert reviewed["manifest"]["raw_result_kind"] == "exact_ratio"
    assert reviewed["manifest"]["raw_numerator"] == "1000.00"
    assert reviewed["manifest"]["raw_denominator"] == "200.000"
    assert reviewed["manifest"]["display_result"] == "5.00"
    eligibility = client.get(
        f"/api/clients/1/m06/subjects/{draft['subject_id']}/eligibility"
    ).json()
    assert eligibility["eligible_for_downstream"] is True
    assert (
        eligibility["meaning"]
        == "technically eligible under the bounded PKG-011 M06 contract"
    )


def test_warning_set_is_exact_and_bound_to_current_revision(api) -> None:
    client, _, candidate = api
    draft = start(client, candidate)
    resolved = client.post(
        f"/api/clients/1/m06/subjects/{draft['subject_id']}/resolve",
        json={"expected_current_revision_id": draft["revision_id"]},
    ).json()
    path = f"/api/clients/1/m06/subjects/{draft['subject_id']}/review-warning"
    wrong = client.post(
        path,
        json={
            "expected_current_revision_id": resolved["revision_id"],
            "warning_ids": ["caller_forged"],
            "reason_code": "planner_warning_review",
            "explanation": "wrong",
            "confirmed": True,
        },
    )
    assert (
        wrong.status_code == 409
        and wrong.json()["detail"]["code"] == "warning_disposition_invalid"
    )


def test_correction_appends_draft_and_preserves_history(api) -> None:
    client, _, candidate = api
    draft = start(client, candidate)
    response = client.post(
        f"/api/clients/1/m06/subjects/{draft['subject_id']}/correct-coefficient",
        json={
            "expected_current_revision_id": draft["revision_id"],
            "coefficient": planner_payload("201.1250"),
            "correction_reason": "new evidence",
        },
    )
    assert response.status_code == 201, response.text
    corrected = response.json()
    assert corrected["revision_sequence"] == 2 and corrected["state"] == "draft"
    assert corrected["coefficient"]["coefficient"] == "201.1250"
    trail = client.get(
        f"/api/clients/1/m06/subjects/{draft['subject_id']}/history"
    ).json()
    assert [row["coefficient"]["coefficient"] for row in trail] == [
        "200.000",
        "201.1250",
    ]


def test_duplicate_start_and_stale_action_leave_one_chain(api) -> None:
    client, _, candidate = api
    draft = start(client, candidate)
    duplicate = client.post(
        "/api/clients/1/m06/start",
        json={
            "m05_subject_id": candidate.m05_subject_id,
            "mode": candidate.mode,
            "input_identity": candidate.input_identity,
            "coefficient": planner_payload(),
        },
    )
    assert (
        duplicate.status_code == 409
        and duplicate.json()["detail"]["code"] == "conversion_subject_conflict"
    )
    path = f"/api/clients/1/m06/subjects/{draft['subject_id']}/supersede"
    winner = client.post(
        path,
        json={
            "expected_current_revision_id": draft["revision_id"],
            "reason": "explicit supersession",
        },
    )
    loser = client.post(
        path,
        json={
            "expected_current_revision_id": draft["revision_id"],
            "reason": "stale supersession",
        },
    )
    assert winner.status_code == 201 and loser.status_code == 409
    assert (
        len(
            client.get(
                f"/api/clients/1/m06/subjects/{draft['subject_id']}/history"
            ).json()
        )
        == 2
    )


def test_foreign_and_missing_subjects_are_indistinguishable(api) -> None:
    client, _, candidate = api
    draft = start(client, candidate)
    foreign = client.get(f"/api/clients/2/m06/subjects/{draft['subject_id']}")
    missing = client.get("/api/clients/2/m06/subjects/M06-S-missing")
    assert (foreign.status_code, foreign.json()) == (
        missing.status_code,
        missing.json(),
    )
    assert foreign.json()["detail"] == {
        "code": "reference_unavailable",
        "message": "referenced conversion evidence is unavailable",
    }


def test_models_are_append_only(api) -> None:
    client, sessions, candidate = api
    draft = start(client, candidate)
    with sessions() as db:
        row = db.get(M06ConversionRevision, draft["revision_id"])
        assert row is not None
        row.state = "resolved"
        with pytest.raises(ValueError, match="immutable"):
            db.flush()
        db.rollback()
        subject = db.get(M06ConversionSubject, draft["subject_id"])
        db.delete(subject)
        with pytest.raises(ValueError, match="cannot be deleted"):
            db.flush()


def test_bulk_and_text_mutations_are_blocked(api) -> None:
    client, sessions, candidate = api
    draft = start(client, candidate)
    with sessions() as db:
        with pytest.raises(ValueError, match="cannot be updated or deleted"):
            db.execute(
                update(M06ConversionRevision)
                .where(M06ConversionRevision.revision_id == draft["revision_id"])
                .values(state="resolved")
            )
        with pytest.raises(ValueError, match="cannot be updated or deleted"):
            db.execute(
                text(
                    "UPDATE m06_conversion_revisions SET state='resolved' WHERE revision_id=:id"
                ),
                {"id": draft["revision_id"]},
            )


def test_safe_negative_input_resolves_blocked_without_result(api, monkeypatch) -> None:
    client, _, candidate = api
    negative = candidate.model_copy(
        update={
            "input_amount": "-0.01",
            "exclusion_reasons": ["authoritative_input_negative"],
            "eligible": False,
        }
    )
    monkeypatch.setattr(
        service,
        "_candidate_rows",
        lambda _db, client_id: [negative] if client_id == 1 else [],
    )
    draft = start(client, negative)
    response = client.post(
        f"/api/clients/1/m06/subjects/{draft['subject_id']}/resolve",
        json={"expected_current_revision_id": draft["revision_id"]},
    )
    assert response.status_code == 201, response.text
    assert response.json()["state"] == "blocked"
    assert response.json()["manifest"]["display_result"] is None
    assert response.json()["manifest"]["raw_result_kind"] is None


def test_mutation_schema_rejects_caller_forged_authority_fields(api) -> None:
    client, _, candidate = api
    payload = {
        "m05_subject_id": candidate.m05_subject_id,
        "mode": candidate.mode,
        "input_identity": candidate.input_identity,
        "coefficient": planner_payload(),
        "actor": "human",
        "input_amount": "1",
        "eligibility": True,
        "display_result": "999",
    }
    assert client.post("/api/clients/1/m06/start", json=payload).status_code == 422


def test_concurrent_duplicate_start_has_one_winner_and_no_residue(
    api, monkeypatch
) -> None:
    client, sessions, candidate = api
    original = service._predecessor_snapshot
    barrier = Barrier(2)

    def synchronized(*args):
        value = original(*args)
        barrier.wait(timeout=10)
        return value

    monkeypatch.setattr(service, "_predecessor_snapshot", synchronized)
    payload = {
        "m05_subject_id": candidate.m05_subject_id,
        "mode": candidate.mode,
        "input_identity": candidate.input_identity,
        "coefficient": planner_payload(),
    }
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(
            pool.map(
                lambda _: client.post("/api/clients/1/m06/start", json=payload),
                range(2),
            )
        )
    assert sorted(response.status_code for response in responses) == [201, 409]
    with sessions() as db:
        assert len(list(db.scalars(select(M06ConversionSubject)))) == 1
        assert len(list(db.scalars(select(M06ConversionRevision)))) == 1


def test_exact_multiplication_and_zero_are_not_missing() -> None:
    row = M06ConversionRevision(
        mode="monthly_pension_to_capital_equivalent",
        formula_id="m06.monthly_pension_to_capital_equivalent.v1",
        input_amount="0.00",
    )
    evidence = type("Evidence", (), {"coefficient_text": "200.1250"})()
    assert service._calculate(row, evidence) == (
        "exact_decimal",
        "0",
        None,
        None,
        "0.00",
    )


def test_exact_multiplication_retains_raw_precision_and_rounds_display_half_up() -> (
    None
):
    row = M06ConversionRevision(
        mode="monthly_pension_to_capital_equivalent",
        formula_id="m06.monthly_pension_to_capital_equivalent.v1",
        input_amount="10.01",
    )
    evidence = type("Evidence", (), {"coefficient_text": "2.500"})()
    assert service._calculate(row, evidence) == (
        "exact_decimal",
        "25.025",
        None,
        None,
        "25.03",
    )


def test_inclusive_effective_period_and_documentary_warning_boundary(
    api, monkeypatch
) -> None:
    _, sessions, candidate = api
    monkeypatch.setattr(service, "_documentary_valid", lambda *_: True)
    with sessions() as db:
        intent = M06CoefficientIntent(
            authority_class="documentary",
            coefficient="200.125",
            source_intake_id="source",
            source_locator="page 3 row 2",
            reason="documented",
            effective_from=candidate.input_date,
            effective_to=candidate.input_date,
            applicability_declared=False,
        )
        warnings, blockers = service._evidence_values(db, 1, candidate, intent)
    assert warnings == [] and blockers == []


def test_manifest_fingerprint_is_canonical_for_mapping_order() -> None:
    assert service._digest({"b": 2, "a": [3, 1]}) == service._digest(
        {"a": [3, 1], "b": 2}
    )
    assert service._digest({"a": [1, 3], "b": 2}) != service._digest(
        {"a": [3, 1], "b": 2}
    )


def test_documentary_intent_requires_complete_provenance() -> None:
    with pytest.raises(ValueError):
        M06CoefficientIntent(
            authority_class="documentary",
            coefficient="200",
            reason="source",
            applicability_declared=False,
        )


def test_candidate_derivation_is_exactly_allowlisted_and_mode_specific(
    monkeypatch,
) -> None:
    contribution = SimpleNamespace(
        component_kind="contribution_component",
        included_in_reconciliation=True,
        evidence_identity="M04-E-contribution",
        effective_value=Decimal("1234.50"),
    )
    severance = SimpleNamespace(
        component_kind="severance_component",
        included_in_reconciliation=True,
        evidence_identity="M04-E-severance",
        effective_value=Decimal("999.00"),
    )
    current = SimpleNamespace(
        revision_id="M05-R-current",
        product_context={
            "m04_product_family": "insurance_policy",
            "m04_aggregate_interpretation": "pension",
        },
        values=[contribution, severance],
        m04_revision_id="M04-R-current",
        intake_id="M02-I-current",
        provider_name="Exact Provider",
        account_reference="A-001",
        statement_date=date(2026, 1, 31),
    )
    subject = SimpleNamespace(
        subject_id="M05-S-current",
        current_revision=current,
        eligibility=SimpleNamespace(
            eligible_for_m06=True, informational_warnings=["stale_warning"]
        ),
    )
    intake = SimpleNamespace(
        intake_id="M02-I-current",
        record_kind="manual",
        lifecycle_status="accepted_for_review",
        declared_monthly_pension_amount=Decimal("88.25"),
        declared_statement_date=date(2026, 1, 15),
    )
    db = SimpleNamespace(scalar=lambda _query: intake)
    monkeypatch.setattr(service, "m05_list_subjects", lambda *_: [subject])
    monkeypatch.setattr(
        service,
        "_current_m04_component",
        lambda *_: SimpleNamespace(
            interpretation="pension", current_employer_related="no"
        ),
    )

    rows = service._candidate_rows(db, 1)

    assert [row.mode for row in rows] == [
        "balance_to_monthly_pension",
        "monthly_pension_to_capital_equivalent",
    ]
    assert rows[0].input_amount == "1234.50"
    assert rows[0].input_identity == "M04-E-contribution"
    assert rows[1].input_amount == "88.25"
    assert rows[1].input_identity == "M02-I-current:declared_monthly_pension_amount"
    assert all(row.product_family == "insurance_policy" for row in rows)

    current.product_context["m04_product_family"] = "provident_fund"
    assert service._candidate_rows(db, 1) == []
    current.product_context["m04_product_family"] = "pension_fund"
    monkeypatch.setattr(
        service,
        "_current_m04_component",
        lambda *_: SimpleNamespace(
            interpretation="pension", current_employer_related="yes"
        ),
    )
    assert service._candidate_rows(db, 1) == []


@pytest.mark.parametrize(
    ("coefficient", "code"),
    [("0", "coefficient_zero"), ("-0.01", "coefficient_negative")],
)
def test_coefficient_domain_rejections_have_stable_codes(coefficient, code) -> None:
    with pytest.raises(service.M06ConversionError) as raised:
        service._coefficient(coefficient)
    assert raised.value.code == code


def test_date_contract_supports_open_bounds_and_fails_closed(api, monkeypatch) -> None:
    _, sessions, candidate = api
    monkeypatch.setattr(service, "_documentary_valid", lambda *_: True)

    def evaluate(**dates):
        with sessions() as db:
            return service._evidence_values(
                db,
                1,
                candidate,
                M06CoefficientIntent(
                    authority_class="documentary",
                    coefficient="200",
                    source_intake_id="source",
                    source_locator="page 1",
                    reason="documented",
                    **dates,
                ),
            )

    assert evaluate(effective_from=date(2025, 1, 1))[1] == []
    assert evaluate(effective_to=date(2026, 1, 31))[1] == []
    assert evaluate(effective_from=date(2026, 2, 1), effective_to=date(2026, 1, 1))[
        1
    ] == ["coefficient_date_contradiction"]
    assert evaluate(effective_from=date(2026, 2, 1))[1] == [
        "coefficient_date_contradiction"
    ]
    assert evaluate()[1] == ["coefficient_applicability_missing"]


def test_large_exact_multiplication_never_uses_context_rounding() -> None:
    amount = "123456789012345678901234567890.12345"
    coefficient = "987654321098765432109876543210.54321"
    row = M06ConversionRevision(
        mode="monthly_pension_to_capital_equivalent",
        formula_id="m06.monthly_pension_to_capital_equivalent.v1",
        input_amount=amount,
    )
    evidence = type("Evidence", (), {"coefficient_text": coefficient})()
    result = service._calculate(row, evidence)
    with service.localcontext() as context:
        context.prec = 200
        expected = service._decimal_text(Decimal(amount) * Decimal(coefficient))
    assert result[0] == "exact_decimal" and result[1] == expected


def test_resolve_failure_rolls_back_successor_and_owned_evidence(
    api, monkeypatch
) -> None:
    client, sessions, candidate = api
    draft = start(client, candidate)
    monkeypatch.setattr(
        service,
        "_manifest",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("fail")),
    )
    with sessions() as db, pytest.raises(RuntimeError, match="fail"):
        service.resolve_conversion(db, 1, draft["subject_id"], draft["revision_id"])
    with sessions() as db:
        assert len(list(db.scalars(select(M06ConversionRevision)))) == 1
        assert len(list(db.scalars(select(M06CoefficientEvidence)))) == 1
        assert len(list(db.scalars(select(M06CalculationManifest)))) == 0


def test_concurrent_resolve_has_one_child_and_no_partial_rows(api, monkeypatch) -> None:
    client, sessions, candidate = api
    draft = start(client, candidate)
    original = service._assert_expected
    barrier = Barrier(2)

    def synchronized(*args):
        original(*args)
        barrier.wait(timeout=10)

    monkeypatch.setattr(service, "_assert_expected", synchronized)
    path = f"/api/clients/1/m06/subjects/{draft['subject_id']}/resolve"
    payload = {"expected_current_revision_id": draft["revision_id"]}
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: client.post(path, json=payload), range(2)))
    assert sorted(response.status_code for response in responses) == [201, 409]
    with sessions() as db:
        revisions = list(db.scalars(select(M06ConversionRevision)))
        evidence = list(db.scalars(select(M06CoefficientEvidence)))
        manifests = list(db.scalars(select(M06CalculationManifest)))
    assert len(revisions) == 2
    assert len(evidence) == 2
    assert len(manifests) == 1


def test_material_manifest_change_changes_fingerprint() -> None:
    baseline = {"warnings": ["a", "b"], "coefficient": "200"}
    changed = {"warnings": ["a", "b"], "coefficient": "201"}
    assert service._manifest_fingerprint(baseline) != service._manifest_fingerprint(
        changed
    )


def test_read_time_revalidation_reports_each_changed_predecessor(monkeypatch) -> None:
    subject = SimpleNamespace(client_id=1, m05_subject_id="M05-S")
    leaf = SimpleNamespace(
        revision_id="M06-R-current",
        state="resolved",
        m02_intake_id="M02-I-old",
        m03_revision_id="M03-R-old",
        m04_revision_id="M04-R-old",
        m05_revision_id="M05-R-old",
        formula_id="m06.balance_to_monthly_pension.v1",
        input_identity="component",
        predecessor_snapshot={"m05_revision_id": "M05-R-old"},
    )
    current_revision = SimpleNamespace(
        revision_id="M05-R-new",
        m03_revision_id="M03-R-new",
        m04_revision_id="M04-R-new",
    )
    monkeypatch.setattr(
        service,
        "m05_subject_response",
        lambda *_: SimpleNamespace(current_revision=current_revision),
    )
    monkeypatch.setattr(
        service,
        "m05_eligibility",
        lambda *_: SimpleNamespace(
            eligible_for_m06=False,
            exclusion_reasons=["archived_case"],
            informational_warnings=[],
        ),
    )
    monkeypatch.setattr(
        service,
        "m03_target_response",
        lambda *_: SimpleNamespace(eligible=False, accepted_revision_id="M03-R-new"),
    )
    monkeypatch.setattr(
        service,
        "m04_eligibility",
        lambda *_: SimpleNamespace(
            eligible_for_m05=False, current_revision_id="M04-R-new"
        ),
    )
    evidence = SimpleNamespace(
        authority_class="planner_declared", evidence_digest="a" * 64
    )
    monkeypatch.setattr(service, "_coefficient_row", lambda *_: evidence)
    monkeypatch.setattr(service, "_coefficient_digest", lambda *_: "a" * 64)
    manifest_payload = {
        "formula_id": leaf.formula_id,
        "input_identity": leaf.input_identity,
        "coefficient_evidence_id": "E",
        "predecessors": leaf.predecessor_snapshot,
    }
    manifest_payload["fingerprint"] = service._manifest_fingerprint(manifest_payload)
    monkeypatch.setattr(
        service,
        "_manifest_row",
        lambda *_: SimpleNamespace(
            manifest=manifest_payload, fingerprint=manifest_payload["fingerprint"]
        ),
    )
    evidence.evidence_id = "E"
    db = SimpleNamespace(
        scalar=lambda _query: SimpleNamespace(
            record_kind="manual", lifecycle_status="superseded"
        )
    )

    reasons, _ = service._revalidation_reasons(db, subject, leaf)

    assert set(reasons) >= {
        "m01_case_ineligible",
        "m02_predecessor_changed",
        "m03_predecessor_changed",
        "m03_predecessor_ineligible",
        "m04_predecessor_changed",
        "m04_predecessor_ineligible",
        "m05_predecessor_changed",
        "m05_predecessor_ineligible",
    }
