"""Fail-closed regression checks for authoritative fixation source changes."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services import fixation_dependency_service as service


def _assess(monkeypatch, *, nominal="100.00", legacy=False, source_present=True):
    run = SimpleNamespace(fixation_dependency_manifest=None if legacy else object())
    monkeypatch.setattr(service, "get_run_with_dependency_manifest", lambda **kwargs: run)
    content = SimpleNamespace(nominal_amount=Decimal("100"), indexed_amount=Decimal("110"),
        grant_date=date(2020, 1, 1), work_start_date=date(2010, 1, 1),
        work_end_date=date(2019, 12, 31))
    entry = SimpleNamespace(dependency_type="grant", stable_identity="g1",
        canonical_content=content, availability_state="available")
    monkeypatch.setattr(service, "parse_persisted_manifest", lambda run: SimpleNamespace(
        context_availability="available", dependencies=[entry]))
    source = SimpleNamespace(grant_id="g1", client_id=7, nominal_amount=Decimal(nominal),
        indexed_amount=Decimal("110"), grant_date=content.grant_date,
        work_start_date=content.work_start_date, work_end_date=content.work_end_date)
    db = MagicMock()
    db.scalars.side_effect = [SimpleNamespace(all=lambda: [source] if source_present else []),
                              SimpleNamespace(all=lambda: [])]
    return service.assess_persisted_fixation_freshness(client_id=7, run_id=2, db_session=db)


def test_authoritative_grant_change_is_detected(monkeypatch):
    assert _assess(monkeypatch, nominal="150.00")["state"] == "changed"


def test_unverified_dependencies_never_produce_current(monkeypatch):
    result = _assess(monkeypatch)
    assert result["state"] == "unknown"
    assert "full_authoritative_dependency_resolution_unavailable" in result["reason_codes"]


def test_legacy_run_is_preserved_and_identified(monkeypatch):
    assert _assess(monkeypatch, legacy=True)["state"] == "legacy"


def test_unavailable_canonical_source_fails_closed(monkeypatch):
    assert _assess(monkeypatch, source_present=False)["state"] == "unknown"
