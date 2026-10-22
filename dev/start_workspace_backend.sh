#!/bin/sh
# Ephemeral local integration stack only. Never use this entrypoint for production.
set -eu
: "${MIGRATION_DATABASE_URL:?local migration URL required}"
: "${APPLICATION_DATABASE_URL:?local application URL required}"
: "${CRTISBA_APPLICATION_DB_ROLE:?CRTISBA role required}"
export DATABASE_URL="$MIGRATION_DATABASE_URL"
alembic upgrade head
python /opt/workspace/grant_workspace_permissions.py
export DATABASE_URL="$APPLICATION_DATABASE_URL"
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
