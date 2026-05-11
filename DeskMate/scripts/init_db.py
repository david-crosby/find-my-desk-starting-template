#!/usr/bin/env python3
"""Create all database tables from the SQLAlchemy models."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from places_core.db import engine
from places_core.models import Base

Path("data").mkdir(exist_ok=True)
Base.metadata.create_all(bind=engine)
print("Tables created.")
