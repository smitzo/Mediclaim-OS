"""Deterministic component evaluation. Does not call providers or claim live accuracy."""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.agents.segregator import _heuristic_classify_page
from app.core.versions import PIPELINE_VERSION, SCHEMA_VERSION, PROMPT_VERSION
from app.services.evidence import build_evidence
from app.services.quality import quality_summary
from app.services.validation import validate_claim
from app.utils.text_extractors import extract_identity_data_from_text, extract_discharge_data_from_text, extract_bill_data_from_text

ROOT = Path(__file__).resolve().parents[1]
EXTRACTORS = {"identity_document": ("identity", extract_identity_data_from_text), "discharge_summary": ("discharge_summary", extract_discharge_data_from_text), "itemized_bill": ("itemized_bill", extract_bill_data_from_text)}


def evaluate():
    path = ROOT/"evaluation/synthetic_claims.json"
    dataset = json.loads(path.read_text())
    matched = labels = emitted_labels = money_correct = money_labels = spans = valid_spans = expected = found = classified = correct_class = reviewed = 0
    started = time.perf_counter()
    for case in dataset["cases"]:
        data, texts, docmap = {}, {}, {}
        for index, doc in enumerate(case["documents"]):
            texts[index] = doc["text"]
            docmap.setdefault(doc["type"], []).append(index)
            prediction = _heuristic_classify_page(index, doc["text"])
            classified += 1
            correct_class += bool(prediction and prediction["document_type"] == doc["type"] or not prediction and doc["type"] == "other")
            if doc["type"] in EXTRACTORS:
                section, extractor = EXTRACTORS[doc["type"]]
                data[section] = extractor(doc["text"]).model_dump(mode="json")
        evidence = build_evidence(data, texts, docmap, {section: "text" for section in data})
        findings = validate_claim(data, evidence)
        reviewed += bool(findings or quality_summary(data, evidence)["requires_review"])
        for field, value in case["expected_fields"].items():
            section, key = field.split(".", 1)
            actual = data.get(section, {}).get(key)
            labels += 1
            emitted_labels += actual not in (None, "")
            matched += actual == value
            if key == "total_amount": money_labels += 1; money_correct += actual == value
        for item in evidence.values():
            if item.verification == "text_match":
                spans += 1
                valid_spans += texts[item.source_page-1][item.span_start:item.span_end] == item.source_value
        codes = {item.code for item in findings}
        expected += len(case["expected_findings"])
        found += sum(code in codes for code in case["expected_findings"])
    metrics = {"field_precision": matched/max(1, emitted_labels), "field_recall": matched/max(1, labels), "monetary_exactness": money_correct/max(1, money_labels), "evidence_span_correctness": valid_spans/max(1, spans), "expected_finding_recall": found/max(1, expected), "classification_accuracy": correct_class/max(1, classified), "review_rate": reviewed/len(dataset["cases"]), "latency_seconds": time.perf_counter()-started, "provider_calls": 0}
    thresholds = json.loads((ROOT/"evaluation/acceptance.json").read_text())
    return {"mode": "deterministic_component", "metric_scope": "declared labeled fields only; evidence metric checks span integrity, not semantic correctness", "dataset_version": dataset["dataset_version"], "dataset_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "pipeline_version": PIPELINE_VERSION, "schema_version": SCHEMA_VERSION, "prompt_version": PROMPT_VERSION, "model": "none", "metrics": metrics, "regression_passed": all(metrics[key] >= value for key, value in thresholds["component_regression"].items()), "production_accepted": False, "production_blockers": [key for key, value in thresholds["production"].items() if value is None]+thresholds["required_staging_evidence"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--production", action="store_true")
    args = parser.parse_args()
    report = evaluate()
    text = json.dumps(report, indent=2)
    if args.output: args.output.write_text(text+"\n")
    print(text)
    raise SystemExit(2 if args.production and not report["production_accepted"] else 0 if report["regression_passed"] else 1)


if __name__ == "__main__": main()
