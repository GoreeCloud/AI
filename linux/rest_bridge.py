"""Owner-authenticated Qt Network REST bridge with explicit redirect refusal.

All nonstreaming Linux API requests use this instead of QML XMLHttpRequest,
which may follow redirects with bearer credentials. No secrets are logged.
"""
import json
import re

from chat_stream import checked_endpoint
from PySide6.QtCore import QObject, QUrl, Signal, Slot
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkProxy, QNetworkReply, QNetworkRequest

_ROUTE = re.compile(r"/api/v1/[A-Za-z0-9_./-]{1,240}\Z")
_MAX_REQUEST = 256_000
_MAX_RESPONSE = 16_000_000


def checked_route(path: str) -> str:
    if (not isinstance(path, str) or len(path) > 256
            or not _ROUTE.fullmatch(path) or "//" in path or ".." in path.split("/")):
        raise ValueError("Unsupported API route")
    return path


class SafeRestBridge(QObject):
    succeeded = Signal(int, str)
    failed = Signal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager = QNetworkAccessManager(self)
        self.manager.setProxy(QNetworkProxy(QNetworkProxy.ProxyType.NoProxy))
        self._reply: QNetworkReply | None = None
        self._request_id: int | None = None
        self._received = bytearray()

    @Slot(int, str, str, str, str, str)
    def start(self, request_id: int, endpoint: str, owner_token: str,
              method: str, path: str, json_body: str) -> None:
        if self._reply is not None:
            self.failed.emit(request_id, "Another API request is active")
            return
        try:
            if not 1 <= request_id <= 2_000_000_000:
                raise ValueError("Invalid request identity")
            base = checked_endpoint(endpoint)
            checked_route(path)
            if (not isinstance(owner_token, str) or not 1 <= len(owner_token) <= 4096
                    or not owner_token.isascii() or "\r" in owner_token
                    or "\n" in owner_token):
                raise ValueError("Invalid owner credential")
            if method not in ("GET", "POST", "PUT", "DELETE"):
                raise ValueError("Unsupported API method")
            if json_body:
                if method == "GET":
                    raise ValueError("GET must not include a body")
                payload = json_body.encode("utf-8")
                if len(payload) > _MAX_REQUEST or not isinstance(json.loads(json_body), dict):
                    raise ValueError("Invalid or oversized API body")
            else:
                payload = b""
                if method in ("POST", "PUT"):
                    raise ValueError("Write requires JSON object")
            request = QNetworkRequest(QUrl(base + path))
            request.setAttribute(QNetworkRequest.Attribute.RedirectPolicyAttribute,
                                 QNetworkRequest.RedirectPolicy.ManualRedirectPolicy)
            request.setRawHeader(b"Authorization", b"Bearer " + owner_token.encode("ascii"))
            request.setRawHeader(b"Accept", b"application/json")
            if payload:
                request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader,
                                  "application/json")
            request.setTransferTimeout(90_000)
            self._received = bytearray()
            if method == "GET":
                reply = self.manager.get(request)
            elif method == "POST":
                reply = self.manager.post(request, payload)
            elif method == "PUT":
                reply = self.manager.put(request, payload)
            else:
                reply = self.manager.deleteResource(request)
            self._request_id = request_id
            self._reply = reply
            reply.setReadBufferSize(65_536)
            reply.readyRead.connect(lambda r=reply: self._consume(r))
            reply.finished.connect(lambda r=reply: self._complete(r))
        except (TypeError, ValueError, UnicodeError, RecursionError):
            self.failed.emit(request_id, "Invalid API request configuration")

    def _release(self, reply: QNetworkReply) -> int | None:
        if self._reply is not reply:
            return None
        request_id = self._request_id
        self._reply = None
        self._request_id = None
        self._received = bytearray()
        reply.deleteLater()
        return request_id

    def _consume(self, reply: QNetworkReply) -> bool:
        if reply is not self._reply:
            return False
        payload = bytes(reply.readAll())
        if len(self._received) + len(payload) > _MAX_RESPONSE:
            request_id = self._release(reply)
            reply.abort()
            if request_id is not None:
                self.failed.emit(request_id, "API response exceeded size limit")
            return False
        self._received.extend(payload)
        return True

    def _complete(self, reply: QNetworkReply) -> None:
        if reply is not self._reply or not self._consume(reply):
            return
        status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        redirect = reply.attribute(QNetworkRequest.Attribute.RedirectionTargetAttribute)
        data = bytes(self._received)
        request_id = self._release(reply)
        if request_id is None:
            return
        if redirect is not None or status is None or not 200 <= int(status) < 300:
            self.failed.emit(request_id, "API request rejected or redirect refused")
            return
        try:
            result = json.loads(data.decode("utf-8", errors="strict"))
            if not isinstance(result, dict):
                raise ValueError("Expected JSON object")
            self.succeeded.emit(request_id, json.dumps(result, separators=(",", ":"),
                                                     ensure_ascii=False))
        except (ValueError, UnicodeError, TypeError, RecursionError):
            self.failed.emit(request_id, "API response was invalid")
