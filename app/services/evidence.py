"""Literal source-span evidence. A text match is not calibrated confidence."""
import re
from app.core.schemas import FieldEvidence

SECTION_TYPES = {
    "identity": ("identity_document", "claim_forms", "cheque_or_bank_details"),
    "discharge_summary": ("discharge_summary", "prescription"),
    "itemized_bill": ("itemized_bill", "cash_receipt", "investigation_report"),
}


def leaves(value, path=""):
    if isinstance(value, dict):
        for key, item in value.items():
            if key != "extra_fields": yield from leaves(item, f"{path}.{key}" if path else key)
    elif isinstance(value, list):
        for index, item in enumerate(value): yield from leaves(item, f"{path}.{index}")
    else: yield path, value


def build_evidence(data, texts, document_map, methods):
    evidence = {}
    for path, value in leaves(data):
        section = path.split(".")[0]
        entry = FieldEvidence(field=path, normalized_value=value, method=methods.get(section, "unknown"), verification="missing_value" if value is None or value == "" else "missing_evidence")
        pages = sorted({page for kind in SECTION_TYPES.get(section, ()) for page in document_map.get(kind, [])})
        if value is not None and value != "":
            pattern = r"\s+".join(re.escape(piece) for piece in str(value).split())
            if pattern:
                for page in pages:
                    text = texts.get(page, "")
                    match = re.search(r"(?<!\w)"+pattern+r"(?!\w)", text, re.IGNORECASE)
                    if match:
                        entry = entry.model_copy(update={"source_page": page+1, "source_value": match.group(), "supporting_text": text[max(0,text.rfind("\n",0,match.start())+1):text.find("\n",match.end()) if "\n" in text[match.end():] else len(text)], "span_start": match.start(), "span_end": match.end(), "verification": "text_match"})
                        break
        if path.split(".")[-1] in data.get(section, {}).get("extra_fields", {}).get("derived_fields", []):
            entry = entry.model_copy(update={"method": "derived", "verification": "derived", "source_page": None, "source_value": None, "supporting_text": None, "span_start": None, "span_end": None})
        evidence[path] = entry
    return evidence
