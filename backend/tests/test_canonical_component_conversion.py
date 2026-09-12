from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.pension_product import COMPONENT_CODES, PensionProductComponent
from app.models.retirement_facts import CapitalAsset
from app.schemas.pension_product import ProductCreate, ProductUpdate
from app.schemas.canonical_conversion import ConversionRequest, ReversalRequest
from app.services.pension_product_service import create_product, update_product, product_response, PensionProductError
from app.services.canonical_component_conversion_service import execute, reverse, preview
from app.services.canonical_conversion_matrix import destinations
from test_recovery_pension_products import engine
from app.models.canonical_conversion import conversions, allocations, pensions, reversals
from app.models.pension_product import PensionProductAuditEvent
from sqlalchemy import func, text
from sqlalchemy.exc import IntegrityError


def seeded(engine, component=5, balance="100.00", product_type="קופת גמל"):
    with Session(engine) as db, db.begin():
        p = create_product(db, 1, ProductCreate(product_name="בדיקה", product_type=product_type, reported_product_total=balance), "test")
        snapshot = product_response(db, p)
        metadata = {k: snapshot[k] for k in ProductCreate.model_fields}
        p = update_product(db, 1, p.product_id, ProductUpdate(**metadata, expected_version=1,
            components={code: balance if i == component else "0.00" for i, code in enumerate(COMPONENT_CODES)}), "test")
        row = db.scalar(select(PensionProductComponent).where(PensionProductComponent.product_id == p.product_id,
            PensionProductComponent.component_code == COMPONENT_CODES[component]))
        return p.product_id, row.component_id, p.version


def request(source, component=5, amount="40.00", destination="capital", key=None):
    product, row, version = source
    return ConversionRequest(product_id=product, expected_product_version=version, destination_type=destination,
        effective_date=date(2026, 9, 11), idempotency_key=key or uuid4().hex,
        selections=[{"component_id": row, "component_code": COMPONENT_CODES[component], "amount": amount}],
        pension={"pension_start_date": date(2030, 1, 1)} if destination == "pension" else None)


@pytest.mark.parametrize("index,pension,capital", [(0,None,None),(1,"exempt","capital_gains"),(2,None,None),(3,None,None),
    (4,"taxable",None),(5,"taxable","exempt"),(6,"taxable",None),(7,"taxable",None),(8,"taxable","exempt"),(9,"taxable",None),(10,"taxable",None)])
def test_complete_matrix(index, pension, capital):
    actual = destinations(COMPONENT_CODES[index], "קופת גמל")
    assert actual.get("pension") == pension and actual.get("capital") == capital


@pytest.mark.parametrize("kind,capital", [("קרן השתלמות","exempt"),("education_fund","exempt"),("klal_stud","exempt"),
    ("קופת גמל להשקעה","capital_gains"),("investment_provident_fund","capital_gains")])
def test_all_component_overrides(kind, capital):
    for code in COMPONENT_CODES:
        assert destinations(code, kind) == {"pension":"exempt", "capital":capital}


@pytest.mark.parametrize("destination", ["capital", "pension"])
@pytest.mark.parametrize("amount,remaining", [("40.00", "60.00"),("100.00","0.00")])
def test_conversion_and_full_reversal(engine, destination, amount, remaining):
    source = seeded(engine)
    req = request(source, amount=amount, destination=destination)
    with Session(engine) as db, db.begin():
        result = execute(db, 1, req, "test")
    with Session(engine) as db, db.begin():
        assert execute(db, 1, req, "test") == result
        row = db.get(PensionProductComponent, source[1])
        assert row.balance == Decimal(remaining)
        if destination == "pension":
            pension = db.execute(select(pensions)).mappings().one()
            assert Decimal(pension["monthly_numerator"]) == Decimal(amount)
            assert pension["monthly_denominator"] == pension["annuity_factor_text"]
            assert pension["tax_treatment"] == "taxable"
        if destination == "capital":
            asset = db.scalar(select(CapitalAsset).where(CapitalAsset.conversion_id == result["conversions"][0]["conversion_id"]))
            assert asset.known_value_amount == Decimal(amount)
    cid = result["conversions"][0]["conversion_id"]
    reversal = ReversalRequest(expected_conversion_version=1, expected_product_version=result["product_version"], idempotency_key="undo", reason="בדיקה")
    with Session(engine) as db, db.begin():
        undone = reverse(db, 1, cid, reversal, "test")
    with Session(engine) as db, db.begin():
        assert reverse(db, 1, cid, reversal, "test") == undone
        assert db.get(PensionProductComponent, source[1]).balance == Decimal("100.00")
        event = db.scalar(select(PensionProductAuditEvent).where(PensionProductAuditEvent.action == "reversal"))
        assert event.actor == "test"
        assert event.snapshot["operation"]["allocations"][0]["before"] == remaining
        assert event.snapshot["operation"]["allocations"][0]["after"] == "100.00"
        if destination == "capital":
            assert db.get(CapitalAsset, result["conversions"][0]["destination_id"]).lifecycle_status == "superseded"


