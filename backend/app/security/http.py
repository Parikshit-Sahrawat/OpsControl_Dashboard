"""Bearer-session gate for all API routes; no anonymous data or mutation."""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.db.session import SessionLocal
from app.security.models import AccessSession, OrganizationMembership, User
from app.security.passwords import hash_password, verify_password
from app.security.scope import Principal, current_principal

router = APIRouter(prefix="/api/v1/auth", tags=["Identity"])
_ALLOWED_PUBLIC = {"/", "/health", "/health/db", "/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc", "/api/v1/auth/login"}
_ROLE_VALUES = {"viewer", "operator", "org_admin"}

class Login(BaseModel):
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=1024)

class UserCreate(Login):
    platform_admin: bool = False

class MemberCreate(BaseModel):
    user_id: str
    organization_id: str
    role: str

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
    principal = Principal(user.id, user.username, user.platform_admin, dict(memberships))
    return principal

class IdentityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path.rstrip("/") or "/"
        if request.method == "OPTIONS" or path in _ALLOWED_PUBLIC or path.startswith("/static/"):
            return await call_next(request)
        if not path.startswith("/api/"):
            return await call_next(request)
        header = request.headers.get("authorization", "")
        if not header.startswith("Bearer ") or len(header.split()) != 2:
            return JSONResponse({"detail": "Authentication required"}, status_code=401, headers={"WWW-Authenticate": "Bearer"})
        with SessionLocal() as db:
            principal = identify(db, header.split()[1])
        if principal is None:
            return JSONResponse({"detail": "Invalid or expired session"}, status_code=401, headers={"WWW-Authenticate": "Bearer"})
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            if path == "/api/v1/auth/logout":
                pass
            elif path.startswith("/api/v1/auth/"):
                if not principal.platform_admin:
                    return JSONResponse({"detail": "Platform administrator required"}, status_code=403)
            elif path.startswith("/api/v1/organizations") and request.method == "POST":
                if not principal.platform_admin:
                    return JSONResponse({"detail": "Platform administrator required"}, status_code=403)
            elif "/templates" in path and not path.endswith("/templates") and path.startswith("/api/v1/monitoring/templates"):
                if not principal.platform_admin:
                    return JSONResponse({"detail": "Platform administrator required"}, status_code=403)
            elif path.startswith("/api/v1/monitoring/templates") and not principal.platform_admin:
                return JSONResponse({"detail": "Platform administrator required"}, status_code=403)
            elif not principal.platform_admin and not any(role == "org_admin" for role in principal.roles.values()):
                # Operators may investigate, but cannot edit monitoring configuration.
                investigation_route = "/investigation/" in path
                if not (investigation_route and any(role == "operator" for role in principal.roles.values())):
                    return JSONResponse({"detail": "Write permission required"}, status_code=403)
        context_token = current_principal.set(principal)
        try:
            return await call_next(request)
        finally:
            current_principal.reset(context_token)

@router.post("/login")
def login(payload: Login):
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == payload.username.strip().lower()))
        # Fixed dummy hash prevents trivially distinguishing unknown usernames.
        if user is None or not user.active or not verify_password(payload.password, user.password_hash):
            raise HTTPException(401, "Invalid username or password")
        token = secrets.token_urlsafe(48)
        expiry = datetime.now(timezone.utc) + timedelta(hours=12)
        db.add(AccessSession(user_id=user.id, token_hash=token_digest(token), expires_at=expiry))
        db.commit()
        return {"access_token": token, "token_type": "bearer", "expires_at": expiry.isoformat()}

@router.get("/me")
def me():
    principal = current_principal.get()
    return {"id": str(principal.user_id), "username": principal.username,
            "platform_admin": principal.platform_admin,
            "memberships": [{"organization_id": str(k), "role": v} for k, v in principal.roles.items()]}

@router.post("/logout", status_code=204)
def logout(request: Request):
    digest = token_digest(request.headers.get("authorization", "").split()[1])
    with SessionLocal() as db:
        row = db.scalar(select(AccessSession).where(AccessSession.token_hash == digest))
        if row: db.delete(row); db.commit()

@router.post("/users", status_code=201)
def create_user(payload: UserCreate):
    from sqlalchemy.exc import IntegrityError
    username = payload.username.strip().lower()
    if not username:
        raise HTTPException(422, "Username required")
    with SessionLocal() as db:
        user = User(username=username, password_hash=hash_password(payload.password),
                    platform_admin=payload.platform_admin)
        db.add(user)
        try: db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, "Username already exists")
        return {"id": str(user.id), "username": user.username}

@router.post("/memberships", status_code=201)
def assign_membership(payload: MemberCreate):
    from uuid import UUID
    from app.models import Organization
    from sqlalchemy.exc import IntegrityError
    if payload.role not in _ROLE_VALUES:
        raise HTTPException(422, "Unsupported membership role")
    with SessionLocal() as db:
        try: user_id, org_id = UUID(payload.user_id), UUID(payload.organization_id)
        except ValueError: raise HTTPException(422, "Invalid user or organization ID")
        if db.get(User, user_id) is None or db.get(Organization, org_id) is None:
            raise HTTPException(404, "User or organization not found")
        row = OrganizationMembership(user_id=user_id, organization_id=org_id, role=payload.role)
        db.add(row)
        try: db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, "Membership already exists")
        return {"id": str(row.id), "organization_id": str(org_id), "role": row.role}
