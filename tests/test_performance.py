import pytest
import time
import cProfile
import pstats
from io import StringIO
import psutil
import os
from typing import Callable, Any
from unittest.mock import Mock, MagicMock
from albumexplore.visualization.view_manager import ViewManager
from albumexplore.visualization.state import ViewType
from albumexplore.visualization.data_interface import DataInterface
from .test_data_generator import create_test_dataset

def profile_function(func: Callable[[], Any]) -> pstats.Stats:
	"""Profile a function and return stats."""
	profiler = cProfile.Profile()
	profiler.enable()
	func()
	profiler.disable()
	return pstats.Stats(profiler)

def get_memory_usage() -> float:
	"""Get current memory usage in MB."""
	process = psutil.Process(os.getpid())
	return process.memory_info().rss / 1024 / 1024

class MockSession:
	def __init__(self, test_data):
		self.test_data = test_data
		
	def query(self, model):
		return MagicMock(all=lambda: self.test_data)

@pytest.fixture
def test_data():
	nodes, edges = create_test_dataset(1000, edge_density=0.1)
	small_nodes, small_edges = create_test_dataset(100, edge_density=0.2)
	return {
		'nodes': nodes,
		'edges': edges,
		'small_nodes': small_nodes,
		'small_edges': small_edges
	}

@pytest.fixture
def view_manager(test_data):
	mock_session = MockSession(test_data['nodes'])
	data_interface = DataInterface(mock_session)
	manager = ViewManager(data_interface)
	manager.nodes = test_data['nodes']
	manager.edges = test_data['edges']
	return manager

def test_layout_performance(view_manager, test_data):
	"""Test force-directed layout performance."""
	# Test with small dataset first
	view_manager.nodes = test_data['small_nodes']
	view_manager.edges = test_data['small_edges']
	
	start_time = time.time()
	view_manager._apply_layout()
	layout_time = time.time() - start_time
	
	assert layout_time < 2.0  # Layout should complete in under 2 seconds
	
	# Profile with larger dataset
	view_manager.nodes = test_data['nodes']
	view_manager.edges = test_data['edges']
	stats = profile_function(view_manager._apply_layout)
	
	stream = StringIO()
	stats.sort_stats('cumulative').print_stats(10)
	print(f"Layout Performance:\n{stream.getvalue()}")

def test_rendering_performance(view_manager):
	"""Test rendering performance for different view types."""
	for view_type in [ViewType.NETWORK, ViewType.ARC, ViewType.CHORD]:
		view_manager.switch_view(view_type)
		
		start_mem = get_memory_usage()
		start_time = time.time()
		
		view_manager.render_current_view()
		
		render_time = time.time() - start_time
		mem_used = get_memory_usage() - start_mem
		
		assert render_time < 3.0  # Rendering should take < 3 seconds
		assert mem_used < 200  # Should use < 200MB additional memory
		
		print(f"{view_type.name} Rendering: {render_time:.2f}s, {mem_used:.1f}MB")

def test_interaction_performance(view_manager, test_data):
	"""Test interaction handler performance."""
	# Test node selection performance
	start_time = time.time()
	for _ in range(100):
		view_manager.select_nodes({test_data['nodes'][0].id})
	select_time = (time.time() - start_time) / 100
	
	assert select_time < 0.02  # Selection should be < 20ms
	
	# Test viewport update performance
	start_time = time.time()
	for _ in range(100):
		view_manager.update_dimensions(800, 600)
	update_time = (time.time() - start_time) / 100
	
	assert update_time < 0.02  # Update should be < 20ms

def test_responsive_performance(view_manager):
	"""Test responsive layout adjustments performance."""
	# Test different screen sizes
	screen_sizes = [(800, 600), (1920, 1080), (375, 812)]
	
	for width, height in screen_sizes:
		start_time = time.time()
		view_manager.update_dimensions(width, height)
		update_time = time.time() - start_time
		
		assert update_time < 0.2  # Should update in under 200ms
		print(f"Responsive update {width}x{height}: {update_time:.3f}s")

