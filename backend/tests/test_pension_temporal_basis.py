from datetime import date, datetime, timezone
from types import SimpleNamespace

import ast
import hashlib
import json
import pytest
from sqlalchemy import inspect, select, text, update
from sqlalchemy.orm import Session

from app.models.canonical_conversion import batches, conversions, pensions
from app.models.client import Client
from app.models.canonical_manual_pension_source import CanonicalManualPensionSource as Manual
from app.models.canonical_pension_temporal_decision import CanonicalPensionTemporalDecision as Decision
from app.models.planning_input_decision import PlanningInputDecision
from app.schemas.canonical_manual_pension_source import (
    ConversionTemporalDecisionWrite,
    ManualPensionInput,
    ManualPensionUpdate,
    TemporalAuthorityInput,
)
from app.services import canonical_manual_pension_service as manual_service
from app.services import pension_temporal_basis_service as temporal
from app.services.canonical_component_conversion_service import execute, reverse
from app.schemas.canonical_conversion import ReversalRequest
from app.services.pension_monthly_basis_service import canonical_bytes
from app.services.professional_source_snapshot_service import snapshot
from app.services.planning_input_service import derive as planning_input
from app.services.pension_product_service import PensionProductError
from test_canonical_component_conversion import request, seeded
from test_recovery_pension_products import engine


GOLDEN = {
    "A": ('{"annual_rate":null,"contract_version":"canonical-pension-temporal-indexation-semantic-v1","rate_basis":null,"temporal_authority_kind":"none","temporal_origin_date":"2030-01-15"}', "e0e454b1cbdebe20564b6ccf176de6fb9a497a32c7430383dc43871c375729cd"),
    "B": ('{"annual_rate":"0.02","contract_version":"canonical-pension-temporal-indexation-semantic-v1","rate_basis":"ANNUAL_EFFECTIVE","temporal_authority_kind":"fixed_manual","temporal_origin_date":"2030-01-15"}', "60d341b65b82ad8545675d9c524d41eb74795e742c06b8e8b4754b817ee0e4b3"),
    "C": ('{"amount_authority_kind":"entered_monthly_amount","client_id":42,"contract_version":"canonical-pension-temporal-indexation-source-v1","provenance":{"base_amount_effective_date":"2030-01-15","lifecycle_status":"current","manual_pension_source_id":"manual-001","raw_fixed_indexation_rate":null,"raw_indexation_method":"none","temporal_authority_explicit":true},"source_id":"manual:manual-001","source_kind":"manual","temporal_authority_ready":true,"temporal_blockers":[],"temporal_semantic_fingerprint":"e0e454b1cbdebe20564b6ccf176de6fb9a497a32c7430383dc43871c375729cd"}', "f69ffda475db596b27ec1e542f9bb6787a3a92c7b31128898d84256540d6925d"),
    "D": ('{"amount_authority_kind":"manual_balance_ratio","client_id":42,"contract_version":"canonical-pension-temporal-indexation-source-v1","provenance":{"base_amount_effective_date":"2030-01-15","lifecycle_status":"current","manual_pension_source_id":"manual-legacy-001","raw_fixed_indexation_rate":null,"raw_indexation_method":"cpi","temporal_authority_explicit":false},"source_id":"manual:manual-legacy-001","source_kind":"manual","temporal_authority_ready":false,"temporal_blockers":["TEMPORAL_CPI_NOT_AUTHORIZED"],"temporal_semantic_fingerprint":null}', "655ccf8e76aad01a32ff31b823fbab2394c287059a7d96b1967db641e7b7d1c8"),
    "E": ('{"amount_authority_kind":"persisted_conversion_ratio","client_id":42,"contract_version":"canonical-pension-temporal-indexation-source-v1","provenance":{"actor":"planner:demo","conversion_effective_date":"2030-01-15","conversion_id":"conversion-001","conversion_status":"active","decided_at":"2026-09-28T12:00:00.000000Z","decision_version":1,"destination_status":"active","destination_version":3,"pension_destination_id":"pension-destination-001","rate_basis":null,"raw_annual_rate_text":null,"raw_authority_kind":"none","source_version_at_decision":3},"source_id":"conversion:pension-destination-001","source_kind":"conversion","temporal_authority_ready":true,"temporal_blockers":[],"temporal_semantic_fingerprint":"e0e454b1cbdebe20564b6ccf176de6fb9a497a32c7430383dc43871c375729cd"}', "d3be1c1d5599fe9afefc0395f197d7114b3e28187f7d5d71ea6523f922a03acb"),
    "F": ('{"amount_authority_kind":"persisted_conversion_ratio","client_id":42,"contract_version":"canonical-pension-temporal-indexation-source-v1","provenance":{"actor":"planner:demo","conversion_effective_date":"2030-01-15","conversion_id":"conversion-001","conversion_status":"active","decided_at":"2026-09-28T12:00:00.000000Z","decision_version":1,"destination_status":"active","destination_version":4,"pension_destination_id":"pension-destination-001","rate_basis":null,"raw_annual_rate_text":null,"raw_authority_kind":"none","source_version_at_decision":3},"source_id":"conversion:pension-destination-001","source_kind":"conversion","temporal_authority_ready":false,"temporal_blockers":["TEMPORAL_CONVERSION_DECISION_STALE"],"temporal_semantic_fingerprint":null}', "092c11e245518f99934ee87b6dd23711c7c7f42be2a319d4c2597eba62813e5d"),
}


