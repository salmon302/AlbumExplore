"""Tag normalization system with atomic tag support."""
import re
import json
import os
import logging
from typing import Dict, Optional, List, Set, Tuple
from collections import defaultdict
from albumexplore.tags.config.tag_rules_config import TagRulesConfig

logger = logging.getLogger(__name__)

class TagNormalizer:
    """Handles tag normalization and variant consolidation with atomic tag support."""
    
    def __init__(self, test_mode: bool = False, enable_atomic_tags: bool = True):
        """Initialize the normalizer with rules.
        
        Args:
            test_mode: If True, use test configuration instead of production rules
            enable_atomic_tags: If True, enable atomic tag decomposition
        """
        self._rules_config = TagRulesConfig(test_mode=test_mode)
        self._variant_cache = {}
        self._single_instance_tags = set()
        self._merge_history = []
        self._similarity_threshold = 0.7
        self._min_frequency_for_normalization = 2
        self._active = True  # Added: Normalization is active by default
        
        # Atomic tag system
        self._enable_atomic_tags = enable_atomic_tags
        self._atomic_config = {}
        self._atomic_decomposition_cache = {}
        self._valid_atomic_tags = set()
        
        if self._enable_atomic_tags:
            self._load_atomic_config()
        
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
    
    # ===== ATOMIC TAG SYSTEM METHODS =====
    
    def _load_atomic_config(self):
        """Load atomic tag configuration from the main config file."""
        try:
            # Get the config file path relative to this module
            config_dir = os.path.dirname(os.path.dirname(__file__))  # tags/
            config_path = os.path.join(config_dir, 'config', 'tag_rules.json')
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Load atomic decomposition rules
            self._atomic_config = config.get('atomic_decomposition', {})
            
            # Load valid atomic tags
            atomic_tags_config = config.get('atomic_tags', {})
            if 'all_valid_tags' in atomic_tags_config:
                self._valid_atomic_tags = set(atomic_tags_config['all_valid_tags'])
            
            logger.info(f"Loaded {len(self._atomic_config)} atomic decomposition rules")
            logger.info(f"Loaded {len(self._valid_atomic_tags)} valid atomic tags")
            
        except Exception as e:
            logger.warning(f"Could not load atomic config: {e}")
            self._atomic_config = {}
            self._valid_atomic_tags = set()
    
    def is_atomic_enabled(self) -> bool:
        """Check if atomic tag system is enabled."""
        return self._enable_atomic_tags
    
    def enable_atomic_tags(self, enable: bool = True):
        """Enable or disable atomic tag processing."""
        self._enable_atomic_tags = enable
        if enable and not self._atomic_config:
            self._load_atomic_config()
    
    def normalize_to_atomic(self, tag: str) -> List[str]:
        """Normalize a tag and decompose to atomic components.
        
        Args:
            tag: The tag to normalize and decompose
            
        Returns:
            List of atomic components for the tag
        """
        if not tag or not self._enable_atomic_tags:
            return [self.normalize(tag)] if tag else []
        
        # Clean and normalize basic format
        cleaned_tag = tag.lower().strip()
        
        # Check cache first
        if cleaned_tag in self._atomic_decomposition_cache:
            return self._atomic_decomposition_cache[cleaned_tag]
        
        # Apply atomic decomposition if rule exists
        if cleaned_tag in self._atomic_config:
            atomic_components = self._atomic_config[cleaned_tag].copy()
            self._atomic_decomposition_cache[cleaned_tag] = atomic_components
            return atomic_components
        
        # Check for case variations and format variations
        normalized_for_lookup = cleaned_tag.replace('-', ' ').replace('_', ' ')
        for rule_tag, components in self._atomic_config.items():
            rule_normalized = rule_tag.replace('-', ' ').replace('_', ' ')
            if rule_normalized == normalized_for_lookup:
                atomic_components = components.copy()
                self._atomic_decomposition_cache[cleaned_tag] = atomic_components
                return atomic_components
        
        # If no decomposition rule found, return normalized single tag
        normalized_single = self.normalize(tag)
        result = [normalized_single]
        self._atomic_decomposition_cache[cleaned_tag] = result
        return result
    
    def normalize_tag_list_to_atomic(self, tags: List[str]) -> List[str]:
        """Normalize a list of tags using atomic decomposition.
        
        Args:
            tags: List of tags to normalize and decompose
            
        Returns:
            List of unique atomic components from all tags
        """
        if not tags:
            return []
        
        if not self._enable_atomic_tags:
            return [self.normalize(tag) for tag in tags if tag]
        
        atomic_tags = []
        for tag in tags:
            if tag:  # Skip empty tags
                atomic_components = self.normalize_to_atomic(tag)
                atomic_tags.extend(atomic_components)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_atomic_tags = []
        for tag in atomic_tags:
            if tag and tag not in seen:
                seen.add(tag)
                unique_atomic_tags.append(tag)
        
        return unique_atomic_tags
    
    def validate_atomic_tag(self, tag: str) -> bool:
        """Check if a tag is a valid atomic component.
        
        Args:
            tag: The tag to validate
            
        Returns:
            True if the tag is a valid atomic component
        """
        if not self._enable_atomic_tags:
            return True
        
        return tag.lower().strip() in self._valid_atomic_tags
    
    def get_atomic_statistics(self) -> Dict[str, any]:
        """Get statistics about atomic tag system usage.
        
        Returns:
            Dictionary containing atomic tag statistics
        """
        return {
            'atomic_enabled': self._enable_atomic_tags,
            'decomposition_rules': len(self._atomic_config),
            'decomposition_cache_size': len(self._atomic_decomposition_cache),
            'valid_atomic_tags': len(self._valid_atomic_tags),
            'version': '1.0'
        }
    
    def clear_atomic_cache(self):
        """Clear the atomic decomposition cache."""
        self._atomic_decomposition_cache.clear()
    
    def reload_atomic_config(self):
        """Reload the atomic tag configuration."""
        if self._enable_atomic_tags:
            self._load_atomic_config()
            self.clear_atomic_cache()
