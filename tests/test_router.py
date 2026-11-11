import pytest
from goreecloud_ai.router import select_model, is_supported_model


def test_selects_gemma_for_general_chat():
    route = select_model("Hello, how are you?", ["qwen2.5:7b", "gemma3:4b"])
    assert route.model == "gemma3:4b"
    assert route.mode == "smart"


def test_selects_qwen_coder_for_code():
    route = select_model("Debug this Python code", ["gemma3:4b", "qwen2.5:7b", "qwen2.5-coder:7b"])
    assert route.model == "qwen2.5-coder:7b"


def test_prefers_qwen_for_reasoning():
    assert select_model("Compare complex architecture", ["gemma3:4b", "qwen3:8b"]).model == "qwen3:8b"


def test_fallback_available_only():
    assert select_model("Write Python", ["gemma3:4b"]).model == "gemma3:4b"


def test_unknown_manual_override_rejected():
    with pytest.raises(ValueError):
        select_model("hi", ["qwen3:8b"], requested="nonexistent:7b")


def test_no_supported_models():
    with pytest.raises(LookupError):
        select_model("hello", ["other:latest"])


def test_namespaced_model():
    assert is_supported_model("local/qwen3:8b")
