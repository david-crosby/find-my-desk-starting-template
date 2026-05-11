from unittest.mock import MagicMock, patch

from places_agent.tools import dispatch_tool


def test_dispatch_unknown_tool():
    result = dispatch_tool("does_not_exist", {})
    assert "error" in result


def _mock_response(payload):
    resp = MagicMock()
    resp.json.return_value = payload
    resp.raise_for_status = MagicMock()
    return resp


def test_list_my_bookings():
    payload = [{"id": 1, "date": "2025-06-01", "status": "confirmed"}]

    with patch("places_agent.tools._client") as mock_client:
        mock_client.get.return_value = _mock_response(payload)
        result = dispatch_tool("list_my_bookings", {"user_id": 1})

    assert isinstance(result, list)
    assert result[0]["id"] == 1


def test_book_desk():
    payload = {"id": 42, "desk_id": 3, "date": "2025-06-01", "status": "confirmed"}

    with patch("places_agent.tools._client") as mock_client:
        mock_client.post.return_value = _mock_response(payload)
        result = dispatch_tool("book_desk", {"user_id": 1, "desk_id": 3, "date": "2025-06-01"})

    assert result["id"] == 42
    assert result["status"] == "confirmed"


def test_cancel_booking():
    payload = {"id": 7, "status": "cancelled"}

    with patch("places_agent.tools._client") as mock_client:
        mock_client.delete.return_value = _mock_response(payload)
        result = dispatch_tool("cancel_booking", {"booking_id": 7})

    assert result["status"] == "cancelled"
