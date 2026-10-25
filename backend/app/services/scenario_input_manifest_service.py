"""SC-SCENARIO-03A: inert, database-derived scenario-input manifest.

This is evidence packaging, not an executable planning snapshot or financial
calculation authority. The caller owns the read-only transaction. A manifest
is valid only when its closed schema and every database-derived source preimage
validate; a recomputed envelope hash alone is never source authority.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
import re
from collections.abc import Mapping

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.pension_product import (
    COMPONENT_CODES, PensionProduct, PensionProductComponent,
)
from app.models.scenario_draft import ScenarioDraft, ScenarioDraftDecision
from app.services.scenario_draft_service import (
    DraftError, _canonical_json, _source_evidence,
)


SHA256_RE = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z", re.ASCII)
MONEY_RE = re.compile(r"(?:0|[1-9][0-9]*)\.[0-9]{2}\Z", re.ASCII)
MANIFEST_IDENTITY_FIELDS = (
    "schema_version", "client_id", "scenario_id", "scenario_version",
    "scenario_status", "decisions",
)
MANIFEST_FIELDS = frozenset({
    *MANIFEST_IDENTITY_FIELDS, "manifest_fingerprint", "execution_allowed",
    "planning_snapshot", "financial_result", "authority_state",
})
DECISION_FIELDS = frozenset({
    "decision_id", "product_id", "component_id", "component_code", "amount",
    "action", "effective_date", "validation_state", "product_version_at_review",
    "source_fingerprint_at_review", "ruleset_digest_at_review",
    "permission_preview_id_at_review", "source",
})
SOURCE_FIELDS = frozenset({
    "schema", "client_id", "product_id", "product_version", "product_type",
    "source_kind", "source_identity", "component_product_id", "component_id",
    "component_code", "balance", "source_fingerprint",
})


class ManifestValidationError(ValueError):
    pass


def _fingerprint(value: Mapping) -> str:
    return hashlib.sha256(_canonical_json(dict(value)).encode("utf-8")).hexdigest()


def _nonempty(value) -> bool:
    return isinstance(value, str) and bool(value)


def _identifier(value) -> bool:
    return _nonempty(value) and len(value) <= 64


def _positive_int(value) -> bool:
    return type(value) is int and value > 0


def _sha_or_none(value) -> bool:
    return value is None or isinstance(value, str) and SHA256_RE.fullmatch(value) is not None


def _canonical_date(value) -> bool:
    if not isinstance(value, str) or DATE_RE.fullmatch(value) is None:
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def _canonical_positive_money(value) -> bool:
    if not isinstance(value, str) or MONEY_RE.fullmatch(value) is None:
        return False
    try:
        amount = Decimal(value)
        return amount.is_finite() and amount > 0 and format(amount, ".2f") == value
    except InvalidOperation:
        return False


def _source_valid(source: object, client_id: int, decision: Mapping) -> bool:
    if type(source) is not dict or set(source) != SOURCE_FIELDS:
        return False
    if (
        source.get("schema") != "scenario-draft-source-v1"
        or source.get("client_id") != client_id
        or not _identifier(source.get("product_id"))
        or not _positive_int(source.get("product_version"))
        or not all(_nonempty(source.get(field)) for field in (
            "product_type", "source_kind", "source_identity",
        ))
        or source.get("source_kind") not in {"manual", "imported"}
        or not _identifier(source.get("component_product_id"))
        or not _identifier(source.get("component_id"))
        or source.get("component_code") not in COMPONENT_CODES
        or source.get("component_product_id") != source.get("product_id")
        or not isinstance(source.get("balance"), str)
        or MONEY_RE.fullmatch(source["balance"]) is None
        or not isinstance(source.get("source_fingerprint"), str)
        or SHA256_RE.fullmatch(source["source_fingerprint"]) is None
        or (source["product_id"], source["component_id"], source["component_code"])
        != (decision.get("product_id"), decision.get("component_id"), decision.get("component_code"))
    ):
        return False
    try:
        balance = Decimal(source["balance"])
    except InvalidOperation:
        return False
    if not balance.is_finite() or balance < 0 or format(balance, ".2f") != source["balance"]:
        return False
    preimage = {key: source[key] for key in SOURCE_FIELDS if key != "source_fingerprint"}
    return source["source_fingerprint"] == _fingerprint(preimage)


def validate_inert_manifest(value: object) -> dict:
    """Validate the complete closed manifest and return a detached copy."""
    if type(value) is not dict or set(value) != MANIFEST_FIELDS:
        raise ManifestValidationError("MANIFEST_SHAPE_INVALID")
    if (
        value.get("schema_version") != "SCENARIO_INERT_MANIFEST_V1"
        or not _positive_int(value.get("client_id"))
        or not _identifier(value.get("scenario_id"))
        or not _positive_int(value.get("scenario_version"))
        or value.get("scenario_status") not in {"draft", "needs_revalidation", "archived"}
        or type(value.get("decisions")) is not list
        or value.get("execution_allowed") is not False
        or value.get("planning_snapshot") is not None
        or value.get("financial_result") is not None
        or value.get("authority_state") != "NOT_EVALUATED"
    ):
        raise ManifestValidationError("MANIFEST_CONTRACT_INVALID")
    seen: set[str] = set()
    for decision in value["decisions"]:
        if type(decision) is not dict or set(decision) != DECISION_FIELDS:
            raise ManifestValidationError("DECISION_SHAPE_INVALID")
        decision_id = decision.get("decision_id")
        if (
            not all(_identifier(decision.get(field)) for field in (
                "decision_id", "product_id", "component_id",
            ))
            or decision.get("component_code") not in COMPONENT_CODES
            or decision_id in seen
            or not _canonical_positive_money(decision.get("amount"))
            or decision.get("action") not in {"pension", "capital_asset"}
            or not _canonical_date(decision.get("effective_date"))
            or decision.get("validation_state") not in {"unverified", "needs_revalidation"}
            or not (decision.get("product_version_at_review") is None
                    or _positive_int(decision.get("product_version_at_review")))
            or not _sha_or_none(decision.get("source_fingerprint_at_review"))
            or not _sha_or_none(decision.get("ruleset_digest_at_review"))
            or not _sha_or_none(decision.get("permission_preview_id_at_review"))
        ):
            raise ManifestValidationError("DECISION_CONTRACT_INVALID")
        seen.add(decision_id)
        if decision.get("source") is not None and not _source_valid(
            decision["source"], value["client_id"], decision,
        ):
            raise ManifestValidationError("SOURCE_EVIDENCE_INVALID")
    identity = {key: value[key] for key in MANIFEST_IDENTITY_FIELDS}
    if (
        not isinstance(value.get("manifest_fingerprint"), str)
        or SHA256_RE.fullmatch(value["manifest_fingerprint"]) is None
        or value["manifest_fingerprint"] != _fingerprint(identity)
    ):
        raise ManifestValidationError("MANIFEST_INTEGRITY_INVALID")
    return deepcopy(value)


def build_inert_manifest(db: Session, client_id: int, scenario_id: str) -> dict:
    """Build one database-derived inert manifest in the caller's snapshot."""
    scenario = db.scalar(select(ScenarioDraft).where(
        ScenarioDraft.client_id == client_id, ScenarioDraft.scenario_id == scenario_id,
    ))
    if scenario is None:
        raise DraftError("SCENARIO_NOT_FOUND", 404)
    decisions = db.scalars(select(ScenarioDraftDecision).where(
        ScenarioDraftDecision.scenario_id == scenario_id,
    ).order_by(ScenarioDraftDecision.decision_id)).all()
    evidence = []
    for row in decisions:
        product = db.scalar(select(PensionProduct).where(
            PensionProduct.client_id == client_id,
            PensionProduct.product_id == row.source_product_id,
        ))
        component = db.scalar(select(PensionProductComponent).where(
            PensionProductComponent.product_id == row.source_product_id,
            PensionProductComponent.component_id == row.source_component_id,
            PensionProductComponent.component_code == row.component_code,
        )) if product is not None else None
        source = _source_evidence(product, component) if component is not None else None
        evidence.append({
            "decision_id": row.decision_id,
            "product_id": row.source_product_id,
            "component_id": row.source_component_id,
            "component_code": row.component_code,
            "amount": format(row.amount, ".2f"),
            "action": row.action,
            "effective_date": row.effective_date.isoformat(),
            "validation_state": row.validation_state,
            "product_version_at_review": row.product_version_at_review,
            "source_fingerprint_at_review": row.source_fingerprint_at_review,
            "ruleset_digest_at_review": row.ruleset_digest_at_review,
            "permission_preview_id_at_review": row.permission_preview_id_at_review,
            "source": source,
        })
    identity = {
        "schema_version": "SCENARIO_INERT_MANIFEST_V1",
        "client_id": client_id,
        "scenario_id": scenario_id,
        "scenario_version": scenario.version,
        "scenario_status": scenario.status,
        "decisions": evidence,
    }
    manifest = {
        **identity,
        "manifest_fingerprint": _fingerprint(identity),
        "execution_allowed": False,
        "planning_snapshot": None,
        "financial_result": None,
        "authority_state": "NOT_EVALUATED",
    }
    return validate_inert_manifest(manifest)
