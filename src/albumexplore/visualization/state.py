"""State management for visualization system."""
from typing import Dict, Any, List, Set
from dataclasses import dataclass, field
from enum import Enum, auto

class ViewType(Enum):
    """Available view types."""
    TABLE = "Table"
    NETWORK = "Network"
    CHORD = "Chord"
    ARC = "Arc"
    TAG_EXPLORER = "Tag Explorer"

class TransitionType(Enum):
    """Available transition types."""
    INSTANT = auto()
    FADE = auto()
    MORPH = auto()

@dataclass
class ViewState:
    """State for a single view."""
    view_type: ViewType
    filters: Dict[str, Any] = field(default_factory=dict)
    selected_ids: Set[str] = field(default_factory=set)
    zoom_level: float = 1.0
    position: Dict[str, float] = field(default_factory=lambda: {"x": 0.0, "y": 0.0})
    viewport_width: float = 800.0
    viewport_height: float = 600.0
    view_specific: Dict[str, Any] = field(default_factory=dict)
    _position_history: List[Dict[str, float]] = field(default_factory=list, repr=False)
    
    def update_position(self, x: float, y: float):
        """Update position with smoothing."""
        # Keep position history for smoothing
        self._position_history.append(self.position.copy())
        if len(self._position_history) > 3:
            self._position_history.pop(0)
        
        # Calculate smoothed position
        if len(self._position_history) > 1:
            weights = [i + 1 for i in range(len(self._position_history))]
            total_weight = sum(weights)
            
            smooth_x = sum(p["x"] * w for p, w in zip(self._position_history, weights)) / total_weight
            smooth_y = sum(p["y"] * w for p, w in zip(self._position_history, weights)) / total_weight
            
            # Mix current and smoothed position
            self.position["x"] = 0.7 * x + 0.3 * smooth_x
            self.position["y"] = 0.7 * y + 0.3 * smooth_y
        else:
            self.position["x"] = x
            self.position["y"] = y

class StateManager:
    """Manages visualization state and history."""
    
    def __init__(self):
        # Initialize with default table view
        self.current_view = ViewState(ViewType.TABLE)
        self.view_history: List[ViewState] = []
        self._undo_stack: List[ViewState] = []
        self._max_history = 20
        
    def switch_view(self, view_type: ViewType):
        """Switch to a different view type."""
        # Save current state to history
        self.view_history.append(self.current_view)
        if len(self.view_history) > self._max_history:
            self.view_history.pop(0)
        
        # Create new view state
        self.current_view = ViewState(
            view_type,
            filters=self.current_view.filters.copy(),
            selected_ids=self.current_view.selected_ids.copy()
        )
    
    def update_filters(self, filters: Dict[str, Any]):
        """Update view filters."""
        # Save current state for undo
        self._undo_stack.append(self.current_view)
        if len(self._undo_stack) > self._max_history:
            self._undo_stack.pop(0)
        
        # Update filters
        self.current_view.filters.update(filters)
    
    def select_nodes(self, node_ids: Set[str]):
        """Update selected nodes."""
        # Save current state for undo
        self._undo_stack.append(self.current_view)
        if len(self._undo_stack) > self._max_history:
            self._undo_stack.pop(0)
        
        self.current_view.selected_ids = node_ids
    
    def undo(self) -> bool:
        """Undo last change."""
        if not self._undo_stack:
            return False
        
        self.current_view = self._undo_stack.pop()
        return True
    
    def update_viewport(self, width: float, height: float):
        """Update viewport dimensions."""
        self.current_view.viewport_width = width
        self.current_view.viewport_height = height
