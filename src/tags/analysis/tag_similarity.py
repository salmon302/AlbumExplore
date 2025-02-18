from typing import Dict, List, Tuple, Set
import numpy as np
from difflib import SequenceMatcher
from .tag_analyzer import TagAnalyzer

class TagSimilarity:
	def __init__(self, tag_analyzer: TagAnalyzer):
		self.analyzer = tag_analyzer
		self.similarity_matrix: Dict[Tuple[str, str], float] = {}
		self.cached_similarities: Dict[str, List[Tuple[str, float]]] = {}
		self._genre_modifiers = {
			'metal': {'black', 'death', 'doom', 'heavy', 'power', 'thrash', 'folk', 'gothic', 'progressive'},
			'rock': {'hard', 'progressive', 'psychedelic', 'indie', 'alternative', 'art', 'space'},
			'core': {'metal', 'death', 'grind', 'math', 'hard'},
			'wave': {'dark', 'new', 'synth', 'cold'}
		}

	def calculate_similarities(self) -> Dict[Tuple[str, str], float]:
		"""Calculate similarities between all tags."""
		tags = list(self.analyzer.tag_frequencies.keys())
		
		for i, tag1 in enumerate(tags):
			for tag2 in tags[i+1:]:
				similarity = self._calculate_tag_similarity(tag1, tag2)
				self.similarity_matrix[(tag1, tag2)] = similarity
				self.similarity_matrix[(tag2, tag1)] = similarity
		
		return self.similarity_matrix

	def _calculate_tag_similarity(self, tag1: str, tag2: str) -> float:
		"""Calculate similarity between two tags using multiple metrics."""
		# String similarity (20% weight)
		string_sim = self._calculate_string_similarity(tag1, tag2) * 0.2
		
		# Token similarity (20% weight)
		token_sim = self._calculate_token_similarity(tag1, tag2) * 0.2
		
		# Co-occurrence similarity (30% weight)
		cooc_sim = self._calculate_cooccurrence_similarity(tag1, tag2) * 0.3
		
		# Network similarity (20% weight)
		network_sim = self._calculate_network_similarity(tag1, tag2) * 0.2
		
		# Context similarity (10% weight)
		context_sim = self._calculate_context_similarity(tag1, tag2) * 0.1
		
		return string_sim + token_sim + cooc_sim + network_sim + context_sim

	def _calculate_string_similarity(self, tag1: str, tag2: str) -> float:
		"""Calculate string similarity with special handling for hyphens."""
		# Normalize tags by replacing hyphens with spaces
		norm_tag1 = tag1.replace('-', ' ')
		norm_tag2 = tag2.replace('-', ' ')
		
		# Calculate similarity on normalized tags
		base_similarity = SequenceMatcher(None, norm_tag1, norm_tag2).ratio()
		
		# Boost similarity for tags that are identical when normalized
		if norm_tag1 == norm_tag2:
			base_similarity = max(base_similarity, 0.9)
		
		return base_similarity

	def _calculate_token_similarity(self, tag1: str, tag2: str) -> float:
		"""Calculate similarity based on shared tokens, handling hyphenated variants."""
		# Normalize tags by replacing hyphens with spaces
		norm_tag1 = tag1.replace('-', ' ')
		norm_tag2 = tag2.replace('-', ' ')
		
		# Split into tokens
		tokens1 = set(norm_tag1.split())
		tokens2 = set(norm_tag2.split())
		
		if not (tokens1 and tokens2):
			return 0.0
		
		intersection = tokens1 & tokens2
		union = tokens1 | tokens2
		
		# Calculate Jaccard similarity
		similarity = len(intersection) / len(union)
		
		# Boost similarity for exact token matches after normalization
		if tokens1 == tokens2:
			similarity = max(similarity, 0.9)
		
		return similarity

	def _calculate_cooccurrence_similarity(self, tag1: str, tag2: str) -> float:
		"""Calculate similarity based on normalized co-occurrences."""
		pair = tuple(sorted([tag1, tag2]))
		if pair in self.analyzer.tag_relationships:
			cooc_count = self.analyzer.tag_relationships[pair]
			# Normalize by the geometric mean of frequencies
			freq1 = self.analyzer.tag_frequencies[tag1]
			freq2 = self.analyzer.tag_frequencies[tag2]
			norm_factor = np.sqrt(freq1 * freq2)
			return cooc_count / norm_factor if norm_factor > 0 else 0.0
		return 0.0

	def _calculate_network_similarity(self, tag1: str, tag2: str) -> float:
		"""Calculate similarity based on network structure with weighted edges."""
		if not (self.analyzer.graph.has_node(tag1) and self.analyzer.graph.has_node(tag2)):
			return 0.0
		
		# Get weighted neighbors
		neighbors1 = {n: self.analyzer.graph[tag1][n].get('weight', 1.0) 
					 for n in self.analyzer.graph.neighbors(tag1)}
		neighbors2 = {n: self.analyzer.graph[tag2][n].get('weight', 1.0) 
					 for n in self.analyzer.graph.neighbors(tag2)}
		
		if not (neighbors1 or neighbors2):
			return 0.0
		
		# Calculate weighted Jaccard similarity
		shared_neighbors = set(neighbors1.keys()) & set(neighbors2.keys())
		if not shared_neighbors:
			return 0.0
		
		# Sum of minimum weights for shared neighbors
		intersection_sum = sum(min(neighbors1[n], neighbors2[n]) for n in shared_neighbors)
		# Sum of maximum weights for all neighbors
		union_sum = sum(max(neighbors1.get(n, 0), neighbors2.get(n, 0)) 
					   for n in set(neighbors1.keys()) | set(neighbors2.keys()))
		
		return intersection_sum / union_sum if union_sum > 0 else 0.0

	def _calculate_context_similarity(self, tag1: str, tag2: str) -> float:
		"""Calculate similarity based on genre context."""
		tokens1 = set(tag1.split())
		tokens2 = set(tag2.split())
		
		# Check if tags share same genre context
		for genre, modifiers in self._genre_modifiers.items():
			if genre in tokens1 and genre in tokens2:
				# Check shared modifiers
				shared_modifiers = (tokens1 & tokens2 & modifiers)
				all_modifiers = (tokens1 | tokens2) & modifiers
				return len(shared_modifiers) / len(all_modifiers) if all_modifiers else 0.8
			
		return 0.0

	def find_similar_tags(self, tag: str, threshold: float = 0.3) -> List[Tuple[str, float]]:
		"""Find tags similar to the given tag."""
		if tag in self.cached_similarities:
			return [pair for pair in self.cached_similarities[tag] if pair[1] >= threshold]
			
		if not self.similarity_matrix:
			self.calculate_similarities()
			
		similar = []
		for other_tag in self.analyzer.tag_frequencies.keys():
			if other_tag == tag:
				continue
				
			pair = (tag, other_tag)
			if pair in self.similarity_matrix:
				similarity = self.similarity_matrix[pair]
				if similarity >= threshold:
					similar.append((other_tag, similarity))
					
		similar.sort(key=lambda x: x[1], reverse=True)
		self.cached_similarities[tag] = similar
		return similar