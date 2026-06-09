"""LLM client utilities for JSON extraction.

OpenAI is the default provider. Gemini remains available by setting
LLM_PROVIDER=gemini for older deployments.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Union

import httpx
import google.generativeai as genai
from google.generativeai.types import HarmBlockThreshold, HarmCategory

from app.core.config import settings

logger = logging.getLogger(__name__)

provider = (settings.llm_provider or "openai").lower()
openai_api_key = settings.openai_api_key or os.environ.get("OPENAI_API_KEY", "")
google_api_key = settings.google_api_key or os.environ.get("GOOGLE_API_KEY", "")

if provider == "gemini" and google_api_key:
    genai.configure(api_key=google_api_key)
    logger.info("[LLM] Gemini configured")
elif provider == "openai" and openai_api_key:
    logger.info("[LLM] OpenAI configured")
else:
    logger.warning("[LLM] Missing API key for provider=%s", provider)


def build_vision_message(prompt: str, images: list[str]) -> list[Union[str, dict]]:
    """Build a provider-neutral content list with base64 PNG images and text."""
    content: list[Union[str, dict]] = []
    for b64 in images:
        content.append({
            "inline_data": {
                "mime_type": "image/png",
                "data": b64,
            }
        })
    content.append(prompt)
    return content


def build_simple_message(prompt: str) -> str:
    return prompt


def call_llm_json(
    system_prompt: str,
    messages: list[Any],
    model: str | None = None,
    max_tokens: int = 2048,
) -> Any:
    """Call the configured LLM with vision-capable content and parse JSON."""
    if provider == "gemini":
        return _call_gemini_json(system_prompt, messages, model or settings.gemini_model, max_tokens)
    return _call_openai_json(system_prompt, messages, model or settings.openai_model, max_tokens)


def call_llm_json_text_only(
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
    max_tokens: int = 2048,
) -> Any:
    """Call the configured LLM with text-only content and parse JSON."""
    if provider == "gemini":
        return _call_gemini_text_json(system_prompt, user_prompt, model or settings.gemini_model, max_tokens)
    return _call_openai_json(system_prompt, [user_prompt], model or settings.openai_model, max_tokens)


def _call_openai_json(system_prompt: str, messages: list[Any], model: str, max_tokens: int) -> Any:
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY is not configured. Set it in .env or environment variables.")

    content = _openai_content(messages)
    payload = {
        "model": model,
        "temperature": 0.1,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},
        ],
    }
    try:
        response = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openai_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=90,
        )
        response.raise_for_status()
        raw_text = response.json()["choices"][0]["message"]["content"]
        return _extract_json(raw_text)
    except Exception as exc:
        logger.exception("[LLM] OpenAI API call failed")
        raise ValueError(f"OpenAI API call failed: {exc}") from exc


def _openai_content(messages: list[Any]) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = []
    for item in messages:
        if isinstance(item, str):
            content.append({"type": "text", "text": item})
            continue
        inline_data = item.get("inline_data") if isinstance(item, dict) else None
        if inline_data:
            mime_type = inline_data.get("mime_type", "image/png")
            data = inline_data.get("data", "")
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:{mime_type};base64,{data}"},
            })
    return content


def _call_gemini_json(system_prompt: str, messages: list[Any], model: str, max_tokens: int) -> Any:
    if not google_api_key:
        raise ValueError("GOOGLE_API_KEY is not configured. Set LLM_PROVIDER=openai or add a Gemini key.")
    gemini_model = _gemini_model(model, max_tokens)
    response = gemini_model.generate_content([system_prompt] + messages)
    return _extract_json(response.text)


def _call_gemini_text_json(system_prompt: str, user_prompt: str, model: str, max_tokens: int) -> Any:
    if not google_api_key:
        raise ValueError("GOOGLE_API_KEY is not configured. Set LLM_PROVIDER=openai or add a Gemini key.")
    gemini_model = _gemini_model(model, max_tokens)
    response = gemini_model.generate_content(f"{system_prompt}\n\n{user_prompt}")
    return _extract_json(response.text)


def _gemini_model(model: str, max_tokens: int):
    return genai.GenerativeModel(
        model_name=model,
        generation_config={"max_output_tokens": max_tokens, "temperature": 0.1},
        safety_settings={
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        },
    )


def _extract_json(text: str) -> Any:
    text = re.sub(r"```(?:json)?", "", text).strip()
    text = re.sub(r"```", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    candidate = _find_balanced_json(text)
    if candidate is not None:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    raise ValueError(f"Could not extract valid JSON from model response. Preview:\n{text[:500]}")


def _find_balanced_json(text: str) -> str | None:
    start = None
    opening = ""
    closing = ""
    stack: list[str] = []
    in_string = False
    escape = False

    for idx, ch in enumerate(text):
        if start is None:
            if ch == "{":
                start = idx
                opening = "{"
                closing = "}"
                stack = [closing]
            elif ch == "[":
                start = idx
                opening = "["
                closing = "]"
                stack = [closing]
            continue

        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
            continue
        if ch == opening:
            stack.append(closing)
            continue
        if ch == "{":
            stack.append("}")
            continue
        if ch == "[":
            stack.append("]")
            continue
        if stack and ch == stack[-1]:
            stack.pop()
            if not stack and start is not None:
                return text[start:idx + 1]
    return None
