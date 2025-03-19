import pytest
from PyQt6.QtWidgets import QMainWindow
from albumexplore.gui.main_window import MainWindow
from albumexplore.visualization.view_manager import ViewManager

def test_main_window_creation(qapp):
    """Test that main window can be created successfully."""
    window = MainWindow()
    assert isinstance(window, QMainWindow)
    assert window.windowTitle() == "Album Explorer"

def test_main_window_view_manager(qapp):
    """Test view manager initialization in main window."""
    window = MainWindow()
    assert hasattr(window, 'view_manager')
    assert isinstance(window.view_manager, ViewManager)

def test_main_window_menu_actions(qapp):
    """Test menu actions are properly initialized."""
    window = MainWindow()
    assert window.menuBar() is not None
    file_menu = window.menuBar().findChild(QMenu, "fileMenu")
    assert file_menu is not None
    assert len(file_menu.actions()) > 0

def test_main_window_status_bar(qapp):
    """Test status bar initialization."""
    window = MainWindow()
    assert window.statusBar() is not None
    
def test_main_window_resize(qapp):
    """Test window responds to resize events."""
    window = MainWindow()
    initial_size = window.size()
    window.resize(800, 600)
    assert window.size() != initial_size
    assert window.size().width() == 800
    assert window.size().height() == 600