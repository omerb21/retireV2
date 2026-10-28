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
    from fastapi import HTTPException
    from render_synthetic_workflow import Start, Election, Factor, start, election, factor, read_estimate
    created = start(Start(balance="1000000.00"))
    sid = created["scenario_id"]
    try:
        read_estimate(sid)
    except HTTPException as exc:
        assert exc.status_code == 409
    else:
        raise AssertionError("Synthetic estimate must be blocked before factor acknowledgment")
    updated = election(sid, Election(expected_version=1))
    assert updated["version"] == 2
    acknowledged = factor(sid, Factor(expected_version=2, divisor="200", acknowledgement=True))
    assert acknowledged["version"] == 3
    result_from_db = read_estimate(sid)
    assert result_from_db["calculation"]["result"]["monthly_estimate_gross_ils"] == "5000.00"
    try:
        factor(sid, Factor(expected_version=2, divisor="200", acknowledgement=True))
    except HTTPException as exc:
        assert exc.status_code == 409
    else:
        raise AssertionError("Synthetic workflow must reject stale factor approval")
    print("STAGE6_SYNTHETIC_POSTGRES_WORKFLOW_SMOKE_PASS", flush=True)
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

@app.get("/demo/stage6/workflow", response_class=HTMLResponse)
def workflow_demo():
    return """<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RETIRE V2 — תרחיש סינתטי ב־PostgreSQL</title>
<style>body{font:17px system-ui;max-width:760px;margin:32px auto;padding:16px;color:#172b3d}
section{border:1px solid #b9c8d2;border-radius:8px;padding:18px;margin:16px 0}
label{display:block;margin:12px 0}input{font:inherit;padding:9px}
button{font:inherit;background:#12517b;color:white;border:0;padding:10px 18px;cursor:pointer}
button:disabled{opacity:.5;cursor:default}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#eef3f6;padding:15px}</style>
</head><body><h1>תרחיש Stage 6 סינתטי — PostgreSQL</h1>
<p>בדיקת זרימת שמירת תרחיש, בחירת קצבה, תיעוד מקדם והפקת אומדן.
כל הנתונים בדויים, המסד נפרד וזמני. זהו מנגנון ניסוי ולא תהליך האישור המקצועי של סביבת הייצור.</p>
<section><h2>1. יצירת תרחיש בדיקה</h2><label>יתרה סינתטית בש״ח
<input id="balance" value="1000000.00"></label>
<button id="start">צור תרחיש</button></section>
<section><h2>2. שמירת בחירת קצבה</h2><p>מועד קצבה קבוע: 30.09.2027, מסלול שאירים סינתטי.</p>
<button id="election" disabled>שמור בחירה וגרסת תרחיש</button></section>
<section><h2>3. תיעוד מקדם סינתטי</h2>
<label>מקדם קצבה <input id="factor" value="200"></label>
<label><input id="ack" type="checkbox"> אני מאשר שמדובר בנתון בדיקה בדוי בלבד</label>
<button id="admission" disabled>תעד מקדם בגרסה הנוכחית</button></section>
<section><h2>4. בדיקת אומדן</h2><button id="calculate" disabled>הפק אומדן באמצעות PTE הקנוני</button>
<p id="status" role="status"></p><pre id="result" aria-live="polite"></pre></section>
<script>
let id=null,version=0;
const $=x=>document.getElementById(x);
function enable(){ $('election').disabled=version!==1;$('admission').disabled=version!==2;$('calculate').disabled=version!==3 }
async function call(path,method,body) {
const options={method,headers:{'Content-Type':'application/json'}};
if(body)options.body=JSON.stringify(body);
const response=await fetch(path,options);const data=await response.json();
if(!response.ok)throw Error(JSON.stringify(data));return data;
}
async function act(task){
try { $('status').textContent='מבצע...';const out=await task();$('status').textContent='הפעולה הושלמה';
$('result').textContent=JSON.stringify(out,null,2); }
catch(err){$('status').textContent='הפעולה נדחתה';$('result').textContent=String(err)}
enable();
}
$('start').onclick=()=>act(async()=>{const r=await call('/demo/stage6/workflow/start','POST',{balance:$('balance').value});id=r.scenario_id;version=r.version;return r});
$('election').onclick=()=>act(async()=>{const r=await call('/demo/stage6/workflow/'+encodeURIComponent(id)+'/election','PUT',{
expected_version:version,pension_start_date:'2027-09-30',survivor_option:'synthetic-standard'});version=r.version;return r});
$('admission').onclick=()=>act(async()=>{const r=await call('/demo/stage6/workflow/'+encodeURIComponent(id)+'/factor','POST',{
expected_version:version,divisor:$('factor').value,acknowledgement:$('ack').checked});version=r.version;return r});
$('calculate').onclick=()=>act(async()=>{const r=await call('/demo/stage6/workflow/'+encodeURIComponent(id)+'/estimate','GET');
return {monthly_estimate_gross_ils:r.calculation.result.monthly_estimate_gross_ils,
result_state:r.calculation.result.result_state,version:r.version,
result_fingerprint:r.calculation.result.result_fingerprint,
is_professional_admission:r.is_professional_admission};});
</script></body></html>"""
