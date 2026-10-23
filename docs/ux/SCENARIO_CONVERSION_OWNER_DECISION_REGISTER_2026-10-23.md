# RETIRE V2 — Owner decision register for scenario conversion

**Status:** O-03 OWNER APPROVED on 2026-10-23; O-01, O-02, O-04 through O-08 remain OPEN. Independent Work contract BLOCKED; financial implementation and production NOT authorized. The owner approval is a product-workflow decision, not legal eligibility approval.

| ID | Professional decision | Conservative proposed default (NOT APPROVED) | Safe work independent of decision |
| --- | --- | --- | --- |
| O-01 | Do investment provident / education fund product exceptions override otherwise blocked severance/termination classifications? | Never override an unsettled severance prerequisite automatically; mark disputed pairing unresolved | Type-resolution design; component × product test fixtures |
| O-02 | Tax treatment for pre-2000 employee/employer contribution converted to pension: V1 frontend exempt vs V1/V2 backend taxable | Return `tax_status=not_evaluated`; make no tax claims | Permission-only preview and evidence collection |
| O-03 | **APPROVED 2026-10-23**: A whole-plan preview must show all components; after explicit review and confirmation the planner may convert only the permitted selected components. Prohibited components remain unchanged; no silent pruning. | **Owner decision recorded**; server must revalidate the explicitly selected subset and reject a now-invalid submitted batch atomically. | Define preview, selection, confirmation, and submit protocol without changing factual conversion behavior |
| O-04 | For excluded components, individual acknowledgments or one reviewed grouped acknowledgment? | No automatic acknowledgment; require conscious user selection before any save | UI explanation/preview prototype, no persistence |
| O-05 | Is `leave_unallocated` a residual or an explicit retained-as-is instruction? | Residual calculated only; do not create a pseudo-conversion decision | Availability math and separate residual display |
| O-06 | Scope of V1 global unresolved-severance/rights-continuity blocker: component, product, or entire scenario? | Do not assume a global rule; block affected operations pending evidence, unrelated operations unresolved only if interdependent | Dependency/source classification mapping |
| O-07 | Who approves a ruleset and how historical effective dates and rule replacements work? | No user-managed financial overrides or retroactive automatic relabeling | Versioned rule record schema draft and audit review |
| O-08 | Which employment, grant, tax approvals/161d evidence is required for each action? | Missing or unreconciled required proof prevents accepted outcome; never infer from existence of unrelated record | Producer inventory and formal evidence status DTO |

## Review gates

**G0 – source facts closed:** V1/V2 basic permission matrix (11×2) matches for ordinary products; product-specific overrides and tax correctness NOT approved.

**G1 – safe technical design:** independent review can evaluate API shape, isolated factual ledger, read-only per-component preview, closed enums, CAS/idempotency, atomic save design and non-tax semantics, clearly marked *design only*. G1 cannot override any O-01 to O-08.

**G2 – professional policy:** owner resolves O-01 to O-08, or explicitly narrows the authorized feature to a permission-only read-only preview with unresolved statuses. An unanswered policy is not permission for a default to become authoritative.

**G3 – independent re-review:** Work rechecks the changed contract against the decision record, finding evidence and actual branch HEAD. Only explicit PASS on the bounded contract can support authorization of an implementation slice; no blanket engine or downstream authorization.

**G4 – implementation:** Codex receives a narrowly scoped development brief after G2/G3; any real code needs focused backend negative tests and separate user verification. No CI expansion or source mutations in scenario execution.

## Recorded approval and next open boundary

**O-03 approved by the professional owner in the conversation on 2026-10-23.** Exact accepted meaning: display all components of a whole pension plan, permit conversion of the allowed subset only after explicit review and confirmation, and never silently skip prohibited components. This does **not** accept product-type exception precedence (O-01), tax treatment (O-02), or individual-versus-grouped exclusion acknowledgment (O-04).

**Next open owner decision: O-04**, granularity of exclusion acknowledgment. No default is yet approved. Other decisions remain open; contract gate remains BLOCKED.
