from typing import Dict, Any, List, Set, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from .models import VisualNode, VisualEdge
from .state import ViewType, ViewState

class TransitionType(Enum):
	NONE = "none"
	INSTANT = "instant"
	FADE = "fade"
	MORPH = "morph"

@dataclass
class ViewTransition:
	source_type: ViewType
	target_type: ViewType
	transition_type: TransitionType
	duration_ms: int = 300
	easing: str = "ease-in-out"

class ViewIntegrationManager:
	"""Manages cross-view integration and transitions."""
	
	def __init__(self):
		self.transition_configs: Dict[tuple[ViewType, ViewType], ViewTransition] = {}
		self.shared_selections: Set[str] = set()
		self.view_sync_handlers: Dict[ViewType, List[Callable]] = {}
		self._transition_cache = {}  # Cache for transition data
		self._last_positions = {}    # Cache for last known positions
		self._init_default_transitions()
	
	def _init_default_transitions(self) -> None:
		"""Initialize default transition configurations."""
		# Table to Network: Morph rows into nodes
		self.transition_configs[(ViewType.TABLE, ViewType.NETWORK)] = ViewTransition(
			ViewType.TABLE, ViewType.NETWORK, TransitionType.MORPH, 500
		)
		# Network to Chord: Fade with position preservation
		self.transition_configs[(ViewType.NETWORK, ViewType.CHORD)] = ViewTransition(
			ViewType.NETWORK, ViewType.CHORD, TransitionType.FADE, 300
		)
		# Chord to Arc: Morph with circular unwrapping
		self.transition_configs[(ViewType.CHORD, ViewType.ARC)] = ViewTransition(
			ViewType.CHORD, ViewType.ARC, TransitionType.MORPH, 400
		)
	
	def register_sync_handler(self, view_type: ViewType, handler: Callable) -> None:
		"""Register a handler for view synchronization events."""
		if view_type not in self.view_sync_handlers:
			self.view_sync_handlers[view_type] = []
		self.view_sync_handlers[view_type].append(handler)
	
	def get_transition_config(self, source: ViewType, target: ViewType) -> ViewTransition:
		"""Get transition configuration for view switch."""
		key = (source, target)
		if key in self.transition_configs:
			return self.transition_configs[key]
		# Default to instant transition if not configured
		return ViewTransition(source, target, TransitionType.INSTANT)
	
	def prepare_transition(self, nodes: List[VisualNode], edges: List[VisualEdge],
						 source_state: ViewState, target_type: ViewType) -> Dict[str, Any]:
		"""Prepare transition with improved smoothness."""
		transition = self.get_transition_config(source_state.view_type, target_type)
		cache_key = (source_state.view_type, target_type)
		
		# Initialize positions with last known positions
		node_positions = self._last_positions.copy()
		
		# Update positions based on transition type
		if transition.transition_type == TransitionType.MORPH:
			for node in nodes:
				if not isinstance(node.data, dict):
					node.data = {}
				if not hasattr(node, 'pos'):
					node.pos = {}
				
				# Use existing position or smoothly interpolate from last known position
				if node.id in self._last_positions:
					last_pos = self._last_positions[node.id]
					current_x = node.data.get('x', last_pos['x'])
					current_y = node.data.get('y', last_pos['y'])
					# Smooth interpolation
					x = last_pos['x'] + (current_x - last_pos['x']) * 0.7
					y = last_pos['y'] + (current_y - last_pos['y']) * 0.7
				else:
					x = node.data.get('x', 0)
					y = node.data.get('y', 0)
				
				# Update all position references
				node.data['x'] = x
				node.data['y'] = y
				node.data['pos'] = {'x': x, 'y': y}
				node.pos['x'] = x
				node.pos['y'] = y
				node_positions[node.id] = {'x': x, 'y': y}
		
		# Store positions for next transition
		self._last_positions = node_positions
		
		# Prepare transition data with easing
		transition_data = {
			'transition': {
				'type': transition.transition_type.value,
				'duration': transition.duration_ms,
				'easing': 'cubic-bezier(0.4, 0.0, 0.2, 1)',  # Smooth easing
			},
			'preserved_positions': node_positions,
			'shared_selections': list(self.shared_selections),
			'source_type': source_state.view_type.value,
			'target_type': target_type.value
		}
		
		# Cache transition data
		self._transition_cache[cache_key] = transition_data
		return transition_data

	
	def sync_selection(self, selected_ids: Set[str], source_type: ViewType) -> None:
		"""Synchronize selection across views."""
		self.shared_selections = selected_ids
		
		# Notify other views
		for view_type, handlers in self.view_sync_handlers.items():
			if view_type != source_type:
				for handler in handlers:
					handler(selected_ids)
	
	def get_shared_state(self) -> Dict[str, Any]:
		"""Get shared state across views."""
		return {
			'selections': list(self.shared_selections),
			'active_transitions': [
				{
					'source': t.source_type.value,
					'target': t.target_type.value,
					'type': t.transition_type.value
				}
				for t in self.transition_configs.values()
			]
		}