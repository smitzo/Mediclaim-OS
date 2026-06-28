from app.services.evidence import build_evidence


def test_only_exact_source_spans_receive_citations():
    text = "Patient Name: Synthetic Patient\nPolicy: TEST-123"
    evidence = build_evidence({"identity": {"patient_name": "Synthetic Patient", "policy_number": "invented", "email": None}}, {0: text, 1: "invented"}, {"identity_document": [0]}, {"identity": "text"})
    match = evidence["identity.patient_name"]
    assert text[match.span_start:match.span_end] == match.source_value
    assert match.source_page == 1 and match.confidence is None
    assert evidence["identity.policy_number"].verification == "missing_evidence"
    assert evidence["identity.email"].verification == "missing_value"
