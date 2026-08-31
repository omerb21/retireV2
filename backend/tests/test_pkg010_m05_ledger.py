from __future__ import annotations

from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import json
from pathlib import Path
import sqlite3
from threading import Barrier, Event, Lock, get_ident
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, event, func, select, text, update
from sqlalchemy.exc import IntegrityError
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
    _sql_tokens,
    authorize_m05_insert,
)
from app.services.m05_ledger_service import (
    ELIGIBILITY_REASON_ORDER,
    CandidateEvaluation,
    M05LedgerError,
    _canonical_numeric,
    _candidate_context,
    _identity_digest,
    _leaf_integrity_reasons,
    _ordered_eligibility_reasons,
    _reconcile,
    _revision_digest,
    _transition,
    _upstream_eligibility_reasons,
    _values,
    _warnings,
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
    assert accepted.status_code == 201, accepted.text
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


def test_material_m02_change_removes_m05_candidate_authority_client_scoped(api) -> None:
    client, _sessions = api
    before = _candidate(client, "A-001")
    assert before["eligible"] is True
    assert before["authoritative_current"] is True

    client.post(
        "/api/clients/1/m02/intakes/manual-ok/lifecycle",
        json={"target_status": "metadata_review"},
    ).raise_for_status()
    client.put(
        "/api/clients/1/m02/intakes/manual-ok",
        json={
            "declared_total_balance_amount": "125.00",
            "declared_component_values": [
                {"label": "Contributions", "value": "75.00"},
                {"label": "Severance", "value": "50.00"},
            ],
        },
    ).raise_for_status()
    client.post(
        "/api/clients/1/m02/intakes/manual-ok/lifecycle",
        json={"target_status": "accepted_for_review"},
    ).raise_for_status()

    changed = next(
        row
        for row in client.get("/api/clients/1/m05/candidates").json()
        if row["intake_id"] == "manual-ok"
    )
    assert changed["eligible"] is False
    assert changed["authoritative_current"] is False
    assert changed["exclusion_reason"] == "m03_ineligible"
    foreign = _candidate(client, "A-001", client_id=2)
    assert foreign["eligible"] is True
    assert foreign["authoritative_current"] is True


def _external_sql(
    sessions: sessionmaker[Session],
    statement: str,
    parameters: dict | None = None,
    *,
    bypass_constraints: bool = False,
) -> None:
    """Simulate corruption outside the guarded SQLAlchemy application boundary."""
    with sessions() as db:
        engine = db.get_bind()
        database_path = engine.url.database
    assert database_path is not None
    with sqlite3.connect(database_path) as connection:
        if bypass_constraints:
            connection.execute("PRAGMA foreign_keys=OFF")
            connection.execute("PRAGMA ignore_check_constraints=ON")
        connection.execute(statement, parameters or {})


def _resign_revision(
    sessions: sessionmaker[Session], revision_id: str
) -> None:
    """Sign a deliberately constructed persisted read-state test fixture."""
    with sessions() as db:
        revision = db.get(M05LedgerRevision, revision_id)
        assert revision is not None
        digest = _revision_digest(revision, _values(db, revision_id))
    _external_sql(
        sessions,
        "UPDATE m05_ledger_revisions SET evidence_digest = :digest "
        "WHERE revision_id = :revision_id",
        {"digest": digest, "revision_id": revision_id},
    )


def _overlap_at_insert(
    sessions: sessionmaker[Session],
    table: str,
    operations,
    *,
    ordered_winner_index: int | None = None,
    ordered_winner_marker: str | None = None,
):
    """Release two independent SQLAlchemy connections at the same pre-write point."""
    engine = sessions.kw["bind"]
    barrier = Barrier(2)
    lock = Lock()
    arrivals: list[tuple[int, int]] = []
    ordered_winner_finished = Event()
    prefix = f"insert into {table}"

    def synchronize(connection, _cursor, statement, parameters, _context, _many):
        normalized = " ".join(statement.lower().split())
        if not normalized.startswith(prefix):
            return
        worker = get_ident()
        should_wait = False
        with lock:
            if worker not in {item[0] for item in arrivals} and len(arrivals) < 2:
                arrivals.append((worker, id(connection)))
                should_wait = True
        if should_wait:
            barrier.wait(timeout=20)
            if (
                ordered_winner_marker is not None
                and ordered_winner_marker not in repr(parameters)
            ):
                assert ordered_winner_finished.wait(timeout=20)

    def run(index, operation):
        try:
            return operation()
        finally:
            if index == ordered_winner_index:
                ordered_winner_finished.set()

    event.listen(engine, "before_cursor_execute", synchronize)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(run, index, operation)
                for index, operation in enumerate(operations)
            ]
            responses = [future.result(timeout=30) for future in futures]
    finally:
        event.remove(engine, "before_cursor_execute", synchronize)
    assert len(arrivals) == 2
    assert len({worker for worker, _ in arrivals}) == 2
    assert len({connection for _, connection in arrivals}) == 2
    return responses


def _assert_stable_race_outcome(responses) -> tuple[object, object]:
    winner = next(response for response in responses if response.status_code == 201)
    loser = next(response for response in responses if response.status_code == 409)
    assert sorted(response.status_code for response in responses) == [201, 409]
    assert loser.json()["detail"] == {
        "code": "M05_CONCURRENT_MODIFICATION",
        "message": "Ledger changed before this action",
    }
    return winner, loser


def _assert_no_race_residue(
    sessions: sessionmaker[Session], subject_id: str, expected_revisions: int
) -> None:
    with sessions() as db:
        revisions = list(
            db.scalars(
                select(M05LedgerRevision)
                .where(M05LedgerRevision.subject_id == subject_id)
                .order_by(M05LedgerRevision.revision_sequence)
            ).all()
        )
        assert len(revisions) == expected_revisions
        assert [row.revision_sequence for row in revisions] == list(
            range(1, expected_revisions + 1)
        )
        assert len({row.revision_sequence for row in revisions}) == len(revisions)
        predecessor_ids = [
            row.predecessor_revision_id
            for row in revisions
            if row.predecessor_revision_id is not None
        ]
        assert len(predecessor_ids) == len(set(predecessor_ids))
        candidate_links = list(
            db.scalars(
                select(M05CandidateLink).where(M05CandidateLink.subject_id == subject_id)
            ).all()
        )
        assert len({row.candidate_id for row in candidate_links}) == len(candidate_links)
        values = list(
            db.scalars(
                select(M05LedgerValue).where(M05LedgerValue.subject_id == subject_id)
            ).all()
        )
        assert len({(row.revision_id, row.evidence_identity) for row in values}) == len(values)
        assert {row.revision_id for row in values} == {
            row.revision_id for row in revisions
        }
        adjustments = list(
            db.scalars(
                select(M05AdjustmentEvidence).where(
                    M05AdjustmentEvidence.subject_id == subject_id
                )
            ).all()
        )
        assert len(adjustments) == sum(
            row.action_type == "adjust" for row in revisions
        )
        for row in revisions:
            assert isinstance(row.warnings, list)
            assert isinstance(row.warning_dispositions, list)


def _persisted_constraint_race(
    sessions: sessionmaker[Session], table: str, row_factories,
    *, ordered_winner_index: int | None = None,
    ordered_winner_marker: str | None = None,
) -> tuple[list[dict[str, str | None]], list[tuple[int, int]]]:
    """Race two real flushes and normalize the dialect-specific integrity loser."""
    engine = sessions.kw["bind"]
    barrier = Barrier(2)
    lock = Lock()
    arrivals: list[tuple[int, int]] = []
    ordered_winner_finished = Event()
    prefix = f"insert into {table}"

    def synchronize(connection, _cursor, statement, parameters, _context, _many):
        if not " ".join(statement.lower().split()).startswith(prefix):
            return
        worker = get_ident()
        with lock:
            if worker in {item[0] for item in arrivals} or len(arrivals) >= 2:
                return
            arrivals.append((worker, id(connection)))
        barrier.wait(timeout=20)
        if (
            ordered_winner_marker is not None
            and ordered_winner_marker not in repr(parameters)
        ):
            assert ordered_winner_finished.wait(timeout=20)

    def persist(index, factory):
        with sessions() as db:
            produced = factory()
            rows = list(produced) if isinstance(produced, (list, tuple)) else [produced]
            for row in rows:
                authorize_m05_insert(row)
            db.add_all(rows)
            try:
                db.flush()
                db.commit()
                return {"outcome": "winner", "message": None}
            except IntegrityError as error:
                db.rollback()
                return {
                    "outcome": "M05_CONCURRENT_MODIFICATION",
                    "message": str(error.orig).lower(),
                }
            finally:
                if index == ordered_winner_index:
                    ordered_winner_finished.set()

    event.listen(engine, "before_cursor_execute", synchronize)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(persist, index, factory)
                for index, factory in enumerate(row_factories)
            ]
            outcomes = [future.result(timeout=30) for future in futures]
    finally:
        event.remove(engine, "before_cursor_execute", synchronize)
    assert len(arrivals) == 2
    assert len({worker for worker, _ in arrivals}) == 2
    assert len({connection for _, connection in arrivals}) == 2
    assert sorted(item["outcome"] for item in outcomes) == [
        "M05_CONCURRENT_MODIFICATION",
        "winner",
    ]
    return outcomes, arrivals


def _isolated_subject(
    sessions: sessionmaker[Session], suffix: str
) -> M05LedgerSubject:
    row = M05LedgerSubject(
        subject_id=f"M05-S-ISOLATED-{suffix}",
        client_id=1,
        provider_name=f"Isolated Provider {suffix}",
        account_reference=f"ISOLATED-{suffix}",
        provider_identity_digest=_identity_digest(f"Isolated Provider {suffix}"),
        account_identity_digest=_identity_digest(f"ISOLATED-{suffix}"),
    )
    with sessions() as db:
        authorize_m05_insert(row)
        db.add(row)
        db.commit()
    return row


def _candidate_row(context, subject_id: str, candidate_id: str) -> M05CandidateLink:
    return M05CandidateLink(
        candidate_id=candidate_id,
        subject_id=subject_id,
        client_id=1,
        intake_id=context.intake.intake_id,
        target_kind="manual_record_review",
        m03_revision_id=context.m03_revision_id,
        m04_revision_id=context.m04_revision_id,
        statement_date=context.statement_date,
        m03_decided_at=context.m03_decided_at,
        source_snapshot_digest=context.source_snapshot_digest,
    )


def _persist_isolated_candidate(
    sessions: sessionmaker[Session], subject_id: str, suffix: str
) -> tuple[M05CandidateLink, object]:
    with sessions() as db:
        context = _candidate_context(
            db, db.get(Client, 1), db.get(M02IntakeRecord, "manual-warning")
        )
        row = _candidate_row(context, subject_id, f"M05-C-ISOLATED-{suffix}")
        authorize_m05_insert(row)
        db.add(row)
        db.commit()
        return row, context


