"""List installed Ollama models without assuming that Qwen or Gemma is present."""
from __future__ import annotations
import re
from dataclasses import dataclass

NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/+:@-]{0,159}$")

class CatalogError(Exception):
    pass

@dataclass(frozen=True)
class ModelChoice:
    name: str
    family: str
    size_bytes: int | None
    provider: str = "ollama"
    processing: str = "local"
    tools_verified: bool = False

def family(name: str) -> str:
    hint = name.rsplit("/",1)[-1].split(":",1)[0].lower()
    return "Qwen" if hint.startswith("qwen") else "Gemma" if hint.startswith("gemma") else "Other"

class OllamaModelCatalog:
    def __init__(self, gateway):
        if not callable(getattr(gateway,"list_models",None)):
            raise CatalogError("invalid_runtime")
        self.gateway = gateway

    def installed(self) -> tuple[ModelChoice,...]:
        records = self.gateway.list_models()
        if type(records) is not tuple or len(records)>200:
            raise CatalogError("invalid_response")
        choices = []
        seen = set()
        for record in records:
            name = getattr(record,"name",None)
            size = getattr(record,"size_bytes",None)
            if (type(name) is not str or not NAME.fullmatch(name)
                    or "://" in name or name in seen
                    or (size is not None and (type(size) is not int or size<0))):
                raise CatalogError("invalid_response")
            seen.add(name)
            choices.append(ModelChoice(name,family(name),size))
        return tuple(sorted(choices,key=lambda c:c.name))

    def select(self,name:str) -> ModelChoice:
        if type(name) is not str or not NAME.fullmatch(name) or "://" in name:
            raise CatalogError("invalid_model")
        for option in self.installed():
            if option.name == name:
                return option
        raise CatalogError("model_not_installed")
