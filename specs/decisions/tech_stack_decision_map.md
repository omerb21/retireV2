**Tech Stack Decision Map**

**1. Frontend Options**

| Option | Pros | Cons | Fit For This Project | Risks |
|---|---|---|---|---|
| Custom React app | Full control over complex planner workflows, audit tables, scenario comparison, validation states, Hebrew/RTL UI, and future expansion. Familiar if current system already uses React. | More design/build effort. Requires discipline to prevent frontend calculations. | High fit. Best for a domain-heavy app with many structured screens and validation-heavy workflows. | Risk of recreating old problem if business logic leaks into hooks/components. Must enforce API/engine-only calculations. |
| Admin template | Faster UI assembly. Good for CRUD-heavy screens: clients, grants, capitalizations, calculation history. | Can feel generic. Complex workflows may fight template structure. May encourage form-first rather than workflow-first design. | Medium-high fit if customized carefully. Useful for V1 fixation screens and internal planner tools. | Template abstractions may make audit/result screens awkward. Styling may dominate architecture decisions. |
| Low-code/no-code | Fastest for simple CRUD. Minimal engineering setup. | Poor fit for deterministic financial engines, strict contracts, auditability, versioning, and custom validation. Harder to enforce source-of-truth rules. | Low fit for production calculation system. Possible only for rough internal prototypes. | Hidden logic, vendor lock-in, weak testing, weak version control, hard to guarantee no duplicate calculations. |
| Server-rendered UI | Simpler deployment and fewer frontend state issues. Strong backend control over rendered data. | Less interactive for scenario workflows. More friction for rich tables, comparisons, client-side validation hints, and future planning UX. | Medium fit. Could work for V1 fixation-only, less ideal for full V2 planning system. | May become cumbersome as scenario builder and comparison flows grow. |

**2. Backend Options**

| Option | Pros | Cons | Fit For This Project | Risks |
|---|---|---|---|---|
| FastAPI | Strong fit for typed contracts, API-first workflow, Python calculation engines, Pydantic validation, clean separation between routes/services/engines. Current system already uses FastAPI. | Requires discipline around architecture. Admin/backoffice must be built separately. | High fit. Especially good for deterministic engine APIs and golden tests. | Old system already had calculations in routers/services, so boundaries must be enforced deliberately. |
| Django | Batteries included: ORM, admin, auth, migrations, permissions. Good for CRUD-heavy business app. | Heavier framework. Engine purity needs careful separation from models/views. API-first style may need DRF or similar. | High fit if admin/auth/data management are major priorities. | Business logic can drift into models/admin/views if not controlled. |
| Flask | Simple and flexible. Easy for small APIs. | Less built-in structure. More decisions required. More manual validation/migrations/auth setup. | Medium-low fit. Flexibility is not ideal when the goal is zero improvisation. | Architecture drift, inconsistent validation, custom glue everywhere. |
| Node/NestJS | Strong modular architecture, TypeScript end-to-end, good API structure. | Calculation logic likely easier in Python given current system and financial/domain code. Adds migration cost. | Medium fit. Better if team strongly prefers TypeScript across stack. | Rewriting domain logic in TS may introduce behavior drift. More risk if current Python knowledge is reused. |

**3. Database Options**

| Option | Pros | Cons | Fit For This Project | Risks |
|---|---|---|---|---|
| PostgreSQL | Strong relational integrity, JSON support for snapshots, production-grade, good migrations, good audit/history support. | More setup than SQLite. Requires hosting/ops decision. | Highest fit for production V2. Best for separating source data, snapshots, outputs, and audit records. | Schema complexity must be managed carefully. |
| SQLite | Simple, local-first, easy development, no server. Good for early local prototype. | Weaker multi-user/concurrent production story. Migration/backup limits for deployed app. | Medium fit for dev/local-only V1. Lower fit for full V2 production. | Can become accidental production DB and block multi-user growth. |
| MySQL | Mature relational DB, widely hosted. | JSON/audit/snapshot ergonomics generally less attractive than PostgreSQL. | Medium fit. Viable but not strongest. | Less ideal for complex snapshots/versioned calculation outputs. |

**4. ORM / Migration Approach**

| Option | Pros | Cons | Fit For This Project | Risks |
|---|---|---|---|---|
| SQLAlchemy + Alembic | Flexible, production-proven, fits FastAPI, explicit models/migrations, good control over data layer. | More manual than Django. Requires migration discipline. | High fit if backend is FastAPI. | Old system used SQLAlchemy-style patterns, but must avoid model/service calculation leakage. |
| Django ORM | Excellent with Django admin/auth/migrations. Fast CRUD productivity. | Best only if Django backend is chosen. Less natural with FastAPI. | High fit if backend is Django. | Logic may drift into models or admin actions. |
| Prisma or equivalent | Strong typed client, good TypeScript fit, clean migrations. | Best with Node/TS stack. Less fit for Python calculation engines. | Medium fit only if Node/NestJS is chosen. | Cross-language mismatch if engines remain Python. |

