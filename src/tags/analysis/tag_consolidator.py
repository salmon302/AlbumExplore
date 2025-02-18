from typing import Dict, List, Tuple, Set, Optional
import pandas as pd
import re
from .tag_analyzer import TagAnalyzer
from .tag_similarity import TagSimilarity
from dataclasses import dataclass
from enum import Enum

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
		self._initialize_default_rules()

	def _initialize_default_rules(self):
		"""Initialize default consolidation rules."""
		# Genre prefix/suffix standardization
		self.add_consolidation_rule(r'(.+)\s*metal$', r'\1 metal', 0.9)
		self.add_consolidation_rule(r'(.+)\s*rock$', r'\1 rock', 0.9)
		self.add_consolidation_rule(r'(.+)\s*core$', r'\1core', 0.9)
		self.add_consolidation_rule(r'(.+)\s*wave$', r'\1wave', 0.9)
		
		# Common variations
		self.add_consolidation_rule(r'prog\s*(.+)', r'progressive \1', 0.85)
		self.add_consolidation_rule(r'psych\s*(.+)', r'psychedelic \1', 0.85)
		self.add_consolidation_rule(r'alt\s*(.+)', r'alternative \1', 0.85)
		self.add_consolidation_rule(r'exp\s*(.+)', r'experimental \1', 0.85)
		
		# Hyphenation standardization
		self.add_consolidation_rule(r'post\s+(.+)', r'post-\1', 0.9)
		self.add_consolidation_rule(r'avant\s+garde', r'avant-garde', 0.9)
		
		# Common misspellings and variations
		self.add_consolidation_rule(r'(.+)core', r'\1core', 0.85)  # Handle variations like 'metal-core'
		self.add_consolidation_rule(r'(.+)\s*&\s*(.+)', r'\1 and \2', 0.85)  # Standardize '&' to 'and'

	def add_consolidation_rule(self, pattern: str, replacement: str, min_similarity: float = 0.7) -> None:
		"""Add a new consolidation rule."""
		self.consolidation_rules.append(ConsolidationRule(pattern, replacement, min_similarity))

	def identify_merge_candidates(self, similarity_threshold: float = 0.7) -> Dict[str, List[Tuple[str, float]]]:
		"""Identify potential tags that could be merged based on similarity and rules."""
		self.analyzer.calculate_relationships()
		self.merge_candidates.clear()
		
		# First apply consolidation rules
		for rule in self.consolidation_rules:
			for tag in self.analyzer.tag_frequencies:
				# Try exact pattern match first
				if re.match(f"^{rule.pattern}$", tag):
					normalized = re.sub(rule.pattern, rule.replacement, tag)
					if normalized != tag:
						if normalized not in self.merge_candidates:
							self.merge_candidates[normalized] = []
						self.merge_candidates[normalized].append((tag, rule.min_similarity))
				# Fall back to similarity check
				elif self.similarity.calculate_similarity(tag, rule.pattern) >= rule.min_similarity:
					normalized = re.sub(rule.pattern, rule.replacement, tag)
					if normalized != tag:
						if normalized not in self.merge_candidates:
							self.merge_candidates[normalized] = []
						self.merge_candidates[normalized].append((tag, rule.min_similarity))
		
		# Then apply similarity-based identification
		for tag in self.analyzer.tag_frequencies:
			similar_tags = self.similarity.find_similar_tags(tag, threshold=similarity_threshold)
			if similar_tags:
				# Filter out tags that are already being merged
				filtered_tags = [(t, s) for t, s in similar_tags 
							   if not any(t in candidates for candidates in self.merge_candidates.values())]
				if filtered_tags:
					self.merge_candidates[tag] = filtered_tags
		
		return self.merge_candidates

	def suggest_merges(self, min_frequency: int = 2) -> List[Dict]:
		"""Generate merge suggestions based on various criteria."""
		suggestions = []
		for primary_tag, candidates in self.merge_candidates.items():
			if self.analyzer.tag_frequencies[primary_tag] < min_frequency:
				continue
			
			for candidate_tag, similarity in candidates:
				if candidate_tag in self.pending_merges.get(primary_tag, set()):
					continue
				
				suggestion = {
					'primary_tag': primary_tag,
					'candidate_tag': candidate_tag,
					'similarity': similarity,
					'primary_freq': self.analyzer.tag_frequencies[primary_tag],
					'candidate_freq': self.analyzer.tag_frequencies[candidate_tag],
				}
				suggestions.append(suggestion)
		
		return sorted(suggestions, key=lambda x: x['similarity'], reverse=True)

	def detect_conflicts(self, primary_tag: str, tags_to_merge: Set[str]) -> List[MergeConflict]:
		"""Detect potential conflicts in a proposed merge."""
		conflicts = []
		
		# Check frequency conflicts with more lenient threshold
		primary_freq = self.analyzer.tag_frequencies[primary_tag]
		for tag in tags_to_merge:
			tag_freq = self.analyzer.tag_frequencies[tag]
			if tag_freq > primary_freq * 2:  # Only flag if significantly more frequent
				conflicts.append(MergeConflict(
					type=ConflictType.FREQUENCY_MISMATCH,
					primary_tag=primary_tag,
					conflicting_tags={tag},
					description=f"Tag '{tag}' has significantly higher frequency ({tag_freq}) than primary tag ({primary_freq})"
				))
		
		# Check relationship conflicts with improved context
		for tag in tags_to_merge:
			related_primary = set(self.analyzer.tag_relationships.get(primary_tag, {}))
			related_merge = set(self.analyzer.tag_relationships.get(tag, {}))
			
			# Only consider strong relationships
			strong_conflicts = {rel for rel in (related_merge - related_primary)
							  if self.analyzer.tag_relationships[tag].get(rel, 0) > 0.5}
			
			if strong_conflicts:
				conflicts.append(MergeConflict(
					type=ConflictType.RELATIONSHIP_CONFLICT,
					primary_tag=primary_tag,
					conflicting_tags={tag},
					description=f"Tag '{tag}' has strong unique relationships: {strong_conflicts}"
				))
		
		# Check for existing merges
		for tag in tags_to_merge:
			if any(tag in merge_set for merge_set in self.pending_merges.values()):
				conflicts.append(MergeConflict(
					type=ConflictType.EXISTING_MERGE,
					primary_tag=primary_tag,
					conflicting_tags={tag},
					description=f"Tag '{tag}' is already part of another pending merge"
				))
		
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
		# Validate primary tag exists
		if primary_tag not in self.analyzer.tag_frequencies:
			return False
		
		# Check for conflicts only if not forcing
		if not force:
			conflicts = self.detect_conflicts(primary_tag, tags_to_merge)
			# Only block on existing merge conflicts
			blocking_conflicts = [c for c in conflicts if c.type == ConflictType.EXISTING_MERGE]
			if blocking_conflicts:
				return False
		
		# Add to pending merges
		self.pending_merges[primary_tag] = self.pending_merges.get(primary_tag, set()) | tags_to_merge
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
			self.analyzer._initialize()  # Rebuild tag frequencies and graph
			
			applied_merges.append(merge_info)
			self.merge_history.extend(applied_merges)
		
		self.pending_merges.clear()
		return applied_merges

	def get_merge_history(self) -> List[Dict]:
		"""Return the history of all applied merges."""
		return self.merge_history