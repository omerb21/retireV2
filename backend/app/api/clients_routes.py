from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.actual_capitalization import ActualCapitalization
from app.models.client import Client
from app.models.client_profile import ClientProfile
from app.models.employment_record import EmploymentRecord
from app.models.grant import Grant

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


class ProfileUpsertRequest(BaseModel):
    birth_date: date | None = None
    gender: str | None = None
    notes: str | None = None


class ProfileResponse(BaseModel):
    client_profile_id: str
    client_id: int
    birth_date: date | None
    gender: str | None
    notes: str | None


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


@router.post("", response_model=ClientResponse)
def create_client(payload: ClientCreateRequest, db: Session = Depends(get_db)) -> ClientResponse:
    client = Client(
        display_name=payload.full_name,
        id_number=payload.id_number,
        birth_date=payload.birth_date,
        status=None,
    )
    db.add(client)
    db.commit()
    db.refresh(client)

    return ClientResponse(
        client_id=client.client_id,
        full_name=client.display_name,
        id_number=client.id_number,
        birth_date=client.birth_date,
    )


@router.get("/{client_id}", response_model=ClientResponse)
def get_client(client_id: int, db: Session = Depends(get_db)) -> ClientResponse:
    client = _require_client(db, client_id)
    return ClientResponse(
        client_id=client_id,
        full_name=client.display_name,
        id_number=client.id_number,
        birth_date=client.birth_date,
    )


@router.put("/{client_id}/profile")
def put_client_profile(
    client_id: int,
    payload: ProfileUpsertRequest,
    db: Session = Depends(get_db),
) -> dict:
    _require_client(db, client_id)
    client_key = client_id

    profile = db.scalar(select(ClientProfile).where(ClientProfile.client_id == client_key))
    if profile is None:
        profile = ClientProfile(
            client_profile_id=f"CP-{client_id}",
            client_id=client_key,
            birth_date=payload.birth_date,
            gender=payload.gender,
            notes=payload.notes,
        )
        db.add(profile)
    else:
        profile.birth_date = payload.birth_date
        profile.gender = payload.gender
        profile.notes = payload.notes

    if payload.birth_date is not None:
        client = db.get(Client, client_id)
        if client is not None:
            client.birth_date = payload.birth_date

    db.commit()
    return {
        "profile": ProfileResponse(
            client_profile_id=profile.client_profile_id,
            client_id=client_id,
            birth_date=profile.birth_date,
            gender=profile.gender,
            notes=profile.notes,
        ).model_dump(mode="json")
    }


@router.get("/{client_id}/profile")
def get_client_profile(client_id: int, db: Session = Depends(get_db)) -> dict:
    _require_client(db, client_id)
    profile = db.scalar(select(ClientProfile).where(ClientProfile.client_id == client_id))
    if profile is None:
        return {"profile": None}

    return {
        "profile": ProfileResponse(
            client_profile_id=profile.client_profile_id,
            client_id=client_id,
            birth_date=profile.birth_date,
            gender=profile.gender,
            notes=profile.notes,
        ).model_dump(mode="json")
    }


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

    return EmploymentRecordResponse(
        employment_record_id=record.employment_record_id,
        client_id=client_id,
        employer_name=record.employer_name,
        work_start_date=record.work_start_date,
        work_end_date=record.work_end_date,
        is_current=record.is_current,
        notes=record.notes,
    )


@router.get("/{client_id}/employment-records", response_model=list[EmploymentRecordResponse])
def list_employment_records(client_id: int, db: Session = Depends(get_db)) -> list[EmploymentRecordResponse]:
    _require_client(db, client_id)
    records = db.scalars(
        select(EmploymentRecord)
        .where(EmploymentRecord.client_id == client_id)
        .order_by(EmploymentRecord.employment_record_id)
    ).all()
    return [
        EmploymentRecordResponse(
            employment_record_id=row.employment_record_id,
            client_id=client_id,
            employer_name=row.employer_name,
            work_start_date=row.work_start_date,
            work_end_date=row.work_end_date,
            is_current=row.is_current,
            notes=row.notes,
        )
        for row in records
    ]


@router.post("/{client_id}/grants", response_model=GrantResponse)
def create_grant(client_id: int, payload: GrantRequest, db: Session = Depends(get_db)) -> GrantResponse:
    _require_client(db, client_id)

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

    return GrantResponse(
        grant_id=grant.grant_id,
        client_id=client_id,
        employment_record_id=grant.employment_record_id,
        employer_name=grant.employer_name,
        nominal_amount=grant.nominal_amount,
        indexed_amount=grant.indexed_amount,
        grant_date=grant.grant_date,
        work_start_date=grant.work_start_date,
        work_end_date=grant.work_end_date,
        notes=grant.notes,
    )


@router.get("/{client_id}/grants", response_model=list[GrantResponse])
def list_grants(client_id: int, db: Session = Depends(get_db)) -> list[GrantResponse]:
    _require_client(db, client_id)
    grants = db.scalars(
        select(Grant).where(Grant.client_id == client_id).order_by(Grant.grant_id)
    ).all()

    return [
        GrantResponse(
            grant_id=row.grant_id,
            client_id=client_id,
            employment_record_id=row.employment_record_id,
            employer_name=row.employer_name,
            nominal_amount=row.nominal_amount,
            indexed_amount=row.indexed_amount,
            grant_date=row.grant_date,
            work_start_date=row.work_start_date,
            work_end_date=row.work_end_date,
            notes=row.notes,
        )
        for row in grants
    ]


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

    return ActualCapitalizationResponse(
        capitalization_id=cap.capitalization_id,
        client_id=client_id,
        amount=cap.amount,
        capitalization_date=cap.capitalization_date,
        source_label=cap.source_label,
        notes=cap.notes,
    )


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
        ActualCapitalizationResponse(
            capitalization_id=row.capitalization_id,
            client_id=client_id,
            amount=row.amount,
            capitalization_date=row.capitalization_date,
            source_label=row.source_label,
            notes=row.notes,
        )
        for row in capitalizations
    ]
