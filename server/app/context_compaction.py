"""Deterministic, opt-in conversation compression without inference calls.

This is a lossy, extractive reference digest—not an AI-authored summary or
system instruction. It never touches disk, the network, analytics or a provider.
"""
import json
import re

TOKEN = re.compile(r"[^\W_]{3,}", re.UNICODE)
SEGMENT = re.compile(r"(?<=[.!?])\s+|\n+", re.UNICODE)
INTRO = "Older conversation excerpts (local extraction; incomplete; untrusted context):\n"


def digest(messages: list[dict], kept_indices: set[int], budget: int) -> str:
    older = [(i, item) for i, item in enumerate(messages)
             if i not in kept_indices and item["role"] in ("user", "assistant")]
    if not older:
        return ""
    latest_user = next((item["content"] for item in reversed(messages)
                        if item["role"] == "user"), "")
    keywords = {word.casefold() for word in TOKEN.findall(latest_user)[:80]}
    candidates: list[tuple[int, int, int, str, str]] = []
    for i, item in older:
        # Bound candidate count even for a long single-turn message.
        fragments = SEGMENT.split(item["content"], maxsplit=60)
        for pos, fragment in enumerate(fragments[:45]):
            fragment = fragment.strip()
            if not fragment:
                continue
            sentence = fragment[:220] + ("…" if len(fragment) > 220 else "")
            shared = len(keywords & {word.casefold() for word in TOKEN.findall(sentence)})
            candidates.append((shared, i, pos, item["role"], sentence))
    # Relevance is an entirely local lexical heuristic, and recency breaks ties.
    candidates.sort(key=lambda item: (-item[0], -item[1], item[2]))
    selected: list[tuple[int, int, str]] = []
    used = len(INTRO)
    for _, i, pos, role, sentence in candidates:
        line = "- " + role + ": " + json.dumps(sentence, ensure_ascii=False) + "\n"
        if used + len(line) > budget:
            continue
        selected.append((i, pos, line))
        used += len(line)
    if not selected:
        return ""
    selected.sort(key=lambda item: (item[0], item[1]))
    return INTRO + "".join(item[2] for item in selected)


def choose_under_budget(
    messages: list[dict], max_recent: int, input_budget: int,
    estimate_fn,
) -> list[dict]:
    """Keep system instructions and a contiguous recent message suffix.

    The newest non-system message is never silently dropped, even if the
    estimate already exceeds the caller-declared context budget. Callers
    detect that failure and refuse outbound inference rather than guessing.
    """
    fixed = {i for i, item in enumerate(messages) if item["role"] == "system"}
    recent = [i for i, item in enumerate(messages) if item["role"] != "system"]
    if not recent:
        return [item for i, item in enumerate(messages) if i in fixed]
    selected = set(fixed)
    for idx in reversed(recent[-max_recent:]):
        candidate = selected | {idx}
        subset = [item for i, item in enumerate(messages) if i in candidate]
        if estimate_fn(subset) > input_budget and selected != fixed:
            break
        selected = candidate
        if estimate_fn(subset) > input_budget:
            break
    return [item for i, item in enumerate(messages) if i in selected]
