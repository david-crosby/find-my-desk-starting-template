import pytest
from unittest.mock import MagicMock, patch

from places_backend.services.allocation import allocate_desk, allocate_room


def test_allocate_desk_returns_first_available():
    mock_desk = MagicMock(id=1, label="G-01")
    db = MagicMock()

    with patch(
        "places_backend.services.allocation.get_available_desks",
        return_value=[mock_desk],
    ):
        result = allocate_desk(db, "2025-06-01")

    assert result is mock_desk


def test_allocate_desk_returns_none_when_fully_booked():
    db = MagicMock()

    with patch(
        "places_backend.services.allocation.get_available_desks",
        return_value=[],
    ):
        result = allocate_desk(db, "2025-06-01")

    assert result is None


def test_allocate_room_returns_first_available():
    mock_room = MagicMock(id=2, name="Boardroom")
    db = MagicMock()

    with patch(
        "places_backend.services.allocation.get_available_rooms",
        return_value=[mock_room],
    ):
        result = allocate_room(db, "2025-06-01", "09:00", "10:00")

    assert result is mock_room


def test_allocate_room_returns_none_when_none_available():
    db = MagicMock()

    with patch(
        "places_backend.services.allocation.get_available_rooms",
        return_value=[],
    ):
        result = allocate_room(db, "2025-06-01", "09:00", "10:00")

    assert result is None