def _manual(identifier, *, mode="entered", method="none", rate=None, explicit=True):
    return SimpleNamespace(client_id=42, manual_pension_source_id=identifier,
        lifecycle_status="current", base_amount_effective_date=date(2030, 1, 15),
        indexation_method=method, fixed_indexation_rate=rate,
        temporal_authority_explicit=explicit, input_mode=mode)


def _conversion(version, decision_version=1, source_version=3):
    destination = dict(pension_destination_id="pension-destination-001", client_id=42,
        conversion_id="conversion-001", effective_date=date(2030, 1, 15), status="active", version=version)
    conversion = dict(conversion_id="conversion-001", client_id=42, batch_id="batch-001",
        destination_type="pension", status="active")
    batch = dict(batch_id="batch-001", client_id=42, effective_date=date(2030, 1, 15))
    decision = SimpleNamespace(client_id=42, pension_destination_id="pension-destination-001",
        authority_kind="none", annual_rate_text=None, rate_basis=None,
        source_version_at_decision=source_version, version=decision_version,
        actor="planner:demo", decided_at=datetime(2026, 9, 28, 12, tzinfo=timezone.utc))
    return destination, conversion, batch, decision


def _source_payload(result):
    return dict(contract_version=temporal.SOURCE, client_id=42, source_id=result["source_id"],
        source_kind=result["source_kind"], amount_authority_kind=(
            "persisted_conversion_ratio" if result["source_kind"] == "conversion" else
            "entered_monthly_amount" if result["source_id"] == "manual:manual-001" else "manual_balance_ratio"),
        temporal_semantic_fingerprint=result["temporal_semantic_fingerprint"],
        temporal_authority_ready=result["temporal_authority_ready"],
        temporal_blockers=result["temporal_blockers"], provenance=result["provenance"])


@pytest.mark.parametrize("name", list("ABCDEF"))
def test_accepted_golden_vectors_exact_bytes_and_hashes(name):
    exact, expected = GOLDEN[name]
    if name == "A":
        payload = dict(contract_version=temporal.SEMANTIC, temporal_authority_kind="none",
            temporal_origin_date="2030-01-15", annual_rate=None, rate_basis=None)
    elif name == "B":
        payload = dict(contract_version=temporal.SEMANTIC, temporal_authority_kind="fixed_manual",
            temporal_origin_date="2030-01-15", annual_rate="0.02", rate_basis=temporal.RATE_BASIS)
    elif name == "C":
        payload = _source_payload(temporal.manual(_manual("manual-001"), 42))
    elif name == "D":
        payload = _source_payload(temporal.manual(_manual("manual-legacy-001", mode="calculated", method="cpi", explicit=False), 42))
    else:
        args = _conversion(3 if name == "E" else 4)
        payload = _source_payload(temporal.conversion(None, 42, *args))
    actual = canonical_bytes(payload)
    assert actual == exact.encode("utf-8")
    assert hashlib.sha256(actual).hexdigest() == expected
    assert temporal.fingerprint(payload) == expected


