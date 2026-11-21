"""Manual MCP trust-boundary regression tests using synthetic sessions only."""
import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import mcp_tools
from app.main import app


@pytest.fixture(autouse=True)
def safe_endpoint(monkeypatch):
    monkeypatch.setenv("GOREECLOUD_AI_AUTH_MODE", "owner")
    monkeypatch.setenv("GOREECLOUD_AI_TOKEN", "test-owner-token")
    monkeypatch.setenv("GOREECLOUD_AI_MCP_URL", "https://mcp.example.test/approved")
    monkeypatch.setenv("GOREECLOUD_AI_MCP_ALLOWED_TOOLS", "read_document,secure_tool")
    monkeypatch.delenv("GOREECLOUD_AI_MCP_TOKEN", raising=False)
    monkeypatch.setattr(mcp_tools, "_mcp_slots", asyncio.Semaphore(2))


@pytest.fixture
def remote_session(monkeypatch):
    import mcp
    from mcp.client import streamable_http

    seen = {"transport": 0, "tools": 0, "calls": []}

    @asynccontextmanager
    async def transport(url, headers, timeout):
        seen["transport"] += 1
        assert url == "https://mcp.example.test/approved"
        assert headers == {}
        assert timeout == 30
        yield ("read", "write", None)

    class Session:
        def __init__(self, read, write):
            assert read == "read" and write == "write"

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return False

        async def initialize(self):
            return None

        async def list_tools(self):
            seen["tools"] += 1
            return SimpleNamespace(tools=[
                SimpleNamespace(name="read_document"),
                SimpleNamespace(name="secure_tool"),
                SimpleNamespace(name="unapproved_extra"),
            ])

        async def call_tool(self, tool, arguments):
            seen["calls"].append((tool, arguments))
            return SimpleNamespace(isError=False, content=[
                SimpleNamespace(text="Synthetic safe document"),
                SimpleNamespace(type="image", data="not-a-user-secret"),
            ])

    monkeypatch.setattr(streamable_http, "streamablehttp_client", transport)
    monkeypatch.setattr(mcp, "ClientSession", Session)
    return seen


def test_validate_rejects_malformed_oversize_deep_and_non_finite_args():
    assert mcp_tools.validate_arguments({"query": "hello", "filters": [True, 5, None]})
    for value in ({"data": "x" * 256_000}, {"nested": [[[]] for _ in range(10001)]},
                  {"bad": float("nan")}, {"bad": float("inf")},
                  {"unsafe": set([2])}, {1: "non-string-key"}):
        with pytest.raises(HTTPException) as exc:
            mcp_tools.validate_arguments(value)
        assert exc.value.status_code in (413, 422)
    deep = {}
    current = deep
    for _ in range(18):
        current["next"] = {}
        current = current["next"]
    with pytest.raises(HTTPException) as exc:
        mcp_tools.validate_arguments(deep)
    assert exc.value.status_code == 422


@pytest.mark.parametrize("url", [
    "http://example.test/mcp", "http://localhost:99999/mcp",
    "https://user:password@example.test/mcp",
    "https://example.test/mcp?private=1",
    "https://example.test/mcp#fragment",
    "file:///tmp/mcp", "http://127.0.0.1@evil.test:8999/mcp",
])
def test_endpoint_rejects_unsafe_origins(monkeypatch, url):
    monkeypatch.setenv("GOREECLOUD_AI_MCP_URL", url)
    with pytest.raises(HTTPException) as exc:
        mcp_tools.configured_endpoint()
    assert exc.value.status_code == 422


def test_loopback_endpoints_remain_supported(monkeypatch):
    for url in ("http://127.0.0.1:5000/mcp", "http://localhost:5001/mcp",
                "http://[::1]:5002/mcp", "https://mcp.example.test"):
        monkeypatch.setenv("GOREECLOUD_AI_MCP_URL", url)
        assert mcp_tools.configured_endpoint() == url


@pytest.mark.asyncio
async def test_allowlist_denied_before_contact(remote_session):
    with pytest.raises(HTTPException) as exc:
        await mcp_tools.access_mcp("unapproved_extra", {"x": "untrusted"})
    assert exc.value.status_code == 403
    assert remote_session["transport"] == 0


@pytest.mark.asyncio
async def test_discovery_bounded_and_successful_tool_call(remote_session):
    listing = await mcp_tools.access_mcp()
    assert listing["tools"] == ["read_document", "secure_tool", "unapproved_extra"]
    assert listing["truncated"] is False
    assert listing["execution"] == "requires per-call user approval"
    result = await mcp_tools.access_mcp("read_document", {"id": "synthetic"})
    assert result == {
        "tool": "read_document", "is_error": False,
        "content": ["Synthetic safe document",
                    "[Non-text MCP content omitted; inspect in a trusted tool viewer]"],
        "truncated": False, "non_text_omitted": True,
    }
    assert remote_session["calls"] == [("read_document", {"id": "synthetic"})]


def test_clean_result_truncates_long_text_and_media():
    huge = SimpleNamespace(isError=True, content=[
        SimpleNamespace(text="x" * 20_000)] * 12)
    data = mcp_tools._clean_result(huge, "secure_tool")
    assert data["is_error"] is True
    assert data["truncated"] is True
    assert len(data["content"]) == 10
    assert len(data["content"][0]) == 12_000


@pytest.mark.asyncio
async def test_capacity_fails_without_remote_contact(monkeypatch, remote_session):
    monkeypatch.setattr(mcp_tools, "_mcp_slots", asyncio.Semaphore(0))
    with pytest.raises(HTTPException) as exc:
        await mcp_tools.access_mcp("read_document", {})
    assert exc.value.status_code == 429
    assert remote_session["transport"] == 0


@pytest.mark.asyncio
async def test_tool_timeout_scrubs_provider_details(monkeypatch, remote_session):
    import mcp

    class TimeoutSession(mcp.ClientSession):
        async def call_tool(self, tool, arguments):
            raise TimeoutError("hidden-private-token-url")
    monkeypatch.setattr(mcp, "ClientSession", TimeoutSession)
    with pytest.raises(HTTPException) as exc:
        await mcp_tools.access_mcp("read_document", {"id": "synthetic"})
    assert exc.value.status_code == 504
    assert "hidden-private" not in str(exc.value.detail)
    assert mcp_tools._mcp_slots._value == 2


def test_api_rejects_unapproved_or_large_tool_payload_without_contact(remote_session):
    client = TestClient(app)
    headers = {"Authorization": "Bearer test-owner-token"}
    denied = client.post("/api/v1/mcp/call", headers=headers, json={
        "name": "read_document", "arguments": {}, "approved": False})
    assert denied.status_code == 403
    too_large = client.post("/api/v1/mcp/call", headers=headers, json={
        "name": "read_document", "arguments": {"data": "x" * 256_000},
        "approved": True})
    assert too_large.status_code == 413
    assert remote_session["transport"] == 0


def test_invalid_allowlist_refuses_configuration_before_contact(monkeypatch, remote_session):
    monkeypatch.setenv("GOREECLOUD_AI_MCP_ALLOWED_TOOLS", "valid,*")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(mcp_tools.access_mcp("valid", {}))
    assert exc.value.status_code == 503
    assert remote_session["transport"] == 0
