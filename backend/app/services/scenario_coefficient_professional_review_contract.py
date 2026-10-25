"""SC-05E: fail-closed validation of a professional coefficient review record.

A supplied record is documentary evidence only. It never establishes trusted
signer identity or permission to invoke a coefficient engine. That requires a
separate authenticated writer and DB-derived reader, not implemented here.
"""
from __future__ import annotations

from datetime import datetime, timezone
import re

from app.services.scenario_input_manifest_service import _fingerprint

_SHA = re.compile(r"^[a-f0-9]{64}$")
_REQUIRED = frozenset({
    "schema_version", "client_id", "scenario_id", "scenario_version",
    "decision_id", "product_id", "component_id", "product_version",
    "manifest_fingerprint", "inventory_fingerprint", "election_fingerprint",
    "source_fingerprint", "professional_actor_id", "reviewed_at",
    "review_reference", "decision", "record_fingerprint",
})
_CONTEXT = frozenset({
    "client_id", "scenario_id", "scenario_version", "decision_id",
    "product_id", "component_id", "product_version", "manifest_fingerprint",
    "inventory_fingerprint", "election_fingerprint", "source_fingerprint",
})


def validate_documentary_review(record: object, expected: object) -> dict:
    """Validate exact provenance and integrity, without granting execution.

    expected MUST come from a trusted same-snapshot DB projection, never from
    the record or external request. No live-signature or identity claims here.
    """
    base = {
        "schema_version": "SCENARIO_COEFFICIENT_REVIEW_VALIDATION_V1",
        "state": "BLOCKED",
        "blockers": [],
        "execution_allowed": False,
        "coefficient_candidate": None,
        "planning_snapshot": None,
        "financial_result": None,
        "authority_state": "NOT_EVALUATED",
    }
    def reject(code):
        return {**base, "blockers": [code]}

    if type(record) is not dict or set(record) != _REQUIRED:
        return reject("REVIEW_RECORD_SHAPE_INVALID")
    if type(expected) is not dict or set(expected) != _CONTEXT:
        return reject("TRUSTED_CONTEXT_MISSING")
    if record.get("schema_version") != "SCENARIO_COEFFICIENT_REVIEW_V1":
        return reject("REVIEW_SCHEMA_INVALID")
    if (type(record["client_id"]) is not int or record["client_id"] <= 0
            or type(record["scenario_version"]) is not int or record["scenario_version"] <= 0
            or type(record["product_version"]) is not int or record["product_version"] <= 0
            or any(type(record[k]) is not str or not record[k] or len(record[k]) > 128
                   for k in ("scenario_id", "decision_id", "product_id", "component_id",
                             "professional_actor_id", "review_reference"))
            or any(type(record[k]) is not str or not _SHA.fullmatch(record[k])
                   for k in ("manifest_fingerprint", "inventory_fingerprint",
                             "election_fingerprint", "source_fingerprint", "record_fingerprint"))):
        return reject("REVIEW_FIELDS_INVALID")
    if record["decision"] not in {"reviewed_for_candidate", "rejected"}:
        return reject("REVIEW_DECISION_INVALID")
    if type(record["reviewed_at"]) is not str:
        return reject("REVIEW_TIMESTAMP_INVALID")
    try:
        dt = datetime.fromisoformat(record["reviewed_at"])
        if dt.tzinfo is None or dt.utcoffset() is None or dt.utcoffset().total_seconds() != 0:
            return reject("REVIEW_TIMESTAMP_INVALID")
    except ValueError:
        return reject("REVIEW_TIMESTAMP_INVALID")
    if record["record_fingerprint"] != _fingerprint({
        k: v for k, v in record.items() if k != "record_fingerprint"
    }):
        return reject("REVIEW_INTEGRITY_INVALID")
    if any(type(record[k]) is not type(expected[k]) or record[k] != expected[k]
           for k in _CONTEXT):
        return reject("REVIEW_PROVENANCE_STALE")
    return {
        **base,
        "state": "DOCUMENTARY_REVIEW_MATCHED_NOT_AUTHORIZED",
        "record_fingerprint": record["record_fingerprint"],
        "review_decision": record["decision"],
    }
