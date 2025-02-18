import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QPen, QColor
from PyQt6.QtWidgets import QApplication
from albumexplore.visualization.models import VisualNode, VisualEdge
from albumexplore.visualization.state import ViewState, ViewType
from albumexplore.visualization.views.network_view import NetworkView

@pytest.fixture
def sample_nodes():
	return [
		VisualNode(
			id="album1",
			label="Artist1 - Album1",
			size=2.0,
			color="#808080",
			shape="circle",
			data={"x": 100, "y": 100, "vx": 0, "vy": 0, "label": "Album1"}
		),
		VisualNode(
			id="album2",
			label="Artist2 - Album2",
			size=1.5,
			color="#808080",
			shape="circle",
			data={"x": 300, "y": 100, "vx": 0, "vy": 0, "label": "Album2"}
		)
	]

@pytest.fixture
def sample_edges():
	return [
		VisualEdge(
			source="album1",
			target="album2",
			weight=1.0,
			color="#666666",
			thickness=0.5,
			data={"shared_tags": ["rock"]}
		)
	]

def test_edge_rendering(qtbot, sample_nodes, sample_edges):
	view = NetworkView()
	view.resize(800, 600)
	
	# Create test edges with varying weights
	test_edges = [
		VisualEdge(
			source="album1",
			target="album2",
			weight=3.0,  # Higher weight
			color="#444444",
			thickness=6.0,  # Increased thickness
			data={"shared_tags": ["rock", "metal", "progressive"]}
		)
	]
	
	view.update_data(sample_nodes, test_edges)
	view.update_layout()
	
	# Verify edge properties
	edge = view.edges[0]
	assert edge.thickness >= 6.0, "Edge thickness not properly set"
	assert edge.color == "#444444", "Edge color not properly set"
	assert edge.weight == 3.0, "Edge weight not properly set"
	
	# Verify node positions for edge rendering
	source = next(n for n in view.nodes if n.id == edge.source)
	target = next(n for n in view.nodes if n.id == edge.target)
	
	assert source is not None and target is not None, "Edge nodes not found"
	assert all(k in source.data for k in ['x', 'y']), "Source coordinates missing"
	assert all(k in target.data for k in ['x', 'y']), "Target coordinates missing"
	
	# Verify coordinates are within view bounds
	assert all(abs(source.data[k]) <= view.width()/2 for k in ['x', 'y']), "Source position out of bounds"
	assert all(abs(target.data[k]) <= view.height()/2 for k in ['y', 'y']), "Target position out of bounds"

def test_label_rendering(qtbot, sample_nodes):
	view = NetworkView()
	view.resize(800, 600)
	view.update_data(sample_nodes, [])
	
	# Verify label data
	for node in view.nodes:
		assert 'label' in node.data, f"Label missing for node {node.id}"
		assert node.data['label'], f"Empty label for node {node.id}"
		
		# Verify label position relative to node
		x = node.data.get('x', 0)
		y = node.data.get('y', 0)
		assert abs(x) <= view.width()/2, f"Node {node.id} X position out of bounds"
		assert abs(y) <= view.height()/2, f"Node {node.id} Y position out of bounds"

def test_force_layout_stability(qtbot, sample_nodes, sample_edges):
	view = NetworkView()
	view.resize(800, 600)
	view.update_data(sample_nodes, sample_edges)
	
	# Run multiple layout iterations
	initial_positions = [(n.data['x'], n.data['y']) for n in view.nodes]
	
	for _ in range(10):
		view.update_layout()
	
	final_positions = [(n.data['x'], n.data['y']) for n in view.nodes]
	
	# Verify nodes have moved but remained within bounds
	for i, (init_pos, final_pos) in enumerate(zip(initial_positions, final_positions)):
		assert init_pos != final_pos, f"Node {i} position unchanged after layout"
		assert abs(final_pos[0]) <= view.width()/2, f"Node {i} X out of bounds"
		assert abs(final_pos[1]) <= view.height()/2, f"Node {i} Y out of bounds"

def test_node_selection(qtbot, sample_nodes):
	view = NetworkView()
	view.resize(800, 600)
	view.update_data(sample_nodes, [])
	
	# Test node selection
	node = view.nodes[0]
	x = int(node.data['x'] + view.width()/2)  # Convert to integer widget coordinates
	y = int(node.data['y'] + view.height()/2)
	
	from PyQt6.QtCore import QPoint
	qtbot.mouseClick(view, Qt.MouseButton.LeftButton, pos=QPoint(x, y))
	assert node.id in view.selected_ids, "Node not selected after click"