@pytest.mark.parametrize("amount,code", [("0","INVALID_CONVERSION_AMOUNT"),("-1","INVALID_CONVERSION_AMOUNT"),("0.001","INVALID_CONVERSION_AMOUNT"),("101","OVER_CONVERSION")])
def test_rejected_amount_no_mutation(engine, amount, code):
    source = seeded(engine)
    with Session(engine) as db:
        with pytest.raises(PensionProductError) as error:
            execute(db, 1, request(source, amount=amount), "test")
        assert error.value.code == code
        db.rollback()
        assert db.get(PensionProductComponent, source[1]).balance == Decimal("100.00")


@pytest.mark.parametrize("change,code", [
    ({"expected_product_version": 1}, "STALE_PRODUCT_VERSION"),
    ({"selections": [{"component_id": "wrong", "component_code": COMPONENT_CODES[5]}]}, "CONVERSION_SOURCE_MISMATCH"),
    ({"selections": [{"component_id": "wrong", "component_code": "תגמולים"}]}, "NON_CANONICAL_COMPONENT"),
    ({"selections": [{"component_id": "wrong", "component_code": "reported_product_total"}]}, "RECONCILIATION_VALUE_NOT_CONVERTIBLE"),
])
def test_invalid_authority_is_atomic(engine, change, code):
    source = seeded(engine)
    req = ConversionRequest.model_validate({**request(source).model_dump(), **change})
    with Session(engine) as db:
        with pytest.raises(PensionProductError) as failure:
            execute(db, 1, req, "test")
        assert failure.value.code == code
        db.rollback()
        assert db.scalar(select(func.count()).select_from(conversions)) == 0
        assert db.get(PensionProductComponent, source[1]).balance == Decimal("100.00")


def test_whole_product_mixed_tax_and_skip_reconciliation(engine):
    source = seeded(engine, component=1)
    with Session(engine) as db, db.begin():
        for row in db.scalars(select(PensionProductComponent).where(PensionProductComponent.product_id == source[0])):
            if row.component_code in (COMPONENT_CODES[0], COMPONENT_CODES[5]):
                row.balance = Decimal("50.01")
    req = request(source, component=1).model_copy(update={"whole_product": True, "selections": []})
    with Session(engine) as db, db.begin():
        p = preview(db, 1, req)
        assert {g["tax_treatment"] for g in p["groups"]} == {"exempt", "capital_gains"}
        assert [s["component_code"] for s in p["skipped"]] == [COMPONENT_CODES[0]]
        result = execute(db, 1, req, "planner-test")
        assert result["product_version"] == 3
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(conversions)) == 2
        assert db.scalar(select(func.count()).select_from(PensionProductComponent)) == 11
        assert sum((a.known_value_amount for a in db.scalars(select(CapitalAsset))), Decimal(0)) == Decimal("150.01")
        rows = db.execute(select(allocations)).mappings().all()
        assert {r["tax_treatment"] for r in rows} == {"exempt", "capital_gains"}
        assert all(r["source_balance_after"] == 0 for r in rows)


