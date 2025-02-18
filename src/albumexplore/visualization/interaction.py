from typing import Dict, Any, Optional, Set
from .state import StateManager


class InteractionHandler:
	def __init__(self, state_manager: StateManager):
		self.state_manager = state_manager
		self.drag_start: Optional[Dict[str, float]] = None
		self.selected_ids: Set[str] = set()

	def handle_zoom(self, delta: float, center: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
		"""Handle zoom interaction."""
		current_zoom = self.state_manager.current_view.zoom_level
		new_zoom = max(0.1, min(current_zoom * (1 + delta), 5.0))
		self.state_manager.update_zoom(new_zoom)
		
		result = {"zoom_level": new_zoom}
		
		if center:
			current_pos = self.state_manager.current_view.position
			scale_change = new_zoom / current_zoom
			new_x = center["x"] - (center["x"] - current_pos["x"]) * scale_change
			new_y = center["y"] - (center["y"] - current_pos["y"]) * scale_change
			self.state_manager.update_position(new_x, new_y)
			result["position"] = {"x": new_x, "y": new_y}
		
		return result

	def start_drag(self, position: Dict[str, float]) -> None:
		"""Start drag interaction."""
		self.drag_start = position

	def update_drag(self, position: Dict[str, float]) -> Dict[str, Any]:
		"""Handle drag interaction."""
		if not self.drag_start:
			return {}
		dx = position["x"] - self.drag_start["x"]
		dy = position["y"] - self.drag_start["y"]
		current_pos = self.state_manager.current_view.position
		new_x = current_pos["x"] + dx
		new_y = current_pos["y"] + dy
		self.state_manager.update_position(new_x, new_y)
		self.drag_start = position
		return {"position": {"x": new_x, "y": new_y}}

	def end_drag(self) -> None:
		"""End drag interaction."""
		self.drag_start = None

	def handle_click(self, position: Dict[str, float], multi_select: bool = False) -> Dict[str, Any]:
		"""Handle click interaction."""
		clicked_node = self._find_node_at_position(position)
		if clicked_node:
			if multi_select:
				if clicked_node in self.selected_ids:
					self.selected_ids.remove(clicked_node)
				else:
					self.selected_ids.add(clicked_node)
			else:
				self.selected_ids = {clicked_node}
			self.state_manager.select_nodes(self.selected_ids)
		elif not multi_select:
			self.selected_ids.clear()
			self.state_manager.select_nodes(set())
		return {"selected_ids": list(self.selected_ids)}

	def _find_node_at_position(self, position: Dict[str, float]) -> Optional[str]:
		"""Find node at given position."""
		current_view = self.state_manager.current_view
		zoom = current_view.zoom_level
		view_pos = current_view.position
		x = (position["x"] + view_pos["x"]) / zoom
		y = (position["y"] + view_pos["y"]) / zoom
		for node in self.state_manager.nodes:
			node_x = node.data.get("x", 0)
			node_y = node.data.get("y", 0)
			size = node.size * zoom
			if (x - node_x)**2 + (y - node_y)**2 <= size**2:
				return node.id
		return None

