"""HTTP API and bundled browser client. Localhost by default."""
from pathlib import Path
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from .ollama import OllamaClient, OllamaError
from .router import select_model
from .settings import Settings
from .store import Store


class NewChat(BaseModel):
    title: str = Field(default="New conversation", min_length=1, max_length=100)


class ChatMessage(BaseModel):
    content: str = Field(min_length=1, max_length=12000)
    model: str = "smart"


def create_app(settings: Settings | None = None, ollama: OllamaClient | None = None) -> FastAPI:
    config = settings or Settings.from_env()
    store = Store(config.database_path)
    backend = ollama or OllamaClient(config.ollama_url)
    app = FastAPI(title="GoreeCloud AI", version="0.1.0", docs_url=None, redoc_url=None, openapi_url=None)

    def authenticated(x_api_key: str | None = Header(default=None)):
        if config.api_token:
            import secrets
            if not secrets.compare_digest(x_api_key or "", config.api_token):
                raise HTTPException(401, "Invalid API token")

    @app.get("/api/health")
    async def health():
        try:
            names = await backend.models()
            return {"status": "ok", "ollama": "online", "installed_models": len(names)}
        except OllamaError:
            return {"status": "degraded", "ollama": "offline", "installed_models": 0}

    @app.get("/api/models", dependencies=[Depends(authenticated)])
    async def models():
        try:
            names = await backend.models()
        except OllamaError as exc:
            raise HTTPException(503, str(exc)) from exc
        return {"models": names, "smart_model": "smart", "supported_families": ["qwen", "gemma"]}

    @app.get("/api/chats", dependencies=[Depends(authenticated)])
    def chats():
        return store.list_chats()

    @app.post("/api/chats", status_code=201, dependencies=[Depends(authenticated)])
    def new_chat(payload: NewChat):
        return store.create_chat(payload.title.strip())

    @app.get("/api/chats/{chat_id}", dependencies=[Depends(authenticated)])
    def get_chat(chat_id: str):
        chat = store.get_chat(chat_id)
        if not chat:
            raise HTTPException(404, "Conversation not found")
        return chat

    @app.delete("/api/chats/{chat_id}", dependencies=[Depends(authenticated)])
    def delete_chat(chat_id: str):
        if not store.delete_chat(chat_id):
            raise HTTPException(404, "Conversation not found")
        return {"deleted": True}

    @app.post("/api/chats/{chat_id}/messages", dependencies=[Depends(authenticated)])
    async def send(chat_id: str, payload: ChatMessage):
        chat = store.get_chat(chat_id)
        if not chat:
            raise HTTPException(404, "Conversation not found")
        if len(payload.content) > config.max_message_chars:
            raise HTTPException(422, "Message exceeds configured limit")
        try:
            names = await backend.models()
            route = select_model(payload.content, names, payload.model)
            history = [
                {"role": msg["role"], "content": msg["content"]}
                for msg in chat["messages"][-config.max_history_messages:]
            ]
            reply = await backend.chat(route.model, history + [{"role": "user", "content": payload.content}])
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(503, str(exc)) from exc
        except OllamaError as exc:
            raise HTTPException(502, str(exc)) from exc
        store.add_exchange(chat_id, payload.content, reply, route.model)
        return {"message": {"role": "assistant", "content": reply, "model": route.model}, "routing": {"mode": route.mode, "reason": route.reason}}

    static = Path(__file__).parent / "static"
    app.mount("/assets", StaticFiles(directory=str(static)), name="assets")

    @app.get("/")
    def index():
        return FileResponse(static / "index.html")

    return app


app = create_app()
