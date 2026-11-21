"""Bounded server-SSE frame decoder for native Qt Quick streaming.

Pure Python and independent of PySide6 so malformed wire framing can be
tested without a GUI. Input is *untrusted* API text, not an instruction.
"""
import json


class StreamFrameError(ValueError):
    pass


class StreamFrames:
    def __init__(self):
        self._pending = bytearray()
        self._total_bytes = 0
        self._total_text = 0
        self._frames = 0
        self.done = False

    def feed(self, chunk: bytes) -> list[dict]:
        if self.done:
            return []
        if not isinstance(chunk, bytes):
            raise StreamFrameError("Invalid stream data")
        self._total_bytes += len(chunk)
        if self._total_bytes > 500_000:
            raise StreamFrameError("Chat stream exceeded maximum size")
        self._pending.extend(chunk)
        if len(self._pending) > 100_000 and b"\n" not in self._pending:
            raise StreamFrameError("SSE event line exceeded maximum size")
        events = []
        while b"\n" in self._pending:
            raw, _, remainder = self._pending.partition(b"\n")
            self._pending = bytearray(remainder)
            if len(raw) > 100_000:
                raise StreamFrameError("SSE event line exceeded maximum size")
            if raw.endswith(b"\r"):
                raw = raw[:-1]
            if not raw or raw.startswith(b":") or not raw.startswith(b"data: "):
                continue
            self._frames += 1
            if self._frames > 10_000:
                raise StreamFrameError("Too many streaming events")
            data = raw[6:]
            if data == b"[DONE]":
                self.done = True
                break
            try:
                event = json.loads(data.decode("utf-8", errors="strict"))
            except (UnicodeError, ValueError) as exc:
                raise StreamFrameError("Invalid streaming JSON") from exc
            if not isinstance(event, dict):
                raise StreamFrameError("Invalid streaming event")
            kind = event.get("type")
            if kind == "delta":
                value = event.get("content")
                if not isinstance(value, str):
                    raise StreamFrameError("Invalid streaming text")
                self._total_text += len(value)
                if self._total_text > 120_000:
                    raise StreamFrameError("Streaming text exceeded maximum size")
                events.append({"type": "delta", "content": value})
            elif kind == "done":
                self.done = True
                provider = event.get("provider")
                model = event.get("model")
                events.append({
                    "type": "done",
                    "provider": provider if isinstance(provider, str) else "selected",
                    "model": model[:128] if isinstance(model, str) else "",
                })
                break
            elif kind == "error":
                raise StreamFrameError("Inference provider reported an error")
            else:
                raise StreamFrameError("Unsupported streaming event")
        if len(self._pending) > 100_000:
            raise StreamFrameError("SSE event line exceeded maximum size")
        return events
