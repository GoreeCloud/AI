"""Opt-in remote MCP client. A tool call requires separate explicit approval."""
import os
from urllib.parse import urlparse

from fastapi import HTTPException


def configured_endpoint() -> str:
    url = os.getenv("GOREeCLOUD_AI_MCP_URL", "").strip()
    if not url:
        raise HTTPException(503, "MCP is not configured")
    parsed = urlparse(url)
    if parsed.scheme != "https" and not (
        parsed.scheme == "http" and parsed.hostname in ("127.0.0.1", "localhost")
    ):
        raise HTTPException(422, "MCP endpoint must use HTTPS or loopback HTTP")
    if parsed.username or parsed.password or not parsed.hostname or parsed.fragment:
        raise HTTPException(422, "Invalid MCP endpoint")
    return url


async def access_mcp(tool: str | None = None, arguments: dict | None = None) -> dict:
    try:
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client
    except ImportError as exc:
        raise HTTPException(503, "MCP Python SDK is not installed") from exc

    headers = {}
    if os.getenv("GOREeCLOUD_AI_MCP_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GOREeCLOUD_AI_MCP_TOKEN"]
    try:
        async with streamablehttp_client(configured_endpoint(), headers=headers, timeout=30) as transport:
            read_stream, write_stream, _ = transport
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                listed = await session.list_tools()
                names = [x.name for x in listed.tools]
                if tool is None:
                    return {"tools": names, "execution": "requires per-call user approval"}
                allowed = [x.strip() for x in os.getenv("GOREeCLOUD_AI_MCP_ALLOWED_TOOLS", "").split(",") if x.strip()]
                if tool not in names or tool not in allowed:
                    raise HTTPException(403, "MCP tool is not in the operator allowlist")
                outcome = await session.call_tool(tool, arguments=arguments or {})
                return {"tool": tool, "is_error": bool(outcome.isError),
                        "content": [str(c)[:12000] for c in outcome.content[:10]]}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(502, "MCP endpoint unavailable or incompatible") from exc
