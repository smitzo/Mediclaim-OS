"""Offline local-adapter backup/restore. Stop API, worker and dispatcher first."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.lifecycle import create_backup, restore_backup, deletion_ledger
from app.services.storage import ClaimStorage


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["backup", "restore", "deletion-ledger"])
    parser.add_argument("source", type=Path)
    parser.add_argument("--target", type=Path)
    parser.add_argument("--latest-deletion-ledger", type=Path)
    parser.add_argument("--quiesced", action="store_true")
    args = parser.parse_args()
    if args.action == "deletion-ledger":
        print(json.dumps(deletion_ledger(ClaimStorage(args.source)))); return
    if not args.quiesced or not args.target: parser.error("Backup/restore requires --quiesced and --target.")
    if args.action == "backup": print(json.dumps(create_backup(ClaimStorage(args.source), args.target)))
    else:
        if not args.latest_deletion_ledger: parser.error("Restore requires the latest independent deletion ledger.")
        store = restore_backup(args.source, args.target, json.loads(args.latest_deletion_ledger.read_text()))
        print(json.dumps({"restored_jobs": len(store.list_jobs(limit=100000))}))


if __name__ == "__main__": main()
