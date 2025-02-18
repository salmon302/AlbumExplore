from typing import Dict, List, Tuple, Optional
import copy
from dataclasses import dataclass
from enum import IntEnum
from .models import VisualNode, VisualEdge
from .state import ViewState, ViewType
import math
from collections import defaultdict

@dataclass
class Viewport:
	x: float
	y: float
	width: float
	height: float
	zoom: float

	def get_visible_area(self) -> float:
		"""Calculate visible area for density calculations"""
		return self.width * self.height * (1.0 / (self.zoom * self.zoom))

class DetailLevel(IntEnum):
	LOW = 0       # Basic shapes, no labels
	MEDIUM = 1    # Reduced labels, simplified edges
	HIGH = 2      # Full detail, all features

class ViewOptimizer:
	def __init__(self):
		self.detail_thresholds = {
			DetailLevel.HIGH: 0.8,    # zoom >= 0.8
			DetailLevel.MEDIUM: 0.4,   # 0.4 <= zoom < 0.8
			DetailLevel.LOW: 0.0      # zoom < 0.4
		}
		self.density_thresholds = {
			DetailLevel.HIGH: 0.001,    # nodes per pixel
			DetailLevel.MEDIUM: 0.005,
			DetailLevel.LOW: 0.01
		}
		self._detail_level_cache = {}
		self._edge_bundle_cache = {}
		self._visibility_cache = {}

	def get_detail_level(self, zoom: float, node_count: int, viewport: Viewport) -> DetailLevel:
		"""Determine detail level with caching."""
		cache_key = (round(zoom, 2), node_count, round(viewport.width), round(viewport.height))
		if cache_key in self._detail_level_cache:
			return self._detail_level_cache[cache_key]
			
		# Quick return for extreme cases
		if zoom < 0.2 or node_count > 1000:
			return DetailLevel.LOW
		if zoom > 1.5 and node_count < 100:
			return DetailLevel.HIGH
			
		# Calculate density efficiently
		visible_area = viewport.get_visible_area()
		density = node_count / visible_area if visible_area > 0 else float('inf')
		
		# Determine detail level
		result = DetailLevel.HIGH
		if density > self.density_thresholds[DetailLevel.LOW]:
			result = DetailLevel.LOW
		elif density > self.density_thresholds[DetailLevel.MEDIUM]:
			result = DetailLevel.MEDIUM
			
		self._detail_level_cache[cache_key] = result
		return result




	def optimize_nodes(self, nodes: List[VisualNode], viewport: Viewport) -> List[VisualNode]:
		"""Optimize nodes based on viewport and detail level"""
		detail_level = self.get_detail_level(viewport.zoom, len(nodes), viewport)
		visible_nodes = []

		for node in nodes:
			if self._is_in_viewport(node, viewport):
				optimized_node = self._optimize_node(node, detail_level)
				visible_nodes.append(optimized_node)

		return visible_nodes

	def optimize_edges(self, edges: List[VisualEdge], viewport: Viewport, 
					  view_type: ViewType) -> List[VisualEdge]:
		"""Optimize edges for rendering."""
		if not edges:
			return []

		detail_level = self.get_detail_level(viewport.zoom, len(edges), viewport)
		optimized = []

		# Bundle edges based on view type
		bundled_edges = self.bundle_edges(edges, view_type, detail_level)

		for edge in bundled_edges:
			if self._is_edge_in_viewport(edge, viewport):
				# Use initial thickness if available, otherwise use base thickness
				base_thickness = edge.data.get('initial_thickness', 2.0) if edge.data else 2.0
				
				# Create optimized edge with fixed thickness
				optimized_edge = copy.deepcopy(edge)
				optimized_edge.thickness = base_thickness
				optimized_edge.data.update({
					'optimized_thickness': base_thickness,
					'optimized_weight': edge.weight,
					'original_thickness': edge.thickness
				})
				optimized.append(optimized_edge)

		return self._filter_edge_crossings(optimized, detail_level)

	def bundle_edges(self, edges: List[VisualEdge], view_type: ViewType,
					detail_level: DetailLevel) -> List[VisualEdge]:
		"""Optimized edge bundling with caching."""
		if not edges:
			return []
			
		cache_key = (tuple(e.id for e in edges), view_type, detail_level)
		if cache_key in self._edge_bundle_cache:
			return self._edge_bundle_cache[cache_key]
			
		# Group edges by endpoints
		bundles = defaultdict(list)
		for edge in edges:
			key = tuple(sorted([edge.source, edge.target]))
			bundles[key].append(edge)
			
		# Create bundled edges efficiently
		result = []
		for edges_group in bundles.values():
			if len(edges_group) > 1:
				total_weight = sum(e.weight for e in edges_group)
				base_edge = edges_group[0]
				bundled_edge = VisualEdge(
					id=f"bundle_{base_edge.source}_{base_edge.target}",
					source=base_edge.source,
					target=base_edge.target,
					weight=total_weight,
					thickness=math.sqrt(len(edges_group)) * 2,
					color=base_edge.color,
					data={'bundle_size': len(edges_group)}
				)
				result.append(bundled_edge)
			else:
				result.extend(edges_group)
				
		self._edge_bundle_cache[cache_key] = result
		return result


	def is_node_visible(self, node: VisualNode, view_bounds: Dict) -> bool:
		"""Check if node is within view bounds."""
		x = float(node.data.get("x", 0))
		y = float(node.data.get("y", 0))
		margin = 50 * view_bounds['zoom']  # Margin to prevent pop-in
		
		return not (x < view_bounds['x'] - margin or 
				   x > view_bounds['x'] + view_bounds['width'] + margin or
				   y < view_bounds['y'] - margin or 
				   y > view_bounds['y'] + view_bounds['height'] + margin)

	def is_edge_visible(self, edge: VisualEdge, view_bounds: Dict, view_type: ViewType, 
					   visibility_cache: Dict) -> bool:
		"""Check if edge is within view bounds."""
		margin = 100 * view_bounds['zoom']  # Margin to prevent pop-in
		
		# Get coordinates from edge data
		x1 = float(edge.data.get('source_x', 0))
		x2 = float(edge.data.get('target_x', 0))
		y1 = float(edge.data.get('source_y', 0))
		y2 = float(edge.data.get('target_y', 0))

		min_x = min(x1, x2)
		max_x = max(x1, x2)
		min_y = min(y1, y2)
		max_y = max(y1, y2)

		return (min_x <= view_bounds['x'] + view_bounds['width'] + margin and
				max_x >= view_bounds['x'] - margin and
				min_y <= view_bounds['y'] + view_bounds['height'] + margin and
				max_y >= view_bounds['y'] - margin)


	def _bundle_force_directed(self, edges: List[VisualEdge]) -> List[VisualEdge]:
		"""Simplified force-directed bundling for better performance."""
		if len(edges) < 2:
			return edges
			
		# Group by angle with reduced precision
		angle_groups = {}
		for edge in edges:
			dx = float(edge.data.get('target_x', 0)) - float(edge.data.get('source_x', 0))
			dy = float(edge.data.get('target_y', 0)) - float(edge.data.get('source_y', 0))
			# Reduce angle precision for faster grouping
			angle = int(math.degrees(math.atan2(dy, dx)) / 30) * 30
			
			if angle not in angle_groups:
				angle_groups[angle] = []
			angle_groups[angle].append(edge)
		
		# Create bundles more efficiently
		bundled = []
		for group in angle_groups.values():
			if len(group) > 1:
				total_weight = sum(e.weight for e in group)
				bundled.append(VisualEdge(
					source=group[0].source,
					target=group[0].target,
					weight=total_weight,
					thickness=math.sqrt(len(group)) * 2,
					color=group[0].color,
					data={'bundle_size': len(group)}
				))
			else:
				bundled.extend(group)
				
		return bundled

	def _create_bundle_edge(self, edges: List[VisualEdge]) -> VisualEdge:
		"""Create a representative edge for a bundle"""
		total_weight = sum(e.weight for e in edges)
		return VisualEdge(
			source=edges[0].source,
			target=edges[0].target,
			weight=total_weight,
			thickness=math.sqrt(len(edges)),
			color=edges[0].color,
			data={'bundle_size': len(edges)}
		)

	def _filter_edge_crossings(self, edges: List[VisualEdge], 
							 detail_level: DetailLevel) -> List[VisualEdge]:
		"""Filter out edge crossings based on detail level"""
		if detail_level in [DetailLevel.HIGH, DetailLevel.MEDIUM]:
			return edges
			
		# For LOW detail, keep only strongest connections
		sorted_edges = sorted(edges, key=lambda e: e.weight, reverse=True)
		return sorted_edges[:max(1, int(len(sorted_edges) * 0.5))]


	def _is_in_viewport(self, node: VisualNode, viewport: Viewport) -> bool:
		"""Check viewport visibility with caching."""
		cache_key = (node.id, viewport.x, viewport.y, viewport.zoom)
		if cache_key in self._visibility_cache:
			return self._visibility_cache[cache_key]
			
		x = float(node.data.get("x", 0))
		y = float(node.data.get("y", 0))
		margin = 50 * viewport.zoom
		
		result = not (x < viewport.x - margin or 
					 x > viewport.x + viewport.width + margin or
					 y < viewport.y - margin or 
					 y > viewport.y + viewport.height + margin)
					 
		self._visibility_cache[cache_key] = result
		return result

	def _is_edge_in_viewport(self, edge: VisualEdge, viewport: Viewport) -> bool:
		"""Check if edge intersects expanded viewport."""
		margin = 100 * viewport.zoom  # Add margin to prevent pop-in
		
		# Get coordinates from edge data
		x1 = float(edge.data.get('source_x', 0))
		x2 = float(edge.data.get('target_x', 0))
		y1 = float(edge.data.get('source_y', 0))
		y2 = float(edge.data.get('target_y', 0))

		min_x = min(x1, x2)
		max_x = max(x1, x2)
		min_y = min(y1, y2)
		max_y = max(y1, y2)

		return (min_x <= viewport.x + viewport.width + margin and
				max_x >= viewport.x - margin and
				min_y <= viewport.y + viewport.height + margin and
				max_y >= viewport.y - margin)

	def _optimize_node(self, node: VisualNode, detail_level: DetailLevel) -> VisualNode:
		"""Apply detail level optimizations to node."""
		if detail_level == DetailLevel.LOW:
			# Remove label and simplify shape
			node.label = ""
			node.shape = "circle"
		elif detail_level == DetailLevel.MEDIUM:
			# Shortened label
			if len(node.label) > 20:
				node.label = node.label[:17] + "..."
		return node

	def _optimize_edge(self, edge: VisualEdge, detail_level: DetailLevel, 
					  view_type: ViewType) -> VisualEdge:
		"""Apply detail level optimizations to edge."""
		# Ensure edge color is visible
		edge.color = '#1a1a1a'  # Darker color for better visibility
		return edge

