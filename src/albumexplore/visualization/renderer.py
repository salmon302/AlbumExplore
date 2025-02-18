from abc import ABC, abstractmethod
import math
from typing import Dict, Any, List, Optional
from .models import VisualNode, VisualEdge
from .state import ViewState, ViewType
from .layout import Point
from .views.base_view import BaseView


class RendererBase(ABC):
	"""Base class for visualization renderers."""
	
	@abstractmethod
	def render(self, nodes: List[VisualNode], edges: List[VisualEdge], 
			   state: ViewState) -> Dict[str, Any]:
		"""Render visualization with current state."""
		pass

	def _get_node_position(self, node: VisualNode, state: ViewState) -> Dict[str, float]:
		if hasattr(node, 'pos') and isinstance(node.pos, dict):
			return {'x': float(node.pos.get('x', 0)), 'y': float(node.pos.get('y', 0))}
		return {'x': float(node.data.get('x', 0)), 'y': float(node.data.get('y', 0))}






class TableRenderer(RendererBase):
	"""Renderer for table view."""
	
	def render(self, nodes: List[VisualNode], edges: List[VisualEdge], 
			   state: ViewState) -> Dict[str, Any]:
		rows = [
			{
				"id": node.id,
				"artist": node.data.get("artist", ""),
				"title": node.data.get("title", ""),
				"year": node.data.get("year", ""),
				"tags": node.data.get("tags", []),
				"selected": node.id in state.selected_ids
			}
			for node in nodes
			if node.data.get("type") == "row"
		]
		sort_info = state.view_specific.get("sort", {})
		return {
			"type": "table",
			"rows": rows,
			"filters": state.filters,
			"columns": state.view_specific.get("columns", ["artist", "title", "year", "tags"]),
			"sort": {
				"column": sort_info.get("column"),
				"direction": sort_info.get("direction", "asc")
			},
			"sortable_columns": ["artist", "title", "year"]
		}


class NetworkRenderer(RendererBase):
	"""Renderer for force-directed network graph."""
	
	def __init__(self):
		self._last_render = None
		self._last_state_hash = None
		
	def _compute_state_hash(self, nodes, edges, state):
		"""Compute hash of current state to detect changes."""
		return hash((
			tuple((n.id, n.size, n.color) for n in nodes),
			tuple((e.source, e.target, e.weight) for e in edges),
			state.zoom_level,
			state.position['x'],
			state.position['y']
		))
	
	def render(self, nodes: List[VisualNode], edges: List[VisualEdge], 
			   state: ViewState) -> Dict[str, Any]:
		# Return empty visualization when there are no nodes
		if not nodes:
			self._last_render = None
			return {
				"type": "network",
				"nodes": [],
				"edges": [],
				"zoom": state.zoom_level,
				"position": state.position,
				"filters": state.filters,
				"viewport": {
					"width": state.viewport_width,
					"height": state.viewport_height
				}
			}

		# Check if we can reuse last render
		current_hash = self._compute_state_hash(nodes, edges, state)
		if self._last_render and current_hash == self._last_state_hash:
			return self._last_render

		preserved_positions = state.view_specific.get("positions", {})
		node_size_scale = state.view_specific.get("node_size_scale", 1.0)
		show_labels = state.view_specific.get("show_labels", True)
		edge_thickness_scale = state.view_specific.get("edge_thickness_scale", 1.0)
		
		rendered_nodes = []
		current_positions = {}
		selected_ids = state.selected_ids
		
		# Process nodes in a stable order
		sorted_nodes = sorted(nodes, key=lambda n: n.id)
		for node in sorted_nodes:
			base_pos = preserved_positions.get(node.id) or self._get_node_position(node, state)
			pos = {
				'x': base_pos['x'] + state.position['x'],
				'y': base_pos['y'] + state.position['y']
			}
			current_positions[node.id] = pos
			rendered_nodes.append({
				"id": node.id,
				"label": node.label if show_labels else "",
				"size": node.size * state.zoom_level * node_size_scale,
				"color": node.color,
				"shape": node.shape,
				"selected": node.id in selected_ids,
				"x": pos["x"],
				"y": pos["y"],
				"data": node.data
			})
		
		# Process edges in a stable order
		sorted_edges = sorted(edges, key=lambda e: (e.source, e.target))
		rendered_edges = [
			{
				"source": edge.source,
				"target": edge.target,
				"weight": edge.data.get('initial_weight', edge.weight) if edge.data else edge.weight,
				"color": edge.color,
				"thickness": (edge.data.get('initial_thickness', edge.thickness) if edge.data else edge.thickness) 
							* state.zoom_level * edge_thickness_scale,
				"data": edge.data
			}
			for edge in sorted_edges
		]
		
		state.view_specific["positions"] = current_positions
		
		result = {
			"type": "network",
			"nodes": rendered_nodes,
			"edges": rendered_edges,
			"zoom": state.zoom_level,
			"position": state.position,
			"filters": state.filters,
			"viewport": {
				"width": state.viewport_width,
				"height": state.viewport_height
			}
		}
		
		self._last_render = result
		self._last_state_hash = current_hash
		return result


