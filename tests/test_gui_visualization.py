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

def test_rapid_view_updates(qtbot, sample_data):
	"""Test view stability during rapid data updates."""
	nodes, edges = sample_data
	view = NetworkView()
	view.resize(800, 600)
	
	# Simulate rapid updates
	for _ in range(10):
		view.update_data(nodes, edges)
		QTest.qWait(50)  # Short delay between updates
		
	assert view.isVisible()
	assert not view.isUpdating()

def test_concurrent_interactions(qtbot, sample_data):
	"""Test view stability during concurrent user interactions."""
	nodes, edges = sample_data
	view = NetworkView()
	view.resize(800, 600)
	view.update_data(nodes, edges)
	
	# Simulate concurrent zoom and pan
	center = view.viewport().rect().center()
	QTest.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=center)
	QTest.mouseMove(view.viewport(), center + QPoint(100, 100))
	QTest.keyClick(view, Qt.Key.Key_Plus, Qt.KeyboardModifier.ControlModifier)
	QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=center + QPoint(100, 100))
	
	assert view.transform().isValid()

def test_repaint_consistency(qtbot, sample_data):
	"""Test view consistency during repaints."""
	nodes, edges = sample_data
	view = NetworkView()
	view.resize(800, 600)
	view.update_data(nodes, edges)
	
	# Force multiple repaints
	initial_positions = {node.id: (node.data['x'], node.data['y']) for node in view.nodes}
	for _ in range(5):
		view.repaint()
		QTest.qWait(100)
	
	# Verify node positions remained stable
	final_positions = {node.id: (node.data['x'], node.data['y']) for node in view.nodes}
	assert initial_positions == final_positions

def test_edge_case_rendering(qtbot, sample_data):
	"""Test rendering edge cases."""
	nodes, edges = sample_data
	view = NetworkView()
	
	# Test minimal size
	view.resize(50, 50)
	view.update_data(nodes, edges)
	assert view.isVisible()
	
	# Test very large size
	view.resize(3000, 2000)
	assert view.isVisible()
	
	# Test with empty data
	view.update_data([], [])
	assert view.isVisible()
	
	# Test with single node
	view.update_data([nodes[0]], [])
	assert view.isVisible()

def test_high_load_performance(qtbot):
	"""Test view performance under high load."""
	# Create large dataset
	nodes = [
		VisualNode(id=f"node{i}", label=f"Node {i}", 
				  size=1.0, color="#808080", shape="circle",
				  data={"x": i*10, "y": i*10})
		for i in range(1000)
	]
	edges = [
		VisualEdge(source=f"node{i}", target=f"node{i+1}", 
				  weight=1.0, color="#666666", thickness=1.0)
		for i in range(999)
	]
	
	view = NetworkView()
	view.resize(800, 600)
	
	# Measure update time
	with qtbot.waitSignal(view.updateFinished, timeout=5000):
		view.update_data(nodes, edges)
	
	assert view.isVisible()
	assert len(view.nodes) == 1000

def test_chord_view_stability(qtbot, sample_data):
    """Test ChordView stability and edge cases."""
    nodes, edges = sample_data
    view = ChordView()
    view.resize(800, 600)
    
    # Test rapid updates
    for _ in range(5):
        view.update_data(nodes, edges)
        QTest.qWait(50)
    
    # Test edge cases
    view.update_data([], [])  # Empty data
    view.update_data([nodes[0]], [])  # Single node
    view.resize(50, 50)  # Minimal size
    view.resize(3000, 2000)  # Large size
    
    assert view.isVisible()
    assert not view.isUpdating()

def test_arc_view_stability(qtbot, sample_data):
    """Test ArcView stability and edge cases."""
    nodes, edges = sample_data
    view = ArcView()
    view.resize(800, 600)
    
    # Test rapid updates
    for _ in range(5):
        view.update_data(nodes, edges)
        QTest.qWait(50)
    
    # Test edge cases
    view.update_data([], [])  # Empty data
    view.update_data([nodes[0]], [])  # Single node
    view.resize(50, 50)  # Minimal size
    view.resize(3000, 2000)  # Large size
    
    assert view.isVisible()
    assert not view.isUpdating()

def test_view_interaction_consistency(qtbot, sample_data):
    """Test consistent interaction behavior across all view types."""
    nodes, edges = sample_data
    views = [NetworkView(), ChordView(), ArcView()]
    
    for view in views:
        view.resize(800, 600)
        view.update_data(nodes, edges)
        
        # Test zoom interaction
        center = view.viewport().rect().center()
        QTest.keyClick(view, Qt.Key.Key_Plus, Qt.KeyboardModifier.ControlModifier)
        
        # Test selection
        QTest.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=center)
        
        # Verify view state
        assert view.transform().isValid()
        assert view.isVisible()