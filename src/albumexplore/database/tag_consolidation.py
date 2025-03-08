"""Utility for consolidating and normalizing tags."""

from typing import Dict, List, Set, Tuple
from sqlalchemy.orm import Session
from .models import Tag, TagVariant
from ..visualization.data_interface import TagNormalizer
import logging

logger = logging.getLogger(__name__)

class TagConsolidator:
    def __init__(self, db: Session):
        self.db = db
        self._normalizer = TagNormalizer()
        
    def consolidate_tags(self):
        """Consolidate and normalize all tags in the database."""
        logger.info("Starting tag consolidation process...")
        
        # Get all tags
        tags = self.db.query(Tag).all()
        tag_groups: Dict[str, List[Tag]] = {}
        
        # Group tags by normalized name
        for tag in tags:
            normalized = self._normalizer.normalize(tag.name)
            tag.normalized_name = normalized
            if normalized not in tag_groups:
                tag_groups[normalized] = []
            tag_groups[normalized].append(tag)
        
        # Process each group
        for normalized_name, group in tag_groups.items():
            if len(group) > 1:
                self._merge_tag_group(normalized_name, group)
            else:
                # Single tag just needs normalized name
                group[0].normalized_name = normalized_name
        
        self.db.commit()
        logger.info("Tag consolidation complete")
    
    def _merge_tag_group(self, normalized_name: str, tags: List[Tag]):
        """Merge a group of tags into a single canonical tag."""
        # Select canonical tag (usually the most common variant)
        canonical = max(tags, key=lambda t: len(t.albums))
        other_tags = [t for t in tags if t != canonical]
        
        logger.info(f"Merging {len(other_tags)} variants into canonical tag '{canonical.name}'")
        
        # Create variants for other tags
        for tag in other_tags:
            variant = TagVariant(
                variant=tag.name,
                canonical_tag=canonical
            )
            self.db.add(variant)
            
            # Move all albums to canonical tag
            for album in tag.albums:
                if canonical not in album.tags:
                    album.tags.append(canonical)
                album.tags.remove(tag)
            
            # Delete old tag
            self.db.delete(tag)
        
        canonical.normalized_name = normalized_name
        self.db.commit()