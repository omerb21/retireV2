"""SC-04: actual canonical registry in the same PostgreSQL scenario snapshot.

No canonical producer mocks; isolated schema in dedicated local test DB.
"""
from datetime import date
from decimal import Decimal
import os
import uuid
from urllib.parse import urlsplit

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

from app.db.base import Base, load_all_models
from app.models.client import Client
from app.models.pension_product import PensionProduct, PensionProductComponent, PensionProductAuditEvent
from app.models.scenario_draft import ScenarioDraft, ScenarioDraftDecision
from app.models.canonical_manual_pension_source import CanonicalManualPensionSource
from app.models.canonical_pension_temporal_decision import CanonicalPensionTemporalDecision
from app.models.canonical_conversion import batches, conversions, allocations, pensions
from app.models.retirement_facts import CapitalAsset, RetirementTimingWorkIntention
from app.models.client_profile import ClientProfile
from app.models.employment_record import EmploymentRecord
from app.services.scenario_draft_service import _source_evidence
from app.services.scenario_pension_source_bridge_service import build_pension_source_bridge_snapshot

load_all_models()


def _url():
    value = os.getenv("SCENARIO_TEST_POSTGRES_URL")
    if not value:
        pytest.skip("dedicated PostgreSQL test URL absent")
    parsed = urlsplit(value)
    if parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        pytest.fail("local PostgreSQL required")
    if parsed.path != "/retire_v2_scenario_test":
        pytest.fail("only retire_v2_scenario_test permitted")
    return value


def _dependent_tables(*tables):
    """Include foreign-key dependencies in real metadata, not hand-built DDL."""
    found = set(tables)
    pending = list(tables)
    while pending:
        table = pending.pop()
        for fk in table.foreign_keys:
            parent = fk.column.table
            if parent not in found:
                found.add(parent)
                pending.append(parent)
    return list(found)


