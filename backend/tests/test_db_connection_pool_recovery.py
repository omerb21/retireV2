"""Database connection-pool recovery for idle managed PostgreSQL computes."""
from unittest.mock import patch

import pytest

from app.db.session import _build_session_local


def test_session_factory_revalidates_stale_postgres_connections(monkeypatch):
    url = "postgresql+psycopg2://test:secret@ep-example.neon.tech/isolated?sslmode=require"
    monkeypatch.setenv("DATABASE_URL", url)
    fake_engine = object()

    with patch("app.db.session.create_engine", return_value=fake_engine) as create_engine:
        session_factory = _build_session_local()

    create_engine.assert_called_once_with(
        url,
        pool_pre_ping=True,
        pool_recycle=240,
    )
    assert session_factory.kw["bind"] is fake_engine
    assert session_factory.kw["autoflush"] is False
    assert session_factory.kw["autocommit"] is False


def test_missing_database_url_never_constructs_an_engine(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with patch("app.db.session.create_engine") as create_engine:
        with pytest.raises(RuntimeError, match="DATABASE_URL is required"):
            _build_session_local()

    create_engine.assert_not_called()
