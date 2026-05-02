# Tech Stack Lock

## Final Locked Stack

- Frontend: React custom app, built from scratch
- Backend: FastAPI, built from scratch
- Backend language: Python
- Frontend language: TypeScript
- Database: PostgreSQL
- ORM: SQLAlchemy
- Migrations: Alembic
- Validation: Pydantic
- Testing: Pytest + FastAPI TestClient + Golden tests
- Hosting during build: local-first
- Production hosting: decided later, Railway/Render are acceptable candidates
- Authentication in Phase 1: deferred, auth-ready metadata only
- Templates: forbidden
- Boilerplates: forbidden
- External business logic: forbidden

## Backend Strategy

Build from scratch. Do not use full-stack templates or existing backend systems.

Allowed:
- FastAPI library
- Pydantic
- SQLAlchemy
- Alembic
- Pytest
- Standard Python tooling

Forbidden:
- imported SaaS boilerplates
- generated admin systems as architecture
- copied V1 structure
- copied V1 code
- business logic from external templates

## Frontend Strategy

Build a custom React app from scratch.

Allowed:
- React
- TypeScript
- routing library if needed
- minimal styling/layout

Forbidden:
- admin templates
- low-code/no-code
- frontend calculation helpers
- local business formulas
- copied V1 components

## Database Strategy

Use PostgreSQL as target database from the beginning.

Rules:
- SQLite may not become accidental production DB.
- PostgreSQL must support snapshots, audit and history.
- No database triggers or database functions may be business calculation authority.

## Auth Strategy

No authentication implementation in Phase 1.
Data model may include nullable created_by / future user references if needed.

## Testing Strategy

Required:
- contract tests
- engine unit tests
- golden tests
- persistence tests
- service tests
- API tests
- UI smoke tests
- full regression gate
