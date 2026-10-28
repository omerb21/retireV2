# SCENARIO_TO_MONTHLY_CASHFLOW: canonical source-bound contract derivation

Status: **DERIVED_DESIGN_ONLY** (2026-10-28). Authority: `PRODUCT_SCENARIO_FOUNDATION_OWNER_DECISION_2026-10-28.md`, approved by product owner; preserve narrower Stage 6 and M09/M10 contracts. This file does not authorize a current M09 route or financial computations.

## Verified existing code anchors

- `backend/app/schemas/scenario_draft.py`: `DraftDecisionWrite` has `decision_id`, `source_product_id`, `source_component_id`, canonical `component_code`, positive two-decimal `amount`, `action in {pension,capital_asset}`, `effective_date`; `DraftReplace` uses `expected_version` and max 500 decisions.
- `backend/app/services/scenario_snapshot_candidate_service.py`: database-derived inert manifest, client/scenario/version, product/component identities, product version, source fingerprint and balance, manifest fingerprint, exact amount and action; blocks `SOURCE_MISSING`, `SOURCE_STALE`, `SOURCE_OVERALLOCATED`, conflicting source facts; candidate reports `STRUCTURALLY_CONSISTENT_NOT_ADMITTED` and explicitly `execution_allowed=False` (not an approved calculation).
- `backend/app/schemas/m09_cashflow.py`: historical contract has canonical `YYYY-MM` start/end months, explicit scenario family/version, monthly gross inflow/outflow/period net, source/result fingerprints, currentness and eligibility.
- `backend/app/api/m09_cashflow_routes.py`: **archive only**, no currently executable scenario pipeline.
- `backend/app/api/m10_comparison_routes.py`: sealed, no replacement execution.
- Stage 6 is an approved single pension-decision nominal gross estimate only, not a portfolio aggregate or cashflow output.

## Proposed handoff identity (read-only, no financial execution yet)

One request is owned by an authenticated professional acting on a particular client, and references:
- `client_id`, `scenario_id`, `scenario_version`, manifest fingerprint derived from the *same* PostgreSQL read-only snapshot;
- evidence of factual baseline: exact canonical client/product/component identities, product version, source fingerprint, component balance, and any required rule/permission revisions;
- decisions: each immutable `decision_id` (if present; reject ambiguity in a persisted identity), action, component identity, exact two-decimal amount, effective date, and decision-level admission/status;
- requested `start_month`, `end_month` as canonical `YYYY-MM`, where start <= end; explicit temporal and price basis, no cross-basis mixing;
- nominated monthly-output producer and contract version; each output must declare owner, admitted input fingerprints, status, blocker codes, and input snapshot identity.

All evidence must be generated/checked server-side. Caller-provided hashes are claims, never independent authority. No new stored financial result arises from evaluating a draft. Historical accepted results remain immutable when the draft or facts change.

## Per-source classification and allocation invariant

Source keys are `(product_id, component_id)`, not display labels or component code alone. For each source, compare the sum of all scenario decision amounts using exact decimal arithmetic with the authoritative component balance inside one consistent database snapshot:
- total > balance => `BLOCKED_OVERALLOCATION`, no executable output;
- source absent, conflicting, not admitted or professionally unverified => `BLOCKED_MISSING_AUTHORITY`;
- expected product version/source fingerprint not equal current source => `BLOCKED_STALE`;
- decision family outside the eventual approved producer => `OUT_OF_SCOPE`, never silently included;
- otherwise `ACCEPTED_FOR_THIS_PRODUCER` requires a *separately* approved relevant producer and exact decision admission, not only structural consistency.

`unallocated = balance - allocated` is a proposed **accounting reconciliation**, not a financial result or conversion. It is shown separately and cannot silently become income, capital withdrawal, assumed pension, available tax exemption, or a comparison metric. The formula remains a proposed display invariant until the precise accepted producer boundary is recorded.

## Temporal and financial execution gates

Existing `effective_date` and monthly horizon do not establish pension start, end, mortality, cessation, overlapping employment, continuation, escalation, indexation or financial eligibility. Before enabling any monthly execution, **professionally approve**:
1. Allowed scenario decision families and their stage-6 admissibility: currently pension single-decision gross only, capital decision not an income producer.
2. Whether/how accepted single-decision gross estimates may be aggregated and assigned to `YYYY-MM` periods; no aggregation is authorized by current Stage 6.
3. Expense and non-pension source inclusion/exclusion, with authoritative M09 domain mapping and explicit null/missing behavior.
4. Nominal price base, temporal start/end assumptions and treatment of amounts after effective date.
5. Fingerprint payload, staleness and invalidation triggers, error/blocker envelope and immutable historical result link.
6. Separate tax/fixation gross-to-net contract (M07/M08) and separate two-scenario comparability/selection contract (M10), never implicit in M09 implementation.

Until approved, a current M09 execution attempt must be **BLOCKED_MISSING_AUTHORITY**, and no nominal gross Stage 6 amount may be labeled net income or retirement cashflow.

## Negative acceptance requirements

- Cross-client scenario, stale manifest, changed product version or overallocated source: reject.
- Two decisions must not double-count a source; decision edits cannot mutate factual balances.
- An out-of-scope capital decision must not produce a pension amount.
- An invalid coefficient, absent approval or stale admission cannot yield a substitute amount.
- Changing facts or decisions must invalidate current result identity while preserving old records.
- Archived M09/M10 results must never be represented as current scenario results.
- Stage 6 existing integration evidence is preserved and not rerun without a new defect.

## Implementation disposition

**NO_EXECUTABLE_M09_AUTHORITY_YET**. Reuse source contracts and verified owners rather than creating a second scenario engine. Exact financial aggregation, temporal rules and tax treatment remain professional decision gates, not programmer discretion. No runtime code, CI, merges, deployment or Render change accompanies this derivation.
