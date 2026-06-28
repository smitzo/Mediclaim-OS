"""Money v2: finite decimal strings, two places, ROUND_HALF_UP; unknown currency stays null."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Annotated
from pydantic import BeforeValidator

CENT = Decimal("0.01")
TOLERANCE = Decimal("0.01")


def money(value):
    if isinstance(value, bool): raise ValueError("Boolean is not a monetary value.")
    try: result = Decimal(str(value))
    except InvalidOperation as exc: raise ValueError("Invalid monetary value.") from exc
    if not result.is_finite() or abs(result) > Decimal("999999999999999"):
        raise ValueError("Monetary value is not finite or is outside the supported range.")
    return result.quantize(CENT, rounding=ROUND_HALF_UP)


Money = Annotated[Decimal, BeforeValidator(money)]
