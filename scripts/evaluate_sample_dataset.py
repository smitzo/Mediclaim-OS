"""Evaluate the local sample PDF dataset without calling LLM services."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "evaluation" / "golden_sample_result.json"


def main() -> None:
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    failures: list[str] = []

    source = ROOT / golden["source_pdf"]
    _check_pdf(source, golden["expected_pages"], failures)

    for item in golden["demo_pdfs"]:
        path = ROOT / item["path"]
        _check_pdf(path, item["expected_pages"], failures)
        if path.exists() and path.stat().st_size < golden["minimum_demo_pdf_bytes"]:
            failures.append(f"{item['path']} is unexpectedly small")

    if failures:
        print("Sample dataset evaluation failed:")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(1)

    print("Sample dataset evaluation passed.")


def _check_pdf(path: Path, expected_pages: int, failures: list[str]) -> None:
    if not path.exists():
        failures.append(f"Missing PDF: {path.relative_to(ROOT)}")
        return
    result = subprocess.run(["pdfinfo", str(path)], check=True, capture_output=True, text=True)
    pages = _pages_from_pdfinfo(result.stdout)
    if pages != expected_pages:
        failures.append(f"{path.relative_to(ROOT)} expected {expected_pages} pages, found {pages}")


def _pages_from_pdfinfo(output: str) -> int:
    for line in output.splitlines():
        if line.startswith("Pages:"):
            return int(line.split(":", 1)[1].strip())
    raise ValueError("pdfinfo output did not include a page count")


if __name__ == "__main__":
    main()
