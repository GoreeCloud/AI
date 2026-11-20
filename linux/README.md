# GoreeCloud AI native Linux preview

Qt Quick 6.12 / PySide6 6.12 source, native operating-system window and controls.
Uses the backend REST API; secrets are entered at runtime and not persisted.

On a Linux machine with Python 3.11+ and a supported desktop environment:

    cd linux
    python3 -m venv .venv
    . .venv/bin/activate
    pip install -r requirements.txt
    python main.py

Run the FastAPI server separately and configure a token. The native UI now
requires explicit cloud-processing approval before OpenRouter inference;
without consent, Auto may use the configured Ollama model. Remote API
endpoints must use HTTPS, with HTTP limited to 127.0.0.1/localhost. The Qt Quick interface
supports chat, model routing, image generation preview, Markdown document CRUD,
agent planning and MCP tool discovery/explicit invocation. It is a native
preview, not a packaged binary or fully feature-parity product. It does not yet
support reference-image file selection or durable image downloads.

GoreeCloud UI light/dark/accent tokens are sourced from the MIT-licensed
GoreeCloud/gc-ui snapshot in ../design/gc.tokens.json; current QML uses the
verified dark Iris token values. Native Qt component conformance is untested.
Test on Linux with actual Qt 6.12 graphics, font scaling and accessibility tools
before distribution. No server key should be hardcoded in the application.
