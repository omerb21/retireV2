# V2 Full System Master Spec - Coding Model Version

## 1. System Purpose

V2 is a from-scratch deterministic rebuild of the retirement planning system.

The goal is not to improve V1 and not to copy V1. The goal is to build a clean, auditable system where:
- every calculation has exactly one authority
- every output is reproducible
- every run is immutable
- no model or developer may improvise architecture
- no business logic exists in UI or API routes
- V1 is read-only reference only

## 2. Full System Scope

The full future system may include:
- clients
- client profile
- pension products
- employment and grants
- actual capitalizations
- fixation of rights
- additional income
- capital assets
- tax
- retirement cashflow
- scenarios
- scenario comparison
- final retirement plan
- reports, only after calculation outputs are stable

Out of scope unless explicitly approved:
- LLM/Agent
- marketing automations
- external integrations
- clearinghouse integrations
- OCR/document parsing
- smart recommendations
- PDF in Phase 1
- automatic indexation in Phase 1

## 3. Enforcement Rules

- Calculations only inside engines
- No frontend calculations
- No API route calculations
- No DB access inside engines
- No fallback behavior
- No duplicated authority
- No hidden state
- No mutation of historical results
- Every run is immutable
- Every saved output must be reproducible from its saved input snapshot
- V1 code must not be copied
- If a behavior is not defined, stop and raise an open question

## 4. System Modules

- Client/Profile module: source data only
- Pension module: pension source data and future pension engine
- Employment/Grants module: source data only
- Actual Capitalizations module: explicit actual exemption-consuming events
- Fixation Engine: exemption calculation authority
- Tax Engine: tax authority
- Cashflow Engine: cashflow authority
- Scenario Builder: orchestration only
- Comparison module: compares existing outputs only
- Retirement Plan module: packages saved outputs only

## 5. Source of Truth

- Exempt capital: Fixation Engine
- Exempt pension: Fixation Engine
- Grant impact: Fixation Engine
- Actual capitalization impact: Fixation Engine
- IDF impact: Fixation Engine
- Tax: Tax Engine
- Cashflow: Cashflow Engine
- Scenario: Scenario Builder orchestration
- Final plan: snapshot packaging, not calculation

## 6. Phase 1 of V2 Scope

Phase 1 builds only the fixation workflow:
- Client
- Client Profile
- Employment Records
- Grants
- Actual Capitalizations
- Fixation Parameters
- Fixation Engine
- Fixation Result
- Audit Rows
- Calculation History

Excluded from Phase 1:
- Pension Engine
- Tax Engine
- Cashflow Engine
- Scenario Builder
- Reports/PDF
- LLM/Agent
- External integrations
- Automatic indexation
- Authentication implementation

## 7. Locked Stack

- Backend: FastAPI from scratch
- Frontend: React custom app from scratch
- Database: PostgreSQL
- ORM: SQLAlchemy
- Migrations: Alembic
- Validation: Pydantic
- Tests: Pytest + FastAPI TestClient + Golden tests
- Build mode: local-first
- Auth: deferred, auth-ready only
- Templates and boilerplates: forbidden

## 8. Authority

The V2 Build Management Manual is the operational authority for all implementation work.
