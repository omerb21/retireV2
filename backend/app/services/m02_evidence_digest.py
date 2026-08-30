from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
import hashlib
import json
import re
from typing import Any

from sqlalchemy import select

from app.models.m02_intake import (
    M02IntakeRecord,
    M02PreservedBlob,
    M02PreservedSource,
)


SCHEMA_VERSION = "m03-m02-evidence-v1"
DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
SNAPSHOT_KEYS = {
    "schema_version",
    "client_id",
    "intake_id",
    "target_kind",
    "record_kind",
    "declared_provider_name",
    "product_name",
    "product_identifier",
    "declared_account_reference",
    "declared_total_balance_amount",
    "declared_monthly_pension_amount",
    "declared_component_values",
    "declared_statement_date",
    "declared_start_date",
    "declared_product_type",
    "source_type",
    "declared_basis",
    "notes",
    "preservation_status",
    "preservation_failure_code",
    "source",
}
SOURCE_KEYS = {
    "source_id",
    "blob_id",
    "original_filename",
    "sanitized_download_filename",
    "normalized_extension",
    "declared_mime_type",
    "validated_media_type",
    "detected_text_encoding",
    "source_type",
    "declared_statement_date",
    "byte_size",
    "preservation_status",
    "validation_diagnostics",
    "blob_sha256_checksum",
    "blob_byte_size",
    "blob_validated_media_type",
}


@dataclass(frozen=True)
class M02Evidence:
    snapshot_json: str
    digest: str
    payload: dict[str, Any]


def _value(record: object, name: str) -> Any:
    if isinstance(record, Mapping):
        return record[name]
    return getattr(record, name)


