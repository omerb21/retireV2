from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import select
from app.models.canonical_manual_pension_source import CanonicalManualPensionSource as Manual
from app.services.pension_product_service import lock_client, PensionProductError, _json_snapshot
from app.services import pension_temporal_basis_service as temporal


def response(row):
    return _json_snapshot({c.name: getattr(row, c.name) for c in Manual.__table__.columns})


def create(db, client_id, payload):
    lock_client(db, client_id)
    values = payload.model_dump(exclude={"temporal_authority", "indexation_method", "fixed_indexation_rate"})
    row = Manual(manual_pension_source_id=uuid4().hex, client_id=client_id, **values)
    temporal.apply_manual(payload, row, creating=True)
    db.add(row)
    db.flush()
    return response(row)


def change(db, client_id, source_id, payload, *, supersede=False):
    lock_client(db, client_id)
    row = db.scalar(select(Manual).where(Manual.client_id == client_id, Manual.manual_pension_source_id == source_id)
                    .with_for_update().execution_options(populate_existing=True))
    if row is None:
        raise PensionProductError("MANUAL_PENSION_NOT_FOUND", "מקור הקצבה לא נמצא", 404)
    if row.lifecycle_status != "current":
        raise PensionProductError("MANUAL_PENSION_SUPERSEDED", "מקור הקצבה אינו נוכחי")
    if row.version != payload.expected_version:
        raise PensionProductError("STALE_MANUAL_PENSION_VERSION", "המקור השתנה; יש לרענן")
    if supersede:
        row.lifecycle_status = "superseded"
    else:
        temporal.apply_manual(payload, row, creating=False)
        for key, value in payload.model_dump(exclude={"expected_version", "temporal_authority", "indexation_method", "fixed_indexation_rate"}).items():
            if key == "base_amount_effective_date" and key not in payload.model_fields_set:
                continue
            setattr(row, key, value)
    row.version += 1
    row.updated_at = datetime.now(timezone.utc)
    db.flush()
    return response(row)
