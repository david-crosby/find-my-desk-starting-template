"""
Peripheral check-in endpoints.

POST /checkin/webhook  — called by Microsoft Graph change notifications when a
                         registered monitor device changes state (user connects).
GET  /checkin/webhook  — Graph subscription validation (echoes validationToken).
"""
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from places_core.checkin_service import process_peripheral_checkin

from ..deps import get_db

router = APIRouter()


@router.get("/webhook")
def validate_webhook(validationToken: str = Query(...)):
    """MS Graph subscription validation — echo the token back as plain text."""
    return PlainTextResponse(content=validationToken, media_type="text/plain")


@router.post("/webhook")
def peripheral_webhook(request: Request, payload: dict, db: Session = Depends(get_db)) -> dict:
    """
    Receive Microsoft Graph change notifications for workplace sensor devices.

    Expected payload shape (MS Graph notification format):
    {
      "value": [{
        "changeType": "updated",
        "resourceData": {
          "deviceId": "<ms-places-device-id>",
          "userId":   "<entra-user-oid>"
        }
      }]
    }
    """
    results = []
    for notification in payload.get("value", []):
        resource = notification.get("resourceData", {})
        device_id = resource.get("deviceId") or resource.get("device_id")
        entra_id = resource.get("userId") or resource.get("user_id")
        if device_id and entra_id:
            result = process_peripheral_checkin(db, device_id, entra_id, method="peripheral")
            results.append(result)
    return {"processed": len(results), "results": results}
