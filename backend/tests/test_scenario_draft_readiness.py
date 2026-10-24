"""Readiness guards exactly the accepted scenario migration revision."""
from types import SimpleNamespace

import pytest
from app import main


class FakeDatabase:
    def __init__(self, versions):
        self.versions = versions
        self.closed = False

    def execute(self, _sql):
        values = self.versions
        return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: values))

    def close(self):
        self.closed = True


@pytest.mark.parametrize("versions,expected", [
    (["f6a9c4d2e107"], True),
    (["c4e8a2f6b731"], False),
    ([], False),
    (["f6a9c4d2e107", "other-head"], False),
])
def test_scenario_head_readiness_is_exact(monkeypatch, versions, expected):
    database = FakeDatabase(versions)
    monkeypatch.setattr(main, "get_session_factory", lambda: lambda: database)
    monkeypatch.setattr(main, "cleanup_batch", lambda _db: 0)
    app = SimpleNamespace(state=SimpleNamespace(rate_limiter_ready=None))
    if expected:
        assert main._cleanup_once(app) is True
    else:
        # RateLimitUnavailable is raised for a head mismatch and swallowed as unready.
        assert main._cleanup_once(app) is False
    assert app.state.rate_limiter_ready is expected
    assert database.closed is True
