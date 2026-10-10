from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import etl, investigations, health, monitoring, organizations, resource_management
from app.security.http import IdentityMiddleware, router as identity_router
import app.security.models  # register identity models with metadata

app = FastAPI(title="OpsControl API", version="0.2.0", description="Operational monitoring and configuration API for OpsControl Dashboard.")
app.add_middleware(IdentityMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(health.router)
app.include_router(identity_router)
app.include_router(etl.router)
app.include_router(investigations.router)
app.include_router(monitoring.router)
app.include_router(organizations.router)
app.include_router(resource_management.router)

@app.get("/")
def root():
    return {"name": "OpsControl API", "version": app.version, "docs": "/docs"}
