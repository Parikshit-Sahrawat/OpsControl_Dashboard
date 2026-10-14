"""Add internal departments/RBAC without replacing customer identity or ownership."""

from alembic import op
from sqlalchemy import text
import uuid

revision = "0025_provider_department_rbac"
down_revision = "0024_notification_leases"
branch_labels = None
depends_on = None


def upgrade():
    PROVIDER_ID = uuid.UUID("45c4acb0-64fe-532b-ae18-678c1324902d")
    PERMISSIONS = {
        "overview.view": "View operational overview",
        "customers.view": "View granted customer records",
        "customers.create": "Create customer records (no automatic access grant)",
        "customers.update": "Update/deactivate granted customers",
        "resources.view": "View customer resources",
        "resources.create": "Create customer resources",
        "resources.update": "Update customer resources",
        "resources.delete": "Deactivate customer resources",
        "etl.view": "View ETL executions and evidence",
        "etl.configure": "Configure customer ETL definitions",
        "etl.investigate": "Manage ETL investigations (not execute/restart jobs)",
        "incidents.view": "View incident evidence",
        "incidents.acknowledge": "Acknowledge incidents",
        "incidents.manage": "Investigate, annotate and resolve incidents",
        "templates.view": "View policies",
        "templates.manage": "Manage customer policies (shared global catalog remains break-glass controlled)",
        "collectors.view": "View collector configuration/history",
        "collectors.manage": "Configure supported collectors (local execution requires break-glass approval)",
        "logs.view": "View granted logs",
        "logs.manage": "Configure customer log sources/evidence",
        "reports.view": "View customer operational reports/history",
        "access.view": "View internal access administration",
        "access.manage_users": "Manage provider employees and department memberships",
        "access.manage_departments": "Manage provider departments",
        "access.manage_roles": "Configure/assign delegable roles",
        "access.manage_permissions": "Configure customer access and permission overrides",
        "audit.view": "View provider access/security audit",
    }
    ROLE_SPECS = {
        "platform-administrator": (
            "Platform Administrator",
            [
                "access.manage_departments",
                "access.manage_permissions",
                "access.manage_roles",
                "access.manage_users",
                "access.view",
                "audit.view",
                "collectors.manage",
                "collectors.view",
                "customers.create",
                "customers.update",
                "customers.view",
                "etl.configure",
                "etl.investigate",
                "etl.view",
                "incidents.acknowledge",
                "incidents.manage",
                "incidents.view",
                "logs.manage",
                "logs.view",
                "overview.view",
                "reports.view",
                "resources.create",
                "resources.delete",
                "resources.update",
                "resources.view",
                "templates.manage",
                "templates.view",
            ],
        ),
        "access-administrator": (
            "Access Administrator",
            [
                "access.manage_departments",
                "access.manage_permissions",
                "access.manage_roles",
                "access.manage_users",
                "access.view",
                "audit.view",
            ],
        ),
        "resource-administrator": (
            "Resource Administrator",
            [
                "collectors.manage",
                "collectors.view",
                "customers.create",
                "customers.update",
                "customers.view",
                "etl.configure",
                "etl.investigate",
                "etl.view",
                "incidents.acknowledge",
                "incidents.manage",
                "incidents.view",
                "logs.manage",
                "logs.view",
                "overview.view",
                "reports.view",
                "resources.create",
                "resources.delete",
                "resources.update",
                "resources.view",
                "templates.manage",
                "templates.view",
            ],
        ),
        "noc-operator": (
            "NOC Operator",
            [
                "collectors.view",
                "customers.view",
                "etl.investigate",
                "etl.view",
                "incidents.acknowledge",
                "incidents.view",
                "logs.view",
                "overview.view",
                "reports.view",
                "resources.view",
                "templates.view",
            ],
        ),
        "incident-operator": (
            "Incident Operator",
            [
                "collectors.view",
                "customers.view",
                "etl.view",
                "incidents.acknowledge",
                "incidents.manage",
                "incidents.view",
                "logs.view",
                "overview.view",
                "reports.view",
                "resources.view",
                "templates.view",
            ],
        ),
        "read-only-viewer": (
            "Read-Only Viewer",
            [
                "collectors.view",
                "customers.view",
                "etl.view",
                "incidents.view",
                "logs.view",
                "overview.view",
                "reports.view",
                "resources.view",
                "templates.view",
            ],
        ),
        "legacy-customer-administrator": (
            "Legacy Customer Administrator",
            [
                "collectors.manage",
                "collectors.view",
                "customers.update",
                "customers.view",
                "etl.configure",
                "etl.investigate",
                "etl.view",
                "incidents.acknowledge",
                "incidents.manage",
                "incidents.view",
                "logs.manage",
                "logs.view",
                "overview.view",
                "reports.view",
                "resources.create",
                "resources.delete",
                "resources.update",
                "resources.view",
                "templates.manage",
                "templates.view",
            ],
        ),
        "legacy-customer-operator": (
            "Legacy Customer Operator",
            [
                "collectors.view",
                "customers.view",
                "etl.investigate",
                "etl.view",
                "incidents.acknowledge",
                "incidents.manage",
                "incidents.view",
                "logs.view",
                "overview.view",
                "reports.view",
                "resources.view",
                "templates.view",
            ],
        ),
    }
    LEGACY_ROLES = {
        "viewer": "read-only-viewer",
        "operator": "legacy-customer-operator",
        "org_admin": "legacy-customer-administrator",
    }

    def role_id(code):
        return uuid.uuid5(uuid.NAMESPACE_URL, "opscontrol:role:" + code)

    def delegable(key):
        return (
            key in PERMISSIONS and not key.startswith("access.") and key != "audit.view"
        )

    bind = op.get_bind()
    op.execute(
        "\nCREATE TABLE service_providers (\n\tid UUID NOT NULL, \n\tname VARCHAR(160) NOT NULL, \n\tcode VARCHAR(40) NOT NULL, \n\tactive BOOLEAN NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (code)\n)\n\n"
    )
    bind.execute(
        text(
            "INSERT INTO service_providers(id,name,code,active) VALUES (:id,'PTC','DEFAULT',true)"
        ),
        {"id": PROVIDER_ID},
    )
    op.execute(
        "ALTER TABLE users ADD COLUMN service_provider_id uuid, ADD COLUMN employee_id varchar(80), ADD COLUMN full_name varchar(160), ADD COLUMN work_email varchar(254)"
    )
    bind.execute(
        text("UPDATE users SET service_provider_id=:id,full_name=username"),
        {"id": PROVIDER_ID},
    )
    op.execute(
        f"ALTER TABLE users ALTER COLUMN service_provider_id SET DEFAULT '{PROVIDER_ID}'::uuid, ALTER COLUMN service_provider_id SET NOT NULL, ALTER COLUMN full_name SET DEFAULT '', ALTER COLUMN full_name SET NOT NULL"
    )
    op.create_foreign_key(
        "fk_user_service_provider",
        "users",
        "service_providers",
        ["service_provider_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        "uq_user_provider", "users", ["id", "service_provider_id"]
    )
    op.create_unique_constraint(
        "uq_employee_id", "users", ["service_provider_id", "employee_id"]
    )
    op.create_index("ix_users_service_provider_id", "users", ["service_provider_id"])
    op.execute(
        "\nCREATE TABLE departments (\n\tid UUID NOT NULL, \n\tservice_provider_id UUID NOT NULL, \n\tname VARCHAR(160) NOT NULL, \n\tcode VARCHAR(40), \n\tdescription VARCHAR(1000), \n\tmanager_id UUID, \n\tactive BOOLEAN NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_department_provider UNIQUE (id, service_provider_id), \n\tCONSTRAINT uq_department_code UNIQUE (service_provider_id, code), \n\tCONSTRAINT fk_department_manager_provider FOREIGN KEY(manager_id, service_provider_id) REFERENCES users (id, service_provider_id) ON DELETE RESTRICT, \n\tFOREIGN KEY(service_provider_id) REFERENCES service_providers (id) ON DELETE RESTRICT\n)\n\n"
    )
    op.execute(
        "CREATE INDEX ix_departments_service_provider_id ON departments (service_provider_id)"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_department_name_ci ON departments (service_provider_id, lower(name))"
    )
    op.execute(
        "\nCREATE TABLE department_memberships (\n\tid UUID NOT NULL, \n\tservice_provider_id UUID NOT NULL, \n\tdepartment_id UUID NOT NULL, \n\tuser_id UUID NOT NULL, \n\tactive BOOLEAN NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_department_employee UNIQUE (department_id, user_id), \n\tCONSTRAINT fk_membership_department_provider FOREIGN KEY(department_id, service_provider_id) REFERENCES departments (id, service_provider_id) ON DELETE RESTRICT, \n\tCONSTRAINT fk_membership_employee_provider FOREIGN KEY(user_id, service_provider_id) REFERENCES users (id, service_provider_id) ON DELETE RESTRICT, \n\tFOREIGN KEY(service_provider_id) REFERENCES service_providers (id) ON DELETE RESTRICT\n)\n\n"
    )
    op.execute(
        "CREATE INDEX ix_department_memberships_department_id ON department_memberships (department_id)"
    )
    op.execute(
        "CREATE INDEX ix_department_memberships_service_provider_id ON department_memberships (service_provider_id)"
    )
    op.execute(
        "CREATE INDEX ix_department_memberships_user_id ON department_memberships (user_id)"
    )
    op.execute(
        "\nCREATE TABLE permissions (\n\tkey VARCHAR(100) NOT NULL, \n\tdescription VARCHAR(240) NOT NULL, \n\tdelegable BOOLEAN NOT NULL, \n\tPRIMARY KEY (key)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE roles (\n\tid UUID NOT NULL, \n\tservice_provider_id UUID NOT NULL, \n\tname VARCHAR(160) NOT NULL, \n\tcode VARCHAR(80) NOT NULL, \n\tdescription VARCHAR(1000), \n\tactive BOOLEAN NOT NULL, \n\tsystem BOOLEAN NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_role_provider UNIQUE (id, service_provider_id), \n\tCONSTRAINT uq_role_code UNIQUE (service_provider_id, code), \n\tFOREIGN KEY(service_provider_id) REFERENCES service_providers (id) ON DELETE RESTRICT\n)\n\n"
    )
    op.execute(
        "CREATE INDEX ix_roles_service_provider_id ON roles (service_provider_id)"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_role_name_ci ON roles (service_provider_id, lower(name))"
    )
    op.execute(
        "\nCREATE TABLE role_permissions (\n\trole_id UUID NOT NULL, \n\tpermission_key VARCHAR(100) NOT NULL, \n\tPRIMARY KEY (role_id, permission_key), \n\tFOREIGN KEY(role_id) REFERENCES roles (id) ON DELETE CASCADE, \n\tFOREIGN KEY(permission_key) REFERENCES permissions (key) ON DELETE RESTRICT\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE department_role_assignments (\n\tid UUID NOT NULL, \n\tservice_provider_id UUID NOT NULL, \n\tdepartment_id UUID NOT NULL, \n\trole_id UUID NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_department_role UNIQUE (department_id, role_id), \n\tCONSTRAINT fk_department_role_owner FOREIGN KEY(department_id, service_provider_id) REFERENCES departments (id, service_provider_id) ON DELETE RESTRICT, \n\tCONSTRAINT fk_department_role_provider FOREIGN KEY(role_id, service_provider_id) REFERENCES roles (id, service_provider_id) ON DELETE RESTRICT, \n\tFOREIGN KEY(service_provider_id) REFERENCES service_providers (id) ON DELETE RESTRICT\n)\n\n"
    )
    op.execute(
        "CREATE INDEX ix_department_role_assignments_department_id ON department_role_assignments (department_id)"
    )
    op.execute(
        "CREATE INDEX ix_department_role_assignments_role_id ON department_role_assignments (role_id)"
    )
    op.execute(
        "CREATE INDEX ix_department_role_assignments_service_provider_id ON department_role_assignments (service_provider_id)"
    )
    op.execute(
        "\nCREATE TABLE user_role_assignments (\n\tid UUID NOT NULL, \n\tservice_provider_id UUID NOT NULL, \n\tuser_id UUID NOT NULL, \n\trole_id UUID NOT NULL, \n\teffect VARCHAR(5) NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_employee_role UNIQUE (user_id, role_id), \n\tCONSTRAINT ck_employee_role_effect CHECK (effect IN ('ALLOW','DENY')), \n\tCONSTRAINT fk_employee_role_owner FOREIGN KEY(user_id, service_provider_id) REFERENCES users (id, service_provider_id) ON DELETE RESTRICT, \n\tCONSTRAINT fk_employee_role_provider FOREIGN KEY(role_id, service_provider_id) REFERENCES roles (id, service_provider_id) ON DELETE RESTRICT, \n\tFOREIGN KEY(service_provider_id) REFERENCES service_providers (id) ON DELETE RESTRICT\n)\n\n"
    )
    op.execute(
        "CREATE INDEX ix_user_role_assignments_role_id ON user_role_assignments (role_id)"
    )
    op.execute(
        "CREATE INDEX ix_user_role_assignments_service_provider_id ON user_role_assignments (service_provider_id)"
    )
    op.execute(
        "CREATE INDEX ix_user_role_assignments_user_id ON user_role_assignments (user_id)"
    )
    op.execute(
        "\nCREATE TABLE customer_access_grants (\n\tid UUID NOT NULL, \n\tservice_provider_id UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tuser_id UUID, \n\tdepartment_id UUID, \n\trole_id UUID, \n\teffect VARCHAR(5) NOT NULL, \n\tlegacy_membership_id UUID, \n\tPRIMARY KEY (id), \n\tCONSTRAINT ck_grant_one_subject CHECK ((user_id IS NULL) <> (department_id IS NULL)), \n\tCONSTRAINT ck_grant_effect_role CHECK ((effect='ALLOW' AND role_id IS NOT NULL) OR (effect='DENY' AND user_id IS NOT NULL AND role_id IS NULL)), \n\tCONSTRAINT fk_grant_employee_provider FOREIGN KEY(user_id, service_provider_id) REFERENCES users (id, service_provider_id) ON DELETE RESTRICT, \n\tCONSTRAINT fk_grant_department_provider FOREIGN KEY(department_id, service_provider_id) REFERENCES departments (id, service_provider_id) ON DELETE RESTRICT, \n\tCONSTRAINT fk_grant_role_provider FOREIGN KEY(role_id, service_provider_id) REFERENCES roles (id, service_provider_id) ON DELETE RESTRICT, \n\tCONSTRAINT fk_grant_employee_assignment FOREIGN KEY(user_id, role_id) REFERENCES user_role_assignments (user_id, role_id) ON DELETE CASCADE, \n\tCONSTRAINT fk_grant_department_assignment FOREIGN KEY(department_id, role_id) REFERENCES department_role_assignments (department_id, role_id) ON DELETE CASCADE, \n\tFOREIGN KEY(service_provider_id) REFERENCES service_providers (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(role_id) REFERENCES roles (id) ON DELETE RESTRICT, \n\tUNIQUE (legacy_membership_id), \n\tFOREIGN KEY(legacy_membership_id) REFERENCES organization_memberships (id) ON DELETE CASCADE\n)\n\n"
    )
    op.execute(
        "CREATE INDEX ix_customer_access_grants_department_id ON customer_access_grants (department_id)"
    )
    op.execute(
        "CREATE INDEX ix_customer_access_grants_organization_id ON customer_access_grants (organization_id)"
    )
    op.execute(
        "CREATE INDEX ix_customer_access_grants_role_id ON customer_access_grants (role_id)"
    )
    op.execute(
        "CREATE INDEX ix_customer_access_grants_service_provider_id ON customer_access_grants (service_provider_id)"
    )
    op.execute(
        "CREATE INDEX ix_customer_access_grants_user_id ON customer_access_grants (user_id)"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_grant_department ON customer_access_grants (department_id, organization_id, role_id) WHERE department_id IS NOT NULL"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_grant_employee ON customer_access_grants (user_id, organization_id, role_id) NULLS NOT DISTINCT WHERE user_id IS NOT NULL"
    )
    for key, description in PERMISSIONS.items():
        bind.execute(
            text(
                "INSERT INTO permissions(key,description,delegable) VALUES (:k,:d,:a)"
            ),
            {"k": key, "d": description, "a": delegable(key)},
        )
    for code, (name, permissions) in ROLE_SPECS.items():
        rid = role_id(code)
        bind.execute(
            text(
                "INSERT INTO roles(id,service_provider_id,name,code,description,active,system) VALUES (:id,:p,:n,:c,'Reviewed default role',true,true)"
            ),
            {"id": rid, "p": PROVIDER_ID, "n": name, "c": code},
        )
        for key in permissions:
            bind.execute(
                text(
                    "INSERT INTO role_permissions(role_id,permission_key) VALUES (:r,:k)"
                ),
                {"r": rid, "k": key},
            )
    for row in bind.execute(
        text("SELECT id,user_id,organization_id,role FROM organization_memberships")
    ).mappings():
        if row["role"] not in LEGACY_ROLES:
            raise RuntimeError(
                "Unknown legacy membership role; migration refused without an explicit safe mapping"
            )
        rid = role_id(LEGACY_ROLES[row["role"]])
        bind.execute(
            text(
                "INSERT INTO user_role_assignments(id,service_provider_id,user_id,role_id,effect) VALUES (:id,:p,:u,:r,'ALLOW') ON CONFLICT(user_id,role_id) DO NOTHING"
            ),
            {"id": uuid.uuid4(), "p": PROVIDER_ID, "u": row["user_id"], "r": rid},
        )
        bind.execute(
            text(
                "INSERT INTO customer_access_grants(id,service_provider_id,user_id,organization_id,role_id,effect,legacy_membership_id) VALUES (:id,:p,:u,:o,:r,'ALLOW',:m)"
            ),
            {
                "id": uuid.uuid4(),
                "p": PROVIDER_ID,
                "u": row["user_id"],
                "o": row["organization_id"],
                "r": rid,
                "m": row["id"],
            },
        )
    # Database-level UUID and provider-ownership immutability, independent of UI.
    op.execute(
        """CREATE FUNCTION protect_access_identity() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
 IF NEW.id IS DISTINCT FROM OLD.id OR (to_jsonb(NEW)->>'service_provider_id') IS DISTINCT FROM (to_jsonb(OLD)->>'service_provider_id') THEN RAISE EXCEPTION 'Identity and provider ownership are immutable'; END IF; RETURN NEW; END $$"""
    )
    for table in (
        "users",
        "service_providers",
        "departments",
        "department_memberships",
        "roles",
        "department_role_assignments",
        "user_role_assignments",
        "customer_access_grants",
    ):
        op.execute(
            f"CREATE TRIGGER immutable_access_identity BEFORE UPDATE ON {table} FOR EACH ROW EXECUTE FUNCTION protect_access_identity()"
        )


def downgrade():
    # Application rollback retains additive tables. Dropping these would discard
    # configuration and make old membership-only software silently under-enforce.
    raise RuntimeError(
        "Unsafe access-schema downgrade refused. Restore a verified pre-upgrade backup into a separate database, or retain this additive schema for application rollback; see CUSTOMER_DEPARTMENT_RBAC.md."
    )
