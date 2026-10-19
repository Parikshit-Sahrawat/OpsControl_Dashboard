"""Bounded projections over already-authorized ORM queries; no scope grants."""

from collections import defaultdict
from sqlalchemy import select, func


def page(db, query, ordering, limit, offset, serialize):
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.scalars(query.order_by(*ordering).limit(limit).offset(offset)).all()
    return {
        "items": [serialize(row) for row in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(rows) < total,
    }


def children(db, model, parent, ids, ordering, limit, serialize):
    """One bounded query for child previews and exact totals across a parent page."""
    result, totals = defaultdict(list), {}
    if not ids:
        return result, totals
    ranked = (
        select(
            model.id.label("child_id"),
            func.row_number().over(partition_by=parent, order_by=ordering).label("rn"),
            func.count().over(partition_by=parent).label("total"),
        )
        .where(parent.in_(ids))
        .subquery()
    )
    for row, total in db.execute(
        select(model, ranked.c.total)
        .join(ranked, model.id == ranked.c.child_id)
        .where(ranked.c.rn <= limit)
        .order_by(parent, ranked.c.rn)
    ):
        key = getattr(row, parent.key)
        result[key].append(serialize(row))
        totals[key] = total
    return result, totals
