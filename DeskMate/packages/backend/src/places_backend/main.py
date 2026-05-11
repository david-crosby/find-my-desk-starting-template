import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from places_core.db import engine
from places_core.models import Base
from places_core.settings import settings

from .api import admin, bookings, desks, feedback, rooms, users

Base.metadata.create_all(bind=engine)

app = FastAPI(title="DeskMate API", version="0.1.0")

# Allow the Streamlit UIs (and any future SPA) to call the API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://localhost:8502"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "Authorization"],
)

# User-facing routes — require any authenticated Entra ID user.
# In dev/demo mode (ms_places_enabled=false) auth is bypassed in deps.py.
app.include_router(desks.router, prefix="/desks", tags=["desks"])
app.include_router(rooms.router, prefix="/rooms", tags=["rooms"])
app.include_router(bookings.router, prefix="/bookings", tags=["bookings"])
app.include_router(feedback.router, prefix="/feedback", tags=["feedback"])
app.include_router(users.router, prefix="/users", tags=["users"])

# Admin routes — require Global Administrator role (enforced in admin router).
app.include_router(admin.router, prefix="/admin", tags=["admin"])


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "ms_places_enabled": settings.ms_places_enabled}


def run() -> None:
    uvicorn.run("places_backend.main:app", host="0.0.0.0", port=8000, reload=True)