def _revision_row(
    template: M05LedgerRevision,
    *,
    revision_id: str,
    subject_id: str,
    candidate_id: str,
    sequence: int,
    predecessor_id: str | None,
) -> M05LedgerRevision:
    values = {
        column.name: getattr(template, column.name)
        for column in M05LedgerRevision.__table__.columns
        if column.name
        not in {
            "revision_id", "subject_id", "candidate_id",
            "revision_sequence", "predecessor_revision_id", "evidence_digest",
        }
    }
    values.update(
        revision_id=revision_id,
        subject_id=subject_id,
        candidate_id=candidate_id,
        revision_sequence=sequence,
        predecessor_revision_id=predecessor_id,
        evidence_digest=(revision_id[-1].lower() if revision_id[-1].lower() in "abcdef0123456789" else "a") * 64,
    )
    return M05LedgerRevision(**values)


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
    fixed = datetime.now(timezone.utc) + timedelta(minutes=1)
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
    primary_keys = {
        "m05_ledger_subjects": "subject_id",
        "m05_candidate_links": "candidate_link_id",
        "m05_ledger_revisions": "revision_id",
        "m05_ledger_values": "value_id",
        "m05_adjustment_evidence": "adjustment_id",
    }

    def snapshot(db: Session, table: str) -> list[tuple]:
        return list(
            db.execute(
                text(f'SELECT * FROM "{table}" ORDER BY "{primary_keys[table]}"')
            ).all()
        )

    with sessions() as db:
        db.execute(
            text(
                'CREATE TABLE pkg010_unrelated '
                '(id INTEGER PRIMARY KEY, "update" TEXT, "delete" TEXT, "from" TEXT)'
            )
        )
        db.execute(
            text(
                'INSERT INTO pkg010_unrelated (id, "update", "delete", "from") '
                "VALUES (1, 'u', 'd', 'f'), (2, 'u2', 'd2', 'f2')"
            )
        )
        db.commit()
        for table, assignment in mutations.items():
            before = snapshot(db, table)
            statements = [
                f"update {table} set {assignment}",
                f"UPDATE {table.upper()} SET {assignment.upper()}",
                f"UpDaTe {table} SeT {assignment}",
                f'DELETE FROM "{table}"',
                f'UPDATE "{table}" SET {assignment}',
                f'UPDATE "main"."{table}" SET {assignment}',
                f'UPDATE app.{table} SET {assignment}',
                f'UPDATE OR IGNORE {table} SET {assignment}',
                f'UPDATE OR ABORT {table} SET {assignment}',
                f'UPDATE ONLY {table} AS guarded SET {assignment}',
                f'DELETE FROM ONLY {table} AS guarded',
                f"UPDATE\n{table}\nSET {assignment}",
                f"-- protected mutation\nUPDATE {table} SET {assignment}",
                f"UPDATE/* bounded */OR/* dialect */IGNORE/* target */{table} SET {assignment}",
                f"WITH bounded AS (SELECT 1) UPDATE {table} SET {assignment}",
                f"WITH bounded AS (SELECT 1) DELETE FROM {table}",
                f"SELECT 1; UPDATE {table} SET {assignment}",
                f"UPDATE\n{table}\nSET {assignment} WHERE 1 = :enabled",
            ]
            for statement in statements:
                with pytest.raises(ValueError, match="M05 append-only"):
                    db.execute(text(statement), {"enabled": 1})
                db.rollback()
                assert snapshot(db, table) == before
                assert db.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar_one() == len(before)
            for conflict_action in ("ROLLBACK", "FAIL", "REPLACE"):
                with pytest.raises(ValueError, match="M05 append-only"):
                    db.execute(
                        text(f"UPDATE OR {conflict_action} {table} SET {assignment}")
                    )
                db.rollback()
                assert snapshot(db, table) == before
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
        legitimate_reads = [
            "SELECT 'x' AS \"update\" FROM m05_ledger_subjects",
            'SELECT subject_id AS "delete" FROM m05_ledger_subjects',
            'SELECT subject_id AS "from" FROM m05_ledger_subjects',
            'SELECT subject_id AS "only" FROM m05_ledger_subjects',
            'SELECT "update", "delete", "from" FROM pkg010_unrelated',
            'SELECT "update" FROM pkg010_unrelated',
            'SELECT "update".subject_id FROM m05_ledger_subjects AS "update"',
            'SELECT "from".subject_id FROM "main"."m05_ledger_subjects" AS "from"',
            'WITH "update" AS (SELECT subject_id FROM m05_ledger_subjects) '
            'SELECT subject_id FROM "update"',
            'SELECT subject_id AS "m05_ledger_subjects" FROM m05_ledger_subjects',
        ]
        for statement in legitimate_reads:
            assert db.execute(text(statement)).all()
        assert db.execute(
            text("SELECT 'm05_ledger_revisions UPDATE DELETE' AS harmless")
        ).scalar_one() == "m05_ledger_revisions UPDATE DELETE"
        assert db.execute(
            text("SELECT 1 /* UPDATE m05_ledger_subjects SET provider_name = 'x' */")
        ).scalar_one() == 1
        db.execute(
            text(
                "WITH source AS (SELECT subject_id FROM m05_ledger_subjects) "
                'UPDATE pkg010_unrelated SET "update" = :value WHERE id = 1'
            ),
            {"value": "m05_ledger_revisions"},
        )
        db.execute(text("DELETE FROM pkg010_unrelated WHERE id = 2"))
        assert db.execute(
            text('SELECT "update" FROM pkg010_unrelated WHERE id = 1')
        ).scalar_one() == "m05_ledger_revisions"
        assert db.execute(text("SELECT COUNT(*) FROM pkg010_unrelated")).scalar_one() == 1
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

    # The application-process boundary includes Session.connection(), an Engine
    # Connection, and driver SQL. Corruption tests intentionally use sqlite3 to
    # represent access outside that supported SQLAlchemy boundary.
    with sessions() as db:
        for execute in (
            lambda: db.connection().execute(
                text("UPDATE OR IGNORE m05_ledger_subjects SET provider_name = 'x'")
            ),
            lambda: db.connection().exec_driver_sql(
                "DELETE FROM ONLY m05_ledger_revisions"
            ),
        ):
            with pytest.raises(ValueError, match="M05 append-only"):
                execute()
            db.rollback()
    engine = sessions.kw["bind"]
    with engine.connect() as connection:
        with pytest.raises(ValueError, match="M05 append-only"):
            connection.execute(
                text("UPDATE ONLY m05_candidate_links SET statement_date = '2000-01-01'")
            )
        with pytest.raises(ValueError, match="M05 append-only"):
            connection.exec_driver_sql(
                "WITH x AS (SELECT 1) DELETE FROM m05_adjustment_evidence"
            )


def test_sql_tokenizer_preserves_quoted_identifier_and_literal_classes() -> None:
    tokens = _sql_tokens(
        'SELECT \'it\'\'s update m05_ledger_subjects\' AS "up""date", '
        '"update", "delete", "from", "only", "or" '
        '/* DELETE FROM m05_ledger_subjects */'
    )
    assert [(token.kind, token.value) for token in tokens] == [
        ("identifier", "select"),
        ("string_literal", "it's update m05_ledger_subjects"),
        ("identifier", "as"),
        ("identifier", 'up"date'),
        ("punctuation", ","),
        ("identifier", "update"),
        ("punctuation", ","),
        ("identifier", "delete"),
        ("punctuation", ","),
        ("identifier", "from"),
        ("punctuation", ","),
        ("identifier", "only"),
        ("punctuation", ","),
        ("identifier", "or"),
    ]


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
    client, sessions = api
    candidate_id = _candidate(client, "A-001")["candidate_id"]

    def start():
        return client.post(
            "/api/clients/1/m05/start",
            json={"candidate_id": candidate_id, "confirm_currency_ils": True},
        )

    responses = _overlap_at_insert(
        sessions, "m05_ledger_subjects", [start, start]
    )
    _assert_stable_race_outcome(responses)
    retry = start()
    assert retry.status_code == 409
    assert retry.json()["detail"]["code"] == "M05_LEDGER_ALREADY_STARTED"
    subjects = client.get("/api/clients/1/m05/subjects").json()
    assert len(subjects) == 1
    assert len(client.get(f"/api/clients/1/m05/subjects/{subjects[0]['subject_id']}/history").json()) == 1
    _assert_no_race_residue(sessions, subjects[0]["subject_id"], 1)


def test_concurrent_same_leaf_successor_has_one_winner(api) -> None:
    client, sessions = api
    started = _start(client, "A-001")
    endpoint = f"/api/clients/1/m05/subjects/{started['subject_id']}/adjust"
    values = [
        row for row in started["values"] if row["component_kind"] != "total_balance"
    ]

    def adjust(index: int):
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
        )

    responses = _overlap_at_insert(
        sessions,
        "m05_ledger_revisions",
        [lambda: adjust(0), lambda: adjust(1)],
    )
    _assert_stable_race_outcome(responses)
    history = client.get(
        f"/api/clients/1/m05/subjects/{started['subject_id']}/history"
    ).json()
    assert [row["revision_sequence"] for row in history] == [1, 2]
    assert history[1]["predecessor_revision_id"] == started["revision_id"]
    _assert_no_race_residue(sessions, started["subject_id"], 2)
    loser_index = next(
        index for index, response in enumerate(responses) if response.status_code == 409
    )
    retry = client.post(
        endpoint,
        json={
            "expected_current_revision_id": history[-1]["revision_id"],
            "evidence_identity": values[loser_index]["evidence_identity"],
            "new_effective_value": "58.00" if loser_index == 0 else "38.00",
            "reason_code": "concurrent_retry",
            "explanation": "retry against the refreshed current leaf",
            "confirmed": True,
        },
    )
    assert retry.status_code == 201, retry.text
    _assert_no_race_residue(sessions, started["subject_id"], 3)


def test_barrier_race_reconcile_vs_adjust_and_retry(api) -> None:
    client, sessions = api
    started = _start(client, "A-001")
    component = next(
        row for row in started["values"] if row["component_kind"] == "contribution_component"
    )
    def reconcile():
        return "reconcile", client.post(
            f"/api/clients/1/m05/subjects/{started['subject_id']}/reconcile",
            json={"expected_current_revision_id": started["revision_id"]},
        )

    def adjust():
        return "adjust", client.post(
            f"/api/clients/1/m05/subjects/{started['subject_id']}/adjust",
            json={
                "expected_current_revision_id": started["revision_id"],
                "evidence_identity": component["evidence_identity"],
                "new_effective_value": "59.99",
                "reason_code": "race",
                "explanation": "barrier synchronized race",
                "confirmed": True,
            },
        )

    outcomes = _overlap_at_insert(
        sessions, "m05_ledger_revisions", [reconcile, adjust]
    )
    responses = [response for _, response in outcomes]
    _assert_stable_race_outcome(responses)
    _assert_no_race_residue(sessions, started["subject_id"], 2)
    current = client.get(
        f"/api/clients/1/m05/subjects/{started['subject_id']}"
    ).json()["current_revision"]
    if current["action_type"] == "adjust":
        retry = client.post(
            f"/api/clients/1/m05/subjects/{started['subject_id']}/reconcile",
            json={"expected_current_revision_id": current["revision_id"]},
        )
    else:
        retry = client.post(
            f"/api/clients/1/m05/subjects/{started['subject_id']}/adjust",
            json={
                "expected_current_revision_id": current["revision_id"],
                "evidence_identity": component["evidence_identity"],
                "new_effective_value": "59.99",
                "reason_code": "retry",
                "explanation": "retry against the new current leaf",
                "confirmed": True,
            },
        )
    assert retry.status_code == 201, retry.text
    history = client.get(
        f"/api/clients/1/m05/subjects/{started['subject_id']}/history"
    ).json()
    assert [row["revision_sequence"] for row in history] == [1, 2, 3]
    _assert_no_race_residue(sessions, started["subject_id"], 3)


@pytest.mark.parametrize(
    ("race", "winner_index"),
    [
        ("review_vs_supersede", 0),
        ("review_vs_supersede", 1),
        ("blocked_adjust_vs_supersede", 0),
        ("blocked_adjust_vs_supersede", 1),
    ],
)
def test_barrier_simultaneous_lifecycle_actions_have_one_clean_winner(
    api, race, winner_index
) -> None:
    client, sessions = api
    started = _start(client, "A-002" if race == "review_vs_supersede" else "A-001")
    current = started
    if race == "blocked_adjust_vs_supersede":
        current = client.post(
            f"/api/clients/1/m05/subjects/{started['subject_id']}/mark-blocked",
            json={
                "expected_current_revision_id": started["revision_id"],
                "reason_code": "blocked_before_race",
                "explanation": "prepare blocked state",
            },
        ).json()
    component = next(
        row for row in current["values"] if row["component_kind"] == "contribution_component"
    )

    def first():
        if race == "review_vs_supersede":
            return client.post(
                f"/api/clients/1/m05/subjects/{started['subject_id']}/review-warning",
                json={
                    "expected_current_revision_id": current["revision_id"],
                    "mandatory_warning_ids": ["reconciliation_difference_review_required"],
                    "reason_code": "race_review",
                    "explanation": "exact warning review",
                    "confirmed": True,
                },
            )
        return client.post(
            f"/api/clients/1/m05/subjects/{started['subject_id']}/adjust",
            json={
                "expected_current_revision_id": current["revision_id"],
                "evidence_identity": component["evidence_identity"],
                "new_effective_value": "59.99",
                "reason_code": "race_adjust",
                "explanation": "blocked adjustment race",
                "confirmed": True,
            },
        )

    def second():
        return client.post(
            f"/api/clients/1/m05/subjects/{started['subject_id']}/supersede",
            json={
                "expected_current_revision_id": current["revision_id"],
                "reason_code": "race_supersede",
                "explanation": "supersession race",
            },
        )

    responses = _overlap_at_insert(
        sessions,
        "m05_ledger_revisions",
        [first, second],
        ordered_winner_index=winner_index,
        ordered_winner_marker=(
            "'review_warning'" if race == "review_vs_supersede" else "'adjust'"
        ) if winner_index == 0 else "'supersede'",
    )
    _assert_stable_race_outcome(responses)
    assert responses[winner_index].status_code == 201
    expected_action = (
        "review_warning" if race == "review_vs_supersede" else "adjust"
    ) if winner_index == 0 else "supersede"
    assert responses[winner_index].json()["action_type"] == expected_action

    subject_url = f"/api/clients/1/m05/subjects/{started['subject_id']}"
    race_leaf = client.get(subject_url).json()["current_revision"]
    assert race_leaf["revision_id"] == responses[winner_index].json()["revision_id"]
    base_revisions = 2 if race == "blocked_adjust_vs_supersede" else 1
    _assert_no_race_residue(sessions, started["subject_id"], base_revisions + 1)

    if winner_index == 0:
        retry = client.post(
            f"{subject_url}/supersede",
            json={
                "expected_current_revision_id": race_leaf["revision_id"],
                "reason_code": "conditional_retry",
                "explanation": "retry valid supersession against refreshed leaf",
            },
        )
        assert retry.status_code == 201, retry.text
        assert retry.json()["state"] == "superseded"
        assert retry.json()["predecessor_revision_id"] == race_leaf["revision_id"]
        _assert_no_race_residue(
            sessions, started["subject_id"], base_revisions + 2
        )
    else:
        if race == "review_vs_supersede":
            retry = client.post(
                f"{subject_url}/review-warning",
                json={
                    "expected_current_revision_id": race_leaf["revision_id"],
                    "mandatory_warning_ids": [
                        "reconciliation_difference_review_required"
                    ],
                    "reason_code": "invalid_retry",
                    "explanation": "terminal superseded leaf rejects warning review",
                    "confirmed": True,
                },
            )
            expected_message = "Warning review is allowed only from draft"
        else:
            retry = client.post(
                f"{subject_url}/adjust",
                json={
                    "expected_current_revision_id": race_leaf["revision_id"],
                    "evidence_identity": component["evidence_identity"],
                    "new_effective_value": "59.98",
                    "reason_code": "invalid_retry",
                    "explanation": "terminal superseded leaf rejects adjustment",
                    "confirmed": True,
                },
            )
            expected_message = "Superseded ledgers are terminal"
        assert retry.status_code == 409
        assert retry.json()["detail"] == {
            "code": "M05_INVALID_LIFECYCLE_TRANSITION",
            "message": expected_message,
        }
        assert client.get(subject_url).json()["current_revision"]["revision_id"] == race_leaf["revision_id"]
        _assert_no_race_residue(
            sessions, started["subject_id"], base_revisions + 1
        )


