from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings
from app.api import etl, investigations, health, monitoring, organizations, resource_management, remote_protocol, rule_catalogs, activation, monitoring_diagnostics, discovery
import app.services.rule_models  # register immutable rule/activation tables
import app.worker.remote_models  # register remote job/evidence tables
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
        if settings.environment.lower() == "production" or not request.url.path.startswith(("/docs", "/redoc")):
            response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
        if settings.environment.lower() == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

production = settings.environment.lower() == "production"
if production and (
    not settings.cors_origin_list
    or any(not origin.startswith("https://") or "*" in origin for origin in settings.cors_origin_list)
):
    raise RuntimeError("Production requires an explicit HTTPS-only CORS origin allowlist")
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
app.include_router(remote_protocol.worker_router)
app.include_router(remote_protocol.admin_router)
app.include_router(rule_catalogs.router)
app.include_router(activation.router)
app.include_router(monitoring_diagnostics.router)
app.include_router(discovery.router)
app.include_router(etl.router)
app.include_router(investigations.router)
app.include_router(monitoring.router)
app.include_router(organizations.router)
app.include_router(resource_management.router)

@app.get("/")
def root():
    return {"name": "OpsControl API", "version": app.version}

@app.exception_handler(RequestValidationError)
async def redacted_validation_error(request: Request, exc: RequestValidationError):
    # Never echo secret-bearing submitted JSON in Pydantic's default error
    # response; even a rejected config may contain a raw password/token.
    safe_errors = [{"loc": [str(part) for part in err.get("loc", ())],
                    "type": str(err.get("type", "value_error"))}
                   for err in exc.errors()]
    return JSONResponse({"detail": "Invalid input", "errors": safe_errors}, status_code=422)
