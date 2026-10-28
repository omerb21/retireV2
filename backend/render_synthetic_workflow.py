"""Disposable PostgreSQL-backed synthetic workflow. NOT the production Stage 6 admission writer."""
from __future__ import annotations
import os
from uuid import uuid4, UUID
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from render_synthetic_stage6 import SyntheticInput, estimate

router = APIRouter(prefix="/demo/stage6/workflow", tags=["synthetic"])
_engine: Engine | None = None

def initialize() -> None:
    global _engine
    url = os.environ.get("SYNTHETIC_DEMO_DATABASE_URL", "")
    if "retire_v2_synthetic_demo" not in url or "host=/var/run/postgresql" not in url:
        raise RuntimeError("SYNTHETIC_DEMO_DATABASE_URL must be the isolated Unix-socket DB")
    _engine = create_engine(url, pool_pre_ping=True)
    with _engine.begin() as db:
        db.execute(text("""CREATE TABLE IF NOT EXISTS synthetic_workflow (
            scenario_id VARCHAR(36) PRIMARY KEY,
            version INTEGER NOT NULL CHECK (version BETWEEN 1 AND 3),
            balance VARCHAR(32) NOT NULL,
            pension_start_date VARCHAR(10),
            survivor_option VARCHAR(32),
            divisor VARCHAR(8),
            state VARCHAR(32) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP)"""))

def database() -> Engine:
    if _engine is None:
        raise HTTPException(503, "SYNTHETIC_DATABASE_UNAVAILABLE")
    return _engine

class Start(BaseModel):
    model_config = ConfigDict(extra="forbid")
    balance: str = Field(pattern=r"^(?:0|[1-9][0-9]{0,11})\.[0-9]{2}$")

class Election(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = 1
    pension_start_date: str = "2027-09-30"
    survivor_option: str = "synthetic-standard"

class Factor(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = 2
    divisor: str = Field(pattern=r"^[1-9][0-9]{0,4}$")
    acknowledgement: bool

def validated_id(value: str) -> str:
    try:
        return str(UUID(value, version=4))
    except (ValueError, AttributeError) as exc:
        raise HTTPException(404, "SYNTHETIC_SCENARIO_NOT_FOUND") from exc

@router.post("/start")
def start(payload: Start):
    # Reuse the canonical validation, without executing or recording an approval.
    from decimal import Decimal
    if Decimal(payload.balance) <= 0:
        raise HTTPException(422, "SYNTHETIC_BALANCE_INVALID")
    sid = str(uuid4())
    with database().begin() as db:
        db.execute(text("""INSERT INTO synthetic_workflow
            (scenario_id, version, balance, state)
            VALUES (:id, 1, :balance, 'CREATED')"""),
            {"id": sid, "balance": payload.balance})
    return {"scenario_id": sid, "version": 1, "state": "CREATED", "synthetic_only": True}

@router.put("/{scenario_id}/election")
def election(scenario_id: str, payload: Election):
    sid = validated_id(scenario_id)
    if (payload.expected_version != 1 or
        payload.pension_start_date != "2027-09-30" or
        payload.survivor_option != "synthetic-standard"):
        raise HTTPException(422, "SYNTHETIC_FIXED_ELECTION_ONLY")
    with database().begin() as db:
        r = db.execute(text("""UPDATE synthetic_workflow
            SET version=2, state='ELECTION_SAVED', pension_start_date=:date,
                survivor_option=:survivor, divisor=NULL
            WHERE scenario_id=:id AND version=:expected"""),
            {"date": payload.pension_start_date, "survivor": payload.survivor_option,
             "id": sid, "expected": payload.expected_version})
        if r.rowcount != 1:
            raise HTTPException(409, "SYNTHETIC_VERSION_CONFLICT")
    return {"scenario_id": sid, "version": 2, "state": "ELECTION_SAVED", "synthetic_only": True}

@router.post("/{scenario_id}/factor")
def factor(scenario_id: str, payload: Factor):
    sid = validated_id(scenario_id)
    if not payload.acknowledgement or payload.expected_version != 2:
        raise HTTPException(422, "SYNTHETIC_ACK_REQUIRED")
    with database().begin() as db:
        r = db.execute(text("""UPDATE synthetic_workflow
            SET version=3, state='FACTOR_ACKNOWLEDGED', divisor=:divisor
            WHERE scenario_id=:id AND version=:expected"""),
            {"divisor": payload.divisor, "id": sid, "expected": payload.expected_version})
        if r.rowcount != 1:
            raise HTTPException(409, "SYNTHETIC_VERSION_CONFLICT")
    return {"scenario_id": sid, "version": 3, "state": "FACTOR_ACKNOWLEDGED",
            "synthetic_only": True, "is_professional_admission": False}

@router.get("/{scenario_id}/estimate")
def read_estimate(scenario_id: str):
    sid = validated_id(scenario_id)
    with database().connect() as db:
        row = db.execute(text("""SELECT version,balance,divisor,state
            FROM synthetic_workflow WHERE scenario_id=:id"""), {"id": sid}).mappings().first()
    if row is None:
        raise HTTPException(404, "SYNTHETIC_SCENARIO_NOT_FOUND")
    if row["version"] != 3 or row["state"] != "FACTOR_ACKNOWLEDGED":
        raise HTTPException(409, "SYNTHETIC_FACTOR_NOT_ACKNOWLEDGED")
    calculated = estimate(SyntheticInput(balance=row["balance"], divisor=row["divisor"]))
    return {"scenario_id": sid, "version": row["version"], "synthetic_only": True,
            "is_professional_admission": False, "calculation": calculated}
