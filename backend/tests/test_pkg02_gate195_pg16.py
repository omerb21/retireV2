"""Gate 195: four narrow, synthetic PostgreSQL16 checks; never connect to Railway.

Runs only on the disposable local CI database; no earlier PKG02 suites are replayed.
"""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from datetime import date
from threading import Event
from uuid import uuid4
import copy
import os

import httpx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.orm.exc import StaleDataError

from app.db.base import load_all_models
from app.db.session import get_db
from app.main import app
from app.models.retirement_facts import RecurringIncome, CapitalAsset
from app.models.pension_product import COMPONENT_CODES, PensionProductComponent
from app.models.canonical_conversion import conversions
from app.models.fixation_run import FixationRun
from app.schemas.canonical_conversion import ReversalRequest
from app.schemas.pension_product import ProductCreate, ProductUpdate
from app.services import planning_input_service as planning
from app.services import canonical_component_conversion_service as conversion
from app.services.pension_product_service import create_product, update_product, product_response
from tests.pkg004d_test_support import seed_eligibility_revision, resolver_payload
from test_pkg003_dependency_manifest import _payload as fixation_payload, _comparison_request
from test_canonical_component_conversion import request as conversion_request

load_all_models()

pytestmark = pytest.mark.skipif(os.environ.get("PKG02_SYNTHETIC_PG16") != "1",
                               reason="Requires isolated disposable PG16 CI")

BASE = "http://127.0.0.1:8000/api/clients"


def new_client(http, tag):
    suffix = uuid4().hex[:14]
    res = http.post(BASE, json={"full_name": "PKG195 SYNTHETIC " + tag,
                                "id_number": suffix, "birth_date": "1970-01-01"})
    assert res.status_code in (200, 201), (res.status_code, res.text)
    return res.json()["client_id"]


def insert_income(http, client_id, *, category="pension"):
    req = {"income_category": category, "description": "PKG195 source pension",
           "amount": "1000.00", "amount_basis": "gross", "frequency": "monthly",
           "continuation_status": "ongoing", "start_date": "2030-01-01"}
    res = http.post(f"{BASE}/{client_id}/recurring-incomes", json=req)
    assert res.status_code in (200, 201), res.text
    return res.json()


def prepare_resolution(http, client_id, income_id):
    base = http.put(f"{BASE}/{client_id}/retirement-planning-input/base-date",
                    json={"expected_version": 0, "planning_base_date": "2030-01-01"})
    assert base.status_code == 200, base.text
    plan = http.get(f"{BASE}/{client_id}/retirement-planning-input")
    assert plan.status_code == 200, plan.text
    before = plan.json()
    source = next(x for x in before["excluded_sources"] if x["id"] == income_id)
    req = {"expected_version": before["decision_version"],
           "expected_income_fingerprint": source["source_fingerprint"],
           "decision_kind": "MISCLASSIFIED_GENERAL_INCOME",
           "income_category": "rental", "reference": "PKG195 synthetic identification"}
    return req, before


