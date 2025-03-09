"""Configuration loader for tag normalization rules."""
import os
import json
import logging
from typing import Dict, List, Optional, Set
from pathlib import Path

logger = logging.getLogger(__name__)

class TagRulesConfig:
    """Manages loading and access to tag normalization rules."""
    
    def __init__(self, test_mode: bool = False):
        """Initialize configuration loader.
        
        Args:
            test_mode: If True, load test configuration instead of production rules
        """
        self._config: Dict = {}
        self._cache: Dict = {}
        self._test_mode = test_mode
        self._load_config()
        
    def _load_config(self):
        """Load configuration from JSON file."""
        if self._test_mode:
            # Use test configuration
            config_path = str(Path(__file__).parent.parent.parent.parent.parent / 'tests' / 'test_data' / 'tag_rules_test.json')
        else:
            # Use production configuration
            config_path = os.path.join(os.path.dirname(__file__), '../../config/tag_rules.json')
        
        try:
            with open(config_path, 'r') as f:
                self._config = json.load(f)
            # Clear cache when config is reloaded
            self._cache.clear()
        except FileNotFoundError:
            logger.warning(f"Config file not found at {config_path}, using empty configuration")
            self._config = {}
        except Exception as e:
            logger.error(f"Error loading tag rules config: {e}")
            self._config = {}
            
    def reload(self):
        """Reload configuration from file."""
        self._load_config()
        
    def get_category_info(self, category: str) -> Optional[Dict]:
        """Get information about a specific category."""
        return self._config.get('categories', {}).get(category)
        
    def get_all_categories(self) -> List[str]:
        """Get list of all defined categories."""
        return list(self._config.get('categories', {}).keys())
        
    def get_prefix_patterns(self, prefix: str) -> List[str]:
        """Get all patterns for a specific prefix."""
        return self._config.get('prefix_patterns', {}).get(prefix, [])
        
    def get_all_prefix_patterns(self) -> Dict[str, List[str]]:
        """Get all prefix patterns."""
        return self._config.get('prefix_patterns', {})
        
    def get_suffix_patterns(self, suffix: str) -> List[str]:
        """Get all patterns for a specific suffix."""
        return self._config.get('suffix_patterns', {}).get(suffix, [])
        
    def get_all_suffix_patterns(self) -> Dict[str, List[str]]:
        """Get all suffix patterns."""
        return self._config.get('suffix_patterns', {})
        
    def get_compound_terms(self) -> Dict[str, List[str]]:
        """Get all compound term mappings."""
        return self._config.get('compound_terms', {})
        
    def get_misspellings(self) -> Dict[str, List[str]]:
        """Get all misspelling mappings."""
        return self._config.get('common_misspellings', {})
        
    def get_single_instance_mappings(self) -> Dict[str, str]:
        """Get all single instance tag mappings."""
        return self._config.get('single_instance_mappings', {})
        
    def get_category_for_tag(self, tag: str) -> Optional[str]:
        """Determine the category for a tag."""
        # Check cache first
        if tag in self._cache:
            return self._cache[tag]
            
        tag = tag.lower()
        for category, info in self._config.get('categories', {}).items():
            # Check core terms
            if any(term in tag for term in info.get('core_terms', [])):
                self._cache[tag] = category
                return category
                
            # Check primary genres
            if tag in info.get('primary_genres', []):
                self._cache[tag] = category
                return category
                
            # Check if it's a modified primary genre
            for genre in info.get('primary_genres', []):
                if genre in tag:
                    for modifier in info.get('modifiers', []):
                        if modifier in tag:
                            self._cache[tag] = category
                            return category
        
        # No category found
        self._cache[tag] = None
        return None
        
    def get_normalized_form(self, tag: str) -> str:
        """Get the normalized form of a tag based on all rules."""
        tag = tag.lower()
        
        # Check compound terms first
        compound_terms = self.get_compound_terms()
        for normalized, variants in compound_terms.items():
            if tag in variants:
                return normalized
                
        # Check misspellings
        misspellings = self.get_misspellings()
        for correct, variants in misspellings.items():
            if tag in variants:
                return correct
                
        # Check single instance mappings
        single_instance = self.get_single_instance_mappings()
        if tag in single_instance:
            return single_instance[tag]
            
        # Apply prefix standardization
        for prefix, patterns in self.get_all_prefix_patterns().items():
            for pattern in patterns:
                if tag.startswith(pattern):
                    tag = prefix + tag[len(pattern):]
                    break
                    
        # Apply suffix standardization
        for suffix, patterns in self.get_all_suffix_patterns().items():
            for pattern in patterns:
                if tag.endswith(pattern):
                    tag = tag[:-len(pattern)] + suffix
                    break
        
        return tag
        
    def save_changes(self) -> bool:
        """Save current configuration back to file."""
        if self._test_mode:
            config_path = str(Path(__file__).parent.parent.parent.parent.parent / 'tests' / 'test_data' / 'tag_rules_test.json')
        else:
            config_path = os.path.join(os.path.dirname(__file__), '../../config/tag_rules.json')
            
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            
            with open(config_path, 'w') as f:
                json.dump(self._config, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving tag rules config: {e}")
            return False