# RETIRE V2 — Stage 6 BLOCKED verdict: minimal contract-repair proposal

**Reference independent Work verdict:** branch `feature/professional-workspace-ux-first-20261022`, HEAD `698279d0105c9233d44eebfc2b09c40ea3df6764`, TREE `735f946034f3f84eb9104ef3def36daceec9cbb1`. Reviewer verdict **BLOCKED**. This proposal is **not** Work acceptance, implementation permission, or an implementation.

## Gate 1 — Scenario-owned monthly authority (CALCULATION_CONTRACT)

Introduce a specifically named **proposed** `scenario_decision_balance_ratio` authority **inside the existing** `pension_monthly_basis_service` ownership, not a new calculating producer. Strict preconditions: one live draft's `pension` decision and component, consistent PostgreSQL read-only snapshot, exact authorized decision amount and coefficient accepted for **that decision version and option**. No `ManualPensionSource` or conversion destination is created or impersonated.

Proposed `base_amount_representation`: `{representation_kind:"exact_ratio",numerator:"<allocated NIS with 2 decimals>",denominator:"<exact positive admitted factor>"}`. Source identity shall use a **new namespace** `scenario-decision:<scenario_id>:<decision_id>`, never `manual:` or `conversion:`. This kind is not currently in the target executor's accepted set; independent review must approve the smallest canonical extension to the existing executor's allowed kind contract. Pure ratio representation already exists; do not write a duplicate formula.

Note: scenario drafts may be edited/cloned. Stable source string is only routing; source authority requires all fingerprints and revisions to match. No permission from self-provided `basis_authority_ready` flags.

## Gate 2 — Fingerprint canonical preimages (TECHNICAL_WIRING)

*Proposed schema version* `SCENARIO_PENSION_AUTHORITY_V1`, **not yet supported by code**. Every hash: `SHA256(canonical_json(preimage))`. For compatibility use the **exact existing canonical serializer and hashing conventions**, with explicit fixed version tags; independent review must inspect the precise serializer at `pension_monthly_basis_service.canonical_bytes` versus `planning_input_service.fingerprint` before approving cross-service equality. Avoid speculative compatibility.

- `monthly_semantic_preimage`: `{contract_version, authority_kind:"scenario_decision_balance_ratio",base_amount_representation:{representation_kind:"exact_ratio",numerator,denominator},base_amount_effective_date}`. This extends the current semantic contract in the same owner.
- `monthly_source_preimage`: `{contract_version,source_id,source_kind:"scenario_decision",client_id,scenario_id,scenario_version,decision_id,decision_revision,source_product_id,source_component_id,component_code,source_product_version,source_fingerprint,amount,selected_coefficient:{source_level,exact_value,original_representation,normalization_id,catalog_version,catalog_hash,row_id,insurer,program,policy_edition,tranche,option,effective_date,evidence_ref,manual_revision,acknowledgment_id},monthly_semantic_fingerprint}`. Fields either verified from the current database snapshot or explicitly null when inapplicable; missing mandatory selected-source evidence blocks.
- `temporal_semantic_preimage`: `{contract_version,temporal_kind:"none",annual_rate:"0",temporal_origin_date,retirement_target_date,base_amount_effective_date}` pending owner decision. **Do not claim it is compatible with current `pension_temporal_authority_service` without inspecting actual code.**
- `temporal_source_preimage`: `{contract_version,source_id,client_id,scenario_id,scenario_version,decision_id,decision_revision,monthly_source_fingerprint,temporal_semantic_fingerprint,temporal_policy_revision,temporal_origin_date,retirement_target_date}` pending owner decision and canonical source-owner acceptance.
- `planning_calculation_input_preimage`: `{contract_version,client_id,scenario_id,scenario_version,decision_id,decision_revision,manifest_fingerprint,partition_fingerprint,source_fingerprint,source_product_version,source_component_id,component_code,amount,action:"pension",source_id,monthly_semantic_fingerprint,monthly_source_fingerprint,temporal_semantic_fingerprint,temporal_source_fingerprint,retirement_target_date,ruleset_digest,permission_admission_revision,professional_admission_revision}`.