class ChordRenderer(RendererBase):
	"""Renderer for chord diagram."""
	
	def render(self, nodes: List[VisualNode], edges: List[VisualEdge], 
			   state: ViewState) -> Dict[str, Any]:
		# Return empty visualization when there are no nodes
		if not nodes:
			return {
				"type": "chord",
				"nodes": [],
				"chords": [],
				"zoom": state.zoom_level,
				"position": state.position,
				"viewport": {"width": state.viewport_width, "height": state.viewport_height},
				"filters": state.filters
			}

		radius = min(state.viewport_width, state.viewport_height) / 3
		inner_radius = radius * 0.7
		total_size = sum(node.size for node in nodes)
		current_angle = 0
		rendered_nodes = []
		node_angles = {}
		show_labels = state.view_specific.get("show_labels", True)
		node_size_scale = state.view_specific.get("node_size_scale", 1.0)
		edge_thickness_scale = state.view_specific.get("edge_thickness_scale", 1.0)
		
		# Pre-calculate gap
		gap = 2 * math.pi * 0.1 / len(nodes)
		
		for node in nodes:
			angle_size = (node.size / total_size) * 2 * math.pi * 0.9
			node_angles[node.id] = (current_angle, current_angle + angle_size)
			mid_angle = current_angle + angle_size/2
			x = radius * math.cos(mid_angle)
			y = radius * math.sin(mid_angle)
			
			rendered_nodes.append({
				"id": node.id,
				"label": node.label if show_labels else "",
				"size": node.size * node_size_scale,
				"color": node.color,
				"selected": node.id in state.selected_ids,
				"radius": radius,
				"start_angle": current_angle,
				"end_angle": current_angle + angle_size,
				"x": x,
				"y": y
			})
			current_angle += angle_size + gap
		
		state.view_specific["positions"] = {
			node["id"]: {"x": node["x"], "y": node["y"]}
			for node in rendered_nodes
		}
		
		rendered_edges = []
		for edge in edges:
			if edge.source in node_angles and edge.target in node_angles:
				source_angles = node_angles[edge.source]
				target_angles = node_angles[edge.target]
				source_mid = (source_angles[0] + source_angles[1]) / 2
				target_mid = (target_angles[0] + target_angles[1]) / 2
				
				source_x = inner_radius * math.cos(source_mid)
				source_y = inner_radius * math.sin(source_mid)
				target_x = inner_radius * math.cos(target_mid)
				target_y = inner_radius * math.sin(target_mid)
				
				rendered_edges.append({
					"source": edge.source,
					"target": edge.target,
					"source_pos": {"x": source_x, "y": source_y},
					"target_pos": {"x": target_x, "y": target_y},
					"control1": {"x": source_x * 0.8, "y": source_y * 0.8},
					"control2": {"x": target_x * 0.8, "y": target_y * 0.8},
					"color": edge.color,
					"thickness": max(1, edge.thickness * edge_thickness_scale),
					"weight": edge.weight
				})
		
		return {
			"type": "chord",
			"nodes": rendered_nodes,
			"chords": rendered_edges,
			"zoom": state.zoom_level,
			"position": state.position,
			"viewport": {"width": state.viewport_width, "height": state.viewport_height},
			"filters": state.filters
		}

