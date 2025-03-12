import pytest
from PyQt6.QtWidgets import QApplication
from albumexplore.visualization.views import view_map
from albumexplore.visualization.models import VisualNode, VisualEdge
from albumexplore.visualization.state import ViewType

@pytest.fixture
def sample_data():
    """Create sample test data."""
    nodes = [
        VisualNode(id=f"node_{i}", label=f"Node {i}", size=10,
                  color="#000000", shape="circle", 
                  data={'x': i*100, 'y': i*100})
        for i in range(5)
    ]
    edges = [
        VisualEdge(source=f"node_{i}", target=f"node_{i+1}",
                  weight=1.0, color="#000000")
        for i in range(4)
    ]
    return nodes, edges

def test_view_creation():
    """Test view creation for all view types."""
    for view_type in ViewType:
        view_class = view_map.get(view_type)
        if view_class:
            view = view_class()
            assert view is not None
            assert view.view_state.view_type == view_type

def test_table_to_network_transition(qtbot, sample_data):
    """Test transition from table to network view."""
    nodes, edges = sample_data
    
    # Setup views
    table_view = view_map[ViewType.TABLE]()
    network_view = view_map[ViewType.NETWORK]()
    
    # Initial data
    table_view.update_data(nodes, edges)
    
    # Select an item
    table_view.selected_ids = {'node_0'}
    
    # Transition to network
    transition_data = {
        'transition': {'type': 'morph'},
        'shared_selections': list(table_view.selected_ids)
    }
    network_view.update_data(nodes, edges)
    network_view.apply_transition(transition_data)
    
    # Verify selection preservation
    assert network_view.selected_ids == table_view.selected_ids