"""Database initialization and configuration."""

from . import Base, SQLALCHEMY_DATABASE_URL
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def init_db(db_url=None):
    """Initialize database connection and create tables."""
    if not db_url:
        db_url = SQLALCHEMY_DATABASE_URL
        
    engine = create_engine(db_url)
    Base.metadata.create_all(bind=engine)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal(), engine

def get_test_db():
    """Get a test database connection."""
    test_db_url = "sqlite:///./test.db"
    return init_db(test_db_url)
