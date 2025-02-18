"""Database package initialization."""
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# SQLite database URL
SQLALCHEMY_DATABASE_URL = "sqlite:///./albumexplore.db"

# Create declarative base
Base = declarative_base()

# Create engine
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Create sessionmaker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_session():
	"""Create a new database session."""
	return SessionLocal()

# Create all tables
if os.path.exists("albumexplore.db"):
	os.remove("albumexplore.db")
Base.metadata.create_all(bind=engine)

