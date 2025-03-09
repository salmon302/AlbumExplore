"""Test configuration and fixtures."""
import os
import logging
import pytest
from pathlib import Path
from typing import Tuple, List

from albumexplore.database import Base, set_test_session, clear_test_session
from albumexplore.visualization.models import VisualNode, VisualEdge
from .utils import setup_test_config

# Configure test logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

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
def db_session(engine, tables):
    """Create a new database session for a test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = scoped_session(sessionmaker(bind=connection))
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(autouse=True)
def setup_test_environment(db_session):
    """Set up test environment before each test."""
    logger.debug("Setting up test environment")
    setup_test_config()
    set_test_session()
    yield
    clear_test_session()
    logger.debug("Test environment cleanup complete")

@pytest.fixture
def sample_data() -> Tuple[List[VisualNode], List[VisualEdge]]:
    """Create sample visualization data."""
    # Create sample nodes
    nodes = [
        VisualNode(
            id="1",
            label="Album 1",
            data={"type": "row", "artist": "Artist 1", "title": "Album 1", "year": "2020"}
        ),
        VisualNode(
            id="2", 
            label="Album 2",
            data={"type": "row", "artist": "Artist 2", "title": "Album 2", "year": "2021"}
        ),
        VisualNode(
            id="3",
            label="Album 3",
            data={"type": "row", "artist": "Artist 3", "title": "Album 3", "year": "2022"}
        )
    ]
    
    # Create sample edges
    edges = [
        VisualEdge(id="e1-2", source="1", target="2"),
        VisualEdge(id="e2-3", source="2", target="3")
    ]
    
    return nodes, edges

@pytest.fixture
def qt_application():
    """Create QApplication instance for tests."""
    from PyQt6.QtWidgets import QApplication
    app = QApplication([])
    yield app
    app.quit()