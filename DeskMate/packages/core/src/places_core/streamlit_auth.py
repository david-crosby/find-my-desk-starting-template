"""
Entra ID SSO for Streamlit via MSAL authorization code flow.

Usage in any Streamlit app.py:

    from places_core.streamlit_auth import require_login, get_access_token

    require_login()   # redirects to Microsoft login if not authenticated
    token = get_access_token()  # pass in Authorization header to backend

Streamlit captures the OAuth callback via st.query_params — no separate
callback server is needed.  Register http://localhost:8501 (user UI) and
http://localhost:8502 (admin UI) as Web redirect URIs in the app registration.
"""
from __future__ import annotations

import streamlit as st
from msal import ConfidentialClientApplication

from .settings import settings

# Only request scopes for one resource at a time — mixing Graph scopes (User.Read)
# with custom API scopes causes Azure to return a Graph token, which the backend
# rejects. User profile info comes from the ID token claims, not Graph.
_SCOPES = [f"api://{settings.azure_client_id}/user_impersonation"]


def _msal_app() -> ConfidentialClientApplication:
    # validate_authority=False skips the eager OpenID discovery HTTP call at
    # construction time — auth still works; discovery happens lazily on first
    # token request instead of crashing the app before the page renders.
    return ConfidentialClientApplication(
        client_id=settings.azure_client_id,
        client_credential=settings.azure_client_secret,
        authority=f"https://login.microsoftonline.com/{settings.azure_tenant_id}",
        validate_authority=False,
    )


def _redirect_uri() -> str:
    port = st.get_option("server.port")
    return f"http://localhost:{port}"


def require_login() -> None:
    """
    Gate the Streamlit app behind Entra ID login.

    When ms_places_enabled is false, authentication is skipped and a demo
    identity is written to session state so the app works without Azure.

    Call this at the top of every page's app.py before rendering any content.
    """
    if not settings.ms_places_enabled:
        st.session_state.setdefault("auth_token", "demo-token")
        st.session_state.setdefault("auth_name", "Demo User")
        st.session_state.setdefault("auth_email", "demo@deskmate.local")
        st.session_state.setdefault("auth_entra_id", "demo")
        return

    # Already authenticated
    if st.session_state.get("auth_token"):
        return

    try:
        app = _msal_app()
    except Exception as exc:
        st.error(
            f"Cannot reach the Microsoft authentication service — check your network connection.\n\n`{exc}`"
        )
        st.stop()
    redirect_uri = _redirect_uri()
    params = st.query_params

    # ── Handle callback from Entra ────────────────────────────────────────────
    if "code" in params:
        result = app.acquire_token_by_authorization_code(
            code=params["code"],
            scopes=_SCOPES,
            redirect_uri=redirect_uri,
        )
        st.query_params.clear()
        if "access_token" in result:
            _store_token(result)
            st.rerun()
            return
        # Exchange failed — fall through and show the sign-in button with an error
        err = result.get("error_description", result.get("error", "Unknown error"))
        st.error(f"Sign-in failed: {err}")

    if "error" in params:
        st.error(f"Sign-in failed: {params.get('error_description', params['error'])}")
        st.query_params.clear()

    # ── Show sign-in page (never auto-redirect — prevents loops) ──────────────
    auth_url = app.get_authorization_request_url(
        scopes=_SCOPES,
        redirect_uri=redirect_uri,
    )
    st.title("DeskMate")
    st.markdown("#### Sign in with your Microsoft work account to continue.")
    st.markdown(
        f'<a href="{auth_url}" target="_self">'
        '<button style="background:#0078D4;color:white;padding:10px 28px;'
        'border:none;border-radius:4px;font-size:15px;cursor:pointer;margin-top:8px">'
        'Sign in with Microsoft</button></a>',
        unsafe_allow_html=True,
    )
    st.stop()


def get_access_token() -> str:
    """Return the stored access token, or an empty string in demo mode."""
    return st.session_state.get("auth_token", "")


def get_auth_headers() -> dict:
    """Return an Authorization header dict suitable for httpx / requests calls."""
    token = get_access_token()
    if token and token != "demo-token":
        return {"Authorization": f"Bearer {token}"}
    return {}


def logout() -> None:
    """Clear the session and force re-authentication."""
    for key in ("auth_token", "auth_name", "auth_email", "auth_entra_id", "msal_device_flow"):
        st.session_state.pop(key, None)
    st.rerun()


def _store_token(result: dict) -> None:
    st.session_state["auth_token"] = result["access_token"]
    id_claims = result.get("id_token_claims", {})
    st.session_state["auth_name"] = id_claims.get("name", result.get("account", {}).get("name", "User"))
    st.session_state["auth_email"] = id_claims.get("preferred_username", "")
    st.session_state["auth_entra_id"] = id_claims.get("oid", "")
