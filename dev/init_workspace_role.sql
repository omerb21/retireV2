-- Local synthetic integration environment only. Executed by postgres:16 initdb.
-- The application role is deliberately not the migration/table-owning role.
CREATE ROLE rtdir_synthetic_app LOGIN PASSWORD 'synthetic_local_only_app_password';