def test_195_fixation_real_saved_manifest_and_changed_capitalization_api():
    """Persist real run with manifest, update persisted capitalization, compare through active HTTP API."""
    engine = create_engine(os.environ["MIGRATION_DATABASE_URL"])
    factory = sessionmaker(engine, expire_on_commit=False)
    app.dependency_overrides[get_db] = lambda: (db for db in [factory()])  # replaced below
    def session_override():
        with factory() as db:
            yield db
    app.dependency_overrides[get_db] = session_override
    try:
        from fastapi.testclient import TestClient
        with TestClient(app) as http:
            client_id = new_client(http, "FIXATION")
            with factory() as db:
                revision, _ = seed_eligibility_revision(db, client_id=client_id)
                db.commit()
            original = resolver_payload(fixation_payload(client_id=client_id), revision_id=revision)
            original["grants_collection_state"] = "confirmed_none"
            original["grants"] = []
            row = original["actual_capitalizations"][0]
            cap = http.post(f"{BASE}/{client_id}/actual-capitalizations",
                            json={"amount": str(row["amount"]),
                                  "capitalization_date": row["capitalization_date"],
                                  "source_label": "PKG195 synthetic accepted capitalization"})
            assert cap.status_code in (200, 201), cap.text
            old = cap.json()
            preview = http.post(f"{BASE}/{client_id}/fixation/calculate", json=original)
            assert preview.status_code == 200, preview.text
            saved = http.post("http://testserver/api/fixation/save",
                              json={"client_id": client_id, "input_data": original,
                                    "preview_identity": preview.json()["preview_identity"]})
            assert saved.status_code == 200, saved.text
            run_id = saved.json()["run_id"]
            manifest = http.get(f"{BASE}/{client_id}/fixation/runs/{run_id}/dependency-manifest")
            assert manifest.status_code == 200 and manifest.json()["availability"] == "available"
            url = f"{BASE}/{client_id}/fixation/runs/{run_id}/dependency-comparison"
            same = http.post(url, json=_comparison_request(original))
            assert same.status_code == 200 and same.json()["technical_result"] == "unchanged", same.text
            updated = http.put(f"{BASE}/{client_id}/actual-capitalizations/{old['capitalization_id']}",
                json={"amount": "36.00", "capitalization_date": old["capitalization_date"],
                      "source_label": old["source_label"], "expected_version": old["version"]})
            assert updated.status_code == 200, updated.text
            from_db = http.get(f"{BASE}/{client_id}/actual-capitalizations").json()
            current = next(x for x in from_db if x["capitalization_id"] == old["capitalization_id"])
            revised = copy.deepcopy(original)
            revised["actual_capitalizations"][0]["amount"] = float(current["amount"])
            after = http.post(url, json=_comparison_request(revised))
            assert after.status_code == 200, after.text
            assert after.json()["technical_result"] == "changed", after.json()
            assert "actual_capitalization" in "|".join(after.json()["changed_dependency_types"]), after.json()
            # Contract is technical comparison only: no fictional automatic professional lifecycle status.
            with factory() as db:
                assert db.get(FixationRun, run_id) is not None
            print("GATE195_FIXATION", {"run_id": run_id, "before": same.json()["technical_result"],
                    "after": after.json()["technical_result"],
                    "changed_dependency_types": after.json()["changed_dependency_types"],
                    "professional_status_in_comparison_contract": False})
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def test_195_income_resolution_becomes_stale_after_changed_source():
    with httpx.Client(timeout=25) as http:
        client_id = new_client(http, "INCOME")
        row = insert_income(http, client_id)
        decision, before = prepare_resolution(http, client_id, row["id"])
        saved = http.put(f"{BASE}/{client_id}/retirement-planning-input/income-resolutions/{row['id']}",
                         json=decision)
        assert saved.status_code == 200, saved.text
        accepted = http.get(f"{BASE}/{client_id}/retirement-planning-input").json()
        assert any(x["id"] == row["id"] for x in accepted["general_income_inputs"]), accepted
        current = http.get(f"{BASE}/{client_id}/recurring-incomes").json()
        record = next(x for x in current if x["id"] == row["id"])
        changed = http.put(f"{BASE}/{client_id}/recurring-incomes/{row['id']}",
                           json={"amount": "1100.00", "frequency": "quarterly",
                                 "expected_version": record["version"]})
        assert changed.status_code == 200, changed.text
        after = http.get(f"{BASE}/{client_id}/retirement-planning-input").json()
        rejected = next(x for x in after["excluded_sources"] if x["id"] == row["id"])
        assert rejected["blocking_facts"] == ["identity_resolution_stale"], rejected
        assert not after["planning_input_ready"]
        assert before["planning_input_fingerprint"] != after["planning_input_fingerprint"]
        print("GATE195_INCOME_RESOLUTION", {"before_ready": accepted["planning_input_ready"],
              "after_ready": after["planning_input_ready"],
              "reason": rejected["blocking_facts"],
              "fingerprint_before": before["planning_input_fingerprint"],
              "fingerprint_after": after["planning_input_fingerprint"]})


