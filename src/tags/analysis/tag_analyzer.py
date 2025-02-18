from typing import Dict, List, Set, Tuple
import pandas as pd
from collections import Counter
import networkx as nx
from ..normalizer import TagNormalizer

class TagAnalyzer:
	def __init__(self, df: pd.DataFrame):
		self.df = df
		self.tag_frequencies: Dict[str, int] = {}
		self.tag_relationships: Dict[Tuple[str, str], float] = {}
		self.tag_clusters: Dict[str, List[str]] = {}
		self.graph = nx.Graph()
		self.normalizer = TagNormalizer()
		self._initialize()

	def _initialize(self):
		"""Initialize tag analysis data structures."""
		# Normalize all tags first
		normalized_tags = []
		for tags in self.df['tags']:
			normalized = [self.normalizer.normalize(tag) for tag in tags]
			normalized_tags.extend(normalized)
		
		# Calculate tag frequencies
		self.tag_frequencies = Counter(normalized_tags)
		
		# Build initial graph with frequency weights
		for tag, freq in self.tag_frequencies.items():
			self.graph.add_node(tag, frequency=freq)

	def analyze_tags(self) -> Dict[str, Dict]:
		"""Analyze tags and return comprehensive statistics."""
		total_tags = sum(self.tag_frequencies.values())
		avg_tags = sum(len(tags) for tags in self.df['tags']) / len(self.df)
		
		# Calculate centrality metrics
		centrality = nx.degree_centrality(self.graph)
		betweenness = nx.betweenness_centrality(self.graph)
		
		# Find tag hierarchies
		hierarchies = self._detect_hierarchies()
		
		stats = {
			'total_tags': total_tags,
			'unique_tags': len(self.tag_frequencies),
			'most_common': self.tag_frequencies.most_common(10),
			'avg_tags_per_album': avg_tags,
			'central_tags': sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:5],
			'bridge_tags': sorted(betweenness.items(), key=lambda x: x[1], reverse=True)[:5],
			'hierarchies': hierarchies
		}
		return stats

	def calculate_relationships(self) -> Dict[Tuple[str, str], float]:
		"""Calculate weighted relationships between tags."""
		total_albums = len(self.df)
		
		for tags in self.df['tags']:
			normalized_tags = [self.normalizer.normalize(tag) for tag in tags]
			for i, tag1 in enumerate(normalized_tags):
				for tag2 in normalized_tags[i+1:]:
					pair = tuple(sorted([tag1, tag2]))
					
					# Calculate co-occurrence weight
					self.tag_relationships[pair] = self.tag_relationships.get(pair, 0) + 1
					
					# Calculate normalized weight for the graph
					weight = self.tag_relationships[pair] / min(
						self.tag_frequencies[tag1],
						self.tag_frequencies[tag2]
					)
					
					# Update graph edge
					if self.graph.has_edge(*pair):
						self.graph[pair[0]][pair[1]]['weight'] = weight
					else:
						self.graph.add_edge(*pair, weight=weight)
		
		return self.tag_relationships

	def _detect_hierarchies(self) -> Dict[str, List[str]]:
		"""Detect hierarchical relationships between tags."""
		hierarchies = {}
		
		for tag in self.tag_frequencies:
			tokens = tag.split()
			if len(tokens) > 1:
				for base_tag in self.tag_frequencies:
					if base_tag in tokens:
						if base_tag not in hierarchies:
							hierarchies[base_tag] = []
						hierarchies[base_tag].append(tag)
		
		return hierarchies

	def get_tag_clusters(self, min_size: int = 2, resolution: float = 1.0) -> Dict[str, List[str]]:
		"""Get clusters of related tags using community detection."""
		# Use Louvain community detection with resolution parameter
		communities = nx.community.louvain_communities(
			self.graph, 
			weight='weight',
			resolution=resolution
		)
		
		# Filter and sort clusters
		self.tag_clusters = {}
		for i, community in enumerate(communities):
			if len(community) >= min_size:
				# Sort tags within cluster by frequency
				sorted_tags = sorted(
					community,
					key=lambda x: self.tag_frequencies[x],
					reverse=True
				)
				self.tag_clusters[f"cluster_{i}"] = sorted_tags
		
		return self.tag_clusters

	def find_similar_tags(self, tag: str, threshold: float = 0.3) -> List[Tuple[str, float]]:
		"""Find tags similar to the given tag."""
		if tag not in self.graph:
			return []
		
		similar_tags = []
		for other_tag in self.graph.nodes():
			if other_tag == tag:
				continue
				
			# Calculate similarity based on shared connections
			shared_neighbors = set(self.graph.neighbors(tag)) & set(self.graph.neighbors(other_tag))
			if not shared_neighbors:
				continue
				
			similarity = len(shared_neighbors) / max(
				self.graph.degree(tag),
				self.graph.degree(other_tag)
			)
			
			if similarity >= threshold:
				similar_tags.append((other_tag, similarity))
		
		return sorted(similar_tags, key=lambda x: x[1], reverse=True)