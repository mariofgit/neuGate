from __future__ import annotations

import logging
import secrets

from fastapi import Depends, Header, HTTPException, status

from neugate.settings import Settings, get_settings

logger = logging.getLogger(__name__)

_API_KEY_HEADER = "X-API-Key"
_AUTH_DISABLED_LOGGED = False


def _extract_api_key(
    x_api_key: str | None,
    authorization: str | None,
) -> str | None:
    if x_api_key and x_api_key.strip():
        return x_api_key.strip()
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
        return token or None
    return None


async def verify_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    """Require NEUGATE_API_KEY when configured. Skip auth when unset (local dev only)."""
    global _AUTH_DISABLED_LOGGED

    expected = settings.api_key.strip()
    if not expected:
        if not _AUTH_DISABLED_LOGGED:
            logger.warning(
                "NEUGATE_API_KEY is not set — API authentication is disabled. "
                "Set NEUGATE_API_KEY in production.",
            )
            _AUTH_DISABLED_LOGGED = True
        return

    provided = _extract_api_key(x_api_key, authorization)
    if not provided or not secrets.compare_digest(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key. Use X-API-Key or Authorization: Bearer <key>.",
            headers={"WWW-Authenticate": "Bearer"},
        )
