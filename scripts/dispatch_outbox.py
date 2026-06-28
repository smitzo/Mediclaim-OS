"""Run independently of Celery/Redis so broker recovery can republish intents."""
import argparse
import logging
import signal
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.storage import storage
from app.services.attempts import AttemptService
from app.workers.tasks import process_claim_job


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    running = True
    def stop(*_):
        nonlocal running
        running = False
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    while running:
        try:
            AttemptService(storage).reconcile()
            storage.dispatch_outbox(process_claim_job.delay)
        except Exception: logging.error("Outbox dispatch failed; will retry.")
        if args.once: break
        time.sleep(2)


if __name__ == "__main__": main()
