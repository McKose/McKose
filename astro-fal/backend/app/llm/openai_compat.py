"""OpenAI-compatible Chat Completions client (raw HTTP, no SDK).

Works against OpenAI and against Gemini's OpenAI-compatible endpoint
(https://generativelanguage.googleapis.com/v1beta/openai/), so switching
GPT-4o-mini <-> Gemini Flash is a config change, not a code change.
Uses ``response_format: json_schema`` (structured outputs) instead of asking
the model nicely for JSON.
"""

from __future__ import annotations

import asyncio
import base64
import json
import random
from typing import Any

import httpx

from app.llm.base import ImageInput, LLMError

_RETRY_STATUS = {408, 409, 429, 500, 502, 503, 504}


class OpenAICompatClient:
    def __init__(
        self,
        *,
        api_key: str,
        model_id: str,
        base_url: str = "https://api.openai.com/v1",
        timeout_s: float = 45.0,
        max_retries: int = 3,
        image_detail: str = "high",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.model_id = model_id
        self._url = base_url.rstrip("/") + "/chat/completions"
        self._headers = {"Authorization": f"Bearer {api_key}"}
        self._timeout = timeout_s
        self._max_retries = max_retries
        self._image_detail = image_detail
        self._transport = transport

    def _payload(self, system, user, schema_name, schema, images, temperature, max_tokens) -> dict[str, Any]:
        content: list[dict[str, Any]] = [{"type": "text", "text": user}]
        for img in images or []:
            b64 = base64.b64encode(img.data).decode()
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{img.mime_type};base64,{b64}", "detail": self._image_detail},
                }
            )
        return {
            "model": self.model_id,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": content}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": schema_name, "schema": schema, "strict": True},
            },
        }

    async def complete_json(
        self,
        *,
        system: str,
        user: str,
        schema_name: str,
        schema: dict[str, Any],
        images: list[ImageInput] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1200,
    ) -> dict[str, Any]:
        payload = self._payload(system, user, schema_name, schema, images, temperature, max_tokens)
        async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as client:
            for attempt in range(self._max_retries + 1):
                try:
                    resp = await client.post(self._url, headers=self._headers, json=payload)
                except httpx.TransportError as exc:
                    if attempt == self._max_retries:
                        raise LLMError(f"transport error: {exc}") from exc
                else:
                    if resp.status_code == 200:
                        return self._parse(resp.json())
                    if resp.status_code not in _RETRY_STATUS or attempt == self._max_retries:
                        raise LLMError(f"HTTP {resp.status_code}: {resp.text[:300]}")
                # Exponential backoff with full jitter.
                await asyncio.sleep(random.uniform(0, 0.5 * 2**attempt))
        raise LLMError("unreachable")

    @staticmethod
    def _parse(body: dict[str, Any]) -> dict[str, Any]:
        try:
            choice = body["choices"][0]
            msg = choice["message"]
        except (KeyError, IndexError) as exc:
            raise LLMError(f"malformed response: {str(body)[:300]}") from exc
        if msg.get("refusal"):
            raise LLMError(f"model refused: {msg['refusal']}")
        if choice.get("finish_reason") == "length":
            raise LLMError("output truncated (max_tokens)")
        try:
            return json.loads(msg["content"])
        except (TypeError, json.JSONDecodeError) as exc:
            raise LLMError("model did not return valid JSON") from exc
