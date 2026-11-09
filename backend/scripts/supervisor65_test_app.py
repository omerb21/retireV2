"""Local, synthetic-only ASGI entrypoint for Supervisor 65 Chromium acceptance.

Not imported by production. There is no client-asserted identity header.
The actor is assigned only inside the hermetic APP_ENV=test local runner,
after strict localhost/database guards, and only for loopback requests.
"""
from __future__ import annotations

import os
from urllib.parse import urlsplit

from fastapi import Request
from starlette.responses import JSONResponse

db_url = os.environ.get("DATABASE_URL", "").replace(
    "postgresql+psycopg2://", "postgresql://", 1,
)
parts = urlsplit(db_url)
if (os.environ.get("APP_ENV") != "test"
        or parts.hostname not in {"127.0.0.1", "localhost", "::1"}
        or parts.path != "/retire_v2_supervisor41_test"
        or not parts.port):
    raise RuntimeError("SUPERVISOR65_SYNTHETIC_LOOPBACK_DB_ONLY")

from app.main import app  # noqa: E402


@app.middleware("http")
async def synthetic_professional_identity(request: Request, call_next):
    # Neither browser input nor arbitrary headers can select an actor.
    if request.client is None or request.client.host not in {
        "127.0.0.1", "::1", "localhost",
    }:
        return JSONResponse({"code": "SUPERVISOR65_LOOPBACK_ONLY"}, status_code=403)
    request.state.trusted_professional_actor = "supervisor65-synthetic-planner"
    return await call_next(request)
