"""SC-05C: writer must reject stale versions and non-pension decisions."""
from datetime import date
from types import SimpleNamespace


class ScalarRows:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows
import pytest

from app.schemas.scenario_pension_election import ScenarioPensionElectionSet
from app.services import scenario_pension_election_store_service as store
from app.services.scenario_draft_service import DraftError


def payload(version=1):
    return ScenarioPensionElectionSet.model_validate({
        "expected_scenario_version": version,
        "elections": [{
            "decision_id": "d", "pension_start_date": date(2040, 1, 1),
            "target_year": 2040, "survivors_option": "תקנוני",
            "spouse_age_diff": 0, "coefficient_selection": "manual_review_required",
        }],
    })


def test_stale_version_fails_before_any_write(monkeypatch):
    monkeypatch.setattr(store, "_scenario", lambda db, client_id, scenario_id:
                        SimpleNamespace(version=2))
    class DB:
        def execute(self, *_): pytest.fail("unexpected write or query")
        def scalars(self, *_): pytest.fail("unexpected query")
    with pytest.raises(DraftError, match="SCENARIO_VERSION_CONFLICT"):
        store.replace_elections(DB(), 7, "s", payload(), "test")


def test_non_pension_decision_rejected_before_version_bump(monkeypatch):
    monkeypatch.setattr(store, "_scenario", lambda db, client_id, scenario_id:
                        SimpleNamespace(version=1))
    monkeypatch.setattr(store, "_cas", lambda *args, **kwargs:
                        pytest.fail("unexpected version bump"))
    class DB:
        def scalars(self, *_):
            return ScalarRows([SimpleNamespace(decision_id="d", action="capital_asset",
                                    effective_date=date(2030, 1, 1))])
    with pytest.raises(DraftError, match="SCENARIO_PENSION_DECISION_MISMATCH"):
        store.replace_elections(DB(), 7, "s", payload(), "test")


def test_pension_start_before_effective_date_rejected(monkeypatch):
    monkeypatch.setattr(store, "_scenario", lambda db, client_id, scenario_id:
                        SimpleNamespace(version=1))
    monkeypatch.setattr(store, "_cas", lambda *args, **kwargs:
                        pytest.fail("unexpected version bump"))
    class DB:
        def scalars(self, *_):
            return ScalarRows([SimpleNamespace(decision_id="d", action="pension",
                                    effective_date=date(2041, 1, 1))])
    with pytest.raises(DraftError, match="SCENARIO_PENSION_START_BEFORE_EFFECTIVE_DATE"):
        store.replace_elections(DB(), 7, "s", payload(), "test")
