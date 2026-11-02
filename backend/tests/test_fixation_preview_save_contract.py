from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import date, datetime, timezone
from decimal import Decimal
import os
from pathlib import Path
import subprocess
import sys

import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

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


def _cbs(*, amount, grant_date, work_end_date, eligibility_date):
    base_date = grant_date or work_end_date
    request = CbsIndexationRequestEvidence(
        amount=Decimal(amount),
        resolved_base_date=base_date,
        base_date_source="grant_date" if grant_date is not None else "work_end_date",
        target_date=eligibility_date,
        calculation_timestamp=NOW,
    )
    return CbsIndexationSuccess(
        request=request,
        response=CbsIndexationResponseEvidence(
            raw_to_value=Decimal(amount) * Decimal("1.1"),
            from_index_period="01-2020",
            to_index_period="11-2026",
            from_index_value=Decimal("100"),
            to_index_value=Decimal("110"),
            base_year="synthetic",
            chaining_coefficient=Decimal("1.1"),
            change_percentage=Decimal("10"),
            missing_optional_fields=[],
            calculation_timestamp=NOW,
            response_status=200,
        ),
    )


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


def _preview(factory, payload, *, client_id: int = 1):
    with factory() as session:
        result = calculate_fixation_preview(
            payload,
            client_id=client_id,
            db_session=session,
            cbs_calculator=_cbs,
        )
    assert result.status == "success"
    assert result.preview_identity is not None
    return result


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


def test_real_postgresql_source_change_and_concurrent_same_preview(postgres_url):
    load_all_models()
    _migrate_fixation_schema(postgres_url)
    engine = create_engine(postgres_url, pool_size=6, max_overflow=2)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        with engine.connect() as connection:
            assert connection.scalar(text("SHOW server_version")).startswith("16.")
        with factory() as session:
            payload = _seed(session)

        stale_preview = _preview(factory, payload)
        with factory.begin() as writer:
            writer.get(Grant, "grant-1").nominal_amount = Decimal("2000.00")
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
            assert session.scalar(select(func.count()).select_from(FixationRun)) == 0

        current = _preview(factory, payload)

        def save_once():
            with factory() as session:
                return save_fixation_from_preview(
                    client_id=1,
                    input_data=payload,
                    preview_identity=current.preview_identity,
                    db_session=session,
                    cbs_calculator=_cbs,
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
    finally:
        engine.dispose()
