from concurrent.futures import ThreadPoolExecutor
import pytest
from app.services.provider_budget import ProviderBudget, ProviderBudgetExceeded
from app.services.quality import complete, quality_summary
from app.core.schemas import IdentityData


def test_signal_is_not_completeness():
    assert not complete("identity", IdentityData(patient_name="Synthetic Patient"))
    assert quality_summary({}, {})["requires_review"]


def test_concurrent_provider_budget_is_bounded():
    budget = ProviderBudget(max_calls=2, max_output_tokens=20)
    def reserve(_):
        try: budget.reserve(10); return True
        except ProviderBudgetExceeded: return False
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert sum(pool.map(reserve, range(5))) == 2
    assert budget.snapshot()["exhausted"]
