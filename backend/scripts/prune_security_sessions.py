"""Maintenance: prune expired sessions and old login-throttle buckets.

Run via a trusted operating-system scheduler (cron/systemd/Kubernetes CronJob).
Does not purge append-only audit evidence or active sessions. Execute with a
dedicated database role if supported by the deployment.
"""
from datetime import datetime, timedelta, timezone
from sqlalchemy import delete
from app.db.session import SessionLocal
from app.security.models import AccessSession, AuthThrottleBucket

def main():
    now=datetime.now(timezone.utc)
    with SessionLocal() as db:
        sessions=db.execute(delete(AccessSession).where(AccessSession.expires_at < now))
        buckets=db.execute(delete(AuthThrottleBucket).where(
            AuthThrottleBucket.window_started_at < now - timedelta(days=2)
        ))
        db.commit()
        print("Expired sessions cleaned: %s; old throttle buckets cleaned: %s" %
              (sessions.rowcount, buckets.rowcount))

if __name__=="__main__":
    main()
