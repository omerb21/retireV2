# RETIRE V2 - Owner decision: scenario planning foundation (2026-10-28)

Status: **OWNER_APPROVED_FOUNDATION**, not authorization for unspecified financial semantics or production deployment.

Owner decision, 2026-10-28: explicitly approved the seven conservative scenario-planning principles proposed in the product-management conversation. This decision supersedes the prior *lack of approval for these principles only*. It does not silently supersede accepted, narrower financial contracts, reopen sealed routes, or authorize business formula invention.

## Binding professional principles

1. **Scenario factual baseline**: Use accepted canonical client data plus separately persisted hypothetical scenario decisions. A scenario calculation/preview must never mutate factual assets, pension product components, or past accepted results.
2. **Allocation accounting**: Count a source component no more than once per scenario; block allocations greater than verified availability. Retain and show unallocated balances separately; never infer how unallocated balances will be realized.
3. **Gross income before net**: Produce gross outcomes only from approved canonical sources and applicable accepted engines; missing professional coefficients or source evidence must not receive invented defaults.
4. **Tax/fixation gate**: A net outcome requires valid, applicable tax, exemption and fixation data *and a separately accepted hypothetical-scenario tax contract*. Otherwise, return explicit blocked/unavailable status; do not invent net values.
5. **Temporal/cashflow basis**: Attribute each authorized income/expense to its verified effective period; nominal and real values have distinct provenance and may not be silently blended. No implicit indexation, gross-to-net conversion or household aggregation.
6. **Comparability**: Compare only results whose accepted scope, temporal horizon, price basis, input identity and validity state are compatible under a separately accepted comparison contract.
7. **Provenance and invalidation**: Preserve canonical source identities, revision/version links, deterministic fingerprints (SHA-256 where contractually applicable), history and non-destructive invalidation. Source or decision changes that affect an output render the prior output non-current, never retroactively alter it.

## Explicit authority boundary

- Stage 6 existing single pension decision estimate remains limited to its previously accepted **nominal gross** calculation. This document does **not** allow Stage 6 aggregation, tax, net, capital, NPV, income-gap, or cashflow outputs.
- Existing M09 archive-only and sealed M10 execution routes remain unchanged. This document does **not** authorize enabling a historical route as a current scenario producer.
- No tax formula, social insurance rule, retirement eligibility determination, indexation, conversion factor fallback, discount rate, or statutory entitlement is defined here.
- No recommendation, final-plan report, M11-M14 business expansion, public rollout, deployment or merge is authorized here.
- Previously accepted source-of-truth contracts and scenario provenance rules take precedence over generic implementation convenience.

## First bounded derivation task (contract/design, not executable financial authority)

Derive a verifiable **scenario-to-current-monthly-cashflow input contract** from existing canonical M01-M09 owners. Its proposed input identity must specify client ID, scenario ID/version, accepted factual revision/fingerprint, decision IDs/versions, exact canonical product/component identity, gross amount provenance, date/horizon, nominal price basis and currentness status.

For each source/decision classify: ACCEPTED_FOR_THIS_PRODUCER, BLOCKED_MISSING_AUTHORITY, BLOCKED_STALE, BLOCKED_OVERALLOCATION, or OUT_OF_SCOPE. Keep unallocated amounts visible separately. Each output must identify its owning producer and be reproducible from a read-only snapshot.

Before implementing any new executable current M09 route, separately resolve, with explicit professional approval: precise allowed decision families and aggregation arithmetic, canonical M09 temporal input mapping, expenses and non-pension sources, currentness fingerprint composition, output envelope/statuses, and whether historical M09 contracts can be reused without violating sealed boundaries. Tax/net and comparison remain separately gated.

## Verification and protection

- No code, migrations, database data, financial engine, API or UI changed by this decision record.
- No CI, deployment, merge or Render action.
- Stage 6 previously accepted end-to-end evidence must not be rerun without new reason.
- Work is authorized to pursue independent already-approved development scopes while professional arithmetic remains blocked; do not represent this document alone as authorization to complete all modules.
