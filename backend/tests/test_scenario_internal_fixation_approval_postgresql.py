"""Supervisor 108 focused real-PG16 admission-to-internal-approval acceptance.

Runs only with the existing disposable localhost PG16 fixture. No migrations,
external databases, tax/CBS calculation, or previous Supervisor 78 replay.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.models.scenario_fixation_approval import (
    ScenarioFixationApprovalHead, ScenarioFixationApprovalRevision,
)
from app.models.pension_product import PensionProductComponent
from app.schemas.scenario_fixation_approval import FixationProfessionalApprovalRequest
from app.services import scenario_fixation_approval_service as ledger
from app.services import scenario_fixation_admission_eligibility_service as eligibility
from app.services import scenario_fixation_admission_review_service as admission
from app.services.scenario_draft_service import DraftError
from tests.test_scenario_unified_engine_binding_postgresql import (
    pg16, _prepared_fixation_sources, _prepared_review,
)

_ATTESTATIONS = [
    "ELIGIBILITY_EVIDENCE_EXAMINED",
    "OFFICIAL_PARAMETERS_EXAMINED",
    "PENSION_CLASSIFICATION_EXAMINED",
    "HISTORICAL_GRANTS_AND_CAPITALIZATIONS_EXAMINED",
    "ABSENCE_OF_OVERLAP_CONFIRMED",
    "LIMITED_INTERNAL_SCOPE_ACKNOWLEDGED",
]
_REASON = "The identified eligibility evidence and official parameter sources were individually assessed."


def seeded(factory):
    _prepared_fixation_sources(factory)
    _prepared_review(factory)


def request(factory, **changes):
    with factory() as db:
        current = ledger.read(db, 7, "a1")
        eligible = eligibility.assess(db, 7, "a1")
        admitted = admission.review(
            db, 7, "a1",
            expected_preparation_fingerprint=eligible["preparation_fingerprint"],
            expected_eligibility_fingerprint=eligible["eligibility_fingerprint"],
        )
    assert eligible["state"] == "ELIGIBLE_FOR_ADMISSION_REVIEW"
    assert admitted["state"] == "ADMITTED_FOR_REVIEW"
    data = {
        "expected_approval_version": current["approval_version"],
        "expected_approval_fingerprint": current["approval_fingerprint"],
        "expected_scenario_version": current["current_readiness"]["scenario_version"],
        "expected_manifest_fingerprint": current["current_readiness"]["manifest_fingerprint"],
        "expected_readiness_fingerprint": current["current_readiness"]["readiness_fingerprint"],
        "expected_preparation_fingerprint": eligible["preparation_fingerprint"],
        "expected_eligibility_fingerprint": eligible["eligibility_fingerprint"],
        "expected_admission_review_fingerprint": admitted["admission_review_fingerprint"],
        "decision": "APPROVE_INTERNAL", "decision_reason": _REASON,
        "review_reference": "document://eligibility-7",
        "attestations": _ATTESTATIONS,
    }
    data.update(changes)
    return FixationProfessionalApprovalRequest(**data)


def approve(factory, payload, actor="trusted-planner"):
    with factory() as db:
        result = ledger.request_internal_approval(db, 7, "a1", payload, actor)
        if result["approval_attempt_state"] == "APPROVED_INTERNAL":
            db.commit()
        else:
            db.rollback()
        return result


def test_01_admission_alone_is_not_professional_authority(pg16):
    factory, _ = pg16
    seeded(factory)
    request(factory)
    with factory() as db:
        state = ledger.read(db, 7, "a1")
    assert state["decision_state"] == "DRAFT"
    assert state["internal_professional_authority"] is False
    assert state["execution_allowed"] is False


def test_02_explicit_authenticated_approval_and_audit(pg16, monkeypatch):
    factory, _ = pg16
    seeded(factory)
    from app.engines import fixation_engine
    from app.services import fixation_service, cbs_indexation_adapter
    def forbidden(*_args, **_kwargs):
        raise AssertionError("INTERNAL_APPROVAL_MUST_NOT_EXECUTE_TAX_OR_CBS")
    monkeypatch.setattr(fixation_engine, "calculate_fixation", forbidden)
    monkeypatch.setattr(fixation_service, "calculate_fixation_payload", forbidden)
    monkeypatch.setattr(cbs_indexation_adapter, "calculate_cbs_indexation", forbidden)
    result = approve(factory, request(factory))
    assert result["approval_attempt_state"] == "APPROVED_INTERNAL"
    assert result["authority_scope"] == "FIXATION_INTERNAL_REVIEW_ONLY"
    assert result["professional_authority"] is False
    assert result["execution_allowed"] is False
    assert result["tax_authority_approval"] is None
    with factory() as db:
        state = ledger.read(db, 7, "a1")
        history = ledger.history(db, 7, "a1")
    assert state["decision_state"] == "APPROVED_INTERNAL"
    assert state["validity_state"] == "CURRENT"
    assert state["internal_professional_authority"] is True
    assert [h["action"] for h in history] == ["SAVE_DRAFT", "APPROVE_INTERNAL"]
    assert history[-1]["actor_id"] == "trusted-planner"
    assert history[-1]["internal_decision"]["review_reference"] == "document://eligibility-7"


@pytest.mark.parametrize("actor", ["", "local-development-only", None])
def test_03_missing_actor_never_writes(pg16, actor):
    factory, _ = pg16
    seeded(factory)
    payload = request(factory)
    with pytest.raises(DraftError):
        approve(factory, payload, actor)
    with factory() as db:
        assert len(ledger.history(db, 7, "a1")) == 1


@pytest.mark.parametrize("field,invalid", [
    ("expected_approval_version", 999),
    ("expected_approval_fingerprint", "0" * 64),
    ("expected_scenario_version", 999),
    ("expected_manifest_fingerprint", "0" * 64),
    ("expected_readiness_fingerprint", "0" * 64),
    ("expected_preparation_fingerprint", "0" * 64),
    ("expected_eligibility_fingerprint", "0" * 64),
    ("expected_admission_review_fingerprint", "0" * 64),
])
def test_04_versions_and_fingerprints_fail_closed(pg16, field, invalid):
    factory, _ = pg16
    seeded(factory)
    payload = request(factory, **{field: invalid})
    with pytest.raises(DraftError):
        approve(factory, payload)
    with factory() as db:
        assert len(ledger.history(db, 7, "a1")) == 1


def test_05_scenarios_cannot_borrow_professional_decision(pg16):
    factory, _ = pg16
    seeded(factory)
    approve(factory, request(factory))
    with factory() as db:
        a = ledger.read(db, 7, "a1")
        b = ledger.read(db, 7, "a2")
    assert a["decision_state"] == "APPROVED_INTERNAL"
    assert b["decision_state"] == "MISSING"
    assert b["internal_professional_authority"] is False


def test_06_foreign_client_scenario_pair_blocked(pg16):
    factory, _ = pg16
    seeded(factory)
    payload = request(factory)
    with factory() as db:
        with pytest.raises(DraftError):
            ledger.request_internal_approval(db, 8, "a1", payload, "trusted-planner")


def test_07_source_mutation_invalidates_historical_approval(pg16):
    factory, _ = pg16
    seeded(factory)
    approve(factory, request(factory))
    with factory.begin() as db:
        db.get(PensionProductComponent, "c7").balance = Decimal("201.00")
    with factory() as db:
        state = ledger.read(db, 7, "a1")
        history = ledger.history(db, 7, "a1")
    assert state["validity_state"] == "STALE"
    assert state["internal_professional_authority"] is False
    assert history[-1]["status"] == "APPROVED_INTERNAL"


def test_08_source_changed_before_action_blocks(pg16):
    factory, _ = pg16
    seeded(factory)
    payload = request(factory)
    with factory.begin() as db:
        db.get(PensionProductComponent, "c7").balance = Decimal("201.00")
    with pytest.raises(DraftError):
        approve(factory, payload)


def test_09_missing_attestation_or_untracked_reference_rejected(pg16):
    from pydantic import ValidationError
    factory, _ = pg16
    seeded(factory)
    with pytest.raises(ValidationError):
        request(factory, attestations=_ATTESTATIONS[:-1])
    with pytest.raises(ValidationError):
        request(factory, review_reference="arbitrary-unverifiable-text")
    with factory() as db:
        assert len(ledger.history(db, 7, "a1")) == 1


def test_09b_unverified_document_reference_is_blocked_by_real_database(pg16):
    factory, _ = pg16
    seeded(factory)
    result = approve(factory, request(factory,
                                     review_reference="document://not-in-client-evidence"))
    assert result["approval_attempt_state"] == "BLOCKED"
    assert "FIXATION_INTERNAL_REVIEW_REFERENCE_NOT_VERIFIED" in result["blockers"]
    with factory() as db:
        assert len(ledger.history(db, 7, "a1")) == 1


def test_10_undocumented_decision_fails_professional_gate(pg16):
    factory, _ = pg16
    seeded(factory)
    payload = request(factory)
    with factory() as db:
        item = ledger.read(db, 7, "a1")
    item["decisions"][0]["evidence_references"] = []
    reasons = ledger._internal_professional_blockers(
        item, {"state": "PREPARED"}, {"state": "ELIGIBLE_FOR_ADMISSION_REVIEW"},
        {"state": "ADMITTED_FOR_REVIEW"})
    assert "FIXATION_INTERNAL_OPEN_OR_UNSUPPORTED_ASSERTION" in reasons
    assert payload is not None


def test_11_unsupported_grants_or_idf_never_auto_approved(pg16):
    factory, _ = pg16
    seeded(factory)
    with factory() as db:
        item = ledger.read(db, 7, "a1")
    item["admission_controls"]["grants_collection"]["state"] = "items_recorded"
    blockers = ledger._internal_professional_blockers(
        item, {"state": "PREPARED"}, {"state": "ELIGIBLE_FOR_ADMISSION_REVIEW"},
        {"state": "ADMITTED_FOR_REVIEW"})
    assert "FIXATION_INTERNAL_UNSUPPORTED_COLLECTION_SCOPE" in blockers


def test_12_concurrent_CAS_only_one_revision_commits(pg16):
    factory, _ = pg16
    seeded(factory)
    payload = request(factory)
    barrier = Barrier(2)

    def worker(_):
        try:
            barrier.wait(timeout=10)
            return approve(factory, payload)["approval_attempt_state"]
        except (DraftError, DBAPIError) as exc:
            return type(exc).__name__

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(worker, (1, 2)))
    assert results.count("APPROVED_INTERNAL") == 1
    with factory() as db:
        assert len(ledger.history(db, 7, "a1")) == 2


def test_13_flush_exception_rolls_back_cas_and_revision(pg16, monkeypatch):
    factory, _ = pg16
    seeded(factory)
    payload = request(factory)
    with factory() as db:
        def reject_flush(*_args, **_kwargs):
            raise RuntimeError("synthetic write failure")
        monkeypatch.setattr(db, "flush", reject_flush)
        with pytest.raises(RuntimeError, match="synthetic write failure"):
            ledger.request_internal_approval(db, 7, "a1", payload, "trusted-planner")
        db.rollback()
    with factory() as db:
        state = ledger.read(db, 7, "a1")
        assert state["approval_version"] == 1
        assert len(ledger.history(db, 7, "a1")) == 1


def test_14_immutable_revision_trigger_in_postgresql(pg16):
    factory, scoped = pg16
    seeded(factory)
    approve(factory, request(factory))
    schema = scoped.get_execution_options()["schema_translate_map"][None]
    # The isolated pg16 fixture uses metadata.create_all, not Alembic.
    # Install the immutable trigger with the same DDL as e53f1c0a7d23
    # before asserting PostgreSQL-level rejection. The migration itself
    # is validated separately from this focused behavioral test.
    with scoped.begin() as conn:
        conn.execute(text(f"""
            CREATE FUNCTION "{schema}".prevent_scenario_fixation_approval_revision_mutation()
            RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                RAISE EXCEPTION 'fixation approval revisions are append-only';
            END; $$;
        """))
        conn.execute(text(f"""
            CREATE TRIGGER trg_scenario_fixation_approval_revision_immutable
            BEFORE UPDATE OR DELETE ON "{schema}".scenario_fixation_approval_revisions
            FOR EACH ROW EXECUTE FUNCTION "{schema}".prevent_scenario_fixation_approval_revision_mutation()
        """))
    with factory() as db:
        item = db.scalar(select(ScenarioFixationApprovalRevision).where(
            ScenarioFixationApprovalRevision.scenario_id == "a1",
            ScenarioFixationApprovalRevision.status == "APPROVED_INTERNAL",
        ))
        with pytest.raises(DBAPIError):
            db.execute(text(
                f'UPDATE "{schema}".scenario_fixation_approval_revisions '
                "SET status = 'DRAFT' WHERE revision_id = :id"
            ), {"id": item.revision_id})
        db.rollback()
    with factory() as db:
        assert ledger.history(db, 7, "a1")[-1]["status"] == "APPROVED_INTERNAL"


def test_15_read_history_never_grants_execution(pg16):
    factory, _ = pg16
    seeded(factory)
    approve(factory, request(factory))
    with factory() as db:
        rows = ledger.history(db, 7, "a1")
        state = ledger.read(db, 7, "a1")
    assert all(row["professional_authority"] is False for row in rows)
    assert all(row["tax_authority_approval"] is None for row in rows)
    assert state["execution_allowed"] is False
    assert state["professional_authority"] is False
