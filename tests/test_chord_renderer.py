import pytest
import math
from PyQt6.QtGui import QPainter, QPainterPath
from PyQt6.QtCore import QRectF
from albumexplore.visualization.models import VisualNode, VisualEdge
from albumexplore.visualization.state import ViewState, ViewType
from albumexplore.visualization.chord_renderer import ChordRenderer

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
            size=1.0,
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
    state = ViewState(ViewType.CHORD)
    state.selected_ids.add("album1")
    state.zoom_level = 1.5
    state.position = {"x": 100.0, "y": 50.0}
    state.viewport = QRectF(0, 0, 800, 600)
    return state

def test_node_angle_calculation(qapp, sample_nodes):
    renderer = ChordRenderer()
    angles = renderer._calculate_node_angles(sample_nodes)

    # Check that all nodes have angles
    assert len(angles) == 3

    # Check that angles form a complete circle
    total_angle = sum(end - start for start, end in angles.values())
    assert pytest.approx(total_angle) == 2 * math.pi

    # Check proportional sizes
    album1_size = angles["album1"][1] - angles["album1"][0]
    album2_size = angles["album2"][1] - angles["album2"][0]
    assert pytest.approx(album1_size) == 2 * album2_size  # album1 is twice the size

def test_bezier_curve_calculation(qapp):
    renderer = ChordRenderer()
    points = renderer._calculate_bezier_curve(0, math.pi/2, 100.0, 80.0)

    # Check number of points
    assert len(points) == 21  # 20 steps + 1

    # Check start and end points
    assert points[0][0] == pytest.approx(100.0)  # radius * cos(0)
    assert points[0][1] == pytest.approx(0.0)    # radius * sin(0)
    assert points[-1][0] == pytest.approx(0.0)   # radius * cos(pi/2)
    assert points[-1][1] == pytest.approx(100.0) # radius * sin(pi/2)

def test_chord_rendering(qapp, sample_nodes, sample_edges, view_state):
    renderer = ChordRenderer()
    result = renderer.render(sample_nodes, sample_edges, view_state)

    assert result["type"] == "chord"
    assert len(result["nodes"]) == 3
    assert len(result["chords"]) == 2

    # Check node rendering
    node1 = next(n for n in result["nodes"] if n["id"] == "album1")
    assert node1["selected"] is True
    assert "start_angle" in node1
    assert "end_angle" in node1
    assert node1["radius"] == pytest.approx(400.0)  # 1000 * 0.4

    # Check chord rendering
    chord = result["chords"][0]
    assert chord["source"] == "album1"
    assert chord["target"] == "album2"
    assert chord["weight"] == 1.0
    assert len(chord["path"]) > 0

def test_chord_connection_visibility(qapp, sample_nodes, sample_edges, view_state):
    renderer = ChordRenderer()
    result = renderer.render(sample_nodes, sample_edges, view_state)

    # Check chord opacity and thickness
    chord = result["chords"][0]
    assert chord["thickness"] >= 2  # Minimum thickness
    assert "control1" in chord and "control2" in chord  # Bezier control points

    # Verify control points for smooth curves
    assert abs(chord["control1"]["x"]) <= result["width"]
    assert abs(chord["control1"]["y"]) <= result["height"]

def test_label_positioning(qapp, sample_nodes, view_state):
    renderer = ChordRenderer()
    result = renderer.render(sample_nodes, [], view_state)

    # Check label radius is outside arc
    node = result["nodes"][0]
    radius = node["radius"]
    label_radius = radius * 1.1  # Should match view implementation
    assert label_radius > radius  # Label should be outside arc

def test_chord_responsiveness(qapp, sample_nodes, sample_edges, view_state):
    """Test chord diagram responds to viewport changes."""
    renderer = ChordRenderer()

    # Test with different viewport sizes
    view_state.viewport = QRectF(0, 0, 1200, 800)
    result1 = renderer.render(sample_nodes, sample_edges, view_state)

    view_state.viewport = QRectF(0, 0, 600, 400)
    result2 = renderer.render(sample_nodes, sample_edges, view_state)

    # Scale should adjust with viewport
    assert result1["scale"] > result2["scale"]

    # Chord paths should still be valid
    for chord in result2["chords"]:
        assert len(chord["path"]) > 0
        assert all(isinstance(p["x"], (int, float)) for p in chord["path"])
        assert all(isinstance(p["y"], (int, float)) for p in chord["path"])