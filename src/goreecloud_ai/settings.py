"""Application configuration. Only administrators control the Ollama endpoint."""
from dataclasses import dataclass
import os
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Settings:
    ollama_url: str = "http://127.0.0.1:11434"
    database_path: str = "./data/ai.sqlite"
    api_token: str | None = None
    max_message_chars: int = 12000
    max_history_messages: int = 30

    def __post_init__(self) -> None:
        p = urlsplit(self.ollama_url)
        if p.scheme not in ("http", "https") or not p.hostname or p.username or p.password or p.query or p.fragment or p.path not in ("", "/"):
            raise ValueError("Ollama URL must be a bare http(s) origin without credentials, path, or query")
        if self.max_message_chars < 1 or self.max_history_messages < 1:
            raise ValueError("Message limits must be positive")
        if self.api_token is not None and len(self.api_token) < 16:
            raise ValueError("Configured API token must contain at least 16 characters")

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            ollama_url=os.getenv("GOREEAI_OLLAMA_URL", "http://127.0.0.1:11434"),
            database_path=os.getenv("GOREEAI_DATABASE_PATH", "./data/ai.sqlite"),
            api_token=os.getenv("GOREEAI_API_TOKEN") or None,
        )
