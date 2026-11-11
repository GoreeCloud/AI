"""Deterministic Ollama Smart Model routing. No invented model performance."""
from dataclasses import dataclass
import re

SMART_PROFILES = {"smart": "balanced", "smart:balanced": "balanced", "smart:fast": "fast", "smart:quality": "quality"}
_CODE = re.compile(r"\b(code|python|javascript|typescript|debug|program|refactor|sql|regex|repository)\b", re.I)
_REASON = re.compile(r"\b(reason|prove|analy[sz]e|compare|architecture|step.by.step|complex|research|design)\b", re.I)
_SIZE = re.compile(r":(\d+(?:\.\d+)?)b(?:$|[-_])", re.I)


@dataclass(frozen=True)
class Route:
    model: str
    reason: str
    mode: str


def is_supported_model(name: str) -> bool:
    base = name.rsplit("/", 1)[-1].lower()
    return base.startswith(("qwen", "gemma"))


def advertised_parameter_billions(name: str) -> float | None:
    """A model-tag label, not a measured speed/accuracy indicator."""
    match = _SIZE.search(name)
    return float(match.group(1)) if match is not None else None


def select_model(prompt: str, available: list[str], requested: str = "smart") -> Route:
    installed = sorted(set(m for m in available if is_supported_model(m)))
    if requested not in SMART_PROFILES:
        if requested not in available:
            raise ValueError("Requested model is not installed")
        return Route(requested, "Manually selected installed model", "manual")
    if not installed:
        raise LookupError("Install a Qwen or Gemma model in Ollama to use Smart Model")

    code = bool(_CODE.search(prompt))
    deep = bool(_REASON.search(prompt))
    family = "qwen" if code or deep else "gemma"
    candidates = [m for m in installed if m.rsplit("/", 1)[-1].lower().startswith(family)]
    fallback = not candidates
    if fallback:
        candidates = installed
    if code:
        coders = [m for m in candidates if "coder" in m.lower()]
        if coders:
            candidates = coders

    profile = SMART_PROFILES[requested]
    if profile == "fast":
        candidates.sort(key=lambda m: (
            advertised_parameter_billions(m) is None,
            advertised_parameter_billions(m) if advertised_parameter_billions(m) is not None else 0,
            m,
        ))
    elif profile == "quality":
        candidates.sort(key=lambda m: (
            advertised_parameter_billions(m) is None,
            -(advertised_parameter_billions(m) or 0),
            m,
        ))
    else:
        candidates.sort()
    task = "Coding-oriented request" if code else "Reasoning-oriented request" if deep else "General conversation"
    metric = "smaller parameter label" if profile == "fast" else "larger parameter label" if profile == "quality" else "stable name ordering"
    note = "; preferred family unavailable" if fallback else ""
    return Route(candidates[0], f"{task}; {profile} profile ({metric}); installed models only{note}", "smart")
