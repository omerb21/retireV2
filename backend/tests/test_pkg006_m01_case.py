from __future__ import annotations

import os
import subprocess
from collections.abc import Generator
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base, load_all_models
from app.db.session import get_db
from app.main import app
from app.models.client import Client
from app.models.client_profile import ClientProfile
from app.models.employment_record import EmploymentRecord


PARENT_REVISION = "a9c4e7f2b615"
PKG006_REVISION = "f3a7c9d2e610"


def _backend_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _run_alembic(db_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    return subprocess.run(
        ["alembic", *args],
        cwd=_backend_root(),
        env=env,
        capture_output=True,
        check=True,
        text=True,
    )


@pytest.fixture
def api(
    tmp_path: Path,
) -> Generator[tuple[TestClient, sessionmaker[Session]], None, None]:
    load_all_models()
    engine = create_engine(f"sqlite:///{tmp_path / 'pkg006.db'}")
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, expire_on_commit=False)
    with session_local() as session:
        session.add_all(
            [
                Client(
                    client_id=1,
                    display_name="Client One",
                    id_number="001",
                    birth_date=None,
                    status=None,
                ),
                Client(
                    client_id=2,
                    display_name="Client Two",
                    id_number="002",
                    birth_date=None,
                    status="active",
                ),
            ]
        )
        session.commit()

    def override_get_db():
        with session_local() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app), session_local
    finally:
        app.dependency_overrides.pop(get_db, None)


def _complete_payload(
    *,
    id_number: str = "001",
    planned_age: int | None = 67,
    planned_date: str | None = None,
) -> dict:
    return {
        "display_name": " Client One ",
        "id_number": id_number,
        "birth_date": "1980-01-01",
        "gender": " female ",
        "employment_status": "salaried_employee",
        "planned_retirement_age": planned_age,
        "planned_retirement_date": planned_date,
    }


def _complete_client(client: TestClient) -> dict:
    response = client.put("/api/clients/1/case", json=_complete_payload())
    assert response.status_code == 200, response.text
    return response.json()


