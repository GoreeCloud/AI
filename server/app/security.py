"""Single-owner auth modes. No upstream data or JWT header can select the key source.

Default mode is a local owner token. Optional offline-JWKS OIDC resource mode
checks a pinned operator-managed public key and exact issuer/audience/owner/scope.
This is a standards-based adapter, NOT deployed GoreeCloud Identity.
"""
import hmac
import json
import os
import stat
from pathlib import Path
from urllib.parse import urlsplit

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

bearer = HTTPBearer(auto_error=False)


def _unauthorized() -> HTTPException:
    return HTTPException(401, "Invalid authentication credentials",
                         headers={"WWW-Authenticate": "Bearer"})


def _oidc_claims(token: str) -> dict:
    issuer = os.getenv("GOREECLOUD_AI_OIDC_ISSUER", "").rstrip("/")
    audience = os.getenv("GOREECLOUD_AI_OIDC_AUDIENCE", "")
    owner_sub = os.getenv("GOREECLOUD_AI_OIDC_OWNER_SUB", "")
    required_scope = os.getenv("GOREECLOUD_AI_OIDC_REQUIRED_SCOPE", "goreecloud.ai.owner")
    key_path = os.getenv("GOREECLOUD_AI_OIDC_JWKS_PATH", "")
    origin = urlsplit(issuer)
    if (origin.scheme != "https" or not origin.hostname or origin.username or origin.password
            or origin.query or origin.fragment or not audience or not owner_sub
            or not required_scope or not key_path):
        raise HTTPException(503, "OIDC mode requires a pinned issuer, audience, owner and JWKS")
    path = Path(key_path).expanduser()
    try:
        if path.is_symlink() or not path.is_file():
            raise ValueError("untrusted JWKS path")
        metadata = path.stat()
        if metadata.st_size > 65536 or metadata.st_mode & (stat.S_IRWXG | stat.S_IRWXO):
            raise ValueError("unprotected JWKS file")
        document = json.loads(path.read_text(encoding="utf-8"))
        keys = document.get("keys")
        if not isinstance(keys, list) or not 1 <= len(keys) <= 8:
            raise ValueError("invalid public key set")
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        if (not isinstance(kid, str) or not kid or header.get("alg") != "RS256"
                or header.get("crit") or header.get("jku") or header.get("x5u")):
            raise ValueError("unapproved JWT header")
        matching = [key for key in keys if isinstance(key, dict) and key.get("kid") == kid
                    and key.get("kty") == "RSA"
                    and key.get("alg", "RS256") == "RS256"
                    and key.get("use", "sig") == "sig"]
        if len(matching) != 1:
            raise ValueError("untrusted signing key")
        public_key = jwt.PyJWK.from_dict(matching[0], algorithm="RS256").key
        claims = jwt.decode(
            token, public_key, algorithms=["RS256"], audience=audience,
            issuer=issuer, leeway=30,
            options={"require": ["exp", "nbf", "iat", "iss", "aud", "sub"]},
        )
    except (OSError, UnicodeError, TypeError, KeyError, ValueError, jwt.PyJWTError) as exc:
        # Never disclose JWTs, key material or claims in HTTP errors.
        raise _unauthorized() from exc
    if claims.get("sub") != owner_sub:
        raise _unauthorized()
    scopes = claims.get("scope", "")
    if not isinstance(scopes, str) or required_scope not in scopes.split():
        raise _unauthorized()
    return claims


def require_owner(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> None:
    mode = os.getenv("GOREECLOUD_AI_AUTH_MODE", "owner")
    if mode not in ("owner", "oidc"):
        raise HTTPException(503, "Invalid authentication mode")
    if not credentials or len(credentials.credentials) > 8192:
        raise _unauthorized()
    if mode == "oidc":
        _oidc_claims(credentials.credentials)
        return
    expected = os.getenv("GOREECLOUD_AI_TOKEN", "").strip()
    if not expected:
        raise HTTPException(503, "Owner API token is not configured")
    if not hmac.compare_digest(credentials.credentials, expected):
        raise _unauthorized()


def required_openrouter_key() -> str:
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise HTTPException(503, "OpenRouter API key is not configured")
    return key
