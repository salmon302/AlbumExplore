"""View integration and transition management."""
from typing import Dict, Any, List, Set, Callable, Tuple
from dataclasses import dataclass
from .models import VisualNode, VisualEdge
from .state import ViewType, ViewState, TransitionType
from albumexplore.gui.gui_logging import graphics_logger

@dataclass
class ViewTransition:
    """Configuration for view transitions."""
    source_type: ViewType
    target_type: ViewType
    transition_type: TransitionType
    duration_ms: int = 300
    easing: str = "easeInOutQuad"

class ViewIntegrationManager:
    """Manages view integration and transitions."""
    
    def __init__(self):
        self.transition_configs: Dict[Tuple[ViewType, ViewType], ViewTransition] = {}
        self.shared_selections: Set[str] = set()
        self.view_sync_handlers: Dict[ViewType, List[Callable]] = {}
        self._transition_cache = {}
        self._last_positions = {}
        self._view_transition_in_progress = False
        self._active_view_type = None
        self._init_default_transitions()
    
    def _init_default_transitions(self):
        """Initialize default transition configurations."""
        # All transitions default to fade
        for source in ViewType:
            for target in ViewType:
                key = (source, target)
                if key not in self.transition_configs:
                    self.transition_configs[key] = ViewTransition(
                        source, target, TransitionType.FADE, 300
                    )
    
    def register_sync_handler(self, view_type: ViewType, handler: Callable):
        """Register a handler for view synchronization events."""
        if view_type not in self.view_sync_handlers:
            self.view_sync_handlers[view_type] = []
        self.view_sync_handlers[view_type].append(handler)
    
    def prepare_transition(self, nodes: List[VisualNode], edges: List[VisualEdge],
                         source_state: ViewState, target_type: ViewType) -> Dict[str, Any]:
        """Prepare transition between views."""
        self._view_transition_in_progress = True
        try:
            transition = self.get_transition_config(source_state.view_type, target_type)
            cache_key = (source_state.view_type, target_type)
            
            # Initialize with cached positions if available
            node_positions = self._last_positions.copy()
            
            # Update positions based on transition type
            if transition.transition_type == TransitionType.MORPH:
                for node in nodes:
                    if not isinstance(node.data, dict):
                        node.data = {}
                        
                    # Use existing position or preserve last known position
                    if node.id in self._last_positions:
                        node.data.update(self._last_positions[node.id])
                    
                    # Cache current position
                    self._last_positions[node.id] = {
                        'x': node.data.get('x', 0),
                        'y': node.data.get('y', 0)
                    }
                    
                transition_data = {
                    'transition': {
                        'type': transition.transition_type.value,
                        'duration': transition.duration_ms,
                        'easing': transition.easing
                    },
                    'preserved_positions': self._last_positions,
                    'shared_selections': list(self.shared_selections)
                }
                
            else:  # FADE or INSTANT
                transition_data = {
                    'transition': {
                        'type': transition.transition_type.value,
                        'duration': transition.duration_ms,
                        'easing': transition.easing
                    },
                    'shared_selections': list(self.shared_selections)
                }
            
            # Cache transition data
            self._transition_cache[cache_key] = transition_data
            graphics_logger.debug(
                f"Prepared {transition.transition_type.value} transition from "
                f"{source_state.view_type.value} to {target_type.value}"
            )
            return transition_data
            
        finally:
            self._view_transition_in_progress = False
    
    def get_transition_config(self, source: ViewType, target: ViewType) -> ViewTransition:
        """Get transition configuration for view types."""
        key = (source, target)
        return self.transition_configs.get(
            key,
            ViewTransition(source, target, TransitionType.INSTANT)
        )
    
    def sync_selection(self, selected_ids: Set[str], source_type: ViewType):
        """Synchronize selection across views."""
        self.shared_selections = selected_ids
        
        # Notify other views
        for view_type, handlers in self.view_sync_handlers.items():
            if view_type != source_type:
                for handler in handlers:
                    handler(selected_ids)
        
        graphics_logger.debug(
            f"Synchronized selection from {source_type.value}: "
            f"{len(selected_ids)} items"
        )
    
    def get_shared_state(self) -> Dict[str, Any]:
        """Get shared state for views."""
        return {
            'selections': list(self.shared_selections),
            'active_transitions': [
                {
                    'source': t.source_type.value,
                    'target': t.target_type.value,
                    'type': t.transition_type.value,
                    'duration': t.duration_ms
                }
                for t in self.transition_configs.values()
            ]
        }