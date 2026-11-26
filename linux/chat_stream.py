"""Native Qt Network SSE bridge with explicit cancellation and no redirect following.

Developer preview: operator-supplied API endpoint; full Identity and secure
production ingress qualification remain outside this client.
"""
import json
from urllib.parse import urlsplit

from PySide6.QtCore import QObject, QUrl, Signal, Slot
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkProxy, QNetworkReply, QNetworkRequest
from stream_frames import StreamFrameError, StreamFrames


def checked_endpoint(address: str) -> str:
    if not isinstance(address, str) or len(address) > 512:
        raise ValueError("Unsupported API address")
    source = address.strip().rstrip("/")
    parsed = urlsplit(source)
    try:
        valid_port = parsed.port is None or 1 <= parsed.port <= 65535
    except ValueError:
        valid_port = False
    loopback = parsed.scheme == "http" and parsed.hostname in (
        "localhost", "127.0.0.1", "::1"
    )
    if not (
        parsed.scheme == "https" or loopback
    ) or not parsed.hostname or not valid_port or parsed.username or parsed.password or (
        parsed.query or parsed.fragment
    ):
        raise ValueError("Use HTTPS or explicitly configured loopback HTTP")
    return source


class ChatStreamBridge(QObject):
    delta = Signal(str)
    completed = Signal(str, str)
    failed = Signal(str)
    stopped = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager = QNetworkAccessManager(self)
        # Avoid forwarding owner credentials through implicit desktop proxy settings.
        self.manager.setProxy(QNetworkProxy(QNetworkProxy.ProxyType.NoProxy))
        self._reply: QNetworkReply | None = None
        self._frames = StreamFrames()

    def _close(self) -> None:
        reply = self._reply
        self._reply = None
        if reply is not None:
            reply.abort()
            reply.deleteLater()

    def _fail(self, message: str) -> None:
        if self._reply is not None:
            self._close()
            self.failed.emit(message)

    @Slot()
    def cancel(self) -> None:
        if self._reply is not None:
            self._close()
            self.stopped.emit()

    @Slot(str, str, str)
    def start(self, address: str, owner_token: str, json_body: str) -> None:
        if self._reply is not None:
            self.failed.emit("Another chat stream is still active")
            return
        try:
            base = checked_endpoint(address)
            if (not isinstance(owner_token, str) or not 1 <= len(owner_token) <= 4096
                    or not owner_token.isascii() or any(ch in owner_token for ch in "\r\n")):
                raise ValueError("Enter a valid API owner token")
            body = json_body.encode("utf-8")
            if not 0 < len(body) <= 256_000:
                raise ValueError("Chat request exceeds supported size")
            parsed = json.loads(json_body)
            if not isinstance(parsed, dict):
                raise ValueError("Invalid chat request")
            request = QNetworkRequest(QUrl(base + "/api/v1/chat/stream"))
            request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
            request.setRawHeader(b"Accept", b"text/event-stream")
            request.setRawHeader(b"Authorization", b"Bearer " + owner_token.encode("ascii"))
            request.setAttribute(
                QNetworkRequest.Attribute.RedirectPolicyAttribute,
                QNetworkRequest.RedirectPolicy.ManualRedirectPolicy,
            )
            request.setTransferTimeout(90_000)
            self._frames = StreamFrames()
            reply = self.manager.post(request, body)
            self._reply = reply
            reply.setReadBufferSize(65_536)
            reply.readyRead.connect(lambda r=reply: self._on_ready(r))
            reply.finished.connect(lambda r=reply: self._on_finished(r))
        except (ValueError, UnicodeError, TypeError):
            # Do not expose endpoint URLs, private JSON, credentials or exception text.
            self.failed.emit("Invalid chat stream configuration or input")

    def _on_ready(self, reply: QNetworkReply) -> None:
        if self._reply is not reply:
            return
        try:
            code = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
            if code is not None and int(code) != 200:
                self._fail("Chat stream request was rejected by the API")
                return
            data = bytes(reply.readAll())
            events = self._frames.feed(data)
            for event in events:
                if event["type"] == "delta":
                    self.delta.emit(event["content"])
                elif event["type"] == "done":
                    self._close()
                    self.completed.emit(event["provider"], event["model"])
                    return
                elif event["type"] == "error":
                    self._fail("Inference provider reported an error")
                    return
            if reply.attribute(QNetworkRequest.Attribute.RedirectionTargetAttribute):
                self._fail("Chat stream redirect refused")
        except (StreamFrameError, ValueError, TypeError, UnicodeError):
            self._fail("Chat stream response was invalid or exceeded its bounds")

    def _on_finished(self, reply: QNetworkReply) -> None:
        if self._reply is not reply:
            return
        self._on_ready(reply)
        if self._reply is reply:
            self._fail("Chat stream ended before a validated completion")
