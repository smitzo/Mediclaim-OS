"""Verify the actual public PDF, previews, evidence, and decimal billing fixture."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "frontend" / "public"


def main() -> None:
    bundle = json.loads((PUBLIC / "demo" / "sample-claim.json").read_text())
    result = bundle["result"]
    data = result["extracted_data"]
    bill = data["itemized_bill"]
    assert result["processing_summary"]["synthetic"] is True
    assert result["processing_summary"]["result_source"] == "prepared_sample"
    assert "Fictional" in result["page_classification"][0]["description"]
    assert result["errors"] == [] and bill["currency"] == "INR"
    with fitz.open(PUBLIC / bundle["pdfHref"].lstrip("/")) as pdf:
        assert len(pdf) == len(bundle["pages"]) == result["processing_summary"]["total_pages"] == 3
        texts = [" ".join(page.get_text().split()) for page in pdf]
        for page, classification in zip(bundle["pages"], result["page_classification"]):
            number = page["number"]
            assert number == classification["page_number"]
            assert page["documentType"] == classification["document_type"]
            assert result["processing_summary"]["pages_per_document_type"][page["documentType"]] == [number - 1]
            assert "Fictional data for demonstration" in texts[number - 1]
            pixmap = fitz.Pixmap(str(PUBLIC / page["preview"].lstrip("/")))
            # Compare actual pixels to a fresh PDF rendering to catch stale previews.
            expected = pdf[number - 1].get_pixmap(matrix=fitz.Matrix(1.6, 1.6), alpha=False)
            assert pixmap.width == expected.width and pixmap.height == expected.height
            assert pixmap.samples == expected.samples
        for evidence in result["field_evidence"].values():
            assert evidence["confidence"] is None
            assert evidence["method"] == "prepared_demo"
            assert evidence["supporting_text"] in texts[evidence["source_page"] - 1]
        for value in data["identity"].values():
            assert value in texts[0]
        for value in data["discharge_summary"].values():
            assert value in texts[1]
        for line in bill["line_items"]:
            assert line["description"] in texts[2]
            assert Decimal(line["unit_price"]) * line["quantity"] == Decimal(line["amount"])
            assert f'{Decimal(line["amount"]):,.2f}' in texts[2]
        subtotal = sum((Decimal(line["amount"]) for line in bill["line_items"]), Decimal("0.00"))
        assert subtotal == Decimal(bill["subtotal"])
        assert subtotal + Decimal(bill["tax"]) - Decimal(bill["discount"]) == Decimal(bill["total_amount"])
        assert f'INR {Decimal(bill["total_amount"]):,.2f}' in texts[2]
    print("Showcase verified: 3 PDF pages, matching preview pixels, source evidence, fields, and exact billing totals.")


if __name__ == "__main__":
    main()
