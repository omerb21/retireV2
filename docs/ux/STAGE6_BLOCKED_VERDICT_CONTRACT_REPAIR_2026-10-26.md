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
- `temporal_semantic_preimage`: `{contract_version,temporal_kind:"none",annual_rate:null,temporal_origin_date,retirement_target_date,base_amount_effective_date}` pending owner decision. **Do not claim it is compatible with current `pension_temporal_authority_service` without inspecting actual code.**
- `temporal_source_preimage`: `{contract_version,source_id,client_id,scenario_id,scenario_version,decision_id,decision_revision,monthly_source_fingerprint,temporal_semantic_fingerprint,temporal_policy_revision,temporal_origin_date,retirement_target_date}` pending owner decision and canonical source-owner acceptance.
- `planning_calculation_input_preimage`: `{contract_version,client_id,scenario_id,scenario_version,decision_id,decision_revision,manifest_fingerprint,partition_fingerprint,source_fingerprint,source_product_version,source_component_id,component_code,amount,action:"pension",source_id,monthly_semantic_fingerprint,monthly_source_fingerprint,temporal_semantic_fingerprint,temporal_source_fingerprint,retirement_target_date,ruleset_digest,permission_admission_revision,professional_admission_revision}`.

These are **candidate preimage definitions**, not existing computed five fingerprints. The independent reviewer must compare all candidate field sets with actual existing origin contracts, decide whether inclusion/exclusion of dates from semantic fingerprints is valid, and document exact producer/consumer identity equality. A full snapshot must be sourced from a single DB owner transaction with `REPEATABLE READ READ ONLY`. Recomputed current fingerprints and supplied previously accepted ones must match at execution.

## Gate 3 — temporal semantics (PROFESSIONAL_DECISION, STILL OPEN)

**Proposed minimal owner option**: treat the saved allocation as a **current nominal amount**, value date equal to the saved balance's verified source-effective date; `temporal_kind=none`, `annual_rate=null`, growth factor 1. Display *"אומדן קצבה חודשי ברוטו על בסיס הצבירה הנוכחית, ללא תשואה או הפקדות עתידיות; אינו תחזית ליתרה במועד הפרישה"*. The retirement target determines applicable coefficient age/option/date only; do not describe this as accumulated capital forecast or guaranteed payable pension. Alternative involving returns is OUT OF SCOPE. **Requires explicit product-owner confirmation before contract adoption**. If factual valuation date is absent, block rather than assume today.

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

## Code-grounded correction after closer reading (2026-10-26)

The previous proposal's `annual_rate:"0"` for `temporal_kind:"none"` is **incorrect**. The existing executor (`pension_target_date_execution_service.py:188-194`) requires **`annual_rate is None`** for `none`; the owner `pension_temporal_basis_service.semantics` likewise rejects any non-null annual rate for `none`. Use `annual_rate:null`; the executor internally applies growth factor 1. No silent fallback.

**Canonical temporal semantic preimage is now verified directly in code**, `pension_temporal_basis_service.semantic_fingerprint(kind,origin,annual_rate,rate_basis)`: `{contract_version:"canonical-pension-temporal-indexation-semantic-v1",temporal_authority_kind:"none",temporal_origin_date:"<verified source valuation date>",annual_rate:null,rate_basis:null}`. Its fingerprint is SHA-256 of `pension_monthly_basis_service.canonical_bytes` on that dictionary. **It must NOT include `retirement_target_date` or `base_amount_effective_date` as extra keys**, contrary to the original provisional candidate: the target is separately represented by current planning/execution identity. The original paragraph above labelled candidate is superseded by this code-grounded finding.

**Canonical temporal source preimage for existing factual sources is NOT transferable**. `pension_temporal_basis_service.manual` binds `manual_pension_source_id`, lifecycle, raw indexation fields and `temporal_authority_explicit`. The scenario authority must adopt an explicitly different scenario-owned provenance and `source_kind`, while preserving the registered semantic fingerprint layout. Reuse the canonical serializer, not a second JSON convention.

**Canonical monthly semantic preimage verified**: `pension_monthly_basis_service.semantic(kind,representation,effective_date)` is `{contract_version:"canonical-pension-monthly-amount-basis-semantic-v1",authority_kind:"scenario_decision_balance_ratio",base_amount_representation:{representation_kind:"exact_ratio",numerator:"<amount .2f>",denominator:"<exact admitted factor>"},base_amount_effective_date:"<verified date>"}`. The proposed new kind requires explicit addition to the existing PTE's allowed authority kinds. No accepted extension exists today.

**Substantive unresolved remaining:** scenario-specific full source preimage, planning `planning_calculation_input_fingerprint` origin and current snapshot producer must be designed and independently accepted against their **real** owners; merely naming the five preimages in this document does not wire them. The static valuation policy, single planner admission and decision-owned source are proposed decisions, **not approved by the user yet**.

**Correction to unit tests proposed:** `none` with `annual_rate="0"` must BLOCK; `none` with `annual_rate=null` can pass the annual-rate shape gate but still requires ready, admitted source+temporal fingerprint and planning identities. The corresponding test must not be mistaken for an authorization of financial execution.


