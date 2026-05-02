Below is the second targeted discovery pass. Evidence only; no code changes made.

**1. exemption_caps.py**
File: `C:\Users\omer\OneDrive\AI PROJECTS\WINSURDF\dev\retire\app\services\rights_fixation\exemption_caps.py`

Full cap table:
```python
ANNUAL_CAPS = {
    2028: 9430,
    2027: 9430,
    2026: 9430,
    2025: 9430,
    2024: 9430,
    2023: 9120,
    2022: 8660,
    2021: 8460,
    2020: 8510,
    2019: 8480,
    2018: 8380,
    2017: 8360,
    2016: 8380,
    2015: 8460,
    2014: 8470,
    2013: 8310,
    2012: 8190,
}
```

Full exemption percentage table:
```python
EXEMPTION_PERCENTAGES = {
    2028: 0.67,
    2027: 0.625,
    2026: 0.575,
    2025: 0.57,
    2024: 0.52,
    2023: 0.52,
    2022: 0.52,
    2021: 0.52,
    2020: 0.52,
    2019: 0.49,
    2018: 0.49,
    2017: 0.49,
    2016: 0.49,
    2015: 0.435,
    2014: 0.435,
    2013: 0.435,
    2012: 0.435,
}
```

Unknown years and years `>= 2028`:
```python
def get_monthly_cap(year: int) -> float:
    if year >= 2028:
        return ANNUAL_CAPS.get(2028, 9430)
    return ANNUAL_CAPS.get(year, ANNUAL_CAPS[2025])


def get_exemption_percentage(year: int) -> float:
    if year >= 2028:
        return EXEMPTION_PERCENTAGES.get(2028, 0.67)
    return EXEMPTION_PERCENTAGES.get(year, EXEMPTION_PERCENTAGES[2025])
```

Formula:
```python
MULTIPLIER = 180

def calc_exempt_capital(year: int) -> float:
    return get_monthly_cap(year) * MULTIPLIER * get_exemption_percentage(year)
```

Finding: unknown years below 2028 fall back to 2025 values. Years `>= 2028` use 2028 cap and 2028 percentage.

**2. work_ratio.py**
File: `C:\Users\omer\OneDrive\AI PROJECTS\WINSURDF\dev\retire\app\services\rights_fixation\work_ratio.py`  
Function: `work_ratio_within_last_32y`

Date inputs used:
```python
if isinstance(start_date, str):
    start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
if isinstance(end_date, str):
    end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
if isinstance(elig_date, str):
    elig_date = datetime.strptime(elig_date, "%Y-%m-%d").date()
if birth_date and isinstance(birth_date, str):
    birth_date = datetime.strptime(birth_date, "%Y-%m-%d").date()
```

Retirement date is calculated but not applied to `effective_end_date` in this implementation:
```python
retirement_date = None
if birth_date and gender:
    try:
        from app.services.retirement_age_service import get_retirement_date
        retirement_date = get_retirement_date(birth_date, gender)
```

```python
# הגבלת תאריך סיום העבודה לגיל הפרישה
effective_end_date = end_date
```

32-year window:
```python
limit_start = elig_date - timedelta(days=int(365.25 * 32))
```

Ratio implementation:
```python
total_days = (end_date - start_date).days
if total_days <= 0:
    return 0.0

overlap_start = max(start_date, limit_start)
overlap_end = min(effective_end_date, elig_date)
overlap_days = max((overlap_end - overlap_start).days, 0)

ratio = overlap_days / total_days if total_days > 0 else 0
ratio = min(max(ratio, 0), 1)
return ratio
```

Invalid dates/errors:
```python
except Exception as e:
    logger.error(...)
    return 0.0
```

Findings:
- Uses `start_date`, `end_date`, `elig_date`.
- Optional `birth_date` and `gender` calculate `retirement_date`, but current code leaves `effective_end_date = end_date`.
- Ratio is capped to `[0, 1]`.
- Partial periods are counted by days, not months.
- 32 years is approximated as `int(365.25 * 32)` days.
- Invalid dates return `0.0`.

