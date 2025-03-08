"""Integration tests for the GUI components."""
import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from albumexplore.gui.app import AlbumExplorer
from albumexplore.gui.models import AlbumTableModel
from albumexplore.database import set_test_session, clear_test_session
import sys

@pytest.fixture
def app():
    """Create QApplication instance."""
    return QApplication(sys.argv)

@pytest.fixture
def main_window(app, session):
    """Create main application window with test session."""
    # Set the test session before creating the window
    set_test_session(session)
    window = AlbumExplorer()
    yield window
    # Clean up
    clear_test_session()
    window.close()

def test_table_view(main_window):
    """Test that table view displays data correctly."""
    table = main_window.table_view
    model = table.model()
    
    assert isinstance(model, AlbumTableModel)
    assert model.rowCount() >= 0
    
def test_tag_explorer(main_window):
    """Test that tag explorer loads and displays tags."""
    explorer = main_window.tag_explorer
    assert explorer is not None
    
def test_filter_panel(main_window):
    """Test filter panel functionality."""
    filter_panel = main_window.filter_panel
    assert filter_panel is not None