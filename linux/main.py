"""Native Linux entry point. No key is persisted on disk by this client."""
import sys
from pathlib import Path

from chat_stream import ChatStreamBridge
from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from rest_bridge import SafeRestBridge


def main() -> int:
    app = QGuiApplication(sys.argv)
    app.setApplicationName("GoreeCloud AI")
    app.setOrganizationName("GoreeCloud")
    engine = QQmlApplicationEngine()
    bridge = ChatStreamBridge()
    engine.rootContext().setContextProperty("streamBridge", bridge)
    rest_bridge = SafeRestBridge()
    engine.rootContext().setContextProperty("restBridge", rest_bridge)
    path = Path(__file__).resolve().parent / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(path)))
    if not engine.rootObjects():
        return 1
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
