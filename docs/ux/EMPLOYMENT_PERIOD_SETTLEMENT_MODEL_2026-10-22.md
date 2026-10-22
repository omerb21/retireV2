# Employment-period-centered settlement model — decision record

Date: 2026-10-22
Scope: RETIRE V2 professional workspace, isolated feature branch
Authority: User explicitly approved the employment-period identity rule. This document defines the constrained implementation direction; tax outcomes and complete data schema remain pending review.

## Binding identity rule

- **One employment record = one continuous period of employment = one termination settlement** (if the period ended).
- Rehire by the same legal employer after termination creates a **new employment record** regardless of employer name / withholding file number matching.
- The legal employer identity can be repeated across records; it must never serve as a unique key for an employment period.
- An active employment period has *no historical completed termination settlement*. Severance choices concerning an anticipated retirement belong to a future scenario, not factual history.

## Current evidence from backend, API and frontend

1. Backend ORM `EmploymentRecord`: immutable `employment_record_id`, `client_id`, employer name, start/end, `is_current`, notes. `Grant` already has nullable FK `employment_record_id` to `employment_records` and an ORM relationship.
2. Public `GrantRequest` / `GrantResponse` in `backend/app/api/clients_routes.py` **omit** `employment_record_id`. Existing `create_grant` and `update_grant` do not populate it; current records are typically unlinked.
3. Current frontend `GrantItem` / `GrantPayload` likewise omit the field. The workspace presently exposes independent inline create/edit of grant records and employment records. This was functional and passed 22 focused tests and a user browser synthetic save/read-back check, but is not the accepted long-term professional workflow.
4. Existing grant contract stores only an exempt grant amount, dates and employer/withholding names. This cannot represent the full distribution and evidence for taxable grant, רצף קצבה, רצף פיצויים and mixed elections. Do not equate the existing grant amount with a complete settlement or an approved exemption.

## Target workflow

1. **Current employer** is a separate professional screen: factual current salary, payroll basis, terms, contribution bases, severance accumulation and source evidence. No automatic current-employer severance retirement election.
2. **Historical employers** is a list of employment periods, each with its own permanent ID and dates. Opening one period reveals its single employment-ending settlement *workspace*.
3. The settlement for one ended period contains zero or more documented components / amounts: exempt grants received, taxable grants, pension-continuity requests/approvals, severance-continuity requests/approvals, sums retained by funds, and supporting 161/tax correspondence. These are component facts and decisions supported by the documents; they are not several termination events.
4. **Grants overview** remains read-only summary/navigation to the linked employment period. Existing detached grants are labeled **not linked to an employment period** until an explicit operator confirmation.
5. On actual retirement from a current employer, capture the real ended-period facts and link settlement evidence then; any preceding scenario decisions remain hypothetical snapshots until actual facts have been confirmed.

## Integrity constraints before new persistent writes

- Add/activate a request/response employment record link only with a server-side check that both the employment period and the grant belong to the same client; reject cross-client links.
- No implicit matching by employer_name, period dates or withholding file number, even when unique-looking. Expose legacy unlinked records for explicit reconciliation.
- For a grant linked to an ended period, verify the record is not current and date/period consistency according to an explicitly approved policy. Do not silently rewrite historic employer, dates, or source financial facts.
- The one-settlement-per-period structure should be represented with a unique period key; *multiple amounts, decisions and evidence items under that single settlement* are allowed. Do not impose one-grant-per-employer.
- Introduce schema/migration and API contract tests before switching existing user entry routes; include mixed elections and repeat employment with same legal employer as acceptance scenarios.
- Source-derived statements, planner assertions, tax-authority approvals and proposed elections require distinguishable provenance/status. Do not derive historical tax approval from a typed numeric value.
- Factual changes must invalidate dependent scenario evaluations; prospective options must not mutate factual PensionProduct components.

## Implementation sequence

A. Audit already existing Grant FK/migration and all readers of it, including PK/FK ownership and deletion semantics. Produce a compatibility and migration plan; do not auto-link legacy grants.
B. Implement secure client-scoped link / unlink with explicit reconciliation UI and negative tests (cross-client / current-period / ambiguous repeat employment). Use the existing FK where safe.
C. Introduce authoritative period-settlement components and status/evidence contracts after precise tax and business field review; connect historical-employer editing screen. Switch grants list to read-only view/open-parent navigation.
D. Build independent current-employer factual screen with richer payroll and rights details, then attach *scenario-owned* future severance choices only after scenario contract approval.

## Non-goals for this slice

No calculation of exemption, 161/161ד eligibility, indexation, scenario payouts, NPV or automatic conversion. No master merge, deployment or full CI.
