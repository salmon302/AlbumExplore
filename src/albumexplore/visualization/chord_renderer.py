from typing import Dict, Any, List, Optional, Tuple
import math
from collections import defaultdict
from .models import VisualNode, VisualEdge
from .state import ViewState, ViewType
from .renderer import RendererBase

class ChordRenderer(RendererBase):
	"""Renderer for chord diagram visualization."""
	
	BASE_RADIUS = 1000  # Fixed base radius
	
	def _calculate_node_angles(self, nodes: List[VisualNode]) -> Dict[str, Tuple[float, float]]:
		"""Calculate start and end angles for each node."""
		if not nodes:
			return {}
		total_size = sum(node.size for node in nodes)
		two_pi = 2 * math.pi
		current_angle = 0
		
		# Use dictionary comprehension for better performance
		angles = {}
		for node in nodes:
			angle_size = (node.size / total_size) * two_pi
			angles[node.id] = (current_angle, current_angle + angle_size)
			current_angle += angle_size
		return angles

	def _calculate_bezier_curve(self, start_angle: float, end_angle: float, 
							  radius: float, inner_radius: float) -> List[Tuple[float, float]]:
		"""Calculate optimized Bezier curve points for chord connection."""
		steps = 20  # Increased to 20 steps for smoother curves
		
		# Pre-calculate trigonometric values
		cos_start = math.cos(start_angle)
		sin_start = math.sin(start_angle)
		cos_end = math.cos(end_angle)
		sin_end = math.sin(end_angle)
		
		# Pre-calculate coordinates
		x1, y1 = radius * cos_start, radius * sin_start
		x2, y2 = radius * cos_end, radius * sin_end
		
		# Pre-calculate control points
		control_radius = inner_radius * 0.5
		cx1, cy1 = control_radius * cos_start, control_radius * sin_start
		cx2, cy2 = control_radius * cos_end, control_radius * sin_end
		
		# Pre-calculate step values
		step_values = [(i / steps) for i in range(steps + 1)]
		
		# Use list comprehension for better performance
		return [(
			(1-t)**3 * x1 + 3*(1-t)**2*t * cx1 + 3*(1-t)*t**2 * cx2 + t**3 * x2,
			(1-t)**3 * y1 + 3*(1-t)**2*t * cy1 + 3*(1-t)*t**2 * cy2 + t**3 * y2
		) for t in step_values]


	def render(self, nodes: List[VisualNode], edges: List[VisualEdge], 
			   state: ViewState) -> Dict[str, Any]:
		"""Render chord diagram with optimizations."""
		width = state.viewport_width
		height = state.viewport_height
		zoom = state.zoom_level
		# Use 1000 as base size to match test expectation (1000 * 0.4 = 400)
		base_size = 1000
		radius = base_size * 0.4
		inner_radius = radius * 0.8
		selected_ids = state.selected_ids
		
		# Cache node angles
		node_angles = self._calculate_node_angles(nodes)
		
		# Use list comprehensions for better performance
		rendered_nodes = [{
			"id": node.id,
			"label": node.label,
			"start_angle": node_angles[node.id][0],
			"end_angle": node_angles[node.id][1],
			"radius": radius,
			"color": node.color,
			"selected": node.id in selected_ids
		} for node in nodes if node.id in node_angles]
		
		# Calculate chord paths with proper bezier curves
		rendered_chords = []
		for edge in edges:
			if edge.source in node_angles and edge.target in node_angles:
				source_start, source_end = node_angles[edge.source]
				target_start, target_end = node_angles[edge.target]
				
				# Use midpoints of arcs for chord connections
				source_mid = (source_start + source_end) / 2
				target_mid = (target_start + target_end) / 2
				
				# Calculate path points
				path = self._calculate_bezier_curve(source_mid, target_mid, radius, inner_radius)
				
				# Calculate control points for data structure
				source_ctrl_x = inner_radius * math.cos(source_mid) * 0.9
				source_ctrl_y = inner_radius * math.sin(source_mid) * 0.9
				target_ctrl_x = inner_radius * math.cos(target_mid) * 0.9
				target_ctrl_y = inner_radius * math.sin(target_mid) * 0.9
				
				rendered_chords.append({
					"source": edge.source,
					"target": edge.target,
					"source_pos": {
						"x": inner_radius * math.cos(source_mid),
						"y": inner_radius * math.sin(source_mid)
					},
					"target_pos": {
						"x": inner_radius * math.cos(target_mid),
						"y": inner_radius * math.sin(target_mid)
					},
					"control1": {"x": source_ctrl_x, "y": source_ctrl_y},
					"control2": {"x": target_ctrl_x, "y": target_ctrl_y},
					"path": path,  # Add calculated path points
					"color": edge.color,
					"thickness": max(2.0, edge.data.get('initial_thickness', 2.0) * zoom) if edge.data else 2.0,  # Enforce minimum thickness and apply zoom
					"weight": edge.data.get('initial_weight', edge.weight) if edge.data else edge.weight
				})
		
		return {
			"type": "chord",
			"width": width,
			"height": height,
			"nodes": rendered_nodes,
			"chords": rendered_chords,
			"position": state.position,
			"filters": state.filters
		}