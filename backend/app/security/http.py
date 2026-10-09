"""Authenticated human API; audited platform-only identity administration.

Server-side role checks and ORM tenant scopes are mandatory even when a
frontend organization filter is supplied. Worker credentials are a distinct
principal type and NEVER authenticate against these user endpoints.
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.db.session import SessionLocal
from app.security.audit import log_event
from app.security.models import AccessSession, OrganizationMembership, SecurityAuditEvent, User, WorkerIdentity
from app.security.passwords import hash_password, verify_password
from app.security.scope import Principal, current_principal
from app.security.throttle import failed_login, login_allowed, successful_login

router = APIRouter(prefix="/api/v1/auth", tags=["Identity"])
worker_router = APIRouter(prefix="/api/v1/worker", tags=["Worker Identity"])
_ALLOWED_PUBLIC = {"/", "/health", "/health/db", "/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc", "/api/v1/auth/login"}
_WORKER_PUBLIC_GATE = {"/api/v1/worker/whoami"}
_ROLE_VALUES = {"viewer", "operator", "org_admin"}

class Login(BaseModel):
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=1024)

class UserCreate(Login):
    platform_admin: bool = False

class MemberCreate(BaseModel):
    user_id: UUID
    organization_id: UUID
    role: str

class MemberPatch(BaseModel):
    role: str

class UserStatus(BaseModel):
    active: bool

class PasswordReset(BaseModel):
    new_password: str = Field(min_length=12, max_length=1024)

class WorkerCreate(BaseModel):
    organization_id: UUID
    name: str = Field(min_length=1, max_length=120)
    expires_in_days: int = Field(default=30, ge=1, le=90)

def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def identify(db, token: str):
    if not token or len(token) > 256:
        return None
    row = db.scalar(select(AccessSession).where(AccessSession.token_hash == token_digest(token)))
    if row is None or row.expires_at.replace(tzinfo=timezone.utc) <= datetime.now(timezone.utc):
        return None
    user = db.get(User, row.user_id)
    if user is None or not user.active:
        return None
    from app.models import Organization
    memberships = db.execute(
        select(OrganizationMembership.organization_id, OrganizationMembership.role)
        .join(Organization, Organization.id == OrganizationMembership.organization_id)
        .where(OrganizationMembership.user_id == user.id, Organization.active.is_(True))
    ).all()
    return Principal(user.id, user.username, user.platform_admin, dict(memberships))

def actor():
    principal = current_principal.get()
    if principal is None:
        raise HTTPException(401, "Authentication required")
    return principal

def require_admin():
    principal = actor()
    if not principal.platform_admin:
        raise HTTPException(403, "Platform administrator required")
    return principal

def revoke_sessions(db, user_id):
    for session in db.scalars(select(AccessSession).where(AccessSession.user_id == user_id)).all():
        db.delete(session)

def _audit_denial(principal, status: int, path: str, request_id=None):
    # No URL queries, credentials, header values or source response data.
    with SessionLocal() as db:
        log_event(db, event_type="HTTP_AUTH_DENIED", outcome="DENIED",
                  actor_id=principal.user_id if principal else None,
                  target_type="route", target_id=path[:120], request_id=request_id)
        db.commit()
    return JSONResponse({"detail": "Authentication required" if status == 401 else "Access denied"},
                        status_code=status, headers={"WWW-Authenticate": "Bearer"} if status == 401 else None)

class IdentityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path.rstrip("/") or "/"
        if request.method == "OPTIONS" or path in _ALLOWED_PUBLIC or path in _WORKER_PUBLIC_GATE:
            return await call_next(request)
        if not path.startswith("/api/"):
            return await call_next(request)
        header = request.headers.get("authorization", "")
        parts = header.split()
        if len(parts) != 2 or parts[0] != "Bearer":
            return _audit_denial(None, 401, path)
        with SessionLocal() as db:
            principal = identify(db, parts[1])
        if principal is None:
            return _audit_denial(None, 401, path)
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            if path == "/api/v1/auth/logout":
                pass
            elif path.startswith("/api/v1/auth/") and not principal.platform_admin:
                return _audit_denial(principal, 403, path)
            elif path.startswith("/api/v1/organizations") and request.method == "POST" and not principal.platform_admin:
                return _audit_denial(principal, 403, path)
            elif path.startswith("/api/v1/monitoring/templates") and not principal.platform_admin:
                return _audit_denial(principal, 403, path)
            elif not principal.platform_admin and not any(role == "org_admin" for role in principal.roles.values()):
                investigation_route = "/investigation/" in path
                if not (investigation_route and any(role == "operator" for role in principal.roles.values())):
                    return _audit_denial(principal, 403, path)
        ctx = current_principal.set(principal)
        try:
            response = await call_next(request)
            if request.method not in {"GET", "HEAD", "OPTIONS"}:
                with SessionLocal() as db:
                    log_event(db, event_type="CONFIG_OR_ACTION", outcome="SUCCESS" if response.status_code < 400 else "FAILURE",
                              actor_id=principal.user_id, target_type="route", target_id=path)
                    db.commit()
            return response
        finally:
            current_principal.reset(ctx)

@router.post("/login")
def login(payload: Login, request: Request):
    username = payload.username.strip().lower()
    ip = request.client.host if request.client else "unknown"
    with SessionLocal() as db:
        if not login_allowed(db, username, ip):
            log_event(db, event_type="LOGIN_RATE_LIMIT", outcome="DENIED", target_type="identity")
            db.commit()
            raise HTTPException(429, "Too many login attempts; try again later", headers={"Retry-After": "900"})
        user = db.scalar(select(User).where(User.username == username))
        if user is None or not user.active or not verify_password(payload.password, user.password_hash):
            failed_login(db, username, ip)
            log_event(db, event_type="LOGIN", outcome="FAILURE", target_type="identity")
            db.commit()
            raise HTTPException(401, "Invalid username or password")
        successful_login(db, username)
        token = secrets.token_urlsafe(48)
        expiry = datetime.now(timezone.utc) + timedelta(hours=12)
        db.add(AccessSession(user_id=user.id, token_hash=token_digest(token), expires_at=expiry))
        log_event(db, event_type="LOGIN", outcome="SUCCESS", actor_id=user.id, target_type="identity", target_id=user.id)
        db.commit()
        return {"access_token": token, "token_type": "bearer", "expires_at": expiry.isoformat()}

@router.get("/me")
def me():
    principal = actor()
    return {"id": str(principal.user_id), "username": principal.username,
            "platform_admin": principal.platform_admin,
            "memberships": [{"organization_id": str(k), "role": v} for k, v in principal.roles.items()]}

@router.post("/logout", status_code=204)
def logout(request: Request):
    principal = actor()
    digest = token_digest(request.headers.get("authorization", "").split()[1])
    with SessionLocal() as db:
        row = db.scalar(select(AccessSession).where(AccessSession.token_hash == digest))
        if row: db.delete(row)
        log_event(db, event_type="LOGOUT", outcome="SUCCESS", actor_id=principal.user_id, target_type="identity")
        db.commit()

@router.post("/users", status_code=201)
def create_user(payload: UserCreate):
    principal = require_admin()
    username = payload.username.strip().lower()
    if not username:
        raise HTTPException(422, "Username required")
    with SessionLocal() as db:
        user = User(username=username, password_hash=hash_password(payload.password), platform_admin=payload.platform_admin)
        db.add(user)
        try:
            db.flush()
            log_event(db, event_type="USER_CREATE", outcome="SUCCESS", actor_id=principal.user_id,
                      target_type="user", target_id=user.id)
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, "Username already exists")
        return {"id": str(user.id), "username": user.username}

@router.get("/users")
def list_users():
    require_admin()
    with SessionLocal() as db:
        return [{"id": str(u.id), "username": u.username, "active": u.active, "platform_admin": u.platform_admin}
                for u in db.scalars(select(User).order_by(User.username)).all()]

@router.patch("/users/{user_id}/status")
def change_user_status(user_id: UUID, payload: UserStatus):
    principal = require_admin()
    with SessionLocal() as db:
        user = db.get(User, user_id)
        if user is None:
            raise HTTPException(404, "User not found")
        if not payload.active and user.platform_admin:
            remaining = db.scalar(select(func.count()).select_from(User).where(User.platform_admin.is_(True), User.active.is_(True)))
            if remaining <= 1:
                raise HTTPException(409, "Cannot disable the last active platform administrator")
        user.active = payload.active
        revoke_sessions(db, user_id)
        log_event(db, event_type="USER_STATUS", outcome="SUCCESS", actor_id=principal.user_id,
                  target_type="user", target_id=user_id)
        db.commit()
        return {"id": str(user_id), "active": user.active}

@router.post("/users/{user_id}/password")
def reset_password(user_id: UUID, payload: PasswordReset):
    principal = require_admin()
    with SessionLocal() as db:
        user = db.get(User, user_id)
        if user is None:
            raise HTTPException(404, "User not found")
        user.password_hash = hash_password(payload.new_password)
        revoke_sessions(db, user_id)
        log_event(db, event_type="PASSWORD_RESET", outcome="SUCCESS", actor_id=principal.user_id,
                  target_type="user", target_id=user_id)
        db.commit()
        return {"id": str(user_id), "sessions_revoked": True}

@router.get("/memberships")
def list_memberships():
    require_admin()
    with SessionLocal() as db:
        return [{"id": str(m.id), "user_id": str(m.user_id),
                 "organization_id": str(m.organization_id), "role": m.role}
                for m in db.scalars(select(OrganizationMembership)).all()]

@router.post("/memberships", status_code=201)
def assign_membership(payload: MemberCreate):
    principal = require_admin()
    from app.models import Organization
    if payload.role not in _ROLE_VALUES:
        raise HTTPException(422, "Unsupported membership role")
    with SessionLocal() as db:
        if db.get(User, payload.user_id) is None or db.get(Organization, payload.organization_id) is None:
            raise HTTPException(404, "User or organization not found")
        row = OrganizationMembership(**payload.model_dump())
        db.add(row)
        try:
            db.flush()
            revoke_sessions(db, row.user_id)
            log_event(db, event_type="MEMBERSHIP_CREATE", outcome="SUCCESS",
                      actor_id=principal.user_id, organization_id=row.organization_id,
                      target_type="membership", target_id=row.id)
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, "Membership already exists")
        return {"id": str(row.id), "organization_id": str(row.organization_id), "role": row.role}

@router.patch("/memberships/{membership_id}")
def change_membership(membership_id: UUID, payload: MemberPatch):
    principal = require_admin()
    if payload.role not in _ROLE_VALUES:
        raise HTTPException(422, "Unsupported membership role")
    with SessionLocal() as db:
        row = db.get(OrganizationMembership, membership_id)
        if row is None:
            raise HTTPException(404, "Membership not found")
        row.role = payload.role
        revoke_sessions(db, row.user_id)
        log_event(db, event_type="MEMBERSHIP_ROLE", outcome="SUCCESS", actor_id=principal.user_id,
                  organization_id=row.organization_id, target_type="membership", target_id=row.id)
        db.commit()
        return {"id": str(row.id), "role": row.role, "sessions_revoked": True}

@router.delete("/memberships/{membership_id}", status_code=204)
def delete_membership(membership_id: UUID):
    principal = require_admin()
    with SessionLocal() as db:
        row = db.get(OrganizationMembership, membership_id)
        if row is None:
            raise HTTPException(404, "Membership not found")
        revoke_sessions(db, row.user_id)
        log_event(db, event_type="MEMBERSHIP_DELETE", outcome="SUCCESS", actor_id=principal.user_id,
                  organization_id=row.organization_id, target_type="membership", target_id=row.id)
        db.delete(row)
        db.commit()

@router.get("/audit")
def audit_events(organization_id: UUID | None = None, limit: int = 100):
    require_admin()
    if limit < 1 or limit > 500:
        raise HTTPException(422, "Limit must be 1..500")
    with SessionLocal() as db:
        stmt = select(SecurityAuditEvent).order_by(SecurityAuditEvent.occurred_at.desc()).limit(limit)
        if organization_id:
            stmt = stmt.where(SecurityAuditEvent.organization_id == organization_id)
        return [{"id": str(e.id), "event_type": e.event_type, "actor_id": str(e.actor_id) if e.actor_id else None,
                 "organization_id": str(e.organization_id) if e.organization_id else None,
                 "target_type": e.target_type, "target_id": e.target_id,
                 "outcome": e.outcome, "occurred_at": e.occurred_at.isoformat()}
                for e in db.scalars(stmt).all()]

@router.post("/workers", status_code=201)
def create_worker(payload: WorkerCreate):
    principal = require_admin()
    from app.models import Organization
    with SessionLocal() as db:
        if db.get(Organization, payload.organization_id) is None:
            raise HTTPException(404, "Organization not found")
        secret = secrets.token_urlsafe(48)
        row = WorkerIdentity(organization_id=payload.organization_id,
                             name=payload.name, token_hash=token_digest(secret),
                             expires_at=datetime.now(timezone.utc) + timedelta(days=payload.expires_in_days))
        db.add(row)
        try:
            db.flush()
            log_event(db, event_type="WORKER_CREATE", outcome="SUCCESS", actor_id=principal.user_id,
                      organization_id=row.organization_id, target_type="worker", target_id=row.id)
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, "Worker name already exists for this organization")
        return {"id": str(row.id), "organization_id": str(row.organization_id),
                "expires_at": row.expires_at.isoformat(), "worker_token": secret}

@router.delete("/workers/{worker_id}", status_code=204)
def revoke_worker(worker_id: UUID):
    principal = require_admin()
    with SessionLocal() as db:
        row = db.get(WorkerIdentity, worker_id)
        if row is None:
            raise HTTPException(404, "Worker not found")
        row.enabled = False
        log_event(db, event_type="WORKER_REVOKE", outcome="SUCCESS", actor_id=principal.user_id,
                  organization_id=row.organization_id, target_type="worker", target_id=row.id)
        db.commit()

@worker_router.get("/whoami")
def worker_whoami(request: Request):
    # A service token cannot access any human-facing /api/v1/ route.
    parts = request.headers.get("authorization", "").split()
    if len(parts) != 2 or parts[0] != "Bearer":
        raise HTTPException(401, "Worker authentication required")
    with SessionLocal() as db:
        row = db.scalar(select(WorkerIdentity).where(WorkerIdentity.token_hash == token_digest(parts[1])))
        if row is None or not row.enabled or row.expires_at.replace(tzinfo=timezone.utc) <= datetime.now(timezone.utc):
            raise HTTPException(401, "Invalid or expired worker identity")
        return {"worker_id": str(row.id), "organization_id": str(row.organization_id),
                "name": row.name, "capabilities": ["identity_only"]}
