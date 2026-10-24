"""Opt-in real PostgreSQL isolation acceptance.

Set SCENARIO_TEST_POSTGRES_URL to a disposable PostgreSQL database URL.
No production credentials. Creates and drops one dedicated probe table.
"""
import os
import uuid

import pytest
from sqlalchemy import create_engine, text


@pytest.mark.skipif(not os.getenv("SCENARIO_TEST_POSTGRES_URL"), reason="dedicated PostgreSQL test URL not supplied")
def test_two_connections_hold_repeatable_read_only_snapshot_under_concurrent_change():
    url = os.environ["SCENARIO_TEST_POSTGRES_URL"]
    engine = create_engine(url, isolation_level="READ COMMITTED")
    if engine.dialect.name != "postgresql":
        pytest.fail("SCENARIO_TEST_POSTGRES_URL must point to PostgreSQL")
    table = "scenario_isolation_probe_" + uuid.uuid4().hex[:16]
    try:
        with engine.begin() as connection:
            connection.execute(text(f"CREATE TABLE {table} (id integer PRIMARY KEY, version integer NOT NULL)"))
            connection.execute(text(f"INSERT INTO {table} (id,version) VALUES (1,1)"))
        with engine.connect() as reader, engine.connect() as writer:
            reader.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
            initial = reader.scalar(text(f"SELECT version FROM {table} WHERE id=1"))
            assert initial == 1
            writer.execute(text(f"UPDATE {table} SET version=2 WHERE id=1"))
            writer.commit()
            assert reader.scalar(text(f"SELECT version FROM {table} WHERE id=1")) == 1
            with pytest.raises(Exception):
                reader.execute(text(f"UPDATE {table} SET version=3 WHERE id=1"))
            reader.rollback()
        with engine.connect() as next_reader:
            assert next_reader.scalar(text(f"SELECT version FROM {table} WHERE id=1")) == 2
            next_reader.rollback()
    finally:
        with engine.begin() as cleanup:
            cleanup.execute(text(f"DROP TABLE IF EXISTS {table}"))
        engine.dispose()
