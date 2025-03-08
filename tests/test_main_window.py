import pytest
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication
from albumexplore.gui.main_window import MainWindow
from albumexplore.visualization.state import ViewType
from albumexplore.visualization.models import VisualNode, VisualEdge

@pytest.fixture
def db_session():
	"""Mock database session."""
	class MockSession:
		def query(self, *args):
			return self
		def all(self):
			return []
	return MockSession()

@pytest.fixture
def main_window(qtbot, db_session):
	"""Create MainWindow instance."""
	window = MainWindow(db_session)
	window.show()
	qtbot.addWidget(window)
	return window

def test_window_initialization(main_window):
	"""Test window initialization."""
	assert main_window.windowTitle() == "Album Explorer"
	assert main_window.size() >= QSize(1200, 800)
	assert main_window.view_selector.count() == len(ViewType)
	assert main_window.status_bar is not None

def test_view_switching(qtbot, main_window):
	"""Test view switching functionality."""
	# Test switching through all view types
	for view_type in ViewType:
		main_window.view_selector.setCurrentText(view_type.value)
		qtbot.wait(100)  # Allow for view transition
		
		# Verify view switch
		assert hasattr(main_window, 'current_view')
		assert main_window.current_view is not None
		assert main_window.status_bar.currentMessage().startswith("Switched to")

def test_error_handling(qtbot, main_window):
	"""Test error handling and display."""
	# Simulate error
	test_error = Exception("Test error message")
	main_window.error_manager.handle_error(test_error, None)
	
	# Verify error display
	assert "Test error message" in main_window.status_bar.currentMessage()

def test_responsive_design(qtbot, main_window):
	"""Test responsive design behavior."""
	initial_size = main_window.size()
	
	# Test various window sizes
	test_sizes = [
		QSize(1200, 800),  # Base size
		QSize(1600, 1200),  # Large size
		QSize(1200, 800)   # Back to base size
	]
	
	for size in test_sizes:
		main_window.resize(size)
		qtbot.wait(100)  # Allow for resize processing
		
		# Verify view container adapts
		assert main_window.view_container.width() <= size.width()
		assert main_window.view_container.height() <= size.height()

def test_data_loading(qtbot, main_window):
	"""Test data loading functionality."""
	# Initial load
	main_window.load_data()
	assert main_window.status_bar.currentMessage() == "Data loaded successfully"
	
	# Verify view update
	assert hasattr(main_window, 'current_view')
	assert main_window.current_view is not None

def test_keyboard_interaction(qtbot, main_window):
	"""Test keyboard event handling."""
	# Test basic keyboard interaction
	QTest.keyClick(main_window, Qt.Key.Key_Right)
	QTest.keyClick(main_window, Qt.Key.Key_Left)
	
	# Verify window remains responsive
	assert main_window.isVisible()
	assert main_window.current_view is not None

def test_view_persistence(qtbot, main_window):
	"""Test view state persistence during operations."""
	# Switch to network view
	main_window.view_selector.setCurrentText(ViewType.NETWORK.value)
	qtbot.wait(100)
	
	initial_view = main_window.current_view
	
	# Perform operations that should preserve view
	main_window.load_data()
	main_window.resize(QSize(1400, 1000))
	
	# Verify view persistence
	assert main_window.current_view is not None
	assert type(main_window.current_view) == type(initial_view)

def test_multiple_view_switches(qtbot, main_window):
	"""Test rapid view switching stability."""
	view_types = list(ViewType)
	
	# Rapidly switch between views
	for _ in range(3):  # Multiple cycles
		for view_type in view_types:
			main_window.view_selector.setCurrentText(view_type.value)
			qtbot.wait(50)  # Short delay between switches
			
			# Verify view stability
			assert main_window.current_view is not None
			assert not main_window.current_view.isHidden()