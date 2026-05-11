"""
DeskMate — Microsoft Graph / Places connectivity test.

Run from the DeskMate/ directory:
    uv run python scripts/test_ms_api.py

Tests (in order):
  1. Load credentials from .env
  2. Acquire app-only access token (client credentials)
  3. Decode token claims (audience, tenant, expiry)
  4. GET /v1.0/organization  — basic Graph connectivity
  5. GET /beta/places/microsoft.graph.room  — Places rooms
  6. GET /beta/places/microsoft.graph.workspace  — Places workspaces
  7. GET /v1.0/users  — User.Read.All (needed for booking UPN resolution)

Each step prints PASS / FAIL with the relevant detail.
No data is written or modified.
"""
from __future__ import annotations

import base64
import json
import os
import sys
import time
from pathlib import Path

# ── Load .env ────────────────────────────────────────────────────────────────

def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip())


_load_dotenv(Path(__file__).parent.parent / ".env")

TENANT_ID = os.environ.get("AZURE_TENANT_ID", "")
CLIENT_ID = os.environ.get("AZURE_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("AZURE_CLIENT_SECRET", "")

# ── Helpers ───────────────────────────────────────────────────────────────────

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"
SKIP = "\033[33mSKIP\033[0m"
INFO = "\033[36mINFO\033[0m"


def _check(label: str, ok: bool, detail: str = "") -> bool:
    status = PASS if ok else FAIL
    suffix = f"  {detail}" if detail else ""
    print(f"  [{status}] {label}{suffix}")
    return ok


def _section(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


def _decode_jwt_claims(token: str) -> dict:
    """Decode JWT payload without signature verification (for inspection only)."""
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload))
    except Exception:
        return {}


# ── Step 1: Credentials ───────────────────────────────────────────────────────

_section("1. Credentials from .env")
creds_ok = True
_check("AZURE_TENANT_ID set", bool(TENANT_ID), TENANT_ID[:8] + "…" if TENANT_ID else "MISSING")
_check("AZURE_CLIENT_ID set", bool(CLIENT_ID), CLIENT_ID[:8] + "…" if CLIENT_ID else "MISSING")
creds_ok = _check("AZURE_CLIENT_SECRET set", bool(CLIENT_SECRET),
                  f"{len(CLIENT_SECRET)} chars" if CLIENT_SECRET else "MISSING")

if not (TENANT_ID and CLIENT_ID and CLIENT_SECRET):
    print("\n  Cannot continue without credentials. Set them in .env and retry.")
    sys.exit(1)

# ── Step 2: Token acquisition ─────────────────────────────────────────────────

_section("2. App-only token (client credentials)")

try:
    from msal import ConfidentialClientApplication
except ImportError:
    print(f"  [{FAIL}] msal not installed — run: uv add msal")
    sys.exit(1)

try:
    import httpx
except ImportError:
    print(f"  [{FAIL}] httpx not installed — run: uv add httpx")
    sys.exit(1)

try:
    msal_app = ConfidentialClientApplication(
        client_id=CLIENT_ID,
        client_credential=CLIENT_SECRET,
        authority=f"https://login.microsoftonline.com/{TENANT_ID}",
    )
except ValueError as exc:
    _check("MSAL app initialised", False, str(exc)[:120])
    print("\n  Common causes:")
    print("    • AZURE_TENANT_ID is wrong — copy it from the Entra portal Overview page")
    print("    • Tenant does not exist or is in a different cloud (GCC, GovCloud, etc.)")
    sys.exit(1)

token_result = msal_app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
access_token = token_result.get("access_token", "")

if not access_token:
    error = token_result.get("error_description", token_result.get("error", "unknown"))
    _check("Token acquired", False, error)
    print("\n  Common causes:")
    print("    • AZURE_CLIENT_SECRET: copy the Value (not the Secret ID / GUID)")
    print("    • Secret has expired — generate a new one in the app registration")
    print("    • AZURE_CLIENT_ID mismatch — must be the app's Application (client) ID")
    sys.exit(1)

_check("Token acquired", True, f"expires_in={token_result.get('expires_in')}s")

# ── Step 3: Token claims ──────────────────────────────────────────────────────

_section("3. Token claims (decoded, not verified)")

claims = _decode_jwt_claims(access_token)
aud = claims.get("aud", "")
tid = claims.get("tid", "")
exp = claims.get("exp", 0)
roles = claims.get("roles", [])

_check("Audience is Graph", aud == "https://graph.microsoft.com", aud)
_check("Tenant ID matches", tid == TENANT_ID, tid)
_check("Token not expired", time.time() < exp,
       f"expires {time.strftime('%H:%M:%S', time.localtime(exp))}")

if roles:
    print(f"  [{INFO}] App roles granted: {', '.join(roles)}")
else:
    print(f"  [{INFO}] No app roles in token (permissions may be delegated-only — check API Permissions)")

# ── Step 4: Places rooms ──────────────────────────────────────────────────────

headers = {"Authorization": f"Bearer {access_token}"}

_section("4. Microsoft Places  GET /beta/places/microsoft.graph.room")

