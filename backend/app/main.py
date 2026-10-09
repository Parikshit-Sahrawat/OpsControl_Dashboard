from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings
from app.api import etl, investigations, health, monitoring, organizations, resource_management
from app.security.http import IdentityMiddleware, router as identity_router, worker_router
import app.security.models  # register identity and service models

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # In production require a TLS-terminating ingress with a verified
        # ASGI scheme (proxy headers only from a trusted ingress).
        if settings.environment.lower() == "production" and request.url.scheme != "https":
            return JSONResponse({"detail": "HTTPS required"}, status_code=403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
        if settings.environment.lower() == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

production = settings.environment.lower() == "production"
app = FastAPI(
    title="OpsControl API", version="0.2.0",
    description="General-purpose open-source monitoring and configuration API.",
    docs_url=None if production else "/docs",
    redoc_url=None if production else "/redoc",
    openapi_url=None if production else "/openapi.json",
)
app.add_middleware(IdentityMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,  # bearer headers; no cookie-origin sharing
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(health.router)
app.include_router(identity_router)
app.include_router(worker_router)
app.include_router(etl.router)
app.include_router(investigations.router)
app.include_router(monitoring.router)
app.include_router(organizations.router)
app.include_router(resource_management.router)

@app.get("/")
def root():
    return {"name": "OpsControl API", "version": app.version}
