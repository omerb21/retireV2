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
    (seed.ClientProfile, seed.PROFILE_ID),
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

def test_stage6_factor_admission_fixture_preconditions_without_database(monkeypatch):
    """Exercise fixture construction and assert admission input facts, without writes."""
    seed.load_all_models()
    from datetime import date
    from decimal import Decimal

    class RecordingDB:
        def __init__(self):
            self.bind = SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))
            self.rows = {}
            self.added = []

        def execute(self, statement):
            return None

        def scalar(self, statement):
            return None

        def get(self, model, pk):
            return self.rows.get((model, pk))

        def add(self, row):
            self.added.append(row)

        def flush(self):
            for row in self.added:
                model = type(row)
                primary_key = model.__mapper__.primary_key[0].key
                self.rows[(model, getattr(row, primary_key))] = row

    db = RecordingDB()
    monkeypatch.setattr(seed, "component_balances", lambda db, product_id: {
        code: Decimal("200.00") if i == 1 else Decimal("0.00")
        for i, code in enumerate(seed.COMPONENT_CODES)
    })
    monkeypatch.setattr(seed, "product_response", lambda db, product: {
        "client_id": seed.CLIENT_ID,
        "conversion_components": [{}] * len(seed.COMPONENT_CODES),
    })
    monkeypatch.setattr(seed, "_source_evidence", lambda product, component: {
        "source_fingerprint": "a" * 64,
    })
    monkeypatch.setattr(seed, "ruleset_digest", lambda: "b" * 64)
    monkeypatch.setattr(seed, "_revision", lambda *args: None)
    seed.create_fixture(db)

    def single(model):
        values = [row for row in db.added if isinstance(row, model)]
        assert len(values) == 1
        return values[0]

    profile = single(seed.ClientProfile)
    product = single(seed.PensionProduct)
    election = single(seed.ScenarioDraftPensionElection)
    decision = single(seed.ScenarioDraftDecision)
    assert profile.client_profile_id == seed.PROFILE_ID
    assert profile.client_id == product.client_id == seed.CLIENT_ID
    assert profile.birth_date == date(1965, 5, 12) and profile.gender == "female"
    assert product.statement_date == date(2026, 9, 30)
    assert election.company_name == "מבטח סינתטי 78"
    assert election.option_name == "standard"
    assert election.coefficient_selection == "manual_review_required"
    assert election.scenario_id == decision.scenario_id == seed.SCENARIO_A
    assert election.decision_id == decision.decision_id == seed.DECISION_ID
    assert election.scenario_version == 1
    assert election.pension_start_date >= product.statement_date
    assert election.pension_start_date >= decision.effective_date
    assert decision.source_product_id == seed.PRODUCT_ID
    assert decision.source_component_id == seed.PENSION_COMPONENT_ID
    assert decision.amount == Decimal("40.00")
    assert decision.source_fingerprint_at_review == "a" * 64
    assert decision.ruleset_digest_at_review == "b" * 64
    assert len([r for r in db.added if isinstance(r, seed.PensionProductComponent)]) == len(seed.COMPONENT_CODES)
    assert not any("FactorAdmission" in type(r).__name__ or
                   "FixationProfessional" in type(r).__name__ for r in db.added)


def test_factor_write_is_not_called_by_fixture(monkeypatch):
    def must_not_be_called(*args, **kwargs):
        raise AssertionError("PROFESSIONAL_FACTOR_ADMISSION_MUST_BE_EXPLICIT")
    from app.services import scenario_pension_factor_admission_write_service as writes
    monkeypatch.setattr(writes, "append_authenticated_serializable_factor_admission",
                        must_not_be_called)
    # The record-construction test above exercises create_fixture; no factor
    # admission is imported, called or persisted by the staging fixture.
    assert "append_authenticated_serializable_factor_admission" not in (
        __import__("inspect").getsource(seed.create_fixture)
    )
