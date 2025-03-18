"""Test configuration and fixtures."""
import os
import logging
import pytest
from pathlib import Path
from typing import Tuple, List
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from albumexplore.database import Base
from albumexplore.visualization.models import VisualNode, VisualEdge
from .utils import setup_test_config
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

# Configure test logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Global test session storage
_test_session = None

def set_test_session(session):
    """Set the global test session."""
    global _test_session
    _test_session = session

def clear_test_session():
    """Clear the global test session."""
    global _test_session
    _test_session = None

@pytest.fixture(scope="function")
def engine():
    """Create test database engine."""
    engine = create_engine('sqlite:///:memory:', poolclass=None)
    yield engine
    engine.dispose()

@pytest.fixture(scope="function")
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
    session_factory = sessionmaker(bind=connection)
    session = scoped_session(session_factory)
    
    yield session
    
    session.remove()
    transaction.rollback()
    connection.close()

@pytest.fixture(autouse=True)
def setup_test_environment(db_session):
    """Set up test environment before each test."""
    logger.debug("Setting up test environment")
    setup_test_config()
    set_test_session(db_session)
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

@pytest.fixture(scope="module")
def qapp():
    """Create QApplication instance for the test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    # Don't quit the app as it may be needed by other tests

@pytest.fixture
def qtbot(qapp):
    """Create a QtBot instance for Qt tests."""
    from pytestqt.plugin import QtBot
    result = QtBot(qapp)
    yield result

@pytest.fixture
def process_events(qapp):
    """Process Qt events for animations."""
    def _process():
        qapp.processEvents()
    return _process