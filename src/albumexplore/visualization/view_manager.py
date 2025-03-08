from typing import Dict, Any, Optional, List, Set
import math
import random
import pandas as pd
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QWidget
from albumexplore.gui.gui_logging import gui_logger
from albumexplore.visualization.views import create_view as create_vis_view

from .models import VisualNode, VisualEdge
from .state import StateManager, ViewType
from .renderer import create_renderer
from .data_interface import DataInterface
from .layout import ForceDirectedLayout, ForceParams
from .optimizations import ViewOptimizer, Viewport
from .responsive import ResponsiveManager, ScreenSize
from .view_integration import ViewIntegrationManager, TransitionType
from .transition_animator import TransitionAnimator

class ViewManager:
    """Manages visualization views and switching between them."""
    
    def __init__(self, data_interface: DataInterface, parent_widget: Optional[QWidget] = None, graphics_debug=None):
        """Initialize view manager."""
        self.data_interface = data_interface
        self.parent_widget = parent_widget
        self.graphics_debug = graphics_debug
        
        # View state management
        self.state_manager = StateManager()
        self.view_integration = ViewIntegrationManager()
        self.current_view_type = ViewType.TABLE
        self.current_view = None
        self.previous_view = None
        self.previous_view_type = None
        
        # Data storage
        self.nodes: List[VisualNode] = []
        self.edges: List[VisualEdge] = []
        self.selected_node_ids: Set[str] = set()
        
        # View container dimensions
        default_width = parent_widget.width() if parent_widget else 800
        default_height = parent_widget.height() if parent_widget else 600
        
        # Layout and viewport
        self.viewport = Viewport(0, 0, default_width, default_height, 1.0)
        self.optimizer = ViewOptimizer()
        
        # Animation state
        self.transition_animator = TransitionAnimator()
        self.is_animating = False
        self.transition_timer = QTimer()
        self.transition_timer.timeout.connect(self._animation_frame)
        self.transition_timer.setInterval(16)  # ~60 FPS
        self.transition_progress = 0.0
        self.transition_data = None
        
        # Load initial data
        self.update_data()

    def switch_view(self, view_type: ViewType, transition_type: TransitionType = TransitionType.NONE) -> Dict[str, Any]:
        """Switch to a different view type."""
        gui_logger.debug(f"Switching to view type: {view_type}")
        try:
            # Store previous view info
            self.previous_view_type = self.current_view_type
            self.previous_view = self.current_view
            
            # Create new view with parent widget
            new_view = create_vis_view(view_type, self.parent_widget)
            if not new_view:
                return {"success": False, "message": f"Failed to create view of type {view_type}"}
            
            # Update state
            self.current_view = new_view
            self.current_view_type = view_type
            self.state_manager.switch_view(view_type)
            
            # Initialize view with current data
            self.current_view.setUpdatesEnabled(False)
            try:
                # For table view, ensure proper data initialization
                if view_type == ViewType.TABLE:
                    gui_logger.debug("Initializing table view data")
                    valid_nodes = [n for n in self.nodes if n.data.get("type") == "row"]
                    gui_logger.debug(f"Found {len(valid_nodes)} valid row nodes")
                    self.current_view.update_data(valid_nodes, [])
                elif view_type == ViewType.TAG_EXPLORER:
                    gui_logger.debug("Initializing tag explorer view data")
                    self.current_view.update_data(self.nodes, self.edges)
                else:
                    self.current_view.update_data(self.nodes, self.edges)
                
                # Set proper size and visibility
                if self.parent_widget:
                    self.current_view.resize(self.parent_widget.size())
                    
                # Ensure the view is visible and properly displayed
                self.current_view.show()
                self.current_view.raise_()
                
                # Special handling for table view to ensure it's properly displayed
                if hasattr(self.current_view, 'table'):
                    self.current_view.table.resize(self.current_view.size())
                    self.current_view.table.show()
                    self.current_view.table.raise_()
                    self.current_view.table.viewport().update()
                
            finally:
                self.current_view.setUpdatesEnabled(True)
                self.current_view.update()
            
            # Schedule cleanup of previous view
            self._schedule_previous_view_cleanup()
            
            # Signal transition if needed
            if transition_type != TransitionType.NONE and self.previous_view:
                transition_config = self.view_integration.create_transition_config(
                    self.previous_view_type,
                    view_type,
                    self.state_manager.current_view,
                    self.nodes
                )
                self.current_view.apply_transition(transition_config)
            
            # Perform view-specific rendering and return result
            return self.render_current_view()
            
        except Exception as e:
            gui_logger.error(f"Error switching view: {str(e)}")
            return {"success": False, "message": f"Error switching view: {str(e)}"}

    def update_data(self) -> None:
        """Update visualization data from the data interface."""
        gui_logger.debug("Updating visualization data")
        try:
            self.nodes, self.edges = self.data_interface.get_visible_data()
            if self.current_view:
                self.current_view.setUpdatesEnabled(False)
                try:
                    # For table view, ensure proper data initialization
                    if self.current_view_type == ViewType.TABLE:
                        gui_logger.debug("Updating table view data")
                        valid_nodes = [n for n in self.nodes if n.data.get("type") == "row"]
                        gui_logger.debug(f"Found {len(valid_nodes)} valid row nodes")
                        self.current_view.update_data(valid_nodes, [])
                    else:
                        self.current_view.update_data(self.nodes, self.edges)
                finally:
                    self.current_view.setUpdatesEnabled(True)
                    if hasattr(self.current_view, 'table'):
                        self.current_view.table.viewport().update()
        except Exception as e:
            gui_logger.error(f"Error updating data: {str(e)}")
            raise

    def update_dimensions(self, width: int, height: int) -> Dict[str, Any]:
        """Update dimensions for responsive layout."""
        # Update viewport dimensions
        self.viewport.width = width
        self.viewport.height = height
        
        if self.current_view:
            # Hold updates while resizing to prevent flicker
            self.current_view.setUpdatesEnabled(False)
            try:
                self.current_view.resize(width, height)
                if hasattr(self.current_view, 'table'):
                    self.current_view.table.resize(width, height)
                return {"success": True}
            finally:
                self.current_view.setUpdatesEnabled(True)
                self.current_view.update()
        
        return {"success": False, "message": "No current view"}

    def select_nodes(self, node_ids: Set[str]) -> None:
        """Update selection state."""
        if self.current_view and hasattr(self.current_view, 'selected_ids'):
            self.current_view.selected_ids = node_ids
            if hasattr(self.current_view, '_update_selection'):
                self.current_view._update_selection()

    def _schedule_previous_view_cleanup(self) -> None:
        """Schedule the previous view for deletion with delay."""
        if not self.previous_view:
            return
        # Schedule cleanup after transition completes
        QTimer.singleShot(500, self._cleanup_previous_view)

    def _cleanup_previous_view(self) -> None:
        """Clean up the previous view properly."""
        if self.previous_view and self.previous_view != self.current_view:
            gui_logger.debug(f"Cleaning up previous view: {self.previous_view_type}")
            
            # Hide the previous view to ensure it doesn't interfere with current view
            self.previous_view.hide()
            
            # Remove from parent if it has a parent
            if self.previous_view.parent():
                self.previous_view.setParent(None)
                
            # Delete the view to free resources
            self.previous_view.deleteLater()
            self.previous_view = None

    def _apply_transition(self, transition_data: Dict[str, Any]) -> None:
        """Apply transition data to the current view."""
        if not self.current_view:
            return
            
        # Ensure current view is properly sized before transition
        if self.parent_widget:
            self.current_view.resize(self.parent_widget.size())
            
        # Apply transition data
        self.current_view.apply_transition(transition_data)
        
        # Start animation if needed
        transition_type = transition_data.get('transition', {}).get('type')
        if transition_type in ['morph', 'fade'] and not self.is_animating:
            self.transition_data = transition_data
            self.transition_progress = 0.0
            self.is_animating = True
            self.transition_timer.start()

    def _animation_frame(self) -> None:
        """Handle animation frame updates."""
        if not self.is_animating or not self.current_view:
            self.transition_timer.stop()
            self.is_animating = False
            return
            
        # Update progress
        self.transition_progress += 0.05
        if self.transition_progress >= 1.0:
            self.transition_timer.stop()
            self.is_animating = False
            self.transition_progress = 1.0
            
        # Update view
        self.transition_animator.update_transition(
            self.current_view,
            self.transition_data,
            self.transition_progress
        )