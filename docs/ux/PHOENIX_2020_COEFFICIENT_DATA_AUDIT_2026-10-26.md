# RETIRE V2 — Phoenix 2020 XLSB coefficient audit (research only)

**Source:** User-provided `מחשבון קצבה פנסיה הפניקס 2020 - נעול.xlsb`; worksheet `מקדמים` decoded from binary cached cell values, no macros executed. Research extraction only: not a professionally authoritative current catalog or an executable scenario input.

## Reproduced inventory

- 86,920 populated records: 43,460 `מקיפה` and 43,460 `כללית`.
- Each of 43,460 keys uniquely pairs a comprehensive and general record by `מין`, `גיל פרישה`, `חלקיות גיל`, `שנת לידה`, `תקופת הבטחה`, `הפרש גיל`.
- Key coverage: male/female (21,730 matched keys each), retirement ages 60–87, birth years 1933–1964, guarantee months 0–240 (12-month steps), spouse age differences -20..+20; stored age-fraction value 0 throughout the extracted table.
- Two *distinct* value columns: `מקדם לפנסיונר` and `מקדם לבן/בת הזוג`. Never treat the first component as the final coefficient for every survivor option without validating the combination formula.
- For 43,460 matched rows the general/comprehensive **pensioner component** difference is min 1.04742687%, mean 2.31330667%, max 3.30340686%. The **spouse component** difference is min 0.42973921%, mean 4.81074643%, max 9.95612023%. The latter is a ratio of the *component*, not a pension-income difference.
- Reproducible example: male, retirement 67, birth year 1953, 180 guarantee months, spouse age difference 0: comprehensive pensioner 178.8783417980; general pensioner 183.4469976310; comprehensive spouse 21.7948666884; general spouse 23.0822967119.
- The table does **not** cover birth year 1965, so one cannot use this file to independently verify that year.
- Worksheet `חישוב זקנה` includes cached output matrices by survivor percentage and guarantee period, but complete formulas and macro calculations have **not** been independently established. Do not assume all cached outputs represent valid same-case actuarial illustrations.

## Acceptance impact

1. A single shared calculator/engine may be feasible but equal coefficients across comprehensive/general products are *disproven within this 2020 Phoenix file*; the source is historical.
2. Cross-insurer equality is **not yet tested**; match identical date, product type, survivor/guarantee conditions and table version before any assertion.
3. Catalog schema should preserve components, option metadata, source edition/hash and explicit provenance; never silently reuse the pensioner-only component as the full coefficient.
4. Owner requirement remains: verified provider/fund/policy-specific table preferred; generic planning fallback transparently marked; manual per-decision factor override supported after authorization.
5. No coefficient lookup, financial scenario, implementation, CI, deploy or approval of Stage 6 is authorized by this research.

## Next focused evidence task

Obtain official 2020 Phoenix regulation for coefficient concordance and matching 2020 other-fund schedules; separately evaluate current 2026 tables across providers. Build a version-matched numeric cross-provider set before concluding one generic table is acceptable.