Related duplicate implementation:
`C:\Users\omer\OneDrive\AI PROJECTS\WINSURDF\dev\retire\app\services\indexation_service.py`, function `IndexationService.work_ratio_within_last_32y`, does cap to retirement date:
```python
effective_end_date = end_date
if retirement_date and end_date > retirement_date:
    effective_end_date = retirement_date
```
This is separate from the rights-fixation module.

**3. eligibility.py and retirement age**
File: `C:\Users\omer\OneDrive\AI PROJECTS\WINSURDF\dev\retire\app\services\rights_fixation\eligibility.py`  
Function: `calculate_eligibility_age`

```python
def calculate_eligibility_age(
    birth_date: date, gender: str, pension_start: date
) -> date:
    from app.services.retirement_age_service import get_retirement_date

    legal_retirement_date = get_retirement_date(birth_date, gender)
    return max(legal_retirement_date, pension_start)
```

Related retirement age file:
`C:\Users\omer\OneDrive\AI PROJECTS\WINSURDF\dev\retire\app\services\retirement_age_service.py`

Male retirement:
```python
DEFAULT_MALE_RETIREMENT_AGE = 67
```

`get_retirement_date`:
```python
def get_retirement_date(birth_date: date, gender: str) -> date:
    result = calculate_retirement_age(birth_date, gender)
    return result["retirement_date"]
```

Gender handling:
```python
gender_normalized = (gender or "").strip().lower()
is_male = gender_normalized in {"male", "m", "זכר"}

if is_male:
    age_years = settings.get("male_retirement_age", DEFAULT_MALE_RETIREMENT_AGE)
    age_months = 0
    retirement_date = birth_date + relativedelta(years=age_years)
    source = "settings"
else:
    if settings.get("use_legal_table_for_women", True):
        age_data = get_female_retirement_age_from_table(birth_date)
        age_years = age_data["years"]
        age_months = age_data["months"]
        retirement_date = birth_date + relativedelta(
            years=age_years, months=age_months
        )
        source = "legal_table"
```

Legacy eligibility function:
```python
def calc_eligibility_date(birthdate: date, gender: str) -> date:
    gender_normalized = (gender or "").strip().lower()
    is_female = gender_normalized in {"female", "f", "נקבה"}
    years = 62 if is_female else DEFAULT_MALE_RETIREMENT_AGE
    return birthdate + relativedelta(years=years)
```

API eligibility validation:
File: `C:\Users\omer\OneDrive\AI PROJECTS\WINSURDF\dev\retire\app\routers\rights_fixation.py`  
Function: `calculate_rights_fixation`

```python
eligibility_date = calc_eligibility_date(
    client.birth_date, client.gender
)

today = date.today()
age_condition_ok = today >= eligibility_date
pension_condition_ok = (
    pension_start_date is not None and today >= pension_start_date
)

if not (age_condition_ok and pension_condition_ok):
    response.status_code = 409
    return {
        "ok": False,
        "reasons": reasons,
        "eligibility_date": (
            eligibility_date.isoformat() if eligibility_date else None
        ),
        "age_condition_ok": age_condition_ok,
        "pension_condition_ok": pension_condition_ok,
    }
```

Effective calculation date:
```python
effective_eligibility_date = eligibility_date
if (
    pension_start_date
    and effective_eligibility_date
    and pension_start_date > effective_eligibility_date
):
    effective_eligibility_date = pension_start_date
```

Findings:
- `eligibility.py` calculates `max(legal_retirement_date, pension_start)`.
- Main API path uses `calc_eligibility_date`, not `calculate_eligibility_age`, for client-id branch.
- `calc_eligibility_date` uses simplified female age `62`, male `67`; it does not use the dynamic female legal table.
- API validates eligibility by current date and pension start date before calculating.
- Internal flow `calculate_and_save_fixation_for_client` does not enforce current-date eligibility.

**4. indexation.py**
File: `C:\Users\omer\OneDrive\AI PROJECTS\WINSURDF\dev\retire\app\services\rights_fixation\indexation.py`  
Function: `calculate_adjusted_amount`

