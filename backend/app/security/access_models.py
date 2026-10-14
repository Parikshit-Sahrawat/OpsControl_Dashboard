"""Internal provider identity and explicit customer grants, independent of customers."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    String,
    ForeignKey,
    ForeignKeyConstraint,
    CheckConstraint,
    UniqueConstraint,
    Index,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base
from app.security.permission_catalog import PROVIDER_ID


def uid():
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def provider():
    return mapped_column(
        UUID(as_uuid=True),
        ForeignKey("service_providers.id", ondelete="RESTRICT"),
        nullable=False,
        default=lambda: PROVIDER_ID,
        index=True,
    )


class ServiceProvider(Base):
    __tablename__ = "service_providers"
    id: Mapped[uuid.UUID] = uid()
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Department(Base):
    __tablename__ = "departments"
    id: Mapped[uuid.UUID] = uid()
    service_provider_id: Mapped[uuid.UUID] = provider()
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    code: Mapped[str | None] = mapped_column(String(40))
    description: Mapped[str | None] = mapped_column(String(1000))
    manager_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    __table_args__ = (
        UniqueConstraint("id", "service_provider_id", name="uq_department_provider"),
        UniqueConstraint("service_provider_id", "code", name="uq_department_code"),
        ForeignKeyConstraint(
            ["manager_id", "service_provider_id"],
            ["users.id", "users.service_provider_id"],
            name="fk_department_manager_provider",
            ondelete="RESTRICT",
        ),
        Index(
            "uq_department_name_ci",
            "service_provider_id",
            text("lower(name)"),
            unique=True,
        ),
    )


class DepartmentMembership(Base):
    __tablename__ = "department_memberships"
    id: Mapped[uuid.UUID] = uid()
    service_provider_id: Mapped[uuid.UUID] = provider()
    department_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    __table_args__ = (
        UniqueConstraint("department_id", "user_id", name="uq_department_employee"),
        ForeignKeyConstraint(
            ["department_id", "service_provider_id"],
            ["departments.id", "departments.service_provider_id"],
            name="fk_membership_department_provider",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["user_id", "service_provider_id"],
            ["users.id", "users.service_provider_id"],
            name="fk_membership_employee_provider",
            ondelete="RESTRICT",
        ),
    )


class Permission(Base):
    __tablename__ = "permissions"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    description: Mapped[str] = mapped_column(String(240), nullable=False)
    delegable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[uuid.UUID] = uid()
    service_provider_id: Mapped[uuid.UUID] = provider()
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000))
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    __table_args__ = (
        UniqueConstraint("id", "service_provider_id", name="uq_role_provider"),
        UniqueConstraint("service_provider_id", "code", name="uq_role_code"),
        Index(
            "uq_role_name_ci", "service_provider_id", text("lower(name)"), unique=True
        ),
    )


class RolePermission(Base):
    __tablename__ = "role_permissions"
    role_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    permission_key: Mapped[str] = mapped_column(
        ForeignKey("permissions.key", ondelete="RESTRICT"), primary_key=True
    )

    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )


class DepartmentRoleAssignment(Base):
    __tablename__ = "department_role_assignments"
    id: Mapped[uuid.UUID] = uid()
    service_provider_id: Mapped[uuid.UUID] = provider()
    department_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    __table_args__ = (
        UniqueConstraint("department_id", "role_id", name="uq_department_role"),
        ForeignKeyConstraint(
            ["department_id", "service_provider_id"],
            ["departments.id", "departments.service_provider_id"],
            name="fk_department_role_owner",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["role_id", "service_provider_id"],
            ["roles.id", "roles.service_provider_id"],
            name="fk_department_role_provider",
            ondelete="RESTRICT",
        ),
    )


class UserRoleAssignment(Base):
    __tablename__ = "user_role_assignments"
    id: Mapped[uuid.UUID] = uid()
    service_provider_id: Mapped[uuid.UUID] = provider()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    effect: Mapped[str] = mapped_column(String(5), nullable=False, default="ALLOW")
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_employee_role"),
        CheckConstraint("effect IN ('ALLOW','DENY')", name="ck_employee_role_effect"),
        ForeignKeyConstraint(
            ["user_id", "service_provider_id"],
            ["users.id", "users.service_provider_id"],
            name="fk_employee_role_owner",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["role_id", "service_provider_id"],
            ["roles.id", "roles.service_provider_id"],
            name="fk_employee_role_provider",
            ondelete="RESTRICT",
        ),
    )


class CustomerAccessGrant(Base):
    __tablename__ = "customer_access_grants"
    id: Mapped[uuid.UUID] = uid()
    service_provider_id: Mapped[uuid.UUID] = provider()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), index=True
    )
    role_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("roles.id", ondelete="RESTRICT"), index=True
    )
    effect: Mapped[str] = mapped_column(String(5), nullable=False, default="ALLOW")
    legacy_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organization_memberships.id", ondelete="CASCADE"), unique=True
    )
    __table_args__ = (
        CheckConstraint(
            "(user_id IS NULL) <> (department_id IS NULL)", name="ck_grant_one_subject"
        ),
        CheckConstraint(
            "(effect='ALLOW' AND role_id IS NOT NULL) OR (effect='DENY' AND user_id IS NOT NULL AND role_id IS NULL)",
            name="ck_grant_effect_role",
        ),
        ForeignKeyConstraint(
            ["user_id", "service_provider_id"],
            ["users.id", "users.service_provider_id"],
            name="fk_grant_employee_provider",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["department_id", "service_provider_id"],
            ["departments.id", "departments.service_provider_id"],
            name="fk_grant_department_provider",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["role_id", "service_provider_id"],
            ["roles.id", "roles.service_provider_id"],
            name="fk_grant_role_provider",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["user_id", "role_id"],
            ["user_role_assignments.user_id", "user_role_assignments.role_id"],
            name="fk_grant_employee_assignment",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["department_id", "role_id"],
            [
                "department_role_assignments.department_id",
                "department_role_assignments.role_id",
            ],
            name="fk_grant_department_assignment",
            ondelete="CASCADE",
        ),
        Index(
            "uq_grant_employee",
            "user_id",
            "organization_id",
            "role_id",
            unique=True,
            postgresql_where=text("user_id IS NOT NULL"),
            postgresql_nulls_not_distinct=True,
        ),
        Index(
            "uq_grant_department",
            "department_id",
            "organization_id",
            "role_id",
            unique=True,
            postgresql_where=text("department_id IS NOT NULL"),
        ),
    )
