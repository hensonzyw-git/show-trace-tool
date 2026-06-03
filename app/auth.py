"""Lightweight bearer-token auth for public cloud deployments."""

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
    if not authorization or not authorization.startswith(prefix):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )
    token = authorization.removeprefix(prefix).strip()
    if token != expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid bearer token",
        )
