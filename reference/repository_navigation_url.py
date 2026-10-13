"""Validate display-only repository navigation links before use."""

from __future__ import annotations

from urllib.parse import parse_qsl, unquote, urlsplit

MAX_URL_LENGTH = 4096
MAX_PARAMETERS_PER_SECTION = 64
_BLOCKED_NAMES = frozenset({"auth", "key", "sig", "oauthcode"})
_BLOCKED_SUFFIXES = (
    "token", "secret", "password", "credential", "credentials",
    "authorization", "apikey", "privatekey", "cookie", "signature",
    "sessionid", "sessionkey", "accesskeyid",
)


def _unsafe_parameter_name(name: str) -> bool:
    for _ in range(3):
        decoded = unquote(name)
        if decoded == name:
            break
        name = decoded
    compact = "".join(character for character in name.casefold() if character.isalnum())
    return compact in _BLOCKED_NAMES or compact.endswith(_BLOCKED_SUFFIXES)


def _has_sensitive_navigation_parameter(section: str) -> bool:
    """Check raw, semicolon-delimited and decoded parameter interpretations.

    Some URL consumers historically treat semicolons as field separators, while
    other link renderers decode percent-encoded separators before navigation.
    Any recognized sensitive name in those interpretations fails closed.
    """
    for _ in range(4):
        if any(_unsafe_parameter_name(name) for name, _ in parse_qsl(
            section.replace(";", "&"),
            keep_blank_values=True,
            max_num_fields=MAX_PARAMETERS_PER_SECTION,
        )):
            return True
        decoded = unquote(section)
        if decoded == section:
            break
        section = decoded
    return False


def is_safe_repository_navigation_url(url: object) -> bool:
    """Validate read-only links without fetching or following the target."""
    if not isinstance(url, str) or not 0 < len(url) <= MAX_URL_LENGTH:
        return False
    if any(char.isspace() or ord(char) < 0x20 or ord(char) == 0x7f or char == "\\" for char in url):
        return False
    try:
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return False
        if parsed.username is not None or parsed.password is not None:
            return False
        parsed.port
        for section in (parsed.query, parsed.fragment):
            if _has_sensitive_navigation_parameter(section):
                return False
    except ValueError:
        return False
    return True
