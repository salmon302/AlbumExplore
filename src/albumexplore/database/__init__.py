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
        # Default to SQLite database in project root instead of src folder
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'albumexplore.db')
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

def get_session() -> Session:
    """Get a new database session."""
    if _SessionFactory is None:
        init_db()
    return _SessionFactory()

@contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional scope around a series of operations."""
    session = get_session()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()

def set_test_session():
    """Set up test database session."""
    global _TestSessionFactory, _engine
    
    # Use in-memory SQLite for tests
    _engine = create_engine('sqlite:///:memory:',
                          connect_args={"check_same_thread": False})
    Base.metadata.create_all(_engine)
    _TestSessionFactory = sessionmaker(bind=_engine)
    
def clear_test_session():
    """Clear test database session."""
    global _TestSessionFactory, _engine
    if _engine:
        Base.metadata.drop_all(_engine)
    _TestSessionFactory = None
    _engine = None

