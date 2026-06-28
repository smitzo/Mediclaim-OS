from decimal import Decimal
import pytest
from pydantic import ValidationError
from app.core.schemas import ItemizedBillData, BillLineItem
from app.core.money import money


def test_exact_decimal_contract_and_rounding():
    bill = ItemizedBillData(currency="INR", line_items=[BillLineItem(description="a", amount="0.10"), BillLineItem(description="b", amount="0.20")], total_amount="0.30")
    assert sum(item.amount for item in bill.line_items) == Decimal("0.30")
    assert bill.model_dump(mode="json")["total_amount"] == "0.30"
    assert money("1.005") == Decimal("1.01")
    assert ItemizedBillData().currency is None


@pytest.mark.parametrize("value", ["NaN", "Infinity", True, "1e100"])
def test_invalid_money_rejected(value):
    with pytest.raises(ValidationError): BillLineItem(description="invalid", amount=value)