## Concrete code-derived binding review: election, decision and planning identity (2026-10-26)

This adds source facts, **not** authorization. Inspected: `app/models/scenario_draft.py`, `app/models/scenario_draft_pension_election.py`, `scenario_coefficient_review_context_service.py`, `planning_input_service.py`, `professional_source_snapshot_service.py` and `pension_target_date_execution_service.py`.

1. **There is no `ScenarioDraftDecision.decision_version` field.** `ScenarioDraftDecision` has `decision_id`, `scenario_id`, amount, effective_date, reviewed product version, source fingerprint and ruleset/preview facts; its parent owns an incrementing `ScenarioDraft.version` and a `ScenarioDraftRevision` per version. Consequently provisional `decision_revision` in the proposal is not an existing fact and MUST NOT be generated as a pretend persistent field. Candidate binding for now: `scenario_version` + `decision_id` + manifest/source fingerprints + the selected coefficient/option acknowledgment revision. Independent review must determine whether this is sufficient or whether a new dedicated revision is indispensable.
2. **Election fact source exists but is only advisory.** `ScenarioDraftPensionElection` has `scenario_id`, `decision_id`, `scenario_version`, `pension_start_date`, `target_year`, `survivors_option`, `spouse_age_diff`, `coefficient_selection in {'catalog_candidate','manual_review_required'}`, `company_name`, `option_name`; it has **no factor value, manual evidence reference, approval, annuity/fund category, policy version or temporal policy**. The exact election identity and `election_fingerprint` preimage already exist in `scenario_coefficient_review_context_service.derive_documentary_review_context()`. Reuse them in future acceptance; do not write a competing option-fingerprint recipe.
3. **The existing documentary review owner is narrower than financial admission.** The context service builds trusted `manifest_fingerprint`, `inventory_fingerprint`, `election_fingerprint`, `source_fingerprint`, checking DOB/sex and product version in one database snapshot. Its `SC-06A` reviewer is documentary and explicitly returns `MATCHED_NOT_AUTHORIZED`. New professional factor selection should bind the same existing identity, plus exact factor source/value and temporal policy, with its own admitted, immutable revision; never promote the documentary review row to calculation authority.
4. **There are two different existing fingerprint serializations to reconcile.** `planning_input_service.fingerprint` uses `json.dumps(serialize(...),sort_keys=True,ensure_ascii=False,separators=(',',':'))`; basis/temporal/PTE use `pension_monthly_basis_service.canonical_bytes`. Neither identical canonicalization nor byte-level equality may be assumed for every allowed value. A future scenario planning producer must explicitly choose the existing owner-specific fingerprint contract and demonstrate producer/consumer equality with Unicode/control-string fixtures.
5. **Existing factual planning identity is not a scenario planning identity.** `planning_input_service.derive` computes `planning_input_fingerprint` from factual source state, client, decision and income resolutions. It builds `pension_inputs` exclusively from factual pension sources. An independently admitted scenario planning source must be **derived** within the existing planning authority (or accepted narrow canonical extension), not appended to arbitrary client-supplied `pension_inputs` nor wrapped as a `manual:` source. The PTE's five hashes must come from actual matching producers.
6. **Temporal and valuation date are different from elected pension start.** `ScenarioDraftDecision.effective_date` is a proposed action date, not automatically the factual valuation date of the allocated balance. The election's `pension_start_date` is an intended payout date; neither can stand in as a factual balance-as-of date without source provenance. The owner-proposed no-growth option is valid mathematically but remains professionally UNDECIDED until explicitly approved. Lack of verified valuation date => BLOCK.
7. **The reviewed code cannot supply a success envelope now.** `scenario_calculation_admission_service.assess` still blocks `PERMISSION_NOT_ADMITTED`, `PROFESSIONAL_ELIGIBILITY_NOT_EVALUATED`, `TAX_NOT_EVALUATED` for each decision; `scenario_annuity_coefficient_assessment_service` always blocks. Distinguish tax-excluded scenario *scope* from permission/eligibility: ignoring a tax code does not automatically approve retirement eligibility.

### Owner decision and acceptance still open

- Confirm or reject *no-growth static current-balance pension illustration*, with exact disclosure and valuation date sourced from factual evidence.
- Confirm or reject *one authenticated planner factor admission per decision and scenario version*, with a mandatory factor source/option reference and explicit invalidation.
- Request one **READ ONLY** independent review of this actual code-derived contract, especially the non-existent `decision_revision` field, two serializer contracts, election-identity reuse and valuation-date evidence. Any mandatory extra DB field or canonical extension requires a separate owner-authorized implementation slice. No code change from this update.


## Valuation-date admission correction: existing product statement date (2026-10-26)

**Direct code facts:** `PensionProduct.statement_date` is a nullable DB date on the existing source product. `ScenarioDraftDecision.effective_date` is a separate proposed action date. `ScenarioDraftPensionElection.pension_start_date` is intended annuity start. `ScenarioDraftService._source_evidence()` hashes product ID, version, product type/source identity and the component balance; **does not directly hash `statement_date`**. `scenario_input_manifest_service.SOURCE_FIELDS` is a strict closed set that likewise excludes statement date; changing that set to fit Stage 6 would disturb the previously accepted inert Manifest schema and is **not** recommended in this package.

