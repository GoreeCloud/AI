"""Validate actual OpenRouter SSE and Ollama NDJSON parsers without network calls."""
import asyncio
import json

import httpx
import pytest

from app import providers


class StreamResponse:
    def __init__(self, lines, status_code=200):
        self.lines = lines
        self.status_code = status_code

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def aiter_text(self):
        for line in self.lines:
            yield line + "\n"


class StubClient:
    def __init__(self, lines, status_code=200):
        self.lines, self.status_code = lines, status_code

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    def stream(self, method, url, json, headers):
        assert method == "POST"
        assert json["stream"] is True
        assert url.startswith(("https://openrouter.ai/api/v1/", "http://127.0.0.1:11434/"))
        return StreamResponse(self.lines, self.status_code)


class ChunkedStream(httpx.AsyncByteStream):
    def __init__(self, chunks):
        self.chunks = chunks
        self.reads = 0
        self.closed = False

    async def __aiter__(self):
        for chunk in self.chunks:
            self.reads += 1
            yield chunk

    async def aclose(self):
        self.closed = True


def patch_byte_stream(monkeypatch, stream):
    client = httpx.AsyncClient
    transport = httpx.MockTransport(lambda request: httpx.Response(200, stream=stream))
    monkeypatch.setattr(providers.httpx, "AsyncClient", lambda **kwargs: client(transport=transport, **kwargs))


