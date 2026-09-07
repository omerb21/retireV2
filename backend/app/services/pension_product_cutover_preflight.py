"""Offline cutover preflight, never a production balance reader.

The eventual migration freezes this algorithm with its schema revision. Input
is a read-only export of legacy rows; output is a deterministic conversion plan
or an explicit list of conflicts. No database or current writer is called here.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.models.pension_product import COMPONENT_CODES
from app.schemas.pension_product import exact_money
from app.services.pension_product_import_service import source_identity


class CutoverConflict(ValueError):
    def __init__(self, conflicts: list[dict]):
        self.conflicts = sorted(conflicts, key=lambda item: (item["client_id"], item["record_id"], item["code"]))
        super().__init__(f"Canonical cutover aborted: {self.conflicts}")


def build_cutover_plan(intakes: list[dict], revisions: list[dict], ledger_values: list[dict]) -> dict[str, Any]:
    conflicts: list[dict] = []
    products: dict[tuple[int, str], dict] = {}
    by_intake: dict[str, dict] = {}
    def conflict(row, code, record_id=None):
        conflicts.append({"client_id": row["client_id"], "record_id": record_id or row.get("intake_id") or row["revision_id"], "code": code})
    for row in sorted(intakes, key=lambda item: (item["client_id"], item["intake_id"])):
        if row["lifecycle_status"] in {"rejected", "superseded"}:
            continue
        # An opaque preserved upload with no authored product values is technical
        # evidence, not a product. Its archive row remains physically untouched.
        if row["record_kind"] == "uploaded_source" and not row.get("declared_component_values") and row.get("declared_total_balance_amount") is None and not row.get("declared_account_reference"):
            continue
        try:
            identity = source_identity(None, row.get("declared_provider_name"), row.get("declared_account_reference") or "", row.get("manual_technical_reference") if row["record_kind"] == "manual" else None)
        except ValueError:
            conflict(row, "ambiguous_product_identity")
            continue
        key = row["client_id"], identity
        if key in products:
            conflict(row, "competing_active_intakes")
            conflict(products[key]["legacy_intake"], "competing_active_intakes")
            continue
        components = dict.fromkeys(COMPONENT_CODES, Decimal("0.00"))
        mapped = set()
        diagnostics = []
        for index, item in enumerate(row.get("declared_component_values") or []):
            code = item.get("code") or item.get("label")
            if code not in COMPONENT_CODES:
                diagnostics.append({"code": "unmapped_legacy_component", "index": index, "source": item})
                continue
            if code in mapped:
                conflict(row, "duplicate_canonical_component")
                continue
            try:
                components[code] = exact_money(item["value"])
                mapped.add(code)
            except (ValueError, KeyError):
                conflict(row, "invalid_canonical_component_amount")
        try:
            total = None if row.get("declared_total_balance_amount") is None else exact_money(row["declared_total_balance_amount"])
        except ValueError:
            conflict(row, "invalid_reported_product_total")
            continue
        product = {
            "client_id": row["client_id"], "source_identity": identity,
            "legacy_intake": row, "components": components, "mapped_codes": mapped,
            "reported_product_total": total,
            # Legacy generic contribution/severance values were components, not
            # proven summary fields. They cannot populate these control totals.
            "reported_rewards_total": None, "reported_severance_total": None,
            "diagnostics": diagnostics, "legacy_revision_ids": [],
        }
        products[key] = product
        by_intake[row["intake_id"]] = product
    # Current leaf is determined by ancestry, not arbitrary timestamp ordering.
    parent_ids = {row["predecessor_revision_id"] for row in revisions if row.get("predecessor_revision_id")}
    leaves: dict[tuple[int, str], list[dict]] = {}
    for row in revisions:
        if row["revision_id"] not in parent_ids:
            leaves.setdefault((row["client_id"], row["subject_id"]), []).append(row)
    for _, rows in sorted(leaves.items()):
        if len(rows) != 1:
            for row in rows:
                conflict(row, "competing_ledger_leaves", row["revision_id"])
            continue
        row = rows[0]
        if row["state"] == "superseded":
            continue
        product = by_intake.get(row["intake_id"])
        if product is None or product["client_id"] != row["client_id"]:
            conflict(row, "ledger_without_unique_active_source", row["revision_id"])
            continue
        try:
            ledger_identity = source_identity(None, row["provider_name"], row["account_reference"])
        except ValueError:
            conflict(row, "ambiguous_ledger_identity", row["revision_id"])
            continue
        if ledger_identity != product["source_identity"]:
            conflict(row, "ledger_source_identity_conflict", row["revision_id"])
        total = row.get("effective_total_value")
        if total is not None and exact_money(total) != product["reported_product_total"]:
            conflict(row, "ledger_source_total_conflict", row["revision_id"])
        seen_codes = set()
        for value in ledger_values:
            if value["revision_id"] != row["revision_id"]:
                continue
            code = value.get("original_code") or value.get("original_label")
            if code not in COMPONENT_CODES:
                product["diagnostics"].append({"code": "unmapped_legacy_ledger_value", "source": value})
                continue
            if code in seen_codes:
                conflict(row, "duplicate_ledger_canonical_component", row["revision_id"])
                continue
            seen_codes.add(code)
            amount = value.get("effective_value")
            if amount is None:
                product["diagnostics"].append({"code": "missing_legacy_ledger_value", "source": value})
                continue
            amount = exact_money(amount)
            if code in product["mapped_codes"] and product["components"][code] != amount:
                conflict(row, "ledger_source_component_conflict", row["revision_id"])
            else:
                product["components"][code] = amount
        product["legacy_revision_ids"].append(row["revision_id"])
    if conflicts:
        raise CutoverConflict(conflicts)
    planned = [products[key] for key in sorted(products)]
    return {"products": planned, "counts": {"products": len(planned), "components": 11 * len(planned), "source_links": len(planned), "conflicts": 0, "unmapped_values": sum(len(item["diagnostics"]) for item in planned)}}
