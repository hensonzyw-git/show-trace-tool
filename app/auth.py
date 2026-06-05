"""Lightweight bearer-token auth for public cloud deployments."""

import hmac
import os

from fastapi import Header, HTTPException, status


def require_api_token(authorization: str | None = Header(default=None)) -> None:
    """Require Bearer auth only when API_TOKEN is configured.

    Local development remains frictionless with no token. In cloud, set
    API_TOKEN and every /api/* route becomes protected.
    """
    expected = os.environ.get("API_TOKEN")
    if not expected:
        return

    prefix = "Bearer "
    token = (
        authorization.removeprefix(prefix).strip()
        if authorization and authorization.startswith(prefix)
        else ""
    )
    # Constant-time compare to avoid leaking the token via response timing.
    # Always return 401 (not 403) so we don't reveal whether the header format
    # was right vs. the value wrong.
    if not hmac.compare_digest(token, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid bearer token",
        )
