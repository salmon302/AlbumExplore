"""Module for validating tag operations and maintaining consistency."""

from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from .models import Tag, TagVariant, TagCategory, TagRelation
import re
import logging

logger = logging.getLogger(__name__)

class TagValidationError(Exception):
    """Raised when a tag operation violates validation rules."""
    pass

class TagValidator:
    """Validates tag operations and ensures consistency."""
    
    def __init__(self, session: Session):
        self.session = session
        
    def validate_merge(self, source: Tag, target: Tag) -> List[str]:
        """
        Validate whether two tags can be merged.
        Returns list of warnings, or raises TagValidationError if merge is invalid.
        """
        warnings = []
        
        # Check if either tag is already non-canonical
        if not source.is_canonical:
            raise TagValidationError(f"Source tag '{source.name}' is not a canonical tag")
        if not target.is_canonical:
            raise TagValidationError(f"Target tag '{target.name}' is not a canonical tag")
            
        # Check for category compatibility
        if source.category_id and target.category_id and source.category_id != target.category_id:
            warnings.append(
                f"Tags are from different categories: {source.category_id} vs {target.category_id}"
            )
            
        # Check for hierarchy conflicts
        if self._has_hierarchy_conflict(source, target):
            raise TagValidationError(
                f"Merging would create a circular hierarchy between {source.name} and {target.name}"
            )
            
        # Check for existing variants
        existing_variants = self.session.query(TagVariant).filter_by(
            canonical_tag_id=target.id
        ).count()
        if existing_variants > 0:
            warnings.append(f"Target tag already has {existing_variants} variants")
            
        return warnings
        
    def validate_category_change(self, tag: Tag, new_category_id: str) -> List[str]:
        """
        Validate whether a tag's category can be changed.
        Returns list of warnings, or raises TagValidationError if change is invalid.
        """
        warnings = []
        
        # Check if category exists
        category = self.session.query(TagCategory).get(new_category_id)
        if not category:
            raise TagValidationError(f"Category '{new_category_id}' does not exist")
            
        # Check impact on variants
        if tag.variants:
            warnings.append(
                f"Category change will affect {len(tag.variants)} variant tags"
            )
            
        # Check for conflicting relationships
        relations = self.session.query(TagRelation).filter(
            (TagRelation.tag1_id == tag.id) |
            (TagRelation.tag2_id == tag.id)
        ).all()
        
        conflicting = 0
        for rel in relations:
            other_tag = self.session.query(Tag).get(
                rel.tag2_id if rel.tag1_id == tag.id else rel.tag1_id
            )
            if other_tag and other_tag.category_id != new_category_id:
                conflicting += 1
                
        if conflicting > 0:
            warnings.append(
                f"Tag has {conflicting} relationships with tags in different categories"
            )
            
        return warnings
        
    def validate_new_tag(self, name: str, category_id: Optional[str] = None) -> bool:
        """
        Validate whether a new tag name is acceptable.
        Returns True if valid, False if invalid.
        """
        # Check for empty or invalid characters
        if not name or not re.match(r'^[\w\s\-]+$', name):
            return False
            
        # Check for existing tag
        existing = self.session.query(Tag).filter_by(name=name).first()
        if existing:
            return False
            
        # Check category if provided
        if category_id:
            category = self.session.query(TagCategory).get(category_id)
            if not category:
                return False
                
        return True
        
    def _has_hierarchy_conflict(self, tag1: Tag, tag2: Tag) -> bool:
        """Check if merging two tags would create a circular hierarchy."""
        # Get all ancestors of both tags
        ancestors1 = self._get_ancestors(tag1)
        ancestors2 = self._get_ancestors(tag2)
        
        # Check if either tag is in the other's ancestry
        return tag1.id in ancestors2 or tag2.id in ancestors1
        
    def _get_ancestors(self, tag: Tag, visited: Optional[set] = None) -> set:
        """Get all ancestor tags in the hierarchy."""
        if visited is None:
            visited = set()
            
        ancestors = set()
        for parent in tag.parent_tags:
            if parent.id not in visited:
                visited.add(parent.id)
                ancestors.add(parent.id)
                ancestors.update(self._get_ancestors(parent, visited))
                
        return ancestors