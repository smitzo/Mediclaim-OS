"""Check tracked text for common credential formats without printing matches."""
import re
import subprocess
from pathlib import Path
PATTERNS = [rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", rb"AKIA[0-9A-Z]{16}", rb"sk-(?:proj-)?[A-Za-z0-9_-]{40,}", rb"gh[pousr]_[A-Za-z0-9]{30,}"]


def main():
    failed = []
    for name in subprocess.check_output(["git", "ls-files", "-z"]).split(b"\0"):
        if not name: continue
        path = Path(name.decode())
        if path.suffix.lower() in {".pdf", ".png", ".jpg", ".lock"}: continue
        if not path.is_file(): continue
        content = path.read_bytes()
        if any(re.search(pattern, content) for pattern in PATTERNS): failed.append(str(path))
    if failed:
        print("Possible credentials in: "+", ".join(failed)); raise SystemExit(1)
    print("Tracked-file credential pattern check passed.")


if __name__ == "__main__": main()