CPI source:
```python
CBS_CPI_API = "https://api.cbs.gov.il/index/data/calculator/120010"
```

Date normalization:
```python
if isinstance(grant_date, date):
    grant_date_str = grant_date.isoformat()
else:
    grant_date_str = str(grant_date)

if to_date and isinstance(to_date, date):
    to_date_str = to_date.isoformat()
else:
    to_date_str = (
        str(to_date) if to_date else datetime.today().date().isoformat()
    )
```

Date validation and future start-date behavior:
```python
from_date = datetime.strptime(grant_date_str, "%Y-%m-%d").date()
to_date_parsed = datetime.strptime(to_date_str, "%Y-%m-%d").date()

if from_date > to_date_parsed:
    return float(amount)
```

API call:
```python
params = {
    "value": amount,
    "date": grant_date_str,
    "toDate": to_date_str,
    "format": "json",
    "download": "false",
    "lang": "he",
}

response = requests.get(CBS_CPI_API, params=params, timeout=10)
response.raise_for_status()
data = response.json()
```

Response parsing and rounding:
```python
answer = data.get("answer")
if not answer:
    return None

to_value = answer.get("to_value")
if to_value is None:
    return None

result = round(float(to_value), 2)
return result
```

Failure behavior:
```python
except ValueError as e:
    logger.error(...)
    return None
```

```python
except Exception as e:
    logger.error(...)
    return None
```

Findings:
- CPI source is CBS API endpoint `https://api.cbs.gov.il/index/data/calculator/120010`.
- On API failure, missing `answer`, missing `to_value`, invalid date, or exception: returns `None`.
- If `grant_date > to_date`: returns nominal `float(amount)`.
- Date granularity passed to API is exact `YYYY-MM-DD`.
- Whether CBS internally indexes by month or exact date is unclear from code.
- Rounding is `round(float(to_value), 2)`.
- In grant calculation, `None` from this function falls back to nominal amount in `grant_impact.py`:
```python
if indexed_full is None:
    indexed_full = float(grant["grant_amount"])
```

**5. Real capitalizations vs scenario commutations**
Actual commutation model:
File: `C:\Users\omer\OneDrive\AI PROJECTS\WINSURDF\dev\retire\app\models\commutation.py`  
Object: `Commutation`

```python
class Commutation(Base):
    __tablename__ = "commutation"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pension_id = Column(
        Integer, ForeignKey("pension.id", ondelete="CASCADE"), nullable=False
    )
    commutation_date = Column(Date, nullable=True)
    commutation_amount = Column(Float, nullable=True)
    commutation_ratio = Column(Float, nullable=True)
    impact_on_exemption = Column(Float, nullable=True)
```

Serialization:
```python
return {
    "id": self.id,
    "pension_id": self.pension_id,
    "commutation_date": (
        self.commutation_date.isoformat() if self.commutation_date else None
    ),
    "commutation_amount": self.commutation_amount,
    "commutation_ratio": self.commutation_ratio,
    "impact_on_exemption": self.impact_on_exemption,
}
```

Saved fixation usage field:
File: `C:\Users\omer\OneDrive\AI PROJECTS\WINSURDF\dev\retire\app\models\fixation_result.py`
```python
used_commutation = Column(Float, nullable=False, default=0.0)
```

Scenario commutation assets:
File: `C:\Users\omer\OneDrive\AI PROJECTS\WINSURDF\dev\retire\app\models\capital_asset.py`
```python
remarks = Column(String(500), nullable=True)
conversion_source = Column(Text, nullable=True)
tax_treatment = Column(
    String(20), nullable=False, default="taxable", server_default="taxable"
)
```

Scenario commutation extraction:
File: `C:\Users\omer\OneDrive\AI PROJECTS\WINSURDF\dev\retire\app\services\retirement\services\commutation_exemption_service.py`  
Function: `_load_scenario_commutations`

