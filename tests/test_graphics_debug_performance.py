import pytest
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtWidgets import QWidget
from PyQt6.QtTest import QTest
from albumexplore.gui.graphics_debug import GraphicsDebugMonitor
import time
import json

class MockWidget(QWidget):
	def __init__(self):
		super().__init__()
		self.node_items = {}
		self.transform = lambda: type('Transform', (), {'m11': lambda: 1.0})()

@pytest.fixture
def debug_monitor(qtbot):
	widget = MockWidget()
	qtbot.addWidget(widget)
	monitor = GraphicsDebugMonitor(widget)
	return monitor, widget

def test_performance_monitoring(debug_monitor, caplog):
	"""Test performance monitoring and logging."""
	monitor, widget = debug_monitor
	
	# Simulate multiple frame renders
	for _ in range(5):
		monitor.log_paint_event(widget, "paint")
		time.sleep(0.05)  # Simulate slow frame
	
	# Check performance report
	report = monitor.get_performance_report()
	assert "Performance Report" in report
	assert "Average FPS" in report
	assert "Frame Time" in report
	assert "Memory Usage" in report

def test_performance_snapshot_data(debug_monitor):
	"""Test performance snapshot data collection."""
	monitor, widget = debug_monitor
	
	# Simulate frame render
	monitor.log_paint_event(widget, "paint")
	
	# Verify snapshot data in performance debugger
	assert len(monitor.perf_debugger.snapshots) > 0
	snapshot = list(monitor.perf_debugger.snapshots)[-1]
	assert snapshot.frame_time > 0
	assert snapshot.memory_usage > 0

def test_low_fps_warning(debug_monitor, caplog):
	"""Test low FPS detection and warning."""
	monitor, widget = debug_monitor
	
	# Simulate slow frames
	for _ in range(3):
		monitor.log_paint_event(widget, "paint")
		time.sleep(0.1)  # Very slow frame
	
	# Force frame rate check
	monitor._check_frame_rate()
	
	# Verify warnings
	assert any("low frame rate" in record.message.lower() 
			  for record in caplog.records)
	assert any("fps" in record.message.lower() 
			  for record in caplog.records)

def test_memory_tracking(debug_monitor):
	"""Test memory usage tracking."""
	monitor, widget = debug_monitor
	
	# Simulate activity
	monitor.log_paint_event(widget, "paint")
	
	# Get performance report
	report = monitor.get_performance_report()
	
	# Verify memory information
	assert "Memory Usage" in report
	assert "MB" in report

def test_combined_performance_issues(debug_monitor, caplog):
	"""Test detection of combined performance issues."""
	monitor, widget = debug_monitor
	
	# Simulate multiple issues
	# 1. Slow frames
	monitor.log_paint_event(widget, "paint")
	time.sleep(0.05)
	
	# 2. Low visibility
	monitor.log_view_update(widget, 5, 100)
	
	# 3. Buffer issues
	monitor.log_buffer_state(widget, False)
	
	# Verify comprehensive logging
	assert any("frame rate" in record.message.lower() 
			  for record in caplog.records)
	assert any("visibility" in record.message.lower() 
			  for record in caplog.records)
	assert any("buffer" in record.message.lower() 
			  for record in caplog.records)

def test_performance_data_persistence(debug_monitor, tmp_path):
	"""Test performance data logging to file."""
	monitor, widget = debug_monitor
	
	# Simulate activity
	monitor.log_paint_event(widget, "paint")
	
	# Verify log file contains performance data
	log_file = monitor.perf_debugger.log_path
	with open(log_file, 'r') as f:
		log_content = f.read()
		assert "timestamp" in log_content
		assert "fps" in log_content
		assert "memory_usage" in log_content