import asyncio
import json

import httpx
import pytest

from app.cache import TTLCache
from app.llm.base import ImageInput, LLMError
from app.llm.openai_compat import OpenAICompatClient

SCHEMA = {"type": "object", "additionalProperties": False, "required": ["a"], "properties": {"a": {"type": "string"}}}


def _ok(content: dict) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(content)}}]})


def _client(handler) -> OpenAICompatClient:
    return OpenAICompatClient(api_key="k", model_id="m", transport=httpx.MockTransport(handler), max_retries=2)


def _call(c: OpenAICompatClient, **kw):
    return asyncio.run(c.complete_json(system="s", user="u", schema_name="t", schema=SCHEMA, **kw))


def test_payload_uses_strict_json_schema_and_inline_images():
    seen = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(req.content)
        seen["auth"] = req.headers["authorization"]
        return _ok({"a": "x"})

    assert _call(_client(handler), images=[ImageInput(b"\xff\xd8jpeg")]) == {"a": "x"}
    body = seen["body"]
    assert seen["auth"] == "Bearer k"
    assert body["response_format"]["json_schema"]["strict"] is True
    parts = body["messages"][1]["content"]
    assert parts[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")


def test_retries_on_429_then_succeeds():
    calls = {"n": 0}

    def handler(req):
        calls["n"] += 1
        return httpx.Response(429, text="slow down") if calls["n"] < 3 else _ok({"a": "y"})

    assert _call(_client(handler)) == {"a": "y"}
    assert calls["n"] == 3


def test_no_retry_on_400():
    calls = {"n": 0}

    def handler(req):
        calls["n"] += 1
        return httpx.Response(400, text="bad schema")

    with pytest.raises(LLMError):
        _call(_client(handler))
    assert calls["n"] == 1


@pytest.mark.parametrize(
    "choice",
    [
        {"finish_reason": "length", "message": {"content": '{"a": '}},
        {"finish_reason": "stop", "message": {"content": None, "refusal": "no"}},
        {"finish_reason": "stop", "message": {"content": "not json"}},
    ],
)
def test_bad_completions_raise(choice):
    with pytest.raises(LLMError):
        _call(_client(lambda req: httpx.Response(200, json={"choices": [choice]})))


def test_cache_single_flight_and_ttl():
    cache = TTLCache()
    calls = {"n": 0}

    async def factory():
        calls["n"] += 1
        await asyncio.sleep(0.01)
        return "v"

    async def main():
        results = await asyncio.gather(*[cache.get_or_create("k", factory, 60) for _ in range(20)])
        assert set(results) == {"v"}
        await cache.get_or_create("short", factory, -1)  # already expired
        await cache.get_or_create("short", factory, 60)

    asyncio.run(main())
    assert calls["n"] == 3