@pytest.mark.parametrize("raw,expected", [
    ("000.0200", "0.02"), ("+2e-2", "0.02"), ("1e2", "100"), (".5", "0.5"),
])
def test_exact_decimal_canonicalization(raw, expected):
    assert temporal.canonical_rate(raw) == expected


@pytest.mark.parametrize("raw,code", [
    (None, "TEMPORAL_FIXED_ANNUAL_RATE_MISSING"), ("0", "TEMPORAL_FIXED_ANNUAL_RATE_NOT_POSITIVE"),
    ("-0", "TEMPORAL_FIXED_ANNUAL_RATE_NOT_POSITIVE"), ("-1e-2", "TEMPORAL_FIXED_ANNUAL_RATE_NOT_POSITIVE"),
    (" 0.02", "TEMPORAL_FIXED_ANNUAL_RATE_INVALID"), ("2%", "TEMPORAL_FIXED_ANNUAL_RATE_INVALID"),
    ("NaN", "TEMPORAL_FIXED_ANNUAL_RATE_INVALID"), ("1e999999", "TEMPORAL_FIXED_ANNUAL_RATE_INVALID"),
    ("1e-999999", "TEMPORAL_FIXED_ANNUAL_RATE_INVALID"), ("1" * 129, "TEMPORAL_FIXED_ANNUAL_RATE_INVALID"),
])
def test_exact_decimal_rejections(raw, code):
    with pytest.raises(PensionProductError) as failure:
        temporal.canonical_rate(raw)
    assert failure.value.code == code


@pytest.mark.parametrize("method,rate", [
    (None, None),
    ("cpi", None),
    ("unknown", None),
    ("none", "0.02"),
])
def test_explicit_manual_authority_rejects_structurally_invalid_persisted_state_before_blockers(method, rate):
    row = _manual("invalid-explicit", method=method, rate=rate, explicit=True)
    row.base_amount_effective_date = None
    with pytest.raises(PensionProductError) as failure:
        temporal.manual(row, 42)
    assert failure.value.code == "TEMPORAL_DECISION_STRUCTURE_INVALID"


@pytest.mark.parametrize("method,rate,kind,canonical_rate", [
    ("none", None, "none", None),
    ("fixed", "0.02", "fixed_manual", "0.02"),
])
def test_explicit_manual_authority_accepts_canonical_persisted_state(method, rate, kind, canonical_rate):
    result = temporal.manual(_manual("valid-explicit", method=method, rate=rate, explicit=True), 42)
    assert result["temporal_authority_ready"] is True
    assert result["temporal_authority_kind"] == kind
    assert result["annual_rate"] == canonical_rate
    assert result["temporal_blockers"] == []


@pytest.mark.parametrize("method,rate,blocker", [
    (None, None, "TEMPORAL_AUTHORITY_MISSING"),
    ("none", None, "TEMPORAL_AUTHORITY_MISSING"),
    ("fixed", "0.02", "TEMPORAL_AUTHORITY_MISSING"),
    ("cpi", None, "TEMPORAL_CPI_NOT_AUTHORIZED"),
    ("unknown", None, "TEMPORAL_AUTHORITY_UNSUPPORTED"),
])
def test_legacy_manual_authority_preserves_visible_blocker_contract(method, rate, blocker):
    result = temporal.manual(_manual("legacy", method=method, rate=rate, explicit=False), 42)
    assert result["temporal_authority_ready"] is False
    assert result["temporal_authority_kind"] is None
    assert result["temporal_blockers"] == [blocker]


