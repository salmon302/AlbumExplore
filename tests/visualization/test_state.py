"""Tests for visualization state management."""
from unittest import TestCase
from albumexplore.visualization.state import ViewType, ViewState, StateManager

class TestViewState(TestCase):
    """Test view state functionality."""
    
    def test_init_default_values(self):
        """Test default initialization values."""
        state = ViewState(ViewType.TABLE)
        
        self.assertEqual(state.view_type, ViewType.TABLE)
        self.assertEqual(state.filters, {})
        self.assertEqual(state.selected_ids, set())
        self.assertEqual(state.zoom_level, 1.0)
        self.assertEqual(state.position, {"x": 0.0, "y": 0.0})
        self.assertEqual(state.viewport_width, 800.0)
        self.assertEqual(state.viewport_height, 600.0)
        self.assertEqual(state.view_specific, {})
    
    def test_update_position(self):
        """Test position updates with smoothing."""
        state = ViewState(ViewType.NETWORK)
        
        # Single update
        state.update_position(10.0, 20.0)
        self.assertEqual(state.position["x"], 10.0)
        self.assertEqual(state.position["y"], 20.0)
        
        # Multiple updates (should be smoothed)
        state.update_position(20.0, 40.0)
        state.update_position(30.0, 60.0)
        
        # Position should be weighted average
        self.assertGreater(state.position["x"], 20.0)
        self.assertLess(state.position["x"], 30.0)
        self.assertGreater(state.position["y"], 40.0)
        self.assertLess(state.position["y"], 60.0)

class TestStateManager(TestCase):
    """Test state manager functionality."""
    
    def setUp(self):
        self.manager = StateManager()
    
    def test_switch_view(self):
        """Test switching between views."""
        # Initial state
        self.assertEqual(self.manager.current_view.view_type, ViewType.TABLE)
        
        # Switch to network view
        self.manager.switch_view(ViewType.NETWORK)
        self.assertEqual(self.manager.current_view.view_type, ViewType.NETWORK)
        
        # Check history
        self.assertEqual(len(self.manager.view_history), 1)
        self.assertEqual(self.manager.view_history[0].view_type, ViewType.TABLE)
    
    def test_update_filters(self):
        """Test filter updates."""
        # Add filter
        self.manager.update_filters({"year": 2024})
        self.assertEqual(self.manager.current_view.filters["year"], 2024)
        
        # Update existing filter
        self.manager.update_filters({"year": 2025})
        self.assertEqual(self.manager.current_view.filters["year"], 2025)
        
        # Add another filter
        self.manager.update_filters({"genre": "prog-metal"})
        self.assertEqual(len(self.manager.current_view.filters), 2)
    
    def test_select_nodes(self):
        """Test node selection."""
        # Single selection
        self.manager.select_nodes({"node1"})
        self.assertEqual(self.manager.current_view.selected_ids, {"node1"})
        
        # Multiple selection
        self.manager.select_nodes({"node1", "node2"})
        self.assertEqual(self.manager.current_view.selected_ids, {"node1", "node2"})
        
        # Clear selection
        self.manager.select_nodes(set())
        self.assertEqual(self.manager.current_view.selected_ids, set())
    
    def test_undo(self):
        """Test undo functionality."""
        # Switch view
        self.manager.switch_view(ViewType.NETWORK)
        
        # Update filters
        self.manager.update_filters({"year": 2024})
        
        # Select nodes
        self.manager.select_nodes({"node1"})
        
        # Undo changes
        self.assertTrue(self.manager.undo())
        self.assertEqual(self.manager.current_view.selected_ids, set())
        
        self.assertTrue(self.manager.undo())
        self.assertEqual(self.manager.current_view.filters, {})
        
        self.assertTrue(self.manager.undo())
        self.assertEqual(self.manager.current_view.view_type, ViewType.TABLE)
        
        # No more changes to undo
        self.assertFalse(self.manager.undo())