```python
assets: List[CapitalAsset] = (
    self.db.query(CapitalAsset)
    .filter(
        CapitalAsset.client_id == self.client_id,
        CapitalAsset.conversion_source.isnot(None),
        CapitalAsset.conversion_source.like(
            '%"source": "scenario_conversion"%'
        ),
        CapitalAsset.remarks.isnot(None),
        CapitalAsset.remarks.like("%COMMUTATION:%"),
        CapitalAsset.tax_treatment == "taxable",
    )
    .all()
)
```

Scenario commutation amount extraction:
```python
if asset.remarks:
    match = re.search(r"amount=([\d.]+)", asset.remarks)
    if match:
        amount = float(match.group(1))

if amount <= 0:
    if asset.current_value is not None:
        amount = float(asset.current_value)
    elif asset.monthly_income is not None:
        amount = float(asset.monthly_income)
```

Scenario mutation of fixation result:
```python
previous_used = float(fixation.used_commutation or 0.0)
fixation.used_commutation = previous_used + used_total
fixation.exempt_capital_remaining = max(0.0, remaining_exempt)
```

Raw result mutation:
```python
raw = fixation.raw_result or {}
if isinstance(raw, dict):
    exemption_summary = raw.get("exemption_summary") or {}
    exemption_summary["remaining_exempt_capital"] = (
        fixation.exempt_capital_remaining
    )
    raw["exemption_summary"] = exemption_summary
    fixation.raw_result = raw
```

Frontend commutation usage:
File: `C:\Users\omer\OneDrive\AI PROJECTS\WINSURDF\dev\retire\frontend\src\pages\SimpleFixation\hooks\useFixationData.ts`

```typescript
const commutationAssets = (capitalAssets.data || []).filter((asset: any) =>
  asset.remarks && asset.remarks.includes('COMMUTATION:') && asset.tax_treatment === 'exempt'
);
```

```typescript
const amountMatch = asset.remarks?.match(/amount=([\d.]+)/);
const amount = amountMatch ? parseFloat(amountMatch[1]) : asset.current_value;
```

Finding:
- There is a SQLAlchemy `Commutation` model with `impact_on_exemption`, but the discovered fixation flow does not appear to read it when calculating current fixation.
- Scenario commutations are represented as `CapitalAsset` rows with `remarks` containing `COMMUTATION:` and `conversion_source`.
- Real actual tax-free capitalizations/heivunim as a separate authoritative fixation input are unclear from code.
- `used_commutation` exists on `FixationResult` and is mutated by scenario exemption allocation.

**6. IDF fixation**
File: `C:\Users\omer\OneDrive\AI PROJECTS\WINSURDF\dev\retire\app\services\rights_fixation\idf_fixation.py`  
Function: `compute_idf_fixation_impact`

Core formula:
```python
base_reduction = reduction_amount_f * (original_percent_f / current_percent_f)

max_reduction = monthly_cap_f * 0.35
monthly_reduction_for_calc = min(base_reduction, max_reduction)
```

Overlap dates:
```python
elig_dt = _parse_date(eligibility_date, "תאריך הזכאות")
comm_dt = _parse_date(commutation_date, "תאריך ההיוון")
prom_dt = _parse_date(promoter_age_date, "תאריך גיל המקדם")

overlap_start = max(elig_dt, comm_dt)
overlap_end = prom_dt
```

Month count:
```python
def _months_between(start: date, end: date) -> int:
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day < start.day:
        months -= 1
    return months
```

Impact:
```python
overlap_months = _months_between(overlap_start, overlap_end)
impact = round(monthly_reduction_for_calc * overlap_months, 2)
```

Zero/error branches:
```python
if (
    reduction_amount is None
    or original_commutation_percent is None
    or current_commutation_percent is None
):
    zero_result.error = (...)
    return zero_result
```

```python
if reduction_amount_f <= 0 or original_percent_f <= 0 or current_percent_f <= 0:
    zero_result.error = (...)
    return zero_result
```

```python
if monthly_cap is None:
    zero_result.error = (...)
    return zero_result
```

