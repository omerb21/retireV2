"""PensionHolding disposition: preserve FK history, remove current authority."""
import sqlite3

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.main import app
from test_recovery_migration import alembic, seed, PARENT, HEAD


def test_historical_holding_and_analysis_survive_without_current_authority(tmp_path):
    path = tmp_path / "holding-archive.db"
    alembic(path, "upgrade", PARENT)
    seed(path)
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("INSERT INTO pension_holding(id,client_id,provider_name,product_type,known_balance_amount,balance_as_of_date) VALUES(7,1,'Archived','pension fund',987654.32,'2020-01-01')")
        db.execute("INSERT INTO pension_analysis_record(id,client_id,pension_holding_id,analysis_record_text) VALUES(8,1,7,'Historical text')")
    alembic(path, "upgrade", HEAD)
    with sqlite3.connect(path) as db:
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        assert db.execute("SELECT pension_holding_id,analysis_record_text FROM pension_analysis_record").fetchone() == (7, "Historical text")
        assert db.execute("SELECT known_balance_amount FROM pension_holding WHERE id=7").fetchone()[0] == 987654.32
        # Only the M02 product is migrated; no implicit holding decomposition.
        assert db.execute("SELECT COUNT(*) FROM pension_products").fetchone()[0] == 1
        assert db.execute("SELECT DISTINCT balance FROM pension_product_components").fetchall() == [("0.00",)]
        for table in ("pension_holding", "pension_analysis_record"):
            for sql in (f"DELETE FROM {table}", f"UPDATE {table} SET id=id", f"INSERT INTO {table} SELECT * FROM {table}"):
                with pytest.raises(sqlite3.IntegrityError, match="LEGACY_PENSION_WORKFLOW_ARCHIVE_ONLY"):
                    db.execute(sql)
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    def session():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[get_db] = session
    statements = []
    def capture(conn, cursor, statement, params, context, executemany):
        statements.append(statement.lower())
    event.listen(engine, "before_cursor_execute", capture)
    try:
        with TestClient(app) as client:
            root = "/api/clients/1/pension-holdings"
            for method, suffix in (("GET", ""), ("POST", ""), ("GET", "/7"), ("PUT", "/7")):
                assert client.request(method, root + suffix, json={}).status_code == 404
            for method in ("POST", "PUT"):
                assert client.request(method, root + "/7/analysis-record", json={"analysis_record_text": "new"}).status_code == 405
            archived = client.get(root + "/7/analysis-record")
            assert archived.status_code == 200
            assert archived.json()["analysis_record_text"] == "Historical text"
            assert "known_balance_amount" not in archived.text
            canonical = client.get("/api/clients/1/pension-products")
            assert canonical.status_code == 200
            assert len(canonical.json()) == 1
        assert not any("from pension_holding" in sql for sql in statements)
        assert not any(sql.lstrip().startswith(("insert into pension_holding", "update pension_holding")) for sql in statements)
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()
