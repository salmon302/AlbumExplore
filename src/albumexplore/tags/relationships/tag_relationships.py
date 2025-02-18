from typing import Dict, List, Set, Tuple
import networkx as nx

class TagRelationships:
	"""Manages relationships between tags."""

	def __init__(self):
		self.graph = nx.Graph()
		self.hierarchies: Dict[str, str] = {}  # child -> parent
		self._initialize_relationships()

	def _initialize_relationships(self):
		"""Initialize basic tag relationships and hierarchies."""
		# Base genre hierarchies
		base_hierarchies = {
			'melodic death metal': 'death metal',
			'technical death metal': 'death metal',
			'atmospheric black metal': 'black metal',
			'progressive metal': 'metal',
			'death metal': 'metal',
			'black metal': 'metal',
		}
		
		# Add hierarchies
		for child, parent in base_hierarchies.items():
			self.add_hierarchy(child, parent)
		
		# Add relationships with weights
		self.add_relationship('atmospheric', 'black metal', weight=0.8)
		self.add_relationship('technical', 'death metal', weight=0.8)
		self.add_relationship('progressive', 'metal', weight=0.7)

	def add_hierarchy(self, child: str, parent: str):
		"""Add a hierarchical relationship between tags."""
		self.hierarchies[child] = parent
		self.graph.add_edge(child, parent, type='hierarchy', weight=1.0)

	def add_relationship(self, tag1: str, tag2: str, weight: float = 0.5):
		"""Add a weighted relationship between tags."""
		self.graph.add_edge(tag1, tag2, type='related', weight=weight)

	def get_related_tags(self, tag: str, min_weight: float = 0.0) -> List[Tuple[str, float]]:
		"""Get related tags with their relationship strengths."""
		if tag not in self.graph:
			return []
		
		related = []
		for neighbor in self.graph.neighbors(tag):
			weight = self.graph[tag][neighbor]['weight']
			if weight >= min_weight:
				related.append((neighbor, weight))
		
		return sorted(related, key=lambda x: x[1], reverse=True)

	def get_parent_tags(self, tag: str) -> List[str]:
		"""Get all parent tags in hierarchy."""
		parents = []
		current = tag
		while current in self.hierarchies:
			parent = self.hierarchies[current]
			parents.append(parent)
			current = parent
		return parents

	def get_child_tags(self, tag: str) -> List[str]:
		"""Get immediate child tags in hierarchy."""
		return [child for child, parent in self.hierarchies.items() if parent == tag]

	def calculate_similarity(self, tag1: str, tag2: str) -> float:
		"""Calculate similarity between two tags."""
		if tag1 == tag2:
			return 1.0
			
		try:
			# Use shortest path length as a similarity measure
			path_length = nx.shortest_path_length(
				self.graph, tag1, tag2, weight='weight'
			)
			return 1.0 / (1.0 + path_length)
		except nx.NetworkXNoPath:
			return 0.0