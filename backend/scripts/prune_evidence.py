"""One atomic bounded retention batch, run by a scheduled maintenance identity."""
import argparse
import json
from app.db.session import SessionLocal
from app.services.retention import prune_batch

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--apply", action="store_true", help="Commit deletion; default is a rolled-back dry run")
    args = parser.parse_args()
    with SessionLocal() as db:
        counts = prune_batch(db, batch_size=args.batch_size)
        if args.apply:
            db.commit()
        else:
            db.rollback()
    print(json.dumps({"applied": args.apply, "rows": counts}, sort_keys=True))

if __name__ == "__main__":
    main()