**Minimal proposed date authority (requires independent design approval):**
- Read `PensionProduct.statement_date` from the same validated `PensionProduct` selected by `client_id`, `source_product_id` and source version, inside the same PostgreSQL `REPEATABLE READ READ ONLY` snapshot as decision, component, election, coefficient and professional admission. Do not trust dates supplied by frontend.
- Require `statement_date IS NOT NULL` for static present-balance illustration. Reject if `statement_date > pension_start_date` or `statement_date > retirement_target_date`, if applicable. If component balance date granularity differs from product statement date, require an explicit source proof; product `statement_date` is **not automatically sufficient** for all derived balances.
- Bind `statement_date` in the *new* scenario-specific **monthly source fingerprint preimage**, temporal source fingerprint and scenario planning input identity, beside product version, balance, normalized factor, option and approval. Set `base_amount_effective_date=statement_date` and `temporal_origin_date=statement_date` only once the same-time basis is established. This ensures date changes invalidate authority even if a source-product version is accidentally unchanged.
- `temporal_kind="none"`, `annual_rate=null`, `rate_basis=null` are code-valid *shapes*, not an owner-approved no-growth policy. The payout date only selects age/option applicability; the result is a static current-balance illustration, not a forecast.
- A new derived scenario identity may combine current accepted Manifest fingerprint with separately recomputed product statement-date evidence. Do not extend Manifest `SOURCE_FIELDS` or fabricate a factual pension source. This keeps historical SC-03 contracts inert and intact.

**Test obligations:** null date; future date; date after pension start; changed date without balance/version mutation; stale date-specific manual approval; different date in source and temporal basis; source product reused across clone; source value and payment target unexpectedly mixed. All BLOCK before executor access if source date authority is unresolved.

**Scope note:** If valuation-date policy is not explicitly accepted by owner and independently reviewed, `STAGE6_IMPLEMENTATION`, coefficient lookup and financial execution remain `NOT_AUTHORIZED`.


## Planning-target identity exact owner and no-regression boundary (2026-10-26)

Verified from `retirement_target_service.extend_read` and `planning_input_service.derive`:
- Existing **factual** `planning_calculation_input_fingerprint` is computed as `planning_input_service.fingerprint({contract:"canonical-retirement-target-date-authority-v1",planning_input_fingerprint,retirement_target_decision_fingerprint,current_target_reference_fingerprint,retirement_target_ready,retirement_target_blockers})`.
- `retirement_target_decision_fingerprint` hashes `{contract:"canonical-retirement-target-date-authority-v1",client_id,retirement_target_date,decision_provenance:"explicit_professional_retirement_target_date"}`.
- The planning input hash itself is based on factual professional source snapshot, incomes/expenses/timings, client, planning base decision and pension income resolutions, **not** the hypothetical scenario decision. A copied factual planning fingerprint does NOT bind the saved scenario's selected amount, coefficient, election, version or source.
- The existing target-reference fingerprint can change with factual client/timing or canonical pension-source facts. `retirement_target_service.references()` does not treat `ScenarioDraftPensionElection.pension_start_date` as factual canonical pension source. Never silently reinterpret it as one.
- The proposed independent scenario route must derive a new, explicitly named scenario planning input identity **within canonical planning ownership** from the existing factual planning identity PLUS verified saved decision manifest, decision-specific source snapshot, selected coefficient/acknowledgment and election source. It must explicitly name whether target is the canonical `PlanningInputDecision.retirement_target_date` or scenario election `pension_start_date`; if these disagree, BLOCK rather than choose a hidden fallback. The independent reviewer must assess the smallest compatible canonical extension to PTE. Do not change the existing factual planning fingerprint in place.

### Target/election negative evidence
- Same scenario amount but updated `PlanningInputDecision` or target-reference facts => stale planning identity; prior approval invalid.
- Altered election pension start without scenario version change => recompute `election_fingerprint` from DB; previous admission invalid.
- An independently chosen scenario start date conflicting with global retirement target => explicit conflict blocker until rule adopted, not a silent current-year substitution.
- Inconsistent serializer bytes between `planning_input_service.fingerprint` and `pension_monthly_basis_service.canonical_bytes` => derive each fingerprint only using its canonical owner, with cross-checkable fixtures.

### Do-not-overclaim
The code proves a safe closed basis for the *existing factual target*, not a scenario planning result. This completes the **code evidence reconciliation** for the specific fingerprint-origin gap but does **not** close Stage 6's CALCULATION_CONTRACT or PROFESSIONAL_DECISION blockers. No implementation, CI or deploy authorized.


## Product-owner delegated decisions — 2026-10-26 (binding product scope, not technical acceptance)

