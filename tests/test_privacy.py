import logging
import pytest
from app.utils.llm_client import _extract_json
from app.agents.id_agent import id_agent
from app.core.schemas import ClaimState, SegregatorOutput


def test_invalid_model_json_never_echoes_document():
    secret = "Synthetic Patient diagnosis account=123 secret-token"
    with pytest.raises(ValueError) as error: _extract_json(secret)
    assert secret not in str(error.value)


def test_request_validation_does_not_echo_credentials(client):
    secret = "synthetic-secret-password"
    response = client.post("/api/auth/sign-in", json={"username": {"password": secret}, "password": secret})
    assert response.status_code == 422 and secret not in response.text


def test_claim_identifier_absent_from_stage_logs(caplog):
    caplog.set_level(logging.INFO)
    id_agent(ClaimState(claim_id="SyntheticSensitiveClaimID", segregator_output=SegregatorOutput()))
    assert "SyntheticSensitiveClaimID" not in caplog.text
