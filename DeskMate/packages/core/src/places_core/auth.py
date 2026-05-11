"""
Entra ID (Azure AD) JWT token validation for the DeskMate backend.

Flow:
  1. Streamlit UIs obtain a user access token via the device code or auth code
     flow using a PublicClientApplication (see ui auth modules).
  2. The token is passed in the Authorization: Bearer header on every API call.
  3. The FastAPI backend validates the token using Microsoft's published JWKS.
  4. Admin routes additionally check the `wids` claim for the Global Administrator
     well-known role ID.

The Global Administrator well-known ID is a stable Microsoft constant:
  62e90394-69f5-4237-9190-012177145e10
"""
from __future__ import annotations

import jwt
from jwt import PyJWKClient

from .settings import settings

# Stable well-known ID for the Entra ID Global Administrator role.
_GLOBAL_ADMIN_WID = "62e90394-69f5-4237-9190-012177145e10"

# PyJWKClient caches the JWKS — one instance per process is sufficient.
_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        jwks_uri = (
            f"https://login.microsoftonline.com/{settings.azure_tenant_id}"
            "/discovery/v2.0/keys"
        )
        _jwks_client = PyJWKClient(jwks_uri, cache_keys=True)
    return _jwks_client


def verify_token(token: str) -> dict:
    """
    Validate an Entra ID access token and return its decoded claims.

    Raises jwt.exceptions.* on any validation failure (expired, wrong audience,
    wrong issuer, invalid signature).
    """
    client = _get_jwks_client()
    signing_key = client.get_signing_key_from_jwt(token)

    claims = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=settings.azure_client_id,
        issuer=(
            f"https://login.microsoftonline.com/{settings.azure_tenant_id}/v2.0"
        ),
        options={"require": ["exp", "iss", "aud", "sub"]},
    )
    return claims


def is_global_admin(claims: dict) -> bool:
    """
    Return True if the token's `wids` claim includes the Global Administrator
    well-known role ID.  The `wids` claim is present when the user has been
    assigned a directory role in Entra ID.
    """
    return _GLOBAL_ADMIN_WID in claims.get("wids", [])
