**Fixation V1 Decision Map**

**1. Cap / Exemption Tables And Years After 2028**

1. decision required  
Whether V1 freezes the current hardcoded tables as authoritative, including the rule that every year `>= 2028` uses 2028 values.

2. evidence from current code  
`exemption_caps.py` contains hardcoded `ANNUAL_CAPS` for 2012-2028 and `EXEMPTION_PERCENTAGES` for 2012-2028.  
`get_monthly_cap(year)`:
```python
if year >= 2028:
    return ANNUAL_CAPS.get(2028, 9430)
```
`get_exemption_percentage(year)`:
```python
if year >= 2028:
    return EXEMPTION_PERCENTAGES.get(2028, 0.67)
```

3. options  
- Preserve exactly: `>= 2028` always maps to 2028.
- Reject future-year fallback and require explicit table entry.
- Allow caller to provide the table as deterministic input.

4. recommended decision for deterministic V1  
Reject implicit future fallback. Require explicit cap and exemption percentage for the eligibility year, including years after 2028.

5. risk if left unresolved  
Future calculations silently use stale 2028 values.

---

**2. Unknown Year Fallback**

1. decision required  
Whether unknown years below 2028 should fall back to 2025.

2. evidence from current code  
`get_monthly_cap(year)`:
```python
return ANNUAL_CAPS.get(year, ANNUAL_CAPS[2025])
```
`get_exemption_percentage(year)`:
```python
return EXEMPTION_PERCENTAGES.get(year, EXEMPTION_PERCENTAGES[2025])
```

3. options  
- Preserve fallback to 2025.
- Reject unknown years as invalid input.
- Require caller-supplied cap/percentage.

4. recommended decision for deterministic V1  
Reject fallback. Unknown year should be a deterministic validation failure.

5. risk if left unresolved  
A wrong eligibility year can produce a plausible but incorrect result.

---

**3. 32-Year Work Ratio**

1. decision required  
Whether to preserve the day-based ratio currently used in `rights_fixation/work_ratio.py`.

2. evidence from current code  
`work_ratio_within_last_32y` uses:
```python
limit_start = elig_date - timedelta(days=int(365.25 * 32))
total_days = (end_date - start_date).days
overlap_days = max((overlap_end - overlap_start).days, 0)
ratio = overlap_days / total_days if total_days > 0 else 0
ratio = min(max(ratio, 0), 1)
```

3. options  
- Preserve exact day-based ratio.
- Switch to month-based ratio.
- Require precomputed ratio as input.

4. recommended decision for deterministic V1  
Preserve exact day-based ratio for V1, because it is the actual fixation flow behavior.

5. risk if left unresolved  
Golden tests may disagree around partial years, leap years, and boundary dates.

---

**4. Retirement-Date Cap In Work Ratio**

1. decision required  
Whether V1 should cap grant work end date at retirement date.

2. evidence from current code  
In `rights_fixation/work_ratio.py`, retirement date is calculated but not applied:
```python
retirement_date = get_retirement_date(birth_date, gender)
```
Then:
```python
effective_end_date = end_date
```

A separate duplicate implementation in `app/services/indexation_service.py` does cap:
```python
if retirement_date and end_date > retirement_date:
    effective_end_date = retirement_date
```

3. options  
- Preserve rights-fixation behavior: no retirement-date cap.
- Use duplicate `IndexationService` behavior: cap at retirement date.
- Mark as business decision.

4. recommended decision for deterministic V1  
Preserve current authoritative rights-fixation behavior: no retirement-date cap, unless a business decision explicitly changes it.

5. risk if left unresolved  
Same grant may receive different impact depending on which duplicate function is treated as source of truth.

---

**5. Indexation Responsibility**

1. decision required  
Whether V1 engine performs CPI indexation itself, calls CBS API, or receives indexed amounts as deterministic input.

2. evidence from current code  
`indexation.py` calls external CBS API:
```python
response = requests.get(CBS_CPI_API, params=params, timeout=10)
```
On failure:
```python
return None
```
Then `grant_impact.py` falls back:
```python
if indexed_full is None:
    indexed_full = float(grant["grant_amount"])
```

3. options  
- Preserve API call inside calculation.
- Preserve fallback to nominal amount.
- Move indexation outside deterministic V1 and require indexed grant amount as input.
- Require CPI table as deterministic input.

4. recommended decision for deterministic V1  
V1 should not call CBS and should not fall back to nominal. It should receive deterministic indexed amounts or deterministic CPI data.

5. risk if left unresolved  
Same input can produce different results depending on network/API availability and current date.

---

**6. Actual Capitalizations Vs Scenario Commutations**

1. decision required  
What counts as a capitalized/commuted amount reducing exempt capital in V1.

2. evidence from current code  
There is a `Commutation` model:
```python
commutation_amount = Column(Float, nullable=True)
impact_on_exemption = Column(Float, nullable=True)
```
But discovered fixation flow does not use it as the calculation source.

Scenario commutations are `CapitalAsset` rows:
```python
CapitalAsset.remarks.like("%COMMUTATION:%")
CapitalAsset.tax_treatment == "taxable"
```
Scenario service mutates fixation:
```python
fixation.used_commutation = previous_used + used_total
fixation.exempt_capital_remaining = max(0.0, remaining_exempt)
```

