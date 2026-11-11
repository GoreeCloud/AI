"""Wire-format tests using httpx MockTransport. No local model or network access."""
import asyncio
import json
import httpx
import pytest
from goreecloud_ai.ollama import OllamaClient, OllamaError


def fake_http(monkeypatch, handler):
    original = httpx.AsyncClient
    transport = httpx.MockTransport(handler)

    def client(*args, **kwargs):
        kwargs["transport"] = transport
        return original(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", client)


def test_model_discovery_filters_malformed_tags(monkeypatch):
    def handler(request):
        assert request.method == "GET" and request.url.path == "/api/tags"
        return httpx.Response(200, json={"models":[
            {"name":"gemma3:4b"}, {"name":"qwen3:8b"}, {}, {"name":42}
        ]})

    fake_http(monkeypatch, handler)
    assert asyncio.run(OllamaClient("http://ollama.local").models()) == ["gemma3:4b", "qwen3:8b"]


def test_nonstreaming_chat_contract_and_malformed_reply(monkeypatch):
    def handler(request):
        assert request.url.path == "/api/chat"
        data = json.loads(request.content)
        assert data["stream"] is False
        assert data["model"] == "qwen3:8b"
        assert data["messages"] == [{"role":"user","content":"hello"}]
        return httpx.Response(200, json={"message":{"content":"hi"}})

    fake_http(monkeypatch, handler)
    client = OllamaClient("http://ollama.local")
    assert asyncio.run(client.chat("qwen3:8b", [{"role":"user","content":"hello"}])) == "hi"


def test_embedding_batch_contract_and_nontruncation(monkeypatch):
    def handler(request):
        assert request.url.path == "/api/embed"
        data = json.loads(request.content)
        assert data == {"model":"embeddinggemma","input":["a","b"],"truncate":False}
        return httpx.Response(200, json={"embeddings":[[1.0,0.0],[0.0,1.0]]})

    fake_http(monkeypatch, handler)
    assert asyncio.run(OllamaClient("http://ollama.local").embed("embeddinggemma", ["a","b"])) == [[1.0,0.0],[0.0,1.0]]


def test_embedding_batch_shape_rejected(monkeypatch):
    fake_http(monkeypatch, lambda request: httpx.Response(200,json={"embeddings":[[1.0]]}))
    with pytest.raises(OllamaError):
        asyncio.run(OllamaClient("http://ollama.local").embed("embeddinggemma", ["a","b"]))


def test_streaming_ndjson_protocol(monkeypatch):
    def handler(request):
        assert json.loads(request.content)["stream"] is True
        body = (
            '{"message":{"content":"hello"},"done":false}\n'
            '{"message":{"content":" world"},"done":false}\n'
            '{"done":true}\n'
        )
        return httpx.Response(200, content=body.encode(), headers={"content-type":"application/x-ndjson"})

    fake_http(monkeypatch, handler)

    async def read():
        return [part async for part in OllamaClient("http://ollama.local").stream_chat("gemma3:4b", [{"role":"user","content":"hi"}])]

    assert asyncio.run(read()) == ["hello", " world"]


def test_streaming_missing_done_is_error(monkeypatch):
    fake_http(monkeypatch, lambda request: httpx.Response(
        200, content=b'{"message":{"content":"partial"},"done":false}\n'
    ))

    async def read():
        return [part async for part in OllamaClient("http://ollama.local").stream_chat("gemma3:4b", [{"role":"user","content":"hi"}])]

    with pytest.raises(OllamaError, match="before completion"):
        asyncio.run(read())


def test_chat_upstream_http_error_is_normalized(monkeypatch):
    fake_http(monkeypatch, lambda request: httpx.Response(503, json={"error":"offline"}))
    with pytest.raises(OllamaError, match="chat request failed"):
        asyncio.run(OllamaClient("http://ollama.local").chat("gemma3:4b", [{"role":"user","content":"hi"}]))
