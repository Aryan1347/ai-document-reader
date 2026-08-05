import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# ── DB URL ────────────────────────────────────────────────────────────────────
# SQLite for demo; swap this one line for PostgreSQL in prod:
# postgresql://user:password@host:5432/dbname
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./chat_history.db")

# ── Engine ────────────────────────────────────────────────────────────────────
# check_same_thread=False required for SQLite + FastAPI (multiple threads)
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

# ── Session Factory ───────────────────────────────────────────────────────────
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ── Base Class ────────────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── Dependency for FastAPI ────────────────────────────────────────────────────
def get_db():
    """
    FastAPI dependency — yields a DB session, closes after request.
    Usage: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()