#!/usr/bin/env python
"""Script to analyze tag similarity and suggest potential merges."""

import click
from sqlalchemy.orm import Session
from ..database import get_session, models
from ..visualization.data_interface import TagNormalizer
import difflib
import logging
from typing import List, Tuple, Set

logger = logging.getLogger(__name__)

def get_tag_context(session: Session, tag: models.Tag) -> Set[str]:
    """Get the context in which a tag is used (related tags, parent/child tags)."""
    context = set()
    
    # Add parent and child tags
    for parent in tag.parent_tags:
        context.add(parent.normalized_name or parent.name)
    for child in tag.child_tags:
        context.add(child.normalized_name or child.name)
        
    # Add tags that frequently appear together
    tag_relationships = session.query(models.TagRelation).filter(
        (models.TagRelation.tag1_id == tag.id) | 
        (models.TagRelation.tag2_id == tag.id)
    ).all()
    
    for rel in tag_relationships:
        other_id = rel.tag2_id if rel.tag1_id == tag.id else rel.tag1_id
        other_tag = session.query(models.Tag).get(other_id)
        if other_tag:
            context.add(other_tag.normalized_name or other_tag.name)
            
    return context

def calculate_similarity(tag1: str, tag2: str, context1: Set[str], context2: Set[str]) -> float:
    """Calculate similarity score between two tags based on name and context."""
    # Name similarity using difflib
    name_similarity = difflib.SequenceMatcher(None, tag1, tag2).ratio()
    
    # Context similarity using Jaccard index
    context_similarity = len(context1 & context2) / len(context1 | context2) if context1 or context2 else 0
    
    # Weighted combination
    return 0.7 * name_similarity + 0.3 * context_similarity

def find_similar_pairs(session: Session, min_similarity: float = 0.8) -> List[Tuple[str, str, float]]:
    """Find pairs of similar tags that might be variants."""
    normalizer = TagNormalizer()
    similar_pairs = []
    
    # Get all canonical tags
    tags = session.query(models.Tag).filter_by(is_canonical=1).all()
    tag_contexts = {tag.id: get_tag_context(session, tag) for tag in tags}
    
    # Compare all pairs
    for i, tag1 in enumerate(tags):
        normalized1 = tag1.normalized_name or normalizer.normalize(tag1.name)
        for tag2 in tags[i+1:]:
            normalized2 = tag2.normalized_name or normalizer.normalize(tag2.name)
            
            # Skip if tags are in different categories
            if tag1.category_id != tag2.category_id:
                continue
                
            similarity = calculate_similarity(
                normalized1, 
                normalized2,
                tag_contexts[tag1.id],
                tag_contexts[tag2.id]
            )
            
            if similarity >= min_similarity:
                similar_pairs.append((tag1.name, tag2.name, similarity))
                
    return similar_pairs

@click.command()
@click.option('--min-similarity', default=0.8, help='Minimum similarity threshold (0-1)')
@click.option('--category', help='Only analyze tags in this category')
@click.option('--output', type=click.Path(), help='Write results to file')
def main(min_similarity: float, category: str, output: str):
    """Analyze tag similarity and suggest potential merges."""
    session = get_session()
    
    try:
        # Get tags to analyze
        query = session.query(models.Tag).filter_by(is_canonical=1)
        if category:
            query = query.filter_by(category_id=category)
        
        total_tags = query.count()
        click.echo(f"Analyzing {total_tags} canonical tags...")
        
        # Find similar pairs
        similar_pairs = find_similar_pairs(session, min_similarity)
        
        # Group by primary tag
        suggestions = {}
        for tag1, tag2, similarity in similar_pairs:
            if tag1 not in suggestions:
                suggestions[tag1] = []
            suggestions[tag1].append((tag2, similarity))
            
        # Output results
        if output:
            with open(output, 'w') as f:
                for tag1, matches in suggestions.items():
                    f.write(f"\n{tag1}:\n")
                    for tag2, sim in sorted(matches, key=lambda x: x[1], reverse=True):
                        f.write(f"  {tag2} (similarity: {sim:.2f})\n")
        else:
            click.echo("\nPotential tag merges:")
            for tag1, matches in suggestions.items():
                click.echo(f"\n{tag1}:")
                for tag2, sim in sorted(matches, key=lambda x: x[1], reverse=True):
                    click.echo(f"  {tag2} (similarity: {sim:.2f})")
                    
        click.echo(f"\nFound {len(similar_pairs)} potential merges.")
        
    except Exception as e:
        logger.error(f"Error analyzing tag similarity: {e}")
        raise
    finally:
        session.close()

if __name__ == '__main__':
    main()