@pytest.mark.asyncio
async def test_openrouter_sse(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-key")
    lines = [
        ': keepalive',
        'data: {"choices":[{"delta":{"role":"assistant","content":null}}]}',
        'data: ' + json.dumps({"model": "tested", "choices": [{"delta": {"content": "Hey"}}]}),
        'data: ' + json.dumps({"choices": [{"delta": {"content": " there"}}]}),
        'data: {"choices":[],"usage":{"completion_tokens":2}}',
        'data:[DONE]'
    ]
    monkeypatch.setattr(providers.httpx, "AsyncClient",
                        lambda **kwargs: StubClient(lines))
    events = [event async for event in providers.stream_chat(
        [{"role": "user", "content": "hello"}], "openrouter/auto", "openrouter")]
    assert events == [
        {"type": "delta", "content": "Hey"},
        {"type": "delta", "content": " there"},
        {"type": "done", "provider": "openrouter", "model": "tested"},
    ]


@pytest.mark.asyncio
async def test_ollama_ndjson(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "mock-local")
    lines = [
        json.dumps({"model": "mock-local", "message": {"content": "Local"}, "done": False}),
        json.dumps({"model": "mock-local", "message": {"content": " OK"}, "done": True}),
    ]
    monkeypatch.setattr(providers.httpx, "AsyncClient",
                        lambda **kwargs: StubClient(lines))
    events = [event async for event in providers.stream_chat(
        [{"role": "user", "content": "hello"}], "openrouter/auto", "ollama")]
    assert events[-1] == {"type": "done", "provider": "ollama", "model": "mock-local"}
    assert "".join(e["content"] for e in events if e["type"] == "delta") == "Local OK"


@pytest.mark.asyncio
async def test_stream_provider_status_redacted(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-key")
    monkeypatch.setattr(providers.httpx, "AsyncClient",
                        lambda **kwargs: StubClient([], 503))
    events = [event async for event in providers.stream_chat(
        [{"role": "user", "content": "secret"}], "openrouter/auto", "openrouter")]
    assert events == [{"type": "error", "message": "Inference provider returned an error"}]
    assert "secret" not in json.dumps(events)


@pytest.mark.asyncio
@pytest.mark.parametrize(("provider", "partial_line"), [
    ("openrouter", 'data: {"choices":[{"delta":{"content":"partial"}}]}'),
    ("ollama", '{"message":{"content":"partial"},"done":false}'),
])
@pytest.mark.parametrize("expose_terminal", [False, True])
async def test_eof_without_provider_terminal_reports_error(
    monkeypatch, provider, partial_line, expose_terminal,
):
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-key")
    monkeypatch.setenv("OLLAMA_MODEL", "mock-local")
    monkeypatch.setattr(providers.httpx, "AsyncClient",
                        lambda **kwargs: StubClient([partial_line]))
    events = [event async for event in providers.stream_chat(
        [{"role": "user", "content": "hello"}], "local", provider,
        expose_terminal=expose_terminal,
    )]
    assert events == [
        {"type": "delta", "content": "partial"},
        {"type": "error", "message": "Model stream stopped before completion"},
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(("provider", "invalid"), [
    ("openrouter", 'truncated JSON'),
    ("openrouter", '[]'),
    ("openrouter", '{"choices":{"unexpected":"private provider data"}}'),
    ("openrouter", '{"choices":["private provider data"]}'),
    ("openrouter", '{"choices":[{"delta":"private provider data"}]}'),
    ("openrouter", '{"choices":[{"delta":{"content":["private provider data"]}}]}'),
    ("ollama", 'truncated JSON'),
    ("ollama", 'true'),
    ("ollama", '{"message":"private provider data","done":true}'),
    ("ollama", '{"message":{"content":["private provider data"]},"done":true}'),
    ("ollama", '{"done":"true"}'),
])
async def test_malformed_provider_data_ends_stream_with_redacted_error(monkeypatch, provider, invalid):
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-key")
    monkeypatch.setenv("OLLAMA_MODEL", "mock-local")
    if provider == "openrouter":
        lines = ['data: {"choices":[{"delta":{"content":"partial"}}]}',
                 'data: ' + invalid, 'data: [DONE]']
    else:
        lines = ['{"message":{"content":"partial"},"done":false}', invalid, '{"done":true}']
    monkeypatch.setattr(providers.httpx, "AsyncClient", lambda **kwargs: StubClient(lines))
    events = [event async for event in providers.stream_chat(
        [{"role": "user", "content": "hello"}], "local", provider, expose_terminal=True,
    )]
    assert events == [
        {"type": "delta", "content": "partial"},
        {"type": "error", "message": "Inference provider returned invalid stream data"},
    ]


@pytest.mark.asyncio
async def test_upstream_line_limit_closes_before_reading_trailing_newline(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "mock-local")
    stream = ChunkedStream([
        b'{"message":{"content":"first"},"done":false}\r\n',
        b"x" * 40_000, b"x" * 40_000, b"x" * 20_001, b"\n",
    ])
    patch_byte_stream(monkeypatch, stream)
    events = [event async for event in providers.stream_chat(
        [{"role": "user", "content": "hello"}], "local", "ollama",
    )]
    assert events == [
        {"type": "delta", "content": "first"},
        {"type": "error", "message": "Upstream response exceeded limit"},
    ]
    assert stream.reads == 4
    assert stream.closed


@pytest.mark.asyncio
@pytest.mark.parametrize("width", [1, 4, 1024])
async def test_bounded_lines_match_httpx_delimiters_and_eof(width):
    text = "\r\nfirst\rsecond\né🙂\v\f\x1c\x1d\x1e\x85\u2028\u2029third\r\r\nlast\r"
    encoded = text.encode("utf-8")
    chunks = [encoded[i:i + width] for i in range(0, len(encoded), width)]
    response = httpx.Response(200, stream=ChunkedStream(chunks))
    baseline = httpx.Response(200, stream=ChunkedStream(chunks))
    expected = [line async for line in baseline.aiter_lines()]
    assert [line async for line in providers._bounded_stream_lines(response)] == expected == text.splitlines()


@pytest.mark.asyncio
async def test_multibyte_frame_at_character_limit_with_provider_metadata(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-key")
    prefix = 'data: {"choices":[{"delta":{"content":"'
    suffix = '"}}]}'
    content = "é" * (100_000 - len(prefix) - len(suffix) - 1) + "🙂"
    frame = (prefix + content + suffix).encode("utf-8")
    first_split = len(prefix) + 1  # In the first two-byte code point.
    last_split = len(frame) - len(suffix) - 2  # In the last four-byte code point.
    assert len(frame) > 100_000
    stream = ChunkedStream([
        b": keepalive\r",
        b'\ndata: {"choices":[{"delta":{"role":"assistant","content":null}}]}\r\n' + frame[:first_split],
        frame[first_split:last_split],
        frame[last_split:] + b'\r\ndata: {"choices":[],"usage":{"prompt_tokens_details":{"cached_tokens":2}}}\r',
        b"\ndata: [DONE]",
        b"\r\n",
        b"This chunk must not be consumed",
    ])
    patch_byte_stream(monkeypatch, stream)
    events = [event async for event in providers.stream_chat(
        [{"role": "user", "content": "hello"}], "openrouter/auto", "openrouter", provider_prompt_cache=True,
    )]
    assert events == [
        {"type": "delta", "content": content},
        {"type": "done", "provider": "openrouter", "model": "openrouter/auto",
         "provider_prompt_cache": {"requested": True, "reported_token_details": {"cached_tokens": 2}}},
    ]
    assert stream.reads == 6
    assert stream.closed


@pytest.mark.asyncio
async def test_cancel_closes_upstream_while_reading_fragmented_line(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "mock-local")
    waiting = asyncio.Event()

    class PausedStream(ChunkedStream):
        async def __aiter__(self):
            yield b'{"message":{"content":"first"},"done":false}\n{"message":'
            waiting.set()
            await asyncio.Future()

    stream = PausedStream([])
    patch_byte_stream(monkeypatch, stream)

    async def consume():
        return [event async for event in providers.stream_chat(
            [{"role": "user", "content": "hello"}], "local", "ollama",
        )]

    consumer = asyncio.create_task(consume())
    try:
        await asyncio.wait_for(waiting.wait(), timeout=5)
    finally:
        consumer.cancel()
        with pytest.raises(asyncio.CancelledError):
            await consumer
    assert stream.closed
