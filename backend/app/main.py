from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.clients_routes import router as clients_router
from app.api.fixation_routes import router as fixation_router
from app.api.official_parameter_routes import router as official_parameter_router

app = FastAPI(title="Retirement Planning V2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(clients_router)
app.include_router(fixation_router)
app.include_router(official_parameter_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
