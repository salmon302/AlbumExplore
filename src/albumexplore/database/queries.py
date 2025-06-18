"""Database queries."""
from typing import List, Tuple, Set
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_
from .models import Album, Tag, album_tags

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