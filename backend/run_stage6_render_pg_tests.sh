#!/bin/sh
# Render FREE isolated CI runner; never starts the API or connects to external DBs.
# The PostgreSQL tests intentionally require localhost and a fixed database name.
set -eu
echo STAGE6_RENDER_LOCAL_POSTGRES_BOOTSTRAP
if [ "${RENDER:-}" != "true" ]; then
  echo STAGE6_RENDER_GUARD_MISSING
  exit 1
fi
unset DATABASE_URL SCENARIO_TEST_POSTGRES_URL
version="$(pg_lsclusters -h | awk 'NR == 1 {print $1}')"
if [ -z "$version" ]; then
  echo STAGE6_POSTGRES_CLUSTER_NOT_FOUND
  exit 1
fi
pg_ctlcluster "$version" main start
runuser -u postgres -- psql -v ON_ERROR_STOP=1 -c "CREATE ROLE root LOGIN SUPERUSER"
runuser -u postgres -- createdb -O root retire_v2_scenario_test
# One isolated localhost-only test needs an explicit hostname. Generate a fresh
# per-container credential; never print it or place it in Git or Render secrets.
pgpass="$(openssl rand -hex 24)"
runuser -u postgres -- psql -v ON_ERROR_STOP=1 -c "ALTER ROLE root PASSWORD '$pgpass'" >/dev/null
export APP_ENV=test
export SCENARIO_TEST_POSTGRES_URL="postgresql+psycopg2://root:$pgpass@127.0.0.1:5432/retire_v2_scenario_test"
unset pgpass
echo STAGE6_RENDER_LOCAL_POSTGRES_READY
set +e
python -m pytest -q \
  tests/test_health.py \
  tests/test_rtdir_vertical_slice.py \
  tests/test_rtdir_postgresql.py \
  tests/test_scenario_draft.py \
  tests/test_scenario_draft_postgresql.py \
  tests/test_stage6_internal_api.py \
  tests/test_stage6_internal_election_api.py \
  tests/test_stage6_factor_admission_api.py \
  tests/test_stage6_factor_revision_api.py \
  tests/test_stage6_p1a_permission_admission.py \
  tests/test_stage6_p1b_admission_model.py \
  tests/test_stage6_p1b_admission_read_service.py \
  tests/test_stage6_p1b_admission_write_service.py \
  tests/test_stage6_p1b_factor_contract.py \
  tests/test_stage6_p1b_migration.py \
  tests/test_stage6_p1b_postgresql.py \
  tests/test_stage6_p1c_canonical_identity.py \
  tests/test_stage6_p1c_snapshot_contract.py \
  tests/test_stage6_p1c_postgresql.py \
  tests/test_stage6_p1d_estimate.py \
  tests/test_stage6_p1d_pte_kind.py \
  tests/test_stage6_p1d_postgresql.py \
  tests/test_scenario_pension_election_contract.py \
  tests/test_scenario_pension_election_store.py \
  tests/test_scenario_pension_election_store_real_postgresql.py
code=$?
echo STAGE6_RENDER_TEST_EXIT_CODE=$code
# A Render web service may not serve the pension API without signed production
# authentication. This test runner always exits and never binds PORT.
exit 1
