"""First-boot admin bootstrap. Run interactively, not via public HTTP."""
import argparse
from getpass import getpass
from sqlalchemy import select
from app.db.session import SessionLocal
from app.security.models import User
from app.security.passwords import hash_password

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", required=True)
    args = parser.parse_args()
    username = args.username.strip().lower()
    if not username: raise SystemExit("Username cannot be empty")
    with SessionLocal() as db:
        if db.scalar(select(User.id).where(User.platform_admin.is_(True))) is not None:
            raise SystemExit("An administrator exists. Create further users through the authenticated admin API.")
        if db.scalar(select(User.id).where(User.username == username)) is not None:
            raise SystemExit("Username already exists")
        first = getpass("Create admin password (min 12 characters): ")
        second = getpass("Confirm password: ")
        if first != second: raise SystemExit("Passwords do not match")
        db.add(User(username=username, password_hash=hash_password(first), platform_admin=True))
        db.commit()
        print("Administrator created. Sign in through the OpsControl login page.")

if __name__ == "__main__":
    main()
