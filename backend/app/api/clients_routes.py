from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.actual_capitalization import ActualCapitalization
from app.models.clearinghouse_snapshot import ClearinghouseSnapshot
from app.models.client import Client
from app.models.client_profile import ClientProfile
from app.models.employment_record import EmploymentRecord
from app.models.grant import Grant
from app.models.retirement_planning_document import RetirementPlanningDocument

router = APIRouter(prefix="/api/clients", tags=["clients"])


class ApiError(BaseModel):
    code: str
    message: str


class ClientCreateRequest(BaseModel):
    full_name: str
    id_number: str
    birth_date: date | None = None


class ClientResponse(BaseModel):
    client_id: int
    full_name: str
    id_number: str
    birth_date: date | None = None
    file_status: str
    professional_identification_status: str


class ProfileUpsertRequest(BaseModel):
    id_number: str | None = None
    birth_date: date | None = None
    gender: str | None = None
    contact_method: str | None = None
    contact_details: str | None = None
    notes: str | None = None


class ProfileResponse(BaseModel):
    client_profile_id: str
    client_id: int
    id_number: str | None
    birth_date: date | None
    gender: str | None
    contact_method: str | None
    contact_details: str | None
    notes: str | None
    file_status: str
    professional_identification_status: str


class EmploymentRecordRequest(BaseModel):
    employer_name: str
    work_start_date: date
    work_end_date: date | None = None
    is_current: bool
    notes: str | None = None


class EmploymentRecordResponse(BaseModel):
    employment_record_id: str
    client_id: int
    employer_name: str
    work_start_date: date
    work_end_date: date | None
    is_current: bool
    notes: str | None


class GrantRequest(BaseModel):
    employment_record_id: str | None = None
    employer_name: str | None = None
    nominal_amount: Decimal | None = None
    indexed_amount: Decimal
    grant_date: date
    work_start_date: date
    work_end_date: date
    notes: str | None = None


class GrantResponse(BaseModel):
    grant_id: str
    client_id: int
    employment_record_id: str | None
    employer_name: str | None
    nominal_amount: Decimal | None
    indexed_amount: Decimal
    grant_date: date
    work_start_date: date
    work_end_date: date
    notes: str | None


class ActualCapitalizationRequest(BaseModel):
    amount: Decimal
    capitalization_date: date
    source_label: str | None = None
    notes: str | None = None


class ActualCapitalizationResponse(BaseModel):
    capitalization_id: str
    client_id: int
    amount: Decimal
    capitalization_date: date
    source_label: str | None
    notes: str | None


class ClearinghouseSnapshotRequest(BaseModel):
    import_date: date
    source_type: str
    source_file: str
    collection_status: str
    collection_notes: str | None = None


class ClearinghouseSnapshotResponse(BaseModel):
    clearinghouse_snapshot_id: str
    client_id: int
    import_date: date
    source_type: str
    source_file: str
    collection_status: str
    collection_notes: str | None
    created_at: datetime


class RetirementPlanningDocumentRequest(BaseModel):
    document_type: str
    source_type: str | None = None
    source_file: str
    collection_date: date
    collection_status: str
    collection_notes: str | None = None


class RetirementPlanningDocumentResponse(BaseModel):
    document_id: str
    client_id: int
    document_type: str
    source_type: str | None
    source_file: str
    collection_date: date
    collection_status: str
    collection_notes: str | None
    created_at: datetime


def _client_not_found(client_id: int) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={"code": "CLIENT_NOT_FOUND", "message": f"Client {client_id} was not found"},
    )


def _require_client(db: Session, client_id: int) -> Client:
    client = db.get(Client, client_id)
    if client is None:
        raise _client_not_found(client_id)
    return client


def _has_text(value: str | None) -> bool:
    return value is not None and value.strip() != ""


def _professional_identification_status(client: Client, profile: ClientProfile | None) -> str:
    has_required_fields = (
        _has_text(client.display_name)
        and _has_text(client.id_number)
        and client.birth_date is not None
        and profile is not None
        and _has_text(profile.contact_method)
        and _has_text(profile.contact_details)
    )
    return "professionally_identified" if has_required_fields else "identification_incomplete"