class ArcRenderer(RendererBase):
	"""Renderer for arc diagram."""
	
	def render(self, nodes: List[VisualNode], edges: List[VisualEdge], 
			   state: ViewState) -> Dict[str, Any]:
		# Return empty visualization when there are no nodes
		if not nodes:
			return {
				"type": "arc",
				"nodes": [],
				"arcs": [],
				"zoom": state.zoom_level,
				"position": state.position,
				"viewport": {"width": state.viewport_width, "height": state.viewport_height},
				"filters": state.filters
			}

		width = state.viewport_width * 0.8
		height = state.viewport_height * 0.8
		base_y = height / 2
		spacing = width / (len(nodes) + 1)
		show_labels = state.view_specific.get("show_labels", True)
		node_size_scale = state.view_specific.get("node_size_scale", 1.0)
		edge_thickness_scale = state.view_specific.get("edge_thickness_scale", 1.0)
		selected_ids = state.selected_ids
		
		node_positions = {}
		rendered_nodes = []
		
		for i, node in enumerate(nodes, 1):
			x = spacing * i
			pos = {"x": x, "y": base_y}
			node_positions[node.id] = pos
			rendered_nodes.append({
				"id": node.id,
				"label": node.label if show_labels else "",
				"size": node.size * node_size_scale,
				"color": node.color,
				"selected": node.id in selected_ids,
				"x": x,
				"y": base_y
			})
		
		state.view_specific["positions"] = node_positions
		
		rendered_edges = []
		for edge in edges:
			if edge.source in node_positions and edge.target in node_positions:
				source_pos = node_positions[edge.source]
				target_pos = node_positions[edge.target]
				distance = abs(target_pos["x"] - source_pos["x"])
				control_y = base_y - distance * 0.5
				
				rendered_edges.append({
					"source": edge.source,
					"target": edge.target,
					"path": [
						(source_pos["x"], source_pos["y"]),
						((source_pos["x"] + target_pos["x"]) / 2, control_y),
						(target_pos["x"], target_pos["y"])
					],
					"color": edge.color,
					"thickness": max(1, edge.thickness * edge_thickness_scale),
					"weight": edge.weight
				})
		
		return {
			"type": "arc",
			"nodes": rendered_nodes,
			"arcs": rendered_edges,
			"zoom": state.zoom_level,
			"position": state.position,
			"viewport": {"width": state.viewport_width, "height": state.viewport_height},
			"filters": state.filters
		}


def create_renderer(view_type: ViewType) -> RendererBase:
	"""Factory function to create appropriate renderer."""
	renderers = {
		ViewType.TABLE: TableRenderer,
		ViewType.NETWORK: NetworkRenderer,
		ViewType.CHORD: ChordRenderer,
		ViewType.ARC: ArcRenderer
	}
	renderer_class = renderers.get(view_type)
	if not renderer_class:
		raise ValueError(f"No renderer available for view type: {view_type}")
	return renderer_class()

def create_view(view_type: str, parent=None) -> BaseView:
	"""Create a view based on the view type."""
	if view_type == "network":
		from .views.enhanced_network_view import EnhancedNetworkView
		return EnhancedNetworkView(parent)
	elif view_type == "arc":
		from .views.arc_renderer import ArcRenderer
		return ArcRenderer(parent)
	elif view_type == "chord":
		from .views.chord_renderer import ChordRenderer
		return ChordRenderer(parent)
	elif view_type == "table":
		from .views.table_view import TableView
		return TableView(parent)
	else:
		raise ValueError(f"Unknown view type: {view_type}")