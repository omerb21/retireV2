"""Historical persisted M09 evidence only. No current planning execution."""
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.client import Client
from app.models.m09_cashflow import M09ResolvedComponentInventory, M09ScenarioRun, M09MonthlyResult
from app.models.m09_scenario_subject import M09ScenarioSubject, M09ScenarioAdjustment, M09SubjectRun, M09SubjectMonthlyResult
from app.services.professional_source_snapshot_service import serialize, record


def archive_marker(response: Response):
    response.headers["X-Professional-Authority"] = "archive-only"


router = APIRouter(prefix="/api/clients/{client_id}/m09", tags=["m09-archive-only"], dependencies=[Depends(archive_marker)])


def archived(db, client_id, model, **identity):
    if db.get(Client, client_id) is None:
        raise HTTPException(404, "לקוח לא נמצא")
    query = select(model).where(model.client_id == client_id)
    for key, value in identity.items():
        query = query.where(getattr(model, key) == value)
    rows = db.scalars(query.order_by(*model.__table__.primary_key.columns)).all()
    if identity and not rows:
        raise HTTPException(404, "רשומת ארכיון לא נמצאה")
    return [serialize(record(row)) for row in rows]


@router.get("/inventories/{inventory_id}")
def inventory(client_id: int, inventory_id: str, db: Session = Depends(get_db)):
    return {"authority": "archive_only", "record": archived(db, client_id, M09ResolvedComponentInventory, inventory_id=inventory_id)[0]}


@router.get("/runs")
def history(client_id: int, db: Session = Depends(get_db)):
    return {"authority": "archive_only", "records": archived(db, client_id, M09ScenarioRun)}


@router.get("/runs/{run_id}")
def result(client_id: int, run_id: str, db: Session = Depends(get_db)):
    run = archived(db, client_id, M09ScenarioRun, run_id=run_id)[0]
    rows = db.scalars(select(M09MonthlyResult).where(M09MonthlyResult.run_id == run_id).order_by(M09MonthlyResult.month)).all()
    return {"authority": "archive_only", "record": run, "monthly_results": serialize([record(r) for r in rows])}


@router.get("/subjects")
def subjects(client_id: int, db: Session = Depends(get_db)):
    return {"authority": "archive_only", "records": archived(db, client_id, M09ScenarioSubject)}


@router.get("/subjects/{subject_id}")
def subject(client_id: int, subject_id: str, db: Session = Depends(get_db)):
    row = archived(db, client_id, M09ScenarioSubject, scenario_subject_id=subject_id)[0]
    adjustments = db.scalars(select(M09ScenarioAdjustment).where(M09ScenarioAdjustment.scenario_subject_id == subject_id)).all()
    return {"authority": "archive_only", "record": row, "adjustments": serialize([record(r) for r in adjustments])}


@router.get("/subjects/{subject_id}/runs")
def subject_runs(client_id: int, subject_id: str, db: Session = Depends(get_db)):
    archived(db, client_id, M09ScenarioSubject, scenario_subject_id=subject_id)
    rows = db.scalars(select(M09SubjectRun).where(M09SubjectRun.client_id == client_id, M09SubjectRun.scenario_subject_id == subject_id).order_by(M09SubjectRun.run_sequence)).all()
    return {"authority": "archive_only", "records": serialize([record(r) for r in rows])}


@router.get("/subjects/{subject_id}/runs/{run_id}")
def subject_run(client_id: int, subject_id: str, run_id: str, db: Session = Depends(get_db)):
    run = archived(db, client_id, M09SubjectRun, scenario_subject_id=subject_id, run_id=run_id)[0]
    rows = db.scalars(select(M09SubjectMonthlyResult).where(M09SubjectMonthlyResult.run_id == run_id).order_by(M09SubjectMonthlyResult.month)).all()
    return {"authority": "archive_only", "record": run, "monthly_results": serialize([record(r) for r in rows])}
