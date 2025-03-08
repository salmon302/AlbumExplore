"""Tag normalization system."""
import re
import json
import os
from typing import Dict, Optional

class TagNormalizer:
    """Handles tag normalization and variant consolidation."""
    
    def __init__(self):
        """Initialize the normalizer with rules."""
        self._load_config()
        self._variant_cache = {}
        
    def _load_config(self):
        """Load normalization rules from config."""
        config_dir = os.path.join(os.path.dirname(__file__), '../../config')
        os.makedirs(config_dir, exist_ok=True)
        config_path = os.path.join(config_dir, 'tag_rules.json')
        
        # Default rules if config doesn't exist
        self._substitutions = {
            r'^prog\s+': 'progressive ',
            r'^alt\s+': 'alternative ',
            r'^exp\s+': 'experimental ',
            r'metal\s*core': 'metalcore',
            r'post[- ](\w+)': 'post-\\1'
        }
        
        self._prefix_standardization = {
            'progressive': 'prog-',
            'alternative': 'alt-',
            'experimental': 'exp-',
            'atmospheric': 'atmo-'
        }
        
        self._category_mapping = {
            'metal': ['death metal', 'black metal', 'doom metal', 'thrash metal',
                     'progressive metal', 'power metal', 'gothic metal'],
            'rock': ['progressive rock', 'psychedelic rock', 'hard rock',
                    'alternative rock', 'post-rock'],
            'core': ['metalcore', 'deathcore', 'post-hardcore', 'hardcore'],
            'fusion': ['jazz fusion', 'prog fusion', 'world fusion'],
            'experimental': ['avant-garde', 'experimental metal', 'experimental rock']
        }
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    self._substitutions.update(config.get('substitutions', {}))
                    self._prefix_standardization.update(config.get('prefix_standardization', {}))
                    for category, tags in config.get('category_mapping', {}).items():
                        if category in self._category_mapping:
                            self._category_mapping[category].extend(tags)
                        else:
                            self._category_mapping[category] = tags
        except Exception as e:
            print(f"Error loading tag rules: {e}")
    
    def normalize(self, tag: str) -> str:
        """Convert a tag to its normalized form."""
        if not tag:
            return tag
            
        # Convert to lowercase and strip whitespace
        tag = tag.lower().strip()
        
        # Check cache first
        if tag in self._variant_cache:
            return self._variant_cache[tag]
            
        # Apply substitutions
        normalized = tag
        for pattern, replacement in self._substitutions.items():
            if re.search(pattern, normalized):
                normalized = re.sub(pattern, replacement, normalized)
        
        # Standardize prefixes
        for full, short in self._prefix_standardization.items():
            if normalized.startswith(full):
                normalized = normalized.replace(full, short, 1)
        
        # Cache the result
        self._variant_cache[tag] = normalized
        return normalized
    
    def get_category(self, tag: str) -> str:
        """Get the category for a tag based on the config mappings."""
        normalized = self.normalize(tag)
        
        for category, tags in self._category_mapping.items():
            if normalized in tags:
                return category
                
        # Try to infer category from tag name
        if any(word in normalized for word in ['metal', 'metalcore', 'core']):
            return 'metal'
        if any(word in normalized for word in ['rock', 'prog-', 'psychedelic']):
            return 'rock'
        if 'jazz' in normalized or 'fusion' in normalized:
            return 'fusion'
        if any(word in normalized for word in ['experimental', 'avant', 'noise']):
            return 'experimental'
            
        return 'other'
        
    def add_variant(self, variant: str, canonical: str):
        """Register a new variant mapping."""
        self._variant_cache[variant.lower().strip()] = canonical.lower().strip()
    
    def clear_cache(self):
        """Clear the variant cache."""
        self._variant_cache.clear()
        
    def reload_config(self):
        """Reload the configuration file."""
        self._load_config()
        self.clear_cache()