```python
if overlap_end <= overlap_start:
    return IdfFixationResult(
        impact=0.0,
        overlap_months=0,
        base_reduction=base_reduction,
        monthly_reduction_for_calc=monthly_reduction_for_calc,
        error="...",
    )
```

Server save behavior:
File: `C:\Users\omer\OneDrive\AI PROJECTS\WINSURDF\dev\retire\app\routers\rights_fixation.py`  
Function: `save_rights_fixation`

```python
idf_data["impact_on_exemption"] = idf_result.impact
idf_data["overlap_months"] = idf_result.overlap_months
idf_data["base_reduction"] = idf_result.base_reduction
idf_data["monthly_reduction_for_calc"] = (
    idf_result.monthly_reduction_for_calc
)
```

Server stores display/audit field but comment says it does not change remaining capital:
```python
# שמירת סיכום ברמת ה-exemption_summary, בלי לשנות את שדה remaining_exempt_capital.
exemption_summary["idf_security_forces_impact"] = (
    idf_impact_value
)
```

Frontend subtracts IDF impact:
File: `C:\Users\omer\OneDrive\AI PROJECTS\WINSURDF\dev\retire\frontend\src\pages\SimpleFixation\utils\fixationCalculations.ts`

```typescript
const remainingExemption = remainingExemptCapital - futureGrantImpact - totalDiscounts - idfImpact;
```

Findings:
- Backend IDF calculation writes `idf_security_forces_impact` into `exemption_summary`.
- Backend save code explicitly comments that it does not change `remaining_exempt_capital`.
- Frontend calculation subtracts `idfImpact` from remaining exemption and saves that result as `remaining_exempt_capital`.
- Therefore IDF is partially reduced in frontend save flow; backend IDF calculation alone is display/audit unless frontend-calculated save payload includes the reduction.

**7. Saved FixationResult structure**
File: `C:\Users\omer\OneDrive\AI PROJECTS\WINSURDF\dev\retire\app\models\fixation_result.py`

```python
class FixationResult(Base):
    __tablename__ = "fixation_result"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("client.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    exempt_capital_remaining = Column(Float, nullable=False, default=0.0)
    used_commutation = Column(Float, nullable=False, default=0.0)
    raw_payload = Column(JSON, nullable=True)
    raw_result = Column(JSON, nullable=True)
    notes = Column(String(500), nullable=True)
```

Where `exempt_capital_remaining` is written:

`C:\Users\omer\OneDrive\AI PROJECTS\WINSURDF\dev\retire\app\routers\rights_fixation.py`, `save_rights_fixation`:
```python
existing.exempt_capital_remaining = result.get("exemption_summary", {}).get(
    "remaining_exempt_capital", 0
)
```

```python
fixation_record = FixationResult(
    client_id=client_id,
    created_at=datetime.now(),
    exempt_capital_remaining=result.get("exemption_summary", {}).get(
        "remaining_exempt_capital", 0
    ),
    used_commutation=0.0,
    raw_payload=formatted_data,
    raw_result=result,
)
```

`C:\Users\omer\OneDrive\AI PROJECTS\WINSURDF\dev\retire\app\routers\rights_fixation_parts\common.py`, `calculate_and_save_fixation_for_client`:
```python
existing.exempt_capital_remaining = remaining_exempt_capital
```

```python
fixation_record = FixationResult(
    client_id=client_id,
    created_at=now,
    exempt_capital_remaining=remaining_exempt_capital,
    used_commutation=0.0,
    raw_payload=formatted_data,
    raw_result=result,
)
```

`C:\Users\omer\OneDrive\AI PROJECTS\WINSURDF\dev\retire\app\services\retirement\services\commutation_exemption_service.py`, `apply_exempt_capital_to_scenario_commutations`:
```python
fixation.exempt_capital_remaining = max(0.0, remaining_exempt)
```

Where `raw_result.exemption_summary.remaining_exempt_capital` is written:

`common.py`, `update_fixation_exempt_pension_fields`:
```python
exemption_summary["remaining_exempt_capital"] = remaining_exempt_capital
```

