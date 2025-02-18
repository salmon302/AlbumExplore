import pytest
from albumexplore.visualization.models import VisualNode, VisualEdge
from albumexplore.visualization.state import ViewState, ViewType
from albumexplore.visualization.arc_renderer import ArcRenderer

@pytest.fixture
def sample_nodes():
	return [
		VisualNode(
			id="album1",
			label="Artist1 - Album1",
			size=2.0,
			color="#808080",
			shape="circle",
			data={"type": "album"}
		),
		VisualNode(
			id="album2",
			label="Artist2 - Album2",
			size=1.5,
			color="#808080",
			shape="circle",
			data={"type": "album"}
		),
		VisualNode(
			id="album3",
			label="Artist3 - Album3",
			size=1.0,
			color="#808080",
			shape="circle",
			data={"type": "album"}
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
		),
		VisualEdge(
			source="album2",
			target="album3",
			weight=0.5,
			color="#666666",
			thickness=0.25,
			data={"shared_tags": ["metal"]}
		)
	]

@pytest.fixture
def view_state():
	state = ViewState(ViewType.ARC)
	state.selected_ids.add("album1")
	state.zoom_level = 1.5
	state.position = {"x": 100.0, "y": 50.0}
	return state

def test_node_positioning(sample_nodes):
	renderer = ArcRenderer()
	positions = renderer._calculate_node_positions(sample_nodes, 1000.0)
	
	# Check that nodes are evenly spaced
	assert len(positions) == 3
	positions_list = list(positions.values())
	spacing = positions_list[1] - positions_list[0]
	assert pytest.approx(positions_list[2] - positions_list[1]) == spacing
	
	# Check that positions are within bounds
	assert all(0 < pos < 1000.0 for pos in positions.values())

def test_arc_calculation():
	renderer = ArcRenderer()
	points = renderer._calculate_arc(100.0, 300.0, 100.0)
	
	# Check number of points
	assert len(points) == 11  # 10 steps + 1
	
	# Check start and end points
	assert points[0][0] == pytest.approx(100.0)  # x1
	assert points[0][1] == pytest.approx(0.0)    # y1
	assert points[-1][0] == pytest.approx(300.0) # x2
	assert points[-1][1] == pytest.approx(0.0)   # y2
	
	# Check maximum height
	min_y = min(point[1] for point in points)
	assert min_y == pytest.approx(-100.0)  # Maximum height should match input

def test_arc_rendering(sample_nodes, sample_edges, view_state):
	renderer = ArcRenderer()
	result = renderer.render(sample_nodes, sample_edges, view_state)
	
	assert result["type"] == "arc"
	assert len(result["nodes"]) == 3
	assert len(result["arcs"]) == 2
	
	# Check node rendering
	node1 = next(n for n in result["nodes"] if n["id"] == "album1")
	assert node1["selected"] is True
	
	# Add debug information
	original_size = next(n.size for n in sample_nodes if n.id == "album1")
	print(f"Original node size: {original_size}")
	print(f"Zoom level: {view_state.zoom_level}")
	print(f"Expected size: {original_size * view_state.zoom_level}")
	print(f"Actual size: {node1['size']}")
	
	assert node1["size"] == 2.0 * view_state.zoom_level
	
	# Check arc rendering
	arc = result["arcs"][0]
	assert arc["source"] == "album1"
	assert arc["target"] == "album2"
	assert arc["weight"] == 1.0
	assert len(arc["path"]) > 0

def test_arc_connection_visibility(sample_nodes, sample_edges, view_state):
    renderer = ArcRenderer()
    result = renderer.render(sample_nodes, sample_edges, view_state)
    
    # Check arc visibility parameters
    arc = result["arcs"][0]
    assert arc["thickness"] >= 2  # Minimum thickness
    assert arc["weight"] > 0  # Weight affects visibility
    
    # Verify path points for proper curve
    path = arc["path"]
    assert len(path) >= 20  # Sufficient points for smooth curve
    start_point = path[0]
    end_point = path[-1]
    assert start_point[1] == end_point[1]  # Same y-coordinate at endpoints

def test_node_label_positioning(sample_nodes, view_state):
    renderer = ArcRenderer()
    result = renderer.render(sample_nodes, [], view_state)
    
    # Check node and label positioning
    node = result["nodes"][0]
    base_y = node["y"]
    size = node["size"]
    
    # Verify node size and position
    assert size > 0
    assert base_y > result["height"] * 0.5  # Node in lower half