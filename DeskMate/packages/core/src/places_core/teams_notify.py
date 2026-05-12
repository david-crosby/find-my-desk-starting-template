"""
Teams notification via Microsoft Graph Activity Notifications.

When ms_places_enabled=True, sends a Teams activity feed notification to the
target user using the application-level Graph API (no bot required).

Requires the Azure app registration to have the TeamsActivity.Send application
permission and a Teams app manifest that declares the activity type "deskAlert".

When ms_places_enabled=False (demo mode), notifications are logged but not sent.
"""
import httpx

from .settings import settings

_GRAPH_TOKEN_URL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
_GRAPH_BASE = "https://graph.microsoft.com/v1.0"


def _get_app_token() -> str | None:
    """Acquire an application-level Graph token via client credentials."""
    if not settings.azure_tenant_id or not settings.azure_client_id or not settings.azure_client_secret:
        return None
    try:
        resp = httpx.post(
            _GRAPH_TOKEN_URL.format(tenant=settings.azure_tenant_id),
            data={
                "grant_type": "client_credentials",
                "client_id": settings.azure_client_id,
                "client_secret": settings.azure_client_secret,
                "scope": "https://graph.microsoft.com/.default",
            },
            timeout=10.0,
        )
        resp.raise_for_status()
        return resp.json().get("access_token")
    except Exception:
        return None


def send_desk_alert(entra_id: str, subject: str, body: str) -> bool:
    """
    Send a Teams activity notification to a user.

    Returns True if the notification was sent successfully, False otherwise.
    In demo mode always returns False without attempting a send.
    """
    if not settings.ms_places_enabled:
        return False

    token = _get_app_token()
    if not token:
        return False

    try:
        # Teams activity feed notification — appears in the user's Teams activity pane.
        # The activityType "deskAlert" must be declared in the DeskMate Teams app manifest.
        resp = httpx.post(
            f"{_GRAPH_BASE}/users/{entra_id}/teamwork/sendActivityNotification",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "topic": {
                    "source": "text",
                    "value": "DeskMate",
                    "webUrl": "",
                },
                "activityType": "deskAlert",
                "previewText": {"content": subject},
                "templateParameters": [
                    {"name": "message", "value": body},
                ],
            },
            timeout=10.0,
        )
        return resp.status_code in (200, 202, 204)
    except Exception:
        return False
