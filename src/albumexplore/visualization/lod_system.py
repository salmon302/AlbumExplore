from dataclasses import dataclass
from typing import List, Dict, Set, Tuple, Optional
from .models import VisualNode, VisualEdge
import math

@dataclass
class LODLevel:
	level: int
	node_threshold: int
	edge_threshold: int
	cluster_threshold: float
	visible_range: Tuple[float, float]
	edge_sampling_rate: float  # Add edge sampling rate

class LODSystem:
	def __init__(self):
		self.levels = [
			LODLevel(0, 50, 100, 0.1, (2.0, float('inf')), 1.0),     # Show all edges
			LODLevel(1, 75, 150, 0.2, (1.5, 2.0), 0.8),             # Show 80% edges
			LODLevel(2, 150, 300, 0.3, (1.0, 1.5), 0.5),            # Show 50% edges
			LODLevel(3, 300, 600, 0.4, (0.5, 1.0), 0.3),            # Show 30% edges
			LODLevel(4, 600, 1200, 0.5, (0.0, 0.5), 0.1)            # Show 10% edges
		]
		self._edge_cache = {}  # Cache for edge visibility
		
	def get_level_for_scale(self, scale: float) -> LODLevel:
		"""Get appropriate LOD level for current scale."""
		for level in self.levels:
			if level.visible_range[0] <= scale <= level.visible_range[1]:
				return level
		return self.levels[-1]  # Return lowest detail if no match

	def should_render_node(self, node: VisualNode, importance: float, level: LODLevel) -> bool:
		"""Determine if a node should be rendered at current LOD level."""
		return importance >= level.cluster_threshold

	def should_render_edge(self, edge: VisualEdge, importance: float, level: LODLevel) -> bool:
		"""Determine if an edge should be rendered with sampling."""
		cache_key = (edge.id, level.level)
		if cache_key not in self._edge_cache:
			# Deterministic sampling based on edge ID and importance
			sample_value = hash(str(edge.id)) % 100 / 100.0
			self._edge_cache[cache_key] = (
				sample_value <= level.edge_sampling_rate and 
				importance >= level.cluster_threshold
			)
		return self._edge_cache[cache_key]

class ClusterManager:
	def __init__(self, lod_system: LODSystem):
		self.lod_system = lod_system
		self.clusters: Dict[int, List[VisualNode]] = {}
		self.cluster_centers: Dict[int, Tuple[float, float]] = {}
		self.node_importance: Dict[str, float] = {}
		
	def calculate_node_importance(self, node: VisualNode, edges: List[VisualEdge]) -> float:
		"""Calculate node importance based on connections and metadata."""
		# Count edges connected to this node
		edge_count = sum(1 for edge in edges if edge.source == node.id or edge.target == node.id)
		
		# Base importance on edge count and node metadata
		importance = math.log(edge_count + 1) * 0.5
		
		# Add weight for node attributes (can be customized)
		if hasattr(node, 'weight'):
			importance += node.weight * 0.3
			
		return min(1.0, importance)

	def update_clusters(self, nodes: List[VisualNode], edges: List[VisualEdge], 
					   scale: float) -> Tuple[List[VisualNode], List[VisualEdge]]:
		"""Update clusters with optimized edge filtering."""
		level = self.lod_system.get_level_for_scale(scale)
		
		# Use set for faster lookups
		visible_node_ids = set()
		
		# Filter nodes first
		visible_nodes = []
		for node in nodes:
			importance = self.node_importance.get(node.id) or self.calculate_node_importance(node, edges)
			self.node_importance[node.id] = importance
			if self.lod_system.should_render_node(node, importance, level):
				visible_nodes.append(node)
				visible_node_ids.add(node.id)
		
		# Filter edges with sampling
		visible_edges = []
		edge_count = 0
		max_edges = level.edge_threshold
		
		for edge in edges:
			if (edge.source in visible_node_ids and 
				edge.target in visible_node_ids):
				importance = min(self.node_importance[edge.source], 
							   self.node_importance[edge.target])
				if (edge_count < max_edges and 
					self.lod_system.should_render_edge(edge, importance, level)):
					visible_edges.append(edge)
					edge_count += 1
		
		return visible_nodes, visible_edges