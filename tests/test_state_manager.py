import pytest
from albumexplore.visualization.state import StateManager, ViewType, ViewState

@pytest.fixture
def state_manager():
	return StateManager()

def test_initial_state(state_manager):
	assert state_manager.current_view.view_type == ViewType.TABLE
	assert len(state_manager.view_history) == 0
	assert state_manager.current_view.zoom_level == 1.0
	assert state_manager.current_view.position == {"x": 0.0, "y": 0.0}
	assert state_manager.current_view.viewport_width == 800.0
	assert state_manager.current_view.viewport_height == 600.0
	assert isinstance(state_manager.current_view.view_specific, dict)

def test_viewport_management(state_manager):
	# Test viewport update
	state_manager.update_viewport(1024.0, 768.0)
	assert state_manager.current_view.viewport_width == 1024.0
	assert state_manager.current_view.viewport_height == 768.0
	
	# Viewport should persist through view switches
	state_manager.switch_view(ViewType.NETWORK)
	assert state_manager.current_view.viewport_width == 1024.0
	assert state_manager.current_view.viewport_height == 768.0

def test_view_specific_state(state_manager):
	# Test setting view-specific state
	state_manager.set_view_specific("layout_type", "force")
	assert state_manager.get_view_specific("layout_type") == "force"
	
	# Test default value for missing key
	assert state_manager.get_view_specific("missing", "default") == "default"
	
	# View-specific state should reset on view switch
	state_manager.switch_view(ViewType.CHORD)
	assert state_manager.get_view_specific("layout_type") is None

def test_state_persistence(state_manager):
	# Set up initial state
	state_manager.update_viewport(1024.0, 768.0)
	state_manager.set_view_specific("layout_type", "force")
	state_manager.update_filters({"year": 2020})
	
	# Switch view and verify state persistence
	state_manager.switch_view(ViewType.NETWORK)
	assert state_manager.current_view.viewport_width == 1024.0
	assert state_manager.current_view.viewport_height == 768.0
	assert state_manager.current_view.filters == {"year": 2020}
	
	# Undo and verify state restoration
	state_manager.undo()
	assert state_manager.current_view.viewport_width == 1024.0
	assert state_manager.current_view.viewport_height == 768.0
	assert state_manager.current_view.filters == {"year": 2020}
	assert state_manager.get_view_specific("layout_type") == "force"

def test_switch_view(state_manager):
	# Switch to network view
	state_manager.switch_view(ViewType.NETWORK)
	assert state_manager.current_view.view_type == ViewType.NETWORK
	assert len(state_manager.view_history) == 1
	
	# Previous state should be saved
	previous_state = state_manager.view_history[0]
	assert previous_state.view_type == ViewType.TABLE

def test_update_filters(state_manager):
	initial_filters = {"year": 2020}
	state_manager.update_filters(initial_filters)
	assert state_manager.current_view.filters == initial_filters
	
	# Add more filters
	state_manager.update_filters({"genre": "metal"})
	assert state_manager.current_view.filters == {
		"year": 2020,
		"genre": "metal"
	}

def test_select_nodes(state_manager):
	# Select nodes
	nodes = {"node1", "node2"}
	state_manager.select_nodes(nodes)
	assert state_manager.current_view.selected_ids == nodes
	
	# Add more nodes
	state_manager.select_nodes({"node3"}, add=True)
	assert state_manager.current_view.selected_ids == {"node1", "node2", "node3"}
	
	# Replace selection
	new_nodes = {"node4"}
	state_manager.select_nodes(new_nodes, add=False)
	assert state_manager.current_view.selected_ids == new_nodes

def test_zoom_and_position(state_manager):
	# Test zoom limits
	state_manager.update_zoom(0.05)  # Should clamp to 0.1
	assert state_manager.current_view.zoom_level == 0.1
	
	state_manager.update_zoom(6.0)  # Should clamp to 5.0
	assert state_manager.current_view.zoom_level == 5.0
	
	# Test position update
	state_manager.update_position(100.0, -50.0)
	assert state_manager.current_view.position == {"x": 100.0, "y": -50.0}

def test_undo(state_manager):
	# Create some history
	state_manager.switch_view(ViewType.NETWORK)
	state_manager.update_filters({"year": 2020})
	state_manager.select_nodes({"node1"})
	
	# Undo changes
	assert state_manager.undo()  # Undo select_nodes
	assert len(state_manager.current_view.selected_ids) == 0
	
	assert state_manager.undo()  # Undo update_filters
	assert len(state_manager.current_view.filters) == 0
	
	assert state_manager.undo()  # Undo switch_view
	assert state_manager.current_view.view_type == ViewType.TABLE
	
	assert not state_manager.undo()  # No more history

def test_history_limit(state_manager):
	# Create more than max_history states
	for i in range(state_manager.max_history + 10):
		state_manager.update_filters({"index": i})
	
	assert len(state_manager.view_history) == state_manager.max_history

def test_table_sort_state(state_manager):
	# Test initial sort state
	sort_info = state_manager.get_table_sort()
	assert sort_info["column"] is None
	assert sort_info["direction"] == "asc"
	
	# Test setting sort state
	state_manager.set_table_sort("artist", "desc")  # Fixed: Added comma between arguments
	sort_info = state_manager.get_table_sort()
	assert sort_info["column"] == "artist"
	assert sort_info["direction"] == "desc"
	
	# Test sort state persistence through view switches
	state_manager.switch_view(ViewType.NETWORK)
	state_manager.switch_view(ViewType.TABLE)
	sort_info = state_manager.get_table_sort()
	assert sort_info["column"] == "artist"
	assert sort_info["direction"] == "desc"
	
	# Test sort state in view history
	state_manager.undo()  # Back to NETWORK view
	state_manager.undo()  # Back to TABLE view with original sort
	sort_info = state_manager.get_table_sort()
	assert sort_info["column"] == "artist"
	assert sort_info["direction"] == "desc"