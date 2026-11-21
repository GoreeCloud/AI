"""Owner-approved remote MCP, with bounded inputs, outputs and concurrency.

The FastAPI caller owns approval and authentication; this module enforces the
operator allowlist and connection/resource boundaries. Not a tool sandbox.
"""
import asyncio
import json
import math
import os
import re
from urllib.parse import urlsplit

from fastapi import HTTPException

MCP_MAX_ARGS_BYTES = 256_000
MCP_MAX_NODES = 10_000
MCP_MAX_DEPTH = 16
MCP_MAX_TOOLS = 100
MCP_MAX_CONTENT_ITEMS = 10
MCP_MAX_TEXT_CHARS = 12_000

# Per-process budget, not a global/cross-replica rate limit.
_mcp_slots = asyncio.Semaphore(2)


def configured_endpoint() -> str:
    url = os.getenv("GOREECLOUD_AI_MCP_URL", "").strip()
    if not url:
        raise HTTPException(503, "MCP endpoint is not configured")
    parsed = urlsplit(url)
    try:
        port_valid = parsed.port is None or 1 <= parsed.port <= 65535
    except ValueError:
        port_valid = False
    loopback = parsed.scheme == "http" and parsed.hostname in (
        "127.0.0.1", "localhost", "::1"
    )
    if not (parsed.scheme == "https" or loopback):
        raise HTTPException(422, "MCP endpoint requires HTTPS or loopback HTTP")
    if (not parsed.hostname or not port_valid or parsed.username or parsed.password
            or parsed.query or parsed.fragment
            or (parsed.path and not parsed.path.startswith("/"))):
        raise HTTPException(422, "Invalid operator MCP endpoint")
    return url


def _allowed_tools() -> frozenset[str]:
    raw = os.getenv("GOREECLOUD_AI_MCP_ALLOWED_TOOLS", "")
    names = [name.strip() for name in raw.split(",") if name.strip()]
    if len(names) > 100 or any(not re.fullmatch(r"[A-Za-z0-9_./:-]{1,128}", name)
                               for name in names):
        raise HTTPException(503, "Invalid MCP tool allowlist configuration")
    return frozenset(names)


def validate_arguments(value: dict) -> dict:
    """Reject oversized, deep or non-JSON arguments before external contact."""
    if not isinstance(value, dict):
        raise HTTPException(422, "MCP arguments must be a JSON object")
    nodes = 0

    def walk(item, depth):
        nonlocal nodes
        nodes += 1
        if nodes > MCP_MAX_NODES or depth > MCP_MAX_DEPTH:
            raise HTTPException(422, "MCP arguments are too complex")
        if isinstance(item, dict):
            for key, nested in item.items():
                if not isinstance(key, str):
                    raise HTTPException(422, "Invalid MCP argument name")
                walk(nested, depth + 1)
        elif isinstance(item, list):
            for nested in item:
                walk(nested, depth + 1)
        elif (item is None or isinstance(item, (str, bool, int))
              or (isinstance(item, float) and math.isfinite(item))):
            pass
        else:
            raise HTTPException(422, "MCP arguments must contain finite JSON values")

    walk(value, 0)
    try:
        payload = json.dumps(value, allow_nan=False, ensure_ascii=True, separators=(",", ":"))
    except (TypeError, ValueError, RecursionError) as exc:
        raise HTTPException(422, "Invalid MCP arguments") from exc
    if len(payload.encode("utf-8")) > MCP_MAX_ARGS_BYTES:
        raise HTTPException(413, "MCP arguments exceed supported size")
    return value


def _clean_result(outcome, tool: str) -> dict:
    contents = getattr(outcome, "content", [])
    if not isinstance(contents, list):
        raise HTTPException(502, "MCP tool returned invalid content")
    rendered = []
    non_text_omitted = False
    truncated = len(contents) > MCP_MAX_CONTENT_ITEMS
    for item in contents[:MCP_MAX_CONTENT_ITEMS]:
        value = getattr(item, "text", None)
        if not isinstance(value, str):
            non_text_omitted = True
            rendered.append("[Non-text MCP content omitted; inspect in a trusted tool viewer]")
            continue
        if len(value) > MCP_MAX_TEXT_CHARS:
            truncated = True
        rendered.append(value[:MCP_MAX_TEXT_CHARS])
    return {
        "tool": tool,
        "is_error": getattr(outcome, "isError", False) is True,
        "content": rendered,
        "truncated": truncated,
        "non_text_omitted": non_text_omitted,
    }


async def access_mcp(tool: str | None = None, arguments: dict | None = None) -> dict:
    # Preflight before opening any network connection or loading the MCP SDK.
    allowed = _allowed_tools()
    if tool is not None:
        if tool not in allowed:
            raise HTTPException(403, "MCP tool is not in the operator allowlist")
        validate_arguments(arguments if arguments is not None else {})
    endpoint = configured_endpoint()
    try:
        await asyncio.wait_for(_mcp_slots.acquire(), timeout=0.5)
    except TimeoutError as exc:
        raise HTTPException(429, "MCP concurrency capacity reached") from exc
    try:
        try:
            from mcp import ClientSession
            from mcp.client.streamable_http import streamablehttp_client
        except ImportError as exc:
            raise HTTPException(503, "MCP Python SDK is not installed") from exc

        headers = {}
        if os.getenv("GOREECLOUD_AI_MCP_TOKEN"):
            headers["Authorization"] = "Bearer " + os.environ["GOREECLOUD_AI_MCP_TOKEN"]
        try:
            async with streamablehttp_client(endpoint, headers=headers, timeout=30) as transport:
                read_stream, write_stream, _ = transport
                async with ClientSession(read_stream, write_stream) as session:
                    await asyncio.wait_for(session.initialize(), timeout=10)
                    listed = await asyncio.wait_for(session.list_tools(), timeout=10)
                    remote = getattr(listed, "tools", None)
                    if not isinstance(remote, list):
                        raise HTTPException(502, "MCP discovery returned invalid tools")
                    if tool is None:
                        names = [t.name for t in remote[:MCP_MAX_TOOLS]
                                 if isinstance(getattr(t, "name", None), str)]
                        return {
                            "tools": names,
                            "truncated": len(remote) > MCP_MAX_TOOLS,
                            "execution": "requires per-call user approval",
                        }
                    if tool not in {getattr(t, "name", None) for t in remote}:
                        raise HTTPException(403, "Requested tool is unavailable at MCP endpoint")
                    result = await asyncio.wait_for(
                        session.call_tool(tool, arguments=arguments or {}), timeout=30
                    )
                    return _clean_result(result, tool)
        except TimeoutError as exc:
            raise HTTPException(504, "MCP endpoint timed out") from exc
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(502, "MCP endpoint unavailable or incompatible") from exc
    finally:
        _mcp_slots.release()
