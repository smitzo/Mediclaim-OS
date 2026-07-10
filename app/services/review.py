from copy import deepcopy
from fastapi import HTTPException
from pydantic import ValidationError
from app.core.schemas import IdentityData, DischargeSummaryData, ItemizedBillData

MODELS = {"identity": IdentityData, "discharge_summary": DischargeSummaryData, "itemized_bill": ItemizedBillData}
BLOCKING = {"required_field_missing", "invalid_bill_schema", "patient_mismatch", "policy_mismatch", "date_order", "total_mismatch", "line_sum_mismatch", "payment_mismatch", "negative_amount"}


def corrected_result(original, corrections):
    result = deepcopy(original)
    for section, changes in corrections.items():
        model = MODELS.get(section)
        if model is None or not isinstance(changes, dict) or set(changes)-set(model.model_fields):
            raise HTTPException(status_code=422, detail="Corrections contain unsupported fields.")
        try: result[section] = model.model_validate({**result.get(section, {}), **changes}).model_dump(mode="json")
        except ValidationError: raise HTTPException(status_code=422, detail="Corrections do not match the result schema.")
    return result


def approval_allowed(findings, acknowledged, notes):
    if any(item.code in BLOCKING for item in findings):
        raise HTTPException(status_code=422, detail="Resolve blocking validation findings before approval.")
    required = {item.id for item in findings if item.severity in {"error", "warning"}}
    if not required.issubset(set(acknowledged)) or required and not notes.strip():
        raise HTTPException(status_code=422, detail="Acknowledge remaining findings and record review notes before approval.")
