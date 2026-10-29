"""Task-owned synthetic incident pagination fixture; never a customer database."""
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from uuid import uuid4
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models import Organization, OperationalIncident


def main():
    if os.getenv("OPSCONTROL_RELEASE_ACCEPTANCE") != "1" or os.getenv("ENVIRONMENT") != "demo":
        raise SystemExit("Owned disposable release fixture required")
    with SessionLocal() as db:
        organization = db.scalar(select(Organization).where(Organization.code == "LAB-N"))
        if organization is None:
            raise RuntimeError("Synthetic north organization missing")
        ids = []
        now = datetime.now(timezone.utc)
        for number in range(61):
            identity = uuid4()
            db.add(OperationalIncident(
                id=identity, organization_id=organization.id,
                episode_key="closure-pagination-" + str(identity),
                source_kind="ALERT", source_reference=str(identity),
                title=f"closure-pagination-{number:03}", severity="INFO",
                status="CLOSED", condition_status="RECOVERED",
                opened_at=now-timedelta(seconds=number+60),
                recovered_at=now, resolved_at=now,
            ))
            ids.append(str(identity))
        db.commit()
    (Path(os.environ["RELEASE_EVIDENCE_DIR"]) / "incident-pagination-fixture.json").write_text(
        json.dumps({"expected_ids": ids, "count": len(ids), "source": "synthetic owned fixture"}, indent=2) + "\n"
    )
    print("Synthetic pagination fixture: 61 immutable IDs committed")


if __name__ == "__main__":
    main()
