import uvicorn
from fastapi import FastAPI

from places_core.db import engine
from places_core.models import Base

from .api import admin, bookings, desks, rooms

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Places Booking API", version="0.1.0")

app.include_router(desks.router, prefix="/desks", tags=["desks"])
app.include_router(rooms.router, prefix="/rooms", tags=["rooms"])
app.include_router(bookings.router, prefix="/bookings", tags=["bookings"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


def run() -> None:
    uvicorn.run("places_backend.main:app", host="0.0.0.0", port=8000, reload=True)
