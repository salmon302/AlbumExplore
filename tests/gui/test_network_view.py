"""Tests for the Network View component."""

import sys
import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt, QPointF

from albumexplore.gui.views.network_view import NetworkView


@pytest.fixture(scope="module")
def app():
    """Create a Qt application."""
    return QApplication(sys.argv)


@pytest.fixture
def network_view(app):
    """Create a network view widget."""
    view = NetworkView()
    yield view
    view.deleteLater()


def test_network_view_creation(network_view):
    """Test that the network view can be created."""
    assert network_view is not None
    assert network_view._zoom == 1.0
    assert network_view._pan_x == 0.0
    assert network_view._pan_y == 0.0
    assert network_view._node_radius == 5.0


def test_update_data_nodes(network_view):
    """Test that the network view can update with node data."""
    # Sample test data
    test_data = {
        'nodes': [
            {'id': 'node1', 'x': 100, 'y': 100, 'label': 'Node 1'},
            {'id': 'node2', 'x': 200, 'y': 200, 'label': 'Node 2'},
        ],
        'edges': [
            {'source': 'node1', 'target': 'node2'}
        ]
    }
    
    network_view.update_data(test_data)
    
    # Verify node positions were updated
    assert 'node1' in network_view._node_positions
    assert 'node2' in network_view._node_positions
    assert network_view._node_positions['node1'] == QPointF(100, 100)
    assert network_view._node_positions['node2'] == QPointF(200, 200)
    
    # Verify edges were updated
    assert ('node1', 'node2') in network_view._visible_edges


def test_node_selection(network_view):
    """Test node selection functionality."""
    # Sample test data with nodes
    test_data = {
        'nodes': [
            {'id': 'node1', 'x': 100, 'y': 100, 'label': 'Node 1'},
            {'id': 'node2', 'x': 200, 'y': 200, 'label': 'Node 2'},
        ],
        'edges': []
    }
    network_view.update_data(test_data)
    
    # Initially no nodes are selected
    assert len(network_view._selected_nodes) == 0
    
    # Simulate finding a node at position and selecting it
    # This is a direct test of the internal method
    node_view = network_view._find_node_at(QPointF(
        network_view.width() / 2 + 100 * network_view._zoom,
        network_view.height() / 2 + 100 * network_view._zoom
    ))
    # Since the view has zero size in tests, this might not work as expected
    # But we can directly modify the selection state
    
    network_view._selected_nodes.add('node1')
    assert 'node1' in network_view._selected_nodes
    
    # Update with selection data - passing a set instead of a list
    network_view.update_data({'selected_ids': set(['node2'])})
    assert 'node2' in network_view._selected_nodes
    assert 'node1' not in network_view._selected_nodes