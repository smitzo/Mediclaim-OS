import base64
from types import SimpleNamespace
import httpx
import pytest
from app.utils import llm_client
from app.services.provider_budget import budget_scope
from app.agents.segregator import _normalize_chunk_result


def test_openai_object_contract_and_usage(monkeypatch):
    monkeypatch.setattr(llm_client, "openai_api_key", "synthetic-test-key")
    def post(url, **kwargs):
        assert kwargs["json"]["response_format"] == {"type": "json_object"}
        return httpx.Response(200, request=httpx.Request("POST", url), json={"choices": [{"finish_reason": "stop", "message": {"content": '{"pages":[{"document_type":"identity_document"}]}'}}], "usage": {"prompt_tokens": 20, "completion_tokens": 10}})
    monkeypatch.setattr(llm_client.httpx, "post", post)
    with budget_scope() as budget:
        parsed = llm_client._call_openai_json("Return JSON", ["synthetic"], "gpt-4o-mini", 100)
        assert budget.snapshot()["input_tokens"] == 20
    assert _normalize_chunk_result([0], parsed)[0]["document_type"] == "identity_document"


def test_transient_provider_failures_are_classified(monkeypatch):
    monkeypatch.setattr(llm_client, "openai_api_key", "synthetic-test-key")
    monkeypatch.setattr(llm_client.httpx, "post", lambda url, **kwargs: httpx.Response(429, request=httpx.Request("POST", url)))
    with pytest.raises(llm_client.ProviderTransientError): llm_client._call_openai_json("JSON", ["synthetic"], "gpt-4o-mini", 100)


def test_gemini_supported_client_parts_and_usage(monkeypatch):
    monkeypatch.setattr(llm_client, "google_api_key", "synthetic-test-key")
    class Client:
        def __init__(self, **kwargs): self.models = self
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def generate_content(self, **kwargs):
            assert kwargs["config"].system_instruction == "Return JSON"
            assert kwargs["contents"][0].parts[0].inline_data.data == b"synthetic-image"
            return SimpleNamespace(text='{"patient_name":"Synthetic"}', usage_metadata=SimpleNamespace(prompt_token_count=5, candidates_token_count=7))
    monkeypatch.setattr(llm_client.genai, "Client", Client)
    with budget_scope() as budget:
        result = llm_client._call_gemini_json("Return JSON", [{"inline_data": {"data": base64.b64encode(b"synthetic-image").decode(), "mime_type": "image/png"}}, "text"], "configured-model", 100)
        assert result["patient_name"] == "Synthetic"
        assert budget.snapshot()["output_tokens"] == 7
