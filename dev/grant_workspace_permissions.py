"""Grant a separate synthetic runtime role after local database migrations.

Only for dev/compose.workspace.yml. Preserves CRTISBA's explicit append-only grants.
No application role may own the migrated tables or be a superuser.
"""
import os

import psycopg2
from psycopg2 import sql

MIGRATION_DATABASE_URL = os.environ["MIGRATION_DATABASE_URL"]
ROLE = os.environ["CRTISBA_APPLICATION_DB_ROLE"]
PROTECTED_TABLE = "retirement_target_date_income_source_basis_decisions"

with psycopg2.connect(MIGRATION_DATABASE_URL) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT rolcanlogin, rolsuper FROM pg_roles WHERE rolname = %s", (ROLE,))
        role = cur.fetchone()
        if role != (True, False):
            raise RuntimeError("Synthetic runtime DB role is missing, superuser, or lacks LOGIN")
        cur.execute("SELECT current_user")
        migration_owner = cur.fetchone()[0]
        if migration_owner == ROLE:
            raise RuntimeError("Synthetic app role must differ from the migration owner")
        cur.execute("SELECT datname FROM pg_database WHERE oid = (SELECT oid FROM pg_database WHERE datname=current_database())")
        database = cur.fetchone()[0]
        cur.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
            sql.Identifier(database), sql.Identifier(ROLE)))
        cur.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(ROLE)))
        cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        tables = [name for (name,) in cur.fetchall()]
        if PROTECTED_TABLE not in tables:
            raise RuntimeError("CRTISBA protected table was not migrated")
        for table in tables:
            if table == PROTECTED_TABLE:
                # Enforced by the migration itself: SELECT/INSERT, no UPDATE/DELETE.
                continue
            cur.execute(sql.SQL("GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE {} TO {}").format(
                sql.Identifier("public", table), sql.Identifier(ROLE)))
        cur.execute("SELECT viewname FROM pg_views WHERE schemaname = 'public'")
        for (view,) in cur.fetchall():
            cur.execute(sql.SQL("GRANT SELECT ON TABLE {} TO {}").format(
                sql.Identifier("public", view), sql.Identifier(ROLE)))
        cur.execute("SELECT sequencename FROM pg_sequences WHERE schemaname = 'public'")
        for (sequence,) in cur.fetchall():
            cur.execute(sql.SQL("GRANT USAGE, SELECT ON SEQUENCE {} TO {}").format(
                sql.Identifier("public", sequence), sql.Identifier(ROLE)))
        cur.execute(
            "SELECT has_table_privilege(%s, %s, 'SELECT'), "
            "has_table_privilege(%s, %s, 'INSERT'), "
            "has_table_privilege(%s, %s, 'UPDATE'), "
            "has_table_privilege(%s, %s, 'DELETE')",
            (ROLE, "public." + PROTECTED_TABLE) * 4,
        )
        privileges = cur.fetchone()
        if privileges != (True, True, False, False):
            raise RuntimeError("CRTISBA append-only DB grants are not preserved")
print("Local DB privileges granted to independent synthetic app role; CRTISBA protections verified.")