def _manual_payload(**changes):
    values = dict(input_mode="entered", payer_name="משלם", monthly_amount="100.00",
        pension_start_date=date(2040, 1, 1), base_amount_effective_date=date(2030, 1, 15),
        tax_treatment="taxable")
    values.update(changes)
    return ManualPensionInput(**values)


def test_manual_tri_state_and_legacy_write_rejection(engine):
    with Session(engine) as db, db.begin():
        omitted = manual_service.create(db, 1, _manual_payload())
        cleared = manual_service.create(db, 1, _manual_payload(temporal_authority=None))
        none = manual_service.create(db, 1, _manual_payload(temporal_authority={"authority_kind": "none"}))
        fixed = manual_service.create(db, 1, _manual_payload(temporal_authority={"authority_kind": "fixed_manual", "annual_rate": "+2e-2"}))
    with Session(engine) as db:
        rows = [db.get(Manual, item["manual_pension_source_id"]) for item in (omitted, cleared, none, fixed)]
        assert [(r.temporal_authority_explicit, r.indexation_method, r.fixed_indexation_rate) for r in rows] == [
            (False, None, None), (False, None, None), (True, "none", None), (True, "fixed", "0.02")]
    with Session(engine) as db:
        row = db.get(Manual, fixed["manual_pension_source_id"])
        before = (row.temporal_authority_explicit, row.indexation_method, row.fixed_indexation_rate)
    update_payload = ManualPensionUpdate(**_manual_payload(monthly_amount="101.00").model_dump(exclude={"temporal_authority"}), expected_version=1)
    with Session(engine) as db, db.begin():
        manual_service.change(db, 1, fixed["manual_pension_source_id"], update_payload)
    with Session(engine) as db:
        row = db.get(Manual, fixed["manual_pension_source_id"])
        assert (row.temporal_authority_explicit, row.indexation_method, row.fixed_indexation_rate) == before
    legacy = ManualPensionUpdate(**_manual_payload().model_dump(), indexation_method="none", expected_version=2)
    with Session(engine) as db, pytest.raises(PensionProductError) as failure:
        manual_service.change(db, 1, fixed["manual_pension_source_id"], legacy)
    assert failure.value.code == "TEMPORAL_DECISION_PAYLOAD_INVALID"


def _created_conversion(engine):
    source = seeded(engine)
    with Session(engine) as db, db.begin():
        result = execute(db, 1, request(source, destination="pension"), "test")
    return source, result["conversions"][0]["destination_id"], result["conversions"][0]["conversion_id"]


def _decision(source_version, decision_version, kind="none", rate=None, actor="planner"):
    return ConversionTemporalDecisionWrite(expected_source_version=source_version,
        expected_decision_version=decision_version,
        temporal_authority=TemporalAuthorityInput(authority_kind=kind, annual_rate=rate), actor=actor)


def test_conversion_create_update_noop_and_stale_precedence(engine):
    _, destination_id, _ = _created_conversion(engine)
    with Session(engine) as db, db.begin():
        created = temporal.write_conversion(db, 1, destination_id, _decision(1, 0))
    assert created["outcome"] == "TEMPORAL_DECISION_CREATED"
    with Session(engine) as db, db.begin():
        unchanged = temporal.write_conversion(db, 1, destination_id, _decision(1, 1, actor="ignored"))
    assert unchanged["outcome"] == "TEMPORAL_DECISION_UNCHANGED"
    with Session(engine) as db:
        row = db.get(Decision, destination_id)
        unchanged_metadata = (row.version, row.actor, row.decided_at, row.source_version_at_decision)
    with Session(engine) as db, db.begin():
        updated = temporal.write_conversion(db, 1, destination_id, _decision(1, 1, "fixed_manual", "2e-2"))
    assert updated["outcome"] == "TEMPORAL_DECISION_UPDATED"
    with Session(engine) as db:
        row = db.get(Decision, destination_id)
        assert (row.version, row.annual_rate_text, row.rate_basis) == (2, "0.02", "ANNUAL_EFFECTIVE")
    with Session(engine) as db, pytest.raises(PensionProductError) as failure:
        temporal.write_conversion(db, 1, destination_id, _decision(2, 1))
    assert failure.value.code == "TEMPORAL_SOURCE_VERSION_STALE"
    with Session(engine) as db, pytest.raises(PensionProductError) as failure:
        temporal.write_conversion(db, 1, destination_id, _decision(1, 1))
    assert failure.value.code == "TEMPORAL_DECISION_VERSION_STALE"
    assert unchanged_metadata[0] == 1


