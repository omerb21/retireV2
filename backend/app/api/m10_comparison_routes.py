"""Legacy stateless comparison execution is sealed; no replacement is exposed."""
from fastapi import APIRouter

router = APIRouter(prefix="/api/clients/{client_id}/m10", tags=["m10-sealed"])
