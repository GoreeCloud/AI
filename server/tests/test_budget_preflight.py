"""Provider credit-cap preflight is fail-closed and never sends prompts."""
import pytest
from fastapi import HTTPException

from app import providers


class FakeResponse:
    def __init__(self, info=None, status=200):
        self.status_code = status
        self.info = info
        self.content = b'{"data":{}}'

    def json(self):
        return {"data": self.info}


class FakeHTTP:
    def __init__(self, response):
        self.response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return False

    async def get(self, url, headers):
        assert url == "https://openrouter.ai/api/v1/key"
        assert headers["Authorization"] == "Bearer fake-only"
        return self.response


@pytest.fixture(autouse=True)
def provider_key(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-only")
    monkeypatch.setenv("GOREECLOUD_AI_REQUIRE_CAPPED_OPENROUTER_KEY", "true")


@pytest.mark.asyncio
async def test_capped_key_accepted(monkeypatch):
    response = FakeResponse({"limit": 25, "limit_remaining": 18,
                             "include_byok_in_limit": True})
    monkeypatch.setattr(providers.httpx, "AsyncClient",
                        lambda **kwargs: FakeHTTP(response))
    await providers.verify_cloud_key_budget()


@pytest.mark.asyncio
@pytest.mark.parametrize("data", [
    {"limit": None, "limit_remaining": None},
    {"limit": 0, "limit_remaining": 0},
    {"limit": 1, "limit_remaining": 0},
    {"limit": "10", "limit_remaining": "4"},
    {"limit": 10, "limit_remaining": 30},
    {"limit": 10, "limit_remaining": 3},
    {"limit": 10, "limit_remaining": 3, "include_byok_in_limit": False, "byok_usage": 0},
    {"limit": 10, "limit_remaining": 3,
     "include_byok_in_limit": False, "byok_usage": 0.5},
])
async def test_unprotected_provider_key_rejected(monkeypatch, data):
    monkeypatch.setattr(providers.httpx, "AsyncClient",
                        lambda **kwargs: FakeHTTP(FakeResponse(data)))
    with pytest.raises(HTTPException) as error:
        await providers.verify_cloud_key_budget()
    assert error.value.status_code == 503


@pytest.mark.asyncio
async def test_cap_lookup_denial_and_opt_out(monkeypatch):
    monkeypatch.setattr(providers.httpx, "AsyncClient",
                        lambda **kwargs: FakeHTTP(FakeResponse({}, 403)))
    with pytest.raises(HTTPException):
        await providers.verify_cloud_key_budget()
    monkeypatch.setenv("GOREECLOUD_AI_REQUIRE_CAPPED_OPENROUTER_KEY", "false")
    await providers.verify_cloud_key_budget()


@pytest.mark.asyncio
async def test_missing_cloud_key_fails_closed(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(HTTPException) as error:
        await providers.verify_cloud_key_budget()
    assert error.value.status_code == 503
