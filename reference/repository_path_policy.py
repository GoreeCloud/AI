from __future__ import annotations

import re

_ALLOWED_ENV_TEMPLATES = {".env.example", ".env.sample", ".env.template", ".env.dist"}
_BLOCKED_BASENAMES = {"id_rsa", "id_ed25519", "credentials.json", "service-account.json"}
_BLOCKED_KEY_EXTENSION_RE = re.compile(r"\.(?:pem|key|p12|pfx|jks|keystore)$", re.IGNORECASE)


def repository_path_allowed(path: str) -> bool:
    for segment in path.split("/"):
        basename = segment.lower()
        if basename == ".env" or (basename.startswith(".env.") and basename not in _ALLOWED_ENV_TEMPLATES):
            return False
        if basename in _BLOCKED_BASENAMES:
            return False
        if _BLOCKED_KEY_EXTENSION_RE.search(basename) is not None:
            return False
    return True
