# Governance v1.2 — Credit-Efficient Lifecycle Amendment Proposal

Status: **PROPOSAL ONLY — NOT ACCEPTED, NOT OPERATIVE**  
Base master: `0f9db6656c9dbbb2aea6f4dc49c367a5dde3245f`  
Supersession target: `RETIREMENT_PLANNING_V2_GOVERNANCE_PROTOCOL v1.1`  
Authority: process only; no business, financial, calculation, security or production authority.

## Problem demonstrated by RTICB V2 / RTDIR

The implementation eventually passed independent acceptance and master closure. It nevertheless required serial WORK returns for implementation rejection, focused correction acceptance, manifest rejection over two unsourced phrases, focused manifest correction audit, and post-merge closure. The latter two mechanical audit gates were individually short but incurred repeated model/session handoffs. The failure was partly inadequate preflight: a prohibited frontend enum, misrouted semantic errors and missing AC-35 tests reached independent review, then an unsupported finding token and PostgreSQL version reached manifest review.

Preserve necessary controls. Reduce avoidable handoffs, re-validation of accepted evidence and unsourced manifest assertions.

## Proposed rules (prospective only)

### 1. One execution owner per implementation package

The implementation owner runs an entire package through implementation, executable verification, contract-compliance preflight and one immutable candidate. No routine "continue" handoffs between intermediate commits. Group related defects into one correction candidate and run focused tests before requesting independent delta acceptance.

### 2. Evidence ledger and machine-verifiable manifest

Before sending an implementation manifest to independent review, the implementation owner must construct a concise evidence ledger keyed by:
- immutable accepted definition and consumer-definition refs, blobs and decision reports;
- accepted implementation HEAD/TREE;
- original independent implementation verdict and closed defect IDs;
- exactly quoted finding tokens *only if explicitly issued* (otherwise use the actual finding text);
- test command/result and source report, without inferred software versions;
- canonical changed-path list from Git compare;
- Alembic/migration and authorization statuses.

Each factual manifest claim must have a traceable evidence source. Reject invented tokens, invented version numbers, unmatched SHAs and surplus path claims locally before publishing the manifest. Existing accepted evidence may be reused when a written impact analysis proves it unaffected; no blanket reruns.

### 3. Risk-tiered audit execution

- **Deep independent acceptance** stays mandatory for a new authoritative definition and new implementation. Scope must include professional semantics, security and transactional ownership where applicable.
- **Delta acceptance** examines corrected findings and their actual regression surface, preserving untouched evidence.
- **Manifest acceptance** is strictly mechanical and may use a lighter model, with a preflight verifier and no semantic reopening.
- **Final master closure** remains mandatory, strictly read-only and post-merge, verifying remote identity, ancestry, allowed paths, preserved accepted HEAD/TREE/blob and governance statuses.

### 4. Consolidation of administrative work

The implementation owner should prepare an evidence ledger and draft short manifest at the same time it prepares the independently auditable candidate; the draft must not falsely claim acceptance yet. Once the independent implementation audit returns PASS, the owner fills the accepted audit token and freezes the accepted implementation HEAD, then submits the manifest for one mechanical audit. After that PASS, the owner performs a pure fast-forward to master and requests one read-only closure check. These gates are chronological and **must not be pre-approved** before the relevant artifact or master state exists.

Where the same independent execution session can remain active to conduct later mechanical gates after receiving the published artifact and a new explicit task, reuse that session and its evidence, but never allow an implementer to self-approve an independent gate.

### 5. Bounded audit reports

Every audit report must distinguish:
1. blocking nonconformities supported by exact file/line/contract;
2. informational improvements that do not block closure;
3. evidence reused versus newly tested;
4. exact next gate and actor.

For a failed audit, return all defects discernible from the scoped evidence in one consolidated report. The implementation owner must fix them together and perform a local self-review before another delta audit. Do not impose an arbitrary re-review limit that could silently waive defects.

### 6. Credit usage measurement

Record per package: number of WORK executions, deep audits, mechanical audits, audit-triggered correction cycles, validation commands, changed lines and completed implementation acceptance. Track *avoidable* audit failures separately from required gates. Do not treat number of passing tests or commits as a cost proxy. Use actual usage data for financial estimates when available; never invent a per-run credit price.

## Unchanged safety/governance invariants

v1.1 sections 3, 4, 5, 9–13 and 17 remain controlling unless and until an explicit independently reviewed change is approved. In particular:
- independent review of accepted definitions and implementations;
- immutable accepted artifact boundary;
- append-only fixes, no force-push;
- pure fast-forward to master;
- post-merge integrity audit;
- explicit implementation authorizations and no downstream authorization by implication;
- professional decision stop gates;
- preserved transactional, fingerprint, client-isolation, testing and security safeguards;
- no production-readiness inference.

## Required validation before adoption

1. Independently inspect the proposed changes against the **actual v1.1 clauses** and identify any conflict or semantic weakening.
2. Produce a precise replacement/diff against the canonical protocol, rather than adopting this proposal as authority.
3. Audit the governance amendment independently and approve explicitly before master integration.
4. Until then, follow v1.1 without exception.

PROPOSAL_ONLY_NOT_AUTHORIZED
