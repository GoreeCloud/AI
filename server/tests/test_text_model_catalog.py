"""Read-only OpenRouter text catalog: synthetic provider transport, no paid calls."""
import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import providers
from app.main import app

client = TestClient(app)
HEADERS = {"Authorization": "Bearer test-owner-token"}


@pytest.fixture(autouse=True)
def owner(monkeypatch):
    monkeypatch.setenv("GOREECLOUD_AI_AUTH_MODE", "owner")
    monkeypatch.setenv("GOREECLOUD_AI_TOKEN", "test-owner-token")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-catalog-only-key")


def mocked(monkeypatch, handler):
    original = httpx.AsyncClient
    mock = httpx.MockTransport(handler)
    monkeypatch.setattr(providers.httpx, "AsyncClient",
                        lambda **opts: original(transport=mock, **opts))


@pytest.mark.asyncio
async def test_fixed_origin_catalog_redacts_and_sorts(monkeypatch):
    calls = []
    def handler(req):
        calls.append((req.method, str(req.url), req.headers.get("authorization")))
        return httpx.Response(200, json={"data": [
            {"id": "vendor/Z", "name": "Zulu", "context_length": 10000,
             "supported_parameters": ["temperature", "tools"], "secret": "must-not-leak",
             "pricing": {"prompt": "0.000003"}},
            {"id": "vendor/A", "name": "Alpha", "context_length": 1000,
             "supported_parameters": ["response_format"]},
            {"id": "vendor/A", "name": "Duplicate", "context_length": 500},
            {"id": "invalid model!", "name": "Invalid ID"},
            {"id": "vendor/B", "context_length": True, "supported_parameters": ["tool_choice"]},
        ]})
    mocked(monkeypatch, handler)
    result = await providers.text_model_catalog()
    assert result["source"] == "openrouter-text-model-catalog"
    assert [m["id"] for m in result["models"]] == ["vendor/A", "vendor/B", "vendor/Z"]
    assert result["models"][1]["context_length"] is None
    assert result["models"][1]["supports_tools"] is True
    assert result["models"][2]["supports_tools"] is True
    assert "must-not-leak" not in str(result)
    assert "pricing" not in str(result)
    assert result["truncated"] is False
    assert calls == [(
        "GET", "https://openrouter.ai/api/v1/models?output_modalities=text",
        "Bearer test-catalog-only-key",
    )]


def test_protected_catalog_route_still_requires_owner(monkeypatch):
    mocked(monkeypatch, lambda req: httpx.Response(200, json={
        "data": [{"id": "vendor/model", "name": "One"}]
    }))
    assert client.get("/api/v1/models/catalog").status_code == 401
    response = client.get("/api/v1/models/catalog", headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["models"][0]["id"] == "vendor/model"
    assert "test-catalog-only-key" not in response.text


@pytest.mark.asyncio
@pytest.mark.parametrize("payload,code", [
    ({"data": []}, 200),
    ({"data": [{"id": "bad path?token=secret"}]}, 200),
    ({"data": "invalid"}, 200),
    ({"data": []}, 302),
    ({"data": []}, 401),
])
async def test_invalid_catalog_shape_or_status_is_generic(monkeypatch, payload, code):
    mocked(monkeypatch, lambda req: httpx.Response(code, json=payload))
    with pytest.raises(HTTPException) as error:
        await providers.text_model_catalog()
    assert error.value.status_code == 503
    assert "secret" not in str(error.value.detail)


@pytest.mark.asyncio
async def test_catalog_is_bounded(monkeypatch):
    mocked(monkeypatch, lambda req: httpx.Response(200, json={
        "data": [{"id": f"vendor/{i}", "name": f"Name {i}"} for i in range(260)]
    }))
    result = await providers.text_model_catalog()
    assert len(result["models"]) == 250
    assert result["truncated"] is True


class LargeBody(httpx.AsyncByteStream):
    async def __aiter__(self):
        for _ in range(260):
            yield b"x" * 32768


@pytest.mark.asyncio
async def test_oversized_provider_response_and_missing_key(monkeypatch):
    mocked(monkeypatch, lambda req: httpx.Response(200, stream=LargeBody()))
    with pytest.raises(HTTPException) as error:
        await providers.text_model_catalog()
    assert error.value.status_code == 503
    monkeypatch.delenv("OPENROUTER_API_KEY")
    with pytest.raises(HTTPException) as error:
        await providers.text_model_catalog()
    assert error.value.status_code == 503
