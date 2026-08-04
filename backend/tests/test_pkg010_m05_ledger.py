from __future__ import annotations

from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, event, func, select, text, update
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base, load_all_models
from app.db.session import get_db
from app.main import app
from app.models.client import Client
from app.models.m02_intake import M02IntakeRecord
from app.models.m05_ledger import (
    M05AdjustmentEvidence,
    M05CandidateLink,
    M05LedgerRevision,
    M05LedgerSubject,
    M05LedgerValue,
)
from app.services.m05_ledger_service import (
    ELIGIBILITY_REASON_ORDER,
    CandidateEvaluation,
    _leaf_integrity_reasons,
    _ordered_eligibility_reasons,
    _reconcile,
    _upstream_eligibility_reasons,
    is_stale,
    parse_authored_money,
    parse_component_money,
)


def _intake(
    intake_id: str,
    client_id: int,
    *,
    provider: str,
    account: str,
    total: str,
    contribution: str,
    severance: str,
    statement_date: date = date(2026, 7, 1),
) -> M02IntakeRecord:
    return M02IntakeRecord(
        intake_id=intake_id,
        client_id=client_id,
        record_kind="manual",
        manual_technical_reference=f"M02-MANUAL-{intake_id}",
        declared_provider_name=provider,
        declared_account_reference=account,
        product_name="Persisted Product",
        declared_product_type="provident_fund",
        declared_total_balance_amount=Decimal(total),
        declared_component_values=[
            {"label": "Contributions", "code": "contribution_component", "value": contribution},
            {"label": "Severance", "code": "severance_component", "value": severance},
        ],
        declared_statement_date=statement_date,
        source_type="manual",
        lifecycle_status="accepted_for_review",
        preservation_status="not_applicable",
        diagnostics=[],
        created_by_actor="m02",
        updated_by_actor="m02",
        lifecycle_decided_by_actor="m02",
    )


def _accept_upstream(client: TestClient, client_id: int, intake_id: str) -> None:
    started = client.post(
        f"/api/clients/{client_id}/m03/targets/{intake_id}/start"
    ).json()
    accepted = client.post(
        f"/api/clients/{client_id}/m03/targets/{intake_id}/accept",
        json={
            "reason": "accepted evidence",
            "expected_current_revision_id": started["revision_id"],
        },
    )
    assert accepted.status_code == 201
    m04_started = client.post(
        f"/api/clients/{client_id}/m04/targets/{intake_id}/start"
    ).json()
    proposal = client.post(
        f"/api/clients/{client_id}/m04/targets/{intake_id}/proposal",
        json={"expected_current_revision_id": m04_started["revision_id"]},
    ).json()
    components = [
        {
            "evidence_identity": component["evidence_identity"],
            "component_kind": component["original_code"],
            "interpretation": "pension",
            "current_employer_related": "unknown",
            "explanation": "bounded planner classification",
        }
        for component in proposal["components"]
    ]
    overridden = client.post(
        f"/api/clients/{client_id}/m04/targets/{intake_id}/override",
        json={
            "expected_current_revision_id": proposal["revision_id"],
            "reason_code": "planner_decision",
            "explanation": "complete exact component mapping",
            "confirmed": True,
            "product_family": "provident_fund",
            "pension_subtype": None,
            "components": components,
        },
    ).json()
    accepted = client.post(
        f"/api/clients/{client_id}/m04/targets/{intake_id}/accept",
        json={
            "expected_current_revision_id": overridden["revision_id"],
            "reason_code": "planner_decision",
            "explanation": "explicit acceptance",
        },
    )
    assert accepted.status_code == 201


@pytest.fixture
def api(tmp_path: Path) -> Generator[tuple[TestClient, sessionmaker[Session]], None, None]:
    load_all_models()
    engine = create_engine(
        f"sqlite:///{tmp_path / 'pkg010.db'}",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    with sessions() as db:
        db.add_all(
            [
                Client(client_id=1, display_name="One", id_number="001", status="delivered"),
                Client(client_id=2, display_name="Two", id_number="002", status="delivered"),
                _intake("manual-ok", 1, provider="Exact Provider", account="A-001", total="100.00", contribution="60.00", severance="40.00"),
                _intake("manual-warning", 1, provider="Exact Provider", account="A-002", total="100.00", contribution="50.00", severance="49.00"),
                _intake("manual-negative", 1, provider="Exact Provider", account="A-003", total="-1.00", contribution="-1.00", severance="0.00"),
                _intake("manual-foreign", 2, provider="Exact Provider", account="A-001", total="100.00", contribution="60.00", severance="40.00"),
            ]
        )
        db.commit()

    def override():
        with sessions() as db:
            yield db

    app.dependency_overrides[get_db] = override
    client = TestClient(app)
    for client_id, intake_id in (
        (1, "manual-ok"),
        (1, "manual-warning"),
        (1, "manual-negative"),
        (2, "manual-foreign"),
    ):
        _accept_upstream(client, client_id, intake_id)
    try:
        yield client, sessions
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def _candidate(client: TestClient, account: str, client_id: int = 1) -> dict:
    response = client.get(f"/api/clients/{client_id}/m05/candidates")
    assert response.status_code == 200
    return next(row for row in response.json() if row["account_reference"] == account)


def _start(client: TestClient, account: str, *, confirm: bool = True) -> dict:
    candidate = _candidate(client, account)
    response = client.post(
        "/api/clients/1/m05/start",
        json={"candidate_id": candidate["candidate_id"], **({"confirm_currency_ils": True} if confirm else {})},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _external_sql(
    sessions: sessionmaker[Session],
    statement: str,
    parameters: dict | None = None,
    *,
    bypass_constraints: bool = False,
) -> None:
    """Simulate corruption outside the guarded application Session boundary."""
    with sessions() as db:
        engine = db.get_bind()
    with engine.connect() as connection:
        if bypass_constraints:
            connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
            connection.exec_driver_sql("PRAGMA ignore_check_constraints=ON")
            connection.commit()
        connection.exec_driver_sql(statement, parameters or {})
        connection.commit()


def test_candidate_start_reconcile_and_m06_gate(api) -> None:
    client, _ = api
    candidate = _candidate(client, "A-001")
    assert candidate["eligible"] is True
    assert candidate["authoritative_current"] is True
    started = _start(client, "A-001")
    assert started["state"] == "draft"
    assert started["currency"] == "ILS"
    assert started["currency_confirmed"] is True
    assert started["signed_discrepancy"] == "0.00"
    assert {row["component_kind"] for row in started["values"]} == {
        "total_balance", "contribution_component", "severance_component"
    }
    reconciled = client.post(
        f"/api/clients/1/m05/subjects/{started['subject_id']}/reconcile",
        json={"expected_current_revision_id": started["revision_id"]},
    )
    assert reconciled.status_code == 201, reconciled.text
    assert reconciled.json()["state"] == "reconciled"
    gate = client.get(
        f"/api/clients/1/m05/subjects/{started['subject_id']}/m06-eligibility"
    ).json()
    assert gate["eligible_for_m06"] is True
    assert "conversion" not in gate["meaning"]


def test_precedence_newer_ineligible_and_revalidation(api) -> None:
    client, sessions = api
    started = _start(client, "A-001")
    with sessions() as db:
        db.add(
            _intake(
                "manual-newer-ineligible",
                1,
                provider="Exact Provider",
                account="A-001",
                total="110.00",
                contribution="70.00",
                severance="40.00",
                statement_date=date(2026, 7, 2),
            )
        )
        db.commit()
    rows = client.get("/api/clients/1/m05/candidates").json()
    old = next(row for row in rows if row["intake_id"] == "manual-ok")
    assert old["authoritative_current"] is True
    assert "newer_ineligible_candidate_exists" in old["informational_warnings"]

    _accept_upstream(client, 1, "manual-newer-ineligible")
    rows = client.get("/api/clients/1/m05/candidates").json()
    old = next(row for row in rows if row["intake_id"] == "manual-ok")
    newer = next(
        row for row in rows if row["intake_id"] == "manual-newer-ineligible"
    )
    assert old["authoritative_current"] is False
    assert newer["authoritative_current"] is True
    gate = client.get(
        f"/api/clients/1/m05/subjects/{started['subject_id']}/m06-eligibility"
    ).json()
    assert "upstream_revalidation_required" in gate["exclusion_reasons"]
    revalidated = client.post(
        f"/api/clients/1/m05/subjects/{started['subject_id']}/revalidate",
        json={
            "expected_current_revision_id": started["revision_id"],
            "candidate_id": newer["candidate_id"],
            "reason_code": "new_authoritative_source",
            "explanation": "explicitly revalidated against the current source",
        },
    )
    assert revalidated.status_code == 201, revalidated.text
    assert revalidated.json()["action_type"] == "revalidate"
    assert revalidated.json()["state"] == "draft"
    assert revalidated.json()["currency_confirmed"] is False


def test_exact_precedence_tie_fails_closed(api, monkeypatch) -> None:
    client, sessions = api
    fixed = datetime.now(timezone.utc) + timedelta(seconds=1)
    monkeypatch.setattr(
        "app.models.m03_review.m03_server_timestamp", lambda: fixed
    )
    with sessions() as db:
        db.add_all(
            [
                _intake(
                    "tie-one",
                    1,
                    provider="Tie Provider",
                    account="Tie Account",
                    total="10.00",
                    contribution="6.00",
                    severance="4.00",
                ),
                _intake(
                    "tie-two",
                    1,
                    provider="Tie Provider",
                    account="Tie Account",
                    total="10.00",
                    contribution="6.00",
                    severance="4.00",
                ),
            ]
        )
        db.commit()
    _accept_upstream(client, 1, "tie-one")
    _accept_upstream(client, 1, "tie-two")
    rows = [
        row
        for row in client.get("/api/clients/1/m05/candidates").json()
        if row["intake_id"] in {"tie-one", "tie-two"}
    ]
    assert len(rows) == 2
    assert all(row["eligible"] is False for row in rows)
    assert all(row["exclusion_reason"] == "authoritative_candidate_tie" for row in rows)


def test_strict_intent_api_rejects_caller_forged_authority(api) -> None:
    client, _ = api
    candidate_id = _candidate(client, "A-001")["candidate_id"]
    response = client.post(
        "/api/clients/1/m05/start",
        json={
            "candidate_id": candidate_id,
            "confirm_currency_ils": True,
            "actor": "planner",
            "eligibility": True,
            "m04_revision_id": "forged",
        },
    )
    assert response.status_code == 422
    missing = client.post(
        "/api/clients/1/m05/start",
        json={"candidate_id": "M05-CAND-forged", "confirm_currency_ils": True},
    )
    assert missing.status_code == 404


def test_currency_confirmation_is_explicit_and_server_owned(api) -> None:
    client, _ = api
    started = _start(client, "A-001", confirm=False)
    rejected = client.post(
        f"/api/clients/1/m05/subjects/{started['subject_id']}/reconcile",
        json={"expected_current_revision_id": started["revision_id"]},
    )
    assert rejected.status_code == 409
    assert rejected.json()["detail"]["code"] == "currency_or_unit_invalid"
    accepted = client.post(
        f"/api/clients/1/m05/subjects/{started['subject_id']}/reconcile",
        json={
            "expected_current_revision_id": started["revision_id"],
            "confirm_currency_ils": True,
        },
    )
    assert accepted.status_code == 201
    evidence = accepted.json()["currency_confirmation_evidence"]
    assert evidence["actor"] == "system:m05-ledger-ui:M05 ledger workflow"
    assert evidence["candidate_id"] == started["candidate_id"]


def test_warning_exact_set_and_signed_values(api) -> None:
    client, _ = api
    started = _start(client, "A-002")
    warning_ids = {row["warning_id"] for row in started["warnings"]}
    assert warning_ids == {"reconciliation_difference_review_required"}
    assert started["signed_discrepancy"] == "1.00"
    reconcile = client.post(
        f"/api/clients/1/m05/subjects/{started['subject_id']}/reconcile",
        json={"expected_current_revision_id": started["revision_id"]},
    )
    assert reconcile.status_code == 409
    invalid = client.post(
        f"/api/clients/1/m05/subjects/{started['subject_id']}/review-warning",
        json={
            "expected_current_revision_id": started["revision_id"],
            "mandatory_warning_ids": [],
            "reason_code": "reviewed",
            "explanation": "reviewed exact discrepancy",
            "confirmed": True,
        },
    )
    assert invalid.status_code == 409
    assert invalid.json()["detail"]["code"] == "warning_disposition_invalid"
    reviewed = client.post(
        f"/api/clients/1/m05/subjects/{started['subject_id']}/review-warning",
        json={
            "expected_current_revision_id": started["revision_id"],
            "mandatory_warning_ids": ["reconciliation_difference_review_required"],
            "reason_code": "reviewed",
            "explanation": "reviewed exact discrepancy",
            "confirmed": True,
        },
    )
    assert reviewed.status_code == 201, reviewed.text
    assert reviewed.json()["state"] == "warning_reviewed"


def test_negative_and_canonical_zero_warning_contract(api) -> None:
    client, _ = api
    started = _start(client, "A-003")
    mandatory = {
        row["warning_id"] for row in started["warnings"]
        if row["classification"] == "mandatory"
    }
    assert mandatory == {"negative_value_review_required"}
    zero = next(row for row in started["values"] if row["original_label"] == "Severance")
    assert zero["source_value"] == "0.00"
    assert zero["source_state"] == "recorded_zero"


def test_adjustment_is_single_value_additive_and_strict(api) -> None:
    client, _ = api
    started = _start(client, "A-001")
    component = next(row for row in started["values"] if row["component_kind"] == "contribution_component")
    endpoint = f"/api/clients/1/m05/subjects/{started['subject_id']}/adjust"
    base = {
        "expected_current_revision_id": started["revision_id"],
        "evidence_identity": component["evidence_identity"],
        "reason_code": "planner_adjustment",
        "explanation": "explicit bounded adjustment",
        "confirmed": True,
    }
    for invalid in (0.5, True, "0.500", "5e-1", " 0.50", "1,00"):
        response = client.post(endpoint, json={**base, "new_effective_value": invalid})
        assert response.status_code == 422
    adjusted = client.post(endpoint, json={**base, "new_effective_value": "59.50"})
    assert adjusted.status_code == 201, adjusted.text
    body = adjusted.json()
    assert body["state"] == "draft"
    assert body["adjustment"]["previous_effective_value"] == "60.00"
    assert body["adjustment"]["new_effective_value"] == "59.50"
    assert body["signed_discrepancy"] == "0.50"
    source = next(row for row in body["values"] if row["evidence_identity"] == component["evidence_identity"])
    assert source["source_value"] == "60.00"
    assert source["effective_value"] == "59.50"


def test_lifecycle_stale_revision_terminal_and_history(api) -> None:
    client, _ = api
    started = _start(client, "A-001")
    blocked = client.post(
        f"/api/clients/1/m05/subjects/{started['subject_id']}/mark-blocked",
        json={
            "expected_current_revision_id": started["revision_id"],
            "reason_code": "manual_block",
            "explanation": "planner blocked the draft",
        },
    ).json()
    repeat = client.post(
        f"/api/clients/1/m05/subjects/{started['subject_id']}/mark-blocked",
        json={
            "expected_current_revision_id": blocked["revision_id"],
            "reason_code": "manual_block",
            "explanation": "repeat",
        },
    )
    assert repeat.status_code == 409
    stale = client.post(
        f"/api/clients/1/m05/subjects/{started['subject_id']}/adjust",
        json={
            "expected_current_revision_id": started["revision_id"],
            "evidence_identity": "total_balance",
            "new_effective_value": "100.00",
            "reason_code": "stale",
            "explanation": "stale action",
            "confirmed": True,
        },
    )
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "M05_STALE_CURRENT_REVISION"
    superseded = client.post(
        f"/api/clients/1/m05/subjects/{started['subject_id']}/supersede",
        json={
            "expected_current_revision_id": blocked["revision_id"],
            "reason_code": "superseded",
            "explanation": "terminal chain",
        },
    ).json()
    terminal = client.post(
        f"/api/clients/1/m05/subjects/{started['subject_id']}/adjust",
        json={
            "expected_current_revision_id": superseded["revision_id"],
            "evidence_identity": "total_balance",
            "new_effective_value": "100.00",
            "reason_code": "invalid",
            "explanation": "must fail",
            "confirmed": True,
        },
    )
    assert terminal.status_code == 409
    history = client.get(f"/api/clients/1/m05/subjects/{started['subject_id']}/history").json()
    assert [row["revision_sequence"] for row in history] == [1, 2, 3]


def test_foreign_and_missing_subjects_are_indistinguishable(api) -> None:
    client, _ = api
    started = _start(client, "A-001")
    foreign = client.get(f"/api/clients/2/m05/subjects/{started['subject_id']}")
    missing = client.get("/api/clients/2/m05/subjects/M05-S-missing")
    assert foreign.status_code == missing.status_code == 404
    assert foreign.json() == missing.json()


def test_append_only_instance_and_bulk_mutation_are_blocked(api) -> None:
    client, sessions = api
    started = _start(client, "A-001")
    with sessions() as db:
        revision = db.get(M05LedgerRevision, started["revision_id"])
        revision.state = "blocked"
        with pytest.raises(ValueError, match="immutable"):
            db.commit()
        db.rollback()
        with pytest.raises(ValueError, match="append-only"):
            db.execute(update(M05LedgerRevision).values(state="blocked"))
        db.rollback()
        value = db.scalar(select(M05LedgerValue).where(M05LedgerValue.revision_id == started["revision_id"]))
        with pytest.raises(ValueError, match="cannot be deleted"):
            db.delete(value)
            db.flush()
        db.rollback()
        subject = db.get(M05LedgerSubject, started["subject_id"])
        with pytest.raises(ValueError, match="cannot be deleted"):
            db.delete(subject)
            db.flush()
        db.rollback()
        with pytest.raises(ValueError, match="append-only"):
            db.execute(delete(M05LedgerValue))


def test_textual_core_dml_is_blocked_for_every_m05_table(api) -> None:
    client, sessions = api
    started = _start(client, "A-001")
    component = next(
        row for row in started["values"] if row["component_kind"] == "contribution_component"
    )
    adjusted = client.post(
        f"/api/clients/1/m05/subjects/{started['subject_id']}/adjust",
        json={
            "expected_current_revision_id": started["revision_id"],
            "evidence_identity": component["evidence_identity"],
            "new_effective_value": "59.00",
            "reason_code": "guard_fixture",
            "explanation": "create adjustment evidence for guard coverage",
            "confirmed": True,
        },
    ).json()
    mutations = {
        "m05_ledger_subjects": "provider_name = 'mutated'",
        "m05_candidate_links": "statement_date = '2000-01-01'",
        "m05_ledger_revisions": "state = 'blocked'",
        "m05_ledger_values": "effective_value = 1.00",
        "m05_adjustment_evidence": "reason_code = 'mutated'",
    }
    with sessions() as db:
        for table, assignment in mutations.items():
            statements = [
                f"update {table} set {assignment}",
                f"UPDATE {table.upper()} SET {assignment.upper()}",
                f"UpDaTe {table} SeT {assignment}",
                f'DELETE FROM "{table}"',
                f'UPDATE "{table}" SET {assignment}',
                f'UPDATE "main"."{table}" SET {assignment}',
                f"UPDATE\n{table}\nSET {assignment}",
                f"-- protected mutation\nUPDATE {table} SET {assignment}",
                f"WITH bounded AS (SELECT 1) UPDATE {table} SET {assignment}",
            ]
            for statement in statements:
                with pytest.raises(ValueError, match="M05 append-only"):
                    db.execute(text(statement))
                db.rollback()
        with pytest.raises(ValueError, match="M05 append-only"):
            db.execute(
                text(
                    "UPDATE m05_ledger_revisions SET reason_code = :reason "
                    "WHERE revision_id = :revision_id"
                ),
                {"reason": "parameterized", "revision_id": adjusted["revision_id"]},
            )
        db.rollback()

        assert db.execute(text("SELECT COUNT(*) FROM m05_ledger_revisions")).scalar_one() == 2
        assert db.execute(
            text("SELECT 'm05_ledger_revisions UPDATE DELETE' AS harmless")
        ).scalar_one() == "m05_ledger_revisions UPDATE DELETE"
        db.execute(
            text("UPDATE clients SET display_name = :name WHERE client_id = 1"),
            {"name": "unrelated allowed"},
        )
        assert db.get(Client, 1).display_name == "unrelated allowed"
        db.rollback()

        assert db.get(M05LedgerSubject, started["subject_id"]).provider_name == "Exact Provider"
        assert db.get(M05LedgerRevision, adjusted["revision_id"]).state == "draft"
        assert db.scalar(
            select(M05CandidateLink).where(
                M05CandidateLink.candidate_id == adjusted["candidate_id"]
            )
        ).statement_date == date(2026, 7, 1)
        assert db.scalar(
            select(M05LedgerValue).where(
                M05LedgerValue.revision_id == adjusted["revision_id"],
                M05LedgerValue.evidence_identity == component["evidence_identity"],
            )
        ).effective_value == Decimal("59.00")
        assert db.scalar(
            select(M05AdjustmentEvidence).where(
                M05AdjustmentEvidence.revision_id == adjusted["revision_id"]
            )
        ).reason_code == "guard_fixture"


def test_database_corruption_fails_closed_without_history_rewrite(api) -> None:
    client, sessions = api
    started = _start(client, "A-001")
    _external_sql(
        sessions,
        "UPDATE m05_ledger_values SET effective_value = 99.99 "
        "WHERE revision_id = :revision_id AND component_kind = 'contribution_component'",
        {"revision_id": started["revision_id"]},
    )

    detail = client.get(f"/api/clients/1/m05/subjects/{started['subject_id']}")
    assert detail.status_code == 409
    assert detail.json()["detail"]["code"] == "ledger_chain_inconsistent"
    gate = client.get(
        f"/api/clients/1/m05/subjects/{started['subject_id']}/m06-eligibility"
    )
    assert gate.status_code == 200
    assert gate.json()["eligible_for_m06"] is False
    assert gate.json()["exclusion_reasons"] == ["ledger_chain_inconsistent"]


@pytest.mark.parametrize(
    "corruption",
    [
        "candidate_statement_date",
        "candidate_m03_decided_at",
        "candidate_intake_id",
        "candidate_m03_revision_id",
        "candidate_m04_revision_id",
        "candidate_target_kind",
        "subject_provider_digest",
        "subject_account_digest",
        "candidate_source_snapshot_digest",
        "candidate_identity",
        "candidate_subject_linkage",
        "candidate_client_linkage",
        "revision_predecessor",
        "revision_sequence",
        "value_row",
        "warning_snapshot",
        "adjustment_evidence",
        "deleted_value_row",
        "broken_chain",
    ],
)
def test_complete_candidate_and_chain_corruption_fails_closed(api, corruption) -> None:
    client, sessions = api
    started = _start(client, "A-001")
    current = started
    if corruption == "adjustment_evidence":
        component = next(
            row
            for row in started["values"]
            if row["component_kind"] == "contribution_component"
        )
        current = client.post(
            f"/api/clients/1/m05/subjects/{started['subject_id']}/adjust",
            json={
                "expected_current_revision_id": started["revision_id"],
                "evidence_identity": component["evidence_identity"],
                "new_effective_value": "59.00",
                "reason_code": "corruption_fixture",
                "explanation": "create immutable adjustment evidence",
                "confirmed": True,
            },
        ).json()
    candidate_id = started["candidate_id"]
    subject_id = started["subject_id"]
    revision_id = current["revision_id"]
    statements = {
        "candidate_statement_date": (
            "UPDATE m05_candidate_links SET statement_date='2000-01-01' WHERE candidate_id=:id",
            candidate_id,
        ),
        "candidate_m03_decided_at": (
            "UPDATE m05_candidate_links SET m03_decided_at='2000-01-01 00:00:00' WHERE candidate_id=:id",
            candidate_id,
        ),
        "candidate_intake_id": (
            "UPDATE m05_candidate_links SET intake_id='corrupt-intake' WHERE candidate_id=:id",
            candidate_id,
        ),
        "candidate_m03_revision_id": (
            "UPDATE m05_candidate_links SET m03_revision_id='M03-R-corrupt' WHERE candidate_id=:id",
            candidate_id,
        ),
        "candidate_m04_revision_id": (
            "UPDATE m05_candidate_links SET m04_revision_id='M04-R-corrupt' WHERE candidate_id=:id",
            candidate_id,
        ),
        "candidate_target_kind": (
            "UPDATE m05_candidate_links SET target_kind='source_evidence_review' WHERE candidate_id=:id",
            candidate_id,
        ),
        "subject_provider_digest": (
            "UPDATE m05_ledger_subjects SET provider_identity_digest='" + "0" * 64 + "' WHERE subject_id=:id",
            subject_id,
        ),
        "subject_account_digest": (
            "UPDATE m05_ledger_subjects SET account_identity_digest='" + "1" * 64 + "' WHERE subject_id=:id",
            subject_id,
        ),
        "candidate_source_snapshot_digest": (
            "UPDATE m05_candidate_links SET source_snapshot_digest='" + "2" * 64 + "' WHERE candidate_id=:id",
            candidate_id,
        ),
        "candidate_identity": (
            "UPDATE m05_candidate_links SET candidate_id='M05-CAND-" + "f" * 40 + "' WHERE candidate_id=:id",
            candidate_id,
        ),
        "candidate_subject_linkage": (
            "UPDATE m05_candidate_links SET subject_id='M05-S-corrupt' WHERE candidate_id=:id",
            candidate_id,
        ),
        "candidate_client_linkage": (
            "UPDATE m05_candidate_links SET client_id=2 WHERE candidate_id=:id",
            candidate_id,
        ),
        "revision_predecessor": (
            "UPDATE m05_ledger_revisions SET predecessor_revision_id='M05-R-corrupt', revision_sequence=2 WHERE revision_id=:id",
            revision_id,
        ),
        "revision_sequence": (
            "UPDATE m05_ledger_revisions SET revision_sequence=99 WHERE revision_id=:id",
            revision_id,
        ),
        "value_row": (
            "UPDATE m05_ledger_values SET effective_value=99.99 WHERE revision_id=:id AND component_kind='contribution_component'",
            revision_id,
        ),
        "warning_snapshot": (
            "UPDATE m05_ledger_revisions SET warnings='[{\"warning_id\":\"negative_value_review_required\",\"classification\":\"mandatory\"}]' WHERE revision_id=:id",
            revision_id,
        ),
        "adjustment_evidence": (
            "UPDATE m05_adjustment_evidence SET reason_code='corrupt' WHERE revision_id=:id",
            revision_id,
        ),
        "deleted_value_row": (
            "DELETE FROM m05_ledger_values WHERE value_id=(SELECT value_id FROM m05_ledger_values WHERE revision_id=:id LIMIT 1)",
            revision_id,
        ),
        "broken_chain": (
            "DELETE FROM m05_ledger_revisions WHERE subject_id=:id",
            subject_id,
        ),
    }
    statement, identifier = statements[corruption]
    with sessions() as db:
        before = db.scalar(
            select(func.count()).select_from(M05LedgerRevision).where(
                M05LedgerRevision.subject_id == subject_id
            )
        )
    _external_sql(
        sessions,
        statement,
        {"id": identifier},
        bypass_constraints=True,
    )

    for suffix in ("", "/history", "/provenance", "/warnings"):
        response = client.get(f"/api/clients/1/m05/subjects/{subject_id}{suffix}")
        assert response.status_code == 409
        assert response.json()["detail"] == {
            "code": "ledger_chain_inconsistent",
            "message": "Ledger chain is inconsistent",
        }
    gate = client.get(
        f"/api/clients/1/m05/subjects/{subject_id}/m06-eligibility"
    )
    assert gate.status_code == 200
    assert gate.json()["eligible_for_m06"] is False
    assert gate.json()["exclusion_reasons"] == ["ledger_chain_inconsistent"]
    mutation = client.post(
        f"/api/clients/1/m05/subjects/{subject_id}/reconcile",
        json={"expected_current_revision_id": revision_id},
    )
    assert mutation.status_code == 409
    assert mutation.json()["detail"]["code"] == "ledger_chain_inconsistent"
    with sessions() as db:
        after = db.scalar(
            select(func.count()).select_from(M05LedgerRevision).where(
                M05LedgerRevision.subject_id == subject_id
            )
        )
    assert after == (0 if corruption == "broken_chain" else before)


def test_duplicate_leaf_is_rejected_by_database_constraint(api) -> None:
    client, sessions = api
    started = _start(client, "A-001")
    with sessions() as db:
        row = db.get(M05LedgerRevision, started["revision_id"])
        duplicate = M05LedgerRevision(
            **{
                column.name: getattr(row, column.name)
                for column in M05LedgerRevision.__table__.columns
                if column.name != "revision_id"
            }
        )
        duplicate.revision_id = "M05-R-" + "f" * 32
        duplicate.predecessor_revision_id = row.revision_id
        duplicate.revision_sequence = 2
        duplicate.action_type = "adjust"
        duplicate.state = "draft"
        duplicate.evidence_digest = "0" * 64
        from app.models.m05_ledger import authorize_m05_insert

        authorize_m05_insert(duplicate)
        db.add(duplicate)
        db.flush()
        second = M05LedgerRevision(
            **{
                column.name: getattr(duplicate, column.name)
                for column in M05LedgerRevision.__table__.columns
                if column.name != "revision_id"
            }
        )
        second.revision_id = "M05-R-" + "e" * 32
        second.evidence_digest = "1" * 64
        authorize_m05_insert(second)
        db.add(second)
        with pytest.raises(Exception):
            db.flush()


def test_archived_case_is_read_only_and_m06_ineligible(api) -> None:
    client, sessions = api
    started = _start(client, "A-001")
    with sessions() as db:
        case = db.get(Client, 1)
        case.status = "archived"
        db.commit()

    detail = client.get(f"/api/clients/1/m05/subjects/{started['subject_id']}")
    assert detail.status_code == 200
    assert detail.json()["eligibility"]["eligible_for_m06"] is False
    assert "archived_case" in detail.json()["eligibility"]["exclusion_reasons"]
    mutation = client.post(
        f"/api/clients/1/m05/subjects/{started['subject_id']}/reconcile",
        json={"expected_current_revision_id": started["revision_id"]},
    )
    assert mutation.status_code == 409
    assert mutation.json()["detail"]["code"] == "archived_case"


def test_complete_eligibility_vocabulary_has_deterministic_order(api) -> None:
    required = [
        "archived_case",
        "ledger_chain_inconsistent",
        "no_authoritative_candidate",
        "authoritative_candidate_tie",
        "upstream_source_ineligible",
        "m03_ineligible",
        "m04_ineligible",
        "upstream_revalidation_required",
        "ledger_draft",
        "ledger_blocked",
        "ledger_superseded",
        "required_value_missing",
        "currency_or_unit_invalid",
        "component_mapping_invalid",
        "component_set_incomplete",
        "reconciliation_unresolved",
        "negative_value_review_required",
        "warning_disposition_invalid",
        "warning_not_reviewed",
        "provenance_invalid",
        "statement_date_invalid",
    ]
    assert list(ELIGIBILITY_REASON_ORDER) == required
    assert _ordered_eligibility_reasons(list(reversed(required)) + required) == required

    client, sessions = api
    unconfirmed = _start(client, "A-001", confirm=False)
    gate = client.get(
        f"/api/clients/1/m05/subjects/{unconfirmed['subject_id']}/m06-eligibility"
    ).json()
    assert gate["exclusion_reasons"] == ["ledger_draft", "currency_or_unit_invalid"]
    assert gate["informational_warnings"] == []

    with sessions() as db:
        leaf = db.get(M05LedgerRevision, unconfirmed["revision_id"])
        intake = db.get(M02IntakeRecord, "manual-ok")
        assert _upstream_eligibility_reasons([], leaf) == (
            ["no_authoritative_candidate"],
            [],
        )
        for reason in (
            "authoritative_candidate_tie",
            "upstream_source_ineligible",
            "m03_ineligible",
            "m04_ineligible",
            "required_value_missing",
            "component_mapping_invalid",
            "component_set_incomplete",
            "statement_date_invalid",
        ):
            row = CandidateEvaluation(
                candidate_id=leaf.candidate_id,
                intake=intake,
                context=None,
                exclusion_reason=reason,
            )
            assert _upstream_eligibility_reasons([row], leaf)[0] == [reason]
        stale_authority = CandidateEvaluation(
            candidate_id=leaf.candidate_id,
            intake=intake,
            context=object(),
            exclusion_reason="no_authoritative_candidate",
            authoritative=False,
        )
        assert _upstream_eligibility_reasons([stale_authority], leaf)[0] == [
            "upstream_revalidation_required"
        ]

        with db.no_autoflush:
            leaf.source_total_value = None
            assert "required_value_missing" in _leaf_integrity_reasons(db, leaf)[0]
            db.rollback()

    # Each remaining leaf-level exclusion is produced independently without
    # persisting the synthetic invalid state.
    mutations = {
        "currency_or_unit_invalid": lambda leaf, values: setattr(leaf, "currency_confirmed", False),
        "component_mapping_invalid": lambda leaf, values: setattr(values[1], "evidence_identity", values[0].evidence_identity),
        "component_set_incomplete": lambda leaf, values: [setattr(value, "included_in_reconciliation", False) for value in values],
        "reconciliation_unresolved": lambda leaf, values: setattr(leaf, "tolerance_satisfied", False),
        "negative_value_review_required": lambda leaf, values: setattr(leaf, "warnings", [{"warning_id": "negative_value_review_required", "classification": "mandatory"}]),
        "warning_disposition_invalid": lambda leaf, values: setattr(leaf, "warning_dispositions", [{"warning_id": "unknown_warning"}]),
        "warning_not_reviewed": lambda leaf, values: setattr(leaf, "warnings", [{"warning_id": "reconciliation_difference_review_required", "classification": "mandatory"}]),
        "provenance_invalid": lambda leaf, values: setattr(leaf, "provenance", {**leaf.provenance, "client_id": 999}),
        "statement_date_invalid": lambda leaf, values: setattr(leaf, "statement_date", leaf.evaluation_date + timedelta(days=1)),
    }
    for expected, mutate in mutations.items():
        with sessions() as db:
            leaf = db.get(M05LedgerRevision, unconfirmed["revision_id"])
            values = list(
                db.scalars(
                    select(M05LedgerValue).where(
                        M05LedgerValue.revision_id == leaf.revision_id
                    )
                ).all()
            )
            with db.no_autoflush:
                mutate(leaf, values)
                reasons, informational = _leaf_integrity_reasons(db, leaf)
                assert expected in reasons
                assert informational == []
            db.rollback()


def test_concurrent_start_has_one_winner_and_clean_retry(api) -> None:
    client, _ = api
    candidate_id = _candidate(client, "A-001")["candidate_id"]

    def start() -> int:
        return client.post(
            "/api/clients/1/m05/start",
            json={"candidate_id": candidate_id, "confirm_currency_ils": True},
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(lambda _: start(), range(2)))
    assert sorted(statuses) == [201, 409]
    assert start() == 409
    subjects = client.get("/api/clients/1/m05/subjects").json()
    assert len(subjects) == 1
    assert len(client.get(f"/api/clients/1/m05/subjects/{subjects[0]['subject_id']}/history").json()) == 1


def test_concurrent_same_leaf_successor_has_one_winner(api) -> None:
    client, _ = api
    started = _start(client, "A-001")
    endpoint = f"/api/clients/1/m05/subjects/{started['subject_id']}/adjust"
    values = [
        row for row in started["values"] if row["component_kind"] != "total_balance"
    ]

    def adjust(index: int) -> int:
        return client.post(
            endpoint,
            json={
                "expected_current_revision_id": started["revision_id"],
                "evidence_identity": values[index]["evidence_identity"],
                "new_effective_value": "59.00" if index == 0 else "39.00",
                "reason_code": "concurrent_adjustment",
                "explanation": "one immutable successor may win",
                "confirmed": True,
            },
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(adjust, range(2)))
    assert sorted(statuses) == [201, 409]
    history = client.get(
        f"/api/clients/1/m05/subjects/{started['subject_id']}/history"
    ).json()
    assert [row["revision_sequence"] for row in history] == [1, 2]
    assert history[1]["predecessor_revision_id"] == started["revision_id"]


@pytest.mark.parametrize(
    ("statement", "evaluation", "expected"),
    [
        (date(2025, 1, 31), date(2026, 1, 31), False),
        (date(2025, 1, 30), date(2026, 1, 31), True),
        (date(2024, 2, 29), date(2025, 2, 28), False),
        (date(2024, 2, 28), date(2025, 2, 28), False),
        (date(2024, 2, 27), date(2025, 2, 28), True),
        (date(2025, 3, 31), date(2026, 3, 30), False),
        (date(2025, 3, 29), date(2026, 3, 30), True),
    ],
)
def test_exact_calendar_stale_examples(statement, evaluation, expected) -> None:
    assert is_stale(statement, evaluation) is expected


def test_strict_money_helpers() -> None:
    assert parse_component_money("0.50") == Decimal("0.50")
    assert parse_component_money("-0.00") == Decimal("0.00")
    assert parse_authored_money("-0.01") == Decimal("-0.01")
    for invalid in ("0.500", "0.499", "5e-1", " 0.50", "1,00", True, [], {}):
        with pytest.raises(Exception):
            parse_component_money(invalid)


@pytest.mark.parametrize(
    ("signed_difference", "satisfied"),
    [
        ("0.00", True),
        ("0.01", True),
        ("0.49", True),
        ("0.50", True),
        ("-0.50", True),
        ("0.51", False),
        ("-0.51", False),
    ],
)
def test_exact_reconciliation_tolerance_boundaries(
    signed_difference: str, satisfied: bool
) -> None:
    difference = Decimal(signed_difference)
    values = [
        {
            "evidence_identity": "total_balance",
            "component_kind": "total_balance",
            "effective_value": Decimal("100.00") + difference,
            "included_in_reconciliation": False,
            "exclusion_reason": "reconciliation_total",
        },
        {
            "evidence_identity": "component:0",
            "component_kind": "contribution_component",
            "effective_value": Decimal("100.00"),
            "included_in_reconciliation": True,
            "exclusion_reason": None,
        },
    ]
    actual, absolute, within_tolerance, included, excluded = _reconcile(values)
    assert actual == difference
    assert absolute == abs(difference)
    assert within_tolerance is satisfied
    assert included == [
        {"evidence_identity": "component:0", "effective_value": "100.00"}
    ]
    assert excluded == []
