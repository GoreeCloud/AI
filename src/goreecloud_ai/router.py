"""Deterministic local Smart Model selection; never invent model availability."""
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class Route:
    model: str
    reason: str
    mode: str


def is_supported_model(name: str) -> bool:
    base = name.rsplit("/", 1)[-1].lower()
    return base.startswith(("qwen", "gemma"))


def select_model(prompt: str, available: list[str], requested: str = "smart") -> Route:
    installed = sorted(set(m for m in available if is_supported_model(m)))
    if requested != "smart":
        if requested not in available:
            raise ValueError("Requested model is not installed")
        return Route(requested, "Manually selected installed model", "manual")
    if not installed:
        raise LookupError("Install a Qwen or Gemma model in Ollama to use Smart Model")
    code = bool(re.search(r"\b(code|python|javascript|typescript|debug|program|refactor|sql|regex|repository)\b", prompt, re.I))
    deep = bool(re.search(r"\b(reason|prove|analy[sz]e|compare|architecture|step.by.step|complex|research|design)\b", prompt, re.I))
    family = "qwen" if code or deep else "gemma"
    candidates = [m for m in installed if m.rsplit("/", 1)[-1].lower().startswith(family)]
    if not candidates:
        candidates = installed
    # Prefer model names with 'coder' for coding tasks, otherwise stable lexical order.
    if code:
        candidates.sort(key=lambda m: (0 if "coder" in m.lower() else 1, m))
    elif deep:
        candidates.sort(key=lambda m: (0 if "qwen" in m.lower() else 1, m))
    else:
        candidates.sort()
    chosen = candidates[0]
    reason = ("Coding-oriented request" if code else "Reasoning-oriented request" if deep else "General conversation") + "; available installed models only"
    return Route(chosen, reason, "smart")
