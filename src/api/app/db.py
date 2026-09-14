"""
Database connection and session management for FloodRescue API.

Provides SQLAlchemy engine, session factory, and dependency injection
for database access in FastAPI routes.
"""
import logging
import os
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.pool import QueuePool

logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://floodrescue:floodrescue@postgres:5432/floodrescue",
)

# Engine configuration with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=3600,   # Recycle connections after 1 hour
    echo=False,
)

# Session factory with explicit transaction settings
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)

# SQLAlchemy ORM base for model declarations
Base = declarative_base()


@event.listens_for(Engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Enable PostGIS extensions on connection establishment."""
    try:
        cursor = dbapi_conn.cursor()
        cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis")
        cursor.close()
    except Exception as e:
        logger.warning(f"PostGIS extension already enabled or unavailable: {e}")


def get_db() -> Session:
    """
    Dependency injection for FastAPI routes to get a database session.

    Yields a SQLAlchemy Session that is automatically closed after use.
    Typical usage in a FastAPI route:

        @app.get("/items")
        def list_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    Context manager for direct database access (non-FastAPI contexts).

    Usage:
        with get_db_context() as db:
            result = db.query(Model).filter(...).first()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        logger.error(f"Database context error: {e}")
        db.rollback()
        raise
    finally:
        db.close()