def _client_to_response(client: Client, profile: ClientProfile | None = None) -> ClientResponse:
    resolved_profile = profile if profile is not None else client.client_profile
    return ClientResponse(
        client_id=client.client_id,
        full_name=client.display_name,
        id_number=client.id_number,
        birth_date=client.birth_date,
        file_status="file_created",
        professional_identification_status=_professional_identification_status(client, resolved_profile),
    )


def _profile_to_response(client: Client, profile: ClientProfile) -> ProfileResponse:
    return ProfileResponse(
        client_profile_id=profile.client_profile_id,
        client_id=client.client_id,
        id_number=client.id_number,
        birth_date=profile.birth_date,
        gender=profile.gender,
        contact_method=profile.contact_method,
        contact_details=profile.contact_details,
        notes=profile.notes,
        file_status="file_created",
        professional_identification_status=_professional_identification_status(client, profile),
    )


def _source_item_not_found(code: str, message: str) -> HTTPException:
    return HTTPException(status_code=404, detail={"code": code, "message": message})


def _employment_record_to_response(row: EmploymentRecord) -> EmploymentRecordResponse:
    return EmploymentRecordResponse(
        employment_record_id=row.employment_record_id,
        client_id=row.client_id,
        employer_name=row.employer_name,
        work_start_date=row.work_start_date,
        work_end_date=row.work_end_date,
        is_current=row.is_current,
        notes=row.notes,
    )


def _grant_to_response(row: Grant) -> GrantResponse:
    return GrantResponse(
        grant_id=row.grant_id,
        client_id=row.client_id,
        employment_record_id=row.employment_record_id,
        employer_name=row.employer_name,
        nominal_amount=row.nominal_amount,
        indexed_amount=row.indexed_amount,
        grant_date=row.grant_date,
        work_start_date=row.work_start_date,
        work_end_date=row.work_end_date,
        notes=row.notes,
    )


def _actual_capitalization_to_response(row: ActualCapitalization) -> ActualCapitalizationResponse:
    return ActualCapitalizationResponse(
        capitalization_id=row.capitalization_id,
        client_id=row.client_id,
        amount=row.amount,
        capitalization_date=row.capitalization_date,
        source_label=row.source_label,
        notes=row.notes,
    )


def _required_collection_text(value: str, field_name: str) -> str:
    if not _has_text(value):
        raise HTTPException(
            status_code=422,
            detail={
                "code": "COLLECTION_METADATA_REQUIRED",
                "message": f"{field_name} is required for collection metadata",
            },
        )
    return value.strip()


def _clearinghouse_snapshot_to_response(row: ClearinghouseSnapshot) -> ClearinghouseSnapshotResponse:
    return ClearinghouseSnapshotResponse(
        clearinghouse_snapshot_id=row.clearinghouse_snapshot_id,
        client_id=row.client_id,
        import_date=row.import_date,
        source_type=row.source_type,
        source_file=row.source_file,
        collection_status=row.collection_status,
        collection_notes=row.collection_notes,
        created_at=row.created_at,
    )


def _document_to_response(row: RetirementPlanningDocument) -> RetirementPlanningDocumentResponse:
    return RetirementPlanningDocumentResponse(
        document_id=row.document_id,
        client_id=row.client_id,
        document_type=row.document_type,
        source_type=row.source_type,
        source_file=row.source_file,
        collection_date=row.collection_date,
        collection_status=row.collection_status,
        collection_notes=row.collection_notes,
        created_at=row.created_at,
    )


def _require_employment_record(db: Session, client_id: int, employment_record_id: str) -> EmploymentRecord:
    row = db.scalar(
        select(EmploymentRecord).where(
            EmploymentRecord.client_id == client_id,
            EmploymentRecord.employment_record_id == employment_record_id,
        )
    )
    if row is None:
        raise _source_item_not_found(
            "EMPLOYMENT_RECORD_NOT_FOUND",
            f"Employment record {employment_record_id} was not found for client {client_id}",
        )
    return row


