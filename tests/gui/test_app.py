"""Tests for the GUI application."""

import sys
import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt

# Import the main classes from the application
from albumexplore.gui.app import AlbumExplorer


@pytest.fixture(scope="module")
def app():
    """Create a Qt application."""
    # Only create the application once per session
    return QApplication(sys.argv)


@pytest.fixture
def window(app):
    """Create the main application window."""
    window = AlbumExplorer()
    yield window
    # Clean up after the test
    window.close()


def test_window_creation(window):
    """Test that the main window can be created."""
    assert window is not None
    assert window.windowTitle() == "Album Explorer"
    assert window.isVisible() is False  # Window is created but not shown
    assert window.size().width() >= 1200
    assert window.size().height() >= 800


def test_network_view_exists(window):
    """Test that the network view widget is created and set as central widget."""
    assert hasattr(window, "network_view")
    assert window.centralWidget() == window.network_view


def test_data_interface(window):
    """Test that the data interface is initialized."""
    assert hasattr(window, "data_interface")
    assert window.data_interface is not None


def test_view_manager(window):
    """Test that the view manager is initialized."""
    assert hasattr(window, "view_manager")
    assert window.view_manager is not None