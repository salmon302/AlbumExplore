import pytest
from unittest.mock import MagicMock, Mock, patch
from albumexplore.visualization.view_manager import ViewManager
from albumexplore.visualization.models import VisualNode, VisualEdge
from albumexplore.visualization.state import ViewType, ViewState
from albumexplore.visualization.responsive import ResponsiveManager
from albumexplore.visualization.optimizations import ViewOptimizer, Viewport
from albumexplore.visualization.layout import ForceDirectedLayout
from albumexplore.database import models

@pytest.fixture
def mock_data_interface():
	interface = MagicMock()
	
	# Mock album data with more complete initialization
	album1 = MagicMock(spec=models.Album)
	album1.id = "album1"
	album1.artist = "Artist1"
	album1.title = "Album1"
	album1.release_year = 2020
	album1.length = "LP"
	album1.tags = [MagicMock(name="metal"), MagicMock(name="prog")]
	
	album2 = MagicMock(spec=models.Album)
	album2.id = "album2"
	album2.artist = "Artist2"
	album2.title = "Album2"
	album2.release_year = 2021
	album2.length = "EP"
	album2.tags = [MagicMock(name="rock")]
	
	# Mock methods with proper return values
	interface.get_albums.return_value = [album1, album2]
	interface.get_album_connections.return_value = [
		{
			"source": "album1",
			"target": "album2",
			"weight": 1,
			"shared_tags": ["rock"]
		}
	]
	interface.get_tags.return_value = ["metal", "prog", "rock"]
	return interface

@pytest.fixture
def view_manager(mock_data_interface):
	manager = ViewManager(mock_data_interface)
	# Initialize with default view type
	manager.state_manager.switch_view(ViewType.TABLE)
	# Update data to populate nodes and edges
	manager.update_data()
	# Initialize viewport
	manager.update_dimensions(800, 600)
	return manager

def test_switch_view(view_manager):
	# Test switching to network view
	result = view_manager.switch_view(ViewType.NETWORK)
	assert result["type"] == "network"
	assert view_manager.state_manager.current_view.view_type == ViewType.NETWORK
	
	# Test switching to table view
	result = view_manager.switch_view(ViewType.TABLE)
	assert result["type"] == "table"
	assert view_manager.state_manager.current_view.view_type == ViewType.TABLE

def test_update_data_table_view(view_manager):
	view_manager.switch_view(ViewType.TABLE)
	view_manager.update_data()
	
	assert len(view_manager.nodes) == 2
	node = next(n for n in view_manager.nodes if n.data.get("type") == "row")
	assert "artist" in node.data
	assert "title" in node.data
	assert "year" in node.data
	assert "tags" in node.data


def test_update_data_network_view(view_manager):
	view_manager.switch_view(ViewType.NETWORK)
	view_manager.update_data()
	
	assert len(view_manager.nodes) == 2
	assert len(view_manager.edges) == 1
	
	# Check node properties
	node = next(n for n in view_manager.nodes if n.id == "album1")
	assert node.shape == "circle"  # LP album
	assert node.size == 2  # Two tags
	
	# Check edge properties
	edge = view_manager.edges[0]
	assert edge.source == "album1"
	assert edge.target == "album2"
	assert edge.weight == 1

def test_update_filters(view_manager):
	filters = {"year": 2020}
	result = view_manager.update_filters(filters)
	
	# Check that data interface was called with filters
	view_manager.data_interface.get_albums.assert_called_with(filters)
	
	# Check that state was updated
	assert view_manager.state_manager.current_view.filters == filters

def test_select_nodes(view_manager):
	node_ids = {"album1"}
	result = view_manager.select_nodes(node_ids)
	
	# Check that state was updated
	assert view_manager.state_manager.current_view.selected_ids == node_ids
	
	# Test adding to selection
	view_manager.select_nodes({"album2"}, add=True)
	assert view_manager.state_manager.current_view.selected_ids == {"album1", "album2"}

def test_update_dimensions(view_manager):
	# Test small screen update
	result = view_manager.update_dimensions(600, 800)
	assert view_manager.viewport.width == 600
	assert view_manager.viewport.height == 800
	assert "layout_adjustments" in result
	
	# Test large screen update
	result = view_manager.update_dimensions(1200, 800)
	assert view_manager.viewport.width == 1200
	assert view_manager.viewport.height == 800
	assert "container_dimensions" in result

@pytest.fixture
def sample_node():
	return VisualNode(
		id="test1",
		label="Test Node",
		size=10,
		color="#000",
		shape="circle",
		data={}
	)

@pytest.fixture
def sample_edge():
	return VisualEdge(
		source="test1",
		target="test2",
		weight=1.0,
		thickness=2.0,
		color="#000",
		data={}
	)

def test_responsive_rendering(view_manager, sample_node, sample_edge):
	view_manager.nodes = [sample_node]
	view_manager.edges = [sample_edge]

	# Test small screen rendering
	view_manager.update_dimensions(600, 800)
	result = view_manager.render_current_view()
	assert "layout_adjustments" in result
	
	# Switch to table view and test responsive columns
	view_manager.switch_view(ViewType.TABLE)
	result = view_manager.render_current_view()
	if "columns" in result:
		assert len(result["columns"]) < 4  # Reduced columns for small screen

def test_responsive_layout_adjustments(view_manager, sample_node):
	view_manager.nodes = [sample_node]
	
	# Test layout adjustments for small screen
	view_manager.update_dimensions(600, 800)
	adjusted_node = view_manager.nodes[0]
	assert adjusted_node.size < 10  # Size should be scaled down
	assert adjusted_node.label == ""  # Label should be hidden

	# Test layout adjustments for large screen
	view_manager.update_dimensions(1200, 800)
	adjusted_node = view_manager.nodes[0]
	assert adjusted_node.size == 10  # Size should be normal
	assert adjusted_node.label == "Test Node"  # Label should be visible

def test_table_sorting(view_manager):
    view_manager.switch_view(ViewType.TABLE)
    
    # Test initial sort state
    sort_info = view_manager.state_manager.get_table_sort()
    assert sort_info["column"] is None
    assert sort_info["direction"] == "asc"
    
    # Test sorting by artist ascending
    result = view_manager.set_table_sort("artist")
    assert len(result["rows"]) == 2
    assert result["rows"][0]["artist"] < result["rows"][1]["artist"]
    
    # Test sorting by artist descending
    result = view_manager.set_table_sort("artist", "desc")
    assert len(result["rows"]) == 2
    assert result["rows"][0]["artist"] > result["rows"][1]["artist"]
    
    # Test sorting by year
    result = view_manager.set_table_sort("year")
    assert len(result["rows"]) == 2
    assert result["rows"][0]["year"] < result["rows"][1]["year"]
    
    # Test invalid column
    result = view_manager.set_table_sort("invalid_column")
    sort_info = view_manager.state_manager.get_table_sort()
    assert sort_info["column"] != "invalid_column"

def test_table_sort_persistence(view_manager):
    view_manager.switch_view(ViewType.TABLE)
    
    # Set initial sort
    view_manager.set_table_sort("artist", "asc")
    
    # Update data and verify sort is maintained
    view_manager.update_data()
    sort_info = view_manager.state_manager.get_table_sort()
    assert sort_info["column"] == "artist"
    assert sort_info["direction"] == "asc"
    
    # Switch views and back, verify sort is maintained
    view_manager.switch_view(ViewType.NETWORK)
    view_manager.switch_view(ViewType.TABLE)
    sort_info = view_manager.state_manager.get_table_sort()
    assert sort_info["column"] == "artist"
    assert sort_info["direction"] == "asc"
