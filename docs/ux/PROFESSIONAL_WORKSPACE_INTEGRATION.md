# Professional Workspace — UX adoption, implementation slice 1

Date: 2026-10-22
Repository base: master at 6f3d523e9c81b55da045ac3c85e747104821d5da
Reference: approved synthetic full-workflow HTML prototype, reviewed by the professional owner.
Status: UX direction accepted; functional/financial acceptance NOT CLAIMED.

## Binding professional workflow

1. Case entry — minimal identity and immediate access to the portfolio.
2. Portfolio — a single horizontally scrollable ledger; one product per row; monetary components as columns; contextual actions after selecting one or more cells; metadata on demand.
3. Supplementary facts — current employer, historical grants, existing pensions, income and other assets.
4. Scenario decisions — retirement dates, employer choices and explicit pension/capital conversions against a named scenario.
5. Comparison — independent alternatives, factual warnings, calculated outputs only from approved engines, followed by professional report.

The technical M01-M14 modules remain the implementation boundaries. They are *not* the visible user journey and must not generate mandatory user-facing status clutter.

## Immutable separation

- Imported evidence and its original monetary amounts are not silently overwritten by a planner correction.
- Factual product corrections go through existing, version-checked canonical ProductUpdate API and backend audit. A classification change between monetary columns is NOT a pension/capital conversion.
- Scenario allocations must be separate from canonical PensionProduct balances. Existing POST canonical-conversions currently updates factual balances; **do not call it from a scenario UI** until an approved scenario producer and persistence contract exist.
- Never claim computed pension, tax, exemption, 161ד, NPV, or scenario comparison values from UX-only model data.
- A change to authoritative inputs must invalidate or explicitly mark any linked scenario as needing re-evaluation.

## First implementation slice (this branch)

- Add a parallel, authenticated /clients/:clientId/workspace route and navigation from the client list.
- Read current client identity and canonical product balances from accepted GET APIs; do not copy hard-coded example data into the live React application.
- A single interactive portfolio ledger with searchable products, optional nonzero component columns, selection, and contextual factual correction. Saving multiple values of the same product is one guarded API operation.
- Case header and separate links to the existing accepted supplementary-data screens.
- Present scenario and comparison stages as unimplemented, with no misleading execute buttons or silent redirects to the mutating conversion API.
- Keep old routes fully accessible during testing.

## First slice acceptance

1. Client A-to-B and A-to-B-to-A navigation never renders stale cross-client responses or selected balances.
2. Ledger shows the eleven known financial component codes and any additional codes, one product per row; raw source history is not hidden or changed.
3. Search, hiding-zero columns and selecting cells make no backend writes.
4. Two corrected balances from one product are written in one PUT with expected_version. Untouched component codes are preserved. Error or 409 retains a draft but never claims a successful save.
5. Scenario and comparison views issue no conversion or financial writes. No fake results are presented as calculated fact.
6. Build, focused tests and an end-to-end journey using synthetic data must pass before proposed merge.

Future slices: end-to-end supplements in the workspace, scenario data contract and reversible allocations, backend integrations, report generation, professional review. No production readiness claim is possible from this slice.