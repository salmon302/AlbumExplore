"""Handler for single-instance tags."""
from typing import List, Dict, Tuple, Optional
from collections import Counter
from .tag_analyzer import TagAnalyzer
from .tag_similarity import TagSimilarity
from ..normalizer.tag_normalizer import TagNormalizer

class SingleInstanceHandler:
    """Handles analysis and normalization of single-instance tags."""
    
    def __init__(self, analyzer: TagAnalyzer, normalizer: TagNormalizer, similarity: TagSimilarity):
        """Initialize with required components."""
        self.analyzer = analyzer
        self.normalizer = normalizer
        self.similarity = similarity
        
    def identify_single_instance_tags(self) -> Dict[str, int]:
        """Identify and return all single-instance tags."""
        single_instance = {tag: count for tag, count in self.analyzer.tag_counts.items() 
                         if count == 1}
        return single_instance
        
    def suggest_normalization(self, tag: str) -> List[Tuple[str, float, str]]:
        """Suggest normalizations for a single-instance tag."""
        # First check normalizer's suggestions
        suggestions = self.normalizer.suggest_normalization_for_single_instance(tag)
        
        # Get similar tags from similarity analyzer
        similar_tags = self.similarity.find_similar_tags(tag, threshold=0.6)
        
        # Add similar tags with appropriate confidence scores
        for similar_tag, sim_score in similar_tags:
            if similar_tag != tag:
                freq = self.analyzer.get_tag_frequency(similar_tag)
                if freq > 1:  # Only suggest more frequently used tags
                    # Adjust confidence based on frequency and similarity
                    confidence = sim_score * min(1.0, freq / 10)
                    reason = f"Similar to more common tag (used {freq} times)"
                    suggestions.append((similar_tag, confidence, reason))
        
        # Get pattern-based suggestions
        pattern_suggestions = self._get_pattern_based_suggestions(tag)
        suggestions.extend(pattern_suggestions)
        
        # Sort by confidence and remove duplicates
        seen = set()
        unique_suggestions = []
        for s in sorted(suggestions, key=lambda x: x[1], reverse=True):
            if s[0] not in seen:
                seen.add(s[0])
                unique_suggestions.append(s)
        
        return unique_suggestions
        
    def _get_pattern_based_suggestions(self, tag: str) -> List[Tuple[str, float, str]]:
        """Generate suggestions based on common tag patterns."""
        suggestions = []
        parts = tag.split()
        
        if len(parts) > 1:
            # Check if prefix matches common patterns
            prefix = parts[0]
            base = ' '.join(parts[1:])
            
            # Get common patterns from analyzer
            patterns = self.analyzer.get_common_patterns()
            
            # Check prefix patterns
            if prefix in patterns:
                for common_base in patterns[prefix]:
                    if common_base != base:
                        suggestion = f"{prefix} {common_base}"
                        confidence = 0.7
                        reason = f"Matches common prefix pattern: {prefix}"
                        suggestions.append((suggestion, confidence, reason))
            
            # Check suffix patterns
            suffix = parts[-1]
            prefix_parts = parts[:-1]
            if suffix in patterns:
                for common_base in patterns[suffix]:
                    if common_base != ' '.join(prefix_parts):
                        suggestion = f"{common_base} {suffix}"
                        confidence = 0.7
                        reason = f"Matches common suffix pattern: {suffix}"
                        suggestions.append((suggestion, confidence, reason))
        
        return suggestions
        
    def get_consolidation_suggestions(self) -> Dict[str, List[Tuple[str, float, str]]]:
        """Get consolidation suggestions for all single-instance tags."""
        single_instance_tags = self.identify_single_instance_tags()
        suggestions = {}
        
        for tag in single_instance_tags:
            tag_suggestions = self.suggest_normalization(tag)
            if tag_suggestions:
                suggestions[tag] = tag_suggestions
                
        return suggestions
        
    def apply_suggestion(self, tag: str, suggestion: str):
        """Apply a normalization suggestion."""
        self.normalizer.add_single_instance_rule(tag, suggestion)
        # Register in analyzer for future analysis
        self.analyzer.tag_counts[suggestion] = self.analyzer.tag_counts.pop(tag, 1)
        
    def apply_suggestions_batch(self, suggestions: Dict[str, str], min_confidence: float = 0.8):
        """Apply multiple suggestions that meet the confidence threshold."""
        applied = []
        for tag, suggestion_list in suggestions.items():
            # Get best suggestion that meets threshold
            for sugg, conf, _ in suggestion_list:
                if conf >= min_confidence:
                    self.apply_suggestion(tag, sugg)
                    applied.append((tag, sugg, conf))
                    break
        return applied