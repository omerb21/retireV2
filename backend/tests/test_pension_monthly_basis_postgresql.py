"""Opt-in PostgreSQL proof; reuses the existing isolated-cluster fixture."""
import pytest
from sqlalchemy import create_engine, text
from test_recovery_migration_postgresql import postgres_url
from test_canonical_conversion_migration import migrate
from test_pension_monthly_basis import (
    migration_contract,
    test_api_date_presence_survives_request_validation_and_reload as check_api_dates,
    test_audit_cardinality_and_date_boundary as check_audit_boundary,
    test_manual_identity_and_incomplete_semantics as check_manual_identity,
    test_database_roundtrip_produces_exact_conversion_golden_bytes as check_golden_roundtrip,
    test_real_audit_selection_requires_action_client_product_and_batch as check_audit_selection,
    test_snapshot_planning_preserve_basis_without_writes_or_target_inference as check_planning,
)


@pytest.fixture
def basis_pg_engine(postgres_url):
    migrate(postgres_url, 'upgrade', 'e0f6b3c9d187')
    engine = create_engine(postgres_url)
    with engine.begin() as db:
        db.execute(text("INSERT INTO clients(client_id,display_name,id_number) VALUES(1,'test','123'),(2,'other','456')"))
    try:
        yield engine
    finally:
        engine.dispose()


def test_pg_additive_migration_and_lossless_downgrade_guard(postgres_url):
    migration_contract(postgres_url)


@pytest.mark.parametrize('mode', ['entered', 'calculated'])
def test_pg_api_tristate_and_exact_ratio(basis_pg_engine, mode):
    check_api_dates(basis_pg_engine, mode, {})


def test_pg_manual_identity_and_registry(basis_pg_engine):
    check_manual_identity(basis_pg_engine)


def test_pg_exact_golden_roundtrip(basis_pg_engine):
    check_golden_roundtrip(basis_pg_engine)


def test_pg_real_audit_selection(basis_pg_engine):
    check_audit_selection(basis_pg_engine)


def test_pg_readonly_planning_basis(basis_pg_engine):
    check_planning(basis_pg_engine)


@pytest.mark.parametrize('state', ['value', 'null', 'zero', 'multiple', 'missing', 'invalid'])
def test_pg_conversion_provenance_boundary(basis_pg_engine, state):
    check_audit_boundary(basis_pg_engine, state)