def test_195_concurrent_income_edit_conflicts_with_resolve_income_no_silent_overwrite():
    engine = create_engine(os.environ["MIGRATION_DATABASE_URL"])
    try:
        with httpx.Client(timeout=25) as http:
            client_id = new_client(http, "INCOME-RACE")
            row = insert_income(http, client_id)
            payload, _ = prepare_resolution(http, client_id, row["id"])
            ready = Event()
            proceed = Event()
            def stale_writer():
                with Session(engine) as db:
                    income = db.get(RecurringIncome, row["id"])
                    assert income.version == 1
                    income.description = "MUST NEVER PERSIST STALE EDIT"
                    ready.set()
                    assert proceed.wait(timeout=15)
                    try:
                        db.commit()
                        return "unexpected_success"
                    except StaleDataError:
                        db.rollback()
                        return "stale"
            with ThreadPoolExecutor(max_workers=1) as pool:
                pending = pool.submit(stale_writer)
                assert ready.wait(timeout=15)
                selected = http.put(f"{BASE}/{client_id}/retirement-planning-input/income-resolutions/{row['id']}",
                                    json=payload)
                assert selected.status_code == 200, selected.text
                proceed.set()
                assert pending.result(timeout=20) == "stale"
            with Session(engine) as db:
                current = db.get(RecurringIncome, row["id"])
                assert current.version == 2 and current.income_category == "rental"
                assert current.description == row["description"]
            print("GATE195_INCOME_CAS_RACE", {"resolution_status": 200,
                  "other_writer": "StaleDataError", "final_version": 2,
                  "no_silent_overwrite": True})
    finally:
        engine.dispose()


def test_195_concurrent_capital_editor_conflicts_with_canonical_reversal():
    engine = create_engine(os.environ["MIGRATION_DATABASE_URL"])
    try:
        with httpx.Client(timeout=20) as http:
            client_id = new_client(http, "CONVERSION-RACE")
        with Session(engine) as db, db.begin():
            product = create_product(db, client_id, ProductCreate(
                product_name="PKG195 synthetic conversion", product_type="קופת גמל",
                reported_product_total="100.00"), "test")
            snapshot = product_response(db, product)
            metadata = {k: snapshot[k] for k in ProductCreate.model_fields}
            product = update_product(db, client_id, product.product_id,
                ProductUpdate(**metadata, expected_version=1,
                    components={code: "100.00" if i == 5 else "0.00"
                                for i, code in enumerate(COMPONENT_CODES)}), "test")
            component = db.scalar(select(PensionProductComponent).where(
                PensionProductComponent.product_id == product.product_id,
                PensionProductComponent.component_code == COMPONENT_CODES[5]))
            source = (product.product_id, component.component_id, product.version)
        with Session(engine) as db, db.begin():
            made = conversion.execute(db, client_id, conversion_request(source), "test")
        converted = made["conversions"][0]
        asset_id = converted["destination_id"]
        conversion_id = converted["conversion_id"]
        ready, proceed = Event(), Event()
        def stale_editor():
            with Session(engine) as db:
                asset = db.get(CapitalAsset, asset_id)
                assert asset.version == 1 and asset.lifecycle_status == "current"
                asset.asset_description = "MUST NEVER PERSIST STALE EDIT"
                ready.set()
                assert proceed.wait(timeout=15)
                try:
                    db.commit()
                    return "unexpected_success"
                except StaleDataError:
                    db.rollback()
                    return "stale"
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(stale_editor)
            assert ready.wait(timeout=15)
            undo = ReversalRequest(expected_conversion_version=1,
                    expected_product_version=made["product_version"],
                    idempotency_key="pkg195-" + uuid4().hex,
                    reason="PKG195 synthetic reversal")
            with Session(engine) as db, db.begin():
                reversed_result = conversion.reverse(db, client_id, conversion_id, undo, "test")
            proceed.set()
            assert pending.result(timeout=20) == "stale"
        with Session(engine) as db:
            capital = db.get(CapitalAsset, asset_id)
            assert capital.lifecycle_status == "superseded" and capital.version == 2
            assert capital.asset_description != "MUST NEVER PERSIST STALE EDIT"
            assert db.execute(select(conversions.c.status).where(
                    conversions.c.conversion_id == conversion_id)).scalar_one() == "reversed"
            component = db.get(PensionProductComponent, source[1])
            assert component.balance == Decimal("100.00")
        print("GATE195_CONVERSION_CAS_RACE", {
            "conversion_id": conversion_id, "final_capital_version": 2,
            "other_writer": "StaleDataError", "reversal": reversed_result["status"],
            "no_silent_overwrite": True})
    finally:
        engine.dispose()
