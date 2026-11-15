"""Synchronous SQLAlchemy engine for Celery workers."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

_sync_engine = None
_SyncSessionLocal = None


def get_sync_engine():
    global _sync_engine
    if _sync_engine is None:
        settings = get_settings()
        url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
        _sync_engine = create_engine(url, pool_pre_ping=True)
    return _sync_engine


def get_sync_session_factory() -> sessionmaker[Session]:
    global _SyncSessionLocal
    if _SyncSessionLocal is None:
        _SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_sync_engine())
    return _SyncSessionLocal


@contextmanager
def sync_session_scope() -> Generator[Session, None, None]:
    """Context manager for Celery tasks."""
    factory = get_sync_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