`commutation_exemption_service.py`, `apply_exempt_capital_to_scenario_commutations`:
```python
exemption_summary["remaining_exempt_capital"] = (
    fixation.exempt_capital_remaining
)
```

Derived pension fields recalculated:

`common.py`, `update_fixation_exempt_pension_fields`:
```python
if exempt_capital_initial > 0:
    exemption_percentage = remaining_exempt_capital / exempt_capital_initial
else:
    exemption_percentage = 0.0

pension_ceiling = get_monthly_cap(eligibility_year_int)
if pension_ceiling > 0:
    exempt_pension_percentage = (
        remaining_exempt_capital / 180.0
    ) / pension_ceiling
    remaining_monthly_exemption = round(
        exempt_pension_percentage * pension_ceiling, 2
    )
else:
    exempt_pension_percentage = 0.0
    remaining_monthly_exemption = 0.0
```

```python
exemption_summary["remaining_monthly_exemption"] = remaining_monthly_exemption
exemption_summary["exempt_pension_percentage"] = exempt_pension_percentage
exemption_summary["total_commutations"] = used_commutation
exemption_summary["final_remaining_exemption"] = remaining_exempt_capital
```

Lazy recalculation:
File: `C:\Users\omer\OneDrive\AI PROJECTS\WINSURDF\dev\retire\app\routers\rights_fixation.py`  
Function: `get_saved_fixation`

```python
needs_update = (
    not isinstance(exemption_summary, dict)
    or "exempt_pension_percentage" not in exemption_summary
    or "remaining_monthly_exemption" not in exemption_summary
)
if needs_update:
    update_fixation_exempt_pension_fields(result)
```

Other callers:
`C:\Users\omer\OneDrive\AI PROJECTS\WINSURDF\dev\retire\app\services\llm_chat\tool_handlers\calculate_fixation_of_rights.py`
```python
update_fixation_exempt_pension_fields(fixation_result)
db.flush()
```

`C:\Users\omer\OneDrive\AI PROJECTS\WINSURDF\dev\retire\app\services\retirement_scenario_execution_service.py`
```python
update_fixation_exempt_pension_fields(fixation_record)
```

**8. Numerical examples / Golden candidates**
Existing hardcoded examples found:

`C:\Users\omer\OneDrive\AI PROJECTS\WINSURDF\dev\retire\app\routers\rights_fixation.py`, function `test_cbs_api`:
```python
test_amount = 100000
test_date = "2020-01-01"

result = calculate_adjusted_amount(test_amount, test_date)
```
This is an API smoke example, not a deterministic golden case because it depends on CBS API/current date.

`C:\Users\omer\OneDrive\AI PROJECTS\WINSURDF\dev\retire\app\routers\rights_fixation.py`, docstring for `/calculate`:
```python
{
    "grants": [
        {
            "grant_amount": 100000,
            "work_start_date": "2010-01-01",
            "work_end_date": "2020-12-31",
            "employer_name": "חברה א'"
        }
    ],
    "eligibility_date": "2025-01-01",
    "eligibility_year": 2025
}
```
No expected output in code.

`C:\Users\omer\OneDrive\AI PROJECTS\WINSURDF\dev\retire\app\routers\rights_fixation.py`, docstring for `/grant/effect`:
```python
{
    "grant_amount": 100000,
    "work_start_date": "2010-01-01",
    "work_end_date": "2020-12-31",
    "eligibility_date": "2025-01-01"
}
```
No expected output in code.

`C:\Users\omer\OneDrive\AI PROJECTS\WINSURDF\dev\retire\tests\test_execute_pension_commutation_tool.py`, `test_execute_pension_commutation_creates_asset_and_updates_fund`:
```python
"commutation_amount": 50000,
"commutation_date": "2025-01-01",
"commutation_type": "taxable",
```
Expected:
```python
assert fund.balance == 50000.0
assert fund.pension_amount == 250.0
assert "amount=50000" in (asset.remarks or "")
assert float(asset.monthly_income or 0) == 50000.0
assert asset.tax_treatment == "taxable"
```
This is a commutation execution example, not a fixation-calculation golden case.

