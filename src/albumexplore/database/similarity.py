"""Album similarity calculation module."""
from typing import List, Tuple, Set, Dict, Any, Optional
from sqlalchemy.orm import Session, joinedload
from .models import Album, Tag
from albumexplore.similarity import manual as manual_mod
from .tag_relationship_similarity import TagRelationshipSimilarity, load_default_relationships


def calculate_album_similarity_optimized(
    session: Session,
    album_id: str,
    limit: int = 50,
    min_similarity: float = 0.3,
    weights: Dict[str, float] = None,
    per_tag_weights: Dict[str, float] = None,
    manual_relationships: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    alpha_manual: float = 0.5,
    use_fuzzy_tags: bool = True,
) -> List[Tuple[Album, float, Dict[str, Any]]]:
    """
    Calculate similarity scores for top N albums compared to a target album.
    
    Args:
        session: Database session
        album_id: ID of the target album to find similar albums for
        limit: Maximum number of similar albums to return
        min_similarity: Minimum similarity threshold (0.0 to 1.0)
        weights: Optional weight overrides for similarity components
        per_tag_weights: Optional per-tag importance weights
        manual_relationships: Optional manual tag relationship mappings
        alpha_manual: Weight for manual relationships (0.0 to 1.0)
        use_fuzzy_tags: Whether to use fuzzy tag matching with relationships (default True)
        
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
    
    # Initialize tag relationship similarity engine if fuzzy matching enabled
    tag_rel_sim = None
    if use_fuzzy_tags:
        # Load relationships (try manual first, fall back to default)
        relationships = manual_relationships if manual_relationships else load_default_relationships()
        if relationships:
            tag_rel_sim = TagRelationshipSimilarity(relationships)
    
    # 4. Calculate similarity scores (in-memory, fast)
    similarities = []
    for candidate in candidate_albums:
        score, breakdown = _calculate_similarity(
            album, candidate,
            album_tag_ids, album_atomic_ids,
            album_genre, album_year, album_country,
            weights=weights,
            per_tag_weights=per_tag_weights,
            tag_rel_sim=tag_rel_sim,
        )
        # If manual relationships provided, compute manual signal between any tag pairs
        manual_raw = None
        try:
            if manual_relationships:
                # iterate tag name pairs (normalized lower-case)
                max_raw = None
                for t1 in getattr(album, 'tags', []):
                    for t2 in getattr(candidate, 'tags', []):
                        if not t1.name or not t2.name:
                            continue
                        a = str(t1.name).strip().lower()
                        b = str(t2.name).strip().lower()
                        r = manual_mod.manual_score(manual_relationships, a, b)
                        if r is None:
                            # try reverse direction
                            r = manual_mod.manual_score(manual_relationships, b, a)
                        if r is not None:
                            if max_raw is None or r > max_raw:
                                max_raw = r
                manual_raw = max_raw
        except Exception:
            # don't let manual mapping errors break the similarity calculation
            manual_raw = None

        if manual_raw is not None:
            # Merge manual signal with automated score
            combined = manual_mod.merge_manual_with_auto(manual_raw, score, alpha_manual=alpha_manual)
            breakdown['manual_raw'] = manual_raw
            breakdown['manual_combined'] = combined
            score = combined
        
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
    album1_country: str,
    weights: Dict[str, float] = None,
    per_tag_weights: Dict[str, float] = None,
    tag_rel_sim: Optional[TagRelationshipSimilarity] = None,
) -> Tuple[float, Dict[str, Any]]:
    """
    Calculate similarity score between two albums with detailed breakdown.
    
    Args:
        album1: First album
        album2: Second album
        album1_tag_ids: Pre-extracted tag IDs for album1
        album1_atomic_ids: Pre-extracted atomic tag IDs for album1
        album1_genre: Genre for album1
        album1_year: Release year for album1
        album1_country: Country for album1
        weights: Optional component weight overrides
        per_tag_weights: Optional per-tag importance weights
        tag_rel_sim: Optional TagRelationshipSimilarity for fuzzy matching
    
    Returns:
        Tuple of (total_similarity_score, breakdown_dict)
    """
    # Composite tag similarity
    album2_tag_ids = {t.id for t in album2.tags}
    
    # Use fuzzy tag matching if relationship engine provided
    if tag_rel_sim is not None:
        # Get tag names for fuzzy matching
        album1_tag_names = {t.name for t in album1.tags if t.name}
        album2_tag_names = {t.name for t in album2.tags if t.name}
        
        # Calculate fuzzy similarity
        tag_similarity = tag_rel_sim.calculate_tag_similarity_score(
            album1_tag_names,
            album2_tag_names,
            tag_objects1=list(album1.tags),
            tag_objects2=list(album2.tags),
            use_fuzzy=True
        )
        
        # For breakdown, still track exact matches
        shared_tags = album1_tag_ids & album2_tag_ids
        union_tags = album1_tag_ids | album2_tag_ids
    else:
        # Fall back to exact Jaccard similarity
        shared_tags = album1_tag_ids & album2_tag_ids
        union_tags = album1_tag_ids | album2_tag_ids

        # If per_tag_weights provided, use weighted Jaccard similarity
        def _tag_weight(tag_id: str, tag_objs: List[Any]) -> float:
            # Default weight 1.0, allow per_tag_weights keyed by id or name
            if not per_tag_weights:
                return 1.0
            # Try by id first
            if tag_id in per_tag_weights:
                return float(per_tag_weights[tag_id])
            # Fallback: try to find tag object's name mapping (build mapping once)
            return float(per_tag_weights.get(tag_id, 1.0))

        if per_tag_weights:
            weighted_shared = 0.0
            weighted_union = 0.0
            # Build set of all tag ids in union and sum weights accordingly
            for tid in union_tags:
                w = _tag_weight(tid, None)
                if tid in shared_tags:
                    weighted_shared += w
                weighted_union += w
            tag_similarity = (weighted_shared / weighted_union) if weighted_union else 0.0
        else:
            tag_similarity = len(shared_tags) / len(union_tags) if union_tags else 0
    
    # Atomic tag similarity (more granular)
    album2_atomic_ids = {t.id for t in album2.atomic_tags}
    shared_atomic = album1_atomic_ids & album2_atomic_ids
    union_atomic = album1_atomic_ids | album2_atomic_ids
    # For atomic tags, also respect per_tag_weights if provided
    if per_tag_weights:
        weighted_shared_a = 0.0
        weighted_union_a = 0.0
        for tid in union_atomic:
            w = float(per_tag_weights.get(tid, 1.0))
            if tid in shared_atomic:
                weighted_shared_a += w
            weighted_union_a += w
        atomic_similarity = (weighted_shared_a / weighted_union_a) if weighted_union_a else 0
    else:
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
    
    # Default base weights
    base_weights = {
        'composite_tags': 0.40,
        'atomic_tags': 0.30,
        'genre': 0.15,
        'year': 0.10,
        'country': 0.05,
        'vocal_style': 0.0,
    }

    # If caller provided overrides, merge them (caller may provide any subset)
    if weights:
        merged = base_weights.copy()
        for k, v in weights.items():
            if k in merged:
                merged[k] = float(v)
        weights = merged
    else:
        weights = base_weights

    # Compute vocal similarity (exact match on vocal_style)
    vocal_similarity = 0.0
    if album1.vocal_style and album2.vocal_style and album1.vocal_style == album2.vocal_style:
        vocal_similarity = 1.0

    total_score = (
        tag_similarity * weights['composite_tags'] +
        atomic_similarity * weights['atomic_tags'] +
        genre_similarity * weights['genre'] +
        year_similarity * weights['year'] +
        country_similarity * weights['country'] +
        vocal_similarity * weights.get('vocal_style', 0.0)
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
        'shared_tag_names': [t.name for t in album2.tags if t.id in shared_tags][:10],  # Max 10 for display
        'vocal_match': vocal_similarity > 0,
        'weights_used': weights,
        'per_tag_weights_used': per_tag_weights or {},
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
