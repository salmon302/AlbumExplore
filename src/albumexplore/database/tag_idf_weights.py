"""TF-IDF style tag weighting for similarity calculations.

Rare/specific tags should contribute more to similarity than common tags.
"""
from typing import Dict
from sqlalchemy.orm import Session
from albumexplore.database.models import Tag, Album
import math
import logging

logger = logging.getLogger(__name__)


def calculate_idf_weights(session: Session, min_frequency: int = 1) -> Dict[str, float]:
    """
    Calculate IDF (Inverse Document Frequency) weights for tags.
    
    Tags that appear on fewer albums are more specific and get higher weights.
    
    Args:
        session: Database session
        min_frequency: Minimum tag frequency to include
    
    Returns:
        Dict mapping tag_id -> IDF weight (higher = more rare/specific)
    """
    # Get total album count
    total_albums = session.query(Album).count()
    
    if total_albums == 0:
        logger.warning("No albums in database for IDF calculation")
        return {}
    
    # Get all tags with frequencies
    tags = session.query(Tag).filter(Tag.frequency >= min_frequency).all()
    
    weights = {}
    for tag in tags:
        if not tag.frequency or tag.frequency == 0:
            continue
        
        # IDF = log(total_albums / albums_with_tag)
        # Add 1 to avoid log(0) and ensure smooth scaling
        idf = math.log((total_albums + 1) / (tag.frequency + 1))
        weights[tag.id] = float(idf)
    
    logger.info(f"Calculated IDF weights for {len(weights)} tags")
    return weights


def normalize_weights(weights: Dict[str, float], target_mean: float = 1.0) -> Dict[str, float]:
    """
    Normalize weights to have a specific mean value.
    
    This ensures IDF weights integrate cleanly with other weighting systems.
    
    Args:
        weights: Dict of tag_id -> weight
        target_mean: Desired mean value (default 1.0 for neutral weighting)
    
    Returns:
        Normalized weights dict
    """
    if not weights:
        return weights
    
    values = list(weights.values())
    current_mean = sum(values) / len(values)
    
    if current_mean == 0:
        return weights
    
    scale_factor = target_mean / current_mean
    
    return {tag_id: weight * scale_factor for tag_id, weight in weights.items()}


def combine_weights(
    idf_weights: Dict[str, float],
    user_weights: Dict[str, float],
    idf_alpha: float = 0.5
) -> Dict[str, float]:
    """
    Combine IDF weights with user-specified per-tag weights.
    
    Args:
        idf_weights: IDF weights from calculate_idf_weights
        user_weights: User-specified weights from UI
        idf_alpha: Weight given to IDF (0.0 = ignore IDF, 1.0 = only IDF)
    
    Returns:
        Combined weights dict
    """
    # Get all tag IDs
    all_tag_ids = set(idf_weights.keys()) | set(user_weights.keys())
    
    combined = {}
    for tag_id in all_tag_ids:
        idf_weight = idf_weights.get(tag_id, 1.0)
        user_weight = user_weights.get(tag_id, 1.0)
        
        # Weighted combination
        combined[tag_id] = (idf_alpha * idf_weight) + ((1.0 - idf_alpha) * user_weight)
    
    return combined


def get_top_distinctive_tags(
    session: Session,
    limit: int = 50,
    min_frequency: int = 5
) -> list[tuple[str, float]]:
    """
    Get the most distinctive (high IDF) tags in the database.
    
    Useful for understanding what tags are most informative.
    
    Args:
        session: Database session
        limit: Number of tags to return
        min_frequency: Minimum frequency threshold
    
    Returns:
        List of (tag_name, idf_weight) tuples, sorted by IDF descending
    """
    idf_weights = calculate_idf_weights(session, min_frequency)
    
    # Get tag objects to map IDs to names
    tag_id_to_name = {}
    tags = session.query(Tag).all()
    for tag in tags:
        if tag.id in idf_weights and tag.name:
            tag_id_to_name[tag.id] = tag.name
    
    # Sort by IDF weight
    tag_scores = [
        (tag_id_to_name.get(tag_id, tag_id), weight)
        for tag_id, weight in idf_weights.items()
        if tag_id in tag_id_to_name
    ]
    tag_scores.sort(key=lambda x: x[1], reverse=True)
    
    return tag_scores[:limit]
