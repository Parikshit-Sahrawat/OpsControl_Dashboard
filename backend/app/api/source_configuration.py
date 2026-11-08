"""Authenticated history/preview/command APIs on the existing Data Source owner."""

from uuid import UUID
from fastapi import APIRouter, Depends, Header, Query, HTTPException
from sqlalchemy import select
from app.db.session import get_db
from app.models.entities import SourceConfigurationRevision
from app.services import source_configuration as service

router = APIRouter(prefix="/data-sources/{item_id}/configuration")


@router.get("")
def current(item_id: UUID, db=Depends(get_db)):
    return service.current(db, service.source_row(db, item_id))


@router.post("/preview")
def preview(item_id: UUID, payload: service.Command, db=Depends(get_db)):
    source = service.source_row(db, item_id, write=True)
    if payload.expected_revision != source.configuration_revision:
        raise HTTPException(409, "STALE_REVISION")
    from types import SimpleNamespace

    source = SimpleNamespace(
        **{
            key: getattr(source, key)
            for key in (
                "id",
                "organization_id",
                "source_type",
                "endpoint",
                "connection_config",
                "name",
                "description",
            )
        }
    )
    for field, value in service.context_values(source, payload).items():
        setattr(source, field, value)
    return service.evaluate(
        db,
        source,
        sorted(
            payload.model_dump(mode="json")["attachments"],
            key=lambda m: (m["priority"], m["template_id"]),
        ),
    )


@router.post("/commands", status_code=201)
def commands(
    item_id: UUID,
    payload: service.Command,
    idempotency_key: UUID = Header(),
    db=Depends(get_db),
):
    return service.commit(db, item_id, payload, idempotency_key)


class Import(service.BaseModel):
    model_config = service.ConfigDict(extra="forbid")
    expected_revision: int = service.Field(ge=0, le=0)


@router.post("/import-legacy", status_code=201)
def import_legacy_configuration(
    item_id: UUID, payload: Import, idempotency_key: UUID = Header(), db=Depends(get_db)
):
    return service.commit(db, item_id, payload, idempotency_key, importing=True)


@router.get("/history")
def history(
    item_id: UUID,
    before: int | None = Query(default=None, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db=Depends(get_db),
):
    service.source_row(db, item_id)
    query = select(SourceConfigurationRevision).where(
        SourceConfigurationRevision.data_source_id == item_id
    )
    if before is not None:
        query = query.where(SourceConfigurationRevision.revision < before)
    rows = list(
        db.scalars(
            query.order_by(SourceConfigurationRevision.revision.desc()).limit(limit + 1)
        )
    )
    return dict(
        items=[service.output(r) for r in rows[:limit]],
        next_before=rows[limit - 1].revision if len(rows) > limit else None,
    )


@router.get("/revisions/{number}")
def revision(item_id: UUID, number: int, db=Depends(get_db)):
    source = service.source_row(db, item_id)
    return service.output(service.revision_row(db, source, number))


@router.get("/diff")
def diff(item_id: UUID, from_revision: int, to_revision: int, db=Depends(get_db)):
    source = service.source_row(db, item_id)
    old = service.output(service.revision_row(db, source, from_revision))["document"]
    new = service.output(service.revision_row(db, source, to_revision))["document"]
    return dict(
        from_revision=from_revision,
        to_revision=to_revision,
        before=old,
        after=new,
        changed=old != new,
    )


@router.post("/rollback", status_code=201)
def rollback(
    item_id: UUID,
    payload: service.Rollback,
    idempotency_key: UUID = Header(),
    db=Depends(get_db),
):
    return service.commit(
        db,
        item_id,
        payload,
        idempotency_key,
        kind="ROLLBACK",
        target=payload.target_revision,
    )
