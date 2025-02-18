from typing import Dict, Any, List, Optional, Set
from .models import VisualNode, VisualEdge

class FilterSystem:
	"""System for filtering visualization elements."""
	
	def __init__(self):
		self.active_filters: Dict[str, Any] = {}
	
	def add_filter(self, filter_type: str, filter_value: Any) -> None:
		"""Add a filter to the system."""
		self.active_filters[filter_type] = filter_value
	
	def remove_filter(self, filter_type: str) -> None:
		"""Remove a filter from the system."""
		if filter_type in self.active_filters:
			del self.active_filters[filter_type]
	
	def clear_filters(self) -> None:
		"""Clear all active filters."""
		self.active_filters.clear()
	
	def filter_nodes(self, nodes: List[VisualNode]) -> List[VisualNode]:
		"""Apply filters to nodes."""
		filtered_nodes = nodes
		
		# Filter by tag
		if 'tag' in self.active_filters:
			tag = self.active_filters['tag']
			filtered_nodes = [
				node for node in filtered_nodes
				if 'tags' in node.data and tag in node.data['tags']
			]
		
		# Filter by year range
		if 'year_range' in self.active_filters:
			start_year, end_year = self.active_filters['year_range']
			filtered_nodes = [
				node for node in filtered_nodes
				if 'year' in node.data and start_year <= node.data['year'] <= end_year
			]
		
		# Filter by genre
		if 'genre' in self.active_filters:
			genre = self.active_filters['genre']
			filtered_nodes = [
				node for node in filtered_nodes
				if 'genre' in node.data and node.data['genre'] == genre
			]
		
		return filtered_nodes
	
	def filter_edges(self, edges: List[VisualEdge], visible_nodes: Set[str]) -> List[VisualEdge]:
		"""Filter edges based on visible nodes and edge properties."""
		filtered_edges = [
			edge for edge in edges
			if edge.source in visible_nodes and edge.target in visible_nodes
		]
		
		# Filter by minimum weight
		if 'min_weight' in self.active_filters:
			min_weight = self.active_filters['min_weight']
			filtered_edges = [
				edge for edge in filtered_edges
				if edge.weight >= min_weight
			]
		
		return filtered_edges
	
	def apply_filters(self, nodes: List[VisualNode], edges: List[VisualEdge]) -> tuple[List[VisualNode], List[VisualEdge]]:
		"""Apply all active filters to nodes and edges."""
		filtered_nodes = self.filter_nodes(nodes)
		visible_nodes = {node.id for node in filtered_nodes}
		filtered_edges = self.filter_edges(edges, visible_nodes)
		
		return filtered_nodes, filtered_edges