"""Rebuild the public synthetic PDF and PNG previews from the canonical fixture.

Run with the project's Python environment. No source claim, provider, or private
patient data is read. PyMuPDF is supplied by the backend lockfiles.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "public" / "demo"
BLUE = (0.10, 0.34, 0.82)
INK = (0.10, 0.13, 0.19)
GRAY = (0.42, 0.46, 0.52)


def money(value: str) -> str:
    return f"INR {Decimal(value):,.2f}"


def heading(page: fitz.Page, title: str, number: int) -> None:
    page.draw_rect(fitz.Rect(42, 42, 78, 78), color=BLUE, fill=BLUE)
    page.insert_text((51, 68), "+", fontsize=30, color=(1, 1, 1), fontname="hebo")
    page.insert_text((91, 56), "Sample Care", fontsize=12, color=BLUE, fontname="hebo")
    page.insert_text((91, 73), "Hospital", fontsize=12, color=BLUE, fontname="hebo")
    page.insert_text((449, 65), "DEMO", fontsize=28, color=(0.83, 0.85, 0.88), fontname="hebo")
    page.insert_text((330, 89), "Fictional data for demonstration", fontsize=10, color=GRAY)
    page.insert_text((42, 135), title, fontsize=20, color=INK, fontname="hebo")
    page.draw_line((42, 155), (553, 155), color=(0.81, 0.83, 0.86), width=0.7)
    page.insert_text((42, 783), "Synthetic sample - no real patient information", fontsize=9, color=GRAY)
    page.insert_text((491, 783), f"Page {number} of 3", fontsize=9, color=GRAY)


def rows(page: fitz.Page, values: list[tuple[str, str]], start: int = 195, highlight: bool = False) -> int:
    y = start
    for index, (label, value) in enumerate(values):
        if highlight and index < 2:
            page.draw_rect(fitz.Rect(211, y - 13, min(545, 220 + len(value) * 6.2), y + 5),
                           color=None, fill=(0.88, 0.94, 1))
        page.insert_text((42, y), f"{label}:", fontsize=11, color=GRAY)
        page.insert_text((216, y), value, fontsize=11, color=INK)
        y += 35
    return y


def main() -> None:
    bundle = json.loads((ASSETS / "sample-claim.json").read_text())
    data = bundle["result"]["extracted_data"]
    identity, discharge, bill = data["identity"], data["discharge_summary"], data["itemized_bill"]
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    heading(page, "SAMPLE MEDICAL CLAIM", 1)
    rows(page, [
        ("Patient name", identity["patient_name"]),
        ("Policy number", identity["policy_number"]),
        ("Hospital", discharge["hospital_name"]),
        ("Insurer", identity["insurance_provider"]),
        ("Claim type", identity["claim_type"]),
        ("Admission", discharge["admission_date"]),
        ("Discharge", discharge["discharge_date"]),
        ("Total billed", money(bill["total_amount"])),
    ], highlight=True)

    page = doc.new_page(width=595, height=842)
    heading(page, "DISCHARGE SUMMARY", 2)
    y = rows(page, [
        ("Patient name", identity["patient_name"]),
        ("Hospital", discharge["hospital_name"]),
        ("Admitted", discharge["admission_date"]),
        ("Discharged", discharge["discharge_date"]),
        ("Diagnosis", discharge["final_diagnosis"]),
        ("Physician", discharge["attending_physician"]),
        ("Condition at discharge", discharge["condition_at_discharge"]),
    ])
    page.insert_text((42, y + 18), "Treatment summary", fontsize=12, fontname="hebo", color=INK)
    page.insert_textbox(fitz.Rect(42, y + 35, 545, y + 100), discharge["treatment_summary"],
                        fontsize=11, color=INK)

    page = doc.new_page(width=595, height=842)
    heading(page, "ITEMIZED BILL", 3)
    y = rows(page, [("Patient name", identity["patient_name"]), ("Bill number", bill["bill_number"]),
                    ("Bill date", bill["bill_date"]), ("Currency", bill["currency"])])
    y += 15
    page.draw_rect(fitz.Rect(42, y - 19, 553, y + 10), fill=(0.95, 0.96, 0.98), color=None)
    for x, text in [(52, "Description"), (310, "Qty"), (355, "Unit price"), (466, "Amount")]:
        page.insert_text((x, y), text, fontsize=10, fontname="hebo", color=GRAY)
    for item in bill["line_items"]:
        y += 38
        for x, text in [(52, item["description"]), (317, str(item["quantity"])),
                        (355, f'{Decimal(item["unit_price"]):,.2f}'), (466, f'{Decimal(item["amount"]):,.2f}')]:
            page.insert_text((x, y), text, fontsize=10, color=INK)
        page.draw_line((42, y + 13), (553, y + 13), color=(0.88, 0.89, 0.91), width=0.5)
    y += 60
    for label, value in [("Subtotal", bill["subtotal"]), ("Tax", bill["tax"]),
                         ("Discount", bill["discount"]), ("Total billed", bill["total_amount"])]:
        page.insert_text((288, y), f"{label}:", fontsize=11, fontname="hebo", color=INK)
        page.insert_text((411, y), money(value), fontsize=11, fontname="hebo", color=INK)
        y += 28

    doc.set_metadata({"title": "Synthetic medical claim demo", "author": "ClaimOps", "subject": "Fictional demonstration data"})
    pdf_path = ASSETS / bundle["filename"]
    doc.save(pdf_path, garbage=4, deflate=True, no_new_id=True)
    for index, meta in enumerate(bundle["pages"]):
        path = ROOT / "frontend" / "public" / meta["preview"].lstrip("/")
        doc[index].get_pixmap(matrix=fitz.Matrix(1.6, 1.6), alpha=False).save(path)
    print(f"Generated {doc.page_count} synthetic pages and PNG previews.")
    doc.close()


if __name__ == "__main__":
    main()
