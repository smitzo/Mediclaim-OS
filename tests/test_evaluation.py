from scripts.evaluate_quality import evaluate


def test_labeled_component_regression_and_unset_production_gate():
    report = evaluate()
    assert report["regression_passed"], report["metrics"]
    assert report["metrics"]["provider_calls"] == 0
    assert not report["production_accepted"]
    assert report["production_blockers"]
