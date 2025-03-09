"""Tag similarity analysis component."""
import re
import numpy as np
from typing import List, Tuple, Dict, Set
from difflib import SequenceMatcher
from .tag_analyzer import TagAnalyzer

class TagSimilarity:
    """Analyzes similarity between tags based on various metrics."""
    
    def __init__(self, analyzer: TagAnalyzer):
        """Initialize with a TagAnalyzer instance."""
        self.analyzer = analyzer
        self._similarity_cache = {}
        
    def find_similar_tags(self, tag: str, threshold: float = 0.6) -> List[Tuple[str, float]]:
        """Find tags similar to the given tag using multiple similarity metrics.
        
        Args:
            tag: The tag to find similar tags for
            threshold: Minimum similarity score (0-1) for suggestions
            
        Returns:
            List of (similar_tag, similarity_score) tuples
        """
        # Check cache first
        if tag in self._similarity_cache:
            return [s for s in self._similarity_cache[tag] if s[1] >= threshold]
            
        similar_tags = []
        
        # Get co-occurrence based similarity
        co_occur_similar = self._get_cooccurrence_similarity(tag)
        similar_tags.extend(co_occur_similar)
        
        # Get string similarity based matches
        string_similar = self._get_string_similarity(tag)
        similar_tags.extend(string_similar)
        
        # Get pattern-based similarity
        pattern_similar = self._get_pattern_similarity(tag)
        similar_tags.extend(pattern_similar)
        
        # Combine scores from different metrics and normalize
        combined = self._combine_similarity_scores(similar_tags)
        
        # Cache results
        self._similarity_cache[tag] = combined
        
        # Return results above threshold
        return [s for s in combined if s[1] >= threshold]
        
    def _get_cooccurrence_similarity(self, tag: str) -> List[Tuple[str, float]]:
        """Calculate similarity based on tag co-occurrences."""
        similar = []
        co_occurrences = self.analyzer.get_co_occurrences(tag)
        
        if not co_occurrences:
            return []
        
        # Get total occurrences for normalization
        total = sum(co_occurrences.values())
        
        # Calculate normalized co-occurrence scores
        for other_tag, count in co_occurrences.items():
            if other_tag != tag:
                # Normalize by total co-occurrences and tag frequency
                score = count / total * min(1.0, count / self.analyzer.get_tag_frequency(other_tag))
                similar.append((other_tag, score))
                
        return sorted(similar, key=lambda x: x[1], reverse=True)
        
    def _get_string_similarity(self, tag: str) -> List[Tuple[str, float]]:
        """Calculate similarity based on string similarity metrics."""
        similar = []
        
        # Get all tags from analyzer
        all_tags = list(self.analyzer.tag_counts.keys())
        
        for other_tag in all_tags:
            if other_tag != tag:
                # Use SequenceMatcher for string similarity
                score = SequenceMatcher(None, tag, other_tag).ratio()
                
                # Boost score if tags share words
                tag_words = set(tag.split())
                other_words = set(other_tag.split())
                shared_words = len(tag_words & other_words)
                if shared_words:
                    word_score = shared_words / max(len(tag_words), len(other_words))
                    score = max(score, word_score)
                    
                similar.append((other_tag, score))
                
        return sorted(similar, key=lambda x: x[1], reverse=True)
        
    def _get_pattern_similarity(self, tag: str) -> List[Tuple[str, float]]:
        """Calculate similarity based on common tag patterns."""
        similar = []
        
        # Get common patterns from analyzer
        patterns = self.analyzer.get_common_patterns()
        
        # Split tag into parts
        parts = tag.split()
        if len(parts) > 1:
            prefix = parts[0]
            suffix = parts[-1]
            
            # Check for tags with same prefix pattern
            if prefix in patterns:
                for base in patterns[prefix]:
                    similar_tag = f"{prefix} {base}"
                    if similar_tag != tag:
                        similar.append((similar_tag, 0.7))
                        
            # Check for tags with same suffix pattern
            if suffix in patterns:
                for base in patterns[suffix]:
                    similar_tag = f"{base} {suffix}"
                    if similar_tag != tag:
                        similar.append((similar_tag, 0.7))
                        
        return similar
        
    def _combine_similarity_scores(self, similarities: List[List[Tuple[str, float]]]) -> List[Tuple[str, float]]:
        """Combine and normalize similarity scores from different metrics."""
        # Combine scores for same tags
        combined_scores: Dict[str, float] = {}
        
        for tag, score in similarities:
            if tag in combined_scores:
                # Use max score as we want to preserve strong matches from any metric
                combined_scores[tag] = max(combined_scores[tag], score)
            else:
                combined_scores[tag] = score
                
        # Convert to list and sort
        combined = [(tag, score) for tag, score in combined_scores.items()]
        return sorted(combined, key=lambda x: x[1], reverse=True)
        
    def find_similar_tag_clusters(self, min_similarity: float = 0.7) -> List[Set[str]]:
        """Find clusters of similar tags that might be variants.
        
        Args:
            min_similarity: Minimum similarity score to consider tags related
            
        Returns:
            List of sets containing related tags
        """
        clusters = []
        processed_tags = set()
        
        for tag in self.analyzer.tag_counts:
            if tag in processed_tags:
                continue
                
            # Find similar tags
            similar = self.find_similar_tags(tag, min_similarity)
            if similar:
                # Create new cluster with original tag and similar ones
                cluster = {tag}
                cluster.update(t for t, _ in similar)
                clusters.append(cluster)
                processed_tags.update(cluster)
            else:
                processed_tags.add(tag)
                
        return clusters
        
    def clear_cache(self):
        """Clear the similarity cache."""
        self._similarity_cache.clear()