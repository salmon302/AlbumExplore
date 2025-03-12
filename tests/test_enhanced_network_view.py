"""Test cases for enhanced network visualization."""
import unittest
import json
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtTest import QTest
from albumexplore.visualization.views.enhanced_network_view import EnhancedNetworkView
from albumexplore.visualization.models import VisualNode, VisualEdge

class TestEnhancedNetworkView(unittest.TestCase):
    def setUp(self):
        self.app = QApplication([])
        self.view = EnhancedNetworkView()
        
        # Initialize test data
        self.test_nodes = [
            VisualNode(id=f"node_{i}", label=f"Node {i}", size=10,
                      color="#000000", shape="circle", 
                      data={'x': i*10, 'y': i*10})
            for i in range(5)
        ]
        self.test_edges = [
            VisualEdge(source=f"node_{i}", target=f"node_{i+1}", 
                      weight=1.0, color="#000000")
            for i in range(4)
        ]
        self.view.resize(800, 600)
        
    def tearDown(self):
        # Clean up test data
        self.test_nodes = []
        self.test_edges = []
        
        # Clean up view and application
        self.view.deleteLater()
        self.app.quit()

    def test_view_initialization(self):
        """Test view initialization."""
        self.assertIsNotNone(self.view)
        self.assertEqual(self.view.nodes, [])
        self.assertEqual(self.view.edges, [])
        self.assertEqual(self.view.selected_ids, set())
        self.assertEqual(self.view.viewport_scale, 1.0)
        
    def test_update_data(self):
        """Test updating visualization data."""
        self.view.update_data(self.test_nodes, self.test_edges)
        self.assertEqual(len(self.view.nodes), len(self.test_nodes))
        self.assertEqual(len(self.view.edges), len(self.test_edges))
        
    def test_node_selection(self):
        """Test node selection functionality."""
        self.view.update_data(self.test_nodes, self.test_edges)
        
        # Test node selection at known position
        node = self.test_nodes[0]
        screen_x = int(node.data['x'] + self.view.width()/2)
        screen_y = int(node.data['y'] + self.view.height()/2)
        
        event = QTest.createMouseEvent(
            QTest.QMouseEvent.Type.MouseButtonPress,
            QPoint(screen_x, screen_y),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier
        )
        self.view.mousePressEvent(event)
        
        self.assertIn(node.id, self.view.selected_ids)
        
    def test_view_zooming(self):
        """Test zoom functionality."""
        initial_scale = self.view.viewport_scale
        
        # Simulate zoom in
        event = QTest.createWheelEvent(
            QPoint(400, 300),
            120,  # Positive delta = zoom in
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier
        )
        self.view.wheelEvent(event)
        
        self.assertGreater(self.view.viewport_scale, initial_scale)

if __name__ == '__main__':
    unittest.main()
