"""State management for visualization system."""
from enum import Enum
from typing import Dict, Any, Set

class ViewType(Enum):
    """Available view types."""
    TABLE = "table"
    CHORD = "chord"
    ARC = "arc"
    TAG_EXPLORER = "tag_explorer"
    MAP = "map"  # Geographic world map view
    SIMILARITY = "similarity"  # Album similarity bar chart view

class TransitionType(Enum):
    """Available transition types between views."""
    MORPH = "morph"      # Morphing transition with position interpolation
    FADE = "fade"        # Fade out/in transition
    INSTANT = "instant"  # Immediate transition without animation

class ViewState:
    """State for a visualization view."""
    
    def __init__(self, view_type: ViewType):
        self.view_type = view_type
        self.filters: Dict[str, Any] = {}
        self.selected_ids: Set[str] = set()
        self.zoom_level: float = 1.0
        self.position: Dict[str, float] = {"x": 0.0, "y": 0.0}
        self.viewport_width: float = 800.0
        self.viewport_height: float = 600.0
        self.view_specific: Dict[str, Any] = {}

    def clone(self) -> 'ViewState':
        """Create a copy of this state."""
        new_state = ViewState(self.view_type)
        new_state.filters = self.filters.copy()
        new_state.selected_ids = self.selected_ids.copy()
        new_state.zoom_level = self.zoom_level
        new_state.position = self.position.copy()
        new_state.viewport_width = self.viewport_width
        new_state.viewport_height = self.viewport_height
        new_state.view_specific = self.view_specific.copy()
        return new_state

class StateManager:
    """Manages visualization state and history."""
    
    def __init__(self):
        self.current_view = ViewState(ViewType.TABLE)
        self.view_history: List[ViewState] = []
        self.max_history = 50

    def switch_view(self, view_type: ViewType) -> None:
        """Switch to a different view type."""
        # Save current state to history
        self.view_history.append(self.current_view)
        if len(self.view_history) > self.max_history:
            self.view_history.pop(0)

        # Create new state
        new_state = ViewState(view_type)
        # Copy persistent state
        new_state.viewport_width = self.current_view.viewport_width
        new_state.viewport_height = self.current_view.viewport_height
        new_state.filters = self.current_view.filters.copy()
        new_state.selected_ids = self.current_view.selected_ids.copy()
        self.current_view = new_state

    def update_viewport(self, width: float, height: float) -> None:
        """Update viewport dimensions."""
        self.current_view.viewport_width = width
        self.current_view.viewport_height = height

    def update_zoom(self, zoom: float) -> None:
        """Update zoom level with clamping."""
        self.current_view.zoom_level = max(0.1, min(zoom, 5.0))

    def update_position(self, x: float, y: float) -> None:
        """Update view position."""
        self.current_view.position = {"x": x, "y": y}

    def update_filters(self, filters:Dict[str,Any]) -> None:
        """Update active filters."""
        self.current_view.filters.update(filters)

    def select_nodes(self, node_ids:Set[str], add:bool=False) -> None:
        """Update node selection."""
        if add:
            self.current_view.selected_ids.update(node_ids)
        else:
            self.current_view.selected_ids = node_ids.copy()

    def set_view_specific(self, key:str, value:Any) -> None:
        """Set view-specific state value."""
        self.current_view.view_specific[key] = value

    def get_view_specific(self, key:str, default:Any=None) -> Any:
        """Get view-specific state value."""
        return self.current_view.view_specific.get(key, default)

    def undo(self) -> bool:
        """Restore previous state."""
        if not self.view_history:
            return False
        self.current_view = self.view_history.pop()
        return True
