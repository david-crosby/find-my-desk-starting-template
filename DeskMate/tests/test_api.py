import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from places_core.models import Base, Building, Desk, Floor, Section, User
from places_backend.main import app
from places_backend.deps import get_db


@pytest.fixture()
def db_session():
    # StaticPool ensures all sessions share the same in-memory connection, so
    # tables created by create_all() are visible to every subsequent session.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_list_desks_empty(client):
    resp = client.get("/desks/")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_rooms_empty(client):
    resp = client.get("/rooms/")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.fixture()
def seeded_db(db_session):
    building = Building(name="HQ", address="Test Street")
    db_session.add(building)
    db_session.flush()
    floor = Floor(building_id=building.id, number=1, name="Ground")
    db_session.add(floor)
    db_session.flush()
    section = Section(floor_id=floor.id, name="Main Area")
    db_session.add(section)
    db_session.flush()
    desk = Desk(section_id=section.id, label="T-01")
    user = User(email="test@example.com", display_name="Test User")
    db_session.add_all([desk, user])
    db_session.commit()
    return {"desk": desk, "user": user}


def test_create_booking(client, seeded_db):
    resp = client.post(
        "/bookings/",
        json={
            "user_id": seeded_db["user"].id,
            "desk_id": seeded_db["desk"].id,
            "date": "2025-06-01",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["date"] == "2025-06-01"
    assert data["status"] == "queued"


def test_cancel_booking(client, seeded_db):
    create_resp = client.post(
        "/bookings/",
        json={
            "user_id": seeded_db["user"].id,
            "desk_id": seeded_db["desk"].id,
            "date": "2025-06-02",
        },
    )
    booking_id = create_resp.json()["id"]

    cancel_resp = client.delete(f"/bookings/{booking_id}")
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"


def test_get_booking_not_found(client):
    resp = client.get("/bookings/99999")
    assert resp.status_code == 404