def test_idempotency_conflict_double_reversal_and_history_guards(engine):
    source = seeded(engine)
    req = request(source, destination="pension")
    with Session(engine) as db, db.begin():
        result = execute(db, 1, req, "test")
    with Session(engine) as db:
        with pytest.raises(PensionProductError, match="מפתח") as failure:
            execute(db, 1, req.model_copy(update={"effective_date": date(2027, 1, 1)}), "test")
        assert failure.value.code == "IDEMPOTENCY_CONFLICT"
    cid = result["conversions"][0]["conversion_id"]
    undo = ReversalRequest(expected_conversion_version=1, expected_product_version=3, idempotency_key="undo", reason="test")
    with Session(engine) as db, db.begin():
        reverse(db, 1, cid, undo, "test")
    with Session(engine) as db:
        with pytest.raises(PensionProductError) as failure:
            reverse(db, 1, cid, undo.model_copy(update={"idempotency_key": "again"}), "test")
        assert failure.value.code == "CONVERSION_ALREADY_REVERSED"
    for statement in (allocations.update().values(amount="1"), reversals.update().values(reason="changed"), pensions.delete(), conversions.delete()):
        with engine.connect() as connection:
            with pytest.raises(IntegrityError, match="CANONICAL_CONVERSION_HISTORY_IMMUTABLE"):
                connection.execute(statement)
            connection.rollback()


def test_downstream_fk_blocks_full_reversal_without_mutation(engine):
    source = seeded(engine)
    with Session(engine) as db, db.begin():
        result = execute(db, 1, request(source, destination="pension"), "test")
    cid = result["conversions"][0]["conversion_id"]
    with engine.begin() as db:
        db.execute(text("CREATE TABLE downstream_test (id INTEGER PRIMARY KEY, conversion_id VARCHAR(64) REFERENCES canonical_conversions(conversion_id))"))
        db.execute(text("INSERT INTO downstream_test VALUES(1,:cid)"), {"cid": cid})
    with Session(engine) as db:
        with pytest.raises(PensionProductError) as failure:
            reverse(db, 1, cid, ReversalRequest(expected_conversion_version=1, expected_product_version=3, idempotency_key="undo", reason="test"), "test")
        assert failure.value.code == "DESTINATION_HAS_DOWNSTREAM_USAGE"
        db.rollback()
        assert db.get(PensionProductComponent, source[1]).balance == Decimal("60.00")
        assert db.scalar(select(pensions.c.status)) == "active"


def test_invalid_explicit_batch_and_late_mixed_batch_failure_rollback(engine, monkeypatch):
    from app.services import canonical_component_conversion_service as service
    source = seeded(engine)
    with Session(engine) as db, db.begin():
        row = db.scalar(select(PensionProductComponent).where(PensionProductComponent.product_id == source[0], PensionProductComponent.component_code == COMPONENT_CODES[1]))
        row.balance = Decimal("20.01")
    good = request(source)
    bad = ConversionRequest.model_validate({**good.model_dump(), "selections": [*good.model_dump()["selections"], {"component_id": "other", "component_code": COMPONENT_CODES[1], "amount": "1.00"}]})
    with Session(engine) as db:
        with pytest.raises(PensionProductError):
            execute(db, 1, bad, "test")
        db.rollback()
        assert db.scalar(select(func.count()).select_from(conversions)) == 0
    def broken_audit(*args, **kwargs):
        raise RuntimeError("late failure")
    monkeypatch.setattr(service, "audit", broken_audit)
    with pytest.raises(RuntimeError, match="late failure"):
        with Session(engine) as db, db.begin():
            execute(db, 1, good.model_copy(update={"whole_product": True, "selections": []}), "test")
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(conversions)) == 0
        assert db.scalar(select(func.count()).select_from(CapitalAsset)) == 0
        assert db.get(PensionProductComponent, source[1]).balance == Decimal("100.00")


def test_invalid_pair_zero_whole_batch_and_component_code_mismatch(engine):
    source = seeded(engine, component=4)
    with Session(engine) as db:
        with pytest.raises(PensionProductError) as failure:
            execute(db, 1, request(source, component=4), "test")
        assert failure.value.code == "INVALID_COMPONENT_DESTINATION"
        db.rollback()
        with pytest.raises(PensionProductError) as failure:
            execute(db, 1, request(source, component=5), "test")
        assert failure.value.code == "CONVERSION_SOURCE_MISMATCH"
        db.rollback()
        with pytest.raises(PensionProductError) as failure:
            execute(db, 1, request(source, component=4).model_copy(update={"whole_product": True, "selections": []}), "test")
        assert failure.value.code == "NO_ELIGIBLE_COMPONENTS"
