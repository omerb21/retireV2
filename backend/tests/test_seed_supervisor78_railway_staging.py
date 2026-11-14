"""Offline guard tests. Never connect to Railway or create live fixture records."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from scripts import seed_supervisor78_railway_staging as seed


def valid_env():
    return {
        "RAILWAY_PROJECT_ID": seed.PROJECT_ID,
        "RAILWAY_ENVIRONMENT_ID": seed.ENVIRONMENT_ID,
        "RAILWAY_ENVIRONMENT_NAME": "staging",
        "RAILWAY_SERVICE_ID": seed.APPLICATION_SERVICE_ID,
        "APP_ENV": "production",
        "AUTH_INGRESS_MODE": "railway_public_edge",
        "CRTISBA_APPLICATION_DB_ROLE": "retire_v2_staging_app",
        "DATABASE_URL": (
            "postgresql+psycopg2://fixture:test-only@"
            "retire-v2-postgres.railway.internal/retire_v2_staging"
        ),
    }


def test_exact_staging_target_is_accepted_without_connecting():
    seed.validate_target(valid_env())


@pytest.mark.parametrize("key,unsafe", [
    ("RAILWAY_PROJECT_ID", "different-project"),
    ("RAILWAY_ENVIRONMENT_ID", "production-id"),
    ("RAILWAY_ENVIRONMENT_NAME", "production"),
    ("RAILWAY_SERVICE_ID", seed.DATABASE_SERVICE_ID),
    ("APP_ENV", "test"),
    ("AUTH_INGRESS_MODE", "render_public_edge"),
    ("CRTISBA_APPLICATION_DB_ROLE", "production_writer"),
    ("DATABASE_URL", "postgresql://fixture:secret@localhost/retire_v2_staging"),
    ("DATABASE_URL", "postgresql://fixture:secret@prod.railway.internal/retire_v2_staging"),
    ("DATABASE_URL", "postgresql://fixture:secret@retire-v2-postgres.railway.internal/production"),
    ("DATABASE_URL", "sqlite:///retire_v2_staging"),
])
def test_wrong_target_rejected_before_factory_or_connection(key, unsafe):
    env = valid_env()
    env[key] = unsafe
    with pytest.raises(RuntimeError, match="SUPERVISOR78_RAILWAY_STAGING_TARGET_INVALID") as exc:
        seed.validate_target(env)
    assert "secret" not in str(exc.value)
    assert "test-only" not in str(exc.value)


def test_missing_target_is_rejected():
    with pytest.raises(RuntimeError, match="SUPERVISOR78_RAILWAY_STAGING_TARGET_INVALID"):
        seed.validate_target({})


class CollisionDB:
    bind = SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))

    def __init__(self, collision_model=None, collision_pk=None, fail_on_read=False):
        self.collision_model, self.collision_pk = collision_model, collision_pk
        self.actions = []
        self.fail_on_read = fail_on_read

    def execute(self, statement):
        self.actions.append("advisory-lock")

    def get(self, model, pk):
        self.actions.append(("read", model, pk))
        return object() if model is self.collision_model and pk == self.collision_pk else None

    def scalar(self, statement):
        self.actions.append("collision-query")
        return None

    def add(self, record):
        self.actions.append(("write", record))

    def flush(self):
        self.actions.append("flush")


@pytest.mark.parametrize("model,pk", [
    (seed.Client, seed.CLIENT_ID),
    (seed.PensionProduct, seed.PRODUCT_ID),
    (seed.ScenarioDraft, seed.SCENARIO_A),
    (seed.ScenarioDraft, seed.SCENARIO_B),
    (seed.ScenarioDraftDecision, seed.DECISION_ID),
    (seed.ScenarioDraftPensionElection, seed.ELECTION_ID),
    (seed.PensionProductComponent, seed.PENSION_COMPONENT_ID),
])
def test_preexisting_fixture_identifier_stops_before_any_write(model, pk):
    db = CollisionDB(model, pk)
    with pytest.raises(RuntimeError, match="SUPERVISOR78_FIXTURE_COLLISION"):
        seed.create_fixture(db)
    assert not any(isinstance(x, tuple) and x[0] == "write" for x in db.actions)


def test_non_postgres_does_not_start_transactional_fixture():
    db = CollisionDB()
    db.bind.dialect.name = "sqlite"
    with pytest.raises(RuntimeError, match="SUPERVISOR78_POSTGRESQL_REQUIRED"):
        seed.create_fixture(db)
    assert db.actions == []


def test_failure_rolls_back_one_transaction(monkeypatch):
    events = []

    class Transaction:
        def __enter__(self):
            events.append("begin")
            return object()

        def __exit__(self, exc_type, exc, tb):
            events.append("rollback" if exc_type else "commit")
            return False

    class Factory:
        def begin(self):
            return Transaction()

    monkeypatch.setattr(seed, "load_all_models", lambda: None)

    def fail_late(db):
        events.append("partial-work")
        raise RuntimeError("synthetic failure")

    monkeypatch.setattr(seed, "create_fixture", fail_late)
    with pytest.raises(RuntimeError, match="synthetic failure"):
        seed.run(valid_env(), Factory())
    assert events == ["begin", "partial-work", "rollback"]


def test_guard_rejects_unsafe_target_without_entering_transaction():
    class Factory:
        def begin(self):
            raise AssertionError("MUST NOT START A TRANSACTION")

    with pytest.raises(RuntimeError, match="SUPERVISOR78_RAILWAY_STAGING_TARGET_INVALID"):
        seed.run({"RAILWAY_ENVIRONMENT_NAME": "production"}, Factory())
