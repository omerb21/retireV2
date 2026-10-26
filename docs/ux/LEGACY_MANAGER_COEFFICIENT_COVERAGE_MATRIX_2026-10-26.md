# RETIRE V2 | Legacy managers-insurance coefficient coverage matrix

**Scope:** retrospective insurer evidence inventory, design-only. Stage 6 execution, coefficient lookup, adapters, CI, merge and production remain unauthorized.

## Meaning of coverage levels

- VERIFIED_SOURCE_ROWS: row-level numerical data in an uploaded original insurer workbook, with the publication and pension option documented. **Not** approval that an individual's policy is entitled to that row.
- OFFICIAL_SOURCE_DISCOVERED: named official insurer catalog/document known, with missing extract or incomplete policy mapping.
- SECONDARY_BENCHMARK_ONLY: illustrative figures useful only for plausibility tests, never for customer-specific execution.
- NO_VERIFIED_ORIGINAL: no official original policy schedule established.

## Source-owned inventory

| Insurer / family | Program codes | Era or marketing scope from source | Pay-out option and assumptions | Status |
|---|---|---|---|---|
| Menora Marav | 805, 806 | 2001–2004 marketing listed in uploaded workbook | 180 guaranteed payments, technical interest 2.5%, charged management 0% in factor | VERIFIED_SOURCE_ROWS |
| Menora Status | 667, 668; related continuation 671 | marketed from 2008; rider may be limited to later contributions | 240 guaranteed payments, technical interest 4%, 0.5% fee | VERIFIED_SOURCE_ROWS |
| Menora Status combined | 225, continuation 672 | marketed circa 2010–2013, conditions vary by accumulation cohort | 240 guaranteed payments, technical interest 4%, separate fee 0.5%/0.6% | VERIFIED_SOURCE_ROWS |
| Harel 1286 (More managers historic) | 1286 | 2009 edition | track A, age/sex base-year factors plus annual increment | VERIFIED_SOURCE_ROWS (sample/table documented) |
| Harel More | edition 2022 / 2024 | later entrants and rider versions | 240-payment option; age/sex base-year and annual increments | VERIFIED_SOURCE_ROWS (sample) |
| Clal Dynamic Profile | 1401 | 2023 rider with 2022 base | 180, 240, 300, or 240+60% spouse with fixed-gap assumption | VERIFIED_SOURCE_ROWS (sample) |
| Clal supplemental/transfer | plan-list-dependent | workbooks 2001, 2009 variants, 2013, 2022 | **Rider/tranche scope**, not original contract for any same-year policy | VERIFIED SOURCE FILES, ENTITLEMENT UNRESOLVED |
| Phoenix Adif historic | Maniv / Atir and family variants | 1982–2003 published history | original policy annex and contract terms needed | OFFICIAL_SOURCE_DISCOVERED, NO ORIGINAL NUMERIC SCHEDULE |

## Owner's requested generations versus original contractual table readiness

| owner cohort | direct original-table coverage | remaining gap |
|---|---|---|
| 1970–1991 | NO_VERIFIED_ORIGINAL | insurer original actuarial annexes, issue-year/version, rider and guaranteed-payment option |
| 1991–1999 | NO_VERIFIED_ORIGINAL | insurer-specific original 'Adif' / participating plans; avoid treating a later continuation rider as original |
| 2000 | NO_VERIFIED_ORIGINAL | pre/post policy variant, deposits and original option |
| 2001 | PARTIAL from Menora Marav / Clal plan-specific file, not universal | June 2001 boundary, policy code and tranche |
| 2002–2004 | PARTIAL | other insurers and exact transition rider |
| 2004–2013 | PARTIAL | robust insurers, all policy and subtranche variations |

## Numeric source sanity checks

From uploaded Menora workbooks as parsed in the research chat, male retirement age 67 with retirement year 2026: Marav 210.1522446397, Status 0.5% 197.6508367192, Status combined 0.6% 199.7598255125. A matching Status 0.5% and Status combined 0.5% matrix was observed; identical cell values **do not make plan eligibility identical**. The earlier reported 5,838 unique numerical coefficient records is conditional on age/sex/year range inventory validation and should be independently recalculated before ingest. Do not use these values as universal age-67 historical generations.

## Historical benchmarks are *not* contract factors

Pensuni (https://pensuni.com/?p=1067) describes male age 65 historical examples 144.20 (to 1989), 153.16 (1990), 166.63 (1991–May 2001), 199.72 (June 2001–2003), 211.37 (2004–2008) and 199.71 (2009–2013), under different payout guarantees and with insurer/policy exceptions. Do not mix those illustration numbers with source-verified issuer tables, assign them to a customer's contract, or accept owner era labels as exact eligibility keys.

## Practical next work package

1. Acquire **original** policy annex PDFs for Phoenix Adif (Maniv/Atir), Menora and Harel legacy programs, and Clal, prioritizing pre-2001. Extract age/sex rows and exact default benefit guarantee under issue-date contracts.
2. Add explicit program mapping, policy issue date, applicable rider, deposit tranche and option evidence; compare 2026 effect only if source-specific adjustment authority is established.
3. Stage 6 acceptance must authorize decision-scoped manual override (including insurer quote and spouse conditions), data-source selection, exact monthly basis producer and date binding before implementing any calculation.
4. No duplicate producers or new regulatory approval workflows.
