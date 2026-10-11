"""Fail-closed runtime identity checks; migrations use a separate owner."""
import ipaddress
from sqlalchemy import text
from app.core.config import settings
from app.db.session import engine

def trusted_proxies(value: str) -> str:
    entries = [item.strip() for item in value.split(",") if item.strip()]
    if not entries:
        raise ValueError("An explicit trusted proxy address list is required")
    for entry in entries:
        try:
            network = ipaddress.ip_network(entry, strict=False)
        except ValueError:
            raise ValueError("Trusted proxies must be IP addresses or bounded CIDRs") from None
        if network.prefixlen == 0:
            raise ValueError("Trusting every proxy is forbidden")
    return ",".join(entries)

def validate_runtime_database_role() -> None:
    if settings.environment != "production":
        return
    # Do not disclose DSNs, credentials or provider exception details on failure.
    with engine.connect() as connection:
        unsafe = connection.scalar(text("""
            SELECT r.rolsuper OR r.rolcreaterole OR r.rolcreatedb OR r.rolbypassrls
                OR pg_has_role(current_user, d.datdba, 'MEMBER')
                OR EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p')
                    AND pg_has_role(current_user, c.relowner, 'MEMBER'))
                OR has_schema_privilege(current_user, 'public', 'CREATE')
                OR has_table_privilege(current_user, 'security_audit_events', 'UPDATE,DELETE,TRUNCATE')
            FROM pg_roles r JOIN pg_database d ON d.datname = current_database()
            WHERE r.rolname = current_user
        """))
        if unsafe is not False:
            raise RuntimeError("Production requires a restricted non-owner runtime database identity with append-only audit privileges")
