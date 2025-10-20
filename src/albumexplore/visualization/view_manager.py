"""View management for visualization system."""
from typing import Dict, Any, List, Set, Optional
from PyQt6.QtCore import QObject, pyqtSignal # Ensure QObject and pyqtSignal are imported
from .models import VisualNode, VisualEdge, Viewport
from .state import ViewType, ViewState, StateManager
from .data_interface import DataInterface
from .renderer import create_renderer, RenderConfig
from .view_integration import ViewIntegrationManager
from albumexplore.gui.graphics_debug import GraphicsDebugMonitor
from albumexplore.gui.gui_logging import graphics_logger
from albumexplore.visualization.layout import ForceLayout # Added import
from albumexplore.visualization.physics.force_params import ForceParams # Added import

class ViewManager(QObject): # Inherit from QObject
    """Manages visualization views and state."""
    view_changed = pyqtSignal() # Define the signal as a class attribute

    def __init__(self, data_interface: DataInterface, parent: Optional[QObject] = None,
                 debug_monitor: Optional[GraphicsDebugMonitor] = None):
        super().__init__(parent) # Call QObject's __init__
        self.data_interface = data_interface
        self.state_manager = StateManager()
        self.integration_manager = ViewIntegrationManager()
        self.debug_monitor = debug_monitor
        # self.parent is already set by QObject if parent is provided.

        # Initialize renderers with default config
        self.render_config = RenderConfig()
        self._renderers: Dict[ViewType, Any] = {}
        for view_type_enum_member in ViewType:
            self._renderers[view_type_enum_member] = create_renderer(view_type_enum_member, self.render_config)

        # Initialize layout engine
        self.layout_params = ForceParams()
        self.layout_engine = ForceLayout(self.layout_params)
        
        # Cache for rendered data
        self._render_cache: Dict[ViewType, Dict[str, Any]] = {}
        self._current_render_data: Optional[Dict[str, Any]] = None # Cache for the most recent render data

        graphics_logger.info("View manager initialized")

    @property
    def current_view_type(self) -> ViewType:
        """Returns the current view type from the state manager."""
        return self.state_manager.current_view.view_type

    def switch_view(self, view_type: ViewType) -> Dict[str, Any]:
        """Switch to a different view type."""
        old_type = self.state_manager.current_view.view_type
        graphics_logger.debug(f"Switching view from {old_type.value} to {view_type.value}")

        nodes, edges = self.data_interface.get_visible_data()

        transition_data = self.integration_manager.prepare_transition(
            nodes, edges,
            self.state_manager.current_view,
            view_type
        )

        self.state_manager.switch_view(view_type)
        
        # Render new view and store it
        self._current_render_data = self._render_view(nodes, edges)
        if self._current_render_data is None: # Should not happen if _render_view guarantees a dict
             self._current_render_data = {}
        self._current_render_data.update(transition_data)
        
        self.view_changed.emit() # Emit the signal *after* the new view is rendered and state is updated

        if self.debug_monitor and self.parent(): # Check if parent exists before calling methods on it
            self.debug_monitor.log_view_update(self.parent(), len(nodes), len(edges))

        return self._current_render_data

    def get_render_data(self) -> Optional[Dict[str, Any]]:
        """Returns the most recently rendered data for the current view."""
        return self._current_render_data
    
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
        """Render current view and cache it."""
        view_type = self.state_manager.current_view.view_type
        
        graphics_logger.info(f"[ViewManager._render_view] Rendering for view type: {view_type.value}")
        graphics_logger.debug(f"[ViewManager._render_view] Input: {len(nodes)} VisualNode objects, {len(edges)} VisualEdge objects.")
        if nodes:
            # Corrected to access x and y from node.pos dictionary
            graphics_logger.debug(f"[ViewManager._render_view] First input VisualNode: id={nodes[0].id}, x={nodes[0].pos['x']}, y={nodes[0].pos['y']}, label={nodes[0].label}")

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
        graphics_logger.info(f"[ViewManager._render_view] renderer.render() completed. Result keys: {list(result.keys()) if result else 'None'}")

        # Adapt TableRenderer output for TagExplorerView if necessary
        if view_type == ViewType.TAG_EXPLORER and result and 'rows' in result and 'nodes' not in result:
            graphics_logger.info(f"[ViewManager._render_view] Adapting 'rows' to 'nodes' for TagExplorerView.")
            # The 'rows' from TableRenderer are dictionaries.
            # TagExplorerView.update_data was refactored to handle nodes that are dicts
            # and access tags via node.get('tags', []) if node.data is not present.
            
            # Create a 'nodes' key and populate it with the data from 'rows'.
            # Each item in 'rows' is a dictionary representing an album's properties.
            adapted_nodes = []
            for row_data in result['rows']:
                adapted_nodes.append(row_data)
            result['nodes'] = adapted_nodes
            
            # Optionally, remove the 'rows' key if it's no longer needed,
            # though simply ensuring 'nodes' is present is the primary goal.
            # del result['rows'] 
            graphics_logger.info(f"[ViewManager._render_view] Adapted {len(result['nodes'])} items from 'rows' to 'nodes'.")

        if result and 'nodes' in result and result['nodes']:
            graphics_logger.info(f"[ViewManager._render_view] Result contains {len(result['nodes'])} nodes.")
            # Log details for the first few nodes in the result
            for i, node_data in enumerate(result['nodes']):
                if i < 3: # Log details for the first 3 nodes
                    graphics_logger.debug(f"[ViewManager._render_view] Output node {i} data from renderer: {node_data}")
                else:
                    break
        elif result and 'nodes' in result:
            graphics_logger.info("[ViewManager._render_view] Result contains an empty list of nodes.")
        else:
            graphics_logger.warning("[ViewManager._render_view] Result from renderer is None, or does not contain 'nodes' key.")

        self._render_cache[view_type] = result # Update specific view type cache
        self._current_render_data = result # Update current render data
        return result
    
    def cleanup(self):
        """Clean up resources."""
        self.data_interface.cleanup()
        self._render_cache.clear()
        graphics_logger.info("View manager cleaned up")