# PKG-004B2 — M07 Calculation Input Resolution

## 1. Definition Status

| Field | Value |
|---|---|
| Package | `PKG-004B2 — M07 Calculation Input Resolution` |
| Package type | Deterministic calculation-input resolution |
| Definition status | `DEFINED_PENDING_IMPLEMENTATION_AUTHORIZATION` |
| Implementation | `NOT_STARTED` |
| Base dependency | Accepted PKG-004B1 evidence foundation |
| Next package authorization | `NOT_AUTHORIZED` |

This document defines scope and acceptance criteria only. It does not
authorize implementation.

## 2. Product and Authority Boundary

The intended product is a personal or narrowly operated professional
calculator, not an organizational SaaS approval and authority-management
system. It calculates when the inputs required by a calculation are present,
technically valid, and unambiguous.

The package answers only:

1. Are all required calculation inputs present?
2. Is every required input technically valid?
3. Is there one unambiguous selected value for every required input?

The system does not assess professional reliability of the data, the authority
of the person who entered it, qualification, warning review,
`accepted_for_use`, professional approval, or a reviewer/supervisor workflow.
A manually entered value, documentary value, or planner assertion is an
allowed calculation candidate. Its origin is retained for traceability and
does not establish a reliability rank.

## 3. Resolution Outcomes

Only these resolution outcomes are defined:

| Outcome | Meaning |
|---|---|
| `resolved` | All required calculation inputs are present, technically valid, and unambiguous. |
| `missing_inputs` | One or more required calculation inputs are absent or technically unusable. |
| `ambiguous_inputs` | One or more required fields have conflicting normalized candidate values and no valid active selection. |

PKG-004B2 does not define `qualified`, `warning_reviewed`,
`accepted_for_use`, technical professional approval, current professional
authority, or eligibility approval.

## 4. Required-Field Manifest

Resolution is governed by a server-owned, versioned calculation-input
manifest. A manifest identifies:

- calculation scope;
- manifest version;
- required field codes;
- technical type for each field;
- normalization rule for each field;
- whether null is a technically valid value;
- whether a field is conditional;
- the technical condition that makes a conditional field required.

The manifest contains calculation-input requirements only. It must not encode
professional approval rules. An unknown manifest version fails closed and
cannot produce a calculation-ready payload.

## 5. Candidate and Selection Model

For every required field, resolution distinguishes:

1. the required calculation field;
2. its candidate values;
3. the selected active value, when selection is needed;
4. source references retained only for traceability;
5. the technical normalization result;
6. the resolution fingerprint.

Candidate values may originate from:

- persisted source evidence;
- documentary evidence;
- planner assertion;
- direct manual entry;
- an accepted technical derivation explicitly defined by a calculation rule.

Source type, timestamp, and asserted or documentary origin do not rank
candidates. A candidate identity must remain distinct from its normalized
value so that identical values can be coalesced without losing their source
references.

An explicit selection identifies an available candidate or normalized
candidate value for a field. It is a user choice for calculation input, not a
professional approval. The package does not label the user as a reviewer,
authority, approver, or supervisor.

## 6. Deterministic Resolution Rules

The resolver applies these rules per required field:

1. With no technically usable candidate, the outcome is `missing_inputs`.
2. With exactly one technically valid candidate value, that value is selected
   automatically.
3. Multiple candidates with the same normalized value are treated as one
   usable value, while every source reference is retained.
4. Multiple candidates with different normalized values produce
   `ambiguous_inputs` unless an explicit user selection identifies an
   available candidate.
5. An existing explicit selection that matches an available candidate is
   used.
6. A selection is invalidated if its candidate no longer exists or its
   normalized value materially changed. The result is `ambiguous_inputs` or
   `missing_inputs`, as applicable.
7. A new PKG-004B1 evidence revision does not by itself invalidate a selection
   when the selected normalized value remains available and no conflicting
   normalized value was introduced.
