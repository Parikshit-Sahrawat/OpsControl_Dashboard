from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.core.config import settings
from fastapi import Request


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_timeout=10,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db(request: Request):
    db = SessionLocal()
    from app.security.scope import configure_request_session, current_principal

    try:
        # Pipeline agent transport also uses this dependency and authenticates
        # its separate service identity in the handler. Human routes have a
        # principal established by the deny-by-default identity middleware.
        if current_principal.get() is not None and request.method not in {
            "GET",
            "HEAD",
            "OPTIONS",
        }:
            from app.security.boundaries import transaction_authority

            # Only these graph/binding configuration mutations opt into readers of
            # authorization state. All access/session mutations remain exclusive.
            route = request.scope.get("route")
            graph_write = request.method == "POST" and getattr(route, "path", None) in {
                "/api/v1/etl/workflows/{workflow_id}/dependencies",
                "/api/v1/etl/workflows/{workflow_id}/jobs/{job_id}/native-bindings",
            }
            (
                transaction_authority(db, shared=True)
                if graph_write
                else transaction_authority(db)
            )
        configure_request_session(db)
        if request.method not in {
            "GET",
            "HEAD",
            "OPTIONS",
        } and request.url.path.startswith("/api/v1/data-pipelines/"):
            from app.etl_bindings.writer import mark

            mark(db)
        db.info["opscontrol_route"] = request.url.path[:120]
        yield db
    finally:
        db.close()
