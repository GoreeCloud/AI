"""OpenRouter metadata-only generation cost checks. No live provider or paid calls."""
import asyncio
import json

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import providers
from app.main import app

OWNER = {"Authorization": "Bearer test-owner-token"}


@pytest.fixture(autouse=True)
def fake_account(monkeypatch):
    monkeypatch.setenv("GOREECLOUD_AI_AUTH_MODE", "owner")
    monkeypatch.setenv("GOREECLOUD_AI_TOKEN", "test-owner-token")
    monkeypatch.setenv("OPENROUTER_API_KEY", "synthetic-server-only-key")
    monkeypatch.setattr(providers, "_generation_slots", asyncio.Semaphore(2))


@pytest.fixture
def mock_lookup(monkeypatch):
    seen = []
    state = {"status": 200, "payload": {
        "data": {"id": "gen-123abcDEF", "model": "test/model",
                 "total_cost": 0.0125, "prompt": "Sensitive should be ignored",
                 "completion": "Private completion should be ignored",
                 "tokens_prompt": 12},
    }}

    class Reply:
        status_code = 200
        async def __aenter__(self):
            self.status_code = state["status"]
            return self
        async def __aexit__(self, *_):
            return False
        async def aiter_bytes(self):
            yield json.dumps(state["payload"]).encode()

    class Client:
        def __init__(self, **kwargs):
            assert kwargs == {"timeout": 8, "follow_redirects": False, "trust_env": False}
        async def __aenter__(self):
            return self
        async def __aexit__(self, *_):
            return False
        def stream(self, method, url, params, headers):
            seen.append((method, url, params, headers))
            return Reply()

    monkeypatch.setattr(providers.httpx, "AsyncClient", Client)
    return seen, state


@pytest.mark.asyncio
async def test_query_cost_returns_only_bounded_cost_metadata(mock_lookup):
    seen, _state = mock_lookup
    outcome = await providers.generation_cost("gen-123abcDEF")
    assert outcome == {
        "generation_id": "gen-123abcDEF",
        "model": "test/model",
        "total_cost_usd": 0.0125,
        "source": "openrouter-reported-generation",
        "note": "Provider metadata only; not an independent invoice or hard USD spending cap",
    }
    assert seen == [("GET", "https://openrouter.ai/api/v1/generation",
                    {"id": "gen-123abcDEF"}, {
                        "Authorization": "Bearer synthetic-server-only-key",
                        "Accept": "application/json",
                    })]
    assert "Sensitive should" not in json.dumps(outcome)
    assert "synthetic-server-only-key" not in json.dumps(outcome)


@pytest.mark.parametrize("invalid", [
    "", "gen-", "other-123abcDEF", "gen-abc?x=1",
    "gen-../../passwd", "gen-" + "a" * 126, "gen-💭", "gen-ABC/123",
])
@pytest.mark.asyncio
async def test_invalid_generation_ids_denied_before_network(monkeypatch, invalid):
    class NoClient:
        def __init__(self, **_):
            raise AssertionError("Untrusted identifier reached outbound HTTP")
    monkeypatch.setattr(providers.httpx, "AsyncClient", NoClient)
    with pytest.raises(HTTPException) as error:
        await providers.generation_cost(invalid)
    assert error.value.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [
    {"data": {"id": "gen-other", "model": "x/y", "total_cost": 0.1}},
    {"data": {"id": "gen-123abcDEF", "model": "x/y", "total_cost": "0.1"}},
    {"data": {"id": "gen-123abcDEF", "model": "x/y", "total_cost": True}},
    {"data": {"id": "gen-123abcDEF", "model": "x/y", "total_cost": -0.1}},
    {"data": {"id": "gen-123abcDEF", "model": "x/y", "total_cost": float("nan")}},
    {"data": {"id": "gen-123abcDEF", "model": [], "total_cost": 0.1}},
    {"error": {"message": "upstream-private-metadata"}},
])
async def test_reject_untrusted_provider_metadata(mock_lookup, payload):
    _seen, state = mock_lookup
    state["payload"] = payload
    with pytest.raises(HTTPException) as error:
        await providers.generation_cost("gen-123abcDEF")
    assert error.value.status_code == 502
    assert "upstream-private" not in str(error.value.detail)


@pytest.mark.asyncio
async def test_no_redirect_or_forbidden_provider_metadata(mock_lookup):
    _seen, state = mock_lookup
    state["status"] = 302
    with pytest.raises(HTTPException) as error:
        await providers.generation_cost("gen-123abcDEF")
    assert error.value.status_code == 502


