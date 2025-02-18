import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtTest import QTest
from albumexplore.visualization.views.chord_view import ChordView
from albumexplore.visualization.views.arc_view import ArcView
from albumexplore.visualization.views.network_view import NetworkView
from albumexplore.visualization.models import VisualNode, VisualEdge
from albumexplore.visualization.state import ViewState, ViewType

@pytest.fixture
def sample_data():
	nodes = [
		VisualNode(id=f"node{i}", label=f"Node {i}", 
				  size=1.0, color="#808080", shape="circle",
				  data={"x": i*100, "y": i*100})
		for i in range(3)
	]
	edges = [
		VisualEdge(source="node0", target="node1", 
				  weight=1.0, color="#666666", thickness=2.0),
		VisualEdge(source="node1", target="node2", 
				  weight=0.5, color="#666666", thickness=1.0)
	]
	return nodes, edges

def test_chord_view_rendering(qtbot, sample_data):
	nodes, edges = sample_data
	view = ChordView()
	view.resize(800, 600)
	view.update_data(nodes, edges)
	
	# Verify view properties
	assert view.width() == 800
	assert view.height() == 600
	assert len(view.nodes) == len(nodes)
	assert len(view.edges) == len(edges)

def test_arc_view_rendering(qtbot, sample_data):
	nodes, edges = sample_data
	view = ArcView()
	view.resize(800, 600)
	view.update_data(nodes, edges)
	
	# Verify view properties
	assert view.width() == 800
	assert view.height() == 600
	assert len(view.nodes) == len(nodes)
	assert len(view.edges) == len(edges)

def test_network_view_rendering(qtbot, sample_data):
	nodes, edges = sample_data
	view = NetworkView()
	view.resize(800, 600)
	view.update_data(nodes, edges)
	
	# Verify view properties
	assert view.width() == 800
	assert view.height() == 600
	assert len(view.nodes) == len(nodes)
	assert len(view.edges) == len(edges)
	
	# Test layout initialization
	view.start_layout()
	assert view.layout_timer.isActive()

def test_network_view_interactions(qtbot, sample_data):
    nodes, edges = sample_data
    view = NetworkView()
    view.resize(800, 600)
    view.update_data(nodes, edges)
    
    # Test zoom interaction
    initial_scale = view.transform().m11()
    QTest.keyClick(view, Qt.Key.Key_Plus, Qt.KeyboardModifier.ControlModifier)
    assert view.transform().m11() > initial_scale
    
    # Test node selection
    center = QPoint(400, 300)
    QTest.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=center)
    assert len(view.selected_nodes) > 0

def test_view_state_persistence(qtbot, sample_data):
    nodes, edges = sample_data
    view = NetworkView()
    view.update_data(nodes, edges)
    
    # Test state saving and loading
    view.zoom_level = 1.5
    state = view.save_state()
    view.zoom_level = 1.0
    view.restore_state(state)
    assert view.zoom_level == 1.5

def test_resize_behavior(qtbot, sample_data):
    nodes, edges = sample_data
    view = NetworkView()
    view.update_data(nodes, edges)
    
    # Test various resize scenarios
    initial_pos = {node.id: (node.data['x'], node.data['y']) 
                  for node in view.nodes}
    
    view.resize(400, 300)  # Small size
    view.resize(1200, 900)  # Large size
    
    # Verify nodes are still within bounds
    for node in view.nodes:
        assert 0 <= node.data['x'] <= view.width()
        assert 0 <= node.data['y'] <= view.height()

def test_animation_transitions(qtbot, sample_data):
    nodes, edges = sample_data
    view = NetworkView()
    view.update_data(nodes, edges)
    
    # Test layout animation
    view.start_layout()
    assert view.layout_timer.isActive()
    
    # Force animation step
    view.layout_timer.timeout.emit()
    assert view.is_animating()