from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from itertools import count
import os
from pathlib import Path
import subprocess
import sys
from threading import Lock

import pytest
from sqlalchemy import create_engine, event, func, select, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session, sessionmaker

import app.services.fixation_service as fixation_service
from app.db.base import Base, load_all_models
from app.models.client import Client
from app.models.fixation_run import FixationRun
from app.models.grant import Grant
from app.schemas.cbs_indexation import (
    CbsIndexationRequestEvidence,
    CbsIndexationResponseEvidence,
    CbsIndexationSuccess,
)
from app.services.fixation_service import (
    FixationPreviewConflictError,
    _is_fixation_run_identity_conflict,
    calculate_fixation_preview,
    save_fixation_from_preview,
)
from tests.pkg004d_test_support import resolver_payload, seed_eligibility_revision
from test_pkg001_admissible_foundation import _legacy_payload
from test_recovery_migration_postgresql import postgres_url


NOW = datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc)
BACKEND = Path(__file__).resolve().parents[1]
FIXATION_SCHEMA_REVISION = "f9a1c3e5b702"


def _migrate_fixation_schema(database_url: str) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "upgrade",
            FIXATION_SCHEMA_REVISION,
        ],
        cwd=BACKEND,
        env={
            **os.environ,
            "DATABASE_URL": database_url,
            "PYTHONIOENCODING": "utf-8",
        },
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=180,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def _cbs(
    *,
    amount,
    grant_date,
    work_end_date,
    eligibility_date,
    calculation_timestamp=NOW,
    index_factor=Decimal("1.1"),
):
    base_date = grant_date or work_end_date
    request = CbsIndexationRequestEvidence(
        amount=Decimal(amount),
        resolved_base_date=base_date,
        base_date_source="grant_date" if grant_date is not None else "work_end_date",
        target_date=eligibility_date,
        calculation_timestamp=calculation_timestamp,
    )
    return CbsIndexationSuccess(
        request=request,
        response=CbsIndexationResponseEvidence(
            raw_to_value=Decimal(amount) * index_factor,
            from_index_period="01-2020",
            to_index_period="11-2026",
            from_index_value=Decimal("100"),
            to_index_value=Decimal("100") * index_factor,
            base_year="synthetic",
            chaining_coefficient=index_factor,
            change_percentage=(index_factor - Decimal("1")) * Decimal("100"),
            missing_optional_fields=[],
            calculation_timestamp=calculation_timestamp,
            response_status=200,
        ),
    )


def _varying_timestamp_cbs(*, index_factor=Decimal("1.1")):
    sequence = count()
    lock = Lock()

    def calculate(**kwargs):
        with lock:
            timestamp = NOW + timedelta(microseconds=next(sequence) + 1)
        return _cbs(
            **kwargs,
            calculation_timestamp=timestamp,
            index_factor=index_factor,
        )

    return calculate


def _seed(session: Session, *, client_id: int = 1) -> dict:
    session.add(
        Client(
            client_id=client_id,
            display_name=f"Synthetic fixation {client_id}",
            id_number=f"fixation-preview-{client_id}",
        )
    )
    session.add(
        Grant(
            grant_id=f"grant-{client_id}",
            client_id=client_id,
            employer_name="Synthetic employer",
            employer_withholding_file_number="SYNTHETIC-WF",
            nominal_amount=Decimal("1000.00"),
            indexed_amount=None,
            grant_date=date(2020, 2, 3),
            work_start_date=date(2010, 1, 1),
            work_end_date=date(2020, 1, 31),
        )
    )
    session.flush()
    revision_id, _ = seed_eligibility_revision(
        session,
        client_id=client_id,
        eligibility_dates=("2026-01-01",),
    )
    session.commit()
    payload = resolver_payload(
        _legacy_payload(client_id=client_id),
        revision_id=revision_id,
    )
    payload["grants_collection_state"] = "confirmed_none"
    payload["grants"] = []
    payload["actual_capitalizations_collection_state"] = "confirmed_none"
    payload["actual_capitalizations"] = []
    return payload


def _preview(factory, payload, *, client_id: int = 1, cbs_calculator=_cbs):
    with factory() as session:
        result = calculate_fixation_preview(
            payload,
            client_id=client_id,
            db_session=session,
            cbs_calculator=cbs_calculator,
        )
    assert result.status == "success"
    assert result.preview_identity is not None
    return result


