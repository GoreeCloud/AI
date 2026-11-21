"""Offscreen QML loading smoke test: verifies component loading, not live UI usability."""
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from chat_stream import ChatStreamBridge
from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from rest_bridge import SafeRestBridge

app = QGuiApplication(sys.argv)
engine = QQmlApplicationEngine()
bridge = ChatStreamBridge()
engine.rootContext().setContextProperty("streamBridge", bridge)
rest_bridge = SafeRestBridge()
engine.rootContext().setContextProperty("restBridge", rest_bridge)
engine.load(QUrl.fromLocalFile(str(Path(__file__).resolve().parent / "Main.qml")))
if not engine.rootObjects():
    raise SystemExit("Qt Quick scene failed to load")
QTimer.singleShot(200, app.quit)
raise SystemExit(app.exec())
