from fastapi import FastAPI, Request, Depends
from app.security.access_control import authorize_route
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from contextlib import asynccontextmanager

from app.core.config import settings
from app.api import operations, access
from app.registry import api as registry_api
from app.native_incidents import api as native_incidents_api
import app.registry.models
import app.native_incidents.models
from app.unified import api as unified
import app.unified.reporting
import app.unified.compatibility
from app.telemetry import api as agent_control, ingestion, rules, inbox
import app.telemetry.models
import app.unified.models
import app.unified.pentaho_models
from app.api import (
    infrastructure,
    etl,
    investigations,
    health,
    monitoring,
    organizations,
    resource_management,
    remote_protocol,
    rule_catalogs,
    activation,
    monitoring_diagnostics,
    discovery,
)
import app.services.rule_models  # register immutable rule/activation tables
import app.worker.remote_models  # register remote job/evidence tables
from app.security.http import (
    IdentityMiddleware,
    router as identity_router,
    worker_router,
)
import app.security.models  # register identity and service models


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # In production require a TLS-terminating ingress with a verified
        # ASGI scheme (proxy headers only from a trusted ingress).
        if (
            settings.environment.lower() == "production"
            and request.url.scheme != "https"
        ):
            response = JSONResponse({"detail": "HTTPS required"}, status_code=403)
        else:
            response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        if (
            settings.environment.lower() == "production"
            or not request.url.path.startswith(("/docs", "/redoc"))
        ):
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
            )
        if settings.environment.lower() == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response


production = settings.environment.lower() == "production"


@asynccontextmanager
async def lifespan(app):
    from app.security.deployment import validate_runtime_database_role

    await run_in_threadpool(validate_runtime_database_role)
    yield


if production and (
    not settings.cors_origin_list
    or any(
        not origin.startswith("https://") or "*" in origin
        for origin in settings.cors_origin_list
    )
):
    raise RuntimeError(
        "Production requires an explicit HTTPS-only CORS origin allowlist"
    )
app = FastAPI(
    lifespan=lifespan,
    title="OpsControl API",
    version="0.3.0",
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
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
from app.data_pipelines import (
    api as data_pipelines_api,
    agent_api as pipeline_agent_api,
)

app.include_router(pipeline_agent_api.router)
app.include_router(data_pipelines_api.router, dependencies=[Depends(authorize_route)])
app.include_router(unified.router, dependencies=[Depends(authorize_route)])
app.include_router(registry_api.router, dependencies=[Depends(authorize_route)])
app.include_router(native_incidents_api.router, dependencies=[Depends(authorize_route)])
app.include_router(inbox.router, dependencies=[Depends(authorize_route)])
app.include_router(rules.router, dependencies=[Depends(authorize_route)])
app.include_router(agent_control.router, dependencies=[Depends(authorize_route)])
app.include_router(agent_control.agent_router)
app.include_router(access.router, dependencies=[Depends(authorize_route)])
app.include_router(health.router, dependencies=[Depends(authorize_route)])
app.include_router(infrastructure.router, dependencies=[Depends(authorize_route)])
app.include_router(operations.router, dependencies=[Depends(authorize_route)])
app.include_router(identity_router, dependencies=[Depends(authorize_route)])
app.include_router(worker_router, dependencies=[Depends(authorize_route)])
app.include_router(
    remote_protocol.worker_router, dependencies=[Depends(authorize_route)]
)
app.include_router(
    remote_protocol.admin_router, dependencies=[Depends(authorize_route)]
)
app.include_router(rule_catalogs.router, dependencies=[Depends(authorize_route)])
app.include_router(activation.router, dependencies=[Depends(authorize_route)])
app.include_router(
    monitoring_diagnostics.router, dependencies=[Depends(authorize_route)]
)
app.include_router(discovery.router, dependencies=[Depends(authorize_route)])
app.include_router(etl.router, dependencies=[Depends(authorize_route)])
app.include_router(investigations.router, dependencies=[Depends(authorize_route)])
app.include_router(monitoring.router, dependencies=[Depends(authorize_route)])
app.include_router(organizations.router, dependencies=[Depends(authorize_route)])
app.include_router(resource_management.router, dependencies=[Depends(authorize_route)])


@app.get("/")
def root():
    return {"name": "OpsControl API", "version": app.version}


@app.exception_handler(RequestValidationError)
async def redacted_validation_error(request: Request, exc: RequestValidationError):
    # Never echo secret-bearing submitted JSON in Pydantic's default error
    # response; even a rejected config may contain a raw password/token.
    safe_errors = [
        {
            "loc": [str(part) for part in err.get("loc", ())],
            "type": str(err.get("type", "value_error")),
        }
        for err in exc.errors()
    ]
    return JSONResponse(
        {"detail": "Invalid input", "errors": safe_errors}, status_code=422
    )


# Constraint failures never expose SQL statements, passwords or bound values.
from sqlalchemy.exc import IntegrityError
from pydantic import ValidationError


@app.exception_handler(IntegrityError)
async def constraint_conflict(request: Request, exc: IntegrityError):
    return JSONResponse(
        {"detail": "Duplicate identity or invalid relationship"}, status_code=409
    )


@app.exception_handler(ValidationError)
async def schema_conflict(request: Request, exc: ValidationError):
    return JSONResponse({"detail": "Invalid configuration"}, status_code=422)
