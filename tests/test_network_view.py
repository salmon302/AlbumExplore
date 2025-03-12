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
            id=f"node_{i}",
            label=f"Node {i}",
            size=10,
            color="#000000",
            shape="circle",
            data={'x': i*100, 'y': i*100}
        )
        for i in range(5)
    ]

@pytest.fixture
def sample_edges():
    return [
        VisualEdge(
            source=f"node_{i}",
            target=f"node_{i+1}",
            weight=1.0,
            color="#000000"
        )
        for i in range(4)
    ]

def test_node_selection(qtbot, sample_nodes):
    """Test node selection functionality."""
    view = NetworkView()
    view.resize(800, 600)
    view.update_data(sample_nodes, [])
    
    # Test node selection
    node = view.nodes[0]
    x = int(node.data['x'] + view.width()/2)
    y = int(node.data['y'] + view.height()/2)
    
    qtbot.mouseClick(view, Qt.MouseButton.LeftButton, pos=QPoint(x, y))
    assert node.id in view.selected_ids, "Node not selected after click"