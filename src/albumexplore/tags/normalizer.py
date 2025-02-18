class TagNormalizer:
	"""Handles tag normalization and standardization."""
	
	def __init__(self):
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
	
	def normalize(self, tag: str) -> str:
		"""Normalize a tag by standardizing format and common variations."""
		if not tag:
			return tag
			
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