8. Conflicts are never resolved by latest-wins, source priority, authority
   rank, or timestamp rank.

Rules are evaluated against the manifest version and calculation scope
recorded by the resolution. Conditional fields participate only when their
manifest-defined technical condition is met.

## 7. Technical Normalization and Validation

Normalization is deterministic and manifest-defined. It may reject or treat
as unusable:

- an invalid date;
- an invalid number;
- an unsupported enum;
- a malformed identifier;
- a value outside a technically impossible range;
- a value that cannot be normalized.

Subjective plausibility checks are excluded unless they are explicit
calculation constraints. Normalization does not judge professional
sufficiency, authenticity, reliability, or authority.

## 8. Resolution Persistence

The package defines an immutable resolution record, or an equivalent immutable
representation, containing:

- client ID;
- calculation scope;
- calculation-input manifest version;
- PKG-004B1 evidence revision ID;
- selected field and value identities;
- normalized values;
- source references;
- resolution outcome;
- missing field list;
- ambiguous field list;
- canonical payload;
- deterministic resolution fingerprint;
- creation timestamp;
- successor and supersession linkage when correction is required.

Closed resolution records are immutable. Corrections create a successor rather
than rewriting accepted history. A successor may preserve a prior selection
across an evidence revision only under rule 7.

The canonical payload is server-generated from the recorded scope, manifest
version, B1 revision, normalized field results, selections, traceability
references, outcome, and missing or ambiguous field lists. Its deterministic
fingerprint uses a declared canonicalization and fingerprint algorithm. A
caller cannot supply either the canonical payload, fingerprint, or resolved
outcome.

## 9. Current Calculation-Input Selector

The narrow selector may return:

- `resolved`;
- `missing_inputs`;
- `ambiguous_inputs`;
- `unavailable` when no resolution record exists.

There is at most one current unsuperseded resolution per client and
calculation scope. The selector never chooses between conflicting values. It
does not use latest-wins as an authority rule. An inconsistent
multiple-current state fails closed as `ambiguous_inputs` or as an invariant
violation; it is never ranked into a result.

The selector determines calculation input only. It does not select current
professional authority.

## 10. Calculation Handoff

Only a `resolved` resolution emits a calculation-ready payload containing:

- client ID;
- calculation scope;
- manifest version;
- normalized selected values;
- source references for audit traceability;
- PKG-004B1 evidence revision ID;
- resolution fingerprint.

`missing_inputs`, `ambiguous_inputs`, and `unavailable` do not emit a
calculation-ready payload.

## 11. Relationship to PKG-004B1

- PKG-004B1 remains accepted and unchanged.
- PKG-004B1 stores evidence, provenance, findings, and technical assessment.
- PKG-004B2 does not alter PKG-004B1 evidence.
- PKG-004B2 does not convert evidence into professional authority.
- PKG-004B2 determines only whether the evidence yields a complete and
  unambiguous calculation-input set.

## 12. Explicit Exclusions

PKG-004B2 explicitly excludes:

- qualification;
- warning review;
- `accepted_for_use`;
- professional authorization;
- source reliability ranking;
- document authenticity validation;
- user licence validation;
- organizational RBAC;
- supervisor workflow;
- fixation integration;
- M08E;
- full M08F;
- M09-M14;
- formal 161D;
- 02M;
- UI implementation;
- production readiness.

It also excludes historical backfill and does not claim V1/V2 parity or full
M07 completion.

## 13. Acceptance Criteria

