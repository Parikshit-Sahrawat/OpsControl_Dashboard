from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import etl, investigations, health
app=FastAPI(title="OpsControl API",version="0.1.0",description="Operational monitoring API for OpsControl Dashboard.")
app.add_middleware(CORSMiddleware,allow_origins=settings.cors_origin_list,allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
app.include_router(health.router);app.include_router(etl.router);app.include_router(investigations.router)
@app.get("/")
def root():return {"name":"OpsControl API","version":app.version,"docs":"/docs"}
