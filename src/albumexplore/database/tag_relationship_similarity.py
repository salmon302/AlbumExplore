"""Enhanced tag similarity using relationship mappings.

This module extends the basic Jaccard similarity with semantic understanding
of tag relationships (synonyms, hierarchies, related concepts).
"""
from typing import Dict, List, Set, Tuple, Any, Optional
from albumexplore.similarity import manual as manual_mod
import logging

logger = logging.getLogger(__name__)


class TagRelationshipSimilarity:
    """Computes tag similarity using relationship mappings."""
    
    def __init__(self, relationships: Optional[Dict[str, List[Dict[str, Any]]]] = None):
        """
        Initialize with tag relationship mappings.
        
        Args:
            relationships: Dict mapping tag_name -> list of {tag, type, weight}
        """
        self.relationships = relationships or {}
        self._similarity_cache: Dict[Tuple[str, str], float] = {}
        
    def tag_similarity(self, tag1: str, tag2: str) -> float:
        """
        Calculate similarity between two tags using relationships.
        
        Returns:
            Similarity score from 0.0 to 1.0
            - 1.0: Identical or synonyms
            - 0.9: Parent-child relationship
            - 0.85: Close related
            - 0.75: Related
            - 0.65: Historical influence
            - 0.0: No relationship
            - negative: Exclude relationships (contradictory)
        """
        # Normalize tag names
        t1 = tag1.strip().lower()
        t2 = tag2.strip().lower()
        
        # Check cache
        cache_key = (t1, t2) if t1 <= t2 else (t2, t1)
        if cache_key in self._similarity_cache:
            return self._similarity_cache[cache_key]
        
        # Identical tags
        if t1 == t2:
            self._similarity_cache[cache_key] = 1.0
            return 1.0
        
        # Check relationships in both directions
        score = self._check_relationship(t1, t2)
        if score is None:
            score = self._check_relationship(t2, t1)
        
        result = score if score is not None else 0.0
        self._similarity_cache[cache_key] = result
        return result
    
    def _check_relationship(self, source_tag: str, target_tag: str) -> Optional[float]:
        """Check if source_tag has a relationship to target_tag."""
        if source_tag not in self.relationships:
            return None
        
        rels = self.relationships[source_tag]
        for rel in rels:
            rel_tag = rel.get('tag', '').strip().lower()
            if rel_tag == target_tag:
                # Use explicit weight if provided, otherwise use type default
                if 'weight' in rel:
                    return float(rel['weight'])
                
                # Default weights by relationship type
                rel_type = rel.get('type', 'related')
                return manual_mod.DEFAULT_TYPE_WEIGHTS.get(rel_type, 0.75)
        
        return None
    
    def fuzzy_tag_overlap(
        self,
        tags1: Set[str],
        tags2: Set[str],
        tag_objects1: List[Any] = None,
        tag_objects2: List[Any] = None,
        use_fuzzy: bool = True
    ) -> Tuple[float, float]:
        """
        Calculate fuzzy tag overlap considering relationships.
        
        Args:
            tags1: Set of tag names from album 1
            tags2: Set of tag names from album 2
            tag_objects1: Optional list of Tag objects for album 1
            tag_objects2: Optional list of Tag objects for album 2
            use_fuzzy: Whether to use fuzzy matching (relationships)
        
        Returns:
            Tuple of (shared_score, union_size) where:
            - shared_score: Weighted count of matching/related tags
            - union_size: Total unique tags across both albums
        """
        if not use_fuzzy:
            # Fall back to exact matching
            shared = tags1 & tags2
            union = tags1 | tags2
            return float(len(shared)), float(len(union))
        
        # Convert to lowercase for matching
        tags1_lower = {t.strip().lower() for t in tags1}
        tags2_lower = {t.strip().lower() for t in tags2}
        
        # Calculate fuzzy overlap
        shared_score = 0.0
        matched_in_tags2 = set()
        
        for t1 in tags1_lower:
            best_match_score = 0.0
            best_match_tag = None
            
            for t2 in tags2_lower:
                sim = self.tag_similarity(t1, t2)
                if sim > best_match_score:
                    best_match_score = sim
                    best_match_tag = t2
            
            if best_match_score > 0:
                shared_score += best_match_score
                if best_match_tag:
                    matched_in_tags2.add(best_match_tag)
        
        # Union size is all unique tags from both sets
        union_size = len(tags1_lower | tags2_lower)
        
        return shared_score, float(union_size)
    
    def calculate_tag_similarity_score(
        self,
        tags1: Set[str],
        tags2: Set[str],
        tag_objects1: List[Any] = None,
        tag_objects2: List[Any] = None,
        use_fuzzy: bool = True
    ) -> float:
        """
        Calculate normalized similarity score between two tag sets.
        
        Returns:
            Similarity score from 0.0 to 1.0 using fuzzy Jaccard similarity
        """
        if not tags1 and not tags2:
            return 0.0
        
        shared_score, union_size = self.fuzzy_tag_overlap(
            tags1, tags2, tag_objects1, tag_objects2, use_fuzzy
        )
        
        if union_size == 0:
            return 0.0
        
        # Normalize by union size (fuzzy Jaccard)
        return shared_score / union_size
    
    def get_related_tags(self, tag: str, min_similarity: float = 0.7) -> List[Tuple[str, float]]:
        """
        Get all tags related to the given tag.
        
        Args:
            tag: Tag name to find relationships for
            min_similarity: Minimum similarity threshold
        
        Returns:
            List of (related_tag, similarity_score) tuples
        """
        tag_lower = tag.strip().lower()
        related = []
        
        if tag_lower in self.relationships:
            for rel in self.relationships[tag_lower]:
                rel_tag = rel.get('tag')
                if not rel_tag:
                    continue
                
                score = self.tag_similarity(tag_lower, rel_tag)
                if score >= min_similarity:
                    related.append((rel_tag, score))
        
        return sorted(related, key=lambda x: x[1], reverse=True)
    
    def clear_cache(self):
        """Clear the similarity cache."""
        self._similarity_cache.clear()


def load_default_relationships() -> Dict[str, List[Dict[str, Any]]]:
    """
    Load default tag relationships from the comprehensive YAML file.
    
    Returns:
        Relationship dictionary or empty dict if file not found
    """
    import os
    from pathlib import Path
    
    try:
        # Try to load comprehensive relationships
        repo_root = Path(__file__).parent.parent.parent.parent
        rel_path = repo_root / "data" / "tag_relationships_comprehensive.yml"
        
        if rel_path.exists():
            logger.info(f"Loading tag relationships from {rel_path}")
            return manual_mod.load_relationships(str(rel_path))
        
        # Fall back to basic relationships
        rel_path = repo_root / "data" / "tag_relationships.yml"
        if rel_path.exists():
            logger.info(f"Loading tag relationships from {rel_path}")
            return manual_mod.load_relationships(str(rel_path))
        
        logger.warning("No tag relationship file found, using empty relationships")
        return {}
    
    except Exception as e:
        logger.error(f"Error loading tag relationships: {e}", exc_info=True)
        return {}
