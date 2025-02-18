from typing import Dict, Any, List, Optional
from .models import VisualNode, VisualEdge

class InfoDisplay:
	"""System for displaying information about visualization elements."""
	
	def get_node_details(self, node: VisualNode) -> Dict[str, Any]:
		"""Get detailed information about a node."""
		details = {
			"id": node.id,
			"label": node.label,
			"type": node.data.get("type", "unknown")
		}
		
		if node.data.get("type") == "album":
			details.update({
				"artist": node.data.get("artist", ""),
				"title": node.data.get("title", ""),
				"year": node.data.get("year", ""),
				"genre": node.data.get("genre", ""),
				"tags": node.data.get("tags", []),
				"length": node.data.get("length", ""),
				"connections": node.size
			})
		
		return details
	
	def get_edge_details(self, edge: VisualEdge) -> Dict[str, Any]:
		"""Get detailed information about an edge."""
		return {
			"source": edge.source,
			"target": edge.target,
			"weight": edge.weight,
			"shared_tags": edge.data.get("shared_tags", []),
			"strength": edge.weight,
			"type": edge.data.get("type", "connection")
		}
	
	def get_selection_summary(self, nodes: List[VisualNode], edges: List[VisualEdge]) -> Dict[str, Any]:
		"""Get summary information about selected elements."""
		return {
			"node_count": len(nodes),
			"edge_count": len(edges),
			"genres": list(set(node.data.get("genre", "") for node in nodes if "genre" in node.data)),
			"years": list(set(node.data.get("year", "") for node in nodes if "year" in node.data)),
			"total_connections": sum(edge.weight for edge in edges),
			"average_connection_strength": sum(edge.weight for edge in edges) / len(edges) if edges else 0
		}
	
	def get_view_statistics(self, nodes: List[VisualNode], edges: List[VisualEdge]) -> Dict[str, Any]:
		"""Get statistical information about the current view."""
		genres = {}
		years = {}
		tags = {}
		
		for node in nodes:
			if "genre" in node.data:
				genre = node.data["genre"]
				genres[genre] = genres.get(genre, 0) + 1
			
			if "year" in node.data:
				year = node.data["year"]
				years[year] = years.get(year, 0) + 1
			
			if "tags" in node.data:
				for tag in node.data["tags"]:
					tags[tag] = tags.get(tag, 0) + 1
		
		return {
			"total_nodes": len(nodes),
			"total_edges": len(edges),
			"genre_distribution": genres,
			"year_distribution": years,
			"tag_distribution": tags,
			"average_connections": len(edges) * 2 / len(nodes) if nodes else 0,
			"density": len(edges) / (len(nodes) * (len(nodes) - 1) / 2) if len(nodes) > 1 else 0
		}