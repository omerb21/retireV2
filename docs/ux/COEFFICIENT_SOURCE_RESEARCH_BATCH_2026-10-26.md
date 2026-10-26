# RETIRE V2 — coefficient research batch: reproducible evidence and insurer source inventory

**2026-10-26 | RESEARCH ONLY | NO Stage 6 execution authority.**

## 1. User intent / design constraints
The Phoenix 2020 pension XLSB is a comparison/calibration source, **not** a requirement to copy a generic V1 implementation. Preferred product: one canonical calculation implementation with correctly matched official coefficient evidence by provider/product/option, supplemented by a planner-controlled per-scenario-decision manual coefficient. A generic historical coefficient is an explicitly labelled planning fallback, never a guaranteed or provider-specific coefficient. Do not create another calculation engine, resurrect M09/M10, reopen closed packages, enable CI, or merge/deploy.

## 2. Independently replicated source-file facts

User file: `מחשבון קצבה פנסיה הפניקס 2020 - נעול.xlsb`. Read-only binary cached cell extraction with `pyxlsb` (no VBA executed), sheet `מקדמים`; cells 0–9 are the relevant coefficient-table columns:

`מין, גיל פרישה, חלקיות גיל, שנת לידה, תקופת הבטחה, הפרש גיל, מקדם לפנסיונר, מקדם לבן/בת הזוג, תקופת הבטחה בשנים, קרן`.

- 86,920 matching rows, precisely 43,460 `מקיפה` and 43,460 `כללית`.
- Unique match key: sex, retirement age, age fraction, birth year, guarantee months, spouse age gap. **43,460 paired keys, 0 duplicate full keys.**
- Population retirement age 60–87; birth year 1933–1964 (the source does *not* cover 1965+); 0 age fraction in coefficient-table rows.
- General vs comprehensive pensioner coefficient relative difference across all 43,460 pairs: min **1.0474268702%**, mean **2.3133066676%**, median **2.3862966728%**, max **3.3034068590%**.
- General vs comprehensive spouse-component relative difference: min **0.4297392149%**, mean **4.8107464341%**, median **4.7490786179%**, max **9.9561202311%**. This is not a full pension-income relative difference.
- Male birth year 1953 / age 67 / 180 guarantee months / spouse gap 0: comprehensive (pensioner **178.8783417980**, spouse **21.7948666884**); general (pensioner **183.4469976310**, spouse **23.0822967119**).
- The second sheet `חישוב זקנה` has a survivor percentage matrix including 30%–100%, but cached numerical results are not a validated formula specification. Never promote an isolated component to a final coefficient without reconstructing and validating the exact option composition.
- These facts disprove *identical* comprehensive/general component tables in this historical Phoenix file. They do **not** establish current market-wide differences, actuarial reasons, or cross-company equivalence.

### Reproducibility method
Using `pyxlsb.open_workbook`, iterate `מקדמים` rows; select populated numeric columns 1–7 and fund column 9 in `מקיפה, כללית`. Key: columns 0–5. Pair on the same key. Relative difference: `100*(general_component/comprehensive_component - 1)` independently for columns 6 and 7. Do not execute Excel macros or assume formulas have been recalculated. Use numeric decimal normalization/precision control before production ingestion.

## 3. Official insurance-manager source index (discovery, NOT complete parsed catalog)

