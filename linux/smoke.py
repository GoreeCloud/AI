"""Offscreen Qt Quick startup and synthetic chat lifecycle checks."""
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from chat_stream import ChatStreamBridge
from PySide6.QtCore import QTimer, QUrl, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, qmlContext
from rest_bridge import SafeRestBridge


class RecordingChatStream(ChatStreamBridge):
    @Slot(str, str, str)
    def start(self, _address, _owner_token, json_body):
        self.messages = json.loads(json_body)["messages"]


def check_chat_transcript(window, stream):
    context = qmlContext(window)
    prompt = context.objectForName("chatPrompt")
    window.setProperty("token", "synthetic-owner-token")

    def send(text):
        prompt.setProperty("text", text)
        window.sendChat()
        assert window.property("busy")
        return stream.messages

    first = send("Cancelled before text")
    stream.stopped.emit()
    second = send("Completed without text")
    assert second == [*first, {"role": "user", "content": "Completed without text"}]
    stream.completed.emit("ollama", "synthetic-model")
    third = send("Cancelled after partial text")
    assert third == [*second, {"role": "user", "content": "Cancelled after partial text"}]
    stream.delta.emit("Synthetic partial answer")
    stream.stopped.emit()
    fourth = send("Follow-up after partial text")
    assert fourth == [
        *third,
        {"role": "assistant", "content": "Synthetic partial answer"},
        {"role": "user", "content": "Follow-up after partial text"},
    ]
    stream.failed.emit("Synthetic provider error")


app = QGuiApplication(sys.argv)
engine = QQmlApplicationEngine()
bridge = RecordingChatStream()
engine.rootContext().setContextProperty("streamBridge", bridge)
rest_bridge = SafeRestBridge()
engine.rootContext().setContextProperty("restBridge", rest_bridge)
engine.load(QUrl.fromLocalFile(str(Path(__file__).resolve().parent / "Main.qml")))
if not engine.rootObjects():
    raise SystemExit("Qt Quick scene failed to load")
check_chat_transcript(engine.rootObjects()[0], bridge)
QTimer.singleShot(200, app.quit)
raise SystemExit(app.exec())
