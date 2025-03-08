import pytest
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtTest import QTest
from albumexplore.gui.views import (
	create_view, ViewType, TableViewWidget,
	NetworkViewWidget, ChordViewWidget, ArcViewWidget
)
from albumexplore.visualization.models import VisualNode, VisualEdge

@pytest.fixture
def sample_data():
	"""Create sample visualization data."""
	nodes = [
		VisualNode(id=f"node{i}", label=f"Node {i}", 
				  size=10.0, color="#808080", shape="circle",
				  data={"x": i*50, "y": i*50, "type": "row",
						"artist": f"Artist {i}", "title": f"Album {i}",
						"year": 2020+i, "tags": [f"tag{i}"]})
		for i in range(5)
	]
	edges = [
		VisualEdge(source=f"node{i}", target=f"node{i+1}", 
				  weight=1.0, color="#666666", thickness=1.0)
		for i in range(4)
	]
	return nodes, edges

def test_view_creation():
	"""Test view creation for all view types."""
	for view_type in ViewType:
		view = create_view(view_type)
		assert view is not None
		assert isinstance(view, (TableViewWidget, NetworkViewWidget, 
							   ChordViewWidget, ArcViewWidget))

def test_table_to_network_transition(qtbot, sample_data):
	"""Test transition from table to network view."""
	nodes, edges = sample_data
	
	# Setup views
	table_view = create_view(ViewType.TABLE)
	network_view = create_view(ViewType.NETWORK)
	
	# Initial data
	table_view.update_data(nodes, edges)
	
	# Select items in table
	table_view.table.selectRow(0)
	selected_ids = table_view.selected_ids
	
	# Transition to network
	transition_data = {
		'transition': {'type': 'morph'},
		'shared_selections': list(selected_ids)
	}
	network_view.update_data(nodes, edges)
	network_view.apply_transition(transition_data)
	
	# Verify selection preservation
	assert network_view.selected_ids == selected_ids

def test_network_to_chord_transition(qtbot, sample_data):
	"""Test transition from network to chord view."""
	nodes, edges = sample_data
	
	# Setup views
	network_view = create_view(ViewType.NETWORK)
	chord_view = create_view(ViewType.CHORD)
	
	# Initial data and selection
	network_view.update_data(nodes, edges)
	network_item = next(iter(network_view.node_items.values()))
	network_item.setSelected(True)
	selected_ids = network_view.selected_ids
	
	# Transition to chord
	transition_data = {
		'transition': {'type': 'fade'},
		'shared_selections': list(selected_ids)
	}
	chord_view.update_data(nodes, edges)
	chord_view.apply_transition(transition_data)
	
	# Verify selection preservation
	assert chord_view.selected_ids == selected_ids

def test_view_resize_handling(qtbot, sample_data):
	"""Test view handling of resize events."""
	nodes, edges = sample_data
	views = [
		create_view(view_type)
		for view_type in ViewType
	]
	
	for view in views:
		view.update_data(nodes, edges)
		
		# Test various sizes
		sizes = [(300, 200), (800, 600), (1200, 900)]
		for width, height in sizes:
			view.resize(width, height)
			qtbot.wait(100)  # Allow for resize processing
			
			# Verify view remains responsive
			assert view.isVisible()
			assert view.width() == width
			assert view.height() == height

def test_edge_case_data_handling(qtbot):
	"""Test handling of edge case data scenarios."""
	views = [create_view(view_type) for view_type in ViewType]
	
	test_cases = [
		([], []),  # Empty data
		([VisualNode(id="single", label="Single", size=10.0, 
					color="#808080", shape="circle", data={})], []),  # Single node
		([], [VisualEdge(source="nonexistent1", target="nonexistent2",
						weight=1.0, color="#666666", thickness=1.0)])  # Invalid edges
	]
	
	for view in views:
		for nodes, edges in test_cases:
			view.update_data(nodes, edges)
			assert view.isVisible()
			
			# Test interaction still works
			if isinstance(view, (NetworkViewWidget, ChordViewWidget, ArcViewWidget)):
				center = view.view.viewport().rect().center()
				QTest.mouseClick(view.view.viewport(), Qt.MouseButton.LeftButton, pos=center)

def test_selection_sync(qtbot, sample_data):
	"""Test selection synchronization between views."""
	nodes, edges = sample_data
	views = [create_view(view_type) for view_type in ViewType]
	
	# Initialize all views
	for view in views:
		view.update_data(nodes, edges)
	
	# Test selection propagation
	test_id = nodes[0].id
	for source_view in views:
		# Make selection in source view
		if isinstance(source_view, TableViewWidget):
			source_view.table.selectRow(0)
		else:
			source_view.node_items[test_id].setSelected(True)
		
		selected_ids = source_view.selected_ids
		
		# Verify selection in other views
		for target_view in views:
			if target_view != source_view:
				transition_data = {
					'shared_selections': list(selected_ids)
				}
				target_view.apply_transition(transition_data)
				assert test_id in target_view.selected_ids