def test_ac010_030_isolates_candidate_tuple_uniqueness(api) -> None:
    _client, sessions = api
    isolated = _isolated_subject(sessions, "CANDIDATE")
    with sessions() as db:
        context = _candidate_context(
            db, db.get(Client, 1), db.get(M02IntakeRecord, "manual-warning")
        )
        before = {
            column.name: getattr(db.get(M05LedgerSubject, isolated.subject_id), column.name)
            for column in M05LedgerSubject.__table__.columns
        }

    outcomes, _ = _persisted_constraint_race(
        sessions,
        "m05_candidate_links",
        [
            lambda: _candidate_row(context, isolated.subject_id, "M05-C-RACE-A"),
            lambda: _candidate_row(context, isolated.subject_id, "M05-C-RACE-B"),
        ],
    )
    loser = next(item for item in outcomes if item["outcome"] != "winner")
    assert all(
        column in loser["message"]
        for column in (
            "client_id", "intake_id", "target_kind",
            "m03_revision_id", "m04_revision_id",
        )
    ), loser
    with sessions() as db:
        links = list(
            db.scalars(
                select(M05CandidateLink).where(
                    M05CandidateLink.subject_id == isolated.subject_id
                )
            ).all()
        )
        assert len(links) == 1
        assert links[0].candidate_id in {"M05-C-RACE-A", "M05-C-RACE-B"}
        after = {
            column.name: getattr(db.get(M05LedgerSubject, isolated.subject_id), column.name)
            for column in M05LedgerSubject.__table__.columns
        }
        assert after == before
        assert db.scalar(
            select(func.count()).select_from(M05LedgerRevision).where(
                M05LedgerRevision.subject_id == isolated.subject_id
            )
        ) == 0
        assert db.scalar(
            select(func.count()).select_from(M05LedgerValue).where(
                M05LedgerValue.subject_id == isolated.subject_id
            )
        ) == 0
        assert db.scalar(
            select(func.count()).select_from(M05AdjustmentEvidence).where(
                M05AdjustmentEvidence.subject_id == isolated.subject_id
            )
        ) == 0


def test_ac010_030_isolates_value_revision_identity_uniqueness(api) -> None:
    client, sessions = api
    started = _start(client, "A-001")
    revision_id = started["revision_id"]
    subject_id = started["subject_id"]
    with sessions() as db:
        before_revision = {
            column.name: getattr(db.get(M05LedgerRevision, revision_id), column.name)
            for column in M05LedgerRevision.__table__.columns
        }
        before_values = db.scalar(
            select(func.count()).select_from(M05LedgerValue).where(
                M05LedgerValue.revision_id == revision_id
            )
        )

    def value_row(value_id: str) -> M05LedgerValue:
        return M05LedgerValue(
            value_id=value_id,
            revision_id=revision_id,
            subject_id=subject_id,
            client_id=1,
            evidence_identity="isolated:value-identity",
            component_index=99,
            original_label="Isolated value identity",
            original_code="unknown_component",
            component_kind="unknown_component",
            source_state="recorded_value",
            source_value=Decimal("1.00"),
            effective_state="recorded_value",
            effective_value=Decimal("1.00"),
            included_in_reconciliation=False,
            exclusion_reason="isolated_constraint_evidence",
        )

    outcomes, _ = _persisted_constraint_race(
        sessions,
        "m05_ledger_values",
        [lambda: value_row("M05-V-RACE-A"), lambda: value_row("M05-V-RACE-B")],
    )
    loser = next(item for item in outcomes if item["outcome"] != "winner")
    assert "revision_id" in loser["message"]
    assert "evidence_identity" in loser["message"]
    with sessions() as db:
        values = list(
            db.scalars(
                select(M05LedgerValue).where(
                    M05LedgerValue.revision_id == revision_id,
                    M05LedgerValue.evidence_identity == "isolated:value-identity",
                )
            ).all()
        )
        assert len(values) == 1
        assert values[0].value_id.startswith("M05-V-")
        assert db.scalar(
            select(func.count()).select_from(M05LedgerValue).where(
                M05LedgerValue.revision_id == revision_id
            )
        ) == before_values + 1
        after_revision = {
            column.name: getattr(db.get(M05LedgerRevision, revision_id), column.name)
            for column in M05LedgerRevision.__table__.columns
        }
        assert after_revision == before_revision
        assert db.scalar(
            select(func.count()).select_from(M05AdjustmentEvidence).where(
                M05AdjustmentEvidence.revision_id == revision_id
            )
        ) == 0


def test_ac010_030_isolates_revision_subject_sequence_uniqueness(api) -> None:
    client, sessions = api
    started = _start(client, "A-001")
    isolated = _isolated_subject(sessions, "SEQUENCE")
    candidate, _ = _persist_isolated_candidate(sessions, isolated.subject_id, "SEQUENCE")
    with sessions() as db:
        template = db.get(M05LedgerRevision, started["revision_id"])
        template_values = {
            column.name: getattr(template, column.name)
            for column in M05LedgerRevision.__table__.columns
        }
    template = M05LedgerRevision(**template_values)

    outcomes, _ = _persisted_constraint_race(
        sessions,
        "m05_ledger_revisions",
        [
            lambda: _revision_row(
                template, revision_id="M05-R-SEQUENCE-A", subject_id=isolated.subject_id,
                candidate_id=candidate.candidate_id, sequence=1, predecessor_id=None,
            ),
            lambda: _revision_row(
                template, revision_id="M05-R-SEQUENCE-B", subject_id=isolated.subject_id,
                candidate_id=candidate.candidate_id, sequence=1, predecessor_id=None,
            ),
        ],
    )
    loser = next(item for item in outcomes if item["outcome"] != "winner")
    assert "subject_id" in loser["message"]
    assert "revision_sequence" in loser["message"]
    assert "predecessor_revision_id" not in loser["message"]
    with sessions() as db:
        rows = list(
            db.scalars(
                select(M05LedgerRevision).where(
                    M05LedgerRevision.subject_id == isolated.subject_id
                )
            ).all()
        )
        assert len(rows) == 1
        assert rows[0].revision_sequence == 1
        assert rows[0].predecessor_revision_id is None
        assert db.scalar(
            select(func.count()).select_from(M05LedgerValue).where(
                M05LedgerValue.subject_id == isolated.subject_id
            )
        ) == 0
        assert db.scalar(
            select(func.count()).select_from(M05AdjustmentEvidence).where(
                M05AdjustmentEvidence.subject_id == isolated.subject_id
            )
        ) == 0