def test_real_canonical_manual_source_in_shared_snapshot():
    engine = create_engine(_url())
    if engine.dialect.name != "postgresql":
        pytest.fail("PostgreSQL required")
    schema = "sc04_real_" + uuid.uuid4().hex[:16]
    scoped = engine.execution_options(schema_translate_map={None: schema})
    try:
        with engine.begin() as conn:
            conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        tables = _dependent_tables(
            Client.__table__, PensionProduct.__table__, PensionProductAuditEvent.__table__,
            PensionProductComponent.__table__, ScenarioDraft.__table__,
            ScenarioDraftDecision.__table__, CanonicalManualPensionSource.__table__,
            batches, conversions, allocations, pensions,
            CanonicalPensionTemporalDecision.__table__,
            CapitalAsset.__table__, RetirementTimingWorkIntention.__table__,
            ClientProfile.__table__, EmploymentRecord.__table__,
        )
        with scoped.begin() as conn:
            # Canonical conversion DDL guards use unqualified CREATE TRIGGER
            # statements. Resolve those names within this isolated test schema.
            conn.execute(text(f'SET LOCAL search_path TO "{schema}", public'))
            Base.metadata.create_all(conn, tables=tables)
            conn.execute(Client.__table__.insert(), {
                "client_id": 7, "display_name": "Real Registry Synthetic",
                "id_number": "SC04-REAL-7",
            })
            conn.execute(PensionProduct.__table__.insert(), {
                "product_id": "p", "client_id": 7, "source_kind": "manual",
                "source_identity": "manual:7:p", "product_name": "Synthetic",
                "product_type": "קרן פנסיה", "account_reference": "SYNTHETIC",
                "historical_employers": [], "version": 1,
                "created_by": "test", "updated_by": "test",
            })
            from app.models.pension_product import COMPONENT_CODES
            for index, code in enumerate(COMPONENT_CODES):
                conn.execute(PensionProductComponent.__table__.insert(), {
                    "component_id": "c" if index == 0 else f"c{index}",
                    "product_id": "p", "component_code": code,
                    "balance": Decimal("100.00") if index == 0 else Decimal("0.00"),
                })
            conn.execute(ScenarioDraft.__table__.insert(), {
                "scenario_id": "s", "client_id": 7, "name": "Synthetic",
                "status": "draft", "version": 1, "created_by": "test",
                "updated_by": "test",
            })
            from types import SimpleNamespace
            source = _source_evidence(
                SimpleNamespace(client_id=7, product_id="p", version=1,
                    product_type="קרן פנסיה", source_kind="manual",
                    source_identity="manual:7:p"),
                SimpleNamespace(product_id="p", component_id="c",
                    component_code=COMPONENT_CODES[0], balance=Decimal("100.00")),
            )
            conn.execute(ScenarioDraftDecision.__table__.insert(), {
                "decision_id": "d", "scenario_id": "s", "source_product_id": "p",
                "source_component_id": "c", "component_code": COMPONENT_CODES[0],
                "amount": Decimal("40.00"), "action": "pension",
                "effective_date": date(2026, 10, 24),
                "validation_state": "unverified", "product_version_at_review": 1,
                "source_fingerprint_at_review": source["source_fingerprint"],
                "ruleset_digest_at_review": "a" * 64,
                "permission_preview_id_at_review": "b" * 64,
            })
            conn.execute(CanonicalManualPensionSource.__table__.insert(), {
                "manual_pension_source_id": "manual-1", "client_id": 7,
                "input_mode": "entered", "payer_name": "Synthetic payer",
                "monthly_amount": Decimal("100.00"), "tax_treatment": "taxable",
                "pension_start_date": date(2040, 1, 1),
                "base_amount_effective_date": date(2026, 9, 1),
                "temporal_authority_explicit": True,
                "indexation_method": "none", "lifecycle_status": "current",
                "version": 1,
            })
        factory = sessionmaker(bind=scoped, expire_on_commit=False)
        queries = []
        def capture(conn, cursor, statement, parameters, context, executemany):
            queries.append(statement.strip().upper())
        event.listen(scoped, "before_cursor_execute", capture)
        try:
            first = build_pension_source_bridge_snapshot(factory, client_id=7, scenario_id="s")
            second = build_pension_source_bridge_snapshot(factory, client_id=7, scenario_id="s")
        finally:
            event.remove(scoped, "before_cursor_execute", capture)
        assert first == second
        assert first["bridge_state"] == "UNRESOLVED"
        assert first["entries"][0]["historical_conversion_source_ids"] == []
        assert first["entries"][0]["reconciliation_state"] == "UNRESOLVED"
        assert first["execution_allowed"] is False
        assert first["financial_result"] is None
        assert first["planning_snapshot"] is None
        assert any("CANONICAL_MANUAL_PENSION_SOURCES" in query for query in queries)
        assert not any(query.startswith(("INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP")) for query in queries)
        # Read a complete, persisted pension-conversion lineage through the
        # real canonical registry; it must stay historical, never admitted.
        with scoped.begin() as conn:
            conn.execute(batches.insert(), {
                "batch_id": "batch-1", "client_id": 7, "source_product_id": "p",
                "destination_type": "pension", "matrix_version": "test-matrix",
                "idempotency_key": "test-batch-1", "request_fingerprint": "a"*64,
                "expected_product_version": 1, "status": "completed",
                "effective_date": date(2026, 9, 1), "actor": "integration-test",
                "result": {},
            })
            conn.execute(conversions.insert(), {
                "conversion_id": "conversion-1", "client_id": 7, "batch_id": "batch-1",
                "destination_type": "pension", "tax_treatment": "taxable",
                "converted_amount": Decimal("40.00"), "status": "active", "version": 1,
            })
            conn.execute(allocations.insert(), {
                "allocation_id": "allocation-1", "conversion_id": "conversion-1",
                "source_product_id": "p", "source_component_id": "c",
                "component_code_snapshot": COMPONENT_CODES[0],
                "amount": Decimal("40.00"), "source_balance_before": Decimal("140.00"),
                "source_balance_after": Decimal("100.00"),
                "tax_treatment": "taxable", "matrix_version": "test-matrix",
            })
            # Monthly basis authority requires one matching conversion audit event.
            conn.execute(PensionProductAuditEvent.__table__.insert(), {
                "event_id": "audit-conversion-1", "client_id": 7,
                "product_id": "p", "action": "conversion", "version": 1,
                "snapshot": {"statement_date": None,
                             "operation": {"batch_id": "batch-1"}},
                "actor": "integration-test",
            })
            conn.execute(pensions.insert(), {
                "pension_destination_id": "destination-1", "client_id": 7,
                "conversion_id": "conversion-1", "name": "Synthetic conversion",
                "description": "Historical converted component",
                "converted_balance": Decimal("40.00"),
                "effective_date": date(2026, 9, 1),
                "pension_start_date": date(2040, 1, 1),
                "annuity_factor_text": "200", "coefficient_source": "test-fixture",
                "coefficient_source_keys": {}, "coefficient_notes": "",
                "coefficient_catalog_version": "fixture",
                "coefficient_fallback_used": False,
                "monthly_numerator": "40.00", "monthly_denominator": "200",
                "monthly_display_amount": Decimal("0.20"),
                "tax_treatment": "taxable", "status": "active", "version": 1,
            })
        historical = build_pension_source_bridge_snapshot(factory, client_id=7, scenario_id="s")
        assert historical["bridge_state"] == "UNRESOLVED"
        assert historical["entries"][0]["historical_conversion_source_ids"] == ["conversion:destination-1"]
        assert historical["entries"][0]["reconciliation_state"] == "UNRESOLVED"
        assert historical["entries"][0]["trace_note"] == "HISTORICAL_CONVERSION_NOT_CURRENT_SCENARIO_AUTHORITY"
        assert historical["execution_allowed"] is False
        assert historical["financial_result"] is None
        assert historical["planning_snapshot"] is None
        assert historical["bridge_fingerprint"] != first["bridge_fingerprint"]
        with scoped.begin() as conn:
            conn.execute(ScenarioDraft.__table__.update().where(ScenarioDraft.scenario_id == "s").values(version=2))
        updated = build_pension_source_bridge_snapshot(factory, client_id=7, scenario_id="s")
        assert updated["bridge_state"] == "UNRESOLVED"
        assert updated["bridge_fingerprint"] != first["bridge_fingerprint"]
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        scoped.dispose()
        engine.dispose()
