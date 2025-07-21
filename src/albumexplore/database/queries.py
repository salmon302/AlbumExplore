"""Database queries."""
from typing import List, Tuple, Set, Dict, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_
from .models import Album, Tag, AtomicTag, TagDecomposition, album_tags, album_atomic_tags

def get_albums_with_tags(session: Session) -> List[Album]:
    """Get all albums with their tags."""
    # Avoid eager loading tags to prevent recursion issues
    # Tags will be loaded lazily when accessed
    return session.query(Album).all()

def get_album_tags(session: Session, album_id: int) -> List[Tag]:
    """Get tags for a specific album."""
    album = session.query(Album).get(album_id)
    return album.tags if album else []

def get_related_albums(session: Session, album_id: int, min_shared_tags: int = 2) -> List[Tuple[Album, float]]:
    """Get related albums based on tag similarity."""
    # Get the album's tags
    album = session.query(Album).get(album_id)
    if not album or not album.tags:
        return []
    
    album_tag_ids = {t.id for t in album.tags}
    
    # Find albums with shared tags
    related = []
    albums = session.query(Album).join(Album.tags).filter(
        and_(
            Album.id != album_id,
            Tag.id.in_(album_tag_ids)
        )
    ).all()
    
    for other_album in albums:
        other_tag_ids = {t.id for t in other_album.tags}
        shared_tags = album_tag_ids & other_tag_ids
        
        if len(shared_tags) >= min_shared_tags:
            # Calculate similarity score
            similarity = len(shared_tags) / (len(album_tag_ids) + len(other_tag_ids) - len(shared_tags))
            related.append((other_album, similarity))
    
    # Sort by similarity score
    related.sort(key=lambda x: x[1], reverse=True)
    return related

def get_tag_co_occurrences(session: Session, min_count: int = 2) -> List[Tuple[Tag, Tag, int]]:
    """Get tag co-occurrence counts."""
    # First get all album-tag pairs
    pairs = session.query(
        album_tags.c.album_id,
        album_tags.c.tag_id
    ).all()
    
    # Build co-occurrence dictionary
    co_occurrences = {}
    for album_id, tag1_id in pairs:
        for _, tag2_id in pairs:
            if tag1_id < tag2_id:  # Avoid counting both (a,b) and (b,a)
                key = (tag1_id, tag2_id)
                co_occurrences[key] = co_occurrences.get(key, 0) + 1
    
    # Filter and format results
    results = []
    for (tag1_id, tag2_id), count in co_occurrences.items():
        if count >= min_count:
            tag1 = session.query(Tag).get(tag1_id)
            tag2 = session.query(Tag).get(tag2_id)
            results.append((tag1, tag2, count))
    
    return sorted(results, key=lambda x: x[2], reverse=True)

def search_albums(session: Session, query: str) -> List[Album]:
    """Search albums by artist or title."""
    return session.query(Album).filter(
        or_(
            Album.pa_artist_name_on_album.ilike(f"%{query}%"),
            Album.title.ilike(f"%{query}%")
        )
    ).all()

def get_albums_by_year(session: Session, year: int) -> List[Album]:
    """Get albums from a specific year."""
    return session.query(Album).filter(Album.year == year).all()

def get_albums_by_genre(session: Session, genre: str) -> List[Album]:
    """Get albums of a specific genre."""
    return session.query(Album).filter(Album.genre.ilike(f"%{genre}%")).all()

def get_most_common_tags(session: Session, limit: int = 20) -> List[Tuple[Tag, int]]:
    """Get most commonly used tags."""
    return session.query(
        Tag,
        func.count(album_tags.c.album_id).label('count')
    ).join(album_tags).group_by(Tag).order_by('count DESC').limit(limit).all()


# =============================================================================
# ATOMIC TAG QUERIES
# =============================================================================

def get_albums_with_atomic_tags(session: Session) -> List[Album]:
    """Get all albums with their atomic tags loaded."""
    return session.query(Album).options(
        joinedload(Album.atomic_tags),
        joinedload(Album.tags)
    ).all()


def get_atomic_tag_breakdown(session: Session, tag_name: str) -> Optional[Dict]:
    """Get atomic decomposition breakdown for a composite tag."""
    # Find the composite tag
    composite_tag = session.query(Tag).filter(Tag.name == tag_name).first()
    if not composite_tag:
        return None
    
    # Get its decomposition
    decompositions = session.query(TagDecomposition).filter(
        TagDecomposition.composite_tag_id == composite_tag.id
    ).join(AtomicTag).all()
    
    if not decompositions:
        return None
    
    atomic_components = []
    for decomp in decompositions:
        atomic_components.append({
            'name': decomp.atomic_tag.name,
            'category': decomp.atomic_tag.category_id,
            'confidence': decomp.confidence,
            'rule_source': decomp.rule_source,
            'is_core': decomp.atomic_tag.is_core
        })
    
    return {
        'composite_tag': tag_name,
        'is_composite': composite_tag.is_composite,
        'decomposition_confidence': composite_tag.decomposition_confidence,
        'atomic_components': atomic_components,
        'component_count': len(atomic_components)
    }


def filter_albums_by_atomic_components(
    session: Session, 
    atomic_tag_names: List[str], 
    match_all: bool = True
) -> List[Album]:
    """Filter albums by atomic tag components."""
    if not atomic_tag_names:
        return []
    
    # Get atomic tag IDs
    atomic_tags = session.query(AtomicTag).filter(
        AtomicTag.name.in_(atomic_tag_names)
    ).all()
    atomic_tag_ids = [tag.id for tag in atomic_tags]
    
    if not atomic_tag_ids:
        return []
    
    query = session.query(Album).join(album_atomic_tags).filter(
        album_atomic_tags.c.atomic_tag_id.in_(atomic_tag_ids)
    )
    
    if match_all:
        # Albums must have ALL specified atomic tags
        query = query.group_by(Album.id).having(
            func.count(album_atomic_tags.c.atomic_tag_id) == len(atomic_tag_ids)
        )
    
    return query.all()