No existing deterministic test fixture with full fixation input/output was found in the inspected test results. Exact useful golden cases from current tests are unclear from code.

**9. Existing tests touching requested areas**
Direct tests for `app/services/rights_fixation/exemption_caps.py`: not found.

Direct tests for `app/services/rights_fixation/work_ratio.py`: not found.

Direct tests for `app/services/rights_fixation/indexation.py`: not found.

Direct tests for `app/services/rights_fixation/idf_fixation.py`: not found.

Direct tests for `FixationResult` persistence calculation fields: not found.

Tests found touching fixation/document endpoints:

`C:\Users\omer\OneDrive\AI PROJECTS\WINSURDF\dev\retire\tests\test_fixation_api.py`
- `test_fixation_endpoints_exist`: asserts `/api/v1/fixation/{client_id}/161d`, `/grants-appendix`, `/package` do not return 404.
- `test_client_not_found`: asserts missing client returns 404 and error detail.
- `test_inactive_client`: asserts inactive client returns 400.
- `test_api_response_structure`: asserts 161d response structure contains JSON fields like `file_path`, `client_id`, `client_name` on success.
- `test_package_endpoint_response_structure`: asserts package response includes `files` and length `3`.
- `test_grants_appendix_endpoint_response_structure`: asserts grants appendix response structure.
- `test_commutations_appendix_endpoint_response_structure`: asserts commutations appendix response structure.
- `test_hebrew_error_messages`: asserts error contains Hebrew characters.

Tests found touching commutation execution:

`C:\Users\omer\OneDrive\AI PROJECTS\WINSURDF\dev\retire\tests\test_execute_pension_commutation_tool.py`
- `test_execute_pension_commutation_creates_asset_and_updates_fund`: asserts commutation tool creates `CapitalAsset`, reduces fund balance/pension, marks taxable, writes `COMMUTATION:` remarks and `conversion_source`.
- `test_execute_process_termination_requires_approved_preview_and_overrides_args`: approval flow test, not fixation formula.
- `test_execute_pension_commutation_rejects_amount_over_balance`: asserts no asset created and fund unchanged when commutation exceeds balance.

`C:\Users\omer\OneDrive\AI PROJECTS\WINSURDF\dev\retire\tests\test_commutation_from_snapshot_balance_and_snapshot_zero.py`
- `test_commutation_from_snapshot_zeros_snapshot_and_does_not_double_balance`: asserts scenario snapshot balances are zeroed after commutation and no double balance remains.

`C:\Users\omer\OneDrive\AI PROJECTS\WINSURDF\dev\retire\tests\test_scenario_conversion_asset_mapping.py`
- `test_scenario_conversion_commutation_asset_is_lump_sum`: asserts scenario conversion commutation asset is a lump sum via `current_value > 0`, `monthly_income == 0`, `payment_frequency == "annually"`.

Tests found touching LLM/orchestration fixation status, not formulas:

`C:\Users\omer\OneDrive\AI PROJECTS\WINSURDF\dev\retire\tests\test_stream_orchestration_plan_fixation_status.py`
- `test_stream_orchestration_plan_fixation_status_uses_tool_no_llm`: asserts fixation-status orchestration uses `GET_FIXATION_STATUS_SNAPSHOT` and does not call LLM.

`C:\Users\omer\OneDrive\AI PROJECTS\WINSURDF\dev\retire\tests\test_llm_system_inventory_deterministic_stream.py`
- `test_stream_system_inventory_bypasses_llm_and_uses_snapshot_tool`: fixture includes `"fixation_results": 1`; asserts system inventory uses snapshot tool without LLM.
- `test_stream_list_all_entities_bypasses_llm_and_formats`: entity-list formatting; no fixation formula assertion.

Unclear from code:
- No direct unit test found for grant impact formula `* 1.35`.
- No direct unit test found for exemption caps fallback behavior.
- No direct unit test found for IDF impact calculation.
- No direct unit test found for scenario commutation exemption allocation mutating `FixationResult`.
- No deterministic full fixation input/output golden case found.