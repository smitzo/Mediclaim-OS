from app.services.validation import validate_claim


def test_conflicting_identity_dates_duplicates_and_totals():
    data = {"identity": {"patient_name": "Synthetic A", "policy_number": "P-1"}, "discharge_summary": {"admission_date": "2026-10-20", "discharge_date": "2026-10-10", "final_diagnosis": "Synthetic", "hospital_name": "Synthetic Hospital"}, "itemized_bill": {"patient_name": "Synthetic B", "bill_date": "01/02/2026", "currency": "INR", "line_items": [{"description": "Test", "amount": "0.10"}, {"description": "Test", "amount": "0.10"}], "total_amount": "0.30"}}
    codes = {item.code for item in validate_claim(data)}
    assert {"patient_mismatch", "date_order", "ambiguous_date", "duplicate_charge", "total_mismatch"} <= codes
    assert all(item.id and item.fields for item in validate_claim(data))


def test_normalized_identity_and_exact_money():
    data = {"identity": {"patient_name": " Synthetic Patient ", "policy_number": "P-1"}, "itemized_bill": {"patient_name": "synthetic patient", "currency": "INR", "line_items": [{"description": "a", "amount": "0.10"}, {"description": "b", "amount": "0.20"}], "total_amount": "0.30"}}
    codes = {item.code for item in validate_claim(data)}
    assert "patient_mismatch" not in codes
    assert "total_mismatch" not in codes
