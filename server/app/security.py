"""Single-owner preview authentication and explicit provider privacy boundaries."""
import hmac
import os

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

bearer = HTTPBearer(auto_error=False)


def require_owner(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> None:
    expected = os.getenv("GOREECLOUD_AI_TOKEN", "").strip()
    if not expected:
        raise HTTPException(503, "Owner API token is not configured")
    if not credentials or not hmac.compare_digest(credentials.credentials, expected):
        raise HTTPException(401, "Invalid owner token", headers={"WWW-Authenticate": "Bearer"})


def required_openrouter_key() -> str:
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise HTTPException(503, "OpenRouter API key is not configured")
    return key
