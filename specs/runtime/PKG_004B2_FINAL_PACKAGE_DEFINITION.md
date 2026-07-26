# PKG-004B2 — M07 Calculation Input Resolution

## 1. Definition Status

| Field | Value |
|---|---|
| Package | `PKG-004B2 — M07 Calculation Input Resolution` |
| Package type | Deterministic calculation-input resolver |
| Definition status | `DEFINED_PENDING_IMPLEMENTATION_AUTHORIZATION` |
| Implementation | `NOT_STARTED` |
| Base dependency | Accepted PKG-004B1 evidence foundation |
| Next package authorization | `NOT_AUTHORIZED` |

This document defines scope and acceptance criteria only. It does not
authorize implementation.

## 2. Purpose and Product Boundary

PKG-004B2 resolves one present calculation-input set from:

- calculation scope;
- a server-owned manifest version;
- one client-scoped PKG-004B1 evidence revision;
- narrow user selections between conflicting values, when supplied.

The intended product is a personal or narrowly operated professional
calculator, not an organizational approval or authority-management system.
The resolver answers only:

1. Are all required calculation inputs present?
2. Is every required input objectively valid for the calculation?
3. Is there one unambiguous value for every required input?

It does not assess professional reliability, data-entry authority,
qualification, warning review, `accepted_for_use`, professional approval, or
reviewer/supervisor workflow.

## 3. Resolver Operation

The package defines a stateless or narrowly state-assisted operation:

```text
resolve_calculation_inputs(
    client_id,
    calculation_scope,
    manifest_version,
    b1_evidence_revision_id,
    selections?
)
```

For every invocation, the resolver loads the specified client-scoped B1
revision, obtains its candidates, applies the manifest's normalization and
required-field rules, applies any still-valid user selections, and returns
the present result. A previously calculated result is not selected as current
and is not required as an input to the next invocation.

The package requires no resolution-history aggregate, correction workflow, or
current-record repository.

## 4. Resolution Outcomes

The complete outcome vocabulary is:

| Outcome | Meaning |
|---|---|
| `resolved` | All required inputs are present, objectively valid for calculation, and unambiguous. |
| `missing_inputs` | One or more required inputs are absent, invalid, or cannot be normalized. |
| `ambiguous_inputs` | One or more required fields have conflicting normalized values and no valid explicit selection. |

No evidence or no usable candidate produces `missing_inputs` and a missing
field list. No other resolution outcome is defined.

## 5. Required-Field Manifest

Resolution is governed by a server-owned, versioned calculation-input
manifest. It defines only:

- required field codes;
- technical data types;
- normalization rules;
- whether null is valid;
- conditional technical requirements and their explicit conditions.

The manifest is bound to a calculation scope. It contains no professional
approval, reliability, source-ranking, or user-authority rule. An unknown
manifest version fails closed and emits no calculation-ready payload.

## 6. B1 Candidate Boundary

PKG-004B2 consumes candidate values represented by the specified
PKG-004B1 evidence revision. B1 evidence may retain persisted-source,
documentary, planner-asserted, and other accepted B1 provenance.

Direct manual entry is not a separate B2 evidence channel. A manually entered
value must first be recorded in B1 as evidence or a planner assertion. A
future UI may create B1 evidence from manual input, but that UI and workflow
are outside PKG-004B2.

An accepted technical derivation may be a candidate only when an explicit
calculation rule defines it and its B1 input references remain traceable.
Candidate origin is traceability information and never establishes ranking.

## 7. Deterministic Resolution Rules

The resolver applies these rules per required field:

1. No technically usable candidate produces `missing_inputs`.
2. Exactly one technically valid normalized value is used automatically.
3. Multiple candidates with the same normalized value are treated as one
   usable value, while all source references are retained.
4. Multiple different normalized values produce `ambiguous_inputs` unless a
   valid explicit user selection identifies one available value.
5. A supplied selection is used only while its selected normalized value or
   candidate identity remains available.
6. A stale selection is ignored or invalidated. It cannot support a resolved
   result; the resolver returns the naturally applicable `missing_inputs` or
   `ambiguous_inputs` result.
7. A selection may remain usable across a B1 revision change when its selected
   normalized value remains available and no new conflicting value exists.
8. Conflicts are never resolved by latest-wins, source priority, authority
   rank, or timestamp rank.

Conditional fields participate only when the manifest's explicit technical
condition is met.

## 8. Narrow User Selection

An explicit selection is only a user choice between conflicting normalized
values. It is not an approval, review, qualification, or reliability
decision.

Selections may be supplied with the resolver request. If persistence is
necessary to remember the user's choice, it is optional and limited to:

- field code;
- selected normalized value or candidate identity;
- calculation scope;
- optional B1 evidence revision reference;
- timestamp.

PKG-004B2 does not require persistent resolution results or immutable
resolution history. Optional selection persistence exists solely to avoid
asking the user to repeat a still-valid conflict choice.

## 9. Objective Technical Validation

Validation is limited to objective rules needed by the calculation:

- parseable date;
- parseable number;
- supported enum;
- required identifier structure;
- an explicit mathematical or domain constraint required by the calculation
  and declared by the manifest.

A value that fails an applicable rule is unusable and contributes to
`missing_inputs`. The resolver does not apply subjective plausibility,
authenticity, reliability, or professional-sufficiency checks.

## 10. Resolver Result and Fingerprint

Every resolver result contains:

