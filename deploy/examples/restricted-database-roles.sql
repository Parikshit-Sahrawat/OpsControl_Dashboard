-- Execute as the migration/schema owner after EVERY Alembic upgrade.
-- These are NOLOGIN capability roles; provision distinct LOGIN identities with
-- externally managed credentials and grant only the needed capability role.
DO $$ BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'opscontrol_app') THEN
        CREATE ROLE opscontrol_app NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'opscontrol_maintenance') THEN
        CREATE ROLE opscontrol_maintenance NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
    END IF;
END $$;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO opscontrol_app, opscontrol_maintenance;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO opscontrol_app;
REVOKE ALL ON alembic_version FROM opscontrol_app;
REVOKE UPDATE, DELETE, TRUNCATE ON security_audit_events FROM opscontrol_app;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO opscontrol_maintenance;
-- SELECT FOR UPDATE used by bounded batches also requires UPDATE privilege.
GRANT UPDATE, DELETE ON metric_samples, log_events, access_sessions, auth_throttle_buckets TO opscontrol_maintenance;
-- Do not grant schema ownership, DDL, TRUNCATE, audit deletion, or migration
-- privileges to either runtime identity. Future tables require explicit grants.