@pytest.mark.asyncio
async def test_no_token_or_capacity_denies_before_contact(monkeypatch, mock_lookup):
    seen, _ = mock_lookup
    monkeypatch.delenv("OPENROUTER_API_KEY")
    with pytest.raises(HTTPException) as error:
        await providers.generation_cost("gen-123abcDEF")
    assert error.value.status_code == 503
    monkeypatch.setenv("OPENROUTER_API_KEY", "synthetic-server-only-key")
    monkeypatch.setattr(providers, "_generation_slots", asyncio.Semaphore(0))
    with pytest.raises(HTTPException) as error:
        await providers.generation_cost("gen-123abcDEF")
    assert error.value.status_code == 429
    assert not seen


@pytest.mark.asyncio
async def test_chat_reports_safe_generation_id(monkeypatch):
    async def fake_post(*_args, **_kwargs):
        return {"id": "gen-123abcDEF", "model": "mock/model",
                "choices": [{"message": {"content": "safe answer"}}],
                "usage": {"prompt_tokens": 12}}
    monkeypatch.setattr(providers, "_post", fake_post)
    result = await providers.chat([{"role": "user", "content": "Synthetic"}],
                                  "openrouter/auto", "openrouter", False)
    assert result["generation_id"] == "gen-123abcDEF"
    assert result["content"] == "safe answer"


@pytest.mark.asyncio
async def test_invalid_model_generation_id_not_exposed(monkeypatch):
    async def fake_post(*_args, **_kwargs):
        return {"id": "https://evil.test/?token=secret", "model": "mock/model",
                "choices": [{"message": {"content": "safe answer"}}]}
    monkeypatch.setattr(providers, "_post", fake_post)
    result = await providers.chat([{"role": "user", "content": "Synthetic"}],
                                  "openrouter/auto", "openrouter", False)
    assert "generation_id" not in result


def test_generation_lookup_endpoint_is_owner_protected(mock_lookup):
    client = TestClient(app)
    assert client.get("/api/v1/usage/openrouter/gen-123abcDEF").status_code == 401
    assert client.get("/api/v1/usage/openrouter/gen-123abcDEF",
                      headers=OWNER).status_code == 200
    assert client.get("/api/v1/usage/openrouter/gen-../..",
                      headers=OWNER).status_code in (404, 422)


@pytest.mark.asyncio
async def test_upstream_network_exception_scrubs_error(monkeypatch):
    class DisconnectedClient:
        def __init__(self, **_):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *_):
            return False
        def stream(self, *_args, **_kwargs):
            raise httpx.ConnectError("private-provider-host-secret")
    monkeypatch.setattr(providers.httpx, "AsyncClient", DisconnectedClient)
    with pytest.raises(HTTPException) as error:
        await providers.generation_cost("gen-123abcDEF")
    assert error.value.status_code == 502
    assert "private-provider-host-secret" not in str(error.value.detail)


@pytest.mark.asyncio
async def test_stream_includes_bounded_generation_id(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "synthetic-server-only-key")
    class StreamResponse:
        status_code = 200
        headers = {"X-Generation-Id": "gen-header1234"}
        async def __aenter__(self):
            return self
        async def __aexit__(self, *_):
            return False
        async def aiter_lines(self):
            yield 'data: {"id":"gen-event1234","model":"sample/model","choices":[{"delta":{"content":"Hi"}}]}'
            yield "data: [DONE]"
    class FakeHTTP:
        def __init__(self, **_):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *_):
            return False
        def stream(self, *_args, **_kwargs):
            return StreamResponse()
    monkeypatch.setattr(providers.httpx, "AsyncClient", FakeHTTP)
    events = [item async for item in providers.stream_chat(
        [{"role": "user", "content": "synthetic example"}],
        "openrouter/auto", "openrouter",
    )]
    assert events[0] == {"type": "delta", "content": "Hi"}
    assert events[-1] == {
        "type": "done", "provider": "openrouter", "model": "sample/model",
        "generation_id": "gen-event1234",
    }
    assert "synthetic example" not in json.dumps(events)


@pytest.mark.asyncio
async def test_oversized_generation_metadata_rejected(monkeypatch):
    class LargeResponse:
        status_code = 200
        async def __aenter__(self):
            return self
        async def __aexit__(self, *_):
            return False
        async def aiter_bytes(self):
            yield b"x" * 65537
    class StubClient:
        def __init__(self, **_):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *_):
            return False
        def stream(self, *_args, **_kwargs):
            return LargeResponse()
    monkeypatch.setattr(providers.httpx, "AsyncClient", StubClient)
    with pytest.raises(HTTPException) as err:
        await providers.generation_cost("gen-123abcDEF")
    assert err.value.status_code == 502
