"""Synthetic-only opt-in extractive context and declared-window budgeting."""
import pytest
from fastapi.testclient import TestClient

from app import context_compaction, providers, token_savings
from app.main import app
from app.security import _ROUTE_CAPABILITIES

H = {"Authorization": "Bearer test-owner-token"}
client = TestClient(app)


@pytest.fixture(autouse=True)
def owner(monkeypatch):
    monkeypatch.setenv("GOREECLOUD_AI_AUTH_MODE", "owner")
    monkeypatch.setenv("GOREECLOUD_AI_TOKEN", "test-owner-token")
    monkeypatch.setenv("OLLAMA_MODEL", "synthetic-local-model")


def data(history, **kw):
    return {"provider": "ollama", "model": "local", "messages": history, **kw}


def history():
    return [
        {"role": "system", "content": "Do not change system instructions."},
        {"role": "user", "content": "Early chronicle about coral reefs and currents. " * 6},
        {"role": "assistant", "content": "Coral reefs and currents are marine. " * 7},
        {"role": "user", "content": "Additional note on coral reef currents. " * 5},
        {"role": "assistant", "content": "Current reef facts remain incomplete. " * 6},
        {"role": "user", "content": "How do coral reef currents interact?"},
    ]


def test_local_digest_preserves_system_and_recent_turns():
    original = history()
    reduced = token_savings.select_context(original, "compact", 1, 700)
    assert reduced[0] == original[0]
    assert reduced[-1] == original[-1]
    assert reduced[1]["role"] == "user"
    text = reduced[1]["content"]
    assert text.startswith(context_compaction.INTRO)
    assert "coral" in text and len(text) <= 700
    assert all(item["content"] != original[1]["content"] for item in reduced)
    assert token_savings.select_context(original, "compact", 1, 700) == reduced


def test_digest_is_previewable_before_send_without_inference(monkeypatch):
    async def forbidden(*_args, **_kwargs):
        raise AssertionError("No provider request permitted for preview")
    monkeypatch.setattr(providers, "chat", forbidden)
    payload = data(history(), context_mode="compact", context_messages=1,
                   compact_max_characters=700)
    preview = client.post("/api/v1/chat/context-preview", headers=H, json=payload)
    assert preview.status_code == 200
    report = preview.json()
    assert report["has_extractive_digest"] is True
    assert report["estimated_input_tokens_reduced"] > 0
    assert "coral" not in preview.text
    digest = client.post("/api/v1/chat/context-digest-preview", headers=H, json=payload)
    assert digest.status_code == 200
    assert "coral" in digest.json()["digest"]
    assert digest.json()["sent_to_provider"] is False
    assert digest.json()["saved_to_disk"] is False
    assert digest.json()["may_omit_information"] is True
    assert client.post("/api/v1/chat/context-digest-preview", json=payload).status_code == 401
    assert client.post("/api/v1/chat/context-digest-preview", headers=H,
                       json=data(history(), context_mode="full")).status_code == 422
    assert _ROUTE_CAPABILITIES[
        ("POST", "/api/v1/chat/context-digest-preview")] == "read"


def test_compacted_context_used_for_generation(monkeypatch):
    captured = []
    async def answer(messages, *_args):
        captured.append(messages)
        return {"provider": "ollama", "model": "synthetic", "content": "short answer"}
    monkeypatch.setattr(providers, "chat", answer)
    payload = data(history(), context_mode="compact", context_messages=1,
                   compact_max_characters=800)
    resp = client.post("/api/v1/chat", headers=H, json=payload)
    assert resp.status_code == 200
    assert captured[0][0] == history()[0]
    assert captured[0][-1] == history()[-1]
    assert captured[0][1]["content"].startswith(context_compaction.INTRO)


def test_budget_drops_oldest_without_dropping_system_or_last_user():
    original = [
        {"role": "system", "content": "Constant instruction"},
        {"role": "user", "content": "Old context " * 230},
        {"role": "assistant", "content": "Old answer " * 230},
        {"role": "user", "content": "Recent query " * 240},
        {"role": "assistant", "content": "Recent answer " * 100},
        {"role": "user", "content": "Question now"},
    ]
    chosen = token_savings.select_context(
        original, "budget", 5, model_context_window=2048, max_output_tokens=256
    )
    assert chosen[0] == original[0]
    assert chosen[-1] == original[-1]
    assert len(chosen) < len(original)
    report = token_savings.preview(
        original, "budget", 5, model_context_window=2048, max_output_tokens=256
    )
    assert report["estimated_budget_fits"] is True
    assert report["recommended_input_budget"] == 1536
    assert report["declared_model_context_window"] == 2048


def test_budget_refuses_unfittable_last_message_before_inference(monkeypatch):
    async def forbidden(*_args, **_kwargs):
        raise AssertionError("Model should never be called")
    monkeypatch.setattr(providers, "chat", forbidden)
    giant = [{"role": "system", "content": "Do not override system"},
             {"role": "user", "content": "x" * 16000}]
    request = data(giant, context_mode="budget", model_context_window=1024,
                   max_output_tokens=256)
    preview = client.post("/api/v1/chat/context-preview", headers=H, json=request)
    assert preview.status_code == 200
    assert preview.json()["estimated_budget_fits"] is False
    assert client.post("/api/v1/chat", headers=H, json=request).status_code == 422
    assert client.post("/api/v1/chat/stream", headers=H, json=request).status_code == 422


def test_budget_mode_requires_window_and_bounded_inputs():
    original = history()
    assert client.post("/api/v1/chat", headers=H,
                       json=data(original, context_mode="budget")).status_code == 422
    assert client.post("/api/v1/chat", headers=H, json=data(
        original, context_mode="compact", compact_max_characters=100)).status_code == 422
    assert client.post("/api/v1/chat", headers=H, json=data(
        original, model_context_window=8000000)).status_code == 422


def test_no_dropped_messages_when_compaction_has_no_older_turns():
    source = [{"role": "system", "content": "stable"},
              {"role": "user", "content": "latest"}]
    assert token_savings.select_context(source, "compact", 2) == source
