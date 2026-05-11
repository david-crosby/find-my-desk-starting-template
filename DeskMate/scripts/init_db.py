#!/usr/bin/env python3
"""Create all database tables from the SQLAlchemy models."""
import sys
from pathlib import Path

_ROOT = Path(__file__).parent.parent
for _pkg in ("core", "backend", "agent"):
    _src = _ROOT / "packages" / _pkg / "src"
    if str(_src) not in sys.path:
        sys.path.insert(0, str(_src))

from places_core.db import engine
from places_core.models import Base

Path("data").mkdir(exist_ok=True)
Base.metadata.create_all(bind=engine)
print("Tables created.")
