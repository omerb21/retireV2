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
    snapshot_extension=None,
) -> dict:
    authoritative = build_inert_manifest(db, client_id, scenario_id)
    if claimed_manifest is not None and not _claimed_manifest_matches(
        authoritative, claimed_manifest,
    ):
        candidate = _invalid(["MANIFEST_DATABASE_MISMATCH"])
    else:
        candidate = _partition_verified_manifest(authoritative)
    pair = {"manifest": authoritative, "candidate": candidate}
    if snapshot_extension is not None:
        return snapshot_extension(db, pair)
    return pair


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
    _snapshot_extension=None,
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
        if _snapshot_extension is None:
            result = _build_pair_in_snapshot(db, client_id, scenario_id, claimed_manifest)
        else:
            result = _build_pair_in_snapshot(
                db, client_id, scenario_id, claimed_manifest, _snapshot_extension,
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


# Stage 6 P1C: approved narrow extension of the existing immutable snapshot owner.
# Identity derivation ONLY. The P1D PTE execution path is deliberately absent.
def build_stage6_p1c_planning_snapshot(factory: sessionmaker[Session], *,
                                       client_id: int, scenario_id: str,
                                       decision_id: str, _stage6_executor=None) -> dict:
    """Derive all five canonical hashes and a one-source planning result.

    All authority is independently read from the SAME REPEATABLE READ READ ONLY
    PostgreSQL snapshot owned by build_manifest_candidate_snapshot().
    No caller-supplied manifest, factor, date, actor, hash or ready flag.
    """
    from sqlalchemy import select
    from app.models.pension_product import PensionProduct
    from app.models.planning_input_decision import PlanningInputDecision
    from app.models.scenario_draft_pension_election import ScenarioDraftPensionElection
    from app.services.scenario_pension_factor_admission_read_service import (
        read_current_admission,
    )
    from app.services.scenario_permission_preview_service import (
        derive_pension_action_permission_admission,
    )
    from app.services.scenario_coefficient_review_context_service import (
        derive_documentary_review_context,
    )
    from app.services.pension_monthly_basis_service import scenario_decision_monthly_identity
    from app.services.pension_temporal_basis_service import scenario_decision_temporal_identity
    from app.services.planning_input_service import (
        scenario_decision_calculation_identity,
        scenario_decision_one_source_planning_result,
    )

    if type(decision_id) is not str or not decision_id or len(decision_id)>64:
        raise ScenarioSnapshotError("STAGE6_P1C_DECISION_INVALID")

    def _stage6_identity(db: Session, pair: dict) -> dict:
        manifest=pair["manifest"]
        partition=pair["candidate"]
        if partition["evidence_state"]!="STRUCTURALLY_CONSISTENT_NOT_ADMITTED":
            raise ScenarioSnapshotError("STAGE6_P1C_SOURCE_BLOCKED")
        decisions=[row for row in manifest["decisions"] if row["decision_id"]==decision_id]
        if len(decisions)!=1 or decisions[0]["action"]!="pension" or decisions[0]["source"] is None:
            raise ScenarioSnapshotError("STAGE6_P1C_DECISION_BLOCKED")
        decision=decisions[0]
        from app.services.scenario_pension_factor_admission_read_service import FactorAdmissionBlocked
        from app.services.scenario_permission_preview_service import ScenarioPermissionError
        try:
            approval=read_current_admission(
                db,client_id=client_id,scenario_id=scenario_id,decision_id=decision_id)
            permission=derive_pension_action_permission_admission(
                db,client_id=client_id,scenario_id=scenario_id,decision_id=decision_id)
            review=derive_documentary_review_context(
                db,client_id=client_id,scenario_id=scenario_id,decision_id=decision_id)
        except FactorAdmissionBlocked as exc:
            raise ScenarioSnapshotError("STAGE6_P1C_FACTOR_ADMISSION_BLOCKED") from exc
        except ScenarioPermissionError as exc:
            raise ScenarioSnapshotError("STAGE6_P1C_PERMISSION_BLOCKED") from exc
        except DraftError as exc:
            raise ScenarioSnapshotError("STAGE6_P1C_DOCUMENTARY_CONTEXT_BLOCKED") from exc
        product=db.scalar(select(PensionProduct).where(
            PensionProduct.client_id==client_id,
            PensionProduct.product_id==decision["product_id"]))
        election=db.scalar(select(ScenarioDraftPensionElection).where(
            ScenarioDraftPensionElection.scenario_id==scenario_id,
            ScenarioDraftPensionElection.decision_id==decision_id,
            ScenarioDraftPensionElection.scenario_version==manifest["scenario_version"]))
        if (product is None or product.statement_date is None or election is None
                or product.version!=decision["source"]["product_version"]
                or election.coefficient_selection!="manual_review_required"
                or not election.option_name):
            raise ScenarioSnapshotError("STAGE6_P1C_FACTS_STALE")
        global_decision=db.get(PlanningInputDecision,client_id)
        if (global_decision is not None
                and global_decision.retirement_target_date is not None
                and global_decision.retirement_target_date!=election.pension_start_date):
            raise ScenarioSnapshotError("SCENARIO_GLOBAL_TARGET_CONFLICT")
        statement=product.statement_date.isoformat()
        target=election.pension_start_date.isoformat()
        if target<statement:
            raise ScenarioSnapshotError("STAGE6_P1C_DATE_ORDER_INVALID")
        if review["manifest_fingerprint"]!=manifest["manifest_fingerprint"]:
            raise ScenarioSnapshotError("STAGE6_P1C_MANIFEST_STALE")
        monthly=scenario_decision_monthly_identity({
            "client_id":client_id,"scenario_id":scenario_id,
            "scenario_version":manifest["scenario_version"],"decision_id":decision_id,
            "manifest_fingerprint":manifest["manifest_fingerprint"],
            "partition_fingerprint":partition["partition_fingerprint"],
            "source_product_id":decision["product_id"],
            "source_product_version":decision["source"]["product_version"],
            "source_component_id":decision["component_id"],
            "component_code":decision["component_code"],
            "source_fingerprint":decision["source"]["source_fingerprint"],
            "amount":decision["amount"],"statement_date":statement,
            "election_fingerprint":review["election_fingerprint"],
            "professional_admission_revision":approval["admission_revision"],
            "professional_admission_fingerprint":approval["professional_admission_fingerprint"],
            "factor_value":approval["factor_value"],
        })
        temporal=scenario_decision_temporal_identity({
            "source_id":monthly["source_id"],"client_id":client_id,
            "scenario_id":scenario_id,"scenario_version":manifest["scenario_version"],
            "decision_id":decision_id,"statement_date":statement,
            "retirement_target_date":target,
            "monthly_source_fingerprint":monthly["monthly_source_fingerprint"],
            "professional_admission_fingerprint":approval["professional_admission_fingerprint"],
        })
        planning_facts={
            "client_id":client_id,"scenario_id":scenario_id,
            "scenario_version":manifest["scenario_version"],"decision_id":decision_id,
            "source_id":monthly["source_id"],
            "manifest_fingerprint":manifest["manifest_fingerprint"],
            "partition_fingerprint":partition["partition_fingerprint"],
            "source_fingerprint":decision["source"]["source_fingerprint"],
            "statement_date":statement,"amount":decision["amount"],"action":"pension",
            "election_fingerprint":review["election_fingerprint"],
            "retirement_target_date":target,
            "monthly_semantic_fingerprint":monthly["monthly_semantic_fingerprint"],
            "monthly_source_fingerprint":monthly["monthly_source_fingerprint"],
            "temporal_semantic_fingerprint":temporal["temporal_semantic_fingerprint"],
            "temporal_source_fingerprint":temporal["temporal_source_fingerprint"],
            "professional_admission_revision":approval["admission_revision"],
            "professional_admission_fingerprint":approval["professional_admission_fingerprint"],
            "ruleset_digest":permission["ruleset_digest"],
            "permission_admission_fingerprint":permission["permission_admission_fingerprint"],
        }
        planning=scenario_decision_calculation_identity(planning_facts)
        one_source=scenario_decision_one_source_planning_result(
            facts=planning_facts,monthly=monthly,temporal=temporal,
            factor_value=approval["factor_value"])
        # Execute only inside the original authoritative read-only snapshot.
        # The ordinary P1C call remains identity-only and never invokes PTE.
        if _stage6_executor is not None:
            return _stage6_executor(
                planning_result=one_source, approval=approval,
                statement_date=statement, retirement_target_date=target,
                five_identities=planning_facts)
        return {
            "schema_version":"STAGE6_P1C_IDENTITY_ONLY_V1",
            "client_id":client_id,"scenario_id":scenario_id,"decision_id":decision_id,
            "scenario_version":manifest["scenario_version"],
            "monthly_semantic_fingerprint":monthly["monthly_semantic_fingerprint"],
            "monthly_source_fingerprint":monthly["monthly_source_fingerprint"],
            "temporal_semantic_fingerprint":temporal["temporal_semantic_fingerprint"],
            "temporal_source_fingerprint":temporal["temporal_source_fingerprint"],
            "planning_calculation_input_fingerprint":planning["planning_calculation_input_fingerprint"],
            "planning_result":one_source,
            "professional_admission_fingerprint":approval["professional_admission_fingerprint"],
            "permission_admission_fingerprint":permission["permission_admission_fingerprint"],
            "ruleset_digest":permission["ruleset_digest"],
            "execution_allowed":False,
            "financial_result":None,
        }

    # This is the pre-existing snapshot owner, not a new transaction engine.
    return build_manifest_candidate_snapshot(
        factory,client_id=client_id,scenario_id=scenario_id,
        _snapshot_extension=_stage6_identity)