- client ID;
- calculation scope;
- manifest version;
- B1 evidence revision ID;
- normalized selected values;
- source references for traceability;
- missing fields;
- ambiguous fields and their candidate values;
- outcome;
- server-generated deterministic fingerprint.

The server may also generate a readable canonical payload as the resolver
result. Persistent archival storage of that payload or result is not required
by PKG-004B2.

The caller cannot supply or override the outcome, canonical payload, or
fingerprint. Repeating resolution with the same material manifest, B1
evidence, and valid selections produces the same material result and
fingerprint.

## 11. Calculation Handoff

When the outcome is `resolved`, the resolver emits a calculation-ready payload
containing:

- client ID;
- calculation scope;
- manifest version;
- B1 evidence revision ID;
- normalized selected values;
- source references;
- resolution fingerprint.

For `missing_inputs` or `ambiguous_inputs`, the resolver returns diagnostic
missing or ambiguity data but emits no calculation-ready payload.

## 12. Required Package Shape

Implementation authorization, if separately granted, may require at most:

1. a calculation-input manifest;
2. a resolver service;
3. input and output schemas;
4. optional narrow user-selection persistence, only if necessary;
5. focused tests.

The package does not require a new immutable resolution aggregate or a
current-record repository.

## 13. Relationship to PKG-004B1

- PKG-004B1 remains accepted and unchanged.
- PKG-004B1 stores evidence, provenance, findings, and technical assessment.
- PKG-004B2 reads but does not alter B1 evidence.
- PKG-004B2 does not convert evidence into professional authority.
- Manually entered information reaches B2 only after representation in B1.

## 14. Explicit Exclusions

PKG-004B2 excludes:

- qualification, warning review, `accepted_for_use`, and professional
  authorization;
- source reliability ranking and document-authenticity validation;
- user licence validation, organizational RBAC, and supervisor workflow;
- stored current-resolution authority or resolution-record lifecycle;
- historical resolution backfill;
- fixation integration;
- UI implementation;
- M08E and full M08F;
- M09-M14;
- formal 161D;
- 02M;
- production readiness;
- V1/V2 parity and full M07-completion claims.

## 15. Acceptance Criteria

| ID | Acceptance criterion |
|---|---|
| AC-B2-001 | A server-owned versioned manifest defines required fields, technical types, normalization, nullability, and conditional technical requirements for a calculation scope. |
| AC-B2-002 | Missing, invalid, or non-normalizable required inputs produce `missing_inputs` with the missing field list and no calculation-ready payload. |
| AC-B2-003 | Exactly one technically valid normalized value is used automatically. |
| AC-B2-004 | Identical normalized values are coalesced without losing source traceability. |
| AC-B2-005 | Conflicting normalized values produce `ambiguous_inputs` and expose the ambiguous fields and candidate values. |
| AC-B2-006 | A valid explicit user selection resolves a conflict without creating an approval or authority state. |
| AC-B2-007 | A stale selection is ignored or invalidated and cannot support a resolved result. |
| AC-B2-008 | Normalization and objective validation are deterministic and manifest-defined. |
| AC-B2-009 | Candidate and source references remain client-isolated and traceable to the specified B1 revision. |
| AC-B2-010 | Identical material resolver inputs produce the same server-generated fingerprint. |
| AC-B2-011 | The resolver returns exactly one of `resolved`, `missing_inputs`, or `ambiguous_inputs`. |
| AC-B2-012 | A calculation-ready payload is emitted only for `resolved`; other outcomes return diagnostics only. |
| AC-B2-013 | The resolver introduces no qualification, approval, reliability, reviewer, supervisor, or current-authority workflow. |

## 16. Negative Acceptance Criteria

| ID | Prohibited behavior |
|---|---|
| NAC-B2-001 | Creating qualification, warning-review, accepted-for-use, professional-approval, or authority states. |
| NAC-B2-002 | Ranking candidates by source, reliability, actor, authority, or timestamp. |
| NAC-B2-003 | Resolving conflicts by latest-wins or automatically choosing one conflicting value. |
| NAC-B2-004 | Accepting caller-supplied outcome, canonical payload, or fingerprint. |
| NAC-B2-005 | Allowing direct manual entry to bypass PKG-004B1 evidence or planner assertions. |
| NAC-B2-006 | Requiring a stored current-resolution selector, current-record invariant, immutable resolution history, or correction lifecycle. |
| NAC-B2-007 | Altering PKG-004B1 evidence or its accepted contract. |
| NAC-B2-008 | Emitting a calculation-ready payload for `missing_inputs` or `ambiguous_inputs`. |
| NAC-B2-009 | Adding fixation integration, UI implementation, or historical backfill. |
| NAC-B2-010 | Expanding into M08E, full M08F, M09-M14, formal 161D, or 02M. |
| NAC-B2-011 | Claiming production readiness, V1/V2 parity, or full M07 completion. |

## 17. Stop Conditions and Final Gate

Implementation must stop and return for product direction if it would require:

- a professional reliability or authority decision;
- an outcome outside the three-value vocabulary;
- source ranking or automatic conflict selection;
- a calculation field, normalization, conditional rule, or derivation not
  supplied by an authorized manifest;
- a resolution-history aggregate or current-record subsystem;
- a direct B2 manual-entry channel;
- fixation, UI, M08E, full M08F, M09-M14, formal 161D, or 02M work.

The definition gate remains:

`PKG_004B2_DEFINED_PENDING_IMPLEMENTATION_AUTHORIZATION`

No implementation is authorized by this gate.
