"""Synthetic, idempotent fixture executed only inside an owned demo/UAT API container."""

import json
import os
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models import (
    Organization,
    VM,
    JobOrder,
    JobOrderHistory,
    ExecutionStatus,
    ExecutionType,
    DataSource,
    Collector,
)
from app.security.models import User
from app.security.access_models import (
    Department,
    DepartmentMembership,
    UserRoleAssignment,
    CustomerAccessGrant,
)
from app.security.permission_catalog import PROVIDER_ID, role_id
from app.security.passwords import hash_password
from app.unified import compatibility  # Register existing legacy identity bindings.

UAT_USERS_JSON = os.environ.get("OPSCONTROL_UAT_USERS_JSON", "")

if os.getenv("ENVIRONMENT") != "demo" or os.getenv("OPSCONTROL_UAT_FIXTURES") != "1":
    raise SystemExit("Synthetic UAT fixture requires explicit local demo/UAT context")
passwords = json.loads(UAT_USERS_JSON)
with SessionLocal() as db:
    departments = {
        d.code: d
        for d in db.scalars(
            select(Department).where(Department.service_provider_id == PROVIDER_ID)
        )
    }
    customers = {}
    for code, label in (
        ("UAT-A", "Synthetic UAT Customer A"),
        ("UAT-B", "Synthetic UAT Customer B"),
    ):
        customer = db.scalar(select(Organization).where(Organization.code == code))
        if customer is None:
            customer = Organization(code=code, name=label)
            db.add(customer)
            db.flush()
        customers[code] = customer
        vm = db.scalar(
            select(VM).where(
                VM.organization_id == customer.id,
                VM.hostname == f"{code.lower()}-vm.example.test",
            )
        )
        if vm is None:
            vm = VM(
                organization_id=customer.id,
                hostname=f"{code.lower()}-vm.example.test",
                environment="SANDBOX",
                os="Linux",
                monitoring_enabled=False,
            )
            db.add(vm)
            db.flush()
        job = db.scalar(
            select(JobOrder).where(
                JobOrder.organization_id == customer.id,
                JobOrder.name == f"{code} ETL synthetic",
            )
        )
        if job is None:
            job = JobOrder(
                organization_id=customer.id,
                vm_id=vm.id,
                name=f"{code} ETL synthetic",
                environment="SANDBOX",
                monitoring_enabled=False,
            )
            db.add(job)
            db.flush()
            status = (
                ExecutionStatus.FAILED if code == "UAT-A" else ExecutionStatus.SUCCESS
            )
            now = datetime.now(timezone.utc)
            db.add(
                JobOrderHistory(
                    job_order_id=job.id,
                    execution_type=ExecutionType.SCHEDULED,
                    status=status,
                    started_at=now - timedelta(hours=1),
                    ended_at=now - timedelta(minutes=55),
                    detected_at=now - timedelta(hours=1),
                    source_result="SYNTHETIC_UAT_ONLY",
                )
            )
        source = db.scalar(
            select(DataSource).where(
                DataSource.organization_id == customer.id,
                DataSource.name == f"{code} API synthetic",
            )
        )
        if source is None:
            source = DataSource(
                organization_id=customer.id,
                name=f"{code} API synthetic",
                source_type="API",
                endpoint=f"https://{code.lower()}.example.test/health",
                status="UNKNOWN",
                enabled=False,
                description="SYNTHETIC UAT; no live telemetry",
            )
            db.add(source)
            db.flush()
        if (
            db.scalar(
                select(Collector).where(
                    Collector.data_source_id == source.id,
                    Collector.name == f"{code} inactive collector",
                )
            )
            is None
        ):
            db.add(
                Collector(
                    data_source_id=source.id,
                    name=f"{code} inactive collector",
                    collector_type="HTTP",
                    enabled=False,
                    status="STOPPED",
                    interval_seconds=60,
                )
            )
        host_source = db.scalar(
            select(DataSource).where(
                DataSource.organization_id == customer.id,
                DataSource.name == f"{code} VM synthetic",
            )
        )
        if host_source is None:
            host_source = DataSource(
                organization_id=customer.id,
                name=f"{code} VM synthetic",
                source_type="LINUX_HOST",
                endpoint=f"{code.lower()}-vm.example.test",
                status="UNKNOWN",
                enabled=False,
                description="SYNTHETIC UAT; no host connection",
            )
            db.add(host_source)
            db.flush()
        if (
            db.scalar(
                select(Collector).where(
                    Collector.data_source_id == host_source.id,
                    Collector.name == f"{code} inactive host collector",
                )
            )
            is None
        ):
            db.add(
                Collector(
                    data_source_id=host_source.id,
                    name=f"{code} inactive host collector",
                    collector_type="SSH",
                    enabled=False,
                    status="STOPPED",
                    interval_seconds=60,
                )
            )
    for username, code, dept, role_code, grants in (
        ("uat-viewer-a", "A", "NOC", "read-only-viewer", ("UAT-A",)),
        ("uat-admin-b", "B", "SYSTEMS", "resource-administrator", ("UAT-B",)),
        ("uat-operator-ab", "AB", "APP-SUPPORT", "noc-operator", ("UAT-A", "UAT-B")),
    ):
        user = db.scalar(select(User).where(User.username == username))
        if user is None:
            user = User(
                username=username,
                full_name=f"Synthetic UAT {code}",
                password_hash=hash_password(passwords[username]),
                platform_admin=False,
            )
            db.add(user)
            db.flush()
        department = departments[dept]
        if (
            db.scalar(
                select(DepartmentMembership).where(
                    DepartmentMembership.user_id == user.id,
                    DepartmentMembership.department_id == department.id,
                )
            )
            is None
        ):
            db.add(
                DepartmentMembership(
                    user_id=user.id,
                    department_id=department.id,
                    service_provider_id=PROVIDER_ID,
                )
            )
        rid = role_id(role_code)
        if (
            db.scalar(
                select(UserRoleAssignment).where(
                    UserRoleAssignment.user_id == user.id,
                    UserRoleAssignment.role_id == rid,
                )
            )
            is None
        ):
            db.add(
                UserRoleAssignment(
                    user_id=user.id, role_id=rid, service_provider_id=PROVIDER_ID
                )
            )
        db.flush()
        for customer_code in grants:
            cid = customers[customer_code].id
            if (
                db.scalar(
                    select(CustomerAccessGrant).where(
                        CustomerAccessGrant.user_id == user.id,
                        CustomerAccessGrant.role_id == rid,
                        CustomerAccessGrant.organization_id == cid,
                    )
                )
                is None
            ):
                db.add(
                    CustomerAccessGrant(
                        user_id=user.id,
                        role_id=rid,
                        organization_id=cid,
                        service_provider_id=PROVIDER_ID,
                    )
                )
    db.commit()
    print(
        json.dumps(
            {
                "customers": {code: str(row.id) for code, row in customers.items()},
                "users": {
                    name: str(db.scalar(select(User.id).where(User.username == name)))
                    for name in passwords
                },
                "fixture": "SYNTHETIC_UAT_ONLY",
            },
            sort_keys=True,
        )
    )
