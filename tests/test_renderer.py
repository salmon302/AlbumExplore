import pytest
from albumexplore.visualization.models import VisualNode, VisualEdge
from albumexplore.visualization.state import ViewState, ViewType
from albumexplore.visualization.renderer import create_renderer, TableRenderer, NetworkRenderer

@pytest.fixture
def responsive_state():
	state = ViewState(ViewType.TABLE)
	state.selected_ids.add("album1")
	state.zoom_level = 1.5
	state.position = {"x": 100.0, "y": 50.0}
	state.filters = {"year": 2020}
	state.viewport_width = 800.0
	state.viewport_height = 600.0
	# Add responsive settings
	state.view_specific = {
		"show_labels": True,
		"node_size_scale": 0.8,
		"edge_thickness_scale": 0.7,
		"columns": ["artist", "title"]
	}
	return state

@pytest.fixture
def sample_nodes():
	return [
		VisualNode(
			id="album1",
			label="Artist1 - Album1",
			size=2.0,
			color="#808080",
			shape="circle",
			data={
				"type": "row",
				"artist": "Artist1",
				"title": "Album1",
				"year": 2020,
				"tags": ["metal", "prog"]
			}
		),
		VisualNode(
			id="album2",
			label="Artist2 - Album2",
			size=1.0,
			color="#808080",
			shape="square",
			data={
				"type": "row",
				"artist": "Artist2",
				"title": "Album2",
				"year": 2021,
				"tags": ["rock"]
			}
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

@pytest.fixture
def view_state():
	state = ViewState(ViewType.TABLE)
	state.selected_ids.add("album1")
	state.zoom_level = 1.5
	state.position = {"x": 100.0, "y": 50.0}
	state.filters = {"year": 2020}
	return state

def test_create_renderer():
	table_renderer = create_renderer(ViewType.TABLE)
	assert isinstance(table_renderer, TableRenderer)
	
	network_renderer = create_renderer(ViewType.NETWORK)
	assert isinstance(network_renderer, NetworkRenderer)
	
	with pytest.raises(ValueError):
		create_renderer("INVALID_VIEW_TYPE")  # Test with invalid view type

def test_table_renderer(sample_nodes, sample_edges, view_state):
	renderer = create_renderer(ViewType.TABLE)
	result = renderer.render(sample_nodes, sample_edges, view_state)
	
	assert result["type"] == "table"
	assert len(result["rows"]) == 2
	
	# Check first row
	row1 = result["rows"][0]
	assert row1["id"] == "album1"
	assert row1["artist"] == "Artist1"
	assert row1["selected"] is True
	assert len(row1["tags"]) == 2
	
	# Check filters
	assert result["filters"] == {"year": 2020}

def test_network_renderer(sample_nodes, sample_edges, view_state):
	view_state.view_type = ViewType.NETWORK
	renderer = create_renderer(ViewType.NETWORK)
	result = renderer.render(sample_nodes, sample_edges, view_state)
	
	assert result["type"] == "network"
	assert len(result["nodes"]) == 2
	assert len(result["edges"]) == 1
	
	# Check node rendering
	node1 = next(n for n in result["nodes"] if n["id"] == "album1")
	assert node1["size"] == 2.0 * view_state.zoom_level
	assert node1["selected"] is True
	assert node1["x"] == view_state.position["x"]
	assert node1["y"] == view_state.position["y"]
	
	# Check edge rendering
	edge = result["edges"][0]
	assert edge["source"] == "album1"
	assert edge["target"] == "album2"
	assert edge["weight"] == 1.0

def test_responsive_table_renderer(sample_nodes, sample_edges, responsive_state):
	renderer = create_renderer(ViewType.TABLE)
	result = renderer.render(sample_nodes, sample_edges, responsive_state)
	
	assert result["type"] == "table"
	assert "columns" in result
	assert len(result["columns"]) == 2
	assert "artist" in result["columns"]
	assert "title" in result["columns"]

def test_responsive_network_renderer(sample_nodes, sample_edges, responsive_state):
	responsive_state.view_type = ViewType.NETWORK
	renderer = create_renderer(ViewType.NETWORK)
	result = renderer.render(sample_nodes, sample_edges, responsive_state)
	
	# Check node scaling
	node = next(n for n in result["nodes"] if n["id"] == "album1")
	expected_size = 2.0 * responsive_state.zoom_level * responsive_state.view_specific["node_size_scale"]
	assert node["size"] == expected_size
	
	# Check edge scaling
	edge = result["edges"][0]
	expected_thickness = 0.5 * responsive_state.zoom_level * responsive_state.view_specific["edge_thickness_scale"]
	assert edge["thickness"] == expected_thickness

def test_responsive_label_visibility(sample_nodes, sample_edges, responsive_state):
	# Test with labels hidden
	responsive_state.view_specific["show_labels"] = False
	renderer = create_renderer(ViewType.NETWORK)
	result = renderer.render(sample_nodes, sample_edges, responsive_state)
	
	node = next(n for n in result["nodes"] if n["id"] == "album1")
	assert node["label"] == ""
	
	# Test with labels shown
	responsive_state.view_specific["show_labels"] = True
	result = renderer.render(sample_nodes, sample_edges, responsive_state)
	node = next(n for n in result["nodes"] if n["id"] == "album1")
	assert node["label"] != ""