def get_atomic_tag_statistics(session: Session) -> Dict:
    """Get comprehensive atomic tag statistics."""
    # Basic counts
    total_atomic_tags = session.query(AtomicTag).count()
    total_decompositions = session.query(TagDecomposition).count()
    composite_tags_count = session.query(Tag).filter(Tag.is_composite == True).count()
    
    # Category distribution
    category_counts = session.query(
        AtomicTag.category_id,
        func.count(AtomicTag.id).label('count')
    ).group_by(AtomicTag.category_id).all()
    
    # Most common atomic tags
    atomic_usage = session.query(
        AtomicTag.name,
        func.count(album_atomic_tags.c.album_id).label('album_count')
    ).join(album_atomic_tags).group_by(AtomicTag.id).order_by('album_count DESC').limit(10).all()
    
    # Decomposition confidence distribution
    confidence_stats = session.query(
        func.avg(TagDecomposition.confidence),
        func.min(TagDecomposition.confidence),
        func.max(TagDecomposition.confidence)
    ).first()
    
    return {
        'total_atomic_tags': total_atomic_tags,
        'total_decompositions': total_decompositions,
        'composite_tags_count': composite_tags_count,
        'category_distribution': dict(category_counts),
        'top_atomic_tags': atomic_usage,
        'confidence_stats': {
            'average': confidence_stats[0] if confidence_stats[0] else 0,
            'min': confidence_stats[1] if confidence_stats[1] else 0,
            'max': confidence_stats[2] if confidence_stats[2] else 0
        }
    }


def get_albums_by_atomic_tag(session: Session, atomic_tag_name: str) -> List[Album]:
    """Get all albums that have a specific atomic tag."""
    return session.query(Album).join(album_atomic_tags).join(AtomicTag).filter(
        AtomicTag.name == atomic_tag_name
    ).all()


def get_atomic_tag_co_occurrences(session: Session, min_count: int = 2) -> List[Tuple[AtomicTag, AtomicTag, int]]:
    """Get atomic tag co-occurrence counts across albums."""
    # Get all album-atomic tag pairs
    pairs = session.query(
        album_atomic_tags.c.album_id,
        album_atomic_tags.c.atomic_tag_id
    ).all()
    
    # Build co-occurrence dictionary by album
    album_tags = {}
    for album_id, atomic_tag_id in pairs:
        if album_id not in album_tags:
            album_tags[album_id] = []
        album_tags[album_id].append(atomic_tag_id)
    
    # Count co-occurrences
    co_occurrences = {}
    for album_id, tag_ids in album_tags.items():
        for i, tag1_id in enumerate(tag_ids):
            for tag2_id in tag_ids[i+1:]:
                key = (min(tag1_id, tag2_id), max(tag1_id, tag2_id))
                co_occurrences[key] = co_occurrences.get(key, 0) + 1
    
    # Filter and format results
    results = []
    for (tag1_id, tag2_id), count in co_occurrences.items():
        if count >= min_count:
            tag1 = session.query(AtomicTag).get(tag1_id)
            tag2 = session.query(AtomicTag).get(tag2_id)
            if tag1 and tag2:
                results.append((tag1, tag2, count))
    
    return sorted(results, key=lambda x: x[2], reverse=True)


def search_albums_by_atomic_tags(
    session: Session, 
    atomic_tag_names: List[str],
    include_composite: bool = True
) -> List[Album]:
    """Search albums by atomic tag names with optional composite tag matching."""
    if not atomic_tag_names:
        return []
    
    # Direct atomic tag search
    atomic_albums = filter_albums_by_atomic_components(
        session, atomic_tag_names, match_all=False
    )
    
    if not include_composite:
        return atomic_albums
    
    # Also search composite tags that contain these atomic components
    composite_albums = set()
    for atomic_name in atomic_tag_names:
        # Find composite tags that decompose to this atomic tag
        decompositions = session.query(TagDecomposition).join(AtomicTag).filter(
            AtomicTag.name == atomic_name
        ).all()
        
        for decomp in decompositions:
            # Get albums tagged with this composite tag
            albums = session.query(Album).join(album_tags).filter(
                album_tags.c.tag_id == decomp.composite_tag_id
            ).all()
            composite_albums.update(albums)
    
    # Combine and deduplicate results
    all_albums = set(atomic_albums) | composite_albums
    return list(all_albums)


def get_tag_atomic_summary(session: Session, tag_id: str) -> Dict:
    """Get a comprehensive summary of a tag's atomic properties."""
    tag = session.query(Tag).get(tag_id)
    if not tag:
        return {}
    
    summary = {
        'tag_name': tag.name,
        'is_atomic': tag.is_atomic,
        'is_composite': tag.is_composite,
        'decomposition_confidence': tag.decomposition_confidence,
        'last_atomic_update': tag.last_atomic_update
    }
    
    if tag.is_composite:
        # Get atomic breakdown
        decompositions = session.query(TagDecomposition).filter(
            TagDecomposition.composite_tag_id == tag.id
        ).join(AtomicTag).all()
        
        summary['atomic_components'] = [
            {
                'name': decomp.atomic_tag.name,
                'category': decomp.atomic_tag.category_id,
                'confidence': decomp.confidence,
                'rule_source': decomp.rule_source
            }
            for decomp in decompositions
        ]
    
    return summary