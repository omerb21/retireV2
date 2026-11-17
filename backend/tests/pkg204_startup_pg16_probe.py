"""Directive 204 isolated PostgreSQL 16 startup compatibility probe.

Run only in disposable Docker PostgreSQL, with PKG204_SYNTHETIC_PG16=1.
This is a separate Python process for each runtime code revision.
Never run against Railway, a user database or an external host.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse

from argon2 import PasswordHasher
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session


def require_synthetic() -> str:
    if os.environ.get("PKG204_SYNTHETIC_PG16") != "1":
        raise RuntimeError("PKG204_SYNTHETIC_ONLY")
    url = os.environ["DATABASE_URL"]
    parsed = urlparse(url)
    if parsed.hostname != "db" or parsed.port != 5432 or parsed.username != "synthetic_planner":
        raise RuntimeError("PKG204_UNEXPECTED_DATABASE_ENDPOINT")
    if parsed.path.lstrip("/") not in {
        "pkg204_old", "pkg204_new", "pkg204_unknown", "pkg204_missing", "pkg204_absent"
    }:
        raise RuntimeError("PKG204_UNAPPROVED_DATABASE_NAME")
    if Path("/.dockerenv").exists() is False:
        raise RuntimeError("PKG204_DOCKER_CONTAINER_REQUIRED")
    return url


def main(case: str) -> None:
    url = require_synthetic()
    sys.path.insert(0, "/tmp/pkg204-old" if case == "old-cas" else "/app/backend")
    from app.db import session as db_session
    from app.main import EXPECTED_ALEMBIC_HEAD, create_app
    from app.security.config import AuthConfig

    expected = "b2d7e4c9f108" if case == "old-cas" else "c194e2f0a816"
    assert EXPECTED_ALEMBIC_HEAD == expected, (case, EXPECTED_ALEMBIC_HEAD)
    assert db_session.SessionLocal is None

    password = "PKG204-synthetic-only-password"
    ph = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4, hash_len=32, salt_len=16)
    conf = AuthConfig(
        production=True,
        ingress_mode="railway_public_edge",
        public_origin="https://pkg204.synthetic.test",
        public_authority="pkg204.synthetic.test",
        username="pkg204",
        password_hash=ph.hash(password),
        dummy_password_hash=ph.hash("no-such-password"),
        actor_id="pkg204-synthetic",
        session_secret=b"S" * 32,
        rate_limit_secret=b"R" * 32,
    )
    app = create_app(config=conf)
    assert not app.state.stage6_preview_enabled, "Stage 6 must not be enabled"
    headers = {
        "x-real-ip": "127.0.0.1",
        "x-forwarded-proto": "https",
        "x-forwarded-host": "pkg204.synthetic.test",
        "origin": "https://pkg204.synthetic.test",
    }
    with TestClient(app, base_url="https://pkg204.synthetic.test") as client:
        ready = client.get("/healthz/ready", headers={"host": "healthcheck.railway.app"})
        permitted = case == "new-cas"
        assert ready.status_code == (200 if permitted else 503), (case, ready.status_code, ready.text)
        assert app.state.rate_limiter_ready is permitted, (case, app.state.rate_limiter_ready)
        if permitted:
            login = client.post(
                "/api/auth/login", headers=headers,
                json={"username": "pkg204", "password": password},
            )
            assert login.status_code == 200, (login.status_code, login.text)
            session = client.get("/api/auth/session", headers=headers)
            assert session.status_code == 200 and session.json()["authenticated"] is True
            csrf = session.json()["csrf_token"]
            no_csrf = client.post("/api/auth/logout", headers=headers)
            assert no_csrf.status_code == 403 and no_csrf.json()["code"] == "CSRF_INVALID"
            logout = client.post("/api/auth/logout", headers={**headers, "x-rtdir-csrf": csrf})
            assert logout.status_code == 204, (logout.status_code, logout.text)
            denied = client.get("/api/auth/session", headers=headers)
            assert denied.status_code == 401
            print("PKG204_NEW_CAS_AUTH_CSRF_PASS")
        else:
            bad_login = client.post("/api/auth/login", headers=headers,
                                    json={"username": "pkg204", "password": password})
            assert bad_login.status_code == 503, (case, bad_login.status_code, bad_login.text)
            assert bad_login.json()["code"] == "AUTH_RATE_LIMIT_UNAVAILABLE"
        print(f"PKG204_STARTUP_{case.upper().replace('-', '_')}_PASS {ready.status_code}")

    if case != "old-cas":
        return

    # Exercise actual old ORM mappings on a genuine migrated CAS schema.
    # Proves why legacy writes must be fenced off even when SQL continues to work.
    from app.models.actual_capitalization import ActualCapitalization
    from app.models.client import Client
    from app.models.retirement_facts import CapitalAsset, RecurringExpense, RecurringIncome

    for model in (ActualCapitalization, CapitalAsset, RecurringIncome, RecurringExpense):
        assert "version" not in model.__mapper__.attrs, model.__name__

    engine = create_engine(url)
    try:
        with Session(engine) as db:
            owner = Client(display_name="PKG204 synthetic", id_number="pkg204-synthetic-old-writer")
            db.add(owner)
            db.flush()
            cap = ActualCapitalization(capitalization_id="pkg204-cap", client_id=owner.client_id,
                                        amount=Decimal("100.00"), capitalization_date=date(2025, 1, 1))
            asset = CapitalAsset(client_id=owner.client_id, asset_category="other",
                                 asset_description="synthetic", known_value_amount=Decimal("200.00"))
            income = RecurringIncome(client_id=owner.client_id, income_category="rental",
                                     description="synthetic", amount=Decimal("300.00"),
                                     amount_basis="gross", frequency="monthly",
                                     continuation_status="ongoing")
            expense = RecurringExpense(client_id=owner.client_id, expense_category="housing",
                                       description="synthetic", amount=Decimal("400.00"),
                                       expense_type="mandatory", frequency="monthly",
                                       continuation_status="ongoing")
            db.add_all([cap, asset, income, expense])
            db.commit()
            for row in (cap, asset, income, expense):
                assert db.execute(
                    text(f"SELECT version FROM {row.__tablename__} WHERE "
                         + ("capitalization_id=:id" if row.__tablename__ == "actual_capitalizations" else "id=:id")),
                    {"id": row.capitalization_id if row.__tablename__ == "actual_capitalizations" else row.id}
                ).scalar_one() == 1
            cap.amount = Decimal("111.00")
            asset.known_value_amount = Decimal("222.00")
            income.amount = Decimal("333.00")
            expense.amount = Decimal("444.00")
            db.commit()
            for row in (cap, asset, income, expense):
                assert db.execute(
                    text(f"SELECT version FROM {row.__tablename__} WHERE "
                         + ("capitalization_id=:id" if row.__tablename__ == "actual_capitalizations" else "id=:id")),
                    {"id": row.capitalization_id if row.__tablename__ == "actual_capitalizations" else row.id}
                ).scalar_one() == 1, row.__tablename__
            print("PKG204_OLD_WRITES_WITHOUT_VERSION_INCREMENT_CONFIRMED_ALL_FOUR")
    finally:
        engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("case", choices=[
        "new-cas", "new-old", "new-unknown", "new-missing",
        "new-disconnected", "old-cas",
    ])
    args = parser.parse_args()
    main(args.case)
