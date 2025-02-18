from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from . import Base, SQLALCHEMY_DATABASE_URL
from . import models  # Import models to ensure they're registered with Base

def init_db():
    """Initialize the database connection and create tables."""
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    return engine
