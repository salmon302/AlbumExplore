#!/usr/bin/env python3
"""
Production Adapter for Atomic Tag System

This adapter provides a simple interface for integrating atomic tags
into existing AlbumExplore production code.
"""

import json
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class AtomicTagAdapter:
    """Production adapter for atomic tag normalization"""
    
    def __init__(self, config_path: str = None):
        """Initialize the adapter"""
        if config_path is None:
            config_path = 'c:/Users/salmo/Documents/GitHub/AlbumExplore/src/albumexplore/config/tag_rules.json'
        
        self.config_path = config_path
        self.config = self._load_config()
        
    def _load_config(self) -> Dict:
        """Load atomic tag configuration"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load atomic tag config: {e}")
            return {}
    
    def normalize_tags(self, tags: List[str]) -> List[str]:
        """Normalize a list of tags to atomic components"""
        if not tags:
            return []
        
        atomic_tags = []
        decomp_rules = self.config.get('atomic_decomposition', {})
        
        for tag in tags:
            if not tag:
                continue
                
            cleaned_tag = tag.lower().strip()
            
            # Check for decomposition rule
            if cleaned_tag in decomp_rules:
                atomic_tags.extend(decomp_rules[cleaned_tag])
            else:
                # Check for case variants
                found = False
                for rule_tag, components in decomp_rules.items():
                    if rule_tag.replace('-', ' ') == cleaned_tag.replace('-', ' '):
                        atomic_tags.extend(components)
                        found = True
                        break
                
                if not found:
                    atomic_tags.append(cleaned_tag)
        
        # Remove duplicates while preserving order
        unique_tags = []
        seen = set()
        for tag in atomic_tags:
            if tag not in seen:
                seen.add(tag)
                unique_tags.append(tag)
        
        return unique_tags
    
    def is_atomic_tag(self, tag: str) -> bool:
        """Check if a tag is a valid atomic component"""
        valid_tags = self.config.get('atomic_tags', {}).get('all_valid_tags', [])
        return tag.lower() in valid_tags
    
    def get_core_genres(self) -> List[str]:
        """Get list of core genre atomic tags"""
        return self.config.get('atomic_tags', {}).get('core_genres', [])
    
    def get_style_modifiers(self) -> List[str]:
        """Get list of style modifier atomic tags"""
        return self.config.get('atomic_tags', {}).get('style_modifiers', [])

# Convenience function for easy integration
def normalize_album_tags(album_tags: List[str]) -> List[str]:
    """Simple function to normalize album tags to atomic components"""
    adapter = AtomicTagAdapter()
    return adapter.normalize_tags(album_tags)