The product owner explicitly authorized the central development manager to make the remaining technical/product sequencing decisions without repeated approval requests, and explicitly approved the initial no-growth approach. The owner additionally requires **future CPI indexation of the capital balance up to withdrawal date**. This is deferred, not abandoned, and Stage 6 V1 must neither implicitly apply it nor falsely state that the static estimate includes it.

**Decision D6-01 | Initial time semantics: APPROVED.** Use the *existing reported/current nominal* component balance as the capital base, as of verified `PensionProduct.statement_date`; no automatic CPI, returns or future contributions. `temporal_authority_kind=none`, `annual_rate=null`, `rate_basis=null`. Calculate gross planning monthly estimate using selected pension option/date coefficient; explicit label (Hebrew): `אומדן קצבה לפי הצבירה המדווחת, ללא הצמדה למדד, תשואה או הפקדות עד מועד המשיכה. סכום הקצבה בפועל עשוי להשתנות.` Missing or untrusted balance date => BLOCK. CPI until withdrawal will be a **separate scoped later package** with an authoritative date/index source and tests; no fixed manual nominal growth rate shall masquerade as CPI.

**Decision D6-02 | Planner coefficient admission: APPROVED IN PRINCIPLE by delegated manager.** In practical terms this is one deliberate confirmation when the retirement planner enters/chooses the coefficient used for *one pension decision* in one saved scenario. It is not another person, board or multiple approvals. UI should let the planner see/edit exact positive decimal factor and pension/survivor option, source reference/evidence and estimated result provenance. Changing the factor, option, amount, source, scenario version or date invalidates the old confirmation and requires re-confirmation. The technical admission record and DB implementation remain subject to independent design acceptance. **Phase 1 may be manual-confirmed coefficients only**, while automated V1 generic / insurer lookup remains blocked until safe selectors exist. This does not abandon eventual specific-insurer tables.

**Decision D6-03 | Canonical integration: delegated manager chooses smallest safe extension, not a new engine.** Adopt a proposed `scenario_decision_balance_ratio` authority for a DB-verified hypothetical scenario decision with `exact_ratio(amount,admitted_factor)`; do not represent it as a factual manual pension source. Bind current source statement date and proposed payout date, and all scenario/election/selected-factor evidence into five canonical authority identities. A separate independent read-only reviewer must inspect the extension and explicitly pass its **design** before the manager authorizes code edits. The user is **not** being asked to approve internal fingerprint formats, source IDs, JSON shape, or contract adapter details.

**Target-date policy D6-04 | No silent conflict:** For the single-decision Stage 6 illustration, the decision's current `ScenarioDraftPensionElection.pension_start_date` is the proposed payment/withdrawal target. An unrelated global `PlanningInputDecision.retirement_target_date` must not silently replace it. The independent reviewer must approve how this scenario-target identity is derived, whether PTE requires a narrow canonical planning extension, and how future differences are surfaced; no false reuse of the global factual target fingerprint. Reject invalid chronological combinations. This is a design choice for the scenario estimate, **not** changing global planning target or factual source.

**Governance / boundary:** These decisions close product-choice requests. They do **not** constitute Work independent acceptance or authorization to turn on calculation/lookup. Retain `STAGE_6_IMPLEMENTATION=NOT_AUTHORIZED`, `COEFFICIENT_LOOKUP=NOT_AUTHORIZED`, `FINANCIAL_CALCULATION=NOT_AUTHORIZED`, `SCENARIO_CALCULATION_ADAPTER=NOT_AUTHORIZED`, `PRODUCTION_DEPLOYMENT=NOT_AUTHORIZED` pending the focused independent verdict and a subsequent bounded implementation approval.


## Stage 6 bounded independent re-review, final owner-approved scope (2026-10-26)

The preceding historical candidate preimages and open-owner-decision descriptions are an audit trail; **the latest D6-01 through D6-04 decision section supersedes earlier "owner approval pending" statements**. No previous hypothetical field named `decision_revision` or `annual_rate:"0"` may be treated as an existing code field or valid temporal-none rate. The earlier `pension_temporal_authority_service` reference is incorrect; canonical owner is `pension_temporal_basis_service`.

**Scope locked:** one saved pension decision only; exact admitted manually entered factor in phase 1; one authenticated planner action; static reported capital at proven product statement date, no CPI/return/new contributions; election pension start is scenario retirement target; dedicated scenario authority `scenario_decision_balance_ratio`; no factual source impersonation. Later CPI-to-withdrawal is an explicit deferred separate package. Future company-specific lookup is desired but not a prerequisite for manual V1.