def canonical_value(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, Mapping):
        return {
            str(key): canonical_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [canonical_value(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def canonical_json(value: Any) -> str:
    return json.dumps(
        canonical_value(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def digest_snapshot(snapshot_json: str) -> str:
    return hashlib.sha256(snapshot_json.encode("utf-8")).hexdigest()


def build_m02_evidence(
    intake: object,
    target_kind: str,
    source: object | None = None,
    blob: object | None = None,
) -> M02Evidence:
    if source is not None and blob is None and not isinstance(source, Mapping):
        blob = getattr(source, "blob", None)
    payload = canonical_value(
        {
            "schema_version": SCHEMA_VERSION,
            "client_id": _value(intake, "client_id"),
            "intake_id": _value(intake, "intake_id"),
            "target_kind": target_kind,
            "record_kind": _value(intake, "record_kind"),
            "declared_provider_name": _value(intake, "declared_provider_name"),
            "product_name": _value(intake, "product_name"),
            "product_identifier": _value(intake, "product_identifier"),
            "declared_account_reference": _value(
                intake, "declared_account_reference"
            ),
            "declared_total_balance_amount": _value(
                intake, "declared_total_balance_amount"
            ),
            "declared_monthly_pension_amount": _value(
                intake, "declared_monthly_pension_amount"
            ),
            "declared_component_values": _value(
                intake, "declared_component_values"
            ),
            "declared_statement_date": _value(intake, "declared_statement_date"),
            "declared_start_date": _value(intake, "declared_start_date"),
            "declared_product_type": _value(intake, "declared_product_type"),
            "source_type": _value(intake, "source_type"),
            "declared_basis": _value(intake, "declared_basis"),
            "notes": _value(intake, "notes"),
            "preservation_status": _value(intake, "preservation_status"),
            "preservation_failure_code": _value(
                intake, "preservation_failure_code"
            ),
            "source": (
                {
                    "source_id": _value(source, "source_id"),
                    "blob_id": _value(source, "blob_id"),
                    "original_filename": _value(source, "original_filename"),
                    "sanitized_download_filename": _value(
                        source, "sanitized_download_filename"
                    ),
                    "normalized_extension": _value(
                        source, "normalized_extension"
                    ),
                    "declared_mime_type": _value(source, "declared_mime_type"),
                    "validated_media_type": _value(
                        source, "validated_media_type"
                    ),
                    "detected_text_encoding": _value(
                        source, "detected_text_encoding"
                    ),
                    "source_type": _value(source, "source_type"),
                    "declared_statement_date": _value(
                        source, "declared_statement_date"
                    ),
                    "byte_size": _value(source, "byte_size"),
                    "preservation_status": _value(
                        source, "preservation_status"
                    ),
                    "validation_diagnostics": _value(
                        source, "validation_diagnostics"
                    ),
                    "blob_sha256_checksum": (
                        _value(blob, "sha256_checksum")
                        if blob is not None
                        else None
                    ),
                    "blob_byte_size": (
                        _value(blob, "byte_size") if blob is not None else None
                    ),
                    "blob_validated_media_type": (
                        _value(blob, "validated_media_type")
                        if blob is not None
                        else None
                    ),
                }
                if source is not None
                else None
            ),
        }
    )
    snapshot_json = canonical_json(payload)
    return M02Evidence(
        snapshot_json=snapshot_json,
        digest=digest_snapshot(snapshot_json),
        payload=payload,
    )


def evidence_from_snapshot(snapshot_json: str) -> M02Evidence:
    if not isinstance(snapshot_json, str) or not snapshot_json:
        raise ValueError("M02 evidence snapshot must be non-empty text")
    try:
        payload = json.loads(snapshot_json)
    except (TypeError, json.JSONDecodeError) as error:
        raise ValueError("M02 evidence snapshot is not valid JSON") from error
    if not isinstance(payload, dict) or set(payload) != SNAPSHOT_KEYS:
        raise ValueError("M02 evidence snapshot shape is invalid")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("M02 evidence snapshot schema is unsupported")
    source = payload.get("source")
    if source is not None and (
        not isinstance(source, dict) or set(source) != SOURCE_KEYS
    ):
        raise ValueError("M02 source evidence snapshot shape is invalid")
    canonical = canonical_json(payload)
    if canonical != snapshot_json:
        raise ValueError("M02 evidence snapshot is not canonical")
    return M02Evidence(
        snapshot_json=canonical,
        digest=digest_snapshot(canonical),
        payload=payload,
    )


def load_authoritative_m02_evidence(
    connection,
    *,
    client_id: int,
    intake_id: str,
    target_kind: str,
    source_id: str | None,
) -> M02Evidence:
    intake = connection.execute(
        select(M02IntakeRecord.__table__).where(
            M02IntakeRecord.intake_id == intake_id,
            M02IntakeRecord.client_id == client_id,
        )
    ).mappings().one_or_none()
    if intake is None:
        raise ValueError("M03 review target must belong to the same client")

    if intake["record_kind"] == "manual":
        existing_source = connection.execute(
            select(M02PreservedSource.source_id).where(
                M02PreservedSource.intake_id == intake_id
            )
        ).first()
        if (
            target_kind != "manual_record_review"
            or source_id is not None
            or existing_source is not None
        ):
            raise ValueError("M03 manual review provenance is inconsistent")
        return build_m02_evidence(intake, target_kind)

    if intake["record_kind"] != "uploaded_source":
        raise ValueError("M03 review target kind is unsupported")
    source = connection.execute(
        select(M02PreservedSource.__table__).where(
            M02PreservedSource.source_id == source_id,
            M02PreservedSource.client_id == client_id,
            M02PreservedSource.intake_id == intake_id,
        )
    ).mappings().one_or_none()
    if target_kind != "source_evidence_review" or source is None:
        raise ValueError("M03 uploaded review provenance is inconsistent")
    blob = connection.execute(
        select(M02PreservedBlob.__table__).where(
            M02PreservedBlob.blob_id == source["blob_id"],
            M02PreservedBlob.client_id == client_id,
        )
    ).mappings().one_or_none()
    if (
        blob is None
        or intake["preservation_status"] != "preserved"
        or source["preservation_status"] != "preserved"
        or source["byte_size"] != blob["byte_size"]
        or not blob["sha256_checksum"]
    ):
        raise ValueError("M03 uploaded review provenance is inconsistent")
    return build_m02_evidence(intake, target_kind, source, blob)


def is_valid_digest(value: str | None) -> bool:
    return isinstance(value, str) and DIGEST_PATTERN.fullmatch(value) is not None


def validate_stored_m02_evidence(
    snapshot_json: str | None,
    digest: str | None,
    *,
    client_id: int,
    intake_id: str,
    target_kind: str,
    source_id: str | None,
) -> M02Evidence | None:
    if snapshot_json is None:
        if digest is not None and not is_valid_digest(digest):
            raise ValueError("Legacy M02 evidence digest is invalid")
        return None
    evidence = evidence_from_snapshot(snapshot_json)
    if not is_valid_digest(digest) or evidence.digest != digest:
        raise ValueError("Stored M02 evidence digest does not match its snapshot")
    payload = evidence.payload
    if (
        payload["client_id"] != client_id
        or payload["intake_id"] != intake_id
        or payload["target_kind"] != target_kind
    ):
        raise ValueError("Stored M02 evidence snapshot scope is invalid")
    source = payload["source"]
    if target_kind == "manual_record_review":
        if (
            payload["record_kind"] != "manual"
            or source_id is not None
            or source is not None
        ):
            raise ValueError("Stored manual M02 evidence snapshot is invalid")
    elif target_kind == "source_evidence_review":
        if (
            payload["record_kind"] != "uploaded_source"
            or not isinstance(source, dict)
            or source["source_id"] != source_id
        ):
            raise ValueError("Stored source M02 evidence snapshot is invalid")
    else:
        raise ValueError("Stored M02 evidence target kind is invalid")
    return evidence
