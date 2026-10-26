# RETIRE V2 — Verified insurer annuity coefficient rows (research-only)

Date: 2026-10-26. **Not an executable catalog, no Stage 6 permission, no automatic matching.** Primary evidence: [Harel 2009 policy, program 1286, pdf page 30 (zero-indexed 29)](https://www.harel-group.co.il/Policies/2010.pdf), visually inspected. Cross-check the policy wording and individual rider before assigning to a customer.

## Harel — מגוון למנהלים, קצבה משלמת, מהדורה 7/2009, תכנית 1286

Annex A, retirement pension **track A** described in policy §18.1.1. Table columns: start age, male 2009 base factor, male annual increment %, female 2009 base factor, female annual increment %. It is **not** a generic coefficient for all Harel manager policies or other payout tracks. The table notes: 4.00% annual gross technical interest, 0.5% annual management deduction; guaranteed longevity basis, but technical gross interest may change, subject to a revised regulator-approved annex. The exact policy and active amendments override archive figures.

| age | male_base_2009 | male_annual_increment_pct | female_base_2009 | female_annual_increment_pct |
|---:|---:|---:|---:|---:|
|60|216.63|0.0824|226.53|0.1531|
|61|213.13|0.0846|222.71|0.1572|
|62|209.69|0.0863|218.91|0.1607|
|63|206.30|0.0874|215.12|0.1633|
|64|203.00|0.0877|211.38|0.1649|
|65|200.24|0.0775|207.70|0.1652|
|66|197.13|0.0772|204.12|0.1644|
|67|194.17|0.0759|200.66|0.1620|
|68|191.40|0.0738|197.35|0.1581|
|69|188.84|0.0708|194.22|0.1527|
|70|186.63|0.0651|191.29|0.1456|
|71|184.49|0.0608|188.59|0.1371|
|72|182.59|0.0560|186.13|0.1273|
|73|180.93|0.0505|183.94|0.1164|
|74|179.51|0.0449|182.03|0.1048|
|75|178.34|0.0398|180.39|0.0929|
|76|177.37|0.0340|179.02|0.0810|
|77|176.59|0.0287|177.90|0.0696|
|78|175.98|0.0239|176.99|0.0589|
|79|175.48|0.0201|176.27|0.0491|
|80|175.11|0.0167|175.70|0.0403|

**Important:** This is archival base-row evidence, not a projection to 2026. No automatic coefficient extrapolation is accepted; the specific annual update language, the individual's effective rider, interest updates and retirement date require independent verification first. No cross-insurer cross-product coefficient comparison should treat these values as contemporary fully adjusted factors.

## Clal — official downloadable archive (not yet parsed)

Official [niyud coefficients](https://www.clalbit.co.il/allowancecoefficients/) exposes distinct files labelled 2001, 2009 3.5% net, 2009 3% net, 2013, 2022. GitHub discussion/research must preserve technical-interest variant; 2009 is not a unique catalog selection key. Direct content extraction failed during this batch, so do **not** claim numeric verification for those Excel sheets.

## Phoenix — official lookup applicability warnings

Official [managers insurance page](https://www.fnx.co.il/pension-savings/managers-insurance/) lists 2013-2022 policies and policies from Feb 2022. Its public policy explanation says the 2013 coefficient table is not automatically life-expectancy guaranteed and presents a year-dependent increment based on start year and gender/age/guarantee terms. Do not interpret company/year alone as an entitlement.

## Menora — policy annex 702

Official [July 2024 rider](https://cdn.menoramivt.co.il/public/docs/20240715/%D7%A0%D7%A1%D7%A4%D7%97-702-07.2024---%D7%9E%D7%95%D7%A0%D7%92%D7%A9.pdf) states company coefficient schedule may change and may require adjusting spouse information, year, survivor percentage and option. This is policy evidence, **not** a complete numerical table.

## Contract consequence

Under the owner's product intention, first prefer an insurer-specific table precisely matched to policy/rider/edition/options; allow explicit per-decision planner override for quoted/special-plan factors; generic V1 factor only as labelled fallback. Do not create a second producer. Independent Stage 6 review remains required to admit coefficient selection, manual changes and pension monthly basis.
