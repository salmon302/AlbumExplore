"""Database initialization and configuration."""
import os
from contextlib import contextmanager
from typing import Iterator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, Session
from albumexplore.database.models import Base
from albumexplore.gui.gui_logging import db_logger

_engine = None
_SessionFactory = None
_TestSessionFactory = None

def init_db(database_url: str = None) -> None:
    """Initialize database connection."""
    global _engine, _SessionFactory
    
    if not database_url:
        # Default to SQLite database in project root
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'albumexplore.db')
        database_url = f"sqlite:///{db_path}"
    
    db_logger.info(f"Initializing database with URL: {database_url}")
    
    # Create engine with extended timeout for large operations
    _engine = create_engine(
        database_url,
        connect_args={
            "timeout": 60,  # 60 second timeout
            "check_same_thread": False
        },
        pool_pre_ping=True  # Enable automatic reconnection
    )
    
    # Create all tables
    Base.metadata.create_all(_engine)
    
    # Create session factory
    _SessionFactory = sessionmaker(bind=_engine)
    
    db_logger.info("Database initialized successfully")

def get_session():
    """Get a new database session."""
    global _SessionFactory, _TestSessionFactory
    if _TestSessionFactory:
        return scoped_session(_TestSessionFactory)
    if not _SessionFactory:
        init_db()
    return scoped_session(_SessionFactory)

@contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional scope around a series of operations."""
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def set_test_session():
    """Set up test database session."""
    global _TestSessionFactory, _engine
    
    # Use SQLite in-memory database for testing
    _engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(_engine)
    _TestSessionFactory = sessionmaker(bind=_engine)

def clear_test_session():
    """Clear test database session."""
    global _TestSessionFactory, _engine
    
    if _TestSessionFactory is not None:
        if _engine:
            Base.metadata.drop_all(_engine)
        _TestSessionFactory = None
        _engine = None

