"""SC-03A/C database-owned inert manifest and snapshot candidate boundary.

The public owner derives both values from one dedicated PostgreSQL read-only
snapshot. Caller mappings are claims only and must byte-match the independently
derived database manifest before they can participate in a candidate.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from decimal import Decimal
import hmac

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.services.scenario_draft_service import DraftError, _canonical_json
from app.services.scenario_input_manifest_service import (
    ManifestValidationError, _fingerprint, build_inert_manifest,
    validate_inert_manifest,
)


class ScenarioSnapshotError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _invalid(blockers: list[str]) -> dict:
    return {
        "schema_version": "SCENARIO_SNAPSHOT_CANDIDATE_V1",
        "evidence_state": "BLOCKED",
        "blockers": sorted(set(blockers)),
        "planning_snapshot": None,
        "execution_allowed": False,
        "financial_result": None,
        "authority_state": "NOT_EVALUATED",
    }


def _partition_verified_manifest(manifest: dict) -> dict:
    """Partition one already database-derived, strictly validated manifest."""
    manifest = validate_inert_manifest(manifest)
    blockers: list[str] = []
    if manifest["scenario_status"] != "draft":
        blockers.append("SCENARIO_NOT_ACTIVE_DRAFT")
    if not manifest["decisions"]:
        return _invalid(blockers + ["SCENARIO_DECISIONS_EMPTY_OR_INVALID"])

    facts: dict[tuple[str, str], dict] = {}
    proposed: list[dict] = []
    allocated: dict[tuple[str, str], Decimal] = defaultdict(lambda: Decimal("0.00"))
    for row in manifest["decisions"]:
        decision_id = row["decision_id"]
        source = row["source"]
        if source is None:
            blockers.append("SOURCE_MISSING:" + decision_id)
            continue
        key = (row["product_id"], row["component_id"])
        amount = Decimal(row["amount"])
        fact = {
            "client_id": source["client_id"],
            "product_id": source["product_id"],
            "component_id": source["component_id"],
            "component_code": source["component_code"],
            "product_version": source["product_version"],
            "balance": source["balance"],
            "source_fingerprint": source["source_fingerprint"],
        }
        if key in facts and facts[key] != fact:
            blockers.append("CONFLICTING_SOURCE_FACTS:" + decision_id)
        facts[key] = fact
        allocated[key] += amount
        if (
            row["product_version_at_review"] != source["product_version"]
            or row["source_fingerprint_at_review"] != source["source_fingerprint"]
            or row["validation_state"] != "unverified"
        ):
            blockers.append("SOURCE_STALE:" + decision_id)
        proposed.append({
            "decision_id": decision_id,
            "product_id": row["product_id"],
            "component_id": row["component_id"],
            "component_code": row["component_code"],
            "amount": row["amount"],
            "action": row["action"],
            "effective_date": row["effective_date"],
            "ruleset_digest_at_review": row["ruleset_digest_at_review"],
            "permission_preview_id_at_review": row["permission_preview_id_at_review"],
        })
    for key, total in allocated.items():
        if total > Decimal(facts[key]["balance"]):
            blockers.append("SOURCE_OVERALLOCATED:" + key[0] + ":" + key[1])
    blockers = sorted(set(blockers))
    source_facts = [facts[key] for key in sorted(facts)]
    decisions = sorted(proposed, key=lambda row: row["decision_id"])
    evidence_state = "BLOCKED" if blockers else "STRUCTURALLY_CONSISTENT_NOT_ADMITTED"
    partition = {
        "schema_version": "SCENARIO_SNAPSHOT_CANDIDATE_V1",
        "client_id": manifest["client_id"],
        "scenario_id": manifest["scenario_id"],
        "scenario_version": manifest["scenario_version"],
        "manifest_fingerprint": manifest["manifest_fingerprint"],
        "source_facts": source_facts,
        "proposed_decisions": decisions,
        "evidence_state": evidence_state,
        "blockers": blockers,
        "planning_snapshot": None,
        "execution_allowed": False,
        "financial_result": None,
        "authority_state": "NOT_EVALUATED",
    }
    partition["partition_fingerprint"] = _fingerprint(partition)
    return partition


def _claimed_manifest_matches(authoritative: dict, claimed: object) -> bool:
    try:
        claimed = validate_inert_manifest(claimed)
    except ManifestValidationError:
        return False
    return hmac.compare_digest(
        _canonical_json(authoritative).encode("utf-8"),
        _canonical_json(claimed).encode("utf-8"),
    )


def _build_pair_in_snapshot(
    db: Session,
    client_id: int,
    scenario_id: str,
    claimed_manifest: object | None,
) -> dict:
    authoritative = build_inert_manifest(db, client_id, scenario_id)
    if claimed_manifest is not None and not _claimed_manifest_matches(
        authoritative, claimed_manifest,
    ):
        candidate = _invalid(["MANIFEST_DATABASE_MISMATCH"])
    else:
        candidate = _partition_verified_manifest(authoritative)
    return {"manifest": authoritative, "candidate": candidate}


def _engine(factory: sessionmaker[Session]) -> Engine:
    bind = factory.kw.get("bind")
    if not isinstance(bind, Engine):
        raise ScenarioSnapshotError("SCENARIO_SNAPSHOT_DATABASE_UNAVAILABLE")
    return bind


def build_manifest_candidate_snapshot(
    factory: sessionmaker[Session],
    *,
    client_id: int,
    scenario_id: str,
    claimed_manifest: object | None = None,
) -> dict:
    """Own one PostgreSQL snapshot and derive Manifest + Candidate within it."""
    if (
        type(client_id) is not int or client_id <= 0
        or not isinstance(scenario_id, str) or not scenario_id or len(scenario_id) > 64
    ):
        raise ScenarioSnapshotError("SCENARIO_SNAPSHOT_REQUEST_INVALID")
    engine = _engine(factory)
    connection = None
    transaction = None
    db = None
    result = None
    primary: BaseException | None = None
    cleanup_failed = False
    try:
        connection = engine.connect()
        if connection.dialect.name != "postgresql":
            raise ScenarioSnapshotError("SCENARIO_SNAPSHOT_REQUIRES_POSTGRESQL")
        connection = connection.execution_options(
            isolation_level="REPEATABLE READ", postgresql_readonly=True,
        )
        transaction = connection.begin()
        db = Session(bind=connection, autoflush=False, expire_on_commit=False)
        result = _build_pair_in_snapshot(
            db, client_id, scenario_id, claimed_manifest,
        )
    except BaseException as exc:
        primary = exc
    finally:
        if connection is not None:
            try:
                if transaction is not None and transaction.is_active:
                    transaction.rollback()
                elif connection.in_transaction():
                    connection.rollback()
            except BaseException:
                cleanup_failed = True
        if db is not None:
            try:
                db.close()
            except BaseException:
                cleanup_failed = True
        if connection is not None:
            if cleanup_failed:
                try:
                    connection.invalidate()
                except BaseException:
                    pass
            try:
                connection.close()
            except BaseException:
                cleanup_failed = True
                try:
                    connection.invalidate()
                except BaseException:
                    pass
    if cleanup_failed:
        raise ScenarioSnapshotError("SCENARIO_SNAPSHOT_CLEANUP_FAILED")
    if primary is not None:
        if isinstance(primary, (DraftError, ScenarioSnapshotError)):
            raise primary
        raise ScenarioSnapshotError("SCENARIO_SNAPSHOT_DATABASE_UNAVAILABLE") from primary
    assert result is not None
    return deepcopy(result)
