from fastapi import FastAPI

from app.api.clients_routes import router as clients_router
from app.api.fixation_routes import router as fixation_router

app = FastAPI(title="Retirement Planning V2")

app.include_router(clients_router)
app.include_router(fixation_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