**5. Hosting Options**

| Option | Pros | Cons | Fit For This Project | Risks |
|---|---|---|---|---|
| Local first | Good for sensitive client data, simple dev/testing, no cloud dependency. | Harder collaboration, backups, updates, remote access. | High fit for early V1/dev and possibly private advisor workflow. | Data loss/backups/security updates become user responsibility. |
| Railway | Fast deployment, managed PostgreSQL, easy for small apps. | Platform limits/costs as app grows. Less control than VPS. | Medium-high fit for early hosted app. | Vendor constraints, background/report jobs may need care. |
| Render | Similar managed deployment, straightforward web service + DB. | Cold starts/free tier limitations, platform constraints. | Medium-high fit for early hosted app. | Performance and cost need monitoring. |
| VPS | Full control, predictable hosting, flexible deployment. | Requires ops knowledge: security, backups, monitoring, updates. | Medium fit if technical ops capacity exists. | Operational burden and security risk if not managed carefully. |

**6. Authentication Options**

| Option | Pros | Cons | Fit For This Project | Risks |
|---|---|---|---|---|
| None / local-only for dev | Fastest for local development. No auth complexity. | Not acceptable for real client data beyond isolated dev/local use. | Good for early dev only. | Accidentally shipping without auth. |
| Email/password | Direct control, simple mental model, works with advisor/admin roles. | Must handle password security, reset flows, sessions/tokens. | Medium-high fit for controlled private app. | Security implementation must be correct. |
| Managed auth provider | Strong security, MFA/SSO options, less custom auth burden. | Added vendor dependency, integration complexity, cost. | High fit for hosted production with real client data. | Vendor lock-in, integration affects user/role model. |

**7. Testing Approach**

| Test Type | Purpose | Fit | Required For V2? |
|---|---|---|---|
| Unit tests | Test pure engines and validators in isolation. | Highest fit for deterministic formulas and contracts. | Required. |
| Integration tests | Test services + DB + engine orchestration. | High fit for snapshot/result persistence and source-of-truth rules. | Required. |
| API tests | Test validation, calculate/save/retrieve flows, and error contracts. | High fit. Prevents router logic drift. | Required. |
| UI smoke tests | Verify screens load, forms submit, outputs display API values. | Medium-high fit. | Required for core workflows. |
| Golden tests | Lock exact numeric behavior for Fixation and future engines. | Critical fit. | Required before implementation acceptance. |

Testing rules:
- Golden tests must be engine-level first.
- API tests must verify saved output equals engine output.
- UI tests must verify display, not calculation.
- Regression tests must cover forbidden patterns where possible.
- No external API dependency in deterministic tests.

**8. Final Recommendation Matrix**

No final stack chosen here. Suitability ranking only.

**Frontend Suitability**

| Rank | Option | Suitability |
|---:|---|---|
| 1 | Custom React app | Highest |
| 2 | Admin template | High for V1/internal CRUD, medium for full V2 |
| 3 | Server-rendered UI | Medium |
| 4 | Low-code/no-code | Low |

**Backend Suitability**

| Rank | Option | Suitability |
|---:|---|---|
| 1 | FastAPI | Highest |
| 2 | Django | High |
| 3 | Node/NestJS | Medium |
| 4 | Flask | Medium-low |

**Database Suitability**

| Rank | Option | Suitability |
|---:|---|---|
| 1 | PostgreSQL | Highest |
| 2 | SQLite | High for local/dev, medium overall |
| 3 | MySQL | Medium |

**ORM / Migration Suitability**

| Rank | Option | Suitability |
|---:|---|---|
| 1 | SQLAlchemy + Alembic | Highest if FastAPI |
| 2 | Django ORM | Highest if Django |
| 3 | Prisma/equivalent | Medium, mainly if Node/NestJS |

**Hosting Suitability**

| Rank | Option | Suitability |
|---:|---|---|
| 1 | Local first | Highest for early V1/dev/private data |
| 2 | Render / Railway | High for early hosted production |
| 3 | VPS | Medium-high with ops capability |

**Authentication Suitability**

| Rank | Option | Suitability |
|---:|---|---|
| 1 | Managed auth provider | Highest for hosted production |
| 2 | Email/password | High for controlled private app |
| 3 | None/local-only | Dev only |

**Testing Suitability**

| Rank | Approach | Suitability |
|---:|---|---|
| 1 | Golden tests | Mandatory |
| 2 | Unit tests | Mandatory |
| 3 | API tests | Mandatory |
| 4 | Integration tests | Mandatory |
| 5 | UI smoke tests | Required for release confidence |