| ID | Acceptance criterion |
|---|---|
| AC-B2-001 | A server-owned, versioned required-field manifest deterministically identifies calculation scope, fields, types, normalization, nullability, and conditional requirements. |
| AC-B2-002 | An unknown manifest version fails closed without a calculation-ready payload. |
| AC-B2-003 | A required field with no technically usable candidate produces `missing_inputs`. |
| AC-B2-004 | One technically valid candidate value is selected automatically. |
| AC-B2-005 | Candidates with the same normalized value are treated as one usable value without losing any source reference. |
| AC-B2-006 | Different normalized candidate values produce `ambiguous_inputs` when no valid explicit selection exists. |
| AC-B2-007 | An explicit user selection matching an available candidate resolves that field without creating an approval status. |
| AC-B2-008 | A selection is invalidated when its candidate disappears or its normalized value materially changes. |
| AC-B2-009 | A selection remains preservable across a new B1 revision when its normalized value remains available and no conflict is introduced. |
| AC-B2-010 | Source references remain traceable and do not participate in ranking. |
| AC-B2-011 | Technical normalization is deterministic and rejects technically invalid or non-normalizable inputs. |
| AC-B2-012 | The server produces a canonical readable resolution payload. |
| AC-B2-013 | Repeated resolution of identical material input produces the same deterministic fingerprint. |
| AC-B2-014 | Resolution, candidates, selections, and reads are client-isolated. |
| AC-B2-015 | Closed resolution records are immutable. |
| AC-B2-016 | Correction occurs through a linked successor and supersession operation. |
| AC-B2-017 | The current selector fails closed for missing records and inconsistent multiple-current state. |
| AC-B2-018 | A calculation-ready payload is emitted only for `resolved`. |
| AC-B2-019 | The calculation handoff includes normalized values, traceability references, B1 revision identity, manifest version, scope, client, and resolution fingerprint. |
| AC-B2-020 | No resolution outcome, actor label, selector, or record represents professional authority or an approval workflow. |

## 14. Negative Acceptance Criteria

| ID | Prohibited behavior |
|---|---|
| NAC-B2-001 | Creating or inferring `qualified`. |
| NAC-B2-002 | Creating or inferring `warning_reviewed`. |
| NAC-B2-003 | Creating or inferring `accepted_for_use`. |
| NAC-B2-004 | Ranking candidates by source type, reliability, authority, actor, or timestamp. |
| NAC-B2-005 | Resolving conflicting values by latest-wins. |
| NAC-B2-006 | Accepting a caller-supplied `resolved` status. |
| NAC-B2-007 | Accepting a caller-supplied canonical payload or fingerprint. |
| NAC-B2-008 | Automatically using one of several conflicting normalized values without a valid explicit selection. |
| NAC-B2-009 | Claiming professional authority, professional sufficiency, eligibility approval, or professional acceptance. |
| NAC-B2-010 | Altering PKG-004B1 evidence or its accepted contract. |
| NAC-B2-011 | Integrating the resolution into fixation. |
| NAC-B2-012 | Fabricating historical resolution records or backfill. |
| NAC-B2-013 | Adding or changing UI. |
| NAC-B2-014 | Claiming production readiness, V1/V2 parity, or full M07 completion. |
| NAC-B2-015 | Treating documentary, asserted, derived, persisted, or manually entered origin as a reliability rank. |
| NAC-B2-016 | Emitting a calculation-ready payload for `missing_inputs`, `ambiguous_inputs`, or `unavailable`. |
| NAC-B2-017 | Selecting a current record from an inconsistent multiple-current state by ordering or ranking. |
| NAC-B2-018 | Introducing reviewer, supervisor, approver, authority, licence-validation, or organizational RBAC workflow. |

## 15. Stop Conditions and Final Gate

Implementation must stop and return for product direction if it would require:

- a professional reliability or authority decision;
- a new outcome beyond the defined resolution vocabulary;
- source ranking or automatic conflict selection;
- a calculation scope, required field, normalization rule, technical
  condition, or derivation rule not supplied by an authorized manifest;
- fixation, UI, M08E, full M08F, M09-M14, formal 161D, or 02M work;
- historical backfill or alteration of accepted PKG-004B1 evidence.

The final definition gate is:

`PKG_004B2_DEFINED_PENDING_IMPLEMENTATION_AUTHORIZATION`

No implementation is authorized by this gate.
