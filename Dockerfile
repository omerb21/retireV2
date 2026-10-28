FROM node:20-slim AS frontend-build
WORKDIR /src/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run test && npm run build

FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 APP_ENV=production
WORKDIR /app
COPY backend/requirements.txt ./backend/requirements.txt
RUN python -m pip install --no-cache-dir -r backend/requirements.txt
# Isolated Render test runner only: local PostgreSQL for existing fail-closed integration tests.
RUN apt-get update && apt-get install -y --no-install-recommends postgresql && rm -rf /var/lib/apt/lists/*
COPY backend/ ./backend/
COPY --from=frontend-build /src/frontend/dist ./frontend/dist
WORKDIR /app/backend
RUN python -m pytest -q tests/test_render_synthetic_stage6.py
CMD ["sh", "-c", "if [ \"${RENDER:-}\" = \"true\" ]; then exec python -m uvicorn render_stage6_preview:app --host 0.0.0.0 --port \"${PORT:?PORT is required}\" --workers 1 --no-proxy-headers; fi; test \"$WEB_CONCURRENCY\" = 1 && exec python -m uvicorn app.main:app --host 0.0.0.0 --port \"${PORT:?PORT is required}\" --workers 1 --no-proxy-headers"]
