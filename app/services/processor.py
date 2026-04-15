"""Claim processing service boundary."""

from __future__ import annotations

import logging
from typing import Any

from app.core.graph import claim_graph
from app.core.schemas import ClaimResponse, ClaimState

logger = logging.getLogger(__name__)


def process_claim_pdf(claim_id: str, pdf_bytes: bytes) -> ClaimResponse:
    """Run the LangGraph pipeline and return a stable API response."""
    initial_state = ClaimState(claim_id=claim_id, pdf_bytes=pdf_bytes)
    final_state = claim_graph.invoke(initial_state)
    state_dict = _state_to_dict(final_state)

    response: ClaimResponse | None = state_dict.get("final_response") or state_dict.get("_response")
    if response is not None:
        return response

    errors = state_dict.get("errors", [])
    if not errors:
        errors = ["Aggregator did not produce a response."]
    if not isinstance(errors, list):
        errors = [str(errors)]

    logger.error(
        "Aggregator response missing for claim %s | keys=%s",
        claim_id,
        sorted(state_dict.keys()),
    )
    return ClaimResponse(
        claim_id=claim_id,
        status="failed",
        errors=errors,
    )


def _state_to_dict(final_state: Any) -> dict[str, Any]:
    if isinstance(final_state, dict):
        return final_state
    try:
        return dict(final_state) if hasattr(final_state, "__iter__") else final_state.__dict__
    except Exception:
        return {}