**Reviewer tasks (read-only at actual current HEAD):**
1. Independently verify every asserted existing owner and precise canonical serializer, including `scenario_snapshot_candidate_service`, `scenario_coefficient_review_context_service`, `pension_monthly_basis_service`, `pension_temporal_basis_service`, `planning_input_service`, `retirement_target_service`, `pension_target_date_execution_service` and `ScenarioDraftPensionElection`.
2. Decide whether this *bounded design* fully specifies a legitimate producer of `scenario_decision_balance_ratio` from DB-derived allocation/factor/date, its deterministic `scenario-decision:` source ID, current five producer-owned hashes, and one-source PTE planning result. If not, specify exact remaining preimage/owner or persistence additions, distinguishing technical design completion from already-existing code.
3. Inspect source-balance valuation: `PensionProduct.statement_date` is nullable and is absent from current draft source digest. Is same-snapshot derived explicit source-date binding sufficient without changing inert SC-03 manifest? Reject missing/stale source date.
4. Verify global planning target does not silently override election `pension_start_date`; verify no false derivation from current factual `planning_calculation_input_fingerprint`.
5. Verify decision-scoped planner admission is not SC-06A: evidence and acknowledgment must bind the factor, option, source/date, scenario version, election fingerprint and actor. Existing `ScenarioDraftDecision` has no decision revision; don't silently invent it.
6. Specify exact executable blockers and fail-closed result envelope, including when all five current/supplied fingerprints can be generated and compared. Confirm no PTE call occurs before admission.
7. Issue a definitive `PASS_DESIGN_ONLY` or `BLOCKED` **for contract completeness**, not claim code is implemented. For BLOCKED, give only the smallest unresolved technical additions. Do not reopen owner D6 decisions.

**Reviewer access:** READ ONLY; no CI, no code changes, no migrations, no PR/merge/deploy. Owner's delegation does not waive independent technical acceptance. Existing authorization flags remain NOT_AUTHORIZED until separate acceptance.


# NORMATIVE ADDENDUM N1 — Stage 6 Phase-1 schema contract (2026-10-26)