def test_case_overview_derives_legacy_draft_and_missing_fields(
    api: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = api

    first = client.get("/api/clients/1")
    second = client.get("/api/clients/2")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["m01_case"] == {
        "client_id": 1,
        "display_name": "Client One",
        "id_number": "001",
        "birth_date": None,
        "gender": None,
        "employment_status": None,
        "planned_retirement_date": None,
        "planned_retirement_age": None,
        "lifecycle_status": "draft",
        "completeness": {
            "status": "incomplete",
            "missing_field_ids": [
                "birth_date",
                "gender",
                "employment_status",
                "planned_retirement",
            ],
            "conflicting_field_ids": [],
        },
        "allowed_lifecycle_targets": [],
        "updated_at": first.json()["m01_case"]["updated_at"],
    }
    assert second.json()["m01_case"]["lifecycle_status"] == "draft"


def test_minimum_facts_update_is_normalized_complete_and_does_not_touch_employment_records(
    api: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, session_local = api
    with session_local() as session:
        session.add(
            EmploymentRecord(
                employment_record_id="EMP-1",
                client_id=1,
                employer_name="Existing Employer",
                work_start_date=date(2020, 1, 1),
                work_end_date=None,
                is_current=True,
            )
        )
        session.commit()

    body = _complete_client(client)

    assert body["display_name"] == "Client One"
    assert body["id_number"] == "001"
    assert body["gender"] == "female"
    assert body["employment_status"] == "salaried_employee"
    assert body["planned_retirement_age"] == 67
    assert body["planned_retirement_date"] is None
    assert body["completeness"] == {
        "status": "complete",
        "missing_field_ids": [],
        "conflicting_field_ids": [],
    }
    assert body["allowed_lifecycle_targets"] == ["intake"]

    with session_local() as session:
        employment = session.get(EmploymentRecord, "EMP-1")
        assert employment is not None
        assert employment.employer_name == "Existing Employer"
        assert employment.is_current is True


@pytest.mark.parametrize(
    ("payload_update", "expected_status"),
    [
        ({"employment_status": "free text"}, 422),
        ({"planned_retirement_age": 17}, 422),
        ({"planned_retirement_age": 121}, 422),
        ({"birth_date": "2030-01-01"}, 422),
        ({"planned_retirement_age": None, "planned_retirement_date": "1979-12-31"}, 422),
    ],
)
def test_minimum_fact_validation(
    api: tuple[TestClient, sessionmaker[Session]],
    payload_update: dict,
    expected_status: int,
) -> None:
    client, _ = api
    payload = _complete_payload()
    payload.update(payload_update)

    response = client.put("/api/clients/1/case", json=payload)

    assert response.status_code == expected_status


def test_planned_retirement_conflict_rejects_atomically_and_atomic_switch_succeeds(
    api: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, session_local = api
    _complete_client(client)
    conflicting = _complete_payload(planned_age=67, planned_date="2047-01-01")

    rejected = client.put("/api/clients/1/case", json=conflicting)

    assert rejected.status_code == 422
    assert rejected.json()["detail"] == {
        "code": "M01_PLANNED_RETIREMENT_CONFLICT",
        "message": "planned_retirement_age and planned_retirement_date are mutually exclusive",
        "conflicting_field_ids": [
            "planned_retirement_age",
            "planned_retirement_date",
        ],
    }
    with session_local() as session:
        persisted = session.get(Client, 1)
        assert persisted is not None
        assert persisted.planned_retirement_age == 67
        assert persisted.planned_retirement_date is None

    switched = client.put(
        "/api/clients/1/case",
        json=_complete_payload(planned_age=None, planned_date="2047-01-01"),
    )
    assert switched.status_code == 200
    assert switched.json()["planned_retirement_age"] is None
    assert switched.json()["planned_retirement_date"] == "2047-01-01"


def test_duplicate_identifier_is_safe_and_has_no_partial_write(
    api: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, session_local = api

    response = client.put("/api/clients/1/case", json=_complete_payload(id_number="002"))

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "DUPLICATE_CLIENT_IDENTIFIER"
    with session_local() as session:
        persisted = session.get(Client, 1)
        assert persisted is not None
        assert persisted.display_name == "Client One"
        assert persisted.id_number == "001"
        assert persisted.birth_date is None
        assert persisted.employment_status is None
        assert session.scalar(
            text("SELECT COUNT(*) FROM client_profiles WHERE client_id = 1")
        ) == 0


@pytest.mark.parametrize(
    ("current", "target"),
    [
        ("draft", "intake"),
        ("intake", "analysis"),
        ("intake", "draft"),
        ("analysis", "review"),
        ("analysis", "intake"),
        ("review", "delivered"),
        ("review", "analysis"),
        ("delivered", "archived"),
        ("delivered", "review"),
        ("archived", "delivered"),
    ],
)
def test_every_allowed_lifecycle_transition(
    api: tuple[TestClient, sessionmaker[Session]],
    current: str,
    target: str,
) -> None:
    client, session_local = api
    _complete_client(client)
    with session_local() as session:
        persisted = session.get(Client, 1)
        assert persisted is not None
        persisted.status = current
        session.commit()

    response = client.post(
        "/api/clients/1/case/lifecycle",
        json={"target_status": target},
    )

    assert response.status_code == 200, response.text
    assert response.json()["lifecycle_status"] == target


@pytest.mark.parametrize(
    ("current", "target"),
    [
        ("draft", "draft"),
        ("draft", "analysis"),
        ("intake", "review"),
        ("analysis", "draft"),
        ("review", "archived"),
        ("archived", "draft"),
    ],
)
def test_invalid_same_state_and_skipped_transitions_are_rejected(
    api: tuple[TestClient, sessionmaker[Session]],
    current: str,
    target: str,
) -> None:
    client, session_local = api
    _complete_client(client)
    with session_local() as session:
        persisted = session.get(Client, 1)
        assert persisted is not None
        persisted.status = current
        session.commit()

    response = client.post(
        "/api/clients/1/case/lifecycle",
        json={"target_status": target},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "invalid_lifecycle_transition"
    with session_local() as session:
        persisted = session.get(Client, 1)
        assert persisted is not None
        assert persisted.status == current


def test_incomplete_forward_transition_reports_missing_fields_and_backward_is_allowed(
    api: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, session_local = api

    blocked = client.post(
        "/api/clients/1/case/lifecycle",
        json={"target_status": "intake"},
    )
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["code"] == "case_incomplete"
    assert blocked.json()["detail"]["missing_field_ids"] == [
        "birth_date",
        "gender",
        "employment_status",
        "planned_retirement",
    ]

    with session_local() as session:
        persisted = session.get(Client, 1)
        assert persisted is not None
        persisted.status = "analysis"
        session.commit()
    backward = client.post(
        "/api/clients/1/case/lifecycle",
        json={"target_status": "intake"},
    )
    assert backward.status_code == 200
    assert backward.json()["lifecycle_status"] == "intake"


def test_archived_is_read_only_reopens_and_unsupported_status_fails_closed(
    api: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, session_local = api
    _complete_client(client)
    with session_local() as session:
        persisted = session.get(Client, 1)
        assert persisted is not None
        persisted.status = "archived"
        session.commit()

    edit = client.put("/api/clients/1/case", json=_complete_payload())
    assert edit.status_code == 409
    assert edit.json()["detail"]["code"] == "archived_case_read_only"

    reopened = client.post(
        "/api/clients/1/case/lifecycle",
        json={"target_status": "delivered"},
    )
    assert reopened.status_code == 200
    assert reopened.json()["lifecycle_status"] == "delivered"

    with session_local() as session:
        persisted = session.get(Client, 1)
        assert persisted is not None
        persisted.status = "mystery"
        session.commit()
    unsupported = client.get("/api/clients/1")
    assert unsupported.status_code == 409
    assert unsupported.json()["detail"]["code"] == "unsupported_client_status"


def test_missing_client_case_routes_do_not_disclose_other_client_data(
    api: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = api

    update = client.put("/api/clients/999/case", json=_complete_payload())
    transition = client.post(
        "/api/clients/999/case/lifecycle",
        json={"target_status": "intake"},
    )

    assert update.status_code == 404
    assert transition.status_code == 404
    assert update.json()["detail"]["code"] == "CLIENT_NOT_FOUND"
    assert transition.json()["detail"]["code"] == "CLIENT_NOT_FOUND"
    assert "Client Two" not in update.text
    assert "Client Two" not in transition.text


def test_pkg006_migration_adds_only_nullable_fields_without_backfill_and_downgrades(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "pkg006-migration.db"
    _run_alembic(db_path, "upgrade", PARENT_REVISION)
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO clients
                    (client_id, display_name, id_number, birth_date, status)
                VALUES
                    (77, 'Legacy Client', '00077', '1970-01-01', 'active')
                """
            )
        )
    engine.dispose()

    _run_alembic(db_path, "upgrade", PKG006_REVISION)
    upgraded_engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    upgraded_inspector = inspect(upgraded_engine)
    columns = {
        column["name"]: column for column in upgraded_inspector.get_columns("clients")
    }
    assert set(columns) >= {
        "employment_status",
        "planned_retirement_date",
        "planned_retirement_age",
    }
    assert columns["employment_status"]["nullable"] is True
    assert columns["planned_retirement_date"]["nullable"] is True
    assert columns["planned_retirement_age"]["nullable"] is True
    with upgraded_engine.connect() as connection:
        row = connection.execute(
            text(
                """
                SELECT status, employment_status, planned_retirement_date,
                       planned_retirement_age
                FROM clients WHERE client_id = 77
                """
            )
        ).one()
        assert tuple(row) == ("active", None, None, None)
    upgraded_engine.dispose()

    _run_alembic(db_path, "downgrade", PARENT_REVISION)
    downgraded_engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    downgraded_columns = {
        column["name"] for column in inspect(downgraded_engine).get_columns("clients")
    }
    assert "employment_status" not in downgraded_columns
    assert "planned_retirement_date" not in downgraded_columns
    assert "planned_retirement_age" not in downgraded_columns
    with downgraded_engine.connect() as connection:
        assert connection.scalar(
            text("SELECT COUNT(*) FROM clients WHERE client_id = 77 AND status = 'active'")
        ) == 1
    downgraded_engine.dispose()
