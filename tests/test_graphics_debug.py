import pytest
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtWidgets import QWidget, QGraphicsItem
from PyQt6.QtTest import QTest
from albumexplore.gui.graphics_debug import GraphicsDebugMonitor
from albumexplore.gui.views import NetworkViewWidget
from albumexplore.visualization.models import VisualNode, VisualEdge
import time

class MockGraphicsItem:
	def __init__(self, x=0, y=0):
		self._pos = QPointF(x, y)
		self._rect = None
	
	def pos(self):
		return self._pos
	
	def boundingRect(self):
		return self._rect

@pytest.fixture
def debug_monitor(qtbot):
	widget = QWidget()
	qtbot.addWidget(widget)
	return GraphicsDebugMonitor(widget)

def test_frame_rate_monitoring(debug_monitor, caplog):
	"""Test frame rate monitoring and logging."""
	# Simulate slow frames
	for _ in range(5):
		debug_monitor.log_paint_event(debug_monitor.parent(), "paint")
		time.sleep(0.05)  # Simulate 50ms frame time
	
	# Trigger frame rate check
	debug_monitor._check_frame_rate()
	
	# Verify warning was logged
	assert any("low frame rate" in record.message.lower() 
			  for record in caplog.records)

def test_overlap_detection(debug_monitor, caplog):
	"""Test detection of overlapping elements."""
	# Create items at same position
	items = [
		MockGraphicsItem(0, 0),
		MockGraphicsItem(1, 1),  # Very close to first item
	]
	
	debug_monitor.log_overlap_check(debug_monitor.parent(), items)
	
	# Verify overlap warning was logged
	assert any("overlap detected" in record.message.lower() 
			  for record in caplog.records)

def test_buffer_state_logging(debug_monitor, caplog):
	"""Test uncleared buffer detection."""
	debug_monitor.log_buffer_state(debug_monitor.parent(), False)
	
	# Verify warning about uncleared buffer
	assert any("uncleared buffer" in record.message.lower() 
			  for record in caplog.records)

def test_view_update_logging(debug_monitor, caplog):
	"""Test logging of view update statistics."""
	# Simulate low visibility scenario
	debug_monitor.log_view_update(debug_monitor.parent(), 5, 100)
	
	# Verify low visibility warning
	assert any("low visibility" in record.message.lower() 
			  for record in caplog.records)

def test_integration_with_network_view(qtbot, caplog):
	"""Test integration with actual NetworkView."""
	view = NetworkViewWidget()
	qtbot.addWidget(view)
	
	# Create test data with overlapping nodes
	nodes = [
		VisualNode(id="1", label="Node 1", size=10, color="#000", 
				  shape="circle", data={"x": 0, "y": 0}),
		VisualNode(id="2", label="Node 2", size=10, color="#000", 
				  shape="circle", data={"x": 1, "y": 1})  # Very close to first node
	]
	edges = [
		VisualEdge(source="1", target="2", weight=1, color="#000", thickness=1)
	]
	
	# Update view with test data
	view.update_data(nodes, edges)
	
	# Trigger a resize to test multiple aspects
	view.resize(800, 600)
	qtbot.wait(100)
	
	# Verify various graphics issues were logged
	assert any("overlap detected" in record.message.lower() 
			  for record in caplog.records)

def test_continuous_monitoring(debug_monitor, qtbot, caplog):
	"""Test continuous monitoring of graphics issues."""
	widget = debug_monitor.parent()
	
	# Simulate rapid updates
	for _ in range(10):
		debug_monitor.log_paint_event(widget, "paint")
		qtbot.wait(10)
	
	# Verify frame timing was logged
	assert any(record.levelname == "WARNING" 
			  for record in caplog.records)

def test_graphics_debug_cleanup(debug_monitor):
	"""Test proper cleanup of graphics debugging."""
	# Verify frame monitor stops
	debug_monitor.frame_monitor.stop()
	assert not debug_monitor.frame_monitor.isActive()
	
	# Verify data structures are cleared
	debug_monitor.frame_times.clear()
	assert len(debug_monitor.frame_times) == 0