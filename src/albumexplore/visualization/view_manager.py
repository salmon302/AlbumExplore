"""View management for visualization system."""
from typing import Dict, Any, List, Set, Optional
from .models import VisualNode, VisualEdge, Viewport
from .state import ViewType, ViewState, StateManager
from .data_interface import DataInterface
from .renderer import create_renderer, RenderConfig
from .view_integration import ViewIntegrationManager
from albumexplore.gui.graphics_debug import GraphicsDebugMonitor
from albumexplore.gui.gui_logging import graphics_logger

class ViewManager:
    """Manages visualization views and state."""
    
    def __init__(self, data_interface: DataInterface, parent=None, 
                 debug_monitor: Optional[GraphicsDebugMonitor] = None):
        self.data_interface = data_interface
        self.state_manager = StateManager()
        self.integration_manager = ViewIntegrationManager()
        self.debug_monitor = debug_monitor
        self.parent = parent
        
        # Initialize renderers with default config
        self.render_config = RenderConfig()
        self._renderers = {}
        for view_type in ViewType:
            self._renderers[view_type] = create_renderer(view_type, self.render_config)
        
        # Cache for rendered data
        self._render_cache: Dict[ViewType, Dict[str, Any]] = {}
        
        graphics_logger.info("View manager initialized")
    
    def switch_view(self, view_type: ViewType) -> Dict[str, Any]:
        """Switch to a different view type."""
        old_type = self.state_manager.current_view.view_type
        graphics_logger.debug(f"Switching view from {old_type.value} to {view_type.value}")
        
        # Get current data
        nodes, edges = self.data_interface.get_visible_data()
        
        # Prepare transition
        transition_data = self.integration_manager.prepare_transition(
            nodes, edges,
            self.state_manager.current_view,
            view_type
        )
        
        # Update state
        self.state_manager.switch_view(view_type)
        
        # Render new view
        result = self._render_view(nodes, edges)
        result.update(transition_data)
        
        if self.debug_monitor:
            self.debug_monitor.log_view_update(self.parent, len(nodes), len(edges))
        
        return result
    
    def select_nodes(self, node_ids: Set[str]) -> Dict[str, Any]:
        """Handle node selection."""
        # Temporarily disable logging to prevent potential recursion
        # graphics_logger.debug(f"Selecting nodes: {len(node_ids)} items")
        
        # Update state
        self.state_manager.current_view.selected_ids = node_ids
        
        # Sync selection across views
        self.integration_manager.sync_selection(
            node_ids,
            self.state_manager.current_view.view_type
        )
        
        # Re-render with updated selection
        nodes, edges = self.data_interface.get_visible_data()
        return self._render_view(nodes, edges)
    
    def update_data(self) -> Dict[str, Any]:
        """Update data and re-render."""
        graphics_logger.debug("Updating data")
        nodes, edges = self.data_interface.get_visible_data()
        return self._render_view(nodes, edges)
    
    def update_dimensions(self, width: float, height: float) -> Dict[str, Any]:
        """Update viewport dimensions."""
        graphics_logger.debug(f"Updating dimensions: {width}x{height}")
        self.state_manager.update_viewport(width, height)
        nodes, edges = self.data_interface.get_visible_data()
        return self._render_view(nodes, edges)
    
    def _render_view(self, nodes: List[VisualNode], edges: List[VisualEdge]) -> Dict[str, Any]:
        """Render current view."""
        view_type = self.state_manager.current_view.view_type
        
        # Create viewport state
        viewport = Viewport(
            width=self.state_manager.current_view.viewport_width,
            height=self.state_manager.current_view.viewport_height,
            zoom=self.state_manager.current_view.zoom_level,
            x=self.state_manager.current_view.position.get("x", 0),
            y=self.state_manager.current_view.position.get("y", 0)
        )
        setattr(viewport, "selected_ids", self.state_manager.current_view.selected_ids)
        
        # Get renderer
        renderer = self._renderers[view_type]
        
        # Render view
        result = renderer.render(nodes, edges, viewport)
        
        # Cache result
        self._render_cache[view_type] = result
        
        # Temporarily disable logging to prevent potential recursion
        # graphics_logger.debug(f"Rendered {view_type.value} view")
        return result
    
    def cleanup(self):
        """Clean up resources."""
        self.data_interface.cleanup()
        self._render_cache.clear()
        graphics_logger.info("View manager cleaned up")