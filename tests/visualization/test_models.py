"""Tests for visualization models."""
from unittest import TestCase
from albumexplore.visualization.models import Point, VisualNode, VisualEdge, Viewport

class TestPoint(TestCase):
    """Test point functionality."""
    
    def test_init(self):
        """Test initialization."""
        p = Point()
        self.assertEqual(p.x, 0.0)
        self.assertEqual(p.y, 0.0)
        
        p = Point(1.0, 2.0)
        self.assertEqual(p.x, 1.0)
        self.assertEqual(p.y, 2.0)

class TestViewport(TestCase):
    """Test viewport functionality."""
    
    def test_init(self):
        """Test initialization."""
        v = Viewport()
        self.assertEqual(v.x, 0.0)
        self.assertEqual(v.y, 0.0)
        self.assertEqual(v.width, 800.0)
        self.assertEqual(v.height, 600.0)
        self.assertEqual(v.zoom, 1.0)
        
        v = Viewport(10.0, 20.0, 1000.0, 800.0, 2.0)
        self.assertEqual(v.x, 10.0)
        self.assertEqual(v.y, 20.0)
        self.assertEqual(v.width, 1000.0)
        self.assertEqual(v.height, 800.0)
        self.assertEqual(v.zoom, 2.0)

class TestVisualNode(TestCase):
    """Test visual node functionality."""
    
    def test_init(self):
        """Test initialization."""
        node = VisualNode(id="test", label="Test Node")
        self.assertEqual(node.id, "test")
        self.assertEqual(node.label, "Test Node")
        self.assertEqual(node.size, 10.0)
        self.assertEqual(node.color, "#4287f5")
        self.assertEqual(node.shape, "circle")
        self.assertEqual(node.data, {})
        self.assertEqual(node.opacity, 1.0)
        self.assertFalse(node.selected)
        self.assertTrue(node.visible)
        self.assertEqual(node.pos, {"x": 0.0, "y": 0.0})
        
        # Test with custom values
        node = VisualNode(
            id="test2",
            label="Test Node 2",
            size=20.0,
            color="#ff0000",
            shape="square",
            data={"key": "value"},
            opacity=0.5,
            selected=True,
            visible=False,
            pos={"x": 10.0, "y": 20.0}
        )
        self.assertEqual(node.id, "test2")
        self.assertEqual(node.label, "Test Node 2")
        self.assertEqual(node.size, 20.0)
        self.assertEqual(node.color, "#ff0000")
        self.assertEqual(node.shape, "square")
        self.assertEqual(node.data, {"key": "value"})
        self.assertEqual(node.opacity, 0.5)
        self.assertTrue(node.selected)
        self.assertFalse(node.visible)
        self.assertEqual(node.pos, {"x": 10.0, "y": 20.0})

class TestVisualEdge(TestCase):
    """Test visual edge functionality."""
    
    def test_init(self):
        """Test initialization."""
        edge = VisualEdge(source="n1", target="n2")
        self.assertEqual(edge.source, "n1")
        self.assertEqual(edge.target, "n2")
        self.assertEqual(edge.weight, 1.0)
        self.assertEqual(edge.thickness, 1.0)
        self.assertEqual(edge.color, "#cccccc")
        self.assertEqual(edge.data, {})
        self.assertEqual(edge.opacity, 1.0)
        self.assertTrue(edge.visible)
        
        # Test with custom values
        edge = VisualEdge(
            source="n3",
            target="n4",
            weight=2.0,
            thickness=3.0,
            color="#ff0000",
            data={"type": "test"},
            opacity=0.7,
            visible=False
        )
        self.assertEqual(edge.source, "n3")
        self.assertEqual(edge.target, "n4")
        self.assertEqual(edge.weight, 2.0)
        self.assertEqual(edge.thickness, 3.0)
        self.assertEqual(edge.color, "#ff0000")
        self.assertEqual(edge.data, {"type": "test"})
        self.assertEqual(edge.opacity, 0.7)
        self.assertFalse(edge.visible)