def test_preview_identity_ignores_cbs_timestamp_but_binds_indexation_result(tmp_path):
    load_all_models()
    engine = create_engine(f"sqlite:///{tmp_path / 'fixation-cbs-identity.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        payload = _seed(session)

    timestamp_varying_cbs = _varying_timestamp_cbs()
    preview = _preview(
        factory,
        payload,
        cbs_calculator=timestamp_varying_cbs,
    )
    with factory() as session:
        run_id = save_fixation_from_preview(
            client_id=1,
            input_data=payload,
            preview_identity=preview.preview_identity,
            db_session=session,
            cbs_calculator=timestamp_varying_cbs,
        )

    changed_result_preview = _preview(
        factory,
        payload,
        cbs_calculator=_varying_timestamp_cbs(index_factor=Decimal("1.2")),
    )
    assert changed_result_preview.preview_identity != preview.preview_identity
    with factory() as session:
        with pytest.raises(FixationPreviewConflictError) as caught:
            save_fixation_from_preview(
                client_id=1,
                input_data=payload,
                preview_identity=preview.preview_identity,
                db_session=session,
                cbs_calculator=_varying_timestamp_cbs(index_factor=Decimal("1.2")),
            )
        assert caught.value.code == "FIXATION_PREVIEW_STALE"
        assert session.scalar(select(func.count()).select_from(FixationRun)) == 1
        run = session.get(FixationRun, run_id)
        assert run is not None and run.is_latest is True
        assert run.fixation_result.result_payload["monthly_exempt_pension"] == (
            preview.monthly_exempt_pension
        )
        saved_grant = run.fixation_input_snapshot.input_payload["grants"][0]
        assert saved_grant["cbs_request_evidence"]["calculation_timestamp"]
        assert saved_grant["cbs_response_evidence"]["calculation_timestamp"]


def test_psycopg2_unique_preview_identity_conflict_is_classified_by_pgcode():
    class Diagnostic:
        constraint_name = "fixation_runs_fixation_run_id_key"

    class Psycopg2UniqueViolation:
        pgcode = "23505"
        diag = Diagnostic()

    conflict = IntegrityError("INSERT", {}, Psycopg2UniqueViolation())
    assert _is_fixation_run_identity_conflict(
        conflict,
        dialect_name="postgresql",
    )

    Psycopg2UniqueViolation.diag.constraint_name = "unrelated_unique_key"
    unrelated = IntegrityError("INSERT", {}, Psycopg2UniqueViolation())
    assert not _is_fixation_run_identity_conflict(
        unrelated,
        dialect_name="postgresql",
    )


def test_real_postgresql_40001_retry_uses_new_transaction_and_revalidates(
    postgres_url,
    monkeypatch,
):
    """Controlled SQLSTATE injection over a real PostgreSQL transaction owner.

    Real concurrent saves are covered separately below.  This oracle isolates
    the retry contract so the rollback, new transaction, and repeated source /
    preview validation are directly observable rather than inferred from the
    final idempotent result.
    """

    load_all_models()
    _migrate_fixation_schema(postgres_url)
    engine = create_engine(postgres_url)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        with engine.connect() as connection:
            server_version = connection.scalar(text("SHOW server_version"))
            assert server_version.startswith("16.")
        with factory() as session:
            payload = _seed(session)
        preview = _preview(factory, payload, cbs_calculator=_varying_timestamp_cbs())

        original_prepare = fixation_service._prepare_fixation
        original_run = fixation_service.run_fixation
        prepare_observations: list[tuple[int, str | None]] = []
        run_transaction_ids: list[int] = []

        def tracing_prepare(*args, **kwargs):
            session = kwargs["db_session"]
            transaction_id = session.scalar(text("SELECT txid_current()"))
            prepared = original_prepare(*args, **kwargs)
            prepare_observations.append(
                (transaction_id, fixation_service._preview_identity(prepared))
            )
            return prepared

        class SerializationFailure:
            pgcode = "40001"

        def fail_first_run(*args, **kwargs):
            session = kwargs["db_session"]
            run_transaction_ids.append(session.scalar(text("SELECT txid_current()")))
            if len(run_transaction_ids) == 1:
                raise OperationalError("INSERT", {}, SerializationFailure())
            return original_run(*args, **kwargs)

        monkeypatch.setattr(fixation_service, "_prepare_fixation", tracing_prepare)
        monkeypatch.setattr(fixation_service, "run_fixation", fail_first_run)

        with factory() as session:
            rollback_events: list[bool] = []
            event.listen(
                session,
                "after_rollback",
                lambda _session: rollback_events.append(True),
            )
            run_id = save_fixation_from_preview(
                client_id=1,
                input_data=payload,
                preview_identity=preview.preview_identity,
                db_session=session,
                cbs_calculator=_varying_timestamp_cbs(),
            )

        assert rollback_events == [True]
        assert len(prepare_observations) == 2
        assert len(run_transaction_ids) == 2
        assert prepare_observations[0][0] != prepare_observations[1][0]
        assert run_transaction_ids[0] != run_transaction_ids[1]
        assert [identity for _, identity in prepare_observations] == [
            preview.preview_identity,
            preview.preview_identity,
        ]
        with factory() as session:
            runs = session.scalars(select(FixationRun)).all()
            assert len(runs) == 1
            assert runs[0].id == run_id
            assert runs[0].fixation_run_id == preview.preview_identity
            assert runs[0].is_latest is True

        print(
            "PG40001_EVIDENCE",
            f"server={server_version}",
            f"rollback_events={len(rollback_events)}",
            f"prepare_txids={[item[0] for item in prepare_observations]}",
            f"run_txids={run_transaction_ids}",
            f"preview_revalidated={len(prepare_observations)}",
            f"run_id={run_id}",
            sep="|",
        )
    finally:
        engine.dispose()


def test_preview_identity_binds_authoritative_sources_and_save_is_idempotent(tmp_path):
    load_all_models()
    engine = create_engine(f"sqlite:///{tmp_path / 'fixation-preview.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        payload = _seed(session)
    with factory() as session:
        other_payload = _seed(session, client_id=2)

    preview = _preview(factory, payload)
    with factory() as session:
        with pytest.raises(FixationPreviewConflictError):
            save_fixation_from_preview(
                client_id=2,
                input_data=other_payload,
                preview_identity=preview.preview_identity,
                db_session=session,
                cbs_calculator=_cbs,
            )
    tampered = deepcopy(payload)
    tampered["parameter_set"]["values"]["monthly_cap"] = 1001
    with factory() as session:
        with pytest.raises(FixationPreviewConflictError):
            save_fixation_from_preview(
                client_id=1,
                input_data=tampered,
                preview_identity=preview.preview_identity,
                db_session=session,
                cbs_calculator=_cbs,
            )
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(FixationRun)) == 0

    with factory() as session:
        run_id = save_fixation_from_preview(
            client_id=1,
            input_data=payload,
            preview_identity=preview.preview_identity,
            db_session=session,
            cbs_calculator=_cbs,
        )
    with factory() as session:
        repeated = save_fixation_from_preview(
            client_id=1,
            input_data=payload,
            preview_identity=preview.preview_identity,
            db_session=session,
            cbs_calculator=_cbs,
        )
        assert repeated == run_id
        assert session.scalar(select(func.count()).select_from(FixationRun)) == 1
        run = session.get(FixationRun, run_id)
        assert run is not None and run.status == "success" and run.is_latest is True
        assert run.fixation_run_id == preview.preview_identity
        assert run.fixation_result.result_payload["monthly_exempt_pension"] == (
            preview.monthly_exempt_pension
        )

    stale_preview = _preview(factory, payload)
    with factory.begin() as writer:
        grant = writer.get(Grant, "grant-1")
        grant.nominal_amount = Decimal("2000.00")
    with factory() as session:
        with pytest.raises(FixationPreviewConflictError) as caught:
            save_fixation_from_preview(
                client_id=1,
                input_data=payload,
                preview_identity=stale_preview.preview_identity,
                db_session=session,
                cbs_calculator=_cbs,
            )
        assert caught.value.code == "FIXATION_PREVIEW_STALE"
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(FixationRun)) == 1
        assert session.get(FixationRun, run_id).is_latest is True

    with factory() as session:
        with pytest.raises(FixationPreviewConflictError) as caught:
            save_fixation_from_preview(
                client_id=1,
                input_data=payload,
                preview_identity=None,
                db_session=session,
                cbs_calculator=_cbs,
            )
        assert caught.value.code == "FIXATION_PREVIEW_IDENTITY_REQUIRED"


