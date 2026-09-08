from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.clients_routes import router as clients_router
from app.api.fixation_m07_routes import router as fixation_m07_router
from app.api.fixation_routes import router as fixation_router
from app.api.pension_product_routes import router as pension_product_router
from app.api.m06_conversion_routes import router as m06_conversion_router
from app.api.m09_cashflow_routes import router as m09_cashflow_router
from app.api.m10_comparison_routes import router as m10_comparison_router
from app.api.official_parameter_routes import router as official_parameter_router
from app.db.base import load_all_models

# Register archive FK targets and immutable SQL guards before the first query.
load_all_models()

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
app.include_router(fixation_m07_router)
app.include_router(official_parameter_router)
app.include_router(pension_product_router)
app.include_router(m06_conversion_router)
app.include_router(m09_cashflow_router)
app.include_router(m10_comparison_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
