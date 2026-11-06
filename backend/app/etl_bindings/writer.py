"""Transaction-local capability of current server code, never a client header.

This fences unchanged old binaries, not a compromised DB-role holder issuing SQL.
Only authority-aware handlers opt in. Pool reuse cannot retain SET LOCAL state.
"""

from sqlalchemy import text, event
from sqlalchemy.orm import Session


def mark(db):
    db.execute(text("SELECT set_config('opscontrol.etl_writer_protocol','1',true)"))


# Recheck trust/key configuration immediately before an admission commit.
@event.listens_for(Session, "before_commit")
def revalidate_admissions(db):
    ids = db.info.pop("etl_admitted_bindings", set())
    if ids:
        from app.etl_bindings.authority import qualified_binding
        from app.etl_bindings.models import ETLNativeBinding

        for identity in sorted(ids, key=str):
            qualified_binding(db, db.get(ETLNativeBinding, identity))


@event.listens_for(Session, "after_rollback")
def clear_admissions(db):
    db.info.pop("etl_admitted_bindings", None)
