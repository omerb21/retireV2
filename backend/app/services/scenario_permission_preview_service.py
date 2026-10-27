"""Read-only SC-PERM permission preview.

This boundary owns a dedicated connection and Session for every invocation. It
never calls the factual conversion services and never commits or flushes.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from decimal import Decimal
import hashlib
import json
import logging
import unicodedata
from typing import Any

logger = logging.getLogger(__name__)

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.pension_product import COMPONENT_CODES, PensionProduct, PensionProductComponent
from app.services.pension_product_reconciliation import reconcile


RULESET_DIGEST = "f3bd4c4bfe1fa07c96a7687dc99b756deb8de2f79083e05a74642b6b5d58800b"
RULESET_EFFECTIVE_FROM = date(2026, 10, 24)

_PRODUCT_MAPPINGS = (
    ("imported", "פוליסת ביטוח חיים משולב חיסכון", "insurance_policy", "map-imported-01"),
    ("imported", "קופת גמל", "provident_fund", "map-imported-03"),
    ("imported", "קרן פנסיה", "pension_fund", "map-imported-04"),
)
_AMBIGUOUS_IMPORTED = {"פוליסת ביטוח חיים"}

_PERMISSIONS = (
    ("standard-component-01", "blocked", "blocked"),
    ("standard-component-02", "allowed", "allowed"),
    ("standard-component-03", "blocked", "blocked"),
    ("standard-component-04", "blocked", "blocked"),
    ("standard-component-05", "allowed", "blocked"),
    ("standard-component-06", "allowed", "allowed"),
    ("standard-component-07", "allowed", "blocked"),
    ("standard-component-08", "allowed", "blocked"),
    ("standard-component-09", "allowed", "allowed"),
    ("standard-component-10", "allowed", "blocked"),
    ("standard-component-11", "allowed", "blocked"),
)
_PRODUCT_CLASSES = ["pension_fund", "insurance_policy", "provident_fund"]
_REASON_HE = {
    "BASE_PERMISSION_ALLOWED": "הפעולה מותרת לפי מטריצת ההרשאות הבסיסית",
    "BASE_PERMISSION_BLOCKED": "הפעולה חסומה לפי מטריצת ההרשאות הבסיסית",
}


class ScenarioPermissionError(RuntimeError):
    def __init__(self, code: str, status_code: int, field_paths: list[str] | None = None):
        super().__init__(code)
        self.code = code
        self.status_code = status_code
        self.field_paths = field_paths or []


def _ruleset_artifact() -> dict[str, Any]:
    component_rules = []
    for component_code, (rule_id, pension, capital) in zip(COMPONENT_CODES, _PERMISSIONS):
        component_rules.append({
            "rule_id": rule_id,
            "component_code": component_code,
            "applicable_product_classes": list(_PRODUCT_CLASSES),
            "actions": {
                "pension": {
                    "permission_status": pension,
                    "reason_code": f"BASE_PERMISSION_{pension.upper()}",
                },
                "capital_asset": {
                    "permission_status": capital,
                    "reason_code": f"BASE_PERMISSION_{capital.upper()}",
                },
            },
        })
    return {
        "schema": "scenario-permission-ruleset-v1",
        "ruleset_id": "retire-v2-permission-standard-20261024",
        "ruleset_version": 1,
        "status": "approved",
        "effective_from": "2026-10-24",
        "effective_until": None,
        "approved_by_actor_id": "github:omerb21",
        "approval_record_id": "owner-decisions-20261023-and-20261024",
        "predecessor_digest": None,
        "product_mappings": [
            {
                "source_kind": source_kind,
                "product_type": product_type,
                "canonical_product_class": product_class,
                "mapping_rule_id": rule_id,
            }
            for source_kind, product_type, product_class, rule_id in _PRODUCT_MAPPINGS
        ],
        "component_rules": component_rules,
        "source_integrity_overlays": [],
    }


def _normalize(value: Any) -> Any:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, dict):
        return {_normalize(key): _normalize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(
        _normalize(value), ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    )


_RULESET_CANONICAL_JSON = canonical_json(_ruleset_artifact())
if hashlib.sha256(_RULESET_CANONICAL_JSON.encode("utf-8")).hexdigest() != RULESET_DIGEST:
    raise RuntimeError("SC-PERM ruleset golden digest mismatch")


def permission_ruleset() -> dict[str, Any]:
    """Return a fresh value; callers cannot mutate the immutable artifact."""
    return json.loads(_RULESET_CANONICAL_JSON)


def ruleset_digest() -> str:
    return hashlib.sha256(_RULESET_CANONICAL_JSON.encode("utf-8")).hexdigest()


def _sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _money(value: Decimal) -> str:
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        raise ScenarioPermissionError("MISSING_CANONICAL_SOURCE", 409)
    rendered = format(value, ".2f")
    if Decimal(rendered) != value:
        raise ScenarioPermissionError("MISSING_CANONICAL_SOURCE", 409)
    return rendered


def _signed_money(value: Decimal | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ScenarioPermissionError("MISSING_CANONICAL_SOURCE", 409)
    rendered = format(value, ".2f")
    if Decimal(rendered) != value:
        raise ScenarioPermissionError("MISSING_CANONICAL_SOURCE", 409)
    return rendered


def _resolve_product(source_kind: str, product_type: str) -> tuple[str, str]:
    if not isinstance(source_kind, str) or source_kind not in {"manual", "imported"}:
        raise ScenarioPermissionError("MISSING_CANONICAL_SOURCE", 409)
    if not isinstance(product_type, str) or not product_type:
        raise ScenarioPermissionError("MISSING_CANONICAL_SOURCE", 409)
    source_kind = unicodedata.normalize("NFC", source_kind)
    product_type = unicodedata.normalize("NFC", product_type)
    for known_kind, known_type, product_class, mapping_rule_id in _PRODUCT_MAPPINGS:
        if source_kind == known_kind and product_type == known_type:
            return product_class, mapping_rule_id
    if source_kind == "manual" or (source_kind == "imported" and product_type in _AMBIGUOUS_IMPORTED):
        raise ScenarioPermissionError("AMBIGUOUS_PRODUCT_TYPE", 422, ["/product_id"])
    raise ScenarioPermissionError("UNKNOWN_PRODUCT_TYPE", 422, ["/product_id"])


def _selected_ruleset(effective_date: date) -> dict[str, Any]:
    if effective_date < RULESET_EFFECTIVE_FROM:
        raise ScenarioPermissionError("UNKNOWN_RULESET", 409, ["/effective_date"])
    return permission_ruleset()


def _read_snapshot(
    db: Session,
    client_id: int,
    product_id: str,
    action: str,
    effective_date: date,
) -> dict[str, Any]:
    ruleset = _selected_ruleset(effective_date)
    product = db.scalar(select(PensionProduct).where(
        PensionProduct.client_id == client_id,
        PensionProduct.product_id == product_id,
    ))
    if product is None:
        raise ScenarioPermissionError(
            "PREVIEW_SOURCE_NOT_FOUND", 404, ["/path/client_id", "/product_id"],
        )
    if (not isinstance(product.product_id, str) or not product.product_id
        or not isinstance(product.source_identity, str) or not product.source_identity
        or type(product.version) is not int or product.version <= 0
        or product.client_id != client_id):
        raise ScenarioPermissionError("MISSING_CANONICAL_SOURCE", 409)
    product_class, _mapping_rule_id = _resolve_product(product.source_kind, product.product_type)
    rows = db.scalars(select(PensionProductComponent).where(
        PensionProductComponent.product_id == product.product_id,
    )).all()
    by_code = {row.component_code: row for row in rows}
    if len(rows) != len(COMPONENT_CODES) or len(by_code) != len(COMPONENT_CODES) or set(by_code) != set(COMPONENT_CODES):
        raise ScenarioPermissionError("MISSING_CANONICAL_SOURCE", 409)

    rule_by_code = {rule["component_code"]: rule for rule in ruleset["component_rules"]}
    components: list[dict[str, Any]] = []
    source_components: list[dict[str, str]] = []
    totals = {
        "allowed": Decimal("0.00"),
        "blocked": Decimal("0.00"),
        "needs_source_reconciliation": Decimal("0.00"),
        "unknown": Decimal("0.00"),
    }
    balances: dict[str, Decimal] = {}
    for code in COMPONENT_CODES:
        row = by_code[code]
        if not isinstance(row.component_id, str) or not row.component_id:
            raise ScenarioPermissionError("MISSING_CANONICAL_SOURCE", 409)
        balance = row.balance
        rendered_balance = _money(balance)
        balances[code] = balance
        rule = rule_by_code[code]
        if product_class not in rule["applicable_product_classes"]:
            raise ScenarioPermissionError("UNKNOWN_RULESET", 409)
        decision = rule["actions"][action]
        status = decision["permission_status"]
        totals[status] += balance
        components.append({
            "component_code": code,
            "component_id": row.component_id,
            "balance": rendered_balance,
            "permission_status": status,
            "reason_code": decision["reason_code"],
            "reason_he": _REASON_HE[decision["reason_code"]],
            "applicable_rule_id": rule["rule_id"],
        })
        source_components.append({
            "component_code": code,
            "component_id": row.component_id,
            "balance": rendered_balance,
        })

    source_fingerprint = _sha256({
        "schema": "scenario-source-fingerprint-v1",
        "client_id": client_id,
        "product_id": product.product_id,
        "product_version": product.version,
        "source_kind": product.source_kind,
        "product_type": product.product_type,
        "components": source_components,
    })
    preview_id = _sha256({
        "schema": "scenario-permission-preview-id-v1",
        "client_id": client_id,
        "product_id": product.product_id,
        "source_fingerprint": source_fingerprint,
        "action": action,
        "effective_date": effective_date.isoformat(),
        "ruleset_id": ruleset["ruleset_id"],
        "ruleset_version": ruleset["ruleset_version"],
        "ruleset_digest": RULESET_DIGEST,
    })
    statuses = {component["permission_status"] for component in components}
    if "needs_source_reconciliation" in statuses:
        overall_status = "needs_source_reconciliation"
    elif "unknown" in statuses:
        overall_status = "unknown"
    elif {"allowed", "blocked"} <= statuses:
        overall_status = "mixed"
    elif "allowed" in statuses:
        overall_status = "allowed"
    else:
        overall_status = "blocked"
    factual = reconcile(
        balances, product.reported_product_total,
        product.reported_rewards_total, product.reported_severance_total,
    )
    return {
        "schema_version": "SCENARIO_PERMISSION_PREVIEW_V1",
        "preview_id": preview_id,
        "client_id": client_id,
        "product_id": product.product_id,
        "product_version": product.version,
        "canonical_product_class": product_class,
        "action": action,
        "effective_date": effective_date.isoformat(),
        "ruleset_id": ruleset["ruleset_id"],
        "ruleset_version": ruleset["ruleset_version"],
        "ruleset_digest": RULESET_DIGEST,
        "source_fingerprint": source_fingerprint,
        "overall_status": overall_status,
        "professional_eligibility_status": "not_evaluated",
        "tax_status": "not_evaluated",
        "components": components,
        "totals": {
            "original_classified_balance": _money(sum(balances.values(), Decimal("0.00"))),
            "allowed_balance": _money(totals["allowed"]),
            "blocked_balance": _money(totals["blocked"]),
            "needs_source_reconciliation_balance": _money(totals["needs_source_reconciliation"]),
            "unknown_balance": _money(totals["unknown"]),
        },
        "reconciliation": {key: _signed_money(value) for key, value in factual.items()},
    }


def _engine(factory: sessionmaker[Session]) -> Engine:
    bind = factory.kw.get("bind")
    if not isinstance(bind, Engine):
        raise ScenarioPermissionError("PREVIEW_DATABASE_UNAVAILABLE", 503)
    return bind


def preview(
    factory: sessionmaker[Session],
    *,
    client_id: int,
    product_id: str,
    action: str,
    effective_date: date,
    request_id: str = "unavailable",
) -> dict[str, Any]:
    """Execute one isolated read snapshot and destroy all owned resources."""
    _selected_ruleset(effective_date)
    engine = _engine(factory)
    connection = None
    transaction = None
    db = None
    result: dict[str, Any] | None = None
    primary: BaseException | None = None
    cleanup_failed = False
    cleanup_diagnostics: list[tuple[str, str]] = []
    try:
        connection = engine.connect()
        dialect = connection.dialect.name
        if dialect == "postgresql":
            connection = connection.execution_options(
                isolation_level="REPEATABLE READ", postgresql_readonly=True,
            )
            transaction = connection.begin()
        elif dialect == "sqlite":
            connection.exec_driver_sql("BEGIN")
            transaction = connection.get_transaction()
        else:
            raise ScenarioPermissionError("PREVIEW_DATABASE_UNAVAILABLE", 503)
        db = Session(bind=connection, autoflush=False, expire_on_commit=False)
        result = _read_snapshot(db, client_id, product_id, action, effective_date)
    except BaseException as exc:
        primary = exc
    finally:
        if connection is not None:
            try:
                if transaction is not None and transaction.is_active:
                    transaction.rollback()
                elif connection.in_transaction():
                    connection.rollback()
            except BaseException as exc:
                cleanup_failed = True
                cleanup_diagnostics.append(("rollback", type(exc).__name__))
        if db is not None:
            try:
                db.close()
            except BaseException as exc:
                cleanup_failed = True
                cleanup_diagnostics.append(("session_close", type(exc).__name__))
        if connection is not None:
            if cleanup_failed:
                try:
                    connection.invalidate()
                except BaseException as exc:
                    cleanup_diagnostics.append(("invalidate", type(exc).__name__))
            try:
                connection.close()
            except BaseException as exc:
                cleanup_failed = True
                cleanup_diagnostics.append(("connection_close", type(exc).__name__))
                try:
                    connection.invalidate()
                except BaseException as invalidate_exc:
                    cleanup_diagnostics.append(("invalidate", type(invalidate_exc).__name__))
    if cleanup_failed:
        logger.error(
            "scenario_permission_preview_cleanup_failed",
            extra={"request_id": request_id, "cleanup_failures": cleanup_diagnostics},
        )
        raise ScenarioPermissionError("PREVIEW_TRANSACTION_CLEANUP_FAILED", 503)
    if primary is not None:
        if isinstance(primary, ScenarioPermissionError):
            raise primary
        raise ScenarioPermissionError("PREVIEW_DATABASE_UNAVAILABLE", 503) from primary
    assert result is not None
    return deepcopy(result)



# Stage6-P1A: read-only, decision-scoped rule admission; not financial authority.
def derive_pension_action_permission_admission(
    db: Session, *, client_id: int, scenario_id: str, decision_id: str,
) -> dict[str, Any]:
    """Derive N1.6 evidence within the caller-owned, consistent read snapshot.

    The caller MUST hold a PostgreSQL REPEATABLE READ READ ONLY transaction.
    This function opens no connection, commits no writes, and does not call preview().
    """
    from app.services.scenario_input_manifest_service import build_inert_manifest
    from app.services.scenario_snapshot_candidate_service import _partition_verified_manifest

    bind = db.get_bind()
    if bind.dialect.name != "postgresql" or not db.in_transaction():
        raise ScenarioPermissionError("PENSION_PERMISSION_SNAPSHOT_REQUIRED", 409)
    if db.new or db.dirty or db.deleted:
        raise ScenarioPermissionError("PENSION_PERMISSION_DIRTY_SESSION", 409)
    # Verify actual transaction settings, not merely the intended caller policy.
    from sqlalchemy import text
    try:
        isolation = db.execute(text("SHOW transaction_isolation")).scalar_one()
        readonly = db.execute(text("SHOW transaction_read_only")).scalar_one()
    except Exception as exc:
        raise ScenarioPermissionError("PENSION_PERMISSION_SNAPSHOT_REQUIRED", 409) from exc
    if isolation.lower() != "repeatable read" or readonly.lower() != "on":
        raise ScenarioPermissionError("PENSION_PERMISSION_SNAPSHOT_REQUIRED", 409)
    return _derive_pension_action_permission_in_transaction(db, client_id=client_id, scenario_id=scenario_id, decision_id=decision_id)


def _derive_pension_action_permission_in_transaction(
    db: Session, *, client_id: int, scenario_id: str, decision_id: str,
) -> dict[str, Any]:
    """Internal shared rule evaluator; caller owns and validates transaction policy."""
    from app.services.scenario_input_manifest_service import build_inert_manifest
    from app.services.scenario_snapshot_candidate_service import _partition_verified_manifest
    with db.no_autoflush:
        manifest = build_inert_manifest(db, client_id, scenario_id)
        partition = _partition_verified_manifest(manifest)
        if partition["evidence_state"] != "STRUCTURALLY_CONSISTENT_NOT_ADMITTED":
            raise ScenarioPermissionError("PENSION_PERMISSION_SOURCE_STALE", 409)
        rows = [r for r in manifest["decisions"] if r["decision_id"] == decision_id]
        if len(rows) != 1:
            raise ScenarioPermissionError("PENSION_PERMISSION_DECISION_NOT_FOUND", 409)
        row = rows[0]
        source = row["source"]
        if row["action"] != "pension" or source is None:
            raise ScenarioPermissionError("PENSION_PERMISSION_ACTION_INVALID", 409)
        amount = Decimal(row["amount"])
        if not amount.is_finite() or amount <= 0:
            raise ScenarioPermissionError("PENSION_PERMISSION_AMOUNT_INVALID", 409)
        effective_date = date.fromisoformat(row["effective_date"])
        ruleset = _selected_ruleset(effective_date)
        if ruleset["status"] != "approved":
            raise ScenarioPermissionError("PENSION_PERMISSION_RULESET_INVALID", 409)
        if ruleset["effective_until"] is not None and effective_date.isoformat() > ruleset["effective_until"]:
            raise ScenarioPermissionError("PENSION_PERMISSION_RULESET_EXPIRED", 409)
        current_digest = ruleset_digest()
        if current_digest != RULESET_DIGEST:
            raise ScenarioPermissionError("PENSION_PERMISSION_RULESET_STALE", 409)
        # A stored preview is documentary only.  If a historical digest exists
        # it must still be current, but its absence cannot replace (or prevent)
        # this fresh in-snapshot rule evaluation.
        if (row["ruleset_digest_at_review"] is not None
                and row["ruleset_digest_at_review"] != current_digest):
            raise ScenarioPermissionError("PENSION_PERMISSION_RULESET_STALE", 409)
        product_class, _ = _resolve_product(source["source_kind"], source["product_type"])
        rules = [r for r in ruleset["component_rules"] if r["component_code"] == row["component_code"]]
        if len(rules) != 1 or product_class not in rules[0]["applicable_product_classes"]:
            raise ScenarioPermissionError("PENSION_PERMISSION_RULE_MISSING", 409)
        rule = rules[0]
        permission = rule["actions"].get("pension")
        if permission is None or permission["permission_status"] != "allowed" or permission["reason_code"] != "BASE_PERMISSION_ALLOWED":
            raise ScenarioPermissionError("PENSION_PERMISSION_NOT_ALLOWED", 409)
        preimage = {
            "contract_version": "SCENARIO_PENSION_ACTION_PERMISSION_ADMISSION_V1",
            "client_id": client_id,
            "scenario_id": scenario_id,
            "scenario_version": manifest["scenario_version"],
            "decision_id": decision_id,
            "source_product_id": source["product_id"],
            "source_product_version": source["product_version"],
            "source_component_id": source["component_id"],
            "source_fingerprint": source["source_fingerprint"],
            "component_code": row["component_code"],
            "amount": row["amount"],
            "action": "pension",
            "effective_date": row["effective_date"],
            "ruleset_id": ruleset["ruleset_id"],
            "ruleset_version": ruleset["ruleset_version"],
            "ruleset_digest": current_digest,
            "applicable_rule_id": rule["rule_id"],
            "permission_status": "allowed",
            "reason_code": "BASE_PERMISSION_ALLOWED",
        }
        return {
            "schema_version": "SCENARIO_PENSION_ACTION_PERMISSION_ADMISSION_V1",
            "permission_admission_fingerprint": _sha256(preimage),
            "permission_status": "allowed",
            "reason_code": "BASE_PERMISSION_ALLOWED",
            "applicable_rule_id": rule["rule_id"],
            "ruleset_id": ruleset["ruleset_id"],
            "ruleset_version": ruleset["ruleset_version"],
            "ruleset_digest": current_digest,
        }