**Precedence:** This addendum supersedes all prior "candidate" preimages, draft success-envelope prose, invented \`decision_revision\`, and "owner decision pending" statements in this document. Product decisions D6-01–D6-04 stand. This specifies **future** code boundaries and is NOT proof that producers exist today. Design independent PASS remains required before implementation. New schema constants below are proposed binding names, not existing Python constants.

## N1.0 Closed conventions and source snapshot

- One PostgreSQL REPEATABLE READ READ ONLY snapshot, owned by existing \`scenario_snapshot_candidate_service.build_manifest_candidate_snapshot\` and a narrowly reviewed internal extension callback. Never accept user-provided manifest, fingerprints, factor admission, planner identity or source date as authority.
- Required DB facts: client ID, active draft scenario/version, one decision ID/action=\`pension\`/amount (>0, canonical NIS two decimals), source product ID/version, component ID/code and sufficient balance, product \`statement_date\` (verified source-valuation date), current source digest and manifest/partition digests, saved election for same scenario version and target pension date, option fingerprint, one authenticated approval and its revision.
- Every identifier is non-empty and bounded by existing DB type, every date is canonical YYYY-MM-DD, every factor is positive finite decimal string normalized without exponent or trailing redundant zeros by \`pension_monthly_basis_service.factor\`. No floats, null for non-null fields, user-supplied version, duplicated source, default date or factor. Statement date must not postdate election start. Missing source-date provenance blocks.
- Exact source ID: \`scenario-decision:\${scenario_id}:\${decision_id}\`. IDs are DB-owned and cannot contain colon; this delimiter constraint must be validated or the source ID encoded injectively with an explicitly versioned encoding. **Chosen encoding:** UTF-8 percent-encoding of each ID's colon and percent using uppercase %3A and %25, in that order (percent first then colon), and reject malformed ID length. Format \`scenario-decision:<escaped-scenario-id>:<escaped-decision-id>\`; collision checks are mandatory. Do not reuse \`manual:\` or \`conversion:\`.
- Coefficient phase-1 is \`MANUAL_PROFESSIONAL_OVERRIDE\` exclusively; neither generic nor company lookup is attempted. It may be clearly tagged \`INSURER_QUOTE\`, \`POLICY_CONTRACT\` or \`PLANNER_ASSUMPTION\` as evidence type; the latter is explicitly an assumption, not a guaranteed insurer benefit.
- All hashes lowercase 64-character hex SHA-256. **Closed field sets**: object preimage has exactly the keys enumerated below; arrays (if any) have documented order. Null is a JSON null, not an absent key. Field-name alphabetical ordering for canonical JSON is established by the respective canonical owner. Each candidate is recomputed from source database facts, not client-supplied hash claims. All recognized evidence and labels are strings except strict integer IDs/versions where indicated and boolean state.

## N1.1 Five authoritative fingerprints — closed schemas

**Hash M1 (monthly semantic).** Owner \`pension_monthly_basis_service.semantic\`; serializer \`pension_monthly_basis_service.canonical_bytes\`; contract tag \`canonical-pension-monthly-amount-basis-semantic-v1\`. Exactly:
\`\`\`json
{"contract_version":"canonical-pension-monthly-amount-basis-semantic-v1","authority_kind":"scenario_decision_balance_ratio","base_amount_representation":{"representation_kind":"exact_ratio","numerator":"1000000.00","denominator":"200"},"base_amount_effective_date":"2026-09-30"}
\`\`\`
Example strings are illustrative, never defaults. \`numerator\` = DB decision amount formatted 2 decimals; \`denominator\` = approved factor exact string; effective date = verified product statement date. All non-null. Reuse existing \`semantic(kind,representation,effective_date)\` exactly with new kind, do not insert scenario IDs here.

**Hash M2 (monthly source).** Owner: approved **scenario branch** inside \`pension_monthly_basis_service\`; serializer \`canonical_bytes\`; contract tag \`canonical-scenario-pension-monthly-source-v1\`. Exactly this closed-key preimage (ordered here semantically; canonical serializer sorts keys):
\`\`\`
{
 "contract_version":"canonical-scenario-pension-monthly-source-v1",
 "source_id":"scenario-decision:<escaped-scenario-id>:<escaped-decision-id>",
 "source_kind":"scenario_decision",
 "client_id":1,"scenario_id":"...","scenario_version":1,"decision_id":"...",
 "manifest_fingerprint":"<sha256>","partition_fingerprint":"<sha256>",
 "source_product_id":"...","source_product_version":1,
 "source_component_id":"...","component_code":"...",
 "source_fingerprint":"<sha256>","amount":"1000000.00",
 "statement_date":"2026-09-30",
 "election_fingerprint":"<sha256>",
 "professional_admission_revision":1,
 "professional_admission_fingerprint":"<sha256>",
 "monthly_semantic_fingerprint":"<M1>"
}
\`\`\`
All fields required and non-null. \`source_fingerprint\` is existing DB-derived draft source digest, not the new M2. A change to source valuation date, balance, coefficient, option, admission or draft version changes M2. Coefficient value/source/option are covered through the admission fingerprint and M1; source/election context is covered by existing underlying digests.

**Hash T1 (temporal semantic).** Owner \`pension_temporal_basis_service.semantic_fingerprint\`; serializer the same \`pension_monthly_basis_service.canonical_bytes\`; contract tag \`canonical-pension-temporal-indexation-semantic-v1\`. Exactly:
\`\`\`json
{"contract_version":"canonical-pension-temporal-indexation-semantic-v1","temporal_authority_kind":"none","temporal_origin_date":"2026-09-30","annual_rate":null,"rate_basis":null}
\`\`\`
All keys mandatory; exactly two JSON nulls. Date is verified statement date. \`none\` means factor 1, no CPI/indexation, interest or future contribution. Never send \`"0"\` instead of null. Retirement target is not embedded in T1.

**Hash T2 (temporal source).** Owner proposed scenario-owned extension inside \`pension_temporal_basis_service\`; serializer \`canonical_bytes\`; tag \`canonical-scenario-pension-temporal-source-v1\`. Exactly:
\`\`\`
{
 "contract_version":"canonical-scenario-pension-temporal-source-v1",
 "source_id":"scenario-decision:<escaped-scenario-id>:<escaped-decision-id>",
 "source_kind":"scenario_decision","client_id":1,
 "scenario_id":"...","scenario_version":1,"decision_id":"...",
 "statement_date":"2026-09-30","retirement_target_date":"2027-09-30",
 "monthly_source_fingerprint":"<M2>","temporal_semantic_fingerprint":"<T1>",
 "professional_admission_fingerprint":"<sha256>"
}
\`\`\`
No null fields. Target is election's pension start; it cannot precede statement date. This new source hash is **not** \`manual()\`'s factual source hash.

**Hash P1 (scenario planning calculation input).** Owner proposed \`planning_input_service.scenario_decision_calculation_identity\` (canonical extension, not new parallel producer); serializer **\`planning_input_service.fingerprint\`**, which applies \`serialize\` and sorted compact JSON; tag \`canonical-scenario-pension-planning-calculation-input-v1\`. Exactly:
\`\`\`
{
 "contract":"canonical-scenario-pension-planning-calculation-input-v1",
 "client_id":1,"scenario_id":"...","scenario_version":1,
 "decision_id":"...","source_id":"scenario-decision:<escaped-scenario-id>:<escaped-decision-id>",
 "manifest_fingerprint":"<sha256>","partition_fingerprint":"<sha256>",
 "source_fingerprint":"<sha256>","statement_date":"2026-09-30",
 "amount":"1000000.00","action":"pension",
 "election_fingerprint":"<sha256>",
 "retirement_target_date":"2027-09-30",
 "monthly_semantic_fingerprint":"<M1>","monthly_source_fingerprint":"<M2>",
 "temporal_semantic_fingerprint":"<T1>","temporal_source_fingerprint":"<T2>",
 "professional_admission_revision":1,
 "professional_admission_fingerprint":"<sha256>",
 "ruleset_digest":"<sha256>",
 "permission_admission_fingerprint":"<sha256>"
}
\`\`\`
All fields non-null, \`ruleset_digest\` and permission admission must be verified **current approved** evidence from existing source/permission owner. A preview ID is not permission; if no source of a current permission-admission fingerprint is accepted in reviewed code, P1 is BLOCKED rather than fabricated. This P1 is distinct from factual \`retirement_target_service.extend_read\`'s \`planning_calculation_input_fingerprint\`, which must remain unchanged. \`source_id\`, target, scenario version and M1/M2/T1/T2 enforce specific decision binding. The planning owner is the only writer/producer of this hash; PTE consumes and compares, never creates authority from a supplied fingerprint.

**Integer types**: \`client_id\`, \`scenario_version\`, \`source_product_version\`, \`professional_admission_revision\` are JSON integers >0. Everything else above is a string except T1 nulls. The five hash preimages have no optional keys. Any literal \`<...>\` is a placeholder that must be replaced with a current validated fact; it cannot enter production.

## N1.2 One-source planning result / PTE call

Contract \`SCENARIO_PENSION_PLANNING_RESULT_V1\`, owned by canonical planning extension and derived inside the single DB snapshot. Closed top-level key set:
\`\`\`
{
 "contract_version":"SCENARIO_PENSION_PLANNING_RESULT_V1",
 "client_id":1,"scenario_id":"...","scenario_version":1,"decision_id":"...",
 "planning_calculation_input_fingerprint":"<P1>",
 "retirement_target":{"retirement_target_date":"2027-09-30","retirement_target_ready":true},
 "pension_inputs":[{
   "source_id":"scenario-decision:<escaped-scenario-id>:<escaped-decision-id>",
   "pension_start_date":"2027-09-30",
   "currency":"ILS",
   "monthly_amount_basis":{
     "contract_version":"canonical-pension-monthly-amount-basis-v1",
     "source_id":"scenario-decision:<escaped-scenario-id>:<escaped-decision-id>",
     "source_kind":"scenario_decision",
     "authority_kind":"scenario_decision_balance_ratio",
     "base_amount_representation":{"representation_kind":"exact_ratio","numerator":"1000000.00","denominator":"200"},
     "base_amount_effective_date":"2026-09-30",
     "basis_authority_ready":true,"basis_blockers":[],
     "base_amount_semantic_fingerprint":"<M1>","base_amount_source_fingerprint":"<M2>"
   },
   "temporal_authority":{
     "contract_version":"canonical-pension-temporal-indexation-basis-v1",
     "source_id":"scenario-decision:<escaped-scenario-id>:<escaped-decision-id>",
     "source_kind":"scenario_decision","temporal_authority_kind":"none",
     "temporal_origin_date":"2026-09-30","annual_rate":null,"rate_basis":null,
     "temporal_authority_ready":true,"temporal_blockers":[],
     "temporal_semantic_fingerprint":"<T1>","temporal_source_fingerprint":"<T2>"
   }
 }]
}
\`\`\`
The source array has exactly one item and its identity must match the addressed saved pension decision, never an injected factual \`manual:\` or \`conversion:\` source. All fields mandatory; \`basis_blockers\` and \`temporal_blockers\` are empty arrays in READY, null permitted only where shown. \`execution_allowed\` is NOT a caller-controlled input field. This new source authority kind must be added through **separate approved canonical PTE contract change**; present PTE rejects it.

Prior to calling \`execute_from_planning_result\`, require current accepted professional and permission admission, exact source/election/date and all five DB-produced fingerprints; then pass P1/M1/M2/T1/T2 as \`supplied_...\` exactly. PTE's current identity comparison proves producer-consumer equality *only if* planning snapshot genuinely owns and recomputes them. If unrelated canonical/global retirement target differs, do not override scenario election. Surface \`SCENARIO_GLOBAL_TARGET_CONFLICT\` as decision blocker under this conservative phase-1 policy.

## N1.3 One-planner professional factor admission

Contract \`SCENARIO_PENSION_FACTOR_ADMISSION_V1\`, owned by a **new narrowly scoped persistence row for an authenticated scenario decision** (not SC-06A; requires separately authorized migration after design PASS).

- Unique logical key: \`(client_id,scenario_id,decision_id,admission_revision)\`. Physical row ID may be UUID; only one admitted **current revision** per decision+scenario version is selectable. Append-only immutable rows; revising supersedes old revision rather than mutating history. Transactional CAS checks scenario version, current source/election fingerprints, max revision and currently authenticated planner. Concurrent approvals: one succeeds, other conflicts.
- Closed admission fingerprint preimage \`SCENARIO_PENSION_FACTOR_ADMISSION_FINGERPRINT_V1\`, SHA-256 with **\`pension_monthly_basis_service.canonical_bytes\`**:
\`\`\`
{
 "contract_version":"SCENARIO_PENSION_FACTOR_ADMISSION_FINGERPRINT_V1",
 "client_id":1,"scenario_id":"...","scenario_version":1,"decision_id":"...",
 "admission_revision":1,"manifest_fingerprint":"<sha256>",
 "source_fingerprint":"<sha256>","election_fingerprint":"<sha256>",
 "source_product_id":"...","source_component_id":"...","component_code":"...",
 "amount":"1000000.00","statement_date":"2026-09-30",
 "pension_start_date":"2027-09-30",
 "factor_value":"200","factor_original_representation":"DIVISOR",
 "factor_evidence_type":"PLANNER_ASSUMPTION",
 "factor_evidence_reference":"<nonempty string>",
 "survivors_option":"<current election exact value>","spouse_age_diff":0,
 "payout_option_name":"<nonempty string>",
 "actor_id":"<authenticated session principal>",
 "acknowledged_at_utc":"2026-10-26T17:00:00.000000Z"
}
\`\`\`
All fields required, non-null. \`spouse_age_diff\` may be any bounded integer accepted by original election contract; original factor representation in Phase-1 is \`DIVISOR\` only. Other formats require separate verified normalization. Evidence type enumerated: \`INSURER_QUOTE\`, \`POLICY_CONTRACT\`, \`PLANNER_ASSUMPTION\`; the UI displays each accurately. \`factor_evidence_reference\` and \`payout_option_name\` are nonempty free-form professional notes constrained to safe lengths. Actor ID comes from authenticated server session, not posted input. Exact selected option is bound via election fingerprint and copied details. UTC timestamp uses fixed six fractional digits and Z.
- On clone: copy neither current admission nor its revision/authorization state. New scenario requires new approval. Any change to scenario version, source facts/date, decision amount, factor, election/option, target, current ruleset or permission evidence makes old admission unusable. Maintain immutable record for audit, but return BLOCKED. Do not treat matching SC-06A documentary review as equivalent to admission.

**Important security binding:** because rule/permission changes must invalidate approvals, the actual admission record must additionally bind \`ruleset_digest\` and \`permission_admission_fingerprint\` from current authoritative permission ownership. These are **two mandatory string fields in the closed preimage above**, immediately following \`election_fingerprint\`. An implementation or reviewer must apply this explicit amendment when treating the displayed object as normative. Missing current permission proof -> BLOCK; never invent approval authority from \`permission_preview_id_at_review\`.

## N1.4 Closed result envelopes and fail-closed order

Schema \`STAGE6_SINGLE_PENSION_DECISION_ESTIMATE_V1\`; both states use exactly these top-level keys (null where indicated):
\`schema_version,client_id,scenario_id,scenario_version,decision_id,source_id,result_state,execution_allowed,blockers,coefficient_provenance,professional_admission_fingerprint,planning_calculation_input_fingerprint,monthly_basis_semantic_fingerprint,monthly_basis_source_fingerprint,temporal_semantic_fingerprint,temporal_source_fingerprint,pte_source_execution_fingerprint,pte_source_result_fingerprint,monthly_estimate_gross_ils,retirement_target_date,statement_date,result_fingerprint\`.

- BLOCKED: \`result_state="BLOCKED"\`, \`execution_allowed=false\`, \`blockers\` sorted unique nonempty strings, monetary output and PTE hashes NULL. The five identity fields, provenance and admission fingerprint are null if pre-admission; if formerly available but now stale they MUST also be null rather than displayed as current. Entity IDs may be safely populated from already validated route/DB context. Date fields null unless verified in same snapshot.
- RESULT_READY: \`result_state="RESULT_READY"\`, \`execution_allowed=true\` (**result description, not a preauthorization bit**), \`blockers=[]\`; all IDs, provenance, admission, 5 identity fields, 2 PTE fingerprints, 2 dates and gross estimate string are non-null. \`monthly_estimate_gross_ils\` is PTE \`final_monthly_amount\` and must match PTE result (no recomputation); decimal exactly two digits.
- \`coefficient_provenance\` in READY is exactly \`{source_level:"MANUAL_PROFESSIONAL_OVERRIDE",factor_value:"<canonical exact>",factor_evidence_type:"...",factor_evidence_reference:"...",payout_option_name:"...",admission_revision:<int>}\`. No 'guaranteed' implication from a planner assumption.
- \`result_fingerprint\` is SHA-256 via **\`pension_monthly_basis_service.canonical_bytes\`** of \`{contract_version:"STAGE6_SINGLE_PENSION_DECISION_RESULT_FINGERPRINT_V1",result:<all other closed top-level fields excluding result_fingerprint>}\`. Always present in READY and BLOCKED; all strings and numbers typed as specified. The result is ephemeral/read-only; no new persisted financial result.
- Execution order: validate route/auth -> read fresh authoritative snapshot -> check decision and balance allocation -> verify valuation date/election/target/ruleset/permission -> verify current admission and explicit factor -> canonical five fingerprints -> confirm one-source planning result -> call PTE **once** -> require PTE \`result_state="result_ready"\`, matching source ID, target, all five input identities, nonnull PTE execution/result fingerprints -> construct READY. Any failure before PTE means **zero PTE invocations** and a BLOCKED result. Failure at PTE remains BLOCKED; never reinterpret stale result as ready. No other financial engines, factual writes or auto coefficient lookups.
- Test fixtures require same byte-for-byte hashes across producer/consumer (including Hebrew Unicode, control characters, null, nested dictionary key sort) and changed-value invalidation, historical inverse coefficient units, simultaneous admissions, cloned scenario, source date only edits, target conflicts and forged old approvals.

**Acceptance gate:** reviewer checks all exact field sets and current ownership. The narrow Phase-1 design can pass only when an actual permission-admission owner is identified, or the gate is explicitly narrowed to an accepted professional authorization independent of the existing always-blocked general scenario assessor. No automatic bypass. This addendum itself remains DESIGN ONLY; no code, CI or deployment permitted.
