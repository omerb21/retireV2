**Project Initialization Spec: V2 Phase 1**

**1. Project Naming**

Project name:
- `Retirement Planning V2`

Repository name:
- `retirement-planning-v2`

Internal short name:
- `retire-v2`

Rules:
- Name must clearly distinguish V2 from the existing V1 codebase.
- V1 must remain reference-only.
- V2 must not be initialized inside the V1 source tree unless explicitly approved later.

**2. High-Level Project Structure**

Conceptual structure only:

- Backend root  
  Contains the FastAPI application, backend configuration, API shell, database setup, contracts, services, engines, and tests.

- Frontend root  
  Contains the custom React application, routing shell, screen shells, API client boundary, and frontend tests.

- Shared concepts  
  Shared business concepts may exist only as documented contracts, not as imported code shared between frontend and backend at initialization. The backend remains the authority for validation contracts and calculation outputs.

Initialization must establish separation between:

- Backend application shell.
- Frontend application shell.
- Database/migration setup.
- Test setup.
- Documentation/spec references.

No business module implementation happens during initialization.

**3. Backend Initialization Plan**

Required base components:

- FastAPI app entry point.
- Application configuration layer.
- Environment variable loading boundary.
- Dependency layer placeholder.
- Database connection boundary placeholder.
- Health/status endpoint only.
- Error response convention placeholder.
- Pydantic availability confirmed.
- Test client availability confirmed.

What must exist before any engine is written:

- Backend app can start locally.
- Backend exposes a non-business health/status endpoint.
- Configuration can read local environment values.
- Database connection configuration is defined conceptually.
- Test framework can import the app.
- API layer is structurally separated from future services and engines.
- No V1 imports exist.
- No business routes exist.

What must NOT be created yet:

- Fixation Engine.
- Domain formulas.
- Client API logic.
- Grant API logic.
- Fixation API logic.
- Database models for business tables.
- Alembic migrations for business schema.
- Authentication implementation.
- LLM/tool endpoints.
- External integration clients.
- PDF/report generation.
- Scenario/pension/tax/cashflow modules.

Backend initialization acceptance:

- FastAPI app shell exists.
- Health/status endpoint works.
- TestClient can call health/status.
- App has no business behavior.
- App has no V1 dependency.

**4. Frontend Initialization Plan**

Minimal React app setup:

- Custom React app from scratch.
- App shell only.
- Basic route container.
- Placeholder navigation structure for Phase 1 screens.
- API client boundary placeholder.
- Error/loading display convention placeholder.
- No visual design system beyond minimal shell.

Routing approach, conceptual:

- Client List route.
- Create Client route placeholder.
- Client Profile route placeholder.
- Employment route placeholder.
- Grants route placeholder.
- Actual Capitalizations route placeholder.
- Fixation Parameters route placeholder.
- Fixation Result route placeholder.
- Fixation History route placeholder.

At initialization, these may be placeholders only. They must not contain business forms or calculations yet.

State management approach, conceptual:

- Keep state local by default for screen shell state.
- Server data must eventually come from API calls.
- No global financial state store at initialization.
- No frontend calculation state.
- No persistence of business results in browser storage.

What must NOT be created yet:

- Business forms.
- Calculation helpers.
- Fixation result formatting logic beyond placeholder text.
- Local cap tables.
- Grant impact utilities.
- IDF utilities.
- Scenario UI.
- Pension/tax/cashflow UI.
- Authentication screens unless explicitly required for shell only.

Frontend initialization acceptance:

- React app starts locally.
- Placeholder routes render.
- Navigation between placeholder screens works.
- No business calculations exist.
- No V1 components are copied.

**5. Database Initialization Plan**

How PostgreSQL is introduced:

- PostgreSQL is the target database for V2.
- Local-first configuration must support connecting to a local PostgreSQL instance.
- Database URL is supplied through environment configuration.
- Database connection boundary is initialized before business models exist.

When Alembic is initialized:

- Alembic is initialized during project setup after backend configuration exists.
- Alembic must be present before business schema work begins.
- The initial migration state may be empty or metadata-only, depending on implementation decision later.
- Business migrations begin only in the database-model phase, not initialization.

What is not migrated yet:

- No `clients` table.
- No `client_profiles` table.
- No `employment_records` table.
- No `grants` table.
- No `actual_capitalizations` table.
- No `fixation_runs` table.
- No `fixation_input_snapshots` table.
- No `fixation_results` table.
- No `fixation_audit_rows` table.
- No `fixation_validation_errors` table.
- No users/auth schema.
- No pension/tax/cashflow/scenario/report tables.

