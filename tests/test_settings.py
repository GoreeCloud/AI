"""Configuration validation without attempting network access."""
import pytest
from goreecloud_ai.settings import Settings


@pytest.mark.parametrize("url", [
    "file:///tmp/x", "http://user:pass@127.0.0.1:11434",
    "http://127.0.0.1:11434/admin", "https://example.test/?token=a",
])
def test_rejects_unsafe_ollama_origin_configuration(url):
    with pytest.raises(ValueError):
        Settings(ollama_url=url)


def test_requires_long_token_if_configured():
    with pytest.raises(ValueError):
        Settings(api_token="short")


def test_local_default_configuration_is_valid():
    assert Settings().ollama_url == "http://127.0.0.1:11434"