def test_same_semantics_stale_binding_is_reauthorized(engine):
    _, destination_id, _ = _created_conversion(engine)
    with Session(engine) as db, db.begin():
        created = temporal.write_conversion(db, 1, destination_id, _decision(1, 0))
        initial_semantic = created["temporal_authority"]["temporal_semantic_fingerprint"]
        initial_source = created["temporal_authority"]["temporal_source_fingerprint"]
    # This fixture simulates a future synchronized destination writer. The
    # production archive guard intentionally exposes no such writer today;
    # removing only its test-database trigger allows the accepted rebind state
    # machine to be exercised without weakening production DDL.
    with engine.begin() as connection:
        connection.exec_driver_sql("DROP TRIGGER trg_canonical_pension_destinations_canonical_update")
        connection.execute(update(pensions).where(
            pensions.c.pension_destination_id == destination_id).values(version=2))
    with Session(engine) as db:
        destination = db.execute(select(pensions).where(
            pensions.c.pension_destination_id == destination_id)).mappings().one()
        conversion_row = db.execute(select(conversions).where(
            conversions.c.conversion_id == destination["conversion_id"])).mappings().one()
        batch = db.execute(select(batches).where(
            batches.c.batch_id == conversion_row["batch_id"])).mappings().one()
        stale = temporal.conversion(db, 1, destination, conversion_row, batch)
        assert stale["temporal_blockers"] == ["TEMPORAL_CONVERSION_DECISION_STALE"]
    with Session(engine) as db, db.begin():
        result = temporal.write_conversion(db, 1, destination_id, _decision(2, 1, actor="reauthorizer"))
    assert result["outcome"] == "TEMPORAL_DECISION_REAUTHORIZED"
    assert result["decision_version"] == 2 and result["source_version_at_decision"] == 2
    assert result["temporal_authority"]["temporal_semantic_fingerprint"] == initial_semantic
    assert result["temporal_authority"]["temporal_source_fingerprint"] != initial_source
    with Session(engine) as db:
        row = db.get(Decision, destination_id)
        assert row.actor == "reauthorizer"


def test_reversal_preserves_decision_and_makes_source_not_current(engine):
    source, destination_id, conversion_id = _created_conversion(engine)
    with Session(engine) as db, db.begin():
        temporal.write_conversion(db, 1, destination_id, _decision(1, 0))
    with Session(engine) as db, db.begin():
        reverse(db, 1, conversion_id, ReversalRequest(expected_conversion_version=1,
            expected_product_version=3, idempotency_key="temporal-reversal", reason="test"), "test")
    with Session(engine) as db:
        assert db.get(Decision, destination_id) is not None
        destination = db.execute(select(pensions).where(pensions.c.pension_destination_id == destination_id)).mappings().one()
        conversion = db.execute(select(conversions).where(conversions.c.conversion_id == conversion_id)).mappings().one()
        batch = db.execute(select(batches).where(batches.c.batch_id == conversion["batch_id"])).mappings().one()
        with pytest.raises(PensionProductError) as failure:
            temporal.conversion(db, 1, destination, conversion, batch)
        assert failure.value.code == "TEMPORAL_SOURCE_NOT_CURRENT"


