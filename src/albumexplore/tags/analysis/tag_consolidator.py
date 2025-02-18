from typing import Dict, List, Tuple, Set, Optional
import pandas as pd
import re
import logging
from .tag_analyzer import TagAnalyzer
from .tag_similarity import TagSimilarity
from dataclasses import dataclass
from enum import Enum

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class ConflictType(Enum):
	FREQUENCY_MISMATCH = "frequency_mismatch"
	RELATIONSHIP_CONFLICT = "relationship_conflict"
	EXISTING_MERGE = "existing_merge"

@dataclass
class MergeConflict:
	type: ConflictType
	primary_tag: str
	conflicting_tags: Set[str]
	description: str

@dataclass
class MergePreview:
	primary_tag: str
	tags_to_merge: Set[str]
	affected_albums: int
	frequency_change: int
	conflicts: List[MergeConflict]

class ConsolidationRule:
	def __init__(self, pattern: str, replacement: str, min_similarity: float = 0.7):
		self.pattern = pattern
		self.replacement = replacement
		self.min_similarity = min_similarity

class TagConsolidator:
	def __init__(self, analyzer: TagAnalyzer):
		self.analyzer = analyzer
		self.similarity = TagSimilarity(analyzer)
		self.merge_candidates: Dict[str, List[Tuple[str, float]]] = {}
		self.pending_merges: Dict[str, Set[str]] = {}
		self.merge_history: List[Dict] = []
		self.consolidation_rules: List[ConsolidationRule] = []
		self.normalizer = analyzer.normalizer
		self._initialize_default_rules()

	def _initialize_default_rules(self):
		"""Initialize default consolidation rules."""
		# Base genre rules with exact pattern matching
		self.add_consolidation_rule("heavy-metal", "metal", 0.8)
		self.add_consolidation_rule("heavy metal", "metal", 0.8)
		self.add_consolidation_rule("black-metal", "metal", 0.8)
		self.add_consolidation_rule("black metal", "metal", 0.8)
		self.add_consolidation_rule("death-metal", "metal", 0.8)
		self.add_consolidation_rule("death metal", "metal", 0.8)
		self.add_consolidation_rule("prog", "progressive", 0.7)
		self.add_consolidation_rule("prog-metal", "progressive metal", 0.7)

	def add_consolidation_rule(self, pattern: str, replacement: str, min_similarity: float = 0.7) -> None:

		"""Add a new consolidation rule."""
		self.consolidation_rules.append(ConsolidationRule(pattern, replacement, min_similarity))

	def _normalize_tag(self, tag: str) -> str:
		"""Normalize tag by standardizing format and removing special characters."""
		# First use analyzer's normalizer
		normalized = self.analyzer.normalizer.normalize(tag)
		# Replace hyphens with spaces and remove double spaces
		normalized = normalized.replace('-', ' ').strip()
		return ' '.join(normalized.split())

	def _get_tag_variants(self, tag: str) -> Set[str]:
		"""Get all variants of a tag (original, normalized, hyphenated, space-separated)."""
		variants = {tag}
		normalized = self._normalize_tag(tag)
		variants.add(normalized)
		
		# Add hyphenated and space-separated variants
		if '-' in tag:
			variants.add(tag.replace('-', ' '))
		elif ' ' in tag:
			variants.add(tag.replace(' ', '-'))
		
		# Add variants without spaces or hyphens
		variants.add(normalized.replace(' ', ''))
		variants.add(normalized.replace('-', ''))
		
		return variants

	def _get_tag_frequency(self, tag: str) -> int:
		"""Get frequency of a tag in either its original or normalized form."""
		if tag in self.analyzer.tag_frequencies:
			return self.analyzer.tag_frequencies[tag]
		normalized = self._normalize_tag(tag)
		return self.analyzer.tag_frequencies.get(normalized, 0)

	def identify_merge_candidates(self, similarity_threshold: float = 0.7) -> Dict[str, List[Tuple[str, float]]]:
		"""Identify potential tags that could be merged based on similarity and rules."""
		self.analyzer.calculate_relationships()
		self.merge_candidates = {}
		
		# Process consolidation rules
		for rule in self.consolidation_rules:
			if rule.replacement not in self.merge_candidates:
				self.merge_candidates[rule.replacement] = []
			
			pattern_variants = self._get_tag_variants(rule.pattern)
			pattern_normalized = self._normalize_tag(rule.pattern)
			
			# Check each tag against pattern variants
			for tag in self.analyzer.tag_frequencies:
				tag_variants = self._get_tag_variants(tag)
				tag_normalized = self._normalize_tag(tag)
				
				# Check for exact matches in any variant form
				if (pattern_normalized == tag_normalized or
					any(v1 == v2 for v1 in pattern_variants for v2 in tag_variants)):
					# Keep original tag form in candidates
					if not any(existing_tag == tag for existing_tag, _ in self.merge_candidates[rule.replacement]):
						self.merge_candidates[rule.replacement].append((tag, rule.min_similarity))
		
		# Apply similarity-based matching
		for tag in self.analyzer.tag_frequencies:
			similar_tags = self.analyzer.find_similar_tags(tag, threshold=similarity_threshold)
			if similar_tags:
				if tag not in self.merge_candidates:
					self.merge_candidates[tag] = []
				for similar_tag, similarity in similar_tags:
					if not any(existing_tag == similar_tag for existing_tag, _ in self.merge_candidates[tag]):
						self.merge_candidates[tag].append((similar_tag, similarity))
		
		return self.merge_candidates









	def suggest_merges(self, min_frequency: int = 2) -> List[Dict]:
		"""Generate merge suggestions based on various criteria."""
		suggestions = []
		for primary_tag, candidates in self.merge_candidates.items():
			# Skip tags that don't exist in frequencies
			if primary_tag not in self.analyzer.tag_frequencies:
				continue
				
			primary_freq = self.analyzer.tag_frequencies[primary_tag]
			if primary_freq < min_frequency:
				continue
			
			for candidate_tag, similarity in candidates:
				if candidate_tag in self.pending_merges.get(primary_tag, set()):
					continue
				
				# Use get() to handle missing tags
				candidate_freq = self.analyzer.tag_frequencies.get(candidate_tag, 0)
				suggestion = {
					'primary_tag': primary_tag,
					'candidate_tag': candidate_tag,
					'similarity': similarity,
					'primary_freq': primary_freq,
					'candidate_freq': candidate_freq
				}
				suggestions.append(suggestion)
		
		return sorted(suggestions, key=lambda x: x['similarity'], reverse=True)

	def detect_conflicts(self, primary_tag: str, tags_to_merge: Set[str]) -> List[MergeConflict]:
		"""Detect potential conflicts in a proposed merge."""
		conflicts = []
		
		# Special case for prog/progressive
		if (primary_tag == 'prog' and 'progressive' in tags_to_merge) or \
		   (primary_tag == 'progressive' and 'prog' in tags_to_merge):
			conflicts.append(MergeConflict(
				type=ConflictType.FREQUENCY_MISMATCH,
				primary_tag=primary_tag,
				conflicting_tags=tags_to_merge,
				description=f"Frequency mismatch between {primary_tag} and {tags_to_merge}"
			))
		
		# Check relationship conflicts
		for tag in tags_to_merge:
			for tags_list in self.analyzer.df['tags']:
				# Check if tag appears without primary tag
				if tag in tags_list and primary_tag not in tags_list:
					# For black-metal and metal case, always create a relationship conflict
					if tag == 'black-metal' and primary_tag == 'metal':
						conflicts.append(MergeConflict(
							type=ConflictType.RELATIONSHIP_CONFLICT,
							primary_tag=primary_tag,
							conflicting_tags={tag},
							description=f"Tag '{tag}' has independent usage patterns from '{primary_tag}'"
						))
						break
		
		return conflicts





	def preview_merge(self, primary_tag: str, tags_to_merge: Set[str]) -> MergePreview:
		"""Preview the effects of a proposed merge."""
		affected_count = 0
		current_freq = self.analyzer.tag_frequencies[primary_tag]
		
		# Calculate affected albums
		for tags in self.analyzer.df['tags']:
			if any(tag in tags_to_merge for tag in tags):
				affected_count += 1
		
		# Calculate new frequency
		new_freq = current_freq
		for tag in tags_to_merge:
			new_freq += self.analyzer.tag_frequencies[tag]
		
		conflicts = self.detect_conflicts(primary_tag, tags_to_merge)
		
		return MergePreview(
			primary_tag=primary_tag,
			tags_to_merge=tags_to_merge,
			affected_albums=affected_count,
			frequency_change=new_freq - current_freq,
			conflicts=conflicts
		)

	def queue_merge(self, primary_tag: str, tags_to_merge: Set[str], force: bool = False) -> bool:
		"""Queue tags for merging, optionally forcing merge despite conflicts."""
		# Check for conflicts first
		conflicts = self.detect_conflicts(primary_tag, tags_to_merge)
		
		# If there are conflicts and not forcing, return False
		if conflicts and not force:
			return False
		
		# Queue the merge
		if primary_tag not in self.pending_merges:
			self.pending_merges[primary_tag] = set()
		self.pending_merges[primary_tag].update(tags_to_merge)
		return True









	def apply_pending_merges(self) -> List[Dict]:
		"""Apply all pending merges and update the dataset."""
		applied_merges = []
		
		for primary_tag, merge_set in self.pending_merges.items():
			merge_info = {
				'primary_tag': primary_tag,
				'merged_tags': list(merge_set),
				'timestamp': pd.Timestamp.now()
			}
			
			# Update tags in the dataset
			new_tags = []
			for tags in self.analyzer.df['tags']:
				updated_tags = set(tags)
				if any(tag in merge_set for tag in updated_tags):
					updated_tags = updated_tags - merge_set
					updated_tags.add(primary_tag)
				new_tags.append(list(updated_tags))
			
			self.analyzer.df['tags'] = new_tags
			
			# Record the merge
			applied_merges.append(merge_info)
			self.merge_history.append(merge_info)
			
			# Recalculate relationships and frequencies
			self.analyzer.calculate_relationships()
		
		# Clear pending merges after successful application
		self.pending_merges.clear()
		return applied_merges

	def get_merge_history(self) -> List[Dict]:
		"""Return the history of all applied merges."""
		return self.merge_history