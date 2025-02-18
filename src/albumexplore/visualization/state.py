from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field
from enum import Enum

class ViewType(Enum):
	TABLE = "table"
	NETWORK = "network"
	ARC = "arc"
	CHORD = "chord"

@dataclass
class ViewState:
	"""State for visualization views with improved stability."""
	view_type: ViewType
	filters: Dict[str, Any] = field(default_factory=dict)
	selected_ids: Set[str] = field(default_factory=set)
	zoom_level: float = 1.0
	position: Dict[str, float] = field(default_factory=lambda: {"x": 0.0, "y": 0.0})
	viewport_width: float = 800.0
	viewport_height: float = 600.0
	view_specific: Dict[str, Any] = field(default_factory=dict)
	_position_history: List[Dict[str, float]] = field(default_factory=list)
	_history_length: int = 3

	def __post_init__(self):
		"""Initialize state after creation."""
		if not isinstance(self.filters, dict):
			self.filters = {}
		if not isinstance(self.position, dict):
			self.position = {"x": 0.0, "y": 0.0}
		if not isinstance(self.view_specific, dict):
			self.view_specific = {}
		self._position_history = [self.position.copy()]
		
		# Initialize view-specific defaults
		if self.view_type == ViewType.NETWORK:
			if "positions" not in self.view_specific:
				self.view_specific["positions"] = {}
			if "render_quality" not in self.view_specific:
				self.view_specific["render_quality"] = "high"

	def update_viewport(self, width: float, height: float) -> None:
		"""Update viewport dimensions."""
		self.viewport_width = width
		self.viewport_height = height

	def set_view_specific(self, key: str, value: Any) -> None:
		"""Set view-specific state property."""
		self.view_specific[key] = value

	def get_view_specific(self, key: str, default: Any = None) -> Any:
		"""Get view-specific state property."""
		return self.view_specific.get(key, default)

	def update_position(self, x: float, y: float) -> None:
		"""Update position with smoothing."""
		new_pos = {"x": x, "y": y}
		self._position_history.append(new_pos)
		
		if len(self._position_history) > self._history_length:
			self._position_history.pop(0)
		
		# Weighted average with more recent positions having higher weight
		weights = [i + 1 for i in range(len(self._position_history))]
		total_weight = sum(weights)
		
		smoothed_x = sum(pos["x"] * w for pos, w in zip(self._position_history, weights)) / total_weight
		smoothed_y = sum(pos["y"] * w for pos, w in zip(self._position_history, weights)) / total_weight
		
		self.position = {"x": smoothed_x, "y": smoothed_y}

	def update_zoom(self, target_zoom: float) -> None:
		"""Update zoom level with smoothing."""
		target = max(0.1, min(target_zoom, 5.0))
		current = self.zoom_level
		# Smooth transition (70% of the way to target)
		self.zoom_level = current + (target - current) * 0.7

class StateManager:
	"""Manages state for visualization system."""
	
	def __init__(self):
		self.current_view: ViewState = ViewState(ViewType.TABLE)
		self.view_history: List[ViewState] = []
		self.max_history: int = 50
		# Initialize table sort state
		self.current_view.set_view_specific("sort", {"column": None, "direction": "asc"})
	
	def switch_view(self, view_type: ViewType) -> None:
		"""Switch to a different view type."""
		self._save_state()
		
		# Preserve current state
		view_specific = {}
		
		# Preserve sort state for table view
		sort_info = self.current_view.get_view_specific("sort")
		if sort_info:
			view_specific["sort"] = sort_info.copy()
		
		# Preserve positions for graph-based views
		if self.current_view.view_type in [ViewType.NETWORK, ViewType.CHORD, ViewType.ARC]:
			positions = self.current_view.get_view_specific("positions", {})
			if positions:
				view_specific["positions"] = positions.copy()
		
		# Create new view state with preserved data
		self.current_view = ViewState(
			view_type,
			filters=self.current_view.filters.copy(),
			selected_ids=self.current_view.selected_ids.copy(),
			zoom_level=self.current_view.zoom_level,
			position=self.current_view.position.copy(),
			viewport_width=self.current_view.viewport_width,
			viewport_height=self.current_view.viewport_height,
			view_specific=view_specific
		)
	
	def update_viewport(self, width: float, height: float) -> None:
		"""Update viewport dimensions."""
		self.current_view.update_viewport(width, height)
	
	def set_view_specific(self, key: str, value: Any) -> None:
		"""Set view-specific state property."""
		self.current_view.set_view_specific(key, value)
	
	def get_view_specific(self, key: str, default: Any = None) -> Any:
		"""Get view-specific state property."""
		return self.current_view.get_view_specific(key, default)
	
	def update_filters(self, filters: Dict[str, Any]) -> None:
		"""Update current view filters."""
		self._save_state()
		self.current_view.filters.update(filters)
	
	def select_nodes(self, node_ids: Set[str], add: bool = False) -> None:
		"""Select nodes in current view with optimized performance."""
		# Skip state save if selection hasn't changed
		if add:
			if not node_ids - self.current_view.selected_ids:
				return
		else:
			if self.current_view.selected_ids == node_ids:
				return
		
		# Save state only if we're making actual changes
		self._save_state()
		
		# Use set operations directly instead of update/assignment
		if add:
			self.current_view.selected_ids |= node_ids
		else:
			self.current_view.selected_ids = node_ids
	
	def update_zoom(self, zoom_level: float) -> None:
		"""Update zoom level."""
		self.current_view.zoom_level = max(0.1, min(zoom_level, 5.0))
	
	def update_position(self, x: float, y: float) -> None:
		"""Update view position."""
		self.current_view.position = {"x": x, "y": y}
	
	def set_table_sort(self, column: Optional[str], direction: str = "asc") -> None:
		"""Set table sorting state."""
		if self.current_view.view_type != ViewType.TABLE:
			return
		
		self._save_state()
		self.current_view.set_view_specific("sort", {
			"column": column,
			"direction": direction
		})
	
	def get_table_sort(self) -> Dict[str, Any]:
		"""Get current table sorting state."""
		sort_info = self.current_view.get_view_specific("sort", {})
		return {
			"column": sort_info.get("column"),
			"direction": sort_info.get("direction", "asc")
		}
	
	def undo(self) -> bool:
		"""Revert to previous state."""
		if self.view_history:
			self.current_view = self.view_history.pop()
			return True
		return False
	
	def _save_state(self) -> None:
		"""Save current state to history with optimized copying."""
		# Create new state with shallow copies where possible
		new_state = ViewState(
			view_type=self.current_view.view_type,
			filters=self.current_view.filters.copy(),
			selected_ids=set(self.current_view.selected_ids),  # Efficient set copy
			zoom_level=self.current_view.zoom_level,
			position=self.current_view.position.copy(),
			viewport_width=self.current_view.viewport_width,
			viewport_height=self.current_view.viewport_height,
			view_specific=self.current_view.view_specific.copy()
		)
		
		self.view_history.append(new_state)
		if len(self.view_history) > self.max_history:
			self.view_history.pop(0)