These are **candidate preimage definitions**, not existing computed five fingerprints. The independent reviewer must compare all candidate field sets with actual existing origin contracts, decide whether inclusion/exclusion of dates from semantic fingerprints is valid, and document exact producer/consumer identity equality. A full snapshot must be sourced from a single DB owner transaction with `REPEATABLE READ READ ONLY`. Recomputed current fingerprints and supplied previously accepted ones must match at execution.

## Gate 3 — temporal semantics (PROFESSIONAL_DECISION, STILL OPEN)

**Proposed minimal owner option**: treat the saved allocation as a **current nominal amount**, value date equal to the saved balance's verified source-effective date; `temporal_kind=none`, `annual_rate=0`, growth factor 1. Display *"אומדן קצבה חודשי ברוטו על בסיס הצבירה הנוכחית, ללא תשואה או הפקדות עתידיות; אינו תחזית ליתרה במועד הפרישה"*. The retirement target determines applicable coefficient age/option/date only; do not describe this as accumulated capital forecast or guaranteed payable pension. Alternative involving returns is OUT OF SCOPE. **Requires explicit product-owner confirmation before contract adoption**. If factual valuation date is absent, block rather than assume today.

## Gate 4 — single planner admission (PROFESSIONAL_DECISION, STILL OPEN)

One authenticated planner acknowledgment for a specific `(client_id,scenario_id,scenario_version,decision_id,decision_revision,product/component/source fingerprint,selected source/factor,option,target date,temporal policy revision,ruleset/permission identity)`. Manual entry is exact positive decimal, referenced insurer quotation/contract document or clearly labelled unsupported professional assumption, author, original units and payer/survivor conditions, effective date and reason. Strict version invalidation on change/clone. SC-06A documentary acknowledgment **does not** grant this permission; do not retrofit SC-06B or multistage approvers. Reviewer must decide durable provenance record and DB read-snapshot integration, not invent a current approval authority.

## Gate 5 — result envelope (CALCULATION_CONTRACT)

Proposed `STAGE6_SINGLE_PENSION_DECISION_ESTIMATE_V1`:

Blocked: `{schema_version,client_id,scenario_id,scenario_version,decision_id,decision_revision,result_state:"BLOCKED",blockers:[...],execution_allowed:false,coefficient_provenance:null,monthly_basis:null,pte_result:null}`.

After **future independent acceptance AND separately authorized implementation**, ready result will bind same IDs, current five fingerprints, coefficient source, monthly/temporal policy, PTE result and result fingerprint. Show only gross nominal estimated monthly pension with source grade and no tax / capital / NPV / gap / portfolio aggregation. Nonmatching PTE `source_id`, version, five hashes, option or decision => BLOCKED. Must never call PTE when a blocker exists; no stale cache success.

## Gate 6 — phased coefficient admission (SOURCE_EVIDENCE)

Phase 1 **proposal**: only manual planner-confirmed factor, decision-specific and fail-closed. No company/generic auto lookup. Later separate specific-company source catalogs and V1 generic planning assumptions may be admitted after deterministic row selection, applicability and provider/fund mapping. Synthetic 200, inferred sex/age/year or max-row-id are always blocked. Preserve distinct original policy factor vs rider or later savings layer, minimum guaranteed payments and surviving-spouse 60% option. Historical per-10000 inversions need exact units and approved conversion.

## No closure claim

This proposal narrows the missing authority, preimage, temporal and professional gates identified by Work. **It is not a repaired runnable contract yet.** In particular existing PTE will reject `scenario_decision_balance_ratio`, scenario planning source is absent, and temporal preimages are not proven compatible. One focused independent **READ ONLY** review of this specific amendment must issue `PASS_DESIGN_ONLY` or `BLOCKED` before any code work; owner must decide Gate 3 and Gate 4 scope. Prior approval flags all remain NOT_AUTHORIZED. No CI or production changes.