def _require_grant(db: Session, client_id: int, grant_id: str) -> Grant:
    row = db.scalar(select(Grant).where(Grant.client_id == client_id, Grant.grant_id == grant_id))
    if row is None:
        raise _source_item_not_found(
            "GRANT_NOT_FOUND",
            f"Grant {grant_id} was not found for client {client_id}",
        )
    return row


def _require_actual_capitalization(db: Session, client_id: int, capitalization_id: str) -> ActualCapitalization:
    row = db.scalar(
        select(ActualCapitalization).where(
            ActualCapitalization.client_id == client_id,
            ActualCapitalization.capitalization_id == capitalization_id,
        )
    )
    if row is None:
        raise _source_item_not_found(
            "ACTUAL_CAPITALIZATION_NOT_FOUND",
            f"Actual capitalization {capitalization_id} was not found for client {client_id}",
        )
    return row


def _require_clearinghouse_snapshot(
    db: Session, client_id: int, clearinghouse_snapshot_id: str
) -> ClearinghouseSnapshot:
    row = db.scalar(
        select(ClearinghouseSnapshot).where(
            ClearinghouseSnapshot.client_id == client_id,
            ClearinghouseSnapshot.clearinghouse_snapshot_id == clearinghouse_snapshot_id,
        )
    )
    if row is None:
        raise _source_item_not_found(
            "CLEARINGHOUSE_SNAPSHOT_NOT_FOUND",
            f"Clearinghouse snapshot {clearinghouse_snapshot_id} was not found for client {client_id}",
        )
    return row


def _require_retirement_planning_document(db: Session, client_id: int, document_id: str) -> RetirementPlanningDocument:
    row = db.scalar(
        select(RetirementPlanningDocument).where(
            RetirementPlanningDocument.client_id == client_id,
            RetirementPlanningDocument.document_id == document_id,
        )
    )
    if row is None:
        raise _source_item_not_found(
            "RETIREMENT_PLANNING_DOCUMENT_NOT_FOUND",
            f"Retirement planning document {document_id} was not found for client {client_id}",
        )
    return row


@router.get("", response_model=list[ClientResponse])
def list_clients(db: Session = Depends(get_db)) -> list[ClientResponse]:
    clients = db.scalars(select(Client).order_by(Client.client_id.asc())).all()
    return [
        _client_to_response(client)
        for client in clients
    ]


@router.post("", response_model=ClientResponse)
def create_client(payload: ClientCreateRequest, db: Session = Depends(get_db)) -> ClientResponse:
    if not _has_text(payload.id_number):
        raise HTTPException(
            status_code=422,
            detail={"code": "ID_NUMBER_REQUIRED", "message": "ID Number is required for file creation"},
        )

    client = Client(
        display_name=payload.full_name,
        id_number=payload.id_number.strip(),
        birth_date=payload.birth_date,
        status=None,
    )
    db.add(client)
    db.commit()
    db.refresh(client)

    return _client_to_response(client)


@router.get("/{client_id}", response_model=ClientResponse)
def get_client(client_id: int, db: Session = Depends(get_db)) -> ClientResponse:
    client = _require_client(db, client_id)
    return _client_to_response(client)


@router.put("/{client_id}/profile")
def put_client_profile(
    client_id: int,
    payload: ProfileUpsertRequest,
    db: Session = Depends(get_db),
) -> dict:
    client = _require_client(db, client_id)
    client_key = client_id

    profile = db.scalar(select(ClientProfile).where(ClientProfile.client_id == client_key))
    if profile is None:
        profile = ClientProfile(
            client_profile_id=f"CP-{client_id}",
            client_id=client_key,
            birth_date=payload.birth_date,
            gender=payload.gender,
            contact_method=payload.contact_method,
            contact_details=payload.contact_details,
            notes=payload.notes,
        )
        db.add(profile)
    else:
        profile.birth_date = payload.birth_date
        profile.gender = payload.gender
        profile.contact_method = payload.contact_method
        profile.contact_details = payload.contact_details
        profile.notes = payload.notes

    if payload.id_number is not None:
        if not _has_text(payload.id_number):
            raise HTTPException(
                status_code=422,
                detail={"code": "ID_NUMBER_REQUIRED", "message": "ID Number is required for file creation"},
            )
        client.id_number = payload.id_number.strip()
    if payload.birth_date is not None:
        client.birth_date = payload.birth_date

    db.commit()
    db.refresh(client)
    db.refresh(profile)
    return {
        "profile": _profile_to_response(client, profile).model_dump(mode="json")
    }