def test_conversion_lifecycle_and_effective_date_structure_precedence():
    destination, conversion, batch, decision = _conversion(3)
    cases = [
        ({**conversion, "status": "reversed"}, {**destination, "status": "reversed"}, batch, "TEMPORAL_SOURCE_NOT_CURRENT"),
        (conversion, {**destination, "status": "reversed"}, batch, "TEMPORAL_SOURCE_STRUCTURE_INVALID"),
        ({**conversion, "status": "reversed"}, destination, batch, "TEMPORAL_SOURCE_STRUCTURE_INVALID"),
        (conversion, {**destination, "effective_date": None}, batch, "TEMPORAL_SOURCE_STRUCTURE_INVALID"),
        (conversion, destination, {**batch, "effective_date": date(2030, 1, 16)}, "TEMPORAL_SOURCE_STRUCTURE_INVALID"),
    ]
    for conversion_row, destination_row, batch_row, code in cases:
        with pytest.raises(PensionProductError) as failure:
            temporal.conversion(None, 42, destination_row, conversion_row, batch_row, decision)
        assert failure.value.code == code


def test_registry_is_sorted_and_source_specific():
    a = temporal.manual(_manual("b"), 42)
    b = temporal.manual(_manual("a"), 42)
    assert a["temporal_semantic_fingerprint"] == b["temporal_semantic_fingerprint"]
    assert a["temporal_source_fingerprint"] != b["temporal_source_fingerprint"]
    assert temporal.registry(42, [a, b]) == temporal.registry(42, [b, a])


def test_manual_fingerprint_ignores_unrelated_fields_and_orders_independent_blockers():
    row = _manual("stable")
    row.payer_name = "first"
    row.description = "description"
    row.pension_start_date = date(2040, 1, 1)
    row.source_reference = "reference"
    row.source_note = "note"
    row.version = 1
    initial = temporal.manual(row, 42)
    row.payer_name = "second"
    row.description = "changed"
    row.pension_start_date = date(2050, 1, 1)
    row.source_reference = "other"
    row.source_note = "changed"
    row.version = 999
    assert temporal.manual(row, 42) == initial
    row.temporal_authority_explicit = False
    row.indexation_method = "cpi"
    row.base_amount_effective_date = None
    blocked = temporal.manual(row, 42)
    assert blocked["temporal_blockers"] == [
        "TEMPORAL_CPI_NOT_AUTHORIZED", "TEMPORAL_ORIGIN_DATE_MISSING"]
    assert len(blocked["temporal_blockers"]) == len(set(blocked["temporal_blockers"]))


def test_snapshot_temporal_fields_do_not_expand_legacy_source_state_fingerprint(engine):
    with Session(engine) as db, db.begin():
        manual_service.create(db, 1, _manual_payload(
            temporal_authority={"authority_kind": "none"}))
    with Session(engine) as db:
        result = snapshot(db, 1, as_of=date(2026, 9, 29))
    legacy = {k: v for k, v in result.items() if k not in (
        "source_state_fingerprint", "pension_temporal_authority_registry_fingerprint")}
    legacy["pension_sources"] = [{k: v for k, v in source.items() if k not in (
        "has_started", "started_as_of", "temporal_authority", "temporal_authority_explicit")}
        for source in result["pension_sources"]]
    expected = hashlib.sha256(json.dumps(legacy, sort_keys=True, ensure_ascii=False,
        separators=(",", ":")).encode()).hexdigest()
    assert result["source_state_fingerprint"] == expected


def test_planning_input_fingerprint_matches_pre_temporal_golden_fixture(engine):
    """Lock the pre-package planning-input boundary to a fixed persisted fixture."""
    fixed = datetime(2026, 1, 2, 3, 4, 5)
    with Session(engine) as db, db.begin():
        client = db.get(Client, 1)
        client.created_at = fixed
        client.updated_at = fixed
        db.add(PlanningInputDecision(client_id=1, version=1,
            planning_base_date=date(2030, 1, 15), actor="golden", updated_at=fixed))
        db.add(Manual(manual_pension_source_id="manual-temporal-golden", client_id=1,
            input_mode="entered", payer_name="Golden payer", description="Golden source",
            source_reference="golden-reference", monthly_amount="100.00", balance=None,
            annuity_factor=None, pension_start_date=date(2040, 1, 1),
            base_amount_effective_date=date(2030, 1, 15), tax_treatment="taxable",
            indexation_method="none", fixed_indexation_rate=None,
            temporal_authority_explicit=True, source_note="golden-note",
            lifecycle_status="current", version=1, created_at=fixed, updated_at=fixed))
    with Session(engine) as db:
        result = planning_input(db, 1)
    assert result["planning_input_fingerprint"] == (
        "cb08f3301b80bc5b311384d009ea8debf38136bcf09f3f938083d5c42260f645"
    )