def test_real_postgresql_source_change_and_concurrent_same_preview(
    postgres_url,
    monkeypatch,
):
    load_all_models()
    _migrate_fixation_schema(postgres_url)
    engine = create_engine(postgres_url, pool_size=6, max_overflow=2)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        with engine.connect() as connection:
            server_version = connection.scalar(text("SHOW server_version"))
            assert server_version.startswith("16.")
        with factory() as session:
            payload = _seed(session)

        timestamp_varying_cbs = _varying_timestamp_cbs()
        stale_preview = _preview(
            factory,
            payload,
            cbs_calculator=timestamp_varying_cbs,
        )
        with factory.begin() as writer:
            writer.get(Grant, "grant-1").nominal_amount = Decimal("2000.00")
        with factory() as session:
            with pytest.raises(FixationPreviewConflictError) as caught:
                save_fixation_from_preview(
                    client_id=1,
                    input_data=payload,
                    preview_identity=stale_preview.preview_identity,
                    db_session=session,
                    cbs_calculator=timestamp_varying_cbs,
                )
            assert caught.value.code == "FIXATION_PREVIEW_STALE"
        with factory() as session:
            assert session.scalar(select(func.count()).select_from(FixationRun)) == 0

        current = _preview(
            factory,
            payload,
            cbs_calculator=timestamp_varying_cbs,
        )

        observed_conflicts: list[str] = []
        conflict_lock = Lock()
        original_serialization_classifier = (
            fixation_service._is_fixation_save_serialization_failure
        )
        original_unique_classifier = fixation_service._is_fixation_run_identity_conflict

        def trace_serialization(exc, *, dialect_name):
            matched = original_serialization_classifier(
                exc,
                dialect_name=dialect_name,
            )
            if matched:
                with conflict_lock:
                    observed_conflicts.append(exc.orig.pgcode)
            return matched

        def trace_unique(exc, *, dialect_name):
            matched = original_unique_classifier(exc, dialect_name=dialect_name)
            if matched:
                with conflict_lock:
                    observed_conflicts.append(exc.orig.pgcode)
            return matched

        monkeypatch.setattr(
            fixation_service,
            "_is_fixation_save_serialization_failure",
            trace_serialization,
        )
        monkeypatch.setattr(
            fixation_service,
            "_is_fixation_run_identity_conflict",
            trace_unique,
        )

        def save_once():
            with factory() as session:
                return save_fixation_from_preview(
                    client_id=1,
                    input_data=payload,
                    preview_identity=current.preview_identity,
                    db_session=session,
                    cbs_calculator=timestamp_varying_cbs,
                )

        with ThreadPoolExecutor(max_workers=2) as pool:
            run_ids = list(pool.map(lambda _index: save_once(), range(2)))
        assert run_ids[0] == run_ids[1]
        with factory() as session:
            runs = session.scalars(select(FixationRun)).all()
            assert len(runs) == 1
            assert runs[0].id == run_ids[0]
            assert runs[0].is_latest is True
            assert runs[0].fixation_run_id == current.preview_identity

            duplicate = FixationRun(
                fixation_run_id=current.preview_identity,
                client_id=1,
                calculation_version="constraint-evidence",
                status="success",
                is_latest=False,
            )
            session.add(duplicate)
            with pytest.raises(IntegrityError) as caught:
                session.flush()
            assert caught.value.orig.pgcode == "23505"
            assert (
                caught.value.orig.diag.constraint_name
                == "fixation_runs_fixation_run_id_key"
            )
            assert _is_fixation_run_identity_conflict(
                caught.value,
                dialect_name="postgresql",
            )
            session.rollback()

        assert observed_conflicts
        assert set(observed_conflicts).issubset({"40001", "23505"})
        print(
            "PG_CONCURRENCY_EVIDENCE",
            f"server={server_version}",
            f"observed_service_conflicts={observed_conflicts}",
            f"run_ids={run_ids}",
            "run_count=1",
            "is_latest=true",
            "real_constraint_sqlstate=23505",
            "real_constraint=fixation_runs_fixation_run_id_key",
            sep="|",
        )
    finally:
        engine.dispose()
