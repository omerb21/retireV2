"""Isolated public UI preview. Never mounts RETIRE V2's API or accesses its DB."""
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

@app.middleware("http")
async def no_api_access(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"code": "SYNTHETIC_PREVIEW_API_DISABLED"}, status_code=404,
                            headers={"Cache-Control": "no-store"})
    response = await call_next(request)
    response.headers["X-Retire-Preview"] = "synthetic-ui-only"
    response.headers["Cache-Control"] = "no-store"
    return response

@app.get("/healthz/live")
def live():
    return {"status": "ok", "mode": "synthetic_ui_preview"}

@app.get("/")
@app.get("/login")
@app.get("/clients")
def shell():
    return FileResponse(DIST / "index.html")

app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")