| Insurer | Official link / reference | Discovered coverage | Evidence status |
| --- | --- | --- | --- |
| Phoenix | https://www.fnx.co.il/pension-savings/managers-insurance/ | Public links to calculator and conversion coefficients for policies sold Jan 2013–Jan 2022; further tables from Feb 2022. Site explicitly states 2013 coefficients generally not life-expectancy-guaranteed without company confirmation. | Official source index verified; numerical tables not fully ingested |
| Clal | https://www.clalbit.co.il/allowancecoefficients/ | Links labelled 2001, 2009 (3.5% and 3% net technical assumptions), 2013 and 2022. | Official source index verified; linked resources require individual verification |
| Clal | https://www.clalbit.co.il/savingandmanagementins/dynamicprofile/ | Separate general policy appendix, non-guaranteed and guaranteed-longevity plans, coefficients for new insured from 2015. | Official source index and a linked PDF verified |
| Clal | https://www.clalbit.co.il/media/26472/נספח-תכניות-ביטוח-מנהלים-כולל-מקדמי-קצבה-מובטחים-תוחלת-חיים-1401.pdf | 32-page official policy appendix with coefficient tables and yearly adjustment rules; **scope and the exact applicable plan must be checked**. | Direct PDF inspected; contains exact table, not blanket cross-policy authority |
| Harel | https://www.harel-group.co.il/Policies/2010.pdf | Historical `הראל מגוון למנהלים` (7/2009 edition), Annex A is pension conversion coefficients. | Official PDF discovered; numeric annex requires row/option extraction and version mapping |
| Menora | https://www.menoramivt.co.il/general/managers-insurance/executive-and-independent-status | `סטטוס מנהלים` product family and policy materials. | Official product reference; relevant historical/variant tables still to catalogue |

**Crucial meaning:** year labels are not sufficient to prove policy applicability. Insurer, policy product/family code, issue and effective dates, guaranteed vs adjustable status, age, sex, retirement year, pay-out option, survivor and guarantee details must match. Personal policy text / an insurer-issued quote may override a general catalogue.

Clal evidence: https://www.clalbit.co.il/allowancecoefficients/ and https://www.clalbit.co.il/savingandmanagementins/dynamicprofile/ .
Phoenix evidence: https://www.fnx.co.il/pension-savings/managers-insurance/ .
Harel evidence: https://www.harel-group.co.il/Policies/2010.pdf .

## 4. Research decisions and next measurable acceptance tasks

### Pension fund tables
Use **one existing canonical producer**, with appropriately versioned and source-bound factor data. Do not infer that all comprehensive funds or all general funds match each other from within-Phoenix data. Next cross-company controlled sample must match: source edition date, comprehensive/general type, birth date/year, retirement date/age, sex, spouse age gap, survivor percentage, guarantee period, fee assumptions, any actuarial/indexation assumptions. Capture table/page/row and calculate both coefficient and estimated monthly payout differences for a fixed capital. Until tested, `CROSS_PROVIDER_GENERIC_TABLE = NOT_VERIFIED`.

### Manager insurance
Build a **documentary table inventory** first, not a lookup service. Prioritize Clal (explicit dated archive), Phoenix (2013–2022 and 2022+), Harel (historical policy appendix), and Menora (Status families). Extract tiny identical test cases before full ingestion and require verification against policy terms for guaranteed factors. Mark documents with dynamic yearly increases separately from fixed factors. An internal source-specific coefficient is not a guarantee unless the exact policy so states.

### Manual override
Planner may explicitly set a positive precise factor per saved pension decision and record reason/evidence and special pay-out option (e.g. spouse receives 60% after death). No implicit transfer of manual factor to another decision; full invalidation when decision/source/date/option/factor changes; no generic catalogue mutation. This remains a Stage 6 proposed feature **not implemented**.

## 5. Execution and acceptance boundaries
`STAGE_6_IMPLEMENTATION=NOT_AUTHORIZED`; `COEFFICIENT_LOOKUP=NOT_AUTHORIZED`; `FINANCIAL_CALCULATION=NOT_AUTHORIZED`; `SCENARIO_CALCULATION_ADAPTER=NOT_AUTHORIZED`; `PRODUCTION_DEPLOYMENT=NOT_AUTHORIZED`.

Independent Work READ ONLY must still resolve current canonical `monthly_amount_basis` authority and all planning/temporal fingerprints, as identified by the existing Stage 6 contract. **Research findings do not permit running the existing V1 coefficient service's 200 fallback or creating parallel producers.**