@router.get("/{client_id}/profile")
def get_client_profile(client_id: int, db: Session = Depends(get_db)) -> dict:
    client = _require_client(db, client_id)
    profile = db.scalar(select(ClientProfile).where(ClientProfile.client_id == client_id))
    if profile is None:
        return {"profile": None}

    return {
        "profile": _profile_to_response(client, profile).model_dump(mode="json")
    }


@router.post("/{client_id}/clearinghouse-snapshots", response_model=ClearinghouseSnapshotResponse)
def create_clearinghouse_snapshot(
    client_id: int,
    payload: ClearinghouseSnapshotRequest,
    db: Session = Depends(get_db),
) -> ClearinghouseSnapshotResponse:
    _require_client(db, client_id)

    snapshot = ClearinghouseSnapshot(
        clearinghouse_snapshot_id=f"CHS-{uuid4().hex}",
        client_id=client_id,
        import_date=payload.import_date,
        source_type=_required_collection_text(payload.source_type, "Source Type"),
        source_file=_required_collection_text(payload.source_file, "Source File"),
        collection_status=_required_collection_text(payload.collection_status, "Collection Status"),
        collection_notes=payload.collection_notes,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)

    return _clearinghouse_snapshot_to_response(snapshot)


@router.get("/{client_id}/clearinghouse-snapshots", response_model=list[ClearinghouseSnapshotResponse])
def list_clearinghouse_snapshots(
    client_id: int,
    db: Session = Depends(get_db),
) -> list[ClearinghouseSnapshotResponse]:
    _require_client(db, client_id)
    snapshots = db.scalars(
        select(ClearinghouseSnapshot)
        .where(ClearinghouseSnapshot.client_id == client_id)
        .order_by(ClearinghouseSnapshot.created_at.desc(), ClearinghouseSnapshot.clearinghouse_snapshot_id.desc())
    ).all()

    return [_clearinghouse_snapshot_to_response(row) for row in snapshots]


@router.get(
    "/{client_id}/clearinghouse-snapshots/{clearinghouse_snapshot_id}",
    response_model=ClearinghouseSnapshotResponse,
)
def get_clearinghouse_snapshot(
    client_id: int,
    clearinghouse_snapshot_id: str,
    db: Session = Depends(get_db),
) -> ClearinghouseSnapshotResponse:
    _require_client(db, client_id)
    snapshot = _require_clearinghouse_snapshot(db, client_id, clearinghouse_snapshot_id)
    return _clearinghouse_snapshot_to_response(snapshot)


