from __future__ import annotations

from contextlib import asynccontextmanager
import asyncio
import json
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth_routes import router as auth_router
from app.api.canonical_conversion_routes import router as canonical_conversion_router
from app.api.clients_routes import router as clients_router
from app.api.fixation_m07_routes import router as fixation_m07_router
from app.api.fixation_routes import router as fixation_router
from app.api.m06_conversion_routes import router as m06_conversion_router
from app.api.m09_cashflow_routes import router as m09_cashflow_router
from app.api.m10_comparison_routes import router as m10_comparison_router
from app.api.official_parameter_routes import router as official_parameter_router
from app.api.pension_product_routes import router as pension_product_router
from app.api.planning_input_routes import router as planning_input_router
from app.api.professional_source_routes import router as professional_source_router
from app.api.retirement_income_readiness_routes import router as readiness_router
from app.api.scenario_permission_preview_routes import router as scenario_permission_preview_router
from app.api.scenario_draft_routes import router as scenario_draft_router
from app.db.base import load_all_models
from app.db.session import get_session_factory
from app.security.config import AuthConfig
from app.security.middleware import RTDIRSecurityMiddleware
from app.security.rate_limit import RateLimitUnavailable, cleanup_batch
from app.security.transport import NO_STORE, error, is_spa_path
from sqlalchemy import text

load_all_models()
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
EXPECTED_ALEMBIC_HEAD = "e2f8a6c1d405"


def _pointer(location: tuple[object, ...]) -> str:
    if not location:
        return "/"
    parts = list(location)
    if parts and parts[0] == "body":
        parts = parts[1:]
    elif parts and parts[0] == "path":
        parts = ["path", *parts[1:]]
    return "/" + "/".join(str(part).replace("~", "~0").replace("/", "~1") for part in parts)


def _cleanup_once(app: FastAPI) -> bool:
    db = get_session_factory()()
    try:
        heads = db.execute(text("SELECT version_num FROM alembic_version")).scalars().all()
        if heads != [EXPECTED_ALEMBIC_HEAD]:
            raise RateLimitUnavailable("database migration head mismatch")
        while cleanup_batch(db) == 64:
            pass
        app.state.rate_limiter_ready = True
        return True
    except RateLimitUnavailable:
        app.state.rate_limiter_ready = False
        return False
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = None
    if app.state.auth_config.production:
        await asyncio.to_thread(_cleanup_once, app)

        async def scheduled_cleanup():
            while True:
                await asyncio.sleep(900)
                await asyncio.to_thread(_cleanup_once, app)

        task = asyncio.create_task(scheduled_cleanup())
    yield
    if task:
        task.cancel()


def create_app(config: AuthConfig | None = None) -> FastAPI:
    config = config or AuthConfig.from_env()
    app = FastAPI(
        title="Retirement Planning V2",
        docs_url=None if config.production else "/docs",
        redoc_url=None if config.production else "/redoc",
        openapi_url=None if config.production else "/openapi.json",
        lifespan=lifespan,
    )
    app.state.auth_config = config
    app.state.rate_limiter_ready = not config.production
    app.add_middleware(RTDIRSecurityMiddleware, config=config)
    if not config.production:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://127.0.0.1:5173"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    for router in (
        auth_router, clients_router, professional_source_router, planning_input_router,
        readiness_router, fixation_router, fixation_m07_router, official_parameter_router,
        pension_product_router, canonical_conversion_router, m06_conversion_router,
        m09_cashflow_router, m10_comparison_router, scenario_permission_preview_router, scenario_draft_router,
    ):
        app.include_router(router)

    @app.exception_handler(RequestValidationError)
    async def request_validation(request: Request, exc: RequestValidationError):
        if not config.production:
            return await request_validation_exception_handler(request, exc)
        parts = [part for part in request.url.path.split("/") if part]
        if (
            request.method == "POST"
            and len(parts) == 5
            and parts[0] == "api"
            and parts[1] == "clients"
            and parts[3:] == ["scenario-conversions", "permission-preview"]
        ):
            return error(
                request, 422, "SCENARIO_PERMISSION_REQUEST_INVALID",
                [_pointer(tuple(item["loc"])) for item in exc.errors()],
            )
        return error(request, 422, "REQUEST_SCHEMA_INVALID", [_pointer(tuple(item["loc"])) for item in exc.errors()])

    @app.exception_handler(Exception)
    async def unexpected_failure(request: Request, exc: Exception):
        if not config.production:
            raise exc
        return error(request, 500, "INTERNAL_ERROR")

    @app.api_route("/health", methods=["GET", "HEAD"])
    def health():
        return {"status": "ok"}

    @app.api_route("/healthz/live", methods=["GET", "HEAD"])
    def live():
        return {"status": "ok"}

    @app.api_route("/healthz/ready", methods=["GET", "HEAD"])
    def ready():
        if config.production and not app.state.rate_limiter_ready:
            return JSONResponse(status_code=503, content={"status": "unavailable"})
        return {"status": "ready"}

    if config.production:
        index = FRONTEND_DIST / "index.html"
        manifest_path = FRONTEND_DIST / ".vite" / "manifest.json"

        def manifest_files() -> set[str]:
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                return {
                    Path(value).name
                    for entry in manifest.values() if isinstance(entry, dict)
                    for value in [entry.get("file"), *(entry.get("css") or []), *(entry.get("assets") or [])]
                    if isinstance(value, str) and value.startswith("assets/")
                }
            except (OSError, ValueError, TypeError):
                return set()

        def shell():
            if not index.is_file():
                return JSONResponse(status_code=503, headers=NO_STORE, content={"status": "unavailable"})
            return FileResponse(index, headers=NO_STORE)

        for path in ["/", "/login", "/clients", "/clients/new", "/fixation/input", "/fixation/result", "/fixation/history"]:
            app.add_api_route(path, shell, methods=["GET", "HEAD"], include_in_schema=False)

        @app.api_route("/assets/{filename}", methods=["GET", "HEAD"], include_in_schema=False)
        def asset(request: Request, filename: str):
            if filename not in manifest_files() or filename.startswith(".") or filename.endswith(".map"):
                return error(request, 404, "ROUTE_NOT_FOUND")
            return FileResponse(FRONTEND_DIST / "assets" / filename, headers={"Cache-Control": "public, max-age=31536000, immutable"})

        @app.api_route("/{spa_path:path}", methods=["GET", "HEAD"], include_in_schema=False)
        def spa(request: Request, spa_path: str):
            if spa_path.startswith(("api/", ".")) or ".." in spa_path:
                return error(request, 404, "ROUTE_NOT_FOUND")
            if not is_spa_path("/" + spa_path):
                return error(request, 404, "ROUTE_NOT_FOUND")
            return shell()
    return app


app = create_app()
