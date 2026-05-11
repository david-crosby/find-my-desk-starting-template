import httpx

from places_core.settings import settings


class PlacesClient:
    """MS Graph / Places API wrapper."""

    BASE_URL = "https://graph.microsoft.com/v1.0"

    def __init__(self, access_token: str) -> None:
        self._http = httpx.Client(
            base_url=self.BASE_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )

    def list_rooms(self, building_id: str) -> list[dict]:
        resp = self._http.get(f"/places/{building_id}/microsoft.graph.room")
        resp.raise_for_status()
        return resp.json().get("value", [])

    def close(self) -> None:
        self._http.close()


def get_access_token() -> str:
    import msal

    app = msal.ConfidentialClientApplication(
        client_id=settings.azure_client_id,
        authority=f"https://login.microsoftonline.com/{settings.azure_tenant_id}",
        client_credential=settings.azure_client_secret,
    )
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    return result["access_token"]
