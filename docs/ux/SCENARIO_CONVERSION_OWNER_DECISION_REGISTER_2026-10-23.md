# RETIRE V2 — Owner decision register for scenario conversion

**Status:** pending professional acceptance. This register summarizes the independent Work BLOCKED audit; proposals are not decisions. Financial implementation and production are NOT authorized.

| ID | Professional decision | Conservative proposed default (NOT APPROVED) | Safe work independent of decision |
| --- | --- | --- | --- |
| O-01 | Do investment provident / education fund product exceptions override otherwise blocked severance/termination classifications? | Never override an unsettled severance prerequisite automatically; mark disputed pairing unresolved | Type-resolution design; component × product test fixtures |
| O-02 | Tax treatment for pre-2000 employee/employer contribution converted to pension: V1 frontend exempt vs V1/V2 backend taxable | Return `tax_status=not_evaluated`; make no tax claims | Permission-only preview and evidence collection |
| O-03 | Mixed whole-plan treatment: reject batch or allow explicitly reviewed eligible subset? | Show every eligible/blocked/unresolved component; no silent skip, and save only after explicit review | Read-only component-level preview contract |
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

## Recommended next owner decision (single, focused)

**O-03:** for a full pension plan containing both allowed and prohibited components, should the planner be permitted to submit an explicitly reviewed eligible subset, with all excluded components visibly listed and none silently removed? The recommended answer is **yes** for an explicitly reviewed subset, never silent pruning. This recommendation is pending owner confirmation.

Decision provenance: owner message/date, revision, approver identity and affected contract section should be recorded only after the owner actually decides.
