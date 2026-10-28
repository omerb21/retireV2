"""Isolated public UI preview. Never mounts RETIRE V2's API or accesses its DB."""
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from render_synthetic_stage6 import router as synthetic_router
from render_synthetic_workflow import router as workflow_router, initialize as initialize_workflow

DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.include_router(synthetic_router)
app.include_router(workflow_router)

@app.on_event("startup")
def assert_canonical_synthetic_pipeline():
    initialize_workflow()
    from render_synthetic_stage6 import SyntheticInput, estimate
    result = estimate(SyntheticInput(balance="1000000.00", divisor="200"))
    assert result["result"]["result_state"] == "RESULT_READY"
    assert result["result"]["monthly_estimate_gross_ils"] == "5000.00"
    print("STAGE6_SYNTHETIC_CANONICAL_PTE_SMOKE_PASS", flush=True)


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

@app.get("/demo/stage6", response_class=HTMLResponse)
def synthetic_demo():
    return """<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>RETIRE V2 — ניסוי Stage 6</title>
<style>body{font:17px system-ui;max-width:720px;margin:40px auto;padding:16px;color:#1b2a39}
label{display:block;margin:18px 0}input{font:inherit;padding:10px;width:95%;max-width:360px}
button{font:inherit;background:#164b74;color:white;border:0;padding:12px 24px;cursor:pointer}
pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#eef4f7;padding:16px}
small{color:#5a6570}</style></head><body>
<h1>RETIRE V2 — בדיקת מנוע Stage 6</h1>
<p>סביבת ניסוי סינתטית בלבד. החישוב מפעיל את שירותי P1C, PTE ו־P1D האמיתיים,
עם נתוני דמה ואישור מקדם סינתטי. אין גישה לתיקי לקוחות או למסד הייצור.</p>
<form id="calc"><label>יתרה סינתטית בש״ח (שתי ספרות אחרי הנקודה)
<input id="balance" value="1000000.00" inputmode="decimal" required></label>
<label>מקדם קצבה סינתטי (מספר שלם חיובי)
<input id="divisor" value="200" inputmode="numeric" required></label>
<button type="submit">חשב באמצעות המנוע הקנוני</button></form>
<p id="status" role="status"></p><pre id="output" aria-live="polite"></pre>
<small>אומדן ברוטו לא מחייב, ללא מס, זכאות, תמחור מבטח או הצמדה.</small>
<script>
document.getElementById('calc').addEventListener('submit',async(e)=>{
 e.preventDefault();const st=document.getElementById('status'),out=document.getElementById('output');
 st.textContent='מחשב...';out.textContent='';
 try{const r=await fetch('/demo/stage6/estimate',{method:'POST',
 headers:{'Content-Type':'application/json'},body:JSON.stringify({
 balance:document.getElementById('balance').value,
 divisor:document.getElementById('divisor').value})});
 const j=await r.json();if(!r.ok)throw new Error(JSON.stringify(j));
 st.textContent=j.result.result_state==='RESULT_READY'?'החישוב הושלם':'החישוב נחסם';
 out.textContent=JSON.stringify({monthly_estimate_gross_ils:j.result.monthly_estimate_gross_ils,
 result_state:j.result.result_state,blockers:j.result.blockers,
 result_fingerprint:j.result.result_fingerprint,
 pte_source_result_fingerprint:j.result.pte_source_result_fingerprint},null,2);
 }catch(err){st.textContent='החישוב לא הושלם';out.textContent=String(err)}
});</script></body></html>"""
