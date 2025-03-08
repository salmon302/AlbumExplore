from typing import List, Dict, Set, Optional, Tuple, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from difflib import SequenceMatcher
from .models import Tag, TagVariant, TagRelation, Album, TagCategory
from ..visualization.data_interface import TagNormalizer
from .tag_validation import TagValidator, TagValidationError
import logging

logger = logging.getLogger(__name__)

class TagManager:
    """Manages tag consolidation, normalization and maintenance."""
    
    def __init__(self, session: Session):
        self.session = session
        self._normalizer = TagNormalizer()
        self._validator = TagValidator(session)
        
    def consolidate_tags(self, dry_run: bool = False) -> Dict[str, int]:
        """
        Consolidate tags by merging variants and updating relationships.
        Returns dict with statistics about consolidation.
        """
        stats = {'merged': 0, 'updated': 0, 'errors': 0, 'warnings': 0}
        
        try:
            # Get all tags
            tags = self.session.query(Tag).all()
            processed = set()
            
            for tag in tags:
                if tag.id in processed:
                    continue
                    
                # Get normalized form
                normalized = self._normalizer.normalize(tag.name)
                if normalized != tag.name:
                    # Look for existing canonical tag
                    canonical = self.session.query(Tag).filter(
                        Tag.normalized_name == normalized,
                        Tag.is_canonical == 1
                    ).first()
                    
                    if canonical:
                        try:
                            # Validate merge
                            warnings = self._validator.validate_merge(tag, canonical)
                            if warnings:
                                stats['warnings'] += len(warnings)
                                for warning in warnings:
                                    logger.warning(f"Merge warning for {tag.name}: {warning}")
                            
                            if not dry_run:
                                # Merge into existing canonical tag
                                self._merge_tags(tag, canonical)
                                stats['merged'] += 1
                                
                        except TagValidationError as e:
                            logger.error(f"Validation error merging {tag.name}: {e}")
                            stats['errors'] += 1
                            continue
                    else:
                        # Make this the canonical tag
                        tag.normalized_name = normalized
                        tag.is_canonical = 1
                        stats['updated'] += 1
                        
                processed.add(tag.id)
                
            if not dry_run:
                self.session.commit()
            
        except Exception as e:
            logger.error(f"Error during tag consolidation: {e}")
            self.session.rollback()
            stats['errors'] += 1
            
        return stats
        
    def _merge_tags(self, source: Tag, target: Tag):
        """Merge source tag into target tag."""
        try:
            # Create variant record
            variant = TagVariant(
                variant=source.name,
                canonical_tag_id=target.id
            )
            self.session.add(variant)
            
            # Update album relationships
            for album in source.albums:
                if target not in album.tags:
                    album.tags.append(target)
                album.tags.remove(source)
            
            # Update tag relationships
            self._merge_tag_relations(source.id, target.id)
            
            # Mark source as non-canonical
            source.is_canonical = 0
            source.normalized_name = target.normalized_name
            source.category_id = target.category_id
            
        except Exception as e:
            logger.error(f"Error merging tags {source.name} -> {target.name}: {e}")
            raise
            
    def _merge_tag_relations(self, source_id: str, target_id: str):
        """Merge tag relationships when consolidating tags."""
        try:
            # Get all relationships involving source tag
            source_relations = self.session.query(TagRelation).filter(
                (TagRelation.tag1_id == source_id) |
                (TagRelation.tag2_id == source_id)
            ).all()
            
            for relation in source_relations:
                # Update or merge relationship
                other_id = relation.tag2_id if relation.tag1_id == source_id else relation.tag1_id
                existing = self.session.query(TagRelation).filter(
                    ((TagRelation.tag1_id == target_id) & (TagRelation.tag2_id == other_id)) |
                    ((TagRelation.tag1_id == other_id) & (TagRelation.tag2_id == target_id))
                ).first()
                
                if existing:
                    # Average the strength values
                    existing.strength = (existing.strength + relation.strength) / 2
                    self.session.delete(relation)
                else:
                    # Update the relationship to use target tag
                    if relation.tag1_id == source_id:
                        relation.tag1_id = target_id
                    else:
                        relation.tag2_id = target_id
                        
        except Exception as e:
            logger.error(f"Error merging tag relations: {e}")
            raise
            
    def suggest_category(self, tag: Tag) -> str:
        """Suggest a category for a tag based on its relationships."""
        # First try normalized form
        normalized = self._normalizer.normalize(tag.name)
        category = self._normalizer.get_category(normalized)
        if category != 'other':
            return category
            
        # Analyze relationships
        related_categories = {}
        
        # Check direct relationships
        relations = self.session.query(TagRelation).filter(
            (TagRelation.tag1_id == tag.id) |
            (TagRelation.tag2_id == tag.id)
        ).all()
        
        for rel in relations:
            other_id = rel.tag2_id if rel.tag1_id == tag.id else rel.tag1_id
            other_tag = self.session.query(Tag).get(other_id)
            if other_tag and other_tag.category_id:
                weight = rel.strength if rel.strength else 1.0
                related_categories[other_tag.category_id] = \
                    related_categories.get(other_tag.category_id, 0) + weight
                    
        if related_categories:
            return max(related_categories.items(), key=lambda x: x[1])[0]
            
        return 'other'
        
    def analyze_tag_usage(self) -> Dict[str, Any]:
        """
        Analyze tag usage patterns and variants.
        Returns statistics about tag usage.
        """
        try:
            stats = {
                'total_tags': 0,
                'canonical_tags': 0,
                'variants': 0,
                'unused_tags': 0,
                'uncategorized': 0,
                'most_common': [],
                'variants_by_tag': {},
                'categories': {}
            }
            
            # Get basic counts
            stats['total_tags'] = self.session.query(Tag).count()
            stats['canonical_tags'] = self.session.query(Tag).filter(Tag.is_canonical == 1).count()
            stats['variants'] = self.session.query(TagVariant).count()
            stats['uncategorized'] = self.session.query(Tag).filter(
                (Tag.category_id.is_(None)) | (Tag.category_id == 'other')
            ).count()
            
            # Get unused tags
            used_tags = self.session.query(Tag).join(Album.tags).distinct().count()
            stats['unused_tags'] = stats['total_tags'] - used_tags
            
            # Get most common tags
            common_tags = self.session.query(
                Tag, func.count(Album.id).label('usage_count')
            ).join(Album.tags).group_by(Tag).order_by(func.count(Album.id).desc()).limit(20).all()
            
            stats['most_common'] = [
                {'name': tag.name, 'count': count, 'category': tag.category_id}
                for tag, count in common_tags
            ]
            
            # Get variant counts by canonical tag
            variant_counts = self.session.query(
                Tag, func.count(TagVariant.id).label('variant_count')
            ).outerjoin(TagVariant).filter(Tag.is_canonical == 1).group_by(Tag).all()
            
            stats['variants_by_tag'] = {
                tag.name: count for tag, count in variant_counts if count > 0
            }
            
            # Get category statistics
            category_stats = self.session.query(
                TagCategory.id,
                TagCategory.name,
                func.count(Tag.id).label('tag_count')
            ).outerjoin(Tag).group_by(TagCategory).all()
            
            stats['categories'] = {
                cat.id: {'name': cat.name, 'count': count}
                for cat, count in category_stats
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error analyzing tag usage: {e}")
            raise
            
    def suggest_merges(self, min_similarity: float = 0.8) -> List[Dict[str, Any]]:
        """
        Suggest tags that could potentially be merged based on similarity.
        Returns list of suggestion objects.
        """
        suggestions = []
        
        try:
            # Get all canonical tags
            tags = self.session.query(Tag).filter_by(is_canonical=1).all()
            
            for i, tag1 in enumerate(tags):
                normalized1 = tag1.normalized_name or self._normalizer.normalize(tag1.name)
                
                for tag2 in tags[i+1:]:
                    normalized2 = tag2.normalized_name or self._normalizer.normalize(tag2.name)
                    
                    # Skip if tags are in different categories
                    if tag1.category_id != tag2.category_id:
                        continue
                        
                    # Calculate similarity
                    name_similarity = SequenceMatcher(None, normalized1, normalized2).ratio()
                    
                    if name_similarity >= min_similarity:
                        try:
                            # Validate potential merge
                            warnings = self._validator.validate_merge(tag1, tag2)
                            
                            suggestions.append({
                                'source': tag1.name,
                                'target': tag2.name,
                                'similarity': name_similarity,
                                'category': tag1.category_id,
                                'warnings': warnings
                            })
                        except TagValidationError:
                            continue
                            
        except Exception as e:
            logger.error(f"Error suggesting merges: {e}")
            
        return suggestions
        
    def get_tag_hierarchy(self) -> Dict[str, Any]:
        """
        Get the current tag hierarchy with category information.
        Returns dict mapping parent tags to sets of child tags.
        """
        try:
            hierarchy = {}
            categories = self.session.query(TagCategory).all()
            
            for category in categories:
                hierarchy[category.id] = {
                    'name': category.name,
                    'tags': {}
                }
                
                # Get canonical tags in this category
                tags = self.session.query(Tag).filter_by(
                    category_id=category.id,
                    is_canonical=1
                ).all()
                
                for tag in tags:
                    hierarchy[category.id]['tags'][tag.name] = {
                        'variants': [v.variant for v in tag.variants],
                        'children': [child.name for child in tag.child_tags]
                    }
                    
            return hierarchy
            
        except Exception as e:
            logger.error(f"Error getting tag hierarchy: {e}")
            raise