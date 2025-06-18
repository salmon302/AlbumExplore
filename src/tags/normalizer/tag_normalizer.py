from typing import List, Dict, Set
import re
from difflib import SequenceMatcher

class TagNormalizer:
	"""Handles tag normalization, cleaning, and standardization."""
	
	COMMON_MISSPELLINGS = {
		# Progressive variations
		'prog': 'progressive',
		'prog-': 'progressive',
		'prog metal': 'progressive metal',
		'prog-metal': 'progressive metal',
		'progmetal': 'progressive metal',
		
		# Metal subgenre variations
		'black-metal': 'black metal',
		'blackmetal': 'black metal',
		'death-metal': 'death metal',
		'deathmetal': 'death metal',
		'tech death': 'technical death metal',
		'tech-death': 'technical death metal',
		'techdeath': 'technical death metal',
		'doom-metal': 'doom metal',
		'doommetal': 'doom metal',
		'power-metal': 'power metal',
		'powermetal': 'power metal',
		'thrash-metal': 'thrash metal',
		'thrashmetal': 'thrash metal',
		'tharsh metal': 'thrash metal',
		
		# Core genre variations
		'metal-core': 'metalcore',
		'metalcoore': 'metalcore',
		'death-core': 'deathcore',
		'deathcoore': 'deathcore',
		'post-core': 'postcore',
		'postcoore': 'postcore',
		'math-core': 'mathcore',
		'mathcoore': 'mathcore',
		
		# Post genre variations
		'post metal': 'post-metal',
		'postmetal': 'post-metal',
		'post rock': 'post-rock',
		'postrock': 'post-rock',
		'post punk': 'post-punk',
		'postpunk': 'post-punk',
		'post hardcore': 'post-hardcore',
		'posthardcore': 'post-hardcore',
		
		# Common misspellings
		'pyschedelic': 'psychedelic',
		'psycedelic': 'psychedelic',
		'pschedelic': 'psychedelic',
		'ambiental': 'ambient',
		'experimental metal': 'experimental',
		'avant garde': 'avant-garde',
		'avantgarde': 'avant-garde',
		'symph': 'symphonic',
		'symphonyc': 'symphonic'
	}

	def __init__(self):
		self.known_tags: Set[str] = set()
		self.tag_aliases: Dict[str, str] = {}
		self.consolidator = None  # Enhanced consolidator reference
		self._initialize_known_tags()

	def set_consolidator(self, consolidator):
		"""Set the enhanced consolidator for advanced normalization."""
		self.consolidator = consolidator

	def normalize_with_categorization(self, tag: str):
		"""Normalize tag and return category information if consolidator is available."""
		normalized_tag = self.normalize(tag)
		
		if self.consolidator:
			# Try to get category from consolidator
			for rule in self.consolidator.consolidation_rules:
				if re.search(rule.pattern, tag, re.IGNORECASE):
					if rule.filter_out:
						return None, rule.category  # Filtered out tag
					elif rule.primary_tag:
						return rule.primary_tag, rule.category
					else:
						return normalized_tag, rule.category
			
			# Fallback to heuristic categorization
			category = self.consolidator._heuristic_categorization(normalized_tag)
			return normalized_tag, category
		
		return normalized_tag, None

	def _initialize_known_tags(self):
		"""Initialize set of known valid tags."""
		base_genres = {
			# Metal genres
			'metal', 'heavy metal', 'power metal', 'doom metal', 'black metal',
			'death metal', 'thrash metal', 'folk metal', 'gothic metal',
			'symphonic metal', 'progressive metal', 'post-metal', 'sludge metal',
			'stoner metal', 'drone metal', 'industrial metal', 'avant-garde metal',
			'technical death metal', 'melodic death metal', 'viking metal',
			
			# Core genres
			'metalcore', 'deathcore', 'grindcore', 'mathcore', 'hardcore',
			'post-hardcore', 'crust', 'powerviolence',
			
			# Rock genres
			'rock', 'hard rock', 'progressive rock', 'psychedelic rock',
			'post-rock', 'indie rock', 'alternative rock', 'art rock',
			'experimental rock', 'garage rock', 'space rock', 'stoner rock',
			
			# Electronic genres
			'electronic', 'ambient', 'industrial', 'synthwave', 'darkwave',
			'ebm', 'idm', 'techno', 'house', 'trance',
			
			# Other genres
			'jazz', 'blues', 'folk', 'classical', 'avant-garde',
			'experimental', 'fusion', 'world music', 'pop', 'punk'
		}
		
		modifiers = {
			'atmospheric', 'technical', 'melodic', 'experimental',
			'avant-garde', 'progressive', 'symphonic', 'post',
			'blackened', 'dark', 'epic', 'raw', 'brutal',
			'ambient', 'industrial', 'psychedelic', 'traditional'
		}
		
		self.known_tags.update(base_genres)
		self.known_tags.update(modifiers)

	def normalize(self, tag: str) -> str:
		"""Normalize a single tag following standardized rules."""
		# Initial case normalization and cleaning
		tag = tag.lower().strip()
		
		# Handle special compound terms first
		compound_terms = {
			'post metal': 'post-metal',
			'post-metal': 'post-metal',
			'postmetal': 'post-metal',
			'progmetal': 'progressive metal',
			'techno metal': 'technical metal'
		}
		
		# Regional spelling variations
		regional_variants = {
			'metal-core': 'metalcore',
			'death-core': 'deathcore',
			'black-core': 'blackcore',
			'grind-core': 'grindcore',
			'math-core': 'mathcore'
		}
		
		# Check if the tag matches any compound terms
		for term, replacement in compound_terms.items():
			if tag == term:
				return replacement
				
		# Check regional variants
		for variant, standard in regional_variants.items():
			if tag == variant:
				return standard
		
		# Normalize hyphens and spaces around them
		tag = re.sub(r'\s*-\s*', '-', tag)  # Standardize spaces around hyphens
		
		# Remove special characters but preserve hyphens and apostrophes
		tag = re.sub(r'[^\w\s\'-]', ' ', tag)
		# Normalize multiple spaces to single space
		tag = re.sub(r'\s+', ' ', tag)
		# Remove leading/trailing spaces
		tag = tag.strip()
		
		# Handle hyphenated compounds specially
		if '-' in tag:
			parts = tag.split('-')
			# Normalize each part individually
			parts = [part.strip() for part in parts]
			# Rejoin with standardized hyphen
			tag = '-'.join(filter(None, parts))
		
		# Check common misspellings
		if tag in self.COMMON_MISSPELLINGS:
			return self.COMMON_MISSPELLINGS[tag]
		
		# Check aliases
		if tag in self.tag_aliases:
			return self.tag_aliases[tag]
		
		# If it's a known tag, return as is
		if tag in self.known_tags:
			return tag
		
		# Try to find closest match
		closest_match = self._find_closest_match(tag)
		if closest_match:
			self.tag_aliases[tag] = closest_match
			return closest_match
		
		return tag


	def _find_closest_match(self, tag: str, threshold: float = 0.85) -> str:
		"""Find the closest matching known tag."""
		best_ratio = 0
		best_match = None
		
		for known_tag in self.known_tags:
			ratio = SequenceMatcher(None, tag, known_tag).ratio()
			if ratio > threshold and ratio > best_ratio:
				best_ratio = ratio
				best_match = known_tag
		
		return best_match if best_match else tag

	def add_alias(self, alias: str, primary: str):
		"""Add a new tag alias mapping."""
		self.tag_aliases[alias.lower().strip()] = primary.lower().strip()

	def normalize_list(self, tags: List[str]) -> List[str]:
		"""Normalize a list of tags."""
		return [self.normalize(tag) for tag in tags]