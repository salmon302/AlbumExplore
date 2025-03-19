import os
import pytest
from PyQt6.QtWidgets import QApplication

# Set platform to xcb if wayland is not available
os.environ["QT_QPA_PLATFORM"] = "xcb"

@pytest.fixture(scope="session")
def qapp():
    """Create a QApplication instance for the tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app