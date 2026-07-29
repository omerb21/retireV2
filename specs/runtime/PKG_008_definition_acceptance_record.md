# PKG-008 Definition Acceptance Record

## Identity

| Field | Value |
|---|---|
| Package | `PKG-008 — M03 Source Review and Downstream Evidence Eligibility Foundation` |
| Module | `M03` |
| Definition status | `ACCEPTED` |
| Accepted definition commit | `078383ad8fd25e0dd24be9f2e65ddf9d15c34535` |
| Accepted definition branch | `origin/pkg-008-definition` |
| Definition base | `fdf435c33ce039c6c2ef578db7d2dffae5a4412d` |
| Definition | `specs/runtime/PKG_008_FINAL_PACKAGE_DEFINITION.md` |
| Implementation | `NOT_AUTHORIZED` |
| Migration execution | `NOT_AUTHORIZED` |
| M03 implementation | `NOT_IMPLEMENTED` |
| M04 | `NOT_AUTHORIZED` |
| Next package | `NOT_AUTHORIZED` |

## Accepted Product Outcome

The accepted bounded outcome is an append-only, client-scoped review
foundation for an uploaded M02 source or manual M02 record. Only a valid
current `accepted` review decision creates narrow technical eligibility for a
separately authorized downstream transformation.

Eligibility does not mean:

- parsed;
- normalized;
- classified;
- professionally authoritative;
- financially authoritative;
- tax-authoritative;
- calculation-ready;
- M04 accepted; or
- M05 ready.

## Locked Product Contracts

### Target kinds

The closed target-kind vocabulary is:

- `source_evidence_review`;
- `manual_record_review`.

An uploaded target references existing M02 intake, source, blob, and checksum
provenance without duplicating them. A manual target references its existing
M02 intake only. The manual technical reference is not external evidence, and
no source, blob, or checksum provenance is invented for a manual target.

### Review creation and lifecycle

- Review creation is explicit and never automatic.
- The first revision is `under_review`.
- Persisted review states are exactly `under_review`, `accepted`, and
  `rejected`.
- Review history is immutable and append-only.
- Accept and reject create new child revisions.
- Reopen creates a new `under_review` child revision.
- Prior accepted and rejected revisions remain unchanged.
- No more than one current open review is permitted for a target.
- Actor/reviewer, timestamp, revision identity, sequence, ownership, and
  provenance are server-controlled.

### Annotations

- Annotations are note-only and append-only.
- An annotation has no typed corrected value or professional value.
- An annotation does not reopen review, change a decision, restore
  eligibility, or mutate M02.
- Superseding an annotation adds a new row and retains the previous row.

### Eligibility and predecessor boundary

- Eligibility is derived and fail-closed.
- Eligibility is never trusted as caller input or caller-mutable state.
- Only the valid current `accepted` revision can satisfy the review-decision
  part of the eligibility contract.
- M03 does not change M02 lifecycle.
- M02 rejection or supersession makes eligibility false while retaining all
  M03 history.
- M02 supersession remains exclusively owned by M02.
- Archived M01 cases are read-only for M03.
- Reopening an M01 case does not change review history or automatically restore
  eligibility.

## Acceptance Evidence

Final definition audit status:

`ACCEPT_PKG_008_DEFINITION`

| Audit area | Result |
|---|---|
| Safety | `PASS` |
| Product outcome | `PASS` |
| Target-kind contract | `PASS` |
| Explicit review creation | `PASS` |
| Lifecycle and immutable revision model | `PASS` |
| M02 interaction | `PASS` |
| Eligibility | `PASS` |
| Annotation contract | `PASS` |
| Archived behavior | `PASS` |
| Client isolation and anti-forgery | `PASS` |
| Data model and migration boundary | `PASS` |
| API/UI completeness | `PASS` |
| Stop conditions | `13 PASS` |
| AC | `22 PASS / 0 FAIL / 0 NOT_PROVEN` |
| NAC | `18 PASS / 0 FAIL / 0 NOT_PROVEN` |
| Blocking definition defects | `None` |
| Non-blocking drafting observations | `None` |
| Product decisions required | `None` |

## Scope Boundaries

- The PKG-008 definition is accepted.
- Implementation remains `NOT_AUTHORIZED`.
- Migration execution remains `NOT_AUTHORIZED`.
- M03 remains not implemented.
- Parser behavior is not authorized.
- Normalization is not authorized.
- Classification is not authorized.
- M04 is not authorized.
- M05 is not authorized.
- Downstream transformation is not authorized.
- M09–M14 remain blocked.
- `02M` remains frozen.
- No production-readiness claim is made.
- No M03-completion claim is made.
- No V1/V2 parity claim is made.

## Follow-Up Boundary

- Definition acceptance does not authorize implementation.
- A separate implementation Gate is required.
- No migration may be created or executed under this acceptance.
- M04 remains closed.
- No next package is authorized.
