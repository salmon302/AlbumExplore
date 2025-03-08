"""Test configuration and fixtures."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from albumexplore.database import Base, set_test_session, clear_test_session

@pytest.fixture(scope="session")
def engine():
    """Create test database engine."""
    return create_engine('sqlite:///:memory:')

@pytest.fixture(scope="session")
def tables(engine):
    """Create all tables for testing."""
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)

@pytest.fixture
def session(engine, tables):
    """Create a new database session for a test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = scoped_session(sessionmaker(bind=connection))
    
    # Set as the test session
    set_test_session(session)
    
    yield session
    
    # Clean up
    clear_test_session()
    session.close()
    transaction.rollback()
    connection.close()