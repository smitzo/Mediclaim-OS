"""Create short demo PDFs from data/sample_data.pdf.

The script uses Ghostscript because it is available in the development image and
does not require importing project dependencies. It keeps the committed demo PDFs
small enough for quick uploads while still being based on the real sample file.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "sample_data.pdf"
OUTPUT_DIR = ROOT / "data" / "demo_pdfs"
RANGES = [
    ("demo_claim_short_1.pdf", 1, 3),
    ("demo_claim_short_2.pdf", 4, 6),
    ("demo_claim_short_3.pdf", 7, 9),
]


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"Missing source PDF: {SOURCE}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for filename, first_page, last_page in RANGES:
        output = OUTPUT_DIR / filename
        subprocess.run(
            [
                "gs",
                "-q",
                "-dNOPAUSE",
                "-dBATCH",
                "-sDEVICE=pdfwrite",
                f"-dFirstPage={first_page}",
                f"-dLastPage={last_page}",
                f"-sOutputFile={output}",
                str(SOURCE),
            ],
            check=True,
        )
        print(f"Wrote {output.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
