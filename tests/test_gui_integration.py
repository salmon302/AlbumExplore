"""Integration tests for the GUI components."""
import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtTest import QTest
from albumexplore.gui.main_window import MainWindow
from albumexplore.visualization.state import ViewType
from albumexplore.database import create_session


@pytest.fixture
def app():
	"""Create QApplication instance for tests."""
	return QApplication([])


@pytest.fixture
def main_window(app):
	"""Create MainWindow instance for tests."""
	session = create_session()
	window = MainWindow(session)
	return window


def test_view_switching(main_window):
	"""Test switching between different view types."""
	# Switch to each view type and verify
	for view_type in ViewType:
		main_window.view_selector.setCurrentText(view_type.value)
		# Get the expected view class
		view_class = main_window.view_manager.get_view_class(view_type)
		assert isinstance(main_window.current_view, view_class)


def test_data_loading(main_window):
	"""Test data loading and display."""
	main_window.load_data()
	assert len(main_window.view_manager.nodes) > 0
	assert hasattr(main_window, 'current_view')


def test_selection_sync(main_window):
	"""Test selection synchronization across views."""
	# Make selection in table view
	main_window.view_selector.setCurrentText(ViewType.TABLE.value)
	table_view = main_window.current_view
	table_view.table.selectRow(0)
	selected = table_view.selected_ids
	
	# Switch to network view and verify selection
	main_window.view_selector.setCurrentText(ViewType.NETWORK.value)
	network_view = main_window.current_view
	assert network_view.selected_ids == selected


def test_responsive_layout(main_window):
	"""Test responsive layout behavior."""
	initial_size = main_window.size()
	new_width = int(initial_size.width() * 1.5)
	new_height = int(initial_size.height() * 1.5)
	main_window.resize(new_width, new_height)
	assert main_window.size().width() > initial_size.width()


def test_window_state_persistence(main_window):
	"""Test window state saving and restoration."""
	initial_size = QSize(1024, 768)
	main_window.resize(initial_size)
	main_window.save_window_state()
	
	# Change window state
	main_window.resize(800, 600)
	
	# Restore state
	main_window.restore_window_state()
	assert main_window.size() == initial_size

def test_view_transition_animation(main_window, qtbot):
	"""Test smooth transitions between views."""
	main_window.view_selector.setCurrentText(ViewType.NETWORK.value)
	initial_view = main_window.current_view
	
	# Switch view and verify transition
	main_window.view_selector.setCurrentText(ViewType.CHORD.value)
	assert hasattr(main_window, 'transition_animation')
	assert main_window.current_view is not initial_view

def test_error_state_visualization(main_window):
	"""Test visual feedback during error states."""
	# Simulate error state
	main_window.error_manager.handle_error(Exception("Visual test error"))
	
	# Verify error indicators
	assert main_window.status_bar.currentMessage() != ""
	assert "Visual test error" in main_window.status_bar.currentMessage()
	
	# Test error recovery
	main_window.error_manager.clear_errors()
	assert main_window.status_bar.currentMessage() == ""

def test_responsive_layout_edge_cases(main_window):
	"""Test layout behavior under extreme window sizes."""
	# Test minimum size
	main_window.resize(main_window.minimumSize())
	min_size = main_window.size()
	assert min_size.width() > 0 and min_size.height() > 0
	
	# Test very large size
	large_size = QSize(2000, 1500)
	main_window.resize(large_size)
	assert main_window.current_view.width() <= large_size.width()
	assert main_window.current_view.height() <= large_size.height()

def test_view_synchronization(main_window):
	"""Test synchronization between different views."""
	# Make selection in network view
	main_window.view_selector.setCurrentText(ViewType.NETWORK.value)
	network_view = main_window.current_view
	
	# Simulate node selection
	test_node_id = list(network_view.nodes)[0].id
	network_view.select_nodes([test_node_id])
	
	# Switch to chord view and verify selection
	main_window.view_selector.setCurrentText(ViewType.CHORD.value)
	chord_view = main_window.current_view
	assert test_node_id in chord_view.selected_nodes

def test_error_handling(main_window):
	"""Test error handling and display."""
	main_window.error_manager.handle_error(Exception("Test error"), None)
	assert "Test error" in main_window.status_bar.currentMessage()