Database initialization acceptance:

- Local PostgreSQL connection settings are defined.
- Backend can be configured for database connectivity.
- Alembic is ready for future migrations.
- No business schema is prematurely created.

**6. Environment Setup**

Local-first rules:

- Development runs locally.
- No cloud dependency during Phase 1 initialization.
- No external API dependency.
- No authentication provider dependency.
- No production secrets required.
- V1 project path must not be used as runtime dependency.

Conceptual environment variables:

- Application environment name.
- Backend host/port.
- Frontend host/port.
- Database URL.
- Database echo/logging flag.
- CORS allowed origins for local frontend.
- Test database URL or test database mode.
- Logging level.
- Optional app version/build label.

Environment rules:

- No business values in environment variables.
- No cap tables in environment variables.
- No exemption percentages in environment variables.
- No fallback year values in environment variables.
- No V1 paths in environment variables except optional manual reference notes outside runtime.

**7. Testing Initialization**

When pytest is initialized:

- Pytest is initialized with the backend shell.
- First backend test verifies the app imports and health/status endpoint responds.
- TestClient setup is created before business APIs are implemented.

When API test structure is created:

- API test structure is created during initialization.
- Only health/status tests exist at initialization.
- Business API test placeholders may be named conceptually but must not assert nonexistent behavior.

What is not tested yet:

- Fixation Engine.
- Golden Cases.
- Client CRUD.
- Grants.
- Actual capitalizations.
- Fixation API.
- Database persistence.
- Alembic migrations.
- Frontend workflows.
- UI smoke tests.
- Authentication.
- External integrations.

Frontend testing initialization:

- A basic frontend test setup may be initialized only to verify app shell rendering.
- No business behavior tests yet.
- No calculation tests in frontend.

Testing initialization acceptance:

- Backend health/status test passes.
- Frontend app shell test, if included, passes.
- No business tests are written before business components exist.
- Test setup does not import V1.

**8. First Milestone**

Milestone name:
- `V2 Phase 1 Initialization Complete`

Exact state after completion:

Working:

- New V2 project identity is established.
- Backend FastAPI shell starts locally.
- Backend health/status endpoint works.
- Backend configuration layer exists.
- Backend dependency/database boundaries exist as placeholders.
- PostgreSQL configuration path is defined.
- Alembic is initialized and ready for future schema work.
- Pytest/TestClient can test backend shell.
- Frontend React shell starts locally.
- Frontend placeholder routing works.
- Placeholder Phase 1 screen routes exist conceptually/render as empty shells.
- Local environment configuration is documented conceptually.
- No V1 code is imported or copied.

Intentionally not implemented:

- No Fixation Engine.
- No formulas.
- No domain contracts implemented.
- No business database tables.
- No business migrations.
- No client CRUD.
- No grant CRUD.
- No actual capitalization CRUD.
- No fixation calculation API.
- No calculation history.
- No real UI forms.
- No authentication.
- No external integrations.
- No PDF/reporting.
- No pension/tax/cashflow/scenario functionality.

Milestone acceptance:

- System shell is runnable.
- Tests prove shell health.
- No business behavior exists yet.
- Architecture boundaries are ready for Phase 1 contract implementation.

**9. Forbidden Actions At Initialization Stage**

Strictly forbidden:

- Writing engine logic.
- Writing domain formulas.
- Writing fixation calculation code.
- Creating Golden Case implementation.
- Creating business API logic.
- Creating client/grant/capitalization CRUD logic.
- Creating business database schema.
- Creating business migrations.
- Copying V1 code.
- Copying V1 folders.
- Copying V1 models.
- Copying V1 routers.
- Copying V1 services.
- Copying V1 frontend components.
- Reusing V1 fallback behavior.
- Reusing V1 LLM/tool logic.
- Reusing V1 scenario mutation logic.
- Adding local cap tables.
- Adding frontend calculation utilities.
- Adding hidden defaults.
- Implementing authentication.
- Adding external integrations.
- Adding PDF/report logic.
- Adding pension/tax/cashflow/scenario modules.
- Introducing templates or boilerplates.
- Expanding UI beyond shell/placeholders.
- Adding business values to environment variables.

If any forbidden action appears necessary, initialization must stop and the decision must be escalated before implementation continues.