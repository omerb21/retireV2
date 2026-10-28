FROM node:20-slim AS frontend-build
WORKDIR /src/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 APP_ENV=production
WORKDIR /app
COPY backend/requirements.txt ./backend/requirements.txt
RUN python -m pip install --no-cache-dir -r backend/requirements.txt
COPY backend/ ./backend/
COPY --from=frontend-build /src/frontend/dist ./frontend/dist
WORKDIR /app/backend
CMD ["sh", "-c", "if [ \"${RENDER:-}\" = \"true\" ]; then echo STAGE6_RENDER_SAFE_TEST_MODE; APP_ENV=test python -m pytest -q tests/test_stage6_internal_api.py tests/test_stage6_internal_election_api.py tests/test_stage6_factor_admission_api.py tests/test_stage6_factor_revision_api.py tests/test_stage6_p1a_permission_admission.py tests/test_stage6_p1b_admission_model.py tests/test_stage6_p1b_admission_read_service.py tests/test_stage6_p1b_admission_write_service.py tests/test_stage6_p1b_factor_contract.py tests/test_stage6_p1b_migration.py tests/test_stage6_p1c_canonical_identity.py tests/test_stage6_p1c_snapshot_contract.py tests/test_stage6_p1d_estimate.py tests/test_stage6_p1d_pte_kind.py tests/test_scenario_pension_election_contract.py tests/test_scenario_pension_election_store.py; result=$?; echo STAGE6_RENDER_TEST_EXIT_CODE=$result; exit 1; fi; test \"$WEB_CONCURRENCY\" = 1 && exec python -m uvicorn app.main:app --host 0.0.0.0 --port \"${PORT:?PORT is required}\" --workers 1 --no-proxy-headers"]
