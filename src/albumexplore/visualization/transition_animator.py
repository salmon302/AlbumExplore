from typing import Dict, Any, List
from PyQt6.QtCore import QObject, QPointF
from .models import VisualNode, VisualEdge
from .state import ViewType
from albumexplore.gui.animations import ViewTransitionAnimator, NodeAnimation

class TransitionAnimator(QObject):
	"""Manages animated transitions with improved smoothness."""
	
	def __init__(self):
		super().__init__()
		self.animator = ViewTransitionAnimator()
		self._last_positions = {}  # Cache for last known positions
		self._animation_duration = 300  # Default duration
		self._easing_curve = 'cubic-bezier(0.4, 0.0, 0.2, 1)'  # Smooth easing
	
	def animate_transition(self, nodes: Dict[str, Any], target_positions: Dict[str, Dict[str, float]], 
						 transition_type: str, duration: int) -> None:
		"""Animate transition with smooth interpolation."""
		# Update duration and ensure it's not too short
		self._animation_duration = max(300, duration)
		
		# Process each node
		for node_id, node in nodes.items():
			# Initialize data structures
			if not hasattr(node, 'data') or not isinstance(node.data, dict):
				node.data = {}
			if not hasattr(node, 'pos'):
				node.pos = {}
			
			# Get target position
			if node_id in target_positions:
				target_pos = target_positions[node_id]
				
				# Get current position or use last known position
				current_x = node.data.get('x', self._last_positions.get(node_id, {}).get('x', 0))
				current_y = node.data.get('y', self._last_positions.get(node_id, {}).get('y', 0))
				
				# Smooth interpolation for initial position
				if node_id in self._last_positions:
					last_pos = self._last_positions[node_id]
					current_x = last_pos['x'] + (current_x - last_pos['x']) * 0.7
					current_y = last_pos['y'] + (current_y - last_pos['y']) * 0.7
				
				# Update all position references
				node.data['x'] = current_x
				node.data['y'] = current_y
				node.data['pos'] = {'x': current_x, 'y': current_y}
				node.pos['x'] = current_x
				node.pos['y'] = current_y
				
				# Store for next transition
				self._last_positions[node_id] = target_pos
		
		# Start animation based on type
		if transition_type == "morph":
			self.animator.morph_nodes(nodes, target_positions, self._animation_duration, self._easing_curve)
		elif transition_type == "fade":
			# Use shorter duration for fade to feel more responsive
			fade_duration = min(200, self._animation_duration)
			self.animator.fade_nodes(nodes, True, fade_duration, self._easing_curve)
	
	def cancel_animations(self) -> None:
		"""Cancel animations and clean up."""
		self.animator.clear()
		# Don't clear position cache to maintain continuity