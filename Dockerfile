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
CMD ["sh", "-c", "test \"$WEB_CONCURRENCY\" = 1 && exec python -m uvicorn app.main:app --host 0.0.0.0 --port \"${PORT:?PORT is required}\" --workers 1 --no-proxy-headers"]
