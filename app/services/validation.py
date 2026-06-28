"""Versioned review findings; successful execution never implies approval."""
import hashlib
import re
import unicodedata
from collections import Counter
from datetime import date
from decimal import Decimal
from pydantic import ValidationError
from app.core.money import money, TOLERANCE
from app.core.schemas import ItemizedBillData, ValidationFinding
from app.services.quality import REQUIRED, missing_fields


def normalize(value):
    return re.sub(r"[\W_]+", "", unicodedata.normalize("NFKC", str(value)).casefold())


def parse_date(value):
    if not value: return None
    value = str(value).strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value): return date.fromisoformat(value)
    match = re.fullmatch(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", value)
    if match:
        first, second, year = map(int, match.groups())
        if first > 12 and second <= 12: return date(year, second, first)
        if second > 12 and first <= 12: return date(year, first, second)
    raise ValueError("Date is ambiguous or unsupported.")


def validate_claim(data, evidence=None):
    findings = []
    evidence = evidence or {}
    def add(code, fields, message, severity="error"):
        identifier = hashlib.sha256((code+"|"+"|".join(fields)).encode()).hexdigest()[:20]
        findings.append(ValidationFinding(id=identifier, code=code, severity=severity, fields=fields, evidence=[field for field in fields if field in evidence], message=message))
    for section in REQUIRED:
        for field in missing_fields(section, data.get(section, {})):
            add("required_field_missing", [f"{section}.{field}"], "Required field is missing.")
    for path, item in evidence.items():
        if item.verification == "missing_evidence": add("unsupported_field", [path], "No literal source evidence supports this value.")
    identity, bill, discharge = (data.get(key, {}) for key in ("identity", "itemized_bill", "discharge_summary"))
    if identity.get("patient_name") and bill.get("patient_name") and normalize(identity["patient_name"]) != normalize(bill["patient_name"]):
        add("patient_mismatch", ["identity.patient_name", "itemized_bill.patient_name"], "Patient identity differs between documents.")
    for field in ("policy_number", "patient_name"):
        values = [(section, payload.get(field)) for section, payload in data.items() if isinstance(payload, dict) and payload.get(field)]
        if len({normalize(value) for _, value in values}) > 1 and field == "policy_number":
            add("policy_mismatch", [f"{section}.{field}" for section, _ in values], "Policy identifiers differ between documents.")
    parsed = {}
    for section, fields in (("discharge_summary", ("admission_date", "discharge_date")), ("itemized_bill", ("bill_date",))):
        for field in fields:
            value = data.get(section, {}).get(field)
            if value:
                try: parsed[field] = parse_date(value)
                except ValueError: add("ambiguous_date", [f"{section}.{field}"], "Date cannot be normalized unambiguously.")
    if parsed.get("admission_date") and parsed.get("discharge_date") and parsed["admission_date"] > parsed["discharge_date"]:
        add("date_order", ["discharge_summary.admission_date", "discharge_summary.discharge_date"], "Admission is after discharge.")
    try: model = ItemizedBillData.model_validate(bill)
    except ValidationError:
        add("invalid_bill_schema", ["itemized_bill"], "Billing fields do not match the monetary schema.")
        return findings
    if model.line_items:
        total = money(sum((item.amount for item in model.line_items), Decimal("0")))
        expected_subtotal = model.subtotal if model.subtotal is not None else total
        if model.subtotal is not None and abs(total-model.subtotal) > TOLERANCE:
            add("line_sum_mismatch", ["itemized_bill.line_items", "itemized_bill.subtotal"], "Line items do not reconcile with subtotal.")
        expected_total = expected_subtotal+(model.tax or Decimal("0"))-(model.discount or Decimal("0"))
        if model.total_amount is not None and abs(expected_total-model.total_amount) > TOLERANCE:
            add("total_mismatch", ["itemized_bill.total_amount", "itemized_bill.line_items"], "Bill total does not reconcile with charges, tax, and discount.")
        counts = Counter((normalize(item.description), item.date, item.quantity, item.unit_price, item.amount) for item in model.line_items)
        if any(count > 1 for count in counts.values()):
            add("duplicate_charge", ["itemized_bill.line_items"], "Repeated charges require review.")
    if model.total_amount is not None and model.insurance_payment is not None and model.patient_responsibility is not None:
        if abs(model.total_amount-model.insurance_payment-model.patient_responsibility) > TOLERANCE:
            add("payment_mismatch", ["itemized_bill.total_amount", "itemized_bill.insurance_payment", "itemized_bill.patient_responsibility"], "Payments and patient responsibility do not reconcile.")
    if any(getattr(model, field) is not None and getattr(model, field) < 0 for field in ("subtotal", "tax", "discount", "total_amount", "insurance_payment", "patient_responsibility")):
        add("negative_amount", ["itemized_bill"], "Negative amounts require a supported adjustment profile.")
    return findings