@router.post("/{client_id}/documents", response_model=RetirementPlanningDocumentResponse)
def create_retirement_planning_document(
    client_id: int,
    payload: RetirementPlanningDocumentRequest,
    db: Session = Depends(get_db),
) -> RetirementPlanningDocumentResponse:
    _require_client(db, client_id)

    document = RetirementPlanningDocument(
        document_id=f"DOC-{uuid4().hex}",
        client_id=client_id,
        document_type=_required_collection_text(payload.document_type, "Document Type"),
        source_type=payload.source_type.strip() if _has_text(payload.source_type) else None,
        source_file=_required_collection_text(payload.source_file, "Source File"),
        collection_date=payload.collection_date,
        collection_status=_required_collection_text(payload.collection_status, "Collection Status"),
        collection_notes=payload.collection_notes,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    return _document_to_response(document)


@router.get("/{client_id}/documents", response_model=list[RetirementPlanningDocumentResponse])
def list_retirement_planning_documents(
    client_id: int,
    db: Session = Depends(get_db),
) -> list[RetirementPlanningDocumentResponse]:
    _require_client(db, client_id)
    documents = db.scalars(
        select(RetirementPlanningDocument)
        .where(RetirementPlanningDocument.client_id == client_id)
        .order_by(RetirementPlanningDocument.created_at.desc(), RetirementPlanningDocument.document_id.desc())
    ).all()

    return [_document_to_response(row) for row in documents]


@router.get("/{client_id}/documents/{document_id}", response_model=RetirementPlanningDocumentResponse)
def get_retirement_planning_document(
    client_id: int,
    document_id: str,
    db: Session = Depends(get_db),
) -> RetirementPlanningDocumentResponse:
    _require_client(db, client_id)
    document = _require_retirement_planning_document(db, client_id, document_id)
    return _document_to_response(document)


@router.post("/{client_id}/employment-records", response_model=EmploymentRecordResponse)
def create_employment_record(
    client_id: int,
    payload: EmploymentRecordRequest,
    db: Session = Depends(get_db),
) -> EmploymentRecordResponse:
    _require_client(db, client_id)

    record = EmploymentRecord(
        employment_record_id=f"ER-{uuid4().hex}",
        client_id=client_id,
        employer_name=payload.employer_name,
        work_start_date=payload.work_start_date,
        work_end_date=payload.work_end_date,
        is_current=payload.is_current,
        notes=payload.notes,
    )
    db.add(record)
    db.commit()

    return _employment_record_to_response(record)


@router.get("/{client_id}/employment-records", response_model=list[EmploymentRecordResponse])
def list_employment_records(client_id: int, db: Session = Depends(get_db)) -> list[EmploymentRecordResponse]:
    _require_client(db, client_id)
    records = db.scalars(
        select(EmploymentRecord)
        .where(EmploymentRecord.client_id == client_id)
        .order_by(EmploymentRecord.employment_record_id)
    ).all()
    return [
        _employment_record_to_response(row)
        for row in records
    ]


@router.put(
    "/{client_id}/employment-records/{employment_record_id}",
    response_model=EmploymentRecordResponse,
)
def update_employment_record(
    client_id: int,
    employment_record_id: str,
    payload: EmploymentRecordRequest,
    db: Session = Depends(get_db),
) -> EmploymentRecordResponse:
    _require_client(db, client_id)
    record = _require_employment_record(db, client_id, employment_record_id)

    record.employer_name = payload.employer_name
    record.work_start_date = payload.work_start_date
    record.work_end_date = payload.work_end_date
    record.is_current = payload.is_current
    record.notes = payload.notes
    db.commit()
    db.refresh(record)

    return _employment_record_to_response(record)


@router.delete("/{client_id}/employment-records/{employment_record_id}")
def delete_employment_record(
    client_id: int,
    employment_record_id: str,
    db: Session = Depends(get_db),
) -> dict:
    _require_client(db, client_id)
    record = _require_employment_record(db, client_id, employment_record_id)

    db.delete(record)
    db.commit()
    return {"deleted": True, "employment_record_id": employment_record_id}


@router.post("/{client_id}/grants", response_model=GrantResponse)
def create_grant(client_id: int, payload: GrantRequest, db: Session = Depends(get_db)) -> GrantResponse:
    _require_client(db, client_id)
    if payload.employment_record_id is not None:
        _require_employment_record(db, client_id, payload.employment_record_id)

    grant = Grant(
        grant_id=f"GR-{uuid4().hex}",
        client_id=client_id,
        employment_record_id=payload.employment_record_id,
        employer_name=payload.employer_name,
        nominal_amount=payload.nominal_amount,
        indexed_amount=payload.indexed_amount,
        grant_date=payload.grant_date,
        work_start_date=payload.work_start_date,
        work_end_date=payload.work_end_date,
        notes=payload.notes,
    )
    db.add(grant)
    db.commit()

    return _grant_to_response(grant)


@router.get("/{client_id}/grants", response_model=list[GrantResponse])
def list_grants(client_id: int, db: Session = Depends(get_db)) -> list[GrantResponse]:
    _require_client(db, client_id)
    grants = db.scalars(
        select(Grant).where(Grant.client_id == client_id).order_by(Grant.grant_id)
    ).all()

    return [
        _grant_to_response(row)
        for row in grants
    ]


@router.put("/{client_id}/grants/{grant_id}", response_model=GrantResponse)
def update_grant(
    client_id: int,
    grant_id: str,
    payload: GrantRequest,
    db: Session = Depends(get_db),
) -> GrantResponse:
    _require_client(db, client_id)
    grant = _require_grant(db, client_id, grant_id)
    if payload.employment_record_id is not None:
        _require_employment_record(db, client_id, payload.employment_record_id)

    grant.employment_record_id = payload.employment_record_id
    grant.employer_name = payload.employer_name
    grant.nominal_amount = payload.nominal_amount
    grant.indexed_amount = payload.indexed_amount
    grant.grant_date = payload.grant_date
    grant.work_start_date = payload.work_start_date
    grant.work_end_date = payload.work_end_date
    grant.notes = payload.notes
    db.commit()
    db.refresh(grant)

    return _grant_to_response(grant)


@router.delete("/{client_id}/grants/{grant_id}")
def delete_grant(client_id: int, grant_id: str, db: Session = Depends(get_db)) -> dict:
    _require_client(db, client_id)
    grant = _require_grant(db, client_id, grant_id)

    db.delete(grant)
    db.commit()
    return {"deleted": True, "grant_id": grant_id}


@router.post("/{client_id}/actual-capitalizations", response_model=ActualCapitalizationResponse)
def create_actual_capitalization(
    client_id: int,
    payload: ActualCapitalizationRequest,
    db: Session = Depends(get_db),
) -> ActualCapitalizationResponse:
    _require_client(db, client_id)

    cap = ActualCapitalization(
        capitalization_id=f"AC-{uuid4().hex}",
        client_id=client_id,
        amount=payload.amount,
        capitalization_date=payload.capitalization_date,
        source_label=payload.source_label,
        notes=payload.notes,
    )
    db.add(cap)
    db.commit()

    return _actual_capitalization_to_response(cap)


@router.get("/{client_id}/actual-capitalizations", response_model=list[ActualCapitalizationResponse])
def list_actual_capitalizations(
    client_id: int,
    db: Session = Depends(get_db),
) -> list[ActualCapitalizationResponse]:
    _require_client(db, client_id)
    capitalizations = db.scalars(
        select(ActualCapitalization)
        .where(ActualCapitalization.client_id == client_id)
        .order_by(ActualCapitalization.capitalization_id)
    ).all()

    return [
        _actual_capitalization_to_response(row)
        for row in capitalizations
    ]


@router.put(
    "/{client_id}/actual-capitalizations/{capitalization_id}",
    response_model=ActualCapitalizationResponse,
)
def update_actual_capitalization(
    client_id: int,
    capitalization_id: str,
    payload: ActualCapitalizationRequest,
    db: Session = Depends(get_db),
) -> ActualCapitalizationResponse:
    _require_client(db, client_id)
    cap = _require_actual_capitalization(db, client_id, capitalization_id)

    cap.amount = payload.amount
    cap.capitalization_date = payload.capitalization_date
    cap.source_label = payload.source_label
    cap.notes = payload.notes
    db.commit()
    db.refresh(cap)

    return _actual_capitalization_to_response(cap)


@router.delete("/{client_id}/actual-capitalizations/{capitalization_id}")
def delete_actual_capitalization(
    client_id: int,
    capitalization_id: str,
    db: Session = Depends(get_db),
) -> dict:
    _require_client(db, client_id)
    cap = _require_actual_capitalization(db, client_id, capitalization_id)

    db.delete(cap)
    db.commit()
    return {"deleted": True, "capitalization_id": capitalization_id}