def test_temporal_package_has_no_cpi_execution_dependency():
    path = __import__("pathlib").Path(temporal.__file__)
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    assert not any("cbs" in name.lower() or "fixation" in name.lower() or "cpi" in name.lower()
                   for name in imported)


def test_sqlite_additive_migration_backfill_and_downgrade_guards(tmp_path):
    from test_canonical_conversion_migration import migrate
    url = "sqlite:///" + (tmp_path / "temporal.db").as_posix()
    migrate(url, "upgrade", "e0f6b3c9d187")
    from sqlalchemy import create_engine
    db_engine = create_engine(url)
    with db_engine.begin() as db:
        db.execute(text("INSERT INTO clients(client_id,display_name,id_number) VALUES(1,'test','123')"))
        db.execute(text("INSERT INTO canonical_manual_pension_sources "
            "(manual_pension_source_id,client_id,input_mode,monthly_amount,indexation_method,fixed_indexation_rate) "
            "VALUES('legacy-none',1,'entered','100.00','none',NULL),"
            "('legacy-fixed',1,'entered','100.00','fixed','0.02'),"
            "('legacy-cpi',1,'entered','100.00','cpi',NULL)"))
    migrate(url, "upgrade", "f1a7c4d0e298")
    columns = {column["name"]: column for column in inspect(db_engine).get_columns("canonical_manual_pension_sources")}
    assert not columns["temporal_authority_explicit"]["nullable"]
    assert columns["temporal_authority_explicit"]["default"] is None
    assert "canonical_pension_temporal_decisions" in inspect(db_engine).get_table_names()
    with db_engine.connect() as db:
        rows = db.execute(text("SELECT indexation_method,fixed_indexation_rate,temporal_authority_explicit "
            "FROM canonical_manual_pension_sources ORDER BY manual_pension_source_id")).all()
        assert rows == [("cpi", None, 0), ("fixed", "0.02", 0), ("none", None, 0)]
    migrate(url, "downgrade", "e0f6b3c9d187")
    assert "temporal_authority_explicit" not in {
        column["name"] for column in inspect(db_engine).get_columns("canonical_manual_pension_sources")}
    migrate(url, "upgrade", "f1a7c4d0e298")
    with db_engine.begin() as db:
        db.execute(text("UPDATE canonical_manual_pension_sources SET temporal_authority_explicit=1, "
                        "indexation_method='none' WHERE manual_pension_source_id='legacy-none'"))
    failure = migrate(url, "downgrade", "e0f6b3c9d187", success=False)
    assert "PENSION_TEMPORAL_DOWNGRADE_WOULD_LOSE_EXPLICIT_AUTHORITY" in failure
    with db_engine.begin() as db:
        db.execute(text("UPDATE canonical_manual_pension_sources SET temporal_authority_explicit=0 "
                        "WHERE manual_pension_source_id='legacy-none'"))
        db.execute(text("INSERT INTO canonical_pension_temporal_decisions VALUES "
            "('missing-destination',1,'none',NULL,NULL,1,1,'test',CURRENT_TIMESTAMP)"))
    # FK enforcement is connection-specific in this migration fixture; the
    # downgrade guard must still reject persisted professional decisions.
    failure = migrate(url, "downgrade", "e0f6b3c9d187", success=False)
    assert "PENSION_TEMPORAL_DOWNGRADE_WOULD_LOSE_DECISIONS" in failure
    db_engine.dispose()
