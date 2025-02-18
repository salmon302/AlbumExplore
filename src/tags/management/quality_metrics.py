from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass
import numpy as np
from ..analysis.tag_analyzer import TagAnalyzer
from ..normalizer import TagNormalizer
from .review_queue import ReviewQueue

@dataclass
class TagQualityScore:
	tag: str
	consistency_score: float
	ambiguity_index: float
	relationship_strength: float
	feedback_score: float
	overall_score: float

class QualityMetrics:
	def __init__(self, analyzer: TagAnalyzer, review_queue: ReviewQueue):
		self.analyzer = analyzer
		self.review_queue = review_queue
		self.normalizer = TagNormalizer()
		self.quality_scores: Dict[str, TagQualityScore] = {}
		self.feedback_weights = {
			'approved': 1.0,
			'rejected': -0.5,
			'rollback': -1.0
		}

	def calculate_consistency_score(self, tag: str) -> float:
		score = 1.0
		normalized = self.normalizer.normalize(tag)
		if tag != normalized:
			score *= 0.7
		if tag not in self.normalizer.known_tags:
			score *= 0.8
		if not tag.islower():
			score *= 0.9
		if ' ' in tag and '-' not in tag:
			score *= 0.9
		return score

	def calculate_ambiguity_index(self, tag: str) -> float:
		similar_tags = self.analyzer.find_similar_tags(tag, threshold=0.3)
		if not similar_tags:
			return 0.3  # Base ambiguity for unique tags
		
		# Calculate weighted ambiguity based on similarity scores
		weighted_sum = sum(score for _, score in similar_tags)
		base_ambiguity = 0.4 if len(similar_tags) > 1 else 0.3
		
		# Adjust scaling factor based on number of similar tags
		scaling_factor = 2.5 if len(similar_tags) > 2 else 2.2
		return min(1.0, base_ambiguity + (weighted_sum / (scaling_factor * len(similar_tags))))



	def calculate_relationship_strength(self, tag: str) -> float:
		if tag not in self.analyzer.graph:
			return 0.0
		neighbors = list(self.analyzer.graph.neighbors(tag))
		if not neighbors:
			return 0.0
		weights = [self.analyzer.graph[tag][neighbor]['weight'] for neighbor in neighbors]
		avg_weight = sum(weights) / len(weights)
		max_weight = max(data['weight'] for _, _, data in self.analyzer.graph.edges(data=True))
		return avg_weight / max_weight if max_weight > 0 else 0.0

	def calculate_feedback_score(self, tag: str) -> float:
		history = self.review_queue.change_history
		relevant_changes = [change for change in history 
						  if change.old_value == tag or change.new_value == tag]
		if not relevant_changes:
			return 0.5
		score = 0.5
		for change in relevant_changes:
			weight = self.feedback_weights.get(change.status.value, 0)
			score += weight * 0.1
		return max(0.0, min(1.0, score))

	def calculate_overall_score(self, tag: str) -> TagQualityScore:
		consistency = self.calculate_consistency_score(tag)
		ambiguity = self.calculate_ambiguity_index(tag)
		relationship = self.calculate_relationship_strength(tag)
		feedback = self.calculate_feedback_score(tag)
		
		weights = {
			'consistency': 0.3,
			'ambiguity': 0.2,
			'relationship': 0.3,
			'feedback': 0.2
		}
		
		overall = (
			consistency * weights['consistency'] +
			ambiguity * weights['ambiguity'] +
			relationship * weights['relationship'] +
			feedback * weights['feedback']
		)
		
		score = TagQualityScore(
			tag=tag,
			consistency_score=consistency,
			ambiguity_index=ambiguity,
			relationship_strength=relationship,
			feedback_score=feedback,
			overall_score=overall
		)
		
		self.quality_scores[tag] = score
		return score

	def get_quality_metrics(self, tag: str) -> Optional[TagQualityScore]:
		if tag not in self.quality_scores:
			return self.calculate_overall_score(tag)
		return self.quality_scores[tag]

	def get_low_quality_tags(self, threshold: float = 0.5) -> List[TagQualityScore]:
		low_quality = []
		for tag in self.analyzer.tag_frequencies:
			score = self.get_quality_metrics(tag)
			if score and score.overall_score < threshold:
				low_quality.append(score)
		return sorted(low_quality, key=lambda x: x.overall_score)