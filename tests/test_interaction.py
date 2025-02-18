import pytest
from albumexplore.visualization.interaction import InteractionHandler
from albumexplore.visualization.state import StateManager, ViewType

@pytest.fixture
def state_manager():
	return StateManager()

@pytest.fixture
def interaction_handler(state_manager):
	return InteractionHandler(state_manager)

def test_zoom_without_center(interaction_handler):
	# Test zoom in
	result = interaction_handler.handle_zoom(0.5)  # Zoom in by 50%
	assert result["zoom_level"] == 1.5  # Default zoom is 1.0
	
	# Reset zoom level
	interaction_handler.state_manager.update_zoom(1.0)
	
	# Test zoom out
	result = interaction_handler.handle_zoom(-0.5)  # Zoom out by 50%
	assert result["zoom_level"] == 0.5  # 50% of original
	
	# Reset zoom level
	interaction_handler.state_manager.update_zoom(1.0)
	
	# Test zoom limits
	result = interaction_handler.handle_zoom(10.0)  # Try to zoom in too much
	assert result["zoom_level"] == 5.0  # Should clamp to max
	
	# Reset zoom level
	interaction_handler.state_manager.update_zoom(1.0)
	
	# Test minimum zoom
	result = interaction_handler.handle_zoom(-0.95)  # Zoom out by 95%
	assert result["zoom_level"] == 0.1  # Should clamp to min

def test_zoom_with_center(interaction_handler):
	center = {"x": 100.0, "y": 100.0}
	initial_pos = {"x": 0.0, "y": 0.0}
	
	# Set initial position
	interaction_handler.state_manager.update_position(0.0, 0.0)
	
	# Zoom in with center point
	result = interaction_handler.handle_zoom(1.0, center)  # Double zoom
	new_pos = result["position"]
	
	# Position should move to maintain center point
	assert new_pos["x"] < initial_pos["x"]  # Should move left
	assert new_pos["y"] < initial_pos["y"]  # Should move up

def test_drag_interaction(interaction_handler):
	# Start drag
	start_pos = {"x": 0.0, "y": 0.0}
	interaction_handler.start_drag(start_pos)
	assert interaction_handler.drag_start == start_pos
	
	# Update drag
	new_pos = {"x": 50.0, "y": 30.0}
	result = interaction_handler.update_drag(new_pos)
	assert result["position"]["x"] == 50.0
	assert result["position"]["y"] == 30.0
	
	# End drag
	interaction_handler.end_drag()
	assert interaction_handler.drag_start is None

def test_click_selection(interaction_handler):
	# Mock _find_node_at_position to return a node ID
	interaction_handler._find_node_at_position = lambda pos: "node1" if pos["x"] < 100 else None
	
	# Single select
	result = interaction_handler.handle_click({"x": 50, "y": 50})
	assert result["selected_ids"] == ["node1"]
	
	# Click empty space should clear selection
	result = interaction_handler.handle_click({"x": 150, "y": 150})
	assert result["selected_ids"] == []

def test_multi_select(interaction_handler):
	# Mock _find_node_at_position
	nodes = {
		(50, 50): "node1",
		(100, 100): "node2"
	}
	interaction_handler._find_node_at_position = lambda pos: nodes.get((pos["x"], pos["y"]))
	
	# Select first node
	result = interaction_handler.handle_click({"x": 50, "y": 50}, multi_select=True)
	assert set(result["selected_ids"]) == {"node1"}
	
	# Add second node
	result = interaction_handler.handle_click({"x": 100, "y": 100}, multi_select=True)
	assert set(result["selected_ids"]) == {"node1", "node2"}
	
	# Deselect first node
	result = interaction_handler.handle_click({"x": 50, "y": 50}, multi_select=True)
	assert set(result["selected_ids"]) == {"node2"}