def test_ac010_030_isolates_one_child_per_predecessor_uniqueness(api) -> None:
    client, sessions = api
    started = _start(client, "A-001")
    subject_id = started["subject_id"]
    root_id = started["revision_id"]
    with sessions() as db:
        source = db.get(M05LedgerRevision, root_id)
        template_values = {
            column.name: getattr(source, column.name)
            for column in M05LedgerRevision.__table__.columns
        }
        value_templates = [
            {
                column.name: getattr(value, column.name)
                for column in M05LedgerValue.__table__.columns
                if column.name not in {"value_id", "revision_id"}
            }
            for value in _values(db, root_id)
        ]
    template = M05LedgerRevision(**template_values)
    winner_revision_id = "M05-R-" + "a" * 32
    loser_revision_id = "M05-R-" + "b" * 32

    def child_bundle(revision_id: str, sequence: int):
        revision = _revision_row(
            template,
            revision_id=revision_id,
            subject_id=subject_id,
            candidate_id=started["candidate_id"],
            sequence=sequence,
            predecessor_id=root_id,
        )
        revision.state = "reconciled"
        revision.action_type = "reconcile"
        values = [
            M05LedgerValue(
                value_id=f"M05-V-{revision_id[-1]}-{index}",
                revision_id=revision_id,
                **value,
            )
            for index, value in enumerate(value_templates)
        ]
        revision.evidence_digest = _revision_digest(revision, values)
        return [revision, *values]

    outcomes, _ = _persisted_constraint_race(
        sessions,
        "m05_ledger_revisions",
        [
            lambda: child_bundle(winner_revision_id, 2),
            lambda: child_bundle(loser_revision_id, 3),
        ],
        ordered_winner_index=0,
        ordered_winner_marker=winner_revision_id,
    )
    loser = next(item for item in outcomes if item["outcome"] != "winner")
    assert "predecessor_revision_id" in loser["message"]
    assert "revision_sequence" not in loser["message"]
    with sessions() as db:
        children = list(
            db.scalars(
                select(M05LedgerRevision).where(
                    M05LedgerRevision.predecessor_revision_id == root_id
                )
            ).all()
        )
        assert len(children) == 1
        assert children[0].revision_id == winner_revision_id
        assert children[0].revision_sequence == 2
        assert db.scalar(
            select(func.count()).select_from(M05LedgerValue).where(
                M05LedgerValue.subject_id == subject_id
            )
        ) == len(value_templates) * 2
        assert db.scalar(
            select(func.count()).select_from(M05AdjustmentEvidence).where(
                M05AdjustmentEvidence.subject_id == subject_id
            )
        ) == 0

    history = client.get(
        f"/api/clients/1/m05/subjects/{subject_id}/history"
    )
    assert history.status_code == 200, history.text
    assert [row["revision_sequence"] for row in history.json()] == [1, 2]
    detail = client.get(f"/api/clients/1/m05/subjects/{subject_id}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["current_revision"]["revision_id"] == winner_revision_id
    provenance = client.get(
        f"/api/clients/1/m05/subjects/{subject_id}/provenance"
    )
    assert provenance.status_code == 200, provenance.text
    eligibility = client.get(
        f"/api/clients/1/m05/subjects/{subject_id}/m06-eligibility"
    )
    assert eligibility.status_code == 200, eligibility.text
    assert "ledger_chain_inconsistent" not in eligibility.json()["exclusion_reasons"]
    _assert_no_race_residue(sessions, subject_id, 2)

    component = next(
        value
        for value in detail.json()["current_revision"]["values"]
        if value["component_kind"] == "contribution_component"
    )
    retry = client.post(
        f"/api/clients/1/m05/subjects/{subject_id}/adjust",
        json={
            "expected_current_revision_id": winner_revision_id,
            "evidence_identity": component["evidence_identity"],
            "new_effective_value": "59.99",
            "reason_code": "post_race_retry",
            "explanation": "legitimate retry against the contiguous current leaf",
            "confirmed": True,
        },
    )
    assert retry.status_code == 201, retry.text
    assert retry.json()["revision_sequence"] == 3
    assert retry.json()["predecessor_revision_id"] == winner_revision_id
    _assert_no_race_residue(sessions, subject_id, 3)


def test_deterministic_duplicate_candidate_tuple_collision_is_isolated(api) -> None:
    client, sessions = api
    candidate_id = _candidate(client, "A-001")["candidate_id"]

    def start():
        return client.post(
            "/api/clients/1/m05/start",
            json={"candidate_id": candidate_id, "confirm_currency_ils": True},
        )

    responses = _overlap_at_insert(
        sessions, "m05_ledger_subjects", [start, start]
    )
    winner, _ = _assert_stable_race_outcome(responses)
    subject_id = winner.json()["subject_id"]
    with sessions() as db:
        links = list(
            db.scalars(
                select(M05CandidateLink).where(
                    M05CandidateLink.candidate_id == candidate_id
                )
            ).all()
        )
        assert len(links) == 1
        assert links[0].subject_id == subject_id
    _assert_no_race_residue(sessions, subject_id, 1)


def test_deterministic_duplicate_value_identity_collision_is_isolated(api) -> None:
    client, sessions = api
    started = _start(client, "A-001")
    component = next(
        value
        for value in started["values"]
        if value["component_kind"] == "contribution_component"
    )
    endpoint = f"/api/clients/1/m05/subjects/{started['subject_id']}/adjust"

    def adjust(value: str):
        return client.post(
            endpoint,
            json={
                "expected_current_revision_id": started["revision_id"],
                "evidence_identity": component["evidence_identity"],
                "new_effective_value": value,
                "reason_code": "duplicate_value_identity_race",
                "explanation": "isolate one value identity collision",
                "confirmed": True,
            },
        )

    responses = _overlap_at_insert(
        sessions,
        "m05_ledger_revisions",
        [lambda: adjust("59.00"), lambda: adjust("58.00")],
    )
    _assert_stable_race_outcome(responses)
    _assert_no_race_residue(sessions, started["subject_id"], 2)
    current = client.get(
        f"/api/clients/1/m05/subjects/{started['subject_id']}"
    ).json()["current_revision"]
    retry = client.post(
        endpoint,
        json={
            "expected_current_revision_id": current["revision_id"],
            "evidence_identity": component["evidence_identity"],
            "new_effective_value": "57.00",
            "reason_code": "duplicate_value_identity_retry",
            "explanation": "retry against the refreshed leaf",
            "confirmed": True,
        },
    )
    assert retry.status_code == 201, retry.text
    _assert_no_race_residue(sessions, started["subject_id"], 3)


def test_deterministic_revision_sequence_collision_is_isolated(api) -> None:
    client, sessions = api
    started = _start(client, "A-001")
    component = next(
        value
        for value in started["values"]
        if value["component_kind"] == "contribution_component"
    )
    subject = f"/api/clients/1/m05/subjects/{started['subject_id']}"

    def block():
        return client.post(
            f"{subject}/mark-blocked",
            json={
                "expected_current_revision_id": started["revision_id"],
                "reason_code": "sequence_race_block",
                "explanation": "isolate revision sequence uniqueness",
            },
        )

    def adjust():
        return client.post(
            f"{subject}/adjust",
            json={
                "expected_current_revision_id": started["revision_id"],
                "evidence_identity": component["evidence_identity"],
                "new_effective_value": "59.00",
                "reason_code": "sequence_race_adjust",
                "explanation": "isolate revision sequence uniqueness",
                "confirmed": True,
            },
        )

    responses = _overlap_at_insert(
        sessions, "m05_ledger_revisions", [block, adjust]
    )
    winner, _ = _assert_stable_race_outcome(responses)
    _assert_no_race_residue(sessions, started["subject_id"], 2)
    current = winner.json()
    if current["action_type"] == "mark_blocked":
        retry = client.post(
            f"{subject}/adjust",
            json={
                "expected_current_revision_id": current["revision_id"],
                "evidence_identity": component["evidence_identity"],
                "new_effective_value": "58.00",
                "reason_code": "sequence_race_retry",
                "explanation": "retry from the refreshed current leaf",
                "confirmed": True,
            },
        )
    else:
        retry = client.post(
            f"{subject}/mark-blocked",
            json={
                "expected_current_revision_id": current["revision_id"],
                "reason_code": "sequence_race_retry",
                "explanation": "retry from the refreshed current leaf",
            },
        )
    assert retry.status_code == 201, retry.text
    _assert_no_race_residue(sessions, started["subject_id"], 3)


def test_deterministic_one_child_predecessor_collision_is_isolated(api) -> None:
    client, sessions = api
    started = _start(client, "A-001")
    subject = f"/api/clients/1/m05/subjects/{started['subject_id']}"

    def reconcile():
        return client.post(
            f"{subject}/reconcile",
            json={"expected_current_revision_id": started["revision_id"]},
        )

    def block(expected: str):
        return client.post(
            f"{subject}/mark-blocked",
            json={
                "expected_current_revision_id": expected,
                "reason_code": "predecessor_child_race",
                "explanation": "isolate one-child predecessor uniqueness",
            },
        )

    responses = _overlap_at_insert(
        sessions,
        "m05_ledger_revisions",
        [reconcile, lambda: block(started["revision_id"])],
    )
    winner, _ = _assert_stable_race_outcome(responses)
    with sessions() as db:
        children = list(
            db.scalars(
                select(M05LedgerRevision).where(
                    M05LedgerRevision.predecessor_revision_id
                    == started["revision_id"]
                )
            ).all()
        )
        assert len(children) == 1
        assert children[0].revision_id == winner.json()["revision_id"]
    _assert_no_race_residue(sessions, started["subject_id"], 2)
    if winner.json()["action_type"] == "reconcile":
        retry = block(winner.json()["revision_id"])
        assert retry.status_code == 201, retry.text
        _assert_no_race_residue(sessions, started["subject_id"], 3)
    else:
        retry = client.post(
            f"{subject}/reconcile",
            json={"expected_current_revision_id": winner.json()["revision_id"]},
        )
        assert retry.status_code == 409


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


@pytest.mark.parametrize(
    ("status", "mutation_allowed"),
    [
        ("draft", True),
        ("intake", True),
        ("analysis", True),
        ("review", True),
        ("delivered", True),
        ("archived", False),
    ],
)
def test_every_m01_lifecycle_state_is_enforced(api, status, mutation_allowed) -> None:
    client, sessions = api
    with sessions() as db:
        db.get(Client, 1).status = status
        db.commit()
    candidate = _candidate(client, "A-001")
    response = client.post(
        "/api/clients/1/m05/start",
        json={"candidate_id": candidate["candidate_id"], "confirm_currency_ils": True},
    )
    if mutation_allowed:
        assert response.status_code == 201
    else:
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "archived_case"


def test_archived_reopen_requires_explicit_revalidation_after_upstream_change(api) -> None:
    client, sessions = api
    started = _start(client, "A-001")
    with sessions() as db:
        db.get(Client, 1).status = "archived"
        db.add(
            _intake(
                "manual-reopen-current",
                1,
                provider="Exact Provider",
                account="A-001",
                total="101.00",
                contribution="61.00",
                severance="40.00",
                statement_date=date(2026, 7, 2),
            )
        )
        db.commit()
    assert client.get(
        f"/api/clients/1/m05/subjects/{started['subject_id']}/m06-eligibility"
    ).json()["exclusion_reasons"][0] == "archived_case"
    with sessions() as db:
        db.get(Client, 1).status = "delivered"
        db.commit()
    _accept_upstream(client, 1, "manual-reopen-current")
    gate = client.get(
        f"/api/clients/1/m05/subjects/{started['subject_id']}/m06-eligibility"
    ).json()
    assert gate["eligible_for_m06"] is False
    assert "upstream_revalidation_required" in gate["exclusion_reasons"]
    assert "m03_ineligible" not in gate["exclusion_reasons"]
    assert client.get(
        f"/api/clients/1/m05/subjects/{started['subject_id']}/history"
    ).json()[-1]["revision_id"] == started["revision_id"]
    candidate_rows = client.get("/api/clients/1/m05/candidates").json()
    old = next(row for row in candidate_rows if row["intake_id"] == "manual-ok")
    assert old["authoritative_current"] is False
    newer = next(
        row
        for row in candidate_rows
        if row["intake_id"] == "manual-reopen-current"
    )
    response = client.post(
        f"/api/clients/1/m05/subjects/{started['subject_id']}/revalidate",
        json={
            "expected_current_revision_id": started["revision_id"],
            "candidate_id": newer["candidate_id"],
            "reason_code": "explicit_reopen_revalidation",
            "explanation": "revalidate only after explicit planner action",
        },
    )
    assert response.status_code == 201
    assert response.json()["action_type"] == "revalidate"


def test_m02_fail_closed_input_matrix(api) -> None:
    _, sessions = api
    with sessions() as db:
        client_one = db.get(Client, 1)
        client_two = db.get(Client, 2)
        intake = db.get(M02IntakeRecord, "manual-ok")
        cases = [
            ("record_kind", "uploaded", client_one, "upstream_source_ineligible"),
            ("lifecycle_status", "draft", client_one, "upstream_source_ineligible"),
            ("declared_provider_name", None, client_one, "required_value_missing"),
            ("declared_provider_name", "", client_one, "required_value_missing"),
            ("declared_account_reference", None, client_one, "required_value_missing"),
            ("declared_account_reference", "", client_one, "required_value_missing"),
            ("declared_statement_date", None, client_one, "required_value_missing"),
            ("declared_total_balance_amount", None, client_one, "required_value_missing"),
        ]
        for field, value, owner, code in cases:
            original = getattr(intake, field)
            with db.no_autoflush:
                setattr(intake, field, value)
                with pytest.raises(M05LedgerError) as raised:
                    _candidate_context(db, owner, intake)
                assert raised.value.code == code
                setattr(intake, field, original)
        with db.no_autoflush:
            with pytest.raises(M05LedgerError) as raised:
                _candidate_context(db, client_two, intake)
            assert raised.value.code == "upstream_source_ineligible"
        db.rollback()


def test_m03_m04_authority_state_matrix_is_revalidated(api) -> None:
    client, sessions = api
    intake_ids = ("m03-none", "m03-rejected", "m03-reopened", "m04-unresolved", "m04-rejected")
    with sessions() as db:
        for index, intake_id in enumerate(intake_ids, start=10):
            db.add(
                _intake(
                    intake_id,
                    1,
                    provider=f"Authority Provider {index}",
                    account=f"AUTH-{index}",
                    total="100.00",
                    contribution="60.00",
                    severance="40.00",
                )
            )
        db.commit()

    rejected_start = client.post("/api/clients/1/m03/targets/m03-rejected/start").json()
    assert client.post(
        "/api/clients/1/m03/targets/m03-rejected/reject",
        json={"reason": "rejected", "expected_current_revision_id": rejected_start["revision_id"]},
    ).status_code == 201

    reopened_start = client.post("/api/clients/1/m03/targets/m03-reopened/start").json()
    reopened_accepted = client.post(
        "/api/clients/1/m03/targets/m03-reopened/accept",
        json={"reason": "accepted", "expected_current_revision_id": reopened_start["revision_id"]},
    ).json()
    assert client.post(
        "/api/clients/1/m03/targets/m03-reopened/reopen",
        json={"reason": "reopen", "expected_current_revision_id": reopened_accepted["revision_id"]},
    ).status_code == 201

    for intake_id in ("m04-unresolved", "m04-rejected"):
        m03_started = client.post(f"/api/clients/1/m03/targets/{intake_id}/start").json()
        assert client.post(
            f"/api/clients/1/m03/targets/{intake_id}/accept",
            json={"reason": "accepted", "expected_current_revision_id": m03_started["revision_id"]},
        ).status_code == 201
    m04_started = client.post("/api/clients/1/m04/targets/m04-unresolved/start").json()
    assert m04_started["state"] == "under_review"
    rejected_m04_start = client.post("/api/clients/1/m04/targets/m04-rejected/start").json()
    rejected_proposal = client.post(
        "/api/clients/1/m04/targets/m04-rejected/proposal",
        json={"expected_current_revision_id": rejected_m04_start["revision_id"]},
    ).json()
    rejected = client.post(
        "/api/clients/1/m04/targets/m04-rejected/reject",
        json={
            "expected_current_revision_id": rejected_proposal["revision_id"],
            "reason_code": "rejected",
            "explanation": "not accepted for M05",
        },
    )
    assert rejected.status_code == 201, rejected.text

    rows = {row["intake_id"]: row for row in client.get("/api/clients/1/m05/candidates").json()}
    assert rows["m03-none"]["exclusion_reason"] == "m03_ineligible"
    assert rows["m03-rejected"]["exclusion_reason"] == "m03_ineligible"
    assert rows["m03-reopened"]["exclusion_reason"] == "m03_ineligible"
    assert rows["m04-unresolved"]["exclusion_reason"] == "m04_ineligible"
    assert rows["m04-rejected"]["exclusion_reason"] == "m04_ineligible"

    forged = client.post(
        "/api/clients/1/m05/start",
        json={
            "candidate_id": rows["m04-rejected"]["candidate_id"],
            "confirm_currency_ils": True,
            "m03_revision_id": "forged",
            "m04_revision_id": "forged",
        },
    )
    assert forged.status_code == 422


def test_exact_identity_matrix_has_no_normalization_or_concatenation_collision() -> None:
    values = [
        "Provider",
        "provider",
        " Provider",
        "Provider ",
        "Pro  vider",
        "Pro-vider",
        "é",
        "e\u0301",
        "א",
        "A",
    ]
    assert len({_identity_digest(value) for value in values}) == len(values)
    assert _identity_digest("ab") + _identity_digest("c") != _identity_digest("a") + _identity_digest("bc")
    assert _identity_digest("same") == _identity_digest("same")


@pytest.mark.parametrize(
    "value",
    [
        "999999999999999999.99",
        "0",
        "0.00",
        "0.50",
        "-0.00",
        "-0.01",
    ],
)
def test_complete_valid_monetary_parser_matrix(value) -> None:
    parsed = parse_component_money(value)
    assert parsed == (Decimal("0.00") if Decimal(value) == 0 else Decimal(value))


@pytest.mark.parametrize(
    "value",
    [
        "1000000000000000000.00",
        "999999999999999999999999999999999999999",
        "1e2",
        "+1.00",
        ".50",
        "1.",
        "",
        " 1.00",
        "1.00 ",
        "\t1.00",
        "1.00\n",
        "١.٠٠",
        1.0,
        True,
        [],
        {},
        "NaN",
        "Infinity",
        "1,00",
        "₪1.00",
        "0.500",
        "0.499",
    ],
)
def test_complete_invalid_monetary_parser_matrix(value) -> None:
    with pytest.raises(M05LedgerError):
        parse_component_money(value)


def test_complete_lifecycle_transition_matrix() -> None:
    states = {"draft", "reconciled", "warning_reviewed", "blocked", "superseded"}
    allowed = {
        ("draft", "reconcile", "reconciled"),
        ("draft", "review_warning", "warning_reviewed"),
        ("draft", "mark_blocked", "blocked"),
        ("reconciled", "mark_blocked", "blocked"),
        ("warning_reviewed", "mark_blocked", "blocked"),
        ("draft", "adjust", "draft"),
        ("reconciled", "adjust", "draft"),
        ("warning_reviewed", "adjust", "draft"),
        ("blocked", "adjust", "draft"),
        ("draft", "supersede", "superseded"),
        ("reconciled", "supersede", "superseded"),
        ("warning_reviewed", "supersede", "superseded"),
        ("blocked", "supersede", "superseded"),
        ("draft", "revalidate", "draft"),
        ("reconciled", "revalidate", "draft"),
        ("warning_reviewed", "revalidate", "draft"),
        ("blocked", "revalidate", "draft"),
    }
    actions = {"reconcile", "review_warning", "mark_blocked", "adjust", "supersede", "revalidate"}
    for previous_state in states:
        previous = SimpleNamespace(state=previous_state, revision_id="M05-R-previous", revision_sequence=1)
        for action in actions:
            for next_state in states:
                current = SimpleNamespace(
                    action_type=action,
                    state=next_state,
                    revision_sequence=2,
                    predecessor_revision_id="M05-R-previous",
                )
                assert _transition(previous, current) is (
                    (previous_state, action, next_state) in allowed
                )
    assert _transition(None, SimpleNamespace(
        action_type="start", state="draft", revision_sequence=1,
        predecessor_revision_id=None,
    )) is True


def test_reconciliation_and_warning_negative_location_matrices() -> None:
    total = {
        "evidence_identity": "total_balance", "component_kind": "total_balance",
        "effective_value": Decimal("100.00"), "source_value": Decimal("100.00"),
        "included_in_reconciliation": False, "exclusion_reason": "reconciliation_total",
    }
    contribution = {
        "evidence_identity": "component:0", "component_kind": "contribution_component",
        "effective_value": Decimal("60.00"), "source_value": Decimal("60.00"),
        "included_in_reconciliation": True, "exclusion_reason": None,
    }
    unknown = {
        "evidence_identity": "component:1", "component_kind": "unknown_component",
        "effective_value": Decimal("999.00"), "source_value": Decimal("999.00"),
        "included_in_reconciliation": False, "exclusion_reason": "unknown_component_not_reconcilable",
    }
    discrepancy, _, _, included, excluded = _reconcile([total, contribution, unknown])
    assert discrepancy == Decimal("40.00")
    assert included == [{"evidence_identity": "component:0", "effective_value": "60.00"}]
    assert excluded == [{"evidence_identity": "component:1", "reason": "unknown_component_not_reconcilable"}]
    with pytest.raises(M05LedgerError, match="non-empty"):
        _reconcile([total, unknown])
    with pytest.raises(M05LedgerError, match="identities"):
        _reconcile([total, contribution, {**contribution}])
    with pytest.raises(M05LedgerError, match="incomplete"):
        _reconcile([total, {**contribution, "effective_value": None}])

    for field in ("source_value", "effective_value"):
        for component in (
            total,
            contribution,
            {
                **contribution,
                "evidence_identity": "severance",
                "component_kind": "severance_component",
            },
        ):
            negative = [
                {**total},
                {**(component if component["component_kind"] != "total_balance" else contribution)},
            ]
            target = negative[0] if component["component_kind"] == "total_balance" else negative[1]
            target[field] = Decimal("-0.01")
            warning_ids = {item["warning_id"] for item in _warnings(negative, Decimal("0.00"), stale=False, newer_ineligible=False)}
            assert "negative_value_review_required" in warning_ids
    both = _warnings(
        [{**total, "source_value": Decimal("-1.00")}, contribution],
        Decimal("0.51"), stale=True, newer_ineligible=True,
    )
    assert both == [
        {"warning_id": "reconciliation_difference_review_required", "classification": "mandatory"},
        {"warning_id": "negative_value_review_required", "classification": "mandatory"},
        {"warning_id": "stale_warning", "classification": "informational"},
        {"warning_id": "newer_ineligible_candidate_exists", "classification": "informational"},
    ]


def test_currency_confirmation_renewal_retention_and_anti_forgery(api) -> None:
    client, _ = api
    started = _start(client, "A-001", confirm=True)
    component = next(
        row for row in started["values"] if row["component_kind"] == "contribution_component"
    )
    adjusted = client.post(
        f"/api/clients/1/m05/subjects/{started['subject_id']}/adjust",
        json={
            "expected_current_revision_id": started["revision_id"],
            "evidence_identity": component["evidence_identity"],
            "new_effective_value": "59.99",
            "reason_code": "currency_retention",
            "explanation": "non-source-changing adjustment",
            "confirmed": True,
        },
    ).json()
    assert adjusted["currency_confirmed"] is True
    assert adjusted["currency_confirmation_evidence"] == started["currency_confirmation_evidence"]

    forged = client.post(
        f"/api/clients/1/m05/subjects/{started['subject_id']}/reconcile",
        json={
            "expected_current_revision_id": adjusted["revision_id"],
            "confirm_currency_ils": True,
            "currency": "USD",
            "actor": "human",
            "confirmed_at": "2026-01-01T00:00:00Z",
            "source_snapshot_digest": "forged",
        },
    )
    assert forged.status_code == 422

    warning = _start(client, "A-002", confirm=False)
    reviewed = client.post(
        f"/api/clients/1/m05/subjects/{warning['subject_id']}/review-warning",
        json={
            "expected_current_revision_id": warning["revision_id"],
            "mandatory_warning_ids": ["reconciliation_difference_review_required"],
            "reason_code": "currency_at_review",
            "explanation": "confirm current ILS snapshot while reviewing",
            "confirmed": True,
            "confirm_currency_ils": True,
        },
    )
    assert reviewed.status_code == 201
    assert reviewed.json()["currency_confirmed"] is True


def test_warning_exact_set_negative_and_mismatch_combination(api) -> None:
    client, _ = api
    started = _start(client, "A-003")
    component = next(
        row for row in started["values"] if row["component_kind"] == "contribution_component"
    )
    adjusted = client.post(
        f"/api/clients/1/m05/subjects/{started['subject_id']}/adjust",
        json={
            "expected_current_revision_id": started["revision_id"],
            "evidence_identity": component["evidence_identity"],
            "new_effective_value": "-2.00",
            "reason_code": "combined_warning_fixture",
            "explanation": "create both locked mandatory warnings",
            "confirmed": True,
        },
    ).json()
    expected = {
        "negative_value_review_required",
        "reconciliation_difference_review_required",
    }
    assert {row["warning_id"] for row in adjusted["warnings"]} == expected
    endpoint = f"/api/clients/1/m05/subjects/{started['subject_id']}/review-warning"
    base = {
        "expected_current_revision_id": adjusted["revision_id"],
        "reason_code": "combined_review",
        "explanation": "review exact simultaneous warning set",
        "confirmed": True,
    }
    for submitted in (
        ["negative_value_review_required"],
        [*expected, "unknown_warning"],
        [*expected, "stale_warning"],
        ["negative_value_review_required", "negative_value_review_required"],
    ):
        response = client.post(endpoint, json={**base, "mandatory_warning_ids": submitted})
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "warning_disposition_invalid"
    reviewed = client.post(endpoint, json={**base, "mandatory_warning_ids": sorted(expected)})
    assert reviewed.status_code == 201
    body = reviewed.json()
    assert body["state"] == "warning_reviewed"
    without_ids = lambda rows: [
        {key: value for key, value in row.items() if key != "value_id"} for row in rows
    ]
    assert without_ids(body["values"]) == without_ids(adjusted["values"])
    assert {row["warning_id"] for row in body["warning_dispositions"]} == expected


def test_required_reason_explanation_and_confirmation_fields_are_strict(api) -> None:
    client, _ = api
    started = _start(client, "A-001")
    endpoint = f"/api/clients/1/m05/subjects/{started['subject_id']}/mark-blocked"
    for payload in (
        {"expected_current_revision_id": started["revision_id"], "reason_code": "", "explanation": "valid"},
        {"expected_current_revision_id": started["revision_id"], "reason_code": "valid", "explanation": "   "},
        {"expected_current_revision_id": started["revision_id"], "reason_code": "valid"},
    ):
        assert client.post(endpoint, json=payload).status_code == 422
    component = next(
        row for row in started["values"] if row["component_kind"] == "contribution_component"
    )
    adjustment = {
        "expected_current_revision_id": started["revision_id"],
        "evidence_identity": component["evidence_identity"],
        "new_effective_value": "59.00",
        "reason_code": "valid",
        "explanation": "valid",
    }
    assert client.post(
        f"/api/clients/1/m05/subjects/{started['subject_id']}/adjust",
        json=adjustment,
    ).status_code == 422


def test_public_eligibility_endpoint_complete_reason_vocabulary_and_combinations(
    api, monkeypatch
) -> None:
    client, sessions = api

    def create_source(
        suffix: str,
        *,
        total: str = "100.00",
        contribution: str = "60.00",
        severance: str = "40.00",
        statement_date: date = date(2026, 7, 1),
        confirm: bool = True,
        provider: str | None = None,
        account: str | None = None,
    ) -> dict:
        intake_id = f"elig-{suffix}"
        with sessions() as db:
            db.add(
                _intake(
                    intake_id,
                    1,
                    provider=provider or f"Eligibility Provider {suffix}",
                    account=account or f"ELIG-{suffix}",
                    total=total,
                    contribution=contribution,
                    severance=severance,
                    statement_date=statement_date,
                )
            )
            db.commit()
        _accept_upstream(client, 1, intake_id)
        candidate = next(
            row
            for row in client.get("/api/clients/1/m05/candidates").json()
            if row["intake_id"] == intake_id
        )
        response = client.post(
            "/api/clients/1/m05/start",
            json={
                "candidate_id": candidate["candidate_id"],
                **({"confirm_currency_ils": True} if confirm else {}),
            },
        )
        assert response.status_code == 201, response.text
        return response.json()

    def gate(started: dict) -> dict:
        response = client.get(
            f"/api/clients/1/m05/subjects/{started['subject_id']}/m06-eligibility"
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["eligible_for_m06"] is (not body["exclusion_reasons"])
        assert "result" not in body
        assert "professional_authority" not in body
        return body

    observed: set[str] = set()

    draft = create_source("draft")
    assert gate(draft)["exclusion_reasons"] == ["ledger_draft"]
    observed.add("ledger_draft")

    no_currency = create_source("currency", confirm=False)
    currency_gate = gate(no_currency)
    assert currency_gate["exclusion_reasons"] == [
        "ledger_draft",
        "currency_or_unit_invalid",
    ]
    observed.update(currency_gate["exclusion_reasons"])

    blocked = create_source("blocked")
    blocked_response = client.post(
        f"/api/clients/1/m05/subjects/{blocked['subject_id']}/mark-blocked",
        json={
            "expected_current_revision_id": blocked["revision_id"],
            "reason_code": "eligibility_fixture",
            "explanation": "prove blocked exclusion through the public route",
        },
    )
    assert blocked_response.status_code == 201
    blocked = blocked_response.json()
    assert gate(blocked)["exclusion_reasons"] == ["ledger_blocked"]
    observed.add("ledger_blocked")

    superseded = create_source("superseded")
    superseded_response = client.post(
        f"/api/clients/1/m05/subjects/{superseded['subject_id']}/supersede",
        json={
            "expected_current_revision_id": superseded["revision_id"],
            "reason_code": "eligibility_fixture",
            "explanation": "prove superseded exclusion through the public route",
        },
    )
    assert superseded_response.status_code == 201
    superseded = superseded_response.json()
    assert gate(superseded)["exclusion_reasons"] == ["ledger_superseded"]
    observed.add("ledger_superseded")

    mismatch = create_source(
        "mismatch", total="100.00", contribution="50.00", severance="49.00"
    )
    mismatch_gate = gate(mismatch)
    assert mismatch_gate["exclusion_reasons"] == [
        "ledger_draft",
        "reconciliation_unresolved",
        "warning_not_reviewed",
    ]
    observed.update(mismatch_gate["exclusion_reasons"])

    negative = create_source(
        "negative", total="-1.00", contribution="-1.00", severance="0.00"
    )
    negative_gate = gate(negative)
    assert negative_gate["exclusion_reasons"] == [
        "ledger_draft",
        "negative_value_review_required",
        "warning_not_reviewed",
    ]
    observed.update(negative_gate["exclusion_reasons"])

    future = create_source("future")
    with sessions() as db:
        db.get(M02IntakeRecord, "elig-future").declared_statement_date = (
            date.today() + timedelta(days=1)
        )
        db.commit()
    future_gate = gate(future)
    assert future_gate["exclusion_reasons"] == ["ledger_draft", "statement_date_invalid"]
    observed.update(future_gate["exclusion_reasons"])

    for suffix, field, value, expected in (
        ("required", "declared_provider_name", None, "required_value_missing"),
        (
            "mapping",
            "declared_component_values",
            [
                {"label": "Changed", "code": "contribution_component", "value": "60.00"},
                {"label": "Severance", "code": "severance_component", "value": "40.00"},
            ],
            "m03_ineligible",
        ),
        ("incomplete", "declared_component_values", [], "m03_ineligible"),
        ("source", "lifecycle_status", "rejected", "upstream_source_ineligible"),
    ):
        started = create_source(suffix)
        with sessions() as db:
            intake = db.get(M02IntakeRecord, f"elig-{suffix}")
            setattr(intake, field, value)
            db.commit()
        reasons = gate(started)["exclusion_reasons"]
        assert reasons == _ordered_eligibility_reasons(["ledger_draft", expected])
        observed.update(reasons)

    m03 = create_source("m03")
    m03_target = client.get("/api/clients/1/m03/targets/elig-m03").json()
    response = client.post(
        "/api/clients/1/m03/targets/elig-m03/reopen",
        json={
            "reason": "public eligibility fixture",
            "expected_current_revision_id": m03_target["current_revision"]["revision_id"],
        },
    )
    assert response.status_code == 201
    m03_gate = gate(m03)
    assert m03_gate["exclusion_reasons"] == ["m03_ineligible", "ledger_draft"]
    observed.update(m03_gate["exclusion_reasons"])

    m04 = create_source("m04")
    m04_target = client.get("/api/clients/1/m04/targets/elig-m04").json()
    response = client.post(
        "/api/clients/1/m04/targets/elig-m04/reopen",
        json={
            "expected_current_revision_id": m04_target["current_revision"]["revision_id"],
            "reason_code": "public_fixture",
            "explanation": "prove M04 current authority is revalidated",
        },
    )
    assert response.status_code == 201, response.text
    m04_gate = gate(m04)
    assert m04_gate["exclusion_reasons"] == ["m04_ineligible", "ledger_draft"]
    observed.update(m04_gate["exclusion_reasons"])

    revalidation = create_source(
        "revalidation", provider="Revalidation Provider", account="REVALIDATE"
    )
    with sessions() as db:
        db.add(
            _intake(
                "elig-revalidation-new",
                1,
                provider="Revalidation Provider",
                account="REVALIDATE",
                total="101.00",
                contribution="61.00",
                severance="40.00",
                statement_date=date(2026, 7, 2),
            )
        )
        db.commit()
    _accept_upstream(client, 1, "elig-revalidation-new")
    revalidation_gate = gate(revalidation)
    assert revalidation_gate["exclusion_reasons"] == [
        "upstream_revalidation_required",
        "ledger_draft",
    ]
    observed.update(revalidation_gate["exclusion_reasons"])

    no_candidate = create_source("none")
    _external_sql(
        sessions,
        "UPDATE m02_intake_records SET client_id = 2 WHERE intake_id = :intake_id",
        {"intake_id": "elig-none"},
        bypass_constraints=True,
    )
    no_candidate_gate = gate(no_candidate)
    assert no_candidate_gate["exclusion_reasons"] == [
        "no_authoritative_candidate",
        "ledger_draft",
    ]
    observed.update(no_candidate_gate["exclusion_reasons"])

    provenance = create_source("provenance")
    altered = dict(provenance["provenance"])
    altered["client_id"] = 999
    _external_sql(
        sessions,
        "UPDATE m05_ledger_revisions SET provenance = :provenance "
        "WHERE revision_id = :revision_id",
        {"provenance": json.dumps(altered), "revision_id": provenance["revision_id"]},
    )
    _resign_revision(sessions, provenance["revision_id"])
    provenance_gate = gate(provenance)
    assert provenance_gate["exclusion_reasons"] == ["ledger_draft", "provenance_invalid"]
    observed.update(provenance_gate["exclusion_reasons"])

    invalid_disposition = create_source(
        "disposition", total="100.00", contribution="50.00", severance="49.00"
    )
    _external_sql(
        sessions,
        "UPDATE m05_ledger_revisions SET warning_dispositions = :value "
        "WHERE revision_id = :revision_id",
        {
            "value": json.dumps([{"warning_id": "unknown_warning"}]),
            "revision_id": invalid_disposition["revision_id"],
        },
    )
    _resign_revision(sessions, invalid_disposition["revision_id"])
    disposition_gate = gate(invalid_disposition)
    assert disposition_gate["exclusion_reasons"] == [
        "ledger_draft",
        "reconciliation_unresolved",
        "warning_disposition_invalid",
        "warning_not_reviewed",
    ]
    observed.update(disposition_gate["exclusion_reasons"])

    corrupted = create_source("corrupted")
    _external_sql(
        sessions,
        "UPDATE m05_ledger_revisions SET reason_code = 'corrupted' "
        "WHERE revision_id = :revision_id",
        {"revision_id": corrupted["revision_id"]},
    )
    with sessions() as db:
        db.get(Client, 1).status = "archived"
        db.commit()
    corrupted_gate = gate(corrupted)
    assert corrupted_gate["exclusion_reasons"] == ["ledger_chain_inconsistent"]
    assert corrupted_gate["informational_warnings"] == []
    observed.add("ledger_chain_inconsistent")
    with sessions() as db:
        db.get(Client, 1).status = "delivered"
        db.commit()

    fixed = datetime.now(timezone.utc) + timedelta(minutes=1)
    monkeypatch.setattr("app.models.m03_review.m03_server_timestamp", lambda: fixed)
    tie = create_source(
        "tie-one", provider="Tie Gate Provider", account="TIE-GATE"
    )
    with sessions() as db:
        db.add_all(
            [
                _intake(
                    "elig-tie-two",
                    1,
                    provider="Tie Gate Provider",
                    account="TIE-GATE",
                    total="100.00",
                    contribution="60.00",
                    severance="40.00",
                ),
                _intake(
                    "elig-tie-newer-ineligible",
                    1,
                    provider="Tie Gate Provider",
                    account="TIE-GATE",
                    total="101.00",
                    contribution="61.00",
                    severance="40.00",
                    statement_date=date(2026, 7, 2),
                ),
            ]
        )
        db.commit()
    _accept_upstream(client, 1, "elig-tie-two")
    tie_gate = gate(tie)
    assert tie_gate["exclusion_reasons"] == ["authoritative_candidate_tie", "ledger_draft"]
    assert tie_gate["informational_warnings"] == [
        "newer_ineligible_candidate_exists"
    ]
    observed.update(tie_gate["exclusion_reasons"])
    monkeypatch.undo()

    stale = create_source(
        "stale",
        statement_date=date.today() - timedelta(days=400),
    )
    reconciled = client.post(
        f"/api/clients/1/m05/subjects/{stale['subject_id']}/reconcile",
        json={"expected_current_revision_id": stale["revision_id"]},
    )
    assert reconciled.status_code == 201
    stale_gate = gate(reconciled.json())
    assert stale_gate["eligible_for_m06"] is True
    assert stale_gate["exclusion_reasons"] == []
    assert stale_gate["informational_warnings"] == ["stale_warning"]
    with sessions() as db:
        db.get(Client, 1).status = "archived"
        db.commit()
    archived_stale_gate = gate(reconciled.json())
    assert archived_stale_gate["exclusion_reasons"] == ["archived_case"]
    assert archived_stale_gate["informational_warnings"] == ["stale_warning"]
    observed.add("archived_case")

    assert observed == set(ELIGIBILITY_REASON_ORDER).difference(
        {
            "component_mapping_invalid",
            "component_set_incomplete",
        }
    )


def _public_state(client: TestClient, state: str, *, warning: bool = False) -> dict:
    current = _start(client, "A-002" if warning else "A-001")
    subject_id = current["subject_id"]
    if state == "draft":
        return current
    if state == "reconciled":
        response = client.post(
            f"/api/clients/1/m05/subjects/{subject_id}/reconcile",
            json={"expected_current_revision_id": current["revision_id"]},
        )
    elif state == "warning_reviewed":
        response = client.post(
            f"/api/clients/1/m05/subjects/{subject_id}/review-warning",
            json={
                "expected_current_revision_id": current["revision_id"],
                "mandatory_warning_ids": ["reconciliation_difference_review_required"],
                "reason_code": "matrix_review",
                "explanation": "review the complete mandatory warning set",
                "confirmed": True,
            },
        )
    elif state == "blocked":
        response = client.post(
            f"/api/clients/1/m05/subjects/{subject_id}/mark-blocked",
            json={
                "expected_current_revision_id": current["revision_id"],
                "reason_code": "matrix_block",
                "explanation": "create the blocked matrix state",
            },
        )
    elif state == "superseded":
        response = client.post(
            f"/api/clients/1/m05/subjects/{subject_id}/supersede",
            json={
                "expected_current_revision_id": current["revision_id"],
                "reason_code": "matrix_supersede",
                "explanation": "create the terminal matrix state",
            },
        )
    else:
        raise AssertionError(f"unsupported fixture state: {state}")
    assert response.status_code == 201, response.text
    return response.json()


def _complete_successor(previous: dict, current: dict, expected_state: str) -> None:
    assert current["state"] == expected_state
    assert current["predecessor_revision_id"] == previous["revision_id"]
    assert current["revision_sequence"] == previous["revision_sequence"] + 1
    assert current["candidate_id"]
    assert current["intake_id"]
    assert current["m03_revision_id"]
    assert current["m04_revision_id"]
    assert current["source_snapshot_digest"]
    assert current["mapping_digest"]
    assert current["values"]
    assert current["source_total_state"] in {"recorded_value", "recorded_zero"}
    assert current["effective_total_state"] in {"recorded_value", "recorded_zero"}
    assert current["currency"] == "ILS"
    assert current["currency_confirmation_evidence"]
    assert current["actor"] == "system:m05-ledger-ui:M05 ledger workflow"
    assert current["created_at"]
    assert current["provenance"]["client_id"] == 1
    assert current["provenance"]["candidate_link"]["candidate_id"] == current["candidate_id"]


@pytest.mark.parametrize(
    ("previous_state", "action", "expected_state", "warning"),
    [
        ("draft", "reconcile", "reconciled", False),
        ("draft", "review_warning", "warning_reviewed", True),
        ("draft", "mark_blocked", "blocked", False),
        ("reconciled", "mark_blocked", "blocked", False),
        ("warning_reviewed", "mark_blocked", "blocked", True),
        ("draft", "adjust", "draft", False),
        ("reconciled", "adjust", "draft", False),
        ("warning_reviewed", "adjust", "draft", True),
        ("blocked", "adjust", "draft", False),
        ("draft", "supersede", "superseded", False),
        ("reconciled", "supersede", "superseded", False),
        ("warning_reviewed", "supersede", "superseded", True),
        ("blocked", "supersede", "superseded", False),
        ("draft", "revalidate", "draft", False),
        ("reconciled", "revalidate", "draft", False),
        ("warning_reviewed", "revalidate", "draft", True),
        ("blocked", "revalidate", "draft", False),
    ],
)
def test_ac010_015_016_every_allowed_transition_is_public_and_complete(
    api, previous_state, action, expected_state, warning
) -> None:
    client, sessions = api
    previous = _public_state(client, previous_state, warning=warning)
    subject_id = previous["subject_id"]
    endpoint = action.replace("_", "-")
    payload: dict = {"expected_current_revision_id": previous["revision_id"]}
    if action == "review_warning":
        payload.update(
            mandatory_warning_ids=["reconciliation_difference_review_required"],
            reason_code="allowed_review",
            explanation="execute the public lifecycle matrix",
            confirmed=True,
        )
    elif action in {"mark_blocked", "supersede"}:
        payload.update(
            reason_code=f"allowed_{action}",
            explanation="execute the public lifecycle matrix",
        )
    elif action == "adjust":
        component = next(
            value
            for value in previous["values"]
            if value["component_kind"] == "contribution_component"
        )
        payload.update(
            evidence_identity=component["evidence_identity"],
            new_effective_value="59.00",
            reason_code="allowed_adjust",
            explanation="execute a single-identity public adjustment",
            confirmed=True,
        )
    elif action == "revalidate":
        intake_id = f"revalidate-{previous_state}"
        with sessions() as db:
            source = db.get(M02IntakeRecord, previous["intake_id"])
            db.add(
                _intake(
                    intake_id,
                    1,
                    provider=source.declared_provider_name,
                    account=source.declared_account_reference,
                    total="101.00",
                    contribution="61.00",
                    severance="40.00",
                    statement_date=source.declared_statement_date + timedelta(days=1),
                )
            )
            db.commit()
        _accept_upstream(client, 1, intake_id)
        candidate = next(
            row
            for row in client.get("/api/clients/1/m05/candidates").json()
            if row["intake_id"] == intake_id
        )
        payload.update(
            candidate_id=candidate["candidate_id"],
            reason_code="allowed_revalidate",
            explanation="bind a complete successor to current upstream authority",
        )
    response = client.post(
        f"/api/clients/1/m05/subjects/{subject_id}/{endpoint}", json=payload
    )
    assert response.status_code == 201, response.text
    current = response.json()
    _complete_successor(previous, current, expected_state)
    history_rows = client.get(
        f"/api/clients/1/m05/subjects/{subject_id}/history"
    ).json()
    assert history_rows[-1] == current
    assert history_rows[-2]["revision_id"] == previous["revision_id"]


@pytest.mark.parametrize(
    ("state", "action", "warning"),
    [
        ("reconciled", "reconcile", False),
        ("reconciled", "review_warning", False),
        ("warning_reviewed", "reconcile", True),
        ("warning_reviewed", "review_warning", True),
        ("blocked", "reconcile", False),
        ("blocked", "review_warning", False),
        ("blocked", "mark_blocked", False),
        ("superseded", "reconcile", False),
        ("superseded", "review_warning", False),
        ("superseded", "mark_blocked", False),
        ("superseded", "adjust", False),
        ("superseded", "supersede", False),
        ("superseded", "revalidate", False),
    ],
)
def test_ac010_015_every_prohibited_transition_fails_without_partial_successor(
    api, state, action, warning
) -> None:
    client, _ = api
    previous = _public_state(client, state, warning=warning)
    subject_id = previous["subject_id"]
    endpoint = action.replace("_", "-")
    payload: dict = {"expected_current_revision_id": previous["revision_id"]}
    if action == "review_warning":
        payload.update(
            mandatory_warning_ids=[],
            reason_code="prohibited_review",
            explanation="must not create a successor",
            confirmed=True,
        )
    elif action in {"mark_blocked", "supersede", "revalidate"}:
        payload.update(
            reason_code=f"prohibited_{action}",
            explanation="must not create a successor",
        )
        if action == "revalidate":
            payload["candidate_id"] = previous["candidate_id"]
    elif action == "adjust":
        component = next(
            value
            for value in previous["values"]
            if value["component_kind"] == "contribution_component"
        )
        payload.update(
            evidence_identity=component["evidence_identity"],
            new_effective_value="59.00",
            reason_code="prohibited_adjust",
            explanation="must not create a successor",
            confirmed=True,
        )
    before = client.get(
        f"/api/clients/1/m05/subjects/{subject_id}/history"
    ).json()
    response = client.post(
        f"/api/clients/1/m05/subjects/{subject_id}/{endpoint}", json=payload
    )
    assert response.status_code == 409
    after = client.get(
        f"/api/clients/1/m05/subjects/{subject_id}/history"
    ).json()
    assert after == before


@pytest.mark.parametrize(
    ("statement", "evaluation", "expected_stale"),
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
def test_ac010_025_locked_calendar_examples_execute_through_public_start(
    api, monkeypatch, statement, evaluation, expected_stale
) -> None:
    client, sessions = api

    class ServerDate(date):
        @classmethod
        def today(cls):
            return cls(evaluation.year, evaluation.month, evaluation.day)

    monkeypatch.setattr("app.services.m05_ledger_service.date", ServerDate)
    suffix = f"{statement.isoformat()}-{evaluation.isoformat()}"
    intake_id = f"calendar-{suffix}"
    account = f"CAL-{suffix}"
    with sessions() as db:
        db.add(
            _intake(
                intake_id,
                1,
                provider="Calendar Provider",
                account=account,
                total="100.00",
                contribution="60.00",
                severance="40.00",
                statement_date=statement,
            )
        )
        db.commit()
    _accept_upstream(client, 1, intake_id)
    candidate = _candidate(client, account)
    started_response = client.post(
        "/api/clients/1/m05/start",
        json={
            "candidate_id": candidate["candidate_id"],
            "confirm_currency_ils": True,
        },
    )
    assert started_response.status_code == 201, started_response.text
    started = started_response.json()
    assert started["statement_date"] == statement.isoformat()
    assert started["evaluation_date"] == evaluation.isoformat()
    assert started["is_stale"] is expected_stale
    warning_ids = {warning["warning_id"] for warning in started["warnings"]}
    assert ("stale_warning" in warning_ids) is expected_stale
    forged = client.post(
        "/api/clients/1/m05/start",
        json={
            "candidate_id": started["candidate_id"],
            "confirm_currency_ils": True,
            "evaluation_date": evaluation.isoformat(),
        },
    )
    assert forged.status_code == 422
    historical = client.get(
        f"/api/clients/1/m05/subjects/{started['subject_id']}/history"
    ).json()
    assert historical[0]["evaluation_date"] == evaluation.isoformat()
    assert historical[0]["is_stale"] is expected_stale


def test_ac010_023_adjustment_public_matrix_and_immutable_source(api) -> None:
    client, sessions = api
    started = _start(client, "A-001")
    original_by_identity = {
        row["evidence_identity"]: row for row in started["values"]
    }
    total = original_by_identity["total_balance"]
    response = client.post(
        f"/api/clients/1/m05/subjects/{started['subject_id']}/adjust",
        json={
            "expected_current_revision_id": started["revision_id"],
            "evidence_identity": total["evidence_identity"],
            "new_effective_value": "99.00",
            "reason_code": "total_adjustment",
            "explanation": "adjust exactly one total identity",
            "confirmed": True,
        },
    )
    assert response.status_code == 201, response.text
    adjusted = response.json()
    adjusted_by_identity = {
        row["evidence_identity"]: row for row in adjusted["values"]
    }
    assert adjusted_by_identity["total_balance"]["source_value"] == "100.00"
    assert adjusted_by_identity["total_balance"]["effective_value"] == "99.00"
    assert adjusted_by_identity["total_balance"]["source_state"] == "recorded_value"
    assert adjusted["adjustment"]["previous_effective_value"] == "100.00"
    assert adjusted["adjustment"]["new_effective_value"] == "99.00"
    assert adjusted["currency_confirmation_evidence"] == started["currency_confirmation_evidence"]
    assert {item["warning_id"] for item in adjusted["warnings"]} == {
        "reconciliation_difference_review_required"
    }
    for identity, original in original_by_identity.items():
        if identity != "total_balance":
            assert adjusted_by_identity[identity]["source_value"] == original["source_value"]
            assert adjusted_by_identity[identity]["effective_value"] == original["effective_value"]

    history_before = client.get(
        f"/api/clients/1/m05/subjects/{started['subject_id']}/history"
    ).json()
    stale_leaf = client.post(
        f"/api/clients/1/m05/subjects/{started['subject_id']}/adjust",
        json={
            "expected_current_revision_id": started["revision_id"],
            "evidence_identity": "total_balance",
            "new_effective_value": "98.00",
            "reason_code": "stale_leaf",
            "explanation": "must resolve only the current leaf",
            "confirmed": True,
        },
    )
    assert stale_leaf.status_code == 409
    batch = client.post(
        f"/api/clients/1/m05/subjects/{started['subject_id']}/adjust",
        json={
            "expected_current_revision_id": adjusted["revision_id"],
            "evidence_identity": "total_balance",
            "new_effective_value": "98.00",
            "reason_code": "batch_attempt",
            "explanation": "batch input is not part of the contract",
            "confirmed": True,
            "adjustments": [{"evidence_identity": "component:forged"}],
        },
    )
    assert batch.status_code == 422
    assert client.get(
        f"/api/clients/1/m05/subjects/{started['subject_id']}/history"
    ).json() == history_before

    with sessions() as db:
        db.get(M02IntakeRecord, "manual-ok").declared_total_balance_amount = None
        db.commit()
    missing_source = client.post(
        f"/api/clients/1/m05/subjects/{started['subject_id']}/adjust",
        json={
            "expected_current_revision_id": adjusted["revision_id"],
            "evidence_identity": "total_balance",
            "new_effective_value": "98.00",
            "reason_code": "missing_source",
            "explanation": "missing predecessor authority must fail closed",
            "confirmed": True,
        },
    )
    assert missing_source.status_code == 409
    assert missing_source.json()["detail"]["code"] == "required_value_missing"


def test_ac010_007_008_009_019_public_component_mapping_contract(api) -> None:
    client, sessions = api
    intake_id = "component-contract"
    with sessions() as db:
        intake = _intake(
            intake_id,
            1,
            provider="Component Contract Provider",
            account="COMPONENT-CONTRACT",
            total="40.00",
            contribution="0.00",
            severance="40.00",
        )
        intake.declared_component_values = [
            {"label": "Duplicate label", "code": "source-contribution", "value": "0.00"},
            {"label": "Duplicate label", "code": "source-unknown", "value": "40.00"},
        ]
        db.add(intake)
        db.commit()
    m03_started = client.post(f"/api/clients/1/m03/targets/{intake_id}/start").json()
    assert client.post(
        f"/api/clients/1/m03/targets/{intake_id}/accept",
        json={"reason": "accepted", "expected_current_revision_id": m03_started["revision_id"]},
    ).status_code == 201
    m04_started = client.post(f"/api/clients/1/m04/targets/{intake_id}/start").json()
    proposal = client.post(
        f"/api/clients/1/m04/targets/{intake_id}/proposal",
        json={"expected_current_revision_id": m04_started["revision_id"]},
    ).json()
    assert len(proposal["components"]) == 2
    assert proposal["components"][0]["original_label"] == proposal["components"][1]["original_label"]
    assert proposal["components"][0]["evidence_identity"] != proposal["components"][1]["evidence_identity"]

    base_component = {
        "evidence_identity": proposal["components"][0]["evidence_identity"],
        "interpretation": "pension",
        "current_employer_related": "unknown",
        "explanation": "prohibited vocabulary must not enter persistence",
    }
    for prohibited in (
        "compensation_component",
        "capital",
        "pension",
        "arbitrary_component_kind",
    ):
        rejected = client.post(
            f"/api/clients/1/m04/targets/{intake_id}/override",
            json={
                "expected_current_revision_id": proposal["revision_id"],
                "reason_code": "prohibited_vocabulary",
                "explanation": "reject non-enum component vocabulary",
                "confirmed": True,
                "product_family": "provident_fund",
                "pension_subtype": None,
                "components": [
                    {**base_component, "component_kind": prohibited},
                    {
                        **base_component,
                        "evidence_identity": proposal["components"][1]["evidence_identity"],
                        "component_kind": "severance_component",
                    },
                ],
            },
        )
        assert rejected.status_code == 422

    overridden = client.post(
        f"/api/clients/1/m04/targets/{intake_id}/override",
        json={
            "expected_current_revision_id": proposal["revision_id"],
            "reason_code": "exact_mapping",
            "explanation": "preserve indexed identities and bounded vocabulary",
            "confirmed": True,
            "product_family": "provident_fund",
            "pension_subtype": None,
            "components": [
                {**base_component, "component_kind": "contribution_component"},
                {
                    **base_component,
                    "evidence_identity": proposal["components"][1]["evidence_identity"],
                    "component_kind": "severance_component",
                },
            ],
        },
    )
    assert overridden.status_code == 201, overridden.text
    accepted = client.post(
        f"/api/clients/1/m04/targets/{intake_id}/accept",
        json={
            "expected_current_revision_id": overridden.json()["revision_id"],
            "reason_code": "accept_mapping",
            "explanation": "accept exact indexed mapping",
        },
    )
    assert accepted.status_code == 201, accepted.text
    candidate_row = next(
        row
        for row in client.get("/api/clients/1/m05/candidates").json()
        if row["intake_id"] == intake_id
    )
    started_response = client.post(
        "/api/clients/1/m05/start",
        json={"candidate_id": candidate_row["candidate_id"], "confirm_currency_ils": True},
    )
    assert started_response.status_code == 201, started_response.text
    started = started_response.json()
    components = [row for row in started["values"] if row["component_index"] is not None]
    assert [row["component_index"] for row in components] == [0, 1]
    assert components[0]["original_label"] == components[1]["original_label"]
    assert components[0]["evidence_identity"] != components[1]["evidence_identity"]
    assert components[0]["source_state"] == "recorded_zero"
    assert components[0]["source_value"] == "0.00"
    assert components[0]["included_in_reconciliation"] is True
    assert components[1]["component_kind"] == "severance_component"
    assert components[1]["source_value"] == "40.00"
    assert components[1]["included_in_reconciliation"] is True
    assert components[1]["exclusion_reason"] is None
    reconciled = client.post(
        f"/api/clients/1/m05/subjects/{started['subject_id']}/reconcile",
        json={"expected_current_revision_id": started["revision_id"]},
    )
    assert reconciled.status_code == 201, reconciled.text
    body = reconciled.json()
    assert body["signed_discrepancy"] == "0.00"
    assert body["included_evidence"] == [
        {"evidence_identity": components[0]["evidence_identity"], "effective_value": "0.00"},
        {"evidence_identity": components[1]["evidence_identity"], "effective_value": "40.00"},
    ]
    assert body["excluded_evidence"] == []

    forged = client.post(
        "/api/clients/1/m05/start",
        json={
            "candidate_id": candidate_row["candidate_id"],
            "confirm_currency_ils": True,
            "component_kind": "compensation_component",
            "mapping": [{"component_kind": "capital"}],
        },
    )
    assert forged.status_code == 422


def test_ac010_028_complete_public_foreign_missing_non_leakage(api) -> None:
    client, _ = api
    local = _start(client, "A-001")
    foreign_candidate = _candidate(client, "A-001", client_id=2)
    foreign_started_response = client.post(
        "/api/clients/2/m05/start",
        json={"candidate_id": foreign_candidate["candidate_id"], "confirm_currency_ils": True},
    )
    assert foreign_started_response.status_code == 201
    foreign_started = foreign_started_response.json()

    def same_public(left, right) -> None:
        assert left.status_code == right.status_code
        assert left.json() == right.json()
        assert left.headers.get("content-type") == right.headers.get("content-type")
        assert left.headers.get("content-length") == right.headers.get("content-length")

    foreign_candidate_attempt = client.post(
        "/api/clients/1/m05/start",
        json={"candidate_id": foreign_candidate["candidate_id"], "confirm_currency_ils": True},
    )
    missing_candidate_attempt = client.post(
        "/api/clients/1/m05/start",
        json={"candidate_id": "M05-CAND-0000000000000000000000000000000000000000", "confirm_currency_ils": True},
    )
    same_public(foreign_candidate_attempt, missing_candidate_attempt)

    for suffix in ("", "/history", "/provenance", "/warnings", "/m06-eligibility"):
        same_public(
            client.get(
                f"/api/clients/1/m05/subjects/{foreign_started['subject_id']}{suffix}"
            ),
            client.get(f"/api/clients/1/m05/subjects/M05-S-missing{suffix}"),
        )

    reason_payload = {
        "expected_current_revision_id": foreign_started["revision_id"],
        "reason_code": "non_leakage",
        "explanation": "foreign and missing identifiers are indistinguishable",
    }
    for endpoint, payload in (
        ("reconcile", {"expected_current_revision_id": foreign_started["revision_id"]}),
        ("mark-blocked", reason_payload),
        ("supersede", reason_payload),
        (
            "review-warning",
            {**reason_payload, "mandatory_warning_ids": [], "confirmed": True},
        ),
        (
            "adjust",
            {
                **reason_payload,
                "evidence_identity": "total_balance",
                "new_effective_value": "99.00",
                "confirmed": True,
            },
        ),
        (
            "revalidate",
            {**reason_payload, "candidate_id": foreign_candidate["candidate_id"]},
        ),
    ):
        same_public(
            client.post(
                f"/api/clients/1/m05/subjects/{foreign_started['subject_id']}/{endpoint}",
                json=payload,
            ),
            client.post(
                f"/api/clients/1/m05/subjects/M05-S-missing/{endpoint}",
                json=payload,
            ),
        )

    foreign_revision = foreign_started["revision_id"]
    missing_revision = "M05-R-00000000000000000000000000000000"
    same_public(
        client.post(
            f"/api/clients/1/m05/subjects/{local['subject_id']}/reconcile",
            json={"expected_current_revision_id": foreign_revision},
        ),
        client.post(
            f"/api/clients/1/m05/subjects/{local['subject_id']}/reconcile",
            json={"expected_current_revision_id": missing_revision},
        ),
    )
    same_public(
        client.post(
            f"/api/clients/1/m05/subjects/{local['subject_id']}/revalidate",
            json={
                "expected_current_revision_id": local["revision_id"],
                "candidate_id": foreign_candidate["candidate_id"],
                "reason_code": "non_leakage",
                "explanation": "foreign candidate",
            },
        ),
        client.post(
            f"/api/clients/1/m05/subjects/{local['subject_id']}/revalidate",
            json={
                "expected_current_revision_id": local["revision_id"],
                "candidate_id": "M05-CAND-0000000000000000000000000000000000000000",
                "reason_code": "non_leakage",
                "explanation": "missing candidate",
            },
        ),
    )


def test_ac010_006_candidate_tuple_is_server_resolved_current_and_unique(api) -> None:
    client, _ = api
    original = _candidate(client, "A-001")
    started = _start(client, "A-001")
    duplicate = client.post(
        "/api/clients/1/m05/start",
        json={"candidate_id": original["candidate_id"], "confirm_currency_ils": True},
    )
    assert duplicate.status_code == 409
    assert len(
        client.get(
            f"/api/clients/1/m05/subjects/{started['subject_id']}/history"
        ).json()
    ) == 1

    m03_target = client.get("/api/clients/1/m03/targets/manual-ok").json()
    reopened = client.post(
        "/api/clients/1/m03/targets/manual-ok/reopen",
        json={
            "reason": "new current review revision",
            "expected_current_revision_id": m03_target["current_revision"]["revision_id"],
        },
    )
    assert reopened.status_code == 201
    accepted = client.post(
        "/api/clients/1/m03/targets/manual-ok/accept",
        json={
            "reason": "new accepted current review revision",
            "expected_current_revision_id": reopened.json()["revision_id"],
        },
    )
    assert accepted.status_code == 201
    m04_target = client.get("/api/clients/1/m04/targets/manual-ok").json()
    revalidation = client.post(
        "/api/clients/1/m04/targets/manual-ok/start-revalidation",
        json={
            "expected_current_revision_id": m04_target["current_revision"]["revision_id"],
            "reason_code": "upstream_revision_changed",
            "explanation": "bind classification to the current M03 revision",
        },
    )
    assert revalidation.status_code == 201, revalidation.text
    proposal = client.post(
        "/api/clients/1/m04/targets/manual-ok/proposal",
        json={"expected_current_revision_id": revalidation.json()["revision_id"]},
    )
    assert proposal.status_code == 201, proposal.text
    components = [
        {
            "evidence_identity": component["evidence_identity"],
            "component_kind": component["original_code"],
            "interpretation": "pension",
            "current_employer_related": "unknown",
            "explanation": "exact current component mapping",
        }
        for component in proposal.json()["components"]
    ]
    overridden = client.post(
        "/api/clients/1/m04/targets/manual-ok/override",
        json={
            "expected_current_revision_id": proposal.json()["revision_id"],
            "reason_code": "current_tuple",
            "explanation": "create current accepted M04 evidence",
            "confirmed": True,
            "product_family": "provident_fund",
            "pension_subtype": None,
            "components": components,
        },
    )
    assert overridden.status_code == 201
    m04_accepted = client.post(
        "/api/clients/1/m04/targets/manual-ok/accept",
        json={
            "expected_current_revision_id": overridden.json()["revision_id"],
            "reason_code": "current_tuple",
            "explanation": "accept current tuple evidence",
        },
    )
    assert m04_accepted.status_code == 201, m04_accepted.text
    current = _candidate(client, "A-001")
    assert current["candidate_id"] != original["candidate_id"]
    assert current["m03_revision_id"] == accepted.json()["revision_id"]
    assert current["m04_revision_id"] == m04_accepted.json()["revision_id"]
    stale = client.post(
        "/api/clients/1/m05/start",
        json={"candidate_id": original["candidate_id"], "confirm_currency_ils": True},
    )
    assert stale.status_code == 404
    forged = client.post(
        "/api/clients/1/m05/start",
        json={
            "candidate_id": current["candidate_id"],
            "confirm_currency_ils": True,
            "client_id": 1,
            "intake_id": "manual-ok",
            "target_kind": "manual_record_review",
            "m03_revision_id": accepted.json()["revision_id"],
            "m04_revision_id": m04_accepted.json()["revision_id"],
        },
    )
    assert forged.status_code == 422


def test_ac010_011_canonical_numeric_is_exact_and_publicly_consumed(api) -> None:
    client, sessions = api
    maximum = Decimal("999999999999999999.99")
    assert _canonical_numeric(Decimal("0.50")) == Decimal("0.50")
    assert _canonical_numeric(Decimal("0.00")) == Decimal("0.00")
    assert _canonical_numeric(maximum) == maximum
    assert _canonical_numeric(-maximum) == -maximum
    with pytest.raises(M05LedgerError, match="range"):
        _canonical_numeric(Decimal("1000000000000000000.00"))

    with sessions() as db:
        db.add(
            _intake(
                "canonical-half",
                1,
                provider="Canonical Provider",
                account="CANONICAL-HALF",
                total="0.50",
                contribution="0.50",
                severance="0.00",
            )
        )
        db.commit()
    _accept_upstream(client, 1, "canonical-half")
    candidate_row = next(
        row
        for row in client.get("/api/clients/1/m05/candidates").json()
        if row["intake_id"] == "canonical-half"
    )
    response = client.post(
        "/api/clients/1/m05/start",
        json={"candidate_id": candidate_row["candidate_id"], "confirm_currency_ils": True},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["source_total_value"] == "0.50"
    assert body["effective_total_value"] == "0.50"
    values = {row["component_kind"]: row for row in body["values"]}
    assert values["contribution_component"]["source_value"] == "0.50"
    assert values["severance_component"]["source_state"] == "recorded_zero"
    assert values["severance_component"]["source_value"] == "0.00"


def test_ac010_024_precedence_ignores_insertion_and_m02_timestamps(api) -> None:
    client, sessions = api
    provider = "Precedence Provider"
    account = "PRECEDENCE-ACCOUNT"
    with sessions() as db:
        db.add_all(
            [
                _intake(
                    "precedence-newer",
                    1,
                    provider=provider,
                    account=account,
                    total="101.00",
                    contribution="61.00",
                    severance="40.00",
                    statement_date=date(2026, 7, 2),
                ),
                _intake(
                    "precedence-older",
                    1,
                    provider=provider,
                    account=account,
                    total="100.00",
                    contribution="60.00",
                    severance="40.00",
                    statement_date=date(2026, 7, 1),
                ),
            ]
        )
        db.commit()
    _accept_upstream(client, 1, "precedence-newer")
    _accept_upstream(client, 1, "precedence-older")

    def selected() -> str:
        rows = [
            row
            for row in client.get("/api/clients/1/m05/candidates").json()
            if row["intake_id"] in {"precedence-newer", "precedence-older"}
        ]
        return next(row["intake_id"] for row in rows if row["authoritative_current"])

    assert selected() == "precedence-newer"
    with sessions() as db:
        older = db.get(M02IntakeRecord, "precedence-older")
        newer = db.get(M02IntakeRecord, "precedence-newer")
        older.created_at = datetime.now(timezone.utc) + timedelta(days=100)
        older.updated_at = datetime.now(timezone.utc) + timedelta(days=200)
        newer.created_at = datetime.now(timezone.utc) - timedelta(days=200)
        newer.updated_at = datetime.now(timezone.utc) - timedelta(days=100)
        db.commit()
    assert selected() == "precedence-newer"