3. options  
- Treat `Commutation` model as actual capitalizations.
- Treat exempt `CapitalAsset` commutations as actual capitalizations.
- Treat scenario commutations as outside V1.
- Require explicit actual capitalization inputs.

4. recommended decision for deterministic V1  
Do not infer actual capitalizations from DB models. Require explicit deterministic actual capitalization/commutation inputs. Scenario commutations stay outside V1.

5. risk if left unresolved  
Scenario side effects and actual historical usage can be mixed, causing double counting or missing reductions.

---

**7. IDF Impact Authority**

1. decision required  
Whether backend IDF impact reduces remaining exempt capital or is display-only.

2. evidence from current code  
Backend computes and stores:
```python
exemption_summary["idf_security_forces_impact"] = idf_impact_value
```
Comment says:
```python
# בלי לשנות את שדה remaining_exempt_capital
```
Frontend subtracts:
```typescript
const remainingExemption =
  remainingExemptCapital - futureGrantImpact - totalDiscounts - idfImpact;
```

3. options  
- Backend IDF impact is display/audit only.
- Backend IDF impact reduces remaining capital.
- Frontend remains authority.
- Require V1 to reduce IDF impact deterministically.

4. recommended decision for deterministic V1  
V1 should make IDF impact authority explicit: if provided/applicable, it must be included in total impact and reduce remaining exempt capital. Frontend should not be the authority.

5. risk if left unresolved  
Saved results differ depending on whether user pressed save through the frontend path.

---

**8. Eligibility Responsibility**

1. decision required  
Whether V1 calculates eligibility date, validates eligibility, or only consumes eligibility date/year.

2. evidence from current code  
`eligibility.py` calculates:
```python
return max(legal_retirement_date, pension_start)
```
API client-id flow uses legacy:
```python
eligibility_date = calc_eligibility_date(client.birth_date, client.gender)
```
Then validates:
```python
age_condition_ok = today >= eligibility_date
pension_condition_ok = pension_start_date is not None and today >= pension_start_date
```
Internal flow does not enforce eligibility:
```python
# do NOT enforce the age/pension start date conditions here
```

3. options  
- V1 calculates eligibility date.
- V1 validates current eligibility.
- V1 receives eligibility date/year as input.
- V1 supports both statutory and effective eligibility date.

4. recommended decision for deterministic V1  
V1 should receive deterministic `eligibility_date` and `eligibility_year`; current-date eligibility validation belongs outside V1.

5. risk if left unresolved  
Results depend on today’s date and on inconsistent retirement-age functions.

---

**9. Missing Data Behavior**

1. decision required  
Whether missing/invalid data should produce zero, fallback, or validation failure.

2. evidence from current code  
Work ratio errors:
```python
except Exception:
    return 0.0
```
Indexation failure:
```python
return None
```
Grant impact fallback:
```python
indexed_full = float(grant["grant_amount"])
```
IDF missing data returns zero impact with error:
```python
zero_result.error = (...)
return zero_result
```
Full fixation catches errors:
```python
return {"grants": [], "exemption_summary": {}, "error": str(e)}
```

3. options  
- Preserve current mixed behavior.
- Convert missing data to zero.
- Convert missing data to explicit validation errors.
- Allow per-field optional behavior.

4. recommended decision for deterministic V1  
Reject hidden fallbacks. Missing required calculation inputs should produce explicit validation failure. Optional branches may return zero only when the branch is explicitly not applicable.

5. risk if left unresolved  
Invalid data can produce valid-looking zero or nominal results.

---

**10. Rounding Behavior**

1. decision required  
Define where V1 rounds and where it preserves precision.

2. evidence from current code  
Indexation:
```python
result = round(float(to_value), 2)
```
Grant limited amount:
```python
limited_indexed_amount = round(indexed_full * ratio, 2)
```
Grant impact:
```python
impact_on_exemption = round(limited_indexed_amount * 1.35, 2)
```
IDF impact:
```python
impact = round(monthly_reduction_for_calc * overlap_months, 2)
```
Monthly exemption:
```python
remaining_monthly_exemption = round(
    calculated_pension_exemption_percentage * pension_ceiling, 2
)
```

3. options  
- Preserve all current intermediate rounding.
- Round only final output fields.
- Use Decimal and explicit rounding mode.

4. recommended decision for deterministic V1  
Preserve current rounding points for V1 golden compatibility: indexed amount, limited indexed amount, grant impact, IDF impact, and monthly exemption at 2 decimals.

5. risk if left unresolved  
Small differences accumulate and break reproducibility.

---

**11. Golden Test Gap**

1. decision required  
Whether V1 can proceed without golden examples from current behavior.

2. evidence from current code  
Discovery found no deterministic full fixation input/output golden case. Existing examples are docstrings or API smoke examples. Existing tests cover endpoints, commutation execution, orchestration, and document response structure, but not deterministic fixation formulas.

3. options  
- Proceed without golden tests.
- Create golden tests from current code behavior before extraction.
- Use manually approved examples as golden cases.

4. recommended decision for deterministic V1  
Before final contract, define golden cases from current useful behavior: caps, grants with/without 15-year exclusion, work ratio boundary, future grant, actual capitalization, IDF, and missing data.

5. risk if left unresolved  
V1 may be deterministic but not demonstrably equivalent to the behavior intended to preserve.