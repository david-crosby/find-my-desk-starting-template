from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .settings import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
