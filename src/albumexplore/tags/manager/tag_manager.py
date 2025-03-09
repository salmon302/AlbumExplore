"""Centralized tag management system."""
import logging
from typing import Dict, List, Set, Tuple, Optional
from collections import Counter, defaultdict
import pandas as pd

from ..normalizer.tag_normalizer import TagNormalizer
from ..config.tag_rules_config import TagRulesConfig
from ..analysis.single_instance_handler import SingleInstanceHandler
from ..analysis.tag_analyzer import TagAnalyzer
from ..analysis.tag_similarity import TagSimilarity

logger = logging.getLogger(__name__)

class TagManager:
    """Coordinates tag normalization, analysis, and management."""
    
    def __init__(self):
        """Initialize tag management components."""
        self.normalizer = TagNormalizer()
        self.rules_config = TagRulesConfig()
        self.tag_data = None
        self.analyzer = None
        self.similarity = None
        self.single_instance_handler = None
        
        # Statistics tracking
        self.stats = {
            'total_tags': 0,
            'normalized_tags': 0,
            'single_instance': 0,
            'categories': defaultdict(int)
        }
        
        # Cache for performance
        self._category_cache = {}
        self._normalized_cache = {}
        
    def process_tag_data(self, tags_data: pd.DataFrame):
        """Process new tag data and initialize analysis components."""
        self.tag_data = tags_data
        
        # Reset statistics
        self.stats = {
            'total_tags': 0,
            'normalized_tags': 0,
            'single_instance': 0,
            'categories': defaultdict(int)
        }
        
        # Initialize analysis components
        self.analyzer = TagAnalyzer(tags_data)
        self.similarity = TagSimilarity(self.analyzer)
        self.single_instance_handler = SingleInstanceHandler(
            self.analyzer,
            self.normalizer,
            self.similarity
        )
        
        # Calculate initial statistics
        self._calculate_statistics()
        
    def normalize_tags(self, tags: List[str]) -> List[str]:
        """Normalize a list of tags."""
        normalized = []
        for tag in tags:
            if tag in self._normalized_cache:
                normalized.append(self._normalized_cache[tag])
            else:
                norm_tag = self.normalizer.normalize(tag)
                self._normalized_cache[tag] = norm_tag
                normalized.append(norm_tag)
        return normalized
        
    def categorize_tag(self, tag: str) -> str:
        """Get category for a tag with caching."""
        if tag in self._category_cache:
            return self._category_cache[tag]
            
        category = self.normalizer.get_category(tag)
        self._category_cache[tag] = category
        self.stats['categories'][category] += 1
        return category
        
    def get_similar_tags(self, tag: str, threshold: float = 0.7) -> List[Tuple[str, float]]:
        """Get similar tags based on configured rules and analysis."""
        if not self.similarity:
            return []
            
        normalized = self.normalizer.normalize(tag)
        return self.similarity.find_similar_tags(normalized, threshold)
        
    def handle_single_instance_tag(self, tag: str) -> Optional[str]:
        """Process a single-instance tag and suggest normalization."""
        if not self.single_instance_handler:
            return None
            
        suggestions = self.single_instance_handler.suggest_normalization(tag)
        if suggestions:
            best_suggestion = suggestions[0]
            if best_suggestion[1] >= 0.8:  # High confidence
                self.normalizer.add_single_instance_rule(tag, best_suggestion[0])
                return best_suggestion[0]
        return None
        
    def get_tag_statistics(self) -> Dict:
        """Get current tag statistics."""
        return self.stats
        
    def _calculate_statistics(self):
        """Calculate and update tag statistics."""
        if not self.tag_data is None:
            all_tags = set()
            normalized_tags = set()
            
            for tags in self.tag_data['tags']:
                if isinstance(tags, list):
                    all_tags.update(tags)
                    normalized = self.normalize_tags(tags)
                    normalized_tags.update(normalized)
            
            self.stats['total_tags'] = len(all_tags)
            self.stats['normalized_tags'] = len(normalized_tags)
            
            # Count single instance tags
            tag_counts = Counter()
            for tags in self.tag_data['tags']:
                if isinstance(tags, list):
                    tag_counts.update(tags)
            
            single_instance = {tag for tag, count in tag_counts.items() if count == 1}
            self.stats['single_instance'] = len(single_instance)
            
            # Update category counts
            self._category_cache.clear()
            self.stats['categories'] = defaultdict(int)
            for tag in normalized_tags:
                self.categorize_tag(tag)
                
    def export_analysis(self) -> Dict:
        """Export complete tag analysis data."""
        analysis = {
            'statistics': self.stats,
            'categories': dict(self.stats['categories']),
            'normalizations': self._normalized_cache,
            'single_instance_suggestions': {}
        }
        
        if self.single_instance_handler:
            # Add suggestions for single instance tags
            single_instance_tags = {tag for tag, count 
                                  in Counter(self._normalized_cache.values()).items() 
                                  if count == 1}
            
            for tag in single_instance_tags:
                suggestions = self.single_instance_handler.suggest_normalization(tag)
                if suggestions:
                    analysis['single_instance_suggestions'][tag] = suggestions
        
        return analysis