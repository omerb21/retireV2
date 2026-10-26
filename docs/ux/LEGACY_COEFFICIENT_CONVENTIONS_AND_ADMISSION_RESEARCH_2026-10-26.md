# RETIRE V2 — Legacy coefficient representation and evidence admission research

**26 October 2026. RESEARCH / DESIGN ONLY.** This document does not modify financial calculation, authorize Stage 6, CI, merge, or deploy.

## New source finding: historic inverted conversion convention
A professional discussion of 1990s–May 2001 "Adif" policies displays a historic table where the published value signifies **monthly pension per 10,000 units of accumulated capital** rather than capital / monthly pension; for that specific convention and identical currency units, the corresponding divisor is `10000 / historic_table_value`. Source: https://www.mpc.co.il/single-post/2016/12/10/איך-תחושב-הקצבה-שלכם-מביטוח-המנהלים . This is secondary historical evidence, **not an insurer-original annex**. Example value 60 per 10,000 mathematically corresponds to divisor 166.6667, not a source-verified coefficient of 166.63.

**Catalog schema requirement**: for every original coefficient entry preserve `source_representation` (`DIVISOR` or `PENSION_PER_10000_CAPITAL`), `source_value_exact`, units/currency and original page/table row; derive a normalized divisor **only** under approved, documented, exact conversion rules. Do not silently convert or assume equivalent basis if the original schedule includes indexing, differing accumulation unit, age or benefit terms. No automatic conversion is presently authorized.

## Policy option evidence
The above discussion identifies the classic basic pension option for certain historic Adif forms as minimum 120 guaranteed monthly payments; alternative survivor guarantees / payment periods may be priced only at retirement. Never map the historical guaranteed basic-option factor to a 60% surviving-spouse plan without the actual contract rider or personal quote.

## Official corroboration of insurer-specific limits
- Phoenix 2018 insurer disclosure: https://digital-content.fnx.co.il/sites/docs/genery/DohotKaspiyim/doch_holdings_q_4_2018_isa_mungash.pdf identifies Adif "Maniv"/"Atir" sold 1982–2003 with specified/guaranteed factor, and distinguishes CPI-linked contracts through 1990 versus participating-profit from 1991. This **does not supply complete original coefficients**.
- Policy-era figure source: https://www.prisha.co.il/Article/מקדם-קצבה provides periods and actuarial assumptions, including differences among post-2001 insurers; these descriptions are **secondary**, useful for classifying archival source searches and not insurer approval.

## Acceptance-oriented inventory record
For each original historic insurer table row:
- insurer, program/policy form and edition, issue interval, original contractual versus rider/continuation/new-deposit layer;
- chosen benefit/payout option (minimum payments, surviving-spouse lifetime percentage, any combination), sex, age, date and beneficiary assumptions;
- source document title, URL, hash and source page plus exact table position;
- `source_representation`, value, denominator/currency/rounding and verified normalization convention;
- original guaranteed status **separately** from future interest, expense and investment return assumptions; catalog provenance / permitted professional use;
- precise block codes if evidence is absent, nonmatching or contradictory.

## Negative acceptance cases
1. Inverted-table row interpreted as divisor without conversion; 10000 denominator assumed with inconsistent units; zero/negative or malformed value: block.
2. 120 minimum payments confused with 60% spouse survivor option; base option used for custom payout mode: block or explicit planner override after authorized contract.
3. Secondary benchmark (~144, ~153, ~166, ~200 etc.) used as binding guaranteed contract for a particular client: block.
4. Identical insurer and issue year but different original policy program or later contributions: prevent silent factor inheritance.
5. Any `annuity_coefficient_service` silent 200 default, stale row or unmatched source: block a claimed contract-specific calculation.

## Decision consequences
- Existing historical source research remains insufficient to admit exact coefficients for all original pre-2001 policy families. Continue insurer annex acquisition, avoiding duplicate calculate producers.
- Decision-scoped manual override remains a required product feature, but **not** currently implemented or approved for Stage 6 execution.
- Independent Work READ ONLY acceptance must decide source normalization, manual provenance and scenario monthly-basis authority before code implementation.

**Flags unchanged:** STAGE_6_IMPLEMENTATION=NOT_AUTHORIZED; COEFFICIENT_LOOKUP=NOT_AUTHORIZED; FINANCIAL_CALCULATION=NOT_AUTHORIZED; SCENARIO_CALCULATION_ADAPTER=NOT_AUTHORIZED; PRODUCTION_DEPLOYMENT=NOT_AUTHORIZED.
