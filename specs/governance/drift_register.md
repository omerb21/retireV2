# Governance Drift Register

## Register Status

Authoritative drift register.

## Drift Entries

| Drift id | Title | Classification | Risk | Owner phase | Blocking status | Current mitigation | Required decision | Target phase | Source evidence | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| DRIFT-001 | Phase 5A service assembly policy bookkeeping alignment | RESOLVED / DOCUMENTATION_ALIGNED | Low | Governance Hardening Sprint / Phase 5A | Not a runtime blocker; not a Phase 6 blocker | Operationally resolved in substance; documentation bookkeeping aligned to persisted policy | None after bookkeeping update | Governance Hardening Sprint closure | specs/phase5a/service_assembly_policy.md; System Integrity Audit; commit d433f4c7ddb086622b30b9738cdcb959dcac4608 | Resolved; governance/process alignment only (no new runtime implementation) |
| DRIFT-002 | API invalid payload 422 vs ValidationError strategy | DECISION_REQUIRED / ARCHITECTURE_BOUNDARY_RISK | High | Phase 5B | Does not block Phase 5A resume once tracked | deferred API response strategy decision | decide API invalid payload response strategy | Phase 5B | System Integrity Audit | Tracked deferred drift |
| DRIFT-003 | API local request/response models and ad hoc dicts | ARCHITECTURE_BOUNDARY_RISK | Medium | Phase 5B | Does not block Phase 5A resume once tracked | deferred API contract architecture decision | decide whether local API shapes become approved API contracts or are replaced | Phase 5B | System Integrity Audit | Tracked deferred drift |
| DRIFT-004 | API direct DB access | ARCHITECTURE_BOUNDARY_RISK | Medium | Phase 5B | Does not block Phase 5A resume once tracked | deferred API/service boundary decision | decide allowed API/service boundary and DB access policy | Phase 5B | System Integrity Audit | Tracked deferred drift |
| DRIFT-005 | row_order vs stage_order persistence mismatch | TRACKED_DEFERRED_DRIFT | Medium | Phase 6/7 or targeted persistence correction | Does not block Phase 5A resume once tracked | deferred persistence boundary decision | decide whether persistence must expose/preserve AuditRow.stage_order semantics | Phase 6/7 or targeted persistence correction | System Integrity Audit | Tracked deferred drift |
| DRIFT-006 | FixationValidationErrors unused at runtime | DECISION_REQUIRED | Low | Phase 5B or contract usage decision | Does not block Phase 5A resume once tracked | runtime list[ValidationError] remains current behavior | decide whether FixationValidationErrors should remain unused, be adopted, or be deprecated | Phase 5B or contract usage decision | System Integrity Audit | Tracked deferred drift |
| DRIFT-007 | unused _loc_to_path / duplicate validation mapping signal | CLEANUP_DEBT | Low | hardening / cleanup | Does not block Phase 5A resume | none required before Phase 5A resume | decide cleanup timing | hardening / cleanup | System Integrity Audit | Tracked cleanup debt |
