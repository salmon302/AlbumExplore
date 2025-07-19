#!/usr/bin/env python3
"""
Enhanced Tag Normalizer with Atomic Tag System Integration

This enhanced normalizer integrates the atomic tag consolidation system
into the primary AlbumExplore tag normalization workflow.
"""

from albumexplore.tags.normalizer.tag_normalizer import TagNormalizer as BaseTagNormalizer
import json
import re
from typing import List, Dict, Set, Tuple

class AtomicTagNormalizer(BaseTagNormalizer):
    """Enhanced tag normalizer with atomic tag decomposition"""
    
    def __init__(self, test_mode: bool = False):
        super().__init__(test_mode)
        self._atomic_config = self._load_atomic_config()
        self._decomposition_cache = {}
        
    def _load_atomic_config(self) -> Dict:
        """Load atomic tag configuration"""
        try:
            config_path = 'c:/Users/salmo/Documents/GitHub/AlbumExplore/src/albumexplore/config/tag_rules.json'
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return config.get('atomic_decomposition', {})
        except Exception as e:
            print(f"Warning: Could not load atomic config: {e}")
            return {}
    
    def normalize_to_atomic(self, tag: str) -> List[str]:
        """Normalize a tag and decompose to atomic components"""
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
        
        # Check for case variations
        for rule_tag, components in self._atomic_config.items():
            if rule_tag.replace('-', ' ') == cleaned_tag.replace('-', ' '):
                self._decomposition_cache[cleaned_tag] = components
                return components
        
        # If no decomposition rule found, return normalized single tag
        normalized_single = super().normalize(tag)
        result = [normalized_single]
        self._decomposition_cache[cleaned_tag] = result
        return result
    
    def normalize_tag_list(self, tags: List[str]) -> List[str]:
        """Normalize a list of tags using atomic decomposition"""
        if not tags:
            return []
        
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
    
    def validate_atomic_tag(self, tag: str) -> bool:
        """Check if a tag is a valid atomic component"""
        config_path = 'c:/Users/salmo/Documents/GitHub/AlbumExplore/src/albumexplore/config/tag_rules.json'
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            valid_tags = config.get('atomic_validation', {}).get('valid_atomic_tags', [])
            return tag.lower() in valid_tags
        except:
            return True  # Default to valid if config unavailable
    
    def get_tag_suggestions(self, tag: str) -> List[Tuple[str, str]]:
        """Get suggestions for atomic decomposition of a tag"""
        suggestions = []
        
        # Check if direct decomposition exists
        if tag.lower() in self._atomic_config:
            components = self._atomic_config[tag.lower()]
            suggestion = " + ".join(components)
            suggestions.append((suggestion, "atomic_decomposition"))
        
        # Check for pattern-based suggestions
        if '-' in tag or ' ' in tag:
            # Compound tag - suggest splitting
            if '-' in tag:
                parts = tag.split('-')
            else:
                parts = tag.split(' ')
            
            if len(parts) > 1:
                suggestion = " + ".join(part.strip() for part in parts if part.strip())
                suggestions.append((suggestion, "pattern_split"))
        
        # Check base normalizer suggestions
        base_normalized = super().normalize(tag)
        if base_normalized != tag.lower():
            suggestions.append((base_normalized, "base_normalization"))
        
        return suggestions
    
    def get_atomic_statistics(self) -> Dict:
        """Get statistics about atomic tag usage"""
        return {
            'total_decomposition_rules': len(self._atomic_config),
            'cache_size': len(self._decomposition_cache),
            'atomic_system_enabled': True,
            'version': '1.0'
        }
