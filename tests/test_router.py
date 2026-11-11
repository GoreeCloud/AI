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



def test_fast_prefers_smaller_parameter_label():
    route = select_model("Hello", ["gemma3:12b", "gemma3:4b", "gemma3:1b"], "smart:fast")
    assert route.model == "gemma3:1b"
    assert route.mode == "smart"


def test_quality_prefers_larger_parameter_label():
    route = select_model("Compare architecture", ["qwen3:4b", "qwen3:8b", "qwen3:14b"], "smart:quality")
    assert route.model == "qwen3:14b"
    assert "quality profile" in route.reason


def test_coding_prefers_installed_coder_with_fast_profile():
    names = ["qwen3:4b", "qwen2.5-coder:7b", "qwen2.5-coder:14b"]
    assert select_model("Debug Python code", names, "smart:fast").model == "qwen2.5-coder:7b"


def test_family_fallback_is_explained():
    route = select_model("Hello", ["qwen3:4b", "qwen3:8b"], "smart:fast")
    assert route.model == "qwen3:4b"
    assert "preferred family unavailable" in route.reason


def test_balanced_alias_matches_default():
    available = ["qwen3:8b", "gemma3:4b"]
    assert select_model("Hello", available, "smart").model == select_model("Hello", available, "smart:balanced").model


def test_manual_selection_still_works():
    assert select_model("hello", ["other:latest"], "other:latest").mode == "manual"


def test_model_parameter_label_parsing():
    from goreecloud_ai.router import advertised_parameter_billions
    assert advertised_parameter_billions("qwen3:14b") == 14.0
    assert advertised_parameter_billions("gemma3:4b-instruct") == 4.0
    assert advertised_parameter_billions("gemma3:latest") is None
