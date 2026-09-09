"""Outer DDL must not collide with the retained archive mutation guard."""
import pytest
from sqlalchemy import create_engine, delete, update
from sqlalchemy.orm import Session

from app.db.base import load_all_models
from app.models.m05_ledger import (
    M05LedgerSubject, _prevent_m05_connection_mutation, _sql_mutates_m05,
)

DDL = [
    "CREATE TRIGGER archive BEFORE INSERT OR UPDATE OR DELETE ON m05_ledger_subjects FOR EACH ROW EXECUTE FUNCTION archive_only()",
    "CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON m05_ledger_values FOR EACH ROW EXECUTE FUNCTION archive_only()",
    "CREATE FUNCTION archive_only() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'UPDATE m05_ledger_values; DELETE FROM m05_ledger_values'; END; $$",
    "CREATE FUNCTION example() RETURNS void AS $body$ BEGIN UPDATE m05_ledger_values SET original_code='x'; END; $body$ LANGUAGE plpgsql",
    'CREATE TABLE "begin" (id int)',
]


@pytest.mark.parametrize("sql", DDL)
def test_outer_postgresql_ddl_is_allowed(sql):
    assert not _sql_mutates_m05(sql)
    _prevent_m05_connection_mutation(None, None, sql, None, None, False)


@pytest.mark.parametrize("sql", [
    "UPDATE m05_ledger_values SET original_code='x'",
    "DELETE FROM m05_ledger_values",
    'UPDATE "m05_ledger_values" SET original_code=\'x\'',
    "UPDATE public.m05_ledger_values SET original_code='x'",
    'DELETE FROM ONLY "public"."m05_ledger_values"',
    "UPDATE ONLY public.m05_ledger_values SET original_code='x'",
    "WITH q AS (SELECT 1) UPDATE m05_ledger_values SET original_code='x'",
    "WITH q AS (SELECT 1) DELETE FROM m05_ledger_values",
    "WITH q AS (DELETE FROM m05_ledger_values RETURNING *) SELECT * FROM q",
    "UPDATE OR ABORT [m05_ledger_values] SET original_code='x'",
    "UPDATE OR IGNORE `m05_ledger_values` SET original_code='x'",
    "UPDATE OR ROLLBACK m05_ledger_values SET original_code='x'",
    "UPDATE OR FAIL m05_ledger_values SET original_code='x'",
    "UPDATE OR REPLACE m05_ledger_values SET original_code='x'",
    "/* outer /* nested */ comment */ DELETE FROM m05_ledger_values",
    "/* outer /* nested */ CREATE TABLE ignored */ DELETE FROM m05_ledger_values",
    "/* outer /* nested */ CREATE TABLE ignored */ UPDATE m05_ledger_values SET original_code='x'",
])
def test_executable_dml_remains_detected(sql):
    assert _sql_mutates_m05(sql)
    with pytest.raises(ValueError, match="M05 append-only"):
        _prevent_m05_connection_mutation(None, None, sql, None, None, False)


@pytest.mark.parametrize("ddl", DDL)
@pytest.mark.parametrize("dml", ["UPDATE m05_ledger_values SET original_code='x'", "DELETE FROM m05_ledger_values"])
def test_ddl_does_not_hide_following_statement(ddl, dml):
    assert _sql_mutates_m05(ddl + "; " + dml)


@pytest.mark.parametrize("sql", [
    "SELECT 'UPDATE m05_ledger_values; DELETE FROM m05_ledger_values'",
    "SELECT $x$ UPDATE m05_ledger_values; $x$",
    r"CREATE FUNCTION f() RETURNS text AS E'SELECT \'UPDATE m05_ledger_values;\'' LANGUAGE sql",
    "-- UPDATE m05_ledger_values\nSELECT 1",
])
def test_quoted_bodies_and_comments_are_not_executable_dml(sql):
    assert not _sql_mutates_m05(sql)
    assert _sql_mutates_m05(sql + "; DELETE FROM m05_ledger_values")


@pytest.fixture
def engine():
    load_all_models()
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE m05_ledger_subjects(subject_id text, provider_name text)")
    yield engine
    engine.dispose()


@pytest.mark.parametrize("sql", [
    "UPDATE m05_ledger_subjects SET provider_name='x'",
    "DELETE FROM m05_ledger_subjects",
    "/* outer /* closes here */ UPDATE m05_ledger_subjects SET provider_name='x' -- */",
])
def test_actual_raw_connection_mutation_rejected(engine, sql):
    with engine.connect() as connection, pytest.raises(ValueError, match="M05 append-only"):
        connection.exec_driver_sql(sql)


@pytest.mark.parametrize("orm", [False, True])
@pytest.mark.parametrize("statement", [update(M05LedgerSubject).values(provider_name="x"), delete(M05LedgerSubject)])
def test_core_and_orm_mutation_rejected(engine, orm, statement):
    with (Session(engine) if orm else engine.connect()) as executor:
        with pytest.raises(ValueError, match="M05 append-only"):
            executor.execute(statement)


def test_new_professional_orm_record_remains_archive_blocked(engine):
    with Session(engine) as session:
        session.add(M05LedgerSubject(subject_id="new", client_id=1, provider_name="p", account_reference="a", provider_identity_digest="a" * 64, account_identity_digest="b" * 64))
        with pytest.raises(ValueError, match="LEGACY_PENSION_WORKFLOW_ARCHIVE_ONLY"):
            session.flush()
