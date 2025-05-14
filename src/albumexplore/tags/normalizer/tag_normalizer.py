"""Tag normalization system."""
import re
import json
import os
import logging
from typing import Dict, Optional, List, Set, Tuple
from collections import defaultdict
from albumexplore.tags.config.tag_rules_config import TagRulesConfig

logger = logging.getLogger(__name__)

class TagNormalizer:
    """Handles tag normalization and variant consolidation."""
    
    def __init__(self, test_mode: bool = False):
        """Initialize the normalizer with rules.
        
        Args:
            test_mode: If True, use test configuration instead of production rules
        """
        self._rules_config = TagRulesConfig(test_mode=test_mode)
        self._variant_cache = {}
        self._single_instance_tags = set()
        self._merge_history = []
        self._similarity_threshold = 0.7
        self._min_frequency_for_normalization = 2
        self._active = True  # Added: Normalization is active by default
        
    def set_active(self, active: bool):
        """Set the active state of the normalizer."""
        self._active = active

    def is_active(self) -> bool:
        """Check if normalization is currently active."""
        return self._active

    def normalize(self, tag: str) -> str:
        """Convert a tag to its normalized form."""
        if not tag:
            return tag
            
        # Convert to lowercase and strip whitespace
        original_cleaned_tag = tag.lower().strip()

        if not self._active:
            return original_cleaned_tag # Return cleaned original if normalization is off
            
        # Check cache first
        if original_cleaned_tag in self._variant_cache:
            return self._variant_cache[original_cleaned_tag]
            
        # Get normalized form from config
        normalized = self._rules_config.get_normalized_form(original_cleaned_tag)
        
        # Cache and return result
        self._variant_cache[original_cleaned_tag] = normalized
        return normalized
        
    def get_category(self, tag: str) -> str:
        """Get the category for a tag based on the config mappings."""
        normalized = self.normalize(tag)
        category = self._rules_config.get_category_for_tag(normalized)
        return category if category else 'other'
        
    def register_single_instance_tag(self, tag: str, frequency: int = 1):
        """Register a tag as a single-instance tag for special handling."""
        if frequency <= self._min_frequency_for_normalization:
            self._single_instance_tags.add(tag.lower().strip())
    
    def get_single_instance_tags(self) -> Set[str]:
        """Get all registered single-instance tags."""
        return self._single_instance_tags
    
    def suggest_normalization_for_single_instance(self, tag: str) -> List[Tuple[str, float, str]]:
        """Suggest possible normalizations for a single-instance tag."""
        tag = tag.lower().strip()
        suggestions = []
        
        # Check existing mappings in config
        single_instance_mappings = self._rules_config.get_single_instance_mappings()
        if tag in single_instance_mappings:
            suggestions.append((single_instance_mappings[tag], 1.0, "Existing rule"))
            
        # Get category information
        category = self._rules_config.get_category_for_tag(tag)
        if category:
            category_info = self._rules_config.get_category_info(category)
            if category_info:
                # Check if it matches any core terms
                for term in category_info.get('core_terms', []):
                    if term in tag:
                        suggestions.append((category, 0.8, "Genre extraction"))
                        break
                
                # Check if it's a modified primary genre
                for genre in category_info.get('primary_genres', []):
                    if genre in tag:
                        for modifier in category_info.get('modifiers', []):
                            if modifier in tag:
                                suggestion = f"{modifier} {genre}"
                                suggestions.append((suggestion, 0.9, "Category pattern"))
                                break
        
        # Return sorted suggestions
        return sorted(suggestions, key=lambda x: x[1], reverse=True)
    
    def add_variant(self, variant: str, canonical: str):
        """Register a new variant mapping."""
        variant = variant.lower().strip()
        canonical = canonical.lower().strip()
        self._variant_cache[variant] = canonical
        
        # If it was a single-instance tag, remove it
        if variant in self._single_instance_tags:
            self._single_instance_tags.remove(variant)
            
        # Add to merge history
        self._merge_history.append({
            'variant': variant,
            'canonical': canonical,
            'timestamp': self._get_timestamp()
        })
        
    def add_single_instance_rule(self, tag: str, normalized_tag: str):
        """Add a rule for normalizing a single-instance tag."""
        tag = tag.lower().strip()
        normalized_tag = normalized_tag.lower().strip()
        
        config = self._rules_config._config  # Access underlying config
        if 'single_instance_mappings' not in config:
            config['single_instance_mappings'] = {}
            
        config['single_instance_mappings'][tag] = normalized_tag
        self._variant_cache[tag] = normalized_tag
        
        # Save changes to config file
        self._rules_config.save_changes()
        
        # If it was in single-instance tags set, remove it
        if tag in self._single_instance_tags:
            self._single_instance_tags.remove(tag)
    
    def get_merge_history(self) -> List[Dict]:
        """Get the history of all tag merges."""
        return self._merge_history
    
    def clear_cache(self):
        """Clear the variant cache."""
        self._variant_cache.clear()
        
    def reload_config(self):
        """Reload the configuration file."""
        self._rules_config.reload()
        self.clear_cache()
        
    def _get_timestamp(self) -> str:
        """Get current timestamp for merge history."""
        from datetime import datetime
        return datetime.now().isoformat()
