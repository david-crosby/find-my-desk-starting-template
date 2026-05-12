import threading
import time
import uvicorn
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from places_core.allocation import run_nightly_allocation
from places_core.auto_release import run_auto_release
from places_core.db import SessionLocal, engine
from places_core.models import Base
from places_core.settings import settings

from .api import admin, bookings, checkin, desks, feedback, rooms, users

Base.metadata.create_all(bind=engine)

_last_allocation_run: dict[str, str] = {}  # date_str → run_date_str


def _scheduler_loop() -> None:
    """Daemon thread: run allocation at the configured time each night."""
    while True:
        time.sleep(60)
        try:
            db = SessionLocal()
            try:
                from places_core.repositories import get_org_rules
                rules = get_org_rules(db)
                run_time = rules.allocation_run_time or "23:00"
            finally:
                db.close()

            now = datetime.now()
            current_hhmm = now.strftime("%H:%M")
            today_str = now.date().isoformat()

            if current_hhmm == run_time and _last_allocation_run.get("date") != today_str:
                _last_allocation_run["date"] = today_str
                target = now.date() + timedelta(days=1)
                db = SessionLocal()
                try:
                    run_nightly_allocation(db, target)
                finally:
                    db.close()

            # Auto-release: check every cycle during the day
            db = SessionLocal()
            try:
                run_auto_release(db)
            finally:
                db.close()
        except Exception:
            pass  # never let the scheduler crash silently kill the thread


@asynccontextmanager
async def lifespan(app: FastAPI):
    t = threading.Thread(target=_scheduler_loop, daemon=True, name="allocation-scheduler")
    t.start()
    yield


app = FastAPI(title="DeskMate API", version="0.1.0", lifespan=lifespan)

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
app.include_router(checkin.router, prefix="/checkin", tags=["checkin"])


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "ms_places_enabled": settings.ms_places_enabled}


def run() -> None:
    uvicorn.run("places_backend.main:app", host="0.0.0.0", port=8000, reload=True)
