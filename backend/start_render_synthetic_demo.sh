#!/bin/sh
# Disposable local PostgreSQL, used ONLY by Render's synthetic demo.
set -eu
test "${RENDER:-}" = "true"
unset DATABASE_URL SCENARIO_TEST_POSTGRES_URL
version="$(pg_lsclusters -h | awk 'NR == 1 {print $1}')"
test -n "$version"
# Unix-socket-only: database TCP is not exposed even on loopback.
pg_ctlcluster "$version" main start -o "-c listen_addresses=''"
runuser -u postgres -- psql -v ON_ERROR_STOP=1 -c "CREATE ROLE root LOGIN SUPERUSER"
runuser -u postgres -- createdb -O root retire_v2_synthetic_demo
export SYNTHETIC_DEMO_DATABASE_URL="postgresql+psycopg2://root@/retire_v2_synthetic_demo?host=/var/run/postgresql"
export APP_ENV=test
python -m pytest -q tests/test_render_synthetic_workflow_pg.py
exec python -m uvicorn render_stage6_preview:app --host 0.0.0.0 --port "${PORT:?PORT is required}" --workers 1 --no-proxy-headers
