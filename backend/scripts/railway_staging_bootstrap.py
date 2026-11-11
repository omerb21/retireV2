"""Initialize only the isolated RETIRE V2 Railway staging database.

The deployment is rejected before any DDL unless its Railway project, environment,
database and runtime are the explicitly configured staging target.
"""
import os
import subprocess
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

PROJECT = "7e49d0ff-a760-4a03-be57-4ee88a4b892c"
ENVIRONMENT = "staging"
DATABASE = "retire_v2_staging"
ROLE = "retire_v2_staging_app"

def main():
    url = os.environ.get("DATABASE_URL", "")
    parsed = make_url(url)
    if (os.environ.get("RAILWAY_PROJECT_ID") != PROJECT
            or os.environ.get("RAILWAY_ENVIRONMENT_NAME") != ENVIRONMENT
            or os.environ.get("APP_ENV") != "production"
            or parsed.database != DATABASE
            or not parsed.host
            or not parsed.host.endswith(".railway.internal")):
        raise RuntimeError("RETIRE_V2_STAGING_BOOTSTRAP_TARGET_INVALID")
    if os.environ.get("CRTISBA_APPLICATION_DB_ROLE") != ROLE:
        raise RuntimeError("RETIRE_V2_STAGING_APPLICATION_ROLE_INVALID")
    engine = create_engine(url, connect_args={"connect_timeout": 10})
    with engine.begin() as conn:
        present = conn.scalar(text("SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname = :name)"), {"name": ROLE})
        if not present:
            conn.execute(text("CREATE ROLE retire_v2_staging_app NOLOGIN"))
    engine.dispose()
    subprocess.run([sys.executable, "-m", "alembic", "-c", "alembic.ini", "upgrade", "head"], check=True)

if __name__ == "__main__":
    main()
