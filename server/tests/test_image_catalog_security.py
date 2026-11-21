"""No paid calls: mock upstream discovery, image shape and bounded responses."""
import base64

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import providers
from app.main import app

OWNER = {"Authorization": "Bearer test-owner-token"}


def mock_transport(monkeypatch, handler):
    original = httpx.AsyncClient
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(providers.httpx, "AsyncClient",
                        lambda **kwargs: original(transport=transport, **kwargs))


@pytest.mark.asyncio
async def test_image_catalog_is_bounded_and_sanitized(monkeypatch):
    seen = []
    def handler(request):
        seen.append((request.method, str(request.url), request.headers.get("authorization")))
        assert request.method == "GET"
        return httpx.Response(200, json={"data": [
            {"id": "vendor/image-one", "name": "<b>Discovery</b>",
             "supported_parameters": {"input_references": {"type": "range", "max": 2}},
             "supports_streaming": False, "operator_secret": "never-expose"},
            {"id": "vendor/image-two", "name": "Image Two",
             "supported_parameters": {}, "supports_streaming": True},
            {"id": "bad slug with spaces", "name": "Exclude"},
        ]})
    mock_transport(monkeypatch, handler)
    result = await providers.image_catalog()
    assert result["source"] == "openrouter-image-api"
    assert len(result["models"]) == 2
    assert result["models"][0]["supports_reference"] is True
    assert result["models"][1]["supports_streaming"] is True
    assert "operator_secret" not in str(result)
    assert seen == [("GET", "https://openrouter.ai/api/v1/images/models", None)]


@pytest.mark.asyncio
@pytest.mark.parametrize("data,status", [
    ({"data": []}, 200),
    ({"data": "invalid"}, 200),
    ({"data": [{"id": "wrong name"}]}, 200),
    ({"data": []}, 403),
])
async def test_catalog_invalid_upstream_fails_closed(monkeypatch, data, status):
    mock_transport(monkeypatch, lambda request: httpx.Response(status, json=data))
    with pytest.raises(HTTPException) as error:
        await providers.image_catalog()
    assert error.value.status_code == 503


@pytest.mark.asyncio
async def test_image_response_matches_openrouter_dedicated_api(monkeypatch):
    binary = b"\x89PNG\r\n\x1a\n" + b"synthetic-image-data"
    reference = "data:image/png;base64," + base64.b64encode(binary).decode()
    async def upstream(url, body, key=None, timeout=90.0):
        assert url == "https://openrouter.ai/api/v1/images"
        assert body == {"model": "vendor/image-one", "prompt": "new picture",
                        "input_references": [{"type": "image_url",
                                              "image_url": {"url": reference}}]}
        assert key == "test-only-key"
        assert timeout == 120
        return {"data": [{"b64_json": base64.b64encode(binary).decode(),
                          "media_type": "image/png"}], "usage": {"cost": 0.02}}
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-only-key")
    monkeypatch.setattr(providers, "_post", upstream)
    output = await providers.image_request("new picture", "vendor/image-one", reference)
    assert output["media_type"] == "image/png"
    assert output["cost"] == 0.02
    assert output["image"].startswith("data:image/png;base64,")


@pytest.mark.asyncio
@pytest.mark.parametrize("image", [
    {"b64_json": "not valid b64!", "media_type": "image/png"},
    {"b64_json": base64.b64encode(b"\x89PNG\r\n\x1a\n").decode(),
     "media_type": "image/jpeg"},
    {"b64_json": "AAA", "media_type": "image/png"},
    {"b64_json": "", "media_type": "image/png"},
])
async def test_invalid_generated_image_rejected(monkeypatch, image):
    async def fake_post(*args, **kwargs):
        return {"data": [image], "usage": {}}
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(providers, "_post", fake_post)
    with pytest.raises(HTTPException) as e:
        await providers.image_request("a picture", "vendor/model", None)
    assert e.value.status_code == 502


class HugeStream(httpx.AsyncByteStream):
    async def __aiter__(self):
        for _ in range(390):
            yield b"x" * 65536


@pytest.mark.asyncio
async def test_upstream_memory_limit_applied_during_streaming(monkeypatch):
    def handler(request):
        return httpx.Response(200, stream=HugeStream())
    mock_transport(monkeypatch, handler)
    with pytest.raises(providers.UpstreamFailure) as error:
        await providers._post("https://openrouter.ai/api/v1/images",
                              {"prompt": "synthetic"}, "fake")
    assert error.value.status == 413


@pytest.mark.asyncio
async def test_invalid_json_from_provider_is_safe(monkeypatch):
    mock_transport(monkeypatch, lambda req: httpx.Response(200, content=b"not json"))
    with pytest.raises(providers.UpstreamFailure):
        await providers._post("https://openrouter.ai/api/v1/images", {})


def test_catalog_api_requires_owner(monkeypatch):
    client = TestClient(app)
    assert client.get("/api/v1/images/models").status_code == 401
