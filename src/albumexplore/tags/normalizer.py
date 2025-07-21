import json
import os
from typing import List, Dict, Set, Optional
import logging

logger = logging.getLogger(__name__)

class TagNormalizer:
	"""Handles tag normalization and standardization with atomic tag support."""
	
	def __init__(self):
		self._active = True  # Default to active for backward compatibility
		self._atomic_mode = False  # Default to standard mode
		
		# Legacy normalization rules
		self.replacements = {
			'prog': 'progressive',
			'psych': 'psychedelic',
			'alt': 'alternative',
			'exp': 'experimental',
			'synth': 'synthesizer',
			'tech': 'technical'
		}
		self.compound_genres = {
			'metalcore', 'deathcore', 'post-metal', 'black-metal',
			'death-metal', 'heavy-metal', 'progressive-metal'
		}
		
		# Atomic tag system
		self._atomic_config = self._load_atomic_config()
		self._decomposition_cache = {}
		
	def _load_atomic_config(self) -> Dict:
		"""Load atomic tag configuration."""
		try:
			# Get the absolute path to the config file
			current_dir = os.path.dirname(os.path.abspath(__file__))
			config_path = os.path.join(current_dir, '..', 'config', 'tag_rules.json')
			config_path = os.path.abspath(config_path)
			
			with open(config_path, 'r', encoding='utf-8') as f:
				config = json.load(f)
			
			logger.info(f"Loaded atomic tag config from {config_path}")
			return config.get('atomic_decomposition', {})
		except Exception as e:
			logger.warning(f"Could not load atomic tag config: {e}")
			return {}
	
	def is_active(self) -> bool:
		"""Check if tag normalization is active."""
		return self._active
	
	def set_active(self, active: bool):
		"""Set whether tag normalization is active."""
		self._active = active
		logger.info(f"Tag normalization {'enabled' if active else 'disabled'}")
	
	def set_atomic_mode(self, atomic_mode: bool):
		"""Set whether to use atomic tag decomposition."""
		self._atomic_mode = atomic_mode
		logger.info(f"Atomic tag mode {'enabled' if atomic_mode else 'disabled'}")
	
	def is_atomic_mode(self) -> bool:
		"""Check if atomic tag mode is enabled."""
		return self._atomic_mode
	
	def get_atomic_mode(self) -> bool:
		"""Check if atomic tag mode is enabled (alias for is_atomic_mode for compatibility)."""
		return self._atomic_mode
	
	def normalize(self, tag: str) -> str:
		"""Normalize a tag by standardizing format and common variations."""
		if not tag or not self._active:
			return tag
		
		if self._atomic_mode:
			# In atomic mode, return the first component of atomic decomposition
			# Use a flag to prevent infinite recursion
			if not hasattr(self, '_normalizing'):
				self._normalizing = True
				try:
					atomic_components = self.normalize_to_atomic(tag)
					return atomic_components[0] if atomic_components else tag
				finally:
					delattr(self, '_normalizing')
			else:
				# We're already in a normalization call, use legacy logic
				return self._legacy_normalize(tag)
		
		return self._legacy_normalize(tag)
	
	def _legacy_normalize(self, tag: str) -> str:
		"""Legacy normalization logic."""
		# Convert to lowercase and strip whitespace
		normalized = tag.lower().strip()
		
		# Remove special characters except hyphens
		normalized = ''.join(c for c in normalized if c.isalnum() or c in '- ')
		normalized = ' '.join(normalized.split())
		
		# Replace common abbreviations
		for abbr, full in self.replacements.items():
			if normalized == abbr or normalized.startswith(abbr + ' ') or normalized.startswith(abbr + '-'):
				normalized = normalized.replace(abbr, full, 1)
		
		# Handle compound genres
		if normalized.replace(' ', '-') in self.compound_genres:
			return normalized.replace(' ', '-')
		elif normalized.replace('-', ' ') in {g.replace('-', ' ') for g in self.compound_genres}:
			base = normalized.replace('-', ' ')
			return next(g for g in self.compound_genres if g.replace('-', ' ') == base)
		
		# Handle special cases
		if 'metal' in normalized and any(prefix in normalized for prefix in ['post', 'black', 'death', 'heavy']):
			parts = normalized.split()
			return '-'.join(parts)
		
		return normalized
	
	def normalize_to_atomic(self, tag: str) -> List[str]:
		"""Normalize a tag and decompose to atomic components."""
		if not tag:
			return []
		
		# Clean and normalize basic format
		cleaned_tag = tag.lower().strip()
		
		# Check cache first
		if cleaned_tag in self._decomposition_cache:
			return self._decomposition_cache[cleaned_tag]
		
		# Apply atomic decomposition if rule exists
		if cleaned_tag in self._atomic_config:
			atomic_components = self._atomic_config[cleaned_tag]
			self._decomposition_cache[cleaned_tag] = atomic_components
			return atomic_components
		
		# Check for case variations and space/hyphen variants
		for rule_tag, components in self._atomic_config.items():
			if (rule_tag.replace('-', ' ') == cleaned_tag.replace('-', ' ') or
				rule_tag.replace(' ', '-') == cleaned_tag.replace(' ', '-')):
				self._decomposition_cache[cleaned_tag] = components
				return components
		
		# If no decomposition rule found, return normalized single tag using legacy normalization
		if self._active:
			normalized_single = self._legacy_normalize(cleaned_tag)
		else:
			normalized_single = cleaned_tag
		
		result = [normalized_single] if normalized_single else [cleaned_tag]
		self._decomposition_cache[cleaned_tag] = result
		return result
	
	def normalize_tag_list(self, tags: List[str]) -> List[str]:
		"""Normalize a list of tags, potentially using atomic decomposition."""
		if not tags:
			return []
		
		if self._atomic_mode:
			# In atomic mode, decompose all tags
			atomic_tags = []
			for tag in tags:
				atomic_components = self.normalize_to_atomic(tag)
				atomic_tags.extend(atomic_components)
			
			# Remove duplicates while preserving order
			seen = set()
			unique_atomic_tags = []
			for tag in atomic_tags:
				if tag not in seen:
					seen.add(tag)
					unique_atomic_tags.append(tag)
			
			return unique_atomic_tags
		else:
			# Standard mode - normalize each tag individually
			return [self.normalize(tag) for tag in tags if tag]
	
	def validate_atomic_tag(self, tag: str) -> bool:
		"""Check if a tag is a valid atomic component."""
		try:
			# Check against all valid atomic tags from config
			if 'all_valid_tags' in self._atomic_config:
				return tag.lower() in self._atomic_config['all_valid_tags']
			
			# Fallback: check if it appears in any decomposition
			for components in self._atomic_config.values():
				if isinstance(components, list) and tag.lower() in components:
					return True
			
			return True  # Default to valid if config unavailable
		except Exception:
			return True
	
	def get_atomic_statistics(self) -> Dict:
		"""Get statistics about atomic tag usage."""
		return {
			'total_decomposition_rules': len(self._atomic_config),
			'cache_size': len(self._decomposition_cache),
			'atomic_mode_enabled': self._atomic_mode,
			'normalization_active': self._active,
			'config_loaded': bool(self._atomic_config)
		}