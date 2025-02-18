from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum
from .review_queue import ReviewQueue, ChangeType, TagChange
from ..normalizer import TagNormalizer
from ..analysis.tag_similarity import TagSimilarity

class CorrectionConfidence(Enum):
	HIGH = "high"      # > 0.8 similarity
	MEDIUM = "medium"  # 0.5 - 0.8 similarity
	LOW = "low"        # < 0.5 similarity

@dataclass
class CorrectionSuggestion:
	original_tag: str
	suggested_tag: str
	confidence: CorrectionConfidence
	reason: str
	similarity_score: float

class CorrectionWorkflow:
	def __init__(self, review_queue: ReviewQueue, tag_similarity: TagSimilarity):
		self.review_queue = review_queue
		self.tag_similarity = tag_similarity
		self.normalizer = TagNormalizer()
		self.correction_history: Dict[str, List[TagChange]] = {}
		
	def suggest_corrections(self, tag: str) -> List[CorrectionSuggestion]:
		"""Generate correction suggestions for a tag."""
		suggestions = []
		
		# Check for normalization issues
		normalized = self.normalizer.normalize(tag)
		if normalized != tag:
			suggestions.append(CorrectionSuggestion(
				original_tag=tag,
				suggested_tag=normalized,
				confidence=CorrectionConfidence.HIGH,
				reason="Normalization rule match",
				similarity_score=1.0
			))
		
		# Find similar tags
		similar_tags = self.tag_similarity.find_similar_tags(tag, threshold=0.3)
		for similar_tag, score in similar_tags:
			confidence = self._get_confidence_level(score)
			suggestions.append(CorrectionSuggestion(
				original_tag=tag,
				suggested_tag=similar_tag,
				confidence=confidence,
				reason="Similar tag found",
				similarity_score=score
			))
		
		return suggestions

	def apply_correction(self, original_tag: str, corrected_tag: str, 
						reviewer: str, notes: Optional[str] = None) -> str:
		"""Apply a correction and add it to the review queue."""
		change_id = self.review_queue.add_change(
			change_type=ChangeType.RENAME,
			old_value=original_tag,
			new_value=corrected_tag,
			notes=notes
		)
		
		if original_tag not in self.correction_history:
			self.correction_history[original_tag] = []
			
		if change_id:
			change = self.review_queue.pending_changes[change_id]
			self.correction_history[original_tag].append(change)
			
		return change_id

	def get_correction_history(self, tag: str) -> List[TagChange]:
		"""Get the correction history for a specific tag."""
		return self.correction_history.get(tag, [])

	def validate_correction(self, original_tag: str, corrected_tag: str) -> List[str]:
		"""Validate a proposed correction against defined rules."""
		issues = []
		
		# Normalize both tags to compare
		normalized_original = self.normalizer.normalize(original_tag)
		normalized_corrected = self.normalizer.normalize(corrected_tag)
		
		# Check if the correction is actually different from the normalized original
		if normalized_original == normalized_corrected:
			# If the corrected tag is in the normalizer's common misspellings or known tags,
			# and it's different from the original tag, consider it valid
			if corrected_tag in self.normalizer.COMMON_MISSPELLINGS.values() or \
			   corrected_tag in self.normalizer.known_tags:
				return []
			issues.append("Correction is equivalent to original after normalization")
		
		# Check if the correction maintains semantic meaning using similarity
		similar_tags = self.tag_similarity.find_similar_tags(original_tag)
		has_semantic_relation = any(
			tag for tag, score in similar_tags 
			if self.normalizer.normalize(tag) == normalized_corrected and score > 0.3
		)
		
		if not has_semantic_relation and normalized_original != normalized_corrected:
			issues.append("Corrected tag may not maintain semantic meaning")
		
		return issues

	def _get_confidence_level(self, similarity_score: float) -> CorrectionConfidence:
		"""Determine confidence level based on similarity score."""
		if similarity_score > 0.8:
			return CorrectionConfidence.HIGH
		elif similarity_score > 0.5:
			return CorrectionConfidence.MEDIUM
		return CorrectionConfidence.LOW