#!/usr/bin/env python
"""Script to analyze and recategorize tags based on their relationships and usage patterns."""

import click
from sqlalchemy.orm import Session
from ..database import get_session, models
from ..visualization.data_interface import TagNormalizer
import logging

logger = logging.getLogger(__name__)

def analyze_tag_relationships(session: Session, tag: models.Tag) -> dict:
    """Analyze a tag's relationships to determine its most likely category."""
    related_categories = {}
    
    # Check direct relationships through tag hierarchy
    for parent in tag.parent_tags:
        if parent.category_id:
            related_categories[parent.category_id] = related_categories.get(parent.category_id, 0) + 2

    # Check tags that frequently appear together
    tag_relationships = session.query(models.TagRelation).filter(
        (models.TagRelation.tag1_id == tag.id) | 
        (models.TagRelation.tag2_id == tag.id)
    ).all()
    
    for rel in tag_relationships:
        other_tag = session.query(models.Tag).filter(
            models.Tag.id == (rel.tag2_id if rel.tag1_id == tag.id else rel.tag1_id)
        ).first()
        
        if other_tag and other_tag.category_id:
            weight = rel.strength if rel.strength else 1.0
            related_categories[other_tag.category_id] = related_categories.get(other_tag.category_id, 0) + weight
    
    return related_categories

def suggest_category(normalizer: TagNormalizer, tag_name: str, relationships: dict) -> str:
    """Suggest a category based on tag name and relationships."""
    # First try relationships
    if relationships:
        strongest_category = max(relationships.items(), key=lambda x: x[1])[0]
        if relationships[strongest_category] > 1.0:  # Threshold for relationship-based categorization
            return strongest_category
    
    # Fall back to name-based categorization
    return normalizer.get_category(tag_name)

@click.command()
@click.option('--dry-run', is_flag=True, help='Show suggested changes without applying them')
@click.option('--force', is_flag=True, help='Apply changes without confirmation')
def main(dry_run: bool, force: bool):
    """Analyze and recategorize tags based on their relationships and patterns."""
    session = get_session()
    normalizer = TagNormalizer()
    changes = []
    
    try:
        # Get all tags without categories or with potentially incorrect categories
        tags = session.query(models.Tag).filter(
            (models.Tag.category_id.is_(None)) |
            (models.Tag.category_id == 'other')
        ).all()
        
        for tag in tags:
            relationships = analyze_tag_relationships(session, tag)
            suggested_category = suggest_category(normalizer, tag.name, relationships)
            
            if suggested_category != tag.category_id:
                changes.append({
                    'tag': tag.name,
                    'old_category': tag.category_id or 'None',
                    'new_category': suggested_category,
                    'confidence': relationships.get(suggested_category, 0) if relationships else 0
                })
        
        if dry_run or not force:
            click.echo(f"\nFound {len(changes)} potential category changes:")
            for change in changes:
                click.echo(f"  {change['tag']}: {change['old_category']} -> {change['new_category']}")
                click.echo(f"    Confidence: {change['confidence']:.2f}")
            
            if dry_run:
                return
                
            if not force and not click.confirm("\nApply these changes?"):
                click.echo("Operation cancelled.")
                return
        
        # Apply changes
        for change in changes:
            tag = session.query(models.Tag).filter_by(name=change['tag']).first()
            tag.category_id = change['new_category']
        
        session.commit()
        click.echo(f"Successfully updated {len(changes)} tag categories.")
        
    except Exception as e:
        logger.error(f"Error during tag categorization: {e}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == '__main__':
    main()