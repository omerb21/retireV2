import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


def _build_session_local() -> sessionmaker:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")
    engine = create_engine(database_url)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


SessionLocal: sessionmaker | None = None


def get_db() -> Generator[Session, None, None]:
    global SessionLocal
    if SessionLocal is None:
        SessionLocal = _build_session_local()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
