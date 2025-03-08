"""Database initialization and session management."""
import logging
import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker, declarative_base

# Configure logging
logger = logging.getLogger(__name__)

# Database configuration
BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
DB_NAME = 'albumexplore.db'
DEFAULT_DB_PATH = os.path.join(BASE_DIR, DB_NAME)
SQLALCHEMY_DATABASE_URL = os.getenv('DATABASE_URL', f'sqlite:///{DEFAULT_DB_PATH}')

# Global SQLAlchemy instances
Base = declarative_base()
_engine = None
_SessionFactory = None

def init_db(db_url=None):
    """Initialize the database connection."""
    global _engine, _SessionFactory
    
    if not db_url:
        db_url = SQLALCHEMY_DATABASE_URL
        
    # Ensure the database directory exists
    if db_url.startswith('sqlite:///'):
        db_path = db_url.replace('sqlite:///', '')
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    
    if _engine is None:
        logger.info(f"Initializing database at {db_url}")
        _engine = create_engine(
            db_url,
            connect_args={"check_same_thread": False},
            pool_pre_ping=True
        )
        
        _SessionFactory = scoped_session(
            sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=_engine
            )
        )
        
        # Create all tables
        Base.metadata.create_all(_engine)
        logger.info("Database tables created successfully")
    
    return _SessionFactory(), _engine

@contextmanager
def get_session():
    """Get a database session with automatic cleanup."""
    if _SessionFactory is None:
        init_db()
    
    session = _SessionFactory()
    try:
        yield session
    finally:
        session.close()

def get_engine():
    """Get the SQLAlchemy engine instance."""
    global _engine
    if _engine is None:
        init_db()
    return _engine

# Import models after Base is defined
from . import models

