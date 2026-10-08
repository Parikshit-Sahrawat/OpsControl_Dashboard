from fastapi import APIRouter
from sqlalchemy import text
from app.db.session import engine
router = APIRouter(tags=["Health"])
@router.get("/health")
def health(): return {"status":"ok"}
@router.get("/health/db")
def db_health():
    with engine.connect() as conn: conn.execute(text("SELECT 1"))
    return {"status":"ok","database":"ok"}
