"""Minimum local completeness policy, distinct from processing success."""
REQUIRED = {
    "identity": ("patient_name", "policy_number"),
    "discharge_summary": ("admission_date", "discharge_date", "final_diagnosis", "hospital_name"),
    "itemized_bill": ("line_items", "total_amount", "currency"),
}


def missing_fields(section, payload):
    return [field for field in REQUIRED[section] if payload.get(field) in (None, "", [])]


def complete(section, model): return not missing_fields(section, model.model_dump())


def quality_summary(data, evidence):
    missing = [f"{section}.{field}" for section in REQUIRED for field in missing_fields(section, data.get(section, {}))]
    unsupported = [path for path, item in evidence.items() if item.verification == "missing_evidence"]
    return {"policy_version": "synthetic-claim-v1", "missing_required_fields": missing, "unsupported_fields": unsupported, "requires_review": bool(missing or unsupported)}
