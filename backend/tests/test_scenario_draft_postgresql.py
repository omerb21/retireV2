"""Opt-in PostgreSQL 16 evidence using an isolated disposable database only."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
import json
import os
from pathlib import Path
import subprocess
import sys

from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker

from app.db.base import load_all_models
from app.models.client import Client
from app.models.scenario_draft import ScenarioDraftDecision, ScenarioDraftRevision
from app.models.scenario_pension_price_basis import ScenarioPensionPriceBasis
from app.schemas.scenario_draft import DraftDecisionWrite, DraftReplace
from app.services import scenario_draft_service as service
from test_recovery_migration_postgresql import postgres_url

BACKEND = Path(__file__).resolve().parents[1]
APPLICATION_ROLE = "scenario_draft_test_app"


def test_scenario_decision_column_update_migration_is_reversible(postgres_url):
    engine = create_engine(postgres_url)
    environment = {
        **os.environ,
        "DATABASE_URL": postgres_url,
        "CRTISBA_APPLICATION_DB_ROLE": APPLICATION_ROLE,
        "PYTHONIOENCODING": "utf-8",
    }
    try:
        with engine.begin() as connection:
            connection.execute(text(f"CREATE ROLE {APPLICATION_ROLE} NOLOGIN"))

        def migrate(*arguments):
            completed = subprocess.run(
                [sys.executable, "-m", "alembic", *arguments],
                cwd=BACKEND, env=environment, capture_output=True, text=True,
                encoding="utf-8", timeout=180,
            )
            assert completed.returncode == 0, completed.stdout + completed.stderr

        def privileges():
            with engine.connect() as connection:
                connection.execute(text(f"SET ROLE {APPLICATION_ROLE}"))
                result = {
                    "amount_update": connection.scalar(text(
                        "SELECT has_column_privilege(current_user, "
                        "'scenario_draft_decisions', 'amount', 'UPDATE')"
                    )),
                    "identity_update": connection.scalar(text(
                        "SELECT has_column_privilege(current_user, "
                        "'scenario_draft_decisions', 'decision_id', 'UPDATE')"
                    )),
                    "select": connection.scalar(text(
                        "SELECT has_table_privilege(current_user, "
                        "'scenario_draft_decisions', 'SELECT')"
                    )),
                    "insert": connection.scalar(text(
                        "SELECT has_table_privilege(current_user, "
                        "'scenario_draft_decisions', 'INSERT')"
                    )),
                    "delete": connection.scalar(text(
                        "SELECT has_table_privilege(current_user, "
                        "'scenario_draft_decisions', 'DELETE')"
                    )),
                }
                connection.rollback()
                return result

        migrate("upgrade", "d277e1a6f003")
        before = privileges()
        assert before == {
            "amount_update": False, "identity_update": False,
            "select": True, "insert": True, "delete": True,
        }
        migrate("upgrade", "f330a1c2d3e4")
        after_upgrade = privileges()
        assert after_upgrade == {
            "amount_update": True, "identity_update": False,
            "select": True, "insert": True, "delete": True,
        }
        migrate("downgrade", "d277e1a6f003")
        after_downgrade = privileges()
        assert after_downgrade == before
    finally:
        engine.dispose()


def test_postgresql_draft_migration_and_cas(postgres_url):
    # postgres_url fixture creates a fresh disposable PostgreSQL 16 instance.
    # Never read the caller's DATABASE_URL; only the fixture URL is used.
    load_all_models()
    engine = create_engine(postgres_url)
    try:
        with engine.begin() as connection:
            connection.execute(text(f"CREATE ROLE {APPLICATION_ROLE} NOLOGIN"))
        completed = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "f330a1c2d3e4"],
            cwd=BACKEND,
            env={**os.environ, "DATABASE_URL": postgres_url,
                 "CRTISBA_APPLICATION_DB_ROLE": APPLICATION_ROLE,
                 "PYTHONIOENCODING": "utf-8"},
            capture_output=True, text=True, encoding="utf-8", timeout=180,
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr
        inspector = inspect(engine)
        assert {"scenario_drafts", "scenario_draft_decisions", "scenario_draft_revisions",
                "scenario_draft_pension_elections"} <= set(inspector.get_table_names())
        amount_type = str(next(
            column["type"] for column in inspector.get_columns("scenario_draft_decisions")
            if column["name"] == "amount"
        )).upper()
        assert "NUMERIC(20, 2)" in amount_type

        with engine.connect() as connection:
            connection.execute(text(f"SET ROLE {APPLICATION_ROLE}"))
            for table in ("scenario_drafts", "scenario_draft_decisions", "scenario_draft_revisions"):
                assert connection.scalar(text(
                    "SELECT has_table_privilege(current_user, :tbl, 'SELECT')"
                ), {"tbl": table})
            assert not connection.scalar(text(
                "SELECT has_table_privilege(current_user, 'scenario_draft_revisions', 'UPDATE')"
            ))
            assert not connection.scalar(text(
                "SELECT has_table_privilege(current_user, 'scenario_draft_revisions', 'DELETE')"
            ))
            for column in (
                "amount", "action", "effective_date", "validation_state",
                "product_version_at_review", "source_fingerprint_at_review",
                "ruleset_digest_at_review", "permission_preview_id_at_review",
            ):
                assert connection.scalar(text(
                    "SELECT has_column_privilege(current_user, "
                    "'scenario_draft_decisions', :column, 'UPDATE')"
                ), {"column": column})
            for column in (
                "decision_id", "scenario_id", "source_product_id",
                "source_component_id", "component_code",
            ):
                assert not connection.scalar(text(
                    "SELECT has_column_privilege(current_user, "
                    "'scenario_draft_decisions', :column, 'UPDATE')"
                ), {"column": column})
            assert not connection.scalar(text(
                "SELECT has_table_privilege(current_user, "
                "'scenario_draft_decisions', 'UPDATE')"
            ))
            connection.rollback()
        factory = sessionmaker(bind=engine, autoflush=False)
        with factory.begin() as db:
            db.add(Client(client_id=1, display_name="Synthetic A", id_number="scenario-pg-a"))
            db.add(Client(client_id=2, display_name="Synthetic B", id_number="scenario-pg-b"))
        # Perform real DML as the restricted runtime role, not just privilege introspection.
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                connection.execute(text(f"SET LOCAL ROLE {APPLICATION_ROLE}"))
                connection.execute(text("""
                    INSERT INTO scenario_drafts
                    (scenario_id, client_id, name, status, version, created_by, updated_by)
                    VALUES ('role-proof', 1, 'proof', 'draft', 1, 'actor', 'actor')
                """))
                connection.execute(text(
                    "UPDATE scenario_drafts SET name='changed' WHERE scenario_id='role-proof'"
                ))
                connection.execute(text("""
                    INSERT INTO scenario_draft_decisions
                    (decision_id, scenario_id, source_product_id, source_component_id,
                     component_code, amount, action, effective_date, validation_state)
                    VALUES ('role-row', 'role-proof', 'synthetic', 'synthetic-row',
                            'תגמולי_עובד_עד_2000', 1.25, 'pension', DATE '2026-10-24', 'unverified')
                """))
                connection.execute(text("""
                    INSERT INTO scenario_draft_revisions
                    (revision_id, scenario_id, version, action, snapshot_json, actor)
                    VALUES ('role-revision', 'role-proof', 1, 'create', '{}', 'actor')
                """))
                connection.execute(text("""
                    UPDATE scenario_draft_decisions
                    SET amount=2.50, action='capital_asset',
                        effective_date=DATE '2026-10-25',
                        validation_state='needs_revalidation',
                        product_version_at_review=2,
                        source_fingerprint_at_review=repeat('a', 64),
                        ruleset_digest_at_review=NULL,
                        permission_preview_id_at_review=NULL
                    WHERE decision_id='role-row'
                """))
                assert connection.scalar(text(
                    "SELECT amount FROM scenario_draft_decisions "
                    "WHERE decision_id='role-row'"
                )) == Decimal("2.50")
                connection.execute(text("SAVEPOINT forbidden_identity_update"))
                try:
                    connection.execute(text("""
                        UPDATE scenario_draft_decisions
                        SET source_product_id='forbidden'
                        WHERE decision_id='role-row'
                    """))
                except DBAPIError as exc:
                    code = getattr(exc.orig, "sqlstate", None) or getattr(exc.orig, "pgcode", None)
                    assert code == "42501"
                    connection.execute(text("ROLLBACK TO SAVEPOINT forbidden_identity_update"))
                else:
                    raise AssertionError("restricted role changed immutable decision identity")
                connection.execute(text(
                    "DELETE FROM scenario_draft_decisions WHERE decision_id='role-row'"
                ))
            finally:
                transaction.rollback()
        with factory.begin() as db:
            created = service.create(db, 1, "חלופה א", "test-actor")
        scenario_id = created["scenario_id"]
        decision = DraftDecisionWrite(
            source_product_id="synthetic-product",
            source_component_id="synthetic-component",
            component_code="תגמולי_עובד_עד_2000",
            amount=Decimal("100.25"),
            action="pension", effective_date="2026-10-24",
        )
        with factory.begin() as db:
            updated = service.replace(
                db, 1, scenario_id,
                DraftReplace(name="חלופה א", expected_version=1, decisions=[decision]),
                "test-actor",
            )
        assert updated["version"] == 2
        assert updated["decisions"][0]["amount"] == "100.25"
        with factory() as db:
            assert service.read(db, 1, scenario_id)["decisions"][0]["amount"] == "100.25"
            try:
                service.read(db, 2, scenario_id)
            except service.DraftError as exc:
                assert (exc.code, exc.status) == ("SCENARIO_NOT_FOUND", 404)
            else:
                raise AssertionError("foreign client accessed scenario")
            amount = db.scalar(select(ScenarioDraftDecision.amount).where(
                ScenarioDraftDecision.scenario_id == scenario_id,
            ))
            assert amount == Decimal("100.25")
        with factory() as db:
            try:
                service.replace(db, 1, scenario_id,
                    DraftReplace(name="stale", expected_version=1, decisions=[decision]), "test-actor")
            except service.DraftError as exc:
                assert exc.code == "SCENARIO_VERSION_CONFLICT"
            else:
                raise AssertionError("stale version accepted")
            db.rollback()
        # Two genuinely distinct database transactions contend on one version.
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        gate = Barrier(2)
        def contender(label):
            with factory() as db:
                existing = service.read(db, 1, scenario_id)
                assert existing["version"] == 2
                gate.wait(timeout=10)
                try:
                    result = service.replace(
                        db, 1, scenario_id,
                        DraftReplace(name=label, expected_version=2, decisions=[decision]),
                        label,
                    )
                    db.commit()
                    return ("ok", result["version"])
                except service.DraftError as exc:
                    db.rollback()
                    return (exc.code, None)
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(contender, "writer-1")
            second = pool.submit(contender, "writer-2")
            outcomes = [first.result(timeout=25), second.result(timeout=25)]
        assert sorted(outcomes) == [("SCENARIO_VERSION_CONFLICT", None), ("ok", 3)]
        with factory() as db:
            assert service.read(db, 1, scenario_id)["version"] == 3
            assert len(service.read(db, 1, scenario_id)["decisions"]) == 1
            assert db.scalar(text(
                "SELECT count(*) FROM scenario_draft_revisions WHERE scenario_id = :id"
            ), {"id": scenario_id}) == 3
        # End-to-end persisted planner journey on actual isolated PostgreSQL:
        # clone the existing scenario, change only the clone, compare saved data,
        # archive the original and verify client isolation after a new session.
        with factory.begin() as db:
            cloned = service.duplicate(db, 1, scenario_id, "חלופה ב", "test-actor")
        clone_id = cloned["scenario_id"]
        assert clone_id != scenario_id
        assert cloned["decisions"][0]["amount"] == "100.25"
        clone_decision = DraftDecisionWrite(
            source_product_id="synthetic-product",
            source_component_id="synthetic-component",
            component_code="תגמולי_עובד_עד_2000",
            amount=Decimal("75.50"), action="capital_asset", effective_date="2026-10-25",
        )
        with factory.begin() as db:
            clone_saved = service.replace(
                db, 1, clone_id,
                DraftReplace(name="חלופה ב", expected_version=cloned["version"],
                             decisions=[clone_decision]), "test-actor",
            )
        assert clone_saved["decisions"][0]["amount"] == "75.50"
        with factory() as db:
            rows = service.list_drafts(db, 1)
            by_id = {row["scenario_id"]: row for row in rows}
            assert set(by_id) == {scenario_id, clone_id}
            assert by_id[scenario_id]["decisions"][0]["amount"] == "100.25"
            assert by_id[clone_id]["decisions"][0]["amount"] == "75.50"
            assert by_id[clone_id]["decisions"][0]["action"] == "capital_asset"
            assert service.list_drafts(db, 2) == []
        with factory.begin() as db:
            archived = service.archive(db, 1, scenario_id, 3, "test-actor")
        assert archived["status"] == "archived"
        with factory() as db:
            assert service.read(db, 1, scenario_id)["status"] == "archived"
            assert service.read(db, 1, clone_id)["status"] != "archived"
            assert db.scalar(text(
                "SELECT count(*) FROM scenario_draft_revisions WHERE scenario_id = :id"
            ), {"id": scenario_id}) == 4
            assert db.scalar(text(
                "SELECT count(*) FROM scenario_draft_revisions WHERE scenario_id = :id"
            ), {"id": clone_id}) == 3

        # Regression 330A: a professional price-basis revision is immutable
        # history, while L05 still permits amount/date/action edits to the
        # stable logical decision. Those edits update the current parent row
        # instead of DELETE/INSERT tripping the RESTRICT foreign key. The old
        # evidence becomes stale solely because the scenario version advances.
        with factory.begin() as db:
            protected = service.create(db, 1, "Price basis lifecycle", "test-actor")
        protected_id = protected["scenario_id"]
        protected_decision = DraftDecisionWrite(
            source_product_id="synthetic-product",
            source_component_id="synthetic-component",
            component_code="תגמולי_עובד_עד_2000",
            amount=Decimal("50.00"), action="pension",
            effective_date="2026-10-24",
        )
        with factory.begin() as db:
            protected = service.replace(
                db, 1, protected_id,
                DraftReplace(name="Price basis lifecycle", expected_version=1,
                             decisions=[protected_decision]),
                "test-actor",
            )
        decision_id = protected["decisions"][0]["decision_id"]
        with factory.begin() as db:
            db.add(ScenarioPensionPriceBasis(
                id="price-basis-history", client_id=1,
                scenario_id=protected_id, decision_id=decision_id,
                scenario_version=2, revision=1,
                source_fingerprint="a" * 64,
                target_fingerprint="b" * 64,
                target_date=date(2030, 1, 1),
                price_basis="NOMINAL_AT_RETIREMENT_TARGET_DATE",
                actor_id="test-actor", record_fingerprint="c" * 64,
            ))
        retained = DraftDecisionWrite(
            decision_id=decision_id,
            source_product_id="synthetic-product",
            source_component_id="synthetic-component",
            component_code="תגמולי_עובד_עד_2000",
            amount=Decimal("51.00"), action="pension",
            effective_date="2026-10-25",
        )
        with factory.begin() as db:
            saved = service.replace(
                db, 1, protected_id,
                DraftReplace(name="Price basis lifecycle edited",
                             expected_version=2, decisions=[retained]),
                "test-actor",
            )
        assert saved["version"] == 3
        assert saved["decisions"][0]["decision_id"] == decision_id
        assert saved["decisions"][0]["amount"] == "51.00"
        assert saved["decisions"][0]["effective_date"] == "2026-10-25"

        action_changed = DraftDecisionWrite(
            decision_id=decision_id,
            source_product_id="synthetic-product",
            source_component_id="synthetic-component",
            component_code="תגמולי_עובד_עד_2000",
            amount=Decimal("51.00"), action="capital_asset",
            effective_date="2026-10-25",
        )
        with factory.begin() as db:
            saved = service.replace(
                db, 1, protected_id,
                DraftReplace(name="Price basis lifecycle edited",
                             expected_version=3, decisions=[action_changed]),
                "test-actor",
            )
        assert saved["version"] == 4
        assert saved["decisions"][0]["decision_id"] == decision_id
        assert saved["decisions"][0]["action"] == "capital_asset"
        with factory() as db:
            history = db.get(ScenarioPensionPriceBasis, "price-basis-history")
            assert history is not None
            assert history.scenario_version == 2
            assert history.revision == 1
            assert history.source_fingerprint == "a" * 64
            assert history.target_fingerprint == "b" * 64
            assert history.record_fingerprint == "c" * 64
            assert history.price_basis == "NOMINAL_AT_RETIREMENT_TARGET_DATE"
            assert db.get(ScenarioDraftDecision, decision_id) is not None
            from app.services.scenario_pension_price_basis_service import (
                current_rows, evaluate_decision,
            )
            source_id = f"scenario-decision:{protected_id}:{decision_id}"
            historical = current_rows(db, 1, (protected_id,))[source_id]
            assert evaluate_decision(
                historical,
                {"source_id": source_id, "decision_id": decision_id,
                 "authority_fingerprint": "a" * 64,
                 "source_kind": "CALCULATED_PENSION", "source_state": "READY"},
                client_id=1, scenario_id=protected_id, scenario_version=4,
                target_fingerprint="b" * 64, target_date="2030-01-01",
            ) == "STALE"
            revisions = db.scalars(select(ScenarioDraftRevision).where(
                ScenarioDraftRevision.scenario_id == protected_id,
            ).order_by(ScenarioDraftRevision.version)).all()
            snapshots = {
                revision.version: json.loads(revision.snapshot_json)
                for revision in revisions
            }
            assert snapshots[2]["decisions"][0]["amount"] == "50.00"
            assert snapshots[3]["decisions"][0]["amount"] == "51.00"
            assert snapshots[3]["decisions"][0]["effective_date"] == "2026-10-25"
            assert snapshots[4]["decisions"][0]["action"] == "capital_asset"

        # Reusing an immutable historical identity for another source is
        # rejected as a controlled conflict. The CAS version/name, current
        # decision and professional history all roll back together.
        unsafe = DraftDecisionWrite(
            decision_id=decision_id,
            source_product_id="another-product",
            source_component_id="another-component",
            component_code="תגמולי_עובד_עד_2000",
            amount=Decimal("51.00"), action="pension",
            effective_date="2026-10-25",
        )
        with factory() as db:
            try:
                service.replace(
                    db, 1, protected_id,
                    DraftReplace(name="must roll back", expected_version=4,
                                 decisions=[unsafe]),
                    "test-actor",
                )
            except service.DraftError as exc:
                assert (exc.code, exc.status) == (
                    "SCENARIO_DECISION_HAS_PRICE_BASIS_HISTORY", 409,
                )
                db.rollback()
            else:
                raise AssertionError("source identity reused immutable price-basis identity")
        with factory() as db:
            try:
                service.replace(
                    db, 1, protected_id,
                    DraftReplace(name="must also roll back", expected_version=4,
                                 decisions=[]),
                    "test-actor",
                )
            except service.DraftError as exc:
                assert (exc.code, exc.status) == (
                    "SCENARIO_DECISION_HAS_PRICE_BASIS_HISTORY", 409,
                )
                db.rollback()
            else:
                raise AssertionError("protected decision was removed")
        with factory() as db:
            after_rejection = service.read(db, 1, protected_id)
            assert after_rejection["version"] == 4
            assert after_rejection["name"] == "Price basis lifecycle edited"
            assert after_rejection["decisions"][0]["amount"] == "51.00"
            assert after_rejection["decisions"][0]["effective_date"] == "2026-10-25"
            assert after_rejection["decisions"][0]["action"] == "capital_asset"
            assert db.scalar(text(
                "SELECT count(*) FROM scenario_pension_price_basis_decisions "
                "WHERE scenario_id = :id"
            ), {"id": protected_id}) == 1
    finally:
        engine.dispose()


def test_synthetic_client_http_scenario_journey_against_disposable_postgresql(postgres_url):
    """Full FastAPI HTTP handlers + real DB, without a browser or financial engine.

    Independent fresh database from the existing disposable PostgreSQL fixture.
    """
    from fastapi.testclient import TestClient
    from app.main import create_app
    from app.security.config import AuthConfig
    from app.db.session import get_db

    load_all_models()
    engine = create_engine(postgres_url)
    try:
        with engine.begin() as conn:
            conn.execute(text(f"CREATE ROLE {APPLICATION_ROLE} NOLOGIN"))
        migration = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "f330a1c2d3e4"],
            cwd=BACKEND,
            env={**os.environ, "DATABASE_URL": postgres_url,
                 "CRTISBA_APPLICATION_DB_ROLE": APPLICATION_ROLE,
                 "PYTHONIOENCODING": "utf-8"},
            capture_output=True, text=True, encoding="utf-8", timeout=180,
        )
        assert migration.returncode == 0, migration.stdout + migration.stderr
        factory = sessionmaker(bind=engine, autoflush=False)
        with factory.begin() as session:
            session.add_all([
                Client(client_id=101, display_name="Synthetic Planner A", id_number="http-synthetic-a"),
                Client(client_id=102, display_name="Synthetic Planner B", id_number="http-synthetic-b"),
            ])

        app = create_app(AuthConfig(production=False))
        def isolated_db():
            with factory() as session:
                yield session
        app.dependency_overrides[get_db] = isolated_db
        try:
            with TestClient(app) as http:
                root = "/api/clients/101/scenario-drafts"
                other = "/api/clients/102/scenario-drafts"

                def ok(response):
                    assert response.status_code == 200, response.text
                    return response.json()

                original = ok(http.post(root, json={"name": "Original"}))
                scenario_id = original["scenario_id"]
                decision = {
                    "source_product_id": "synthetic-product",
                    "source_component_id": "synthetic-component",
                    "component_code": "תגמולי_עובד_עד_2000",
                    "amount": "100.25", "action": "pension",
                    "effective_date": "2026-10-26",
                }
                original = ok(http.put(f"{root}/{scenario_id}", json={
                    "name": "Original", "expected_version": original["version"],
                    "decisions": [decision],
                }))
                assert original["decisions"][0]["amount"] == "100.25"
                original_decision_id = original["decisions"][0]["decision_id"]
                with factory.begin() as session:
                    session.add(ScenarioPensionPriceBasis(
                        id="http-price-basis-history", client_id=101,
                        scenario_id=scenario_id, decision_id=original_decision_id,
                        scenario_version=original["version"], revision=1,
                        source_fingerprint="d" * 64,
                        target_fingerprint="e" * 64,
                        target_date=date(2030, 1, 1),
                        price_basis="NOMINAL_AT_RETIREMENT_TARGET_DATE",
                        actor_id="test-actor", record_fingerprint="f" * 64,
                    ))
                retained = {**decision, "decision_id": original_decision_id}
                original = ok(http.put(f"{root}/{scenario_id}", json={
                    "name": "Original retained", "expected_version": original["version"],
                    "decisions": [{**retained, "amount": "100.26"}],
                }))
                assert original["decisions"][0]["decision_id"] == original_decision_id
                assert original["decisions"][0]["amount"] == "100.26"
                original = ok(http.put(f"{root}/{scenario_id}", json={
                    "name": "Original retained", "expected_version": original["version"],
                    "decisions": [{**retained, "amount": "100.26",
                                   "effective_date": "2026-10-27"}],
                }))
                assert original["decisions"][0]["effective_date"] == "2026-10-27"
                original = ok(http.put(f"{root}/{scenario_id}", json={
                    "name": "Original retained", "expected_version": original["version"],
                    "decisions": [{**retained, "amount": "100.26",
                                   "effective_date": "2026-10-27",
                                   "action": "capital_asset"}],
                }))
                assert original["decisions"][0]["action"] == "capital_asset"
                rejected = http.put(f"{root}/{scenario_id}", json={
                    "name": "must roll back", "expected_version": original["version"],
                    "decisions": [{**retained, "source_product_id": "other-product",
                                   "source_component_id": "other-component"}],
                })
                assert rejected.status_code == 409, rejected.text
                assert rejected.json()["code"] == (
                    "SCENARIO_DECISION_HAS_PRICE_BASIS_HISTORY"
                )
                original = ok(http.get(f"{root}/{scenario_id}"))
                assert original["name"] == "Original retained"
                assert original["decisions"][0]["amount"] == "100.26"
                assert original["decisions"][0]["effective_date"] == "2026-10-27"
                assert original["decisions"][0]["action"] == "capital_asset"
                clone = ok(http.post(f"{root}/{scenario_id}/duplicate", json={"name": "Alternative"}))
                assert clone["decisions"][0]["amount"] == "100.26"
                clone_id = clone["scenario_id"]
                changed = {key: clone["decisions"][0][key] for key in ("decision_id", "source_product_id", "source_component_id", "component_code", "effective_date")}
                changed.update({"action": "capital_asset", "amount": "80.00"})
                clone = ok(http.put(f"{root}/{clone_id}", json={
                    "name": "Alternative", "expected_version": clone["version"],
                    "decisions": [changed],
                }))
                assert clone["decisions"][0]["action"] == "capital_asset"

                stale = http.put(f"{root}/{clone_id}", json={
                    "name": "Stale", "expected_version": clone["version"] - 1,
                    "decisions": [changed],
                })
                assert stale.status_code == 409, stale.text

                listed = ok(http.get(root))
                assert {item["scenario_id"] for item in listed} == {scenario_id, clone_id}
                assert next(item for item in listed if item["scenario_id"] == scenario_id)["decisions"][0]["amount"] == "100.26"
                assert next(item for item in listed if item["scenario_id"] == clone_id)["decisions"][0]["amount"] == "80.00"
                assert ok(http.get(other)) == []
                assert http.get(f"{other}/{scenario_id}").status_code == 404

                clone = ok(http.put(f"{root}/{clone_id}", json={
                    "name": "Alternative", "expected_version": clone["version"],
                    "decisions": [],
                }))
                assert clone["decisions"] == []
                # Recreate the HTTP client to exercise a new request/session,
                # akin to refreshing the SPA without relying on in-memory UI state.
            with TestClient(app) as refreshed:
                persisted = ok(refreshed.get(root))
                assert len(persisted) == 2
                assert next(item for item in persisted if item["scenario_id"] == scenario_id)["decisions"][0]["amount"] == "100.26"
                assert next(item for item in persisted if item["scenario_id"] == clone_id)["decisions"] == []
                assert all(item["financial_validation"] == "not_evaluated" for item in persisted)
        finally:
            app.dependency_overrides.clear()
    finally:
        engine.dispose()
