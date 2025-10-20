"""Album similarity calculation module."""
from typing import List, Tuple, Set, Dict, Any
from sqlalchemy.orm import Session, joinedload
from .models import Album, Tag


def calculate_album_similarity_optimized(
    session: Session,
    album_id: str,
    limit: int = 50,
    min_similarity: float = 0.3
) -> List[Tuple[Album, float, Dict[str, Any]]]:
    """
    Calculate similarity scores for top N albums compared to a target album.
    
    Args:
        session: Database session
        album_id: ID of the target album to find similar albums for
        limit: Maximum number of similar albums to return
        min_similarity: Minimum similarity threshold (0.0 to 1.0)
        
    Returns:
        List of (album, similarity_score, breakdown_dict) tuples, sorted by score descending
    """
    # 1. Get target album with preloaded tags (1 query)
    album = session.query(Album).options(
        joinedload(Album.tags),
        joinedload(Album.atomic_tags)
    ).filter(Album.id == album_id).first()
    
    if not album:
        return []
    
    # 2. Extract album attributes
    album_tag_ids = {t.id for t in album.tags}
    album_atomic_ids = {t.id for t in album.atomic_tags}
    album_genre = album.genre
    album_year = album.release_year
    album_country = album.country
    
    # If album has no tags, can't find similar albums by tag
    if not album_tag_ids and not album_atomic_ids:
        return []
    
    # 3. Bulk query: Get all candidate albums with tags (optimized)
    # Query albums that share at least one tag OR atomic tag
    query = session.query(Album).options(
        joinedload(Album.tags),
        joinedload(Album.atomic_tags)
    ).filter(Album.id != album_id)
    
    # Join with tags if we have composite tags
    if album_tag_ids:
        query = query.join(Album.tags).filter(Tag.id.in_(album_tag_ids))
    
    candidate_albums = query.distinct().all()
    
    # 4. Calculate similarity scores (in-memory, fast)
    similarities = []
    for candidate in candidate_albums:
        score, breakdown = _calculate_similarity(
            album, candidate,
            album_tag_ids, album_atomic_ids,
            album_genre, album_year, album_country
        )
        
        if score >= min_similarity:
            similarities.append((candidate, score, breakdown))
    
    # 5. Sort by score and limit results
    similarities.sort(key=lambda x: x[1], reverse=True)
    return similarities[:limit]


def _calculate_similarity(
    album1: Album,
    album2: Album,
    album1_tag_ids: Set[str],
    album1_atomic_ids: Set[str],
    album1_genre: str,
    album1_year: int,
    album1_country: str
) -> Tuple[float, Dict[str, Any]]:
    """
    Calculate similarity score between two albums with detailed breakdown.
    
    Returns:
        Tuple of (total_similarity_score, breakdown_dict)
    """
    # Composite tag similarity (Jaccard similarity)
    album2_tag_ids = {t.id for t in album2.tags}
    shared_tags = album1_tag_ids & album2_tag_ids
    union_tags = album1_tag_ids | album2_tag_ids
    tag_similarity = len(shared_tags) / len(union_tags) if union_tags else 0
    
    # Atomic tag similarity (more granular)
    album2_atomic_ids = {t.id for t in album2.atomic_tags}
    shared_atomic = album1_atomic_ids & album2_atomic_ids
    union_atomic = album1_atomic_ids | album2_atomic_ids
    atomic_similarity = len(shared_atomic) / len(union_atomic) if union_atomic else 0
    
    # Genre similarity (exact match)
    genre_similarity = 1.0 if album1_genre and album2.genre and album1_genre == album2.genre else 0.0
    
    # Year proximity (albums within 5 years = 1.0, decays linearly to 0 at 20 years)
    if album1_year and album2.release_year:
        year_diff = abs(album1_year - album2.release_year)
        year_similarity = max(0, 1.0 - (year_diff / 20.0))
    else:
        year_similarity = 0.0
    
    # Country match (exact match)
    country_similarity = 1.0 if album1_country and album2.country and album1_country == album2.country else 0.0
    
    # Weighted combination
    weights = {
        'composite_tags': 0.40,
        'atomic_tags': 0.30,
        'genre': 0.15,
        'year': 0.10,
        'country': 0.05
    }
    
    total_score = (
        tag_similarity * weights['composite_tags'] +
        atomic_similarity * weights['atomic_tags'] +
        genre_similarity * weights['genre'] +
        year_similarity * weights['year'] +
        country_similarity * weights['country']
    )
    
    # Build breakdown dictionary for tooltip/details
    breakdown = {
        'shared_tags_count': len(shared_tags),
        'total_tags': len(album1_tag_ids),
        'shared_atomic_count': len(shared_atomic),
        'total_atomic': len(album1_atomic_ids),
        'tag_similarity': tag_similarity,
        'atomic_similarity': atomic_similarity,
        'genre_match': genre_similarity > 0,
        'year_proximity': year_similarity,
        'year_diff': abs(album1_year - album2.release_year) if album1_year and album2.release_year else None,
        'country_match': country_similarity > 0,
        'shared_tag_names': [album2.tags[i].name for i, tag_id in enumerate(album2_tag_ids) if tag_id in shared_tags][:10],  # Max 10 for display
    }
    
    return total_score, breakdown


def get_shared_tags(
    session: Session,
    album1_id: str,
    album2_id: str
) -> List[Tag]:
    """
    Get the list of tags shared between two albums.
    
    Args:
        session: Database session
        album1_id: ID of first album
        album2_id: ID of second album
        
    Returns:
        List of shared Tag objects
    """
    album1 = session.query(Album).options(joinedload(Album.tags)).filter(Album.id == album1_id).first()
    album2 = session.query(Album).options(joinedload(Album.tags)).filter(Album.id == album2_id).first()
    
    if not album1 or not album2:
        return []
    
    tag1_ids = {t.id for t in album1.tags}
    shared_tags = [t for t in album2.tags if t.id in tag1_ids]
    
    return shared_tags