try:
    resp = httpx.get(
        "https://graph.microsoft.com/beta/places/microsoft.graph.room",
        headers=headers,
        params={"$top": 10},
        timeout=15,
    )
    if resp.status_code == 200:
        rooms = resp.json().get("value", [])
        _check("Rooms endpoint reachable", True, f"{len(rooms)} room(s) returned")
        for r in rooms[:3]:
            name = r.get("displayName", "—")
            building = r.get("building", "—")
            email = r.get("emailAddress", "—")
            capacity = r.get("capacity", "—")
            print(f"         • {name}  |  building={building}  |  cap={capacity}  |  {email}")
        if not rooms:
            print(f"  [{INFO}] No rooms returned — tenant may not have MS Places configured,")
            print(f"         or Place.Read.All admin consent is missing.")
    elif resp.status_code == 403:
        _check("Rooms endpoint reachable", False, "403 Forbidden — Place.Read.All permission missing or admin consent not granted")
    elif resp.status_code == 404:
        _check("Rooms endpoint reachable", False, "404 — MS Places (beta) not available on this tenant; requires M365 E5 or Places licence")
    else:
        _check("Rooms endpoint reachable", False, f"HTTP {resp.status_code}: {resp.text[:120]}")
except Exception as exc:
    _check("Rooms endpoint reachable", False, str(exc))

# ── Step 5: Places workspaces ─────────────────────────────────────────────────

_section("5. Microsoft Places  GET /beta/places/microsoft.graph.workspace")

try:
    resp = httpx.get(
        "https://graph.microsoft.com/beta/places/microsoft.graph.workspace",
        headers=headers,
        params={"$top": 10},
        timeout=15,
    )
    workspace_emails: list[str] = []
    if resp.status_code == 200:
        workspaces = resp.json().get("value", [])
        _check("Workspaces endpoint reachable", True, f"{len(workspaces)} workspace(s) returned")
        for w in workspaces[:3]:
            name = w.get("displayName", "—")
            building = w.get("building", "—")
            floor = w.get("floorNumber", "—")
            email = w.get("emailAddress", "—")
            print(f"         • {name}  |  building={building}  floor={floor}  |  {email}")
        workspace_emails = [w["emailAddress"] for w in workspaces if w.get("emailAddress")]
        if not workspaces:
            print(f"  [{INFO}] No workspaces returned — workspaces must be configured in")
            print(f"         the Microsoft Places admin portal (places.microsoft.com).")
    elif resp.status_code == 403:
        _check("Workspaces endpoint reachable", False, "403 Forbidden — Place.Read.All admin consent missing")
        workspace_emails = []
    elif resp.status_code == 404:
        _check("Workspaces endpoint reachable", False, "404 — workspace type not available on this tenant")
        workspace_emails = []
    else:
        _check("Workspaces endpoint reachable", False, f"HTTP {resp.status_code}: {resp.text[:120]}")
        workspace_emails = []
except Exception as exc:
    _check("Workspaces endpoint reachable", False, str(exc))
    workspace_emails = []

# ── Step 6: Availability check (getSchedule) ─────────────────────────────────

_section("6. Availability check  POST /v1.0/users/{upn}/calendar/getSchedule")

from datetime import date, timedelta

tomorrow = (date.today() + timedelta(days=1)).isoformat()
start_dt = f"{tomorrow}T09:00:00"
end_dt = f"{tomorrow}T10:00:00"

if workspace_emails:
    probe_email = workspace_emails[0]
    try:
        resp = httpx.post(
            f"https://graph.microsoft.com/v1.0/users/{probe_email}/calendar/getSchedule",
            headers=headers,
            json={
                "schedules": workspace_emails[:5],
                "startTime": {"dateTime": start_dt, "timeZone": "GMT Standard Time"},
                "endTime": {"dateTime": end_dt, "timeZone": "GMT Standard Time"},
                "availabilityViewInterval": 60,
            },
            timeout=15,
        )
        if resp.status_code == 200:
            schedules = resp.json().get("value", [])
            free = sum(1 for s in schedules if not s.get("scheduleItems"))
            _check("getSchedule works", True, f"{free}/{len(schedules)} workspace(s) free {tomorrow} 09:00–10:00")
            for s in schedules:
                status = "free" if not s.get("scheduleItems") else "busy"
                print(f"         • {s['scheduleId']}  →  {status}")
        elif resp.status_code == 403:
            _check("getSchedule works", False, "403 — Calendars.ReadWrite not consented or mailbox access denied")
        else:
            _check("getSchedule works", False, f"HTTP {resp.status_code}: {resp.text[:120]}")
    except Exception as exc:
        _check("getSchedule works", False, str(exc))
else:
    print(f"  [{SKIP}] No workspace emails available to test — skipped")

# ── Step 7: User directory ────────────────────────────────────────────────────

_section("7. User directory  GET /v1.0/users  (User.Read.All)")

try:
    resp = httpx.get(
        "https://graph.microsoft.com/v1.0/users",
        headers=headers,
        params={"$top": 5, "$select": "id,displayName,mail,userPrincipalName"},
        timeout=10,
    )
    if resp.status_code == 200:
        users = resp.json().get("value", [])
        _check("User.Read.All granted", True, f"{len(users)} user(s) in page")
        for u in users[:3]:
            print(f"         • {u.get('displayName', '—')}  {u.get('mail') or u.get('userPrincipalName', '—')}")
    elif resp.status_code == 403:
        _check("User.Read.All granted", False, "403 — add User.Read.All (Application) in API permissions and grant admin consent")
    else:
        _check("User.Read.All granted", False, f"HTTP {resp.status_code}: {resp.text[:120]}")
except Exception as exc:
    _check("User.Read.All granted", False, str(exc))

# ── Summary ───────────────────────────────────────────────────────────────────

print(f"\n{'─' * 60}")
print("  Done. Fix any FAIL items above before enabling MS_PLACES_ENABLED=true.")
print(f"{'─' * 60}\n")
