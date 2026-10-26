# RETIRE V2 — SC-06B Documentary Review Lifecycle Contract

**Status: DESIGN DRAFT / NOT IMPLEMENTATION-AUTHORIZED**  
**Predecessor:** SC-06A independent PASS, HEAD `1b1d6cf7e6b8363c37c995cab0b8d1f97c9aec1c`.  
**Owner decision D-02 APPROVED (2026-10-26):** a verified professional may explicitly supersede a prior rejection after a fresh review, with a mandatory recorded rationale and immutable original rejection. Other lifecycle choices remain design-only.  
**Scope:** distinguish immutable historical review evidence from currently applicable documentary evidence; **not** professional admission or permission to calculate.

## 1. Verified starting point

- `scenario_coefficient_professional_reviews` is append-only at the application role. Current rows contain `review_id`, immutable decision and source identity, timestamp, actor and fingerprints; **no supersession/revocation relationship**.
- `scenario_coefficient_readiness_service` reads all reviews for a scenario decision under the existing SC-03 PostgreSQL `REPEATABLE READ READ ONLY` snapshot, and correctly fails closed when any matching rejection, stale or invalid review is present.
- SC-06A acceptance explicitly retained that blocking behavior. A new policy must **not silently modify SC-06A**.

## 2. Terms

**Historical evidence:** every previously appended review row, retained indefinitely subject to approved retention policies.  
**Current provenance:** DB-derived scenario, decision, election, source, product and profile facts within one snapshot, fingerprinted by the existing SC-05 context service.  
**Applicable evidence:** a review that is both integrity-valid and provenance-matched **and** has an explicit, independently validated lifecycle status; chronological order alone does not establish applicability.  
**Supersession event:** a separately appended, authenticated, auditable statement relating one exact prior `review_id` to one specific successor `review_id`, with an explicit professional rationale. It never changes/deletes either original review.  
**Professional admission:** separate future contract; no lifecycle event grants it.

## 3. Proposed invariants (fail closed)

1. No UPDATE/DELETE on review evidence; no inferred supersession from `created_at`, `reviewed_at`, scenario version, matching fingerprints or newest row.
2. A successor must reference an existing prior review for the **same client, scenario and decision**. Record IDs and their immutable fingerprints must both match; reject foreign-client and foreign-decision references.
3. Every transition needs a verified professional actor from the server-authenticated session, explicit reason, precise event identity and a dedicated PostgreSQL `SERIALIZABLE` write transaction. Never accept request-supplied actor or fingerprints as authority.
4. Original and successor remain visible in history. A supersession is an additional event, not a mutation of their contents.
5. No cycles, branching successors, duplicate active successors, ambiguous ordering or cross-provenance reuse. Conflicts, missing targets and malformed lifecycle events block readiness.
6. A matching rejection stays blocking until an **explicit, authenticated supersession event** records a fresh professional review, the successor decision and a mandatory professional rationale. The owner has approved this replacement principle (D-02). A new approval does not automatically cancel rejection.
7. A source change invalidates prior **current applicability** without deleting evidence. An explicit successor after new source verification may become applicable only under an approved policy.
8. All applicable/current resolution occurs inside **one** accepted SC-03 snapshot; never read lifecycle events and source facts in separate transactions.
9. No coefficient lookup, no financial calculation, no scenario adapter, no API or deployment authorization.

## 4. Suggested append-only data contract — proposal only

A distinct `scenario_coefficient_review_lifecycle_events` table rather than altering the approved SC-05 review table:

- `event_id` immutable unique ID
- `client_id`, `scenario_id`, `decision_id` — ownership scope
- `prior_review_id`, `successor_review_id` — exact immutable references
- `prior_record_fingerprint`, `successor_record_fingerprint` — bound identity
- `event_kind` — initially only `supersession` (no silent revoke)
- `reason` — non-empty professional rationale
- `professional_actor_id`, `recorded_at`
- `event_fingerprint` — canonical event integrity

Constraints must enforce append-only ACL (`SELECT, INSERT`), FK references and relevant uniqueness. DB or transactional validation must enforce **same ownership, no cycles and no branching**; hashes alone are not trust evidence. Strong concurrent-write tests required.

No migration is created in this design phase.

## 5. Proposed resolver (future; not implemented)

A future read-only resolver would return only documentary disposition:

| Evidence / event state | Proposed result |
| --- | --- |
| No review exists | BLOCKED — missing |
| One matching review, no invalid evidence | UNRESOLVED — documented, not authorized |
| Matching rejection, no valid authorized supersession | BLOCKED — rejected |
| Historical review stale, no successor relationship | BLOCKED — history unresolved |
| Exact, authenticated, unambiguous supersession chain, new matching review | UNRESOLVED — documented, not authorized **only if policy approved** |
| Invalid fingerprint / altered event / missing or foreign target | BLOCKED |
| Concurrent successors / cycles / ambiguity | BLOCKED |

A valid lifecycle chain never implies `execution_allowed=true`, an annuity factor, financial result or planning snapshot.

## 6. Decisions required before implementation

**D-01 — When a source changes:** Can a new validated review explicitly replace the old historical review, or must both block pending manual reconciliation?

**D-02 — Rejections: APPROVED.** After a fresh examination, a verified professional may explicitly supersede a prior `rejected` review. Require an intentional authenticated action, a professional reason and an immutable link to the original rejection. A distinct second-person approval is **not required by this decision**; do not invent one. This still conveys documentary applicability only, not financial authority.

**D-03 — Concurrency:** Is a strict single active chain per scenario decision sufficient, including multiple source versions, or is a separate reviewed-context identity required for each branch?

**D-04 — UI:** Is the lifecycle managed solely as a professional audit action within the eventual workflow, with the chronology visible on demand?

D-01, D-03 and D-04 remain proposed and not approved. Until the lifecycle contract is approved for implementation, **preserve current SC-06A fail-closed behavior**.

## 7. Acceptance plan for a future authorized package

- Contract/negative-oracle tests for spoofed actors, false successor links, cross-client references, timestamp ordering attacks, tampering, stale source and conflicting rejections.
- Disposable PostgreSQL tests for FK/ACL, serializable concurrent conflict, append-only history, and one-snapshot resolver behavior.
- One bounded independent Work Medium READ ONLY acceptance gate at package boundary; no repetitive CI.
- Explicit owner authorization before migrations or production service code, and separate merge/deploy permission.

**Persistent boundaries:** `COEFFICIENT_LOOKUP = NOT_AUTHORIZED`; `FINANCIAL_CALCULATION = NOT_AUTHORIZED`; `SCENARIO_CALCULATION_ADAPTER = NOT_AUTHORIZED`; `PRODUCTION_DEPLOYMENT = NOT_AUTHORIZED`.
