"""Dry-run by default. Apply requires a backup directory outside the source."""
import argparse
import json
import os
import shutil
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.legacy_import import inspect_legacy, apply_import


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--target", type=Path)
    parser.add_argument("--tenant-map", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--backup-dir", type=Path)
    args = parser.parse_args()
    mapping = json.loads(args.tenant_map.read_text()) if args.tenant_map else {}
    accounts, claims = inspect_legacy(args.source, mapping)
    print(json.dumps({"mode": "apply" if args.apply else "dry-run", "accounts": len(accounts), "jobs": len(claims), "legacy_sessions_will_be_invalidated": True}))
    if not args.apply: return
    if not args.backup_dir or not args.target: parser.error("--apply requires --target and --backup-dir")
    source = args.source.resolve()
    if args.backup_dir.resolve().is_relative_to(source) or args.target.resolve().is_relative_to(source):
        parser.error("Backup and target must be outside the legacy source.")
    args.backup_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    import time
    backup = shutil.make_archive(str(args.backup_dir/f"legacy-{time.time_ns()}"), "gztar", source)
    os.chmod(backup, 0o600)
    from app.services.storage import ClaimStorage
    print(json.dumps(apply_import(ClaimStorage(args.target), accounts, claims)))


if __name__ == "__main__": main()
