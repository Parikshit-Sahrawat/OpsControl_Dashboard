"""Trusted control-plane scheduler for assigned remote HTTP collectors."""
import logging
import time
from app.worker.remote_scheduler import queue_due_once
logging.basicConfig(level=logging.INFO)

def main():
    while True:
        try:
            count=queue_due_once()
            if count: logging.info("Remote HTTP jobs queued: %s", count)
        except KeyboardInterrupt:
            return
        except Exception:
            logging.exception("Remote scheduler error")
        time.sleep(5)

if __name__=="__main__":main()
