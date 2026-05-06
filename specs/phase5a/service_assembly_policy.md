# Phase 5A Service Assembly Policy

## Status

Authoritative Accepted Temporary Policy

## Scope

Phase 5A ordinary service assembly only

## Approved Policy

For Phase 5A service assembly only:
If assemble_fixation_input has no explicit IDF relevance source available, and the service assembly path is not an IDF-specific flow, idf_relevant=False is approved as an explicit service assembly rule for ordinary non-IDF cases.

## Strict Limitations

- not generic default
- not hidden fallback
- not inference from idf object
- not "assume non-IDF"
- not contract relaxation
- direct FixationInput payloads remain strict
- future explicit source overrides this rule

## Related Commit

d433f4c7ddb086622b30b9738cdcb959dcac4608

## Source Of Authority

- Supervisor-approved Governance Hardening planning
- prior Phase 5A policy decision
