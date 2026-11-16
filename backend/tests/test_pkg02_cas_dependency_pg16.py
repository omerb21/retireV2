"""PKG-02 isolated PostgreSQL 16 acceptance. Execute only in disposable synthetic CI.

Requires PKG02_SYNTHETIC_PG16=1 and the local backend in dev compose.
No Railway or production URLs are used.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from threading import Barrier
import os
import subprocess
import uuid

import httpx
import psycopg2
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from app.db.base import load_all_models
from app.models.retirement_facts import RecurringExpense

load_all_models()
from app.services import planning_input_service as planning

pytestmark = pytest.mark.skipif(
    os.environ.get("PKG02_SYNTHETIC_PG16") != "1",
    reason="Only allowed in explicitly isolated synthetic PostgreSQL 16 CI",
)

BASE = "http://127.0.0.1:8000/api/clients"


def _post(client, path, data):
    r = client.post(path, json=data)
    assert r.status_code in (200, 201), (path, r.status_code, r.text)
    return r.json()


def _client(client, label):
    suffix = uuid.uuid4().hex[:12]
    return _post(client, BASE, {"full_name": f"PKG02 SYNTHETIC {label} {suffix}",
                                "id_number": suffix})["client_id"]


def _payloads():
    return {
        "actual-capitalizations": {
            "amount": "100.00", "capitalization_date": "2025-01-01", "source_label": "SYNTHETIC"},
        "capital-assets": {
            "asset_category": "other", "asset_description": "SYNTHETIC ASSET",
            "known_value_amount": "500.00", "value_as_of_date": "2025-01-01"},
        "recurring-incomes": {
            "income_category": "rental", "description": "SYNTHETIC INCOME",
            "amount": "1000.00", "amount_basis": "gross",
            "frequency": "monthly", "continuation_status": "ongoing",
            "start_date": "2020-01-01"},
        "recurring-expenses": {
            "expense_category": "housing", "description": "SYNTHETIC EXPENSE",
            "amount": "300.00", "frequency": "monthly",
            "expense_type": "mandatory", "continuation_status": "ongoing",
            "start_date": "2020-01-01"},
    }


def _id(route, row):
    return row["capitalization_id"] if route == "actual-capitalizations" else row["id"]


def _change(route, item, payload, *, amount=None, frequency=None):
    if route == "actual-capitalizations":
        return {**payload, "amount": amount or "111.00",
                "capitalization_date": "2025-02-02",
                "expected_version": item["version"]}
    if route == "capital-assets":
        return {"known_value_amount": amount or "555.00",
                "value_as_of_date": "2025-02-02", "expected_version": item["version"]}
    return {"amount": amount or "1111.00", "frequency": frequency or "quarterly",
            "expected_version": item["version"]}


def test_pg16_four_api_records_versioned_writes_and_isolation():
    with httpx.Client(timeout=20) as http:
        a = _client(http, "A")
        b = _client(http, "B")
        for route, original in _payloads().items():
            item = _post(http, f"{BASE}/{a}/{route}", original)
            assert item["client_id"] == a and item["version"] == 1
            identity = _id(route, item)
            url = f"{BASE}/{a}/{route}/{identity}"
            rows = http.get(f"{BASE}/{a}/{route}").json()
            assert any(_id(route, row) == identity and row["version"] == 1 for row in rows)
            update = _change(route, item, original)
            accepted = http.put(url, json=update)
            assert accepted.status_code == 200, (route, accepted.text)
            assert accepted.json()["version"] == 2
            missing = http.put(url, json={k: v for k, v in update.items() if k != "expected_version"})
            assert missing.status_code == 422, (route, missing.status_code, missing.text)
            stale = http.put(url, json=update)
            assert stale.status_code == 409, (route, stale.text)
            assert stale.json()["detail"]["code"] == "RECORD_VERSION_CONFLICT"
            assert http.get(f"{BASE}/{a}/{route}").json()[0]["version"] == 2
            foreign = http.put(f"{BASE}/{b}/{route}/{identity}", json=update)
            assert foreign.status_code == 404, (route, foreign.status_code, foreign.text)
            if route == "actual-capitalizations":
                wrong = http.delete(url, params={"expected_version": 1})
                assert wrong.status_code == 409 and wrong.json()["detail"]["code"] == "RECORD_VERSION_CONFLICT"
                assert http.delete(url).status_code == 422
                assert http.delete(f"{BASE}/{b}/{route}/{identity}", params={"expected_version": 2}).status_code == 404
                assert http.delete(url, params={"expected_version": 2}).status_code == 200
                assert not http.get(f"{BASE}/{a}/{route}").json()


def test_pg16_two_concurrent_api_writers_exactly_one_success():
    with httpx.Client(timeout=30) as http:
        a = _client(http, "RACE")
        row = _post(http, f"{BASE}/{a}/recurring-expenses", _payloads()["recurring-expenses"])
        identity = row["id"]
    url = f"{BASE}/{a}/recurring-expenses/{identity}"
    gate = Barrier(2)
    def worker(amount):
        with httpx.Client(timeout=30) as client:
            gate.wait(timeout=15)
            return amount, client.put(url, json={"amount": amount, "expected_version": 1})
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(worker, ("901.00", "902.00")))
    assert sorted(r.status_code for _, r in outcomes) == [200, 409]
    winner = next(amount for amount, r in outcomes if r.status_code == 200)
    loser = next(r for _, r in outcomes if r.status_code == 409)
    assert loser.json()["detail"]["code"] == "RECORD_VERSION_CONFLICT"
    with httpx.Client(timeout=20) as client:
        final = client.get(f"{BASE}/{a}/recurring-expenses").json()[0]
    assert Decimal(str(final["amount"])) == Decimal(winner) and final["version"] == 2


def test_pg16_two_stale_orm_sessions_cannot_silently_overwrite():
    engine = create_engine(os.environ["MIGRATION_DATABASE_URL"])
    try:
        with httpx.Client(timeout=20) as http:
            a = _client(http, "ORM")
            item = _post(http, f"{BASE}/{a}/recurring-expenses", _payloads()["recurring-expenses"])
        gate = Barrier(2)
        def writer(amount):
            with Session(engine) as db:
                row = db.get(RecurringExpense, item["id"])
                assert row.version == 1
                row.amount = Decimal(amount)
                gate.wait(timeout=15)
                try:
                    db.commit()
                    return ("committed", amount)
                except StaleDataError:
                    db.rollback()
                    return ("conflict", amount)
        with ThreadPoolExecutor(max_workers=2) as pool:
            states = list(pool.map(writer, ("55.00", "66.00")))
        assert sorted(x[0] for x in states) == ["committed", "conflict"]
        winner = next(amount for state, amount in states if state == "committed")
        with Session(engine) as db:
            final = db.get(RecurringExpense, item["id"])
            assert final.version == 2 and final.amount == Decimal(winner)
    finally:
        engine.dispose()


def test_pg16_dependency_fingerprint_contract_per_domain():
    engine = create_engine(os.environ["MIGRATION_DATABASE_URL"])
    try:
        with httpx.Client(timeout=20) as http:
            a = _client(http, "DEPENDENCY")
            plan_url = f"{BASE}/{a}/retirement-planning-input"
            def sample():
                r = http.get(plan_url)
                assert r.status_code == 200, r.text
                v = r.json()
                return {k: v[k] for k in ("source_state_fingerprint", "planning_input_fingerprint",
                         "planning_calculation_input_fingerprint")}
            before = sample()
            snapshots = []
            for route, original in _payloads().items():
                row = _post(http, f"{BASE}/{a}/{route}", original)
                created = sample()
                identity = _id(route, row)
                payload = _change(route, row, original)
                resp = http.put(f"{BASE}/{a}/{route}/{identity}", json=payload)
                assert resp.status_code == 200, (route, resp.text)
                after = sample()
                changed = {k for k in before if created[k] != after[k]}
                # A fact's revision must change the planning-input hash if it is a planning input.
                if route in ("capital-assets", "recurring-incomes", "recurring-expenses"):
                    assert created["planning_input_fingerprint"] != after["planning_input_fingerprint"]
                    assert created["planning_calculation_input_fingerprint"] != after["planning_calculation_input_fingerprint"]
                if route in ("recurring-incomes", "recurring-expenses", "actual-capitalizations"):
                    assert created["source_state_fingerprint"] == after["source_state_fingerprint"]
                if route == "capital-assets":
                    assert created["source_state_fingerprint"] != after["source_state_fingerprint"]
                snapshots.append((route, created, after, sorted(changed)))
                before = after
            # Preserve exact evidence as a printable, reproducible per-domain trace.
            for route, created, after, changed in snapshots:
                print("PKG02_DEPENDENCY", route, "before", created, "after", after, "changed", changed)
    finally:
        engine.dispose()


def test_pg16_migration_backfills_existing_rows_without_mutating_financial_values():
    import sqlalchemy as sa
    from alembic.config import Config
    from alembic import command
    old_url = os.environ["MIGRATION_DATABASE_URL"]
    dbname = "pkg02_cas_" + uuid.uuid4().hex[:15]
    root = psycopg2.connect(old_url)
    root.autocommit = True
    try:
        with root.cursor() as cur:
            cur.execute("CREATE DATABASE " + dbname)
    finally:
        root.close()
    from sqlalchemy.engine import make_url
    url = make_url(old_url).set(database=dbname).render_as_string(hide_password=False)
    cfg = Config("/app/backend/alembic.ini")
    try:
        import sqlalchemy
        import os as _os
        previous = _os.environ.get("DATABASE_URL")
        _os.environ["DATABASE_URL"] = url
        try:
            command.upgrade(cfg, "b2d7e4c9f108")
            engine = create_engine(url)
            with engine.begin() as c:
                c.execute(text("INSERT INTO clients(client_id,display_name,id_number) VALUES(944194,'PKG02 SYNTHETIC','194')"))
                c.execute(text("INSERT INTO actual_capitalizations(capitalization_id,client_id,amount,capitalization_date) VALUES('PKG02-OLD',944194,123.45,'2020-01-01')"))
                c.execute(text("INSERT INTO capital_asset(client_id,asset_category,asset_description,known_value_amount) VALUES(944194,'other','old',234.56)"))
                c.execute(text("INSERT INTO recurring_income(client_id,income_category,description,amount,amount_basis,frequency,continuation_status) VALUES(944194,'rental','old',345.67,'gross','monthly','ongoing')"))
                c.execute(text("INSERT INTO recurring_expense(client_id,expense_category,description,amount,frequency,expense_type,continuation_status) VALUES(944194,'housing','old',456.78,'monthly','mandatory','ongoing')"))
            before = {}
            tables = ("actual_capitalizations", "capital_asset", "recurring_income", "recurring_expense")
            with engine.connect() as c:
                for table in tables:
                    before[table] = c.execute(text(f"SELECT * FROM {table}")).mappings().all()[0]
            engine.dispose()
            command.upgrade(cfg, "head")
            engine = create_engine(url)
            with engine.connect() as c:
                for table in tables:
                    rows = c.execute(text(f"SELECT * FROM {table}")).mappings().all()
                    assert len(rows) == 1 and rows[0]["version"] == 1, table
                    assert all(rows[0][k] == value for k, value in before[table].items()), table
                    col = c.execute(text("SELECT data_type,is_nullable,column_default FROM information_schema.columns WHERE table_name=:table AND column_name='version'"), {"table": table}).one()
                    assert col[0] == "bigint" and col[1] == "NO" and "1" in col[2], (table, col)
            engine.dispose()
        finally:
            if previous is None:
                _os.environ.pop("DATABASE_URL", None)
            else:
                _os.environ["DATABASE_URL"] = previous
    finally:
        cleanup = psycopg2.connect(old_url)
        cleanup.autocommit = True
        try:
            with cleanup.cursor() as cur:
                cur.execute("DROP DATABASE IF EXISTS " + dbname + " WITH (FORCE)")
        finally:
            cleanup.close()


def test_pg16_version_only_bookkeeping_does_not_invalidate_professional_fingerprints():
    """CAS metadata must not silently change pre-existing professional source meaning."""
    engine = create_engine(os.environ["MIGRATION_DATABASE_URL"])
    try:
        with httpx.Client(timeout=20) as http:
            a = _client(http, "VERSION-ONLY")
            saved = {}
            for route, original in _payloads().items():
                saved[route] = _post(http, f"{BASE}/{a}/{route}", original)
            path = f"{BASE}/{a}/retirement-planning-input"
            initial = http.get(path)
            assert initial.status_code == 200
            expected = initial.json()
            with engine.begin() as db:
                table_map = {
                    "actual-capitalizations": ("actual_capitalizations", "capitalization_id"),
                    "capital-assets": ("capital_asset", "id"),
                    "recurring-incomes": ("recurring_income", "id"),
                    "recurring-expenses": ("recurring_expense", "id"),
                }
                for domain, (table, key) in table_map.items():
                    rowid = _id(domain, saved[domain])
                    stmt = text(f"UPDATE {table} SET version = version + 1 WHERE {key} = :rowid AND client_id = :client")
                    result = db.execute(stmt, {"rowid": rowid, "client": a})
                    assert result.rowcount == 1
            current = http.get(path)
            assert current.status_code == 200
            actual = current.json()
            for key in ("source_state_fingerprint", "planning_input_fingerprint",
                        "planning_calculation_input_fingerprint"):
                assert actual[key] == expected[key], (key, expected[key], actual[key])
            print("PKG02_VERSION_ONLY_NO_FALSE_STALENESS", {
                k: actual[k] for k in ("source_state_fingerprint",
                                      "planning_input_fingerprint",
                                      "planning_calculation_input_fingerprint")
            })
    finally:
        engine.dispose()
