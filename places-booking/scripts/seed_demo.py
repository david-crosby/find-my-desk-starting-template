#!/usr/bin/env python3
"""Populate the database with demo locations, floors, desks, rooms, and users."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from places_core.db import SessionLocal
from places_core.models import Desk, Floor, Location, Room, User

db = SessionLocal()
try:
    hq = Location(name="HQ", address="1 Main Street, London")
    satellite = Location(name="Satellite Office", address="42 High Road, Manchester")
    db.add_all([hq, satellite])
    db.flush()

    g_floor = Floor(location_id=hq.id, number=0, name="Ground")
    f_floor = Floor(location_id=hq.id, number=1, name="First")
    s_floor = Floor(location_id=satellite.id, number=0, name="Ground")
    db.add_all([g_floor, f_floor, s_floor])
    db.flush()

    for i in range(1, 6):
        db.add(Desk(floor_id=g_floor.id, label=f"G-{i:02d}"))
    for i in range(1, 4):
        db.add(Desk(floor_id=f_floor.id, label=f"F-{i:02d}"))
    for i in range(1, 3):
        db.add(Desk(floor_id=s_floor.id, label=f"S-{i:02d}"))

    db.add_all([
        Room(floor_id=g_floor.id, name="Boardroom", capacity=12),
        Room(floor_id=g_floor.id, name="Huddle A", capacity=4),
        Room(floor_id=f_floor.id, name="Training Room", capacity=20),
        Room(floor_id=f_floor.id, name="Huddle B", capacity=4),
        Room(floor_id=s_floor.id, name="Meeting Room 1", capacity=6),
    ])

    db.add_all([
        User(email="alice@example.com", display_name="Alice Smith"),
        User(email="bob@example.com", display_name="Bob Jones"),
        User(email="carol@example.com", display_name="Carol White"),
        User(email="admin@example.com", display_name="Facilities Admin", is_admin=True),
    ])

    db.commit()
    print("Demo data loaded.")
finally:
    db.close()
