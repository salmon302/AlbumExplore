"""
Cross-source album matching utility.

Provides fuzzy matching to link albums from different data sources.
"""
import logging
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Tuple

from sqlalchemy.orm import Session

# Try to use rapidfuzz (faster), fall back to python-Levenshtein
try:
    from rapidfuzz import fuzz
    USING_RAPIDFUZZ = True
except ImportError:
    from Levenshtein import ratio as lev_ratio
    USING_RAPIDFUZZ = False

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from albumexplore.database.models import Album, Artist

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    """Result of a matching operation."""
    album: Optional[Album]
    confidence: float
    match_method: str  # 'mbid', 'exact', 'fuzzy', 'none'
    details: Dict[str, Any]
    
    @property
    def is_match(self) -> bool:
        return self.album is not None and self.confidence >= 0.7


def fuzz_ratio(s1: str, s2: str) -> float:
    """
    Calculate fuzzy string similarity (0-1).
    
    Uses rapidfuzz if available, otherwise python-Levenshtein.
    """
    if not s1 or not s2:
        return 0.0
    
    if USING_RAPIDFUZZ:
        return fuzz.ratio(s1, s2) / 100.0
    else:
        return lev_ratio(s1, s2)


def normalize_for_matching(text: str) -> str:
    """
    Normalize text for matching.
    
    - Lowercase
    - Remove common prefixes/suffixes
    - Strip punctuation
    - Normalize whitespace
    """
    if not text:
        return ""
    
    text = text.lower().strip()
    
    # Remove common articles
    for article in ['the ', 'a ', 'an ']:
        if text.startswith(article):
            text = text[len(article):]
    
    # Remove punctuation
    text = ''.join(c if c.isalnum() or c.isspace() else ' ' for c in text)
    
    # Normalize whitespace
    text = ' '.join(text.split())
    
    return text


class AlbumMatcher:
    """
    Match albums across data sources.
    
    Matching priority:
    1. MusicBrainz ID (MBID) - exact match
    2. Artist + Album title - exact match (case-insensitive)
    3. Artist + Album title - fuzzy match with confidence threshold
    
    Usage:
        matcher = AlbumMatcher(session)
        
        result = matcher.match(
            artist="Pink Floyd",
            album="The Wall",
            year=1979,
            mbid=None
        )
        
        if result.is_match:
            print(f"Matched with {result.confidence:.0%} confidence")
    """
    
    # Matching thresholds
    EXACT_MATCH_THRESHOLD = 0.95
    FUZZY_MATCH_THRESHOLD = 0.80
    MINIMUM_CONFIDENCE = 0.70
    
    # Weights for combined scoring
    ARTIST_WEIGHT = 0.4
    TITLE_WEIGHT = 0.5
    YEAR_WEIGHT = 0.1
    
    def __init__(self, session: Session):
        """
        Initialize the matcher.
        
        Args:
            session: SQLAlchemy database session
        """
        self.session = session
        self._album_cache: Dict[str, Album] = {}
        self._load_cache()
    
    def _load_cache(self):
        """Pre-load albums for faster matching."""
        logger.info("Loading album cache for matching...")
        albums = self.session.query(Album).all()
        
        for album in albums:
            # Cache by MBID
            if album.mbid:
                self._album_cache[f"mbid:{album.mbid}"] = album
            
            # Cache by normalized artist+title
            artist_name = album.pa_artist_name_on_album or ""
            if album.artist_obj:
                artist_name = album.artist_obj.name
            
            key = self._make_cache_key(artist_name, album.title)
            self._album_cache[key] = album
        
        logger.info(f"Cached {len(albums)} albums")
    
    def _make_cache_key(self, artist: str, title: str) -> str:
        """Create a cache key from artist and title."""
        return f"{normalize_for_matching(artist)}||{normalize_for_matching(title)}"
    
    def match_by_mbid(self, mbid: str) -> Optional[Album]:
        """
        Find album by MusicBrainz ID.
        
        Args:
            mbid: MusicBrainz Release ID
            
        Returns:
            Album if found, None otherwise
        """
        if not mbid:
            return None
        
        # Check cache first
        cache_key = f"mbid:{mbid}"
        if cache_key in self._album_cache:
            return self._album_cache[cache_key]
        
        # Query database
        return self.session.query(Album).filter(Album.mbid == mbid).first()
    
    def match_exact(self, artist: str, title: str) -> Optional[Album]:
        """
        Find album by exact artist+title match (case-insensitive).
        
        Args:
            artist: Artist name
            title: Album title
            
        Returns:
            Album if found, None otherwise
        """
        cache_key = self._make_cache_key(artist, title)
        return self._album_cache.get(cache_key)
    
    def match_fuzzy(
        self,
        artist: str,
        title: str,
        year: Optional[int] = None,
        limit: int = 5,
    ) -> List[Tuple[Album, float]]:
        """
        Find albums by fuzzy matching.
        
        Args:
            artist: Artist name
            title: Album title
            year: Release year (optional, improves matching)
            limit: Maximum number of candidates to return
            
        Returns:
            List of (Album, confidence) tuples, sorted by confidence
        """
        normalized_artist = normalize_for_matching(artist)
        normalized_title = normalize_for_matching(title)
        
        candidates = []
        
        for album in self.session.query(Album).all():
            # Get album's artist name
            album_artist = album.pa_artist_name_on_album or ""
            if album.artist_obj:
                album_artist = album.artist_obj.name
            
            normalized_album_artist = normalize_for_matching(album_artist)
            normalized_album_title = normalize_for_matching(album.title or "")
            
            # Calculate component scores
            artist_score = fuzz_ratio(normalized_artist, normalized_album_artist)
            title_score = fuzz_ratio(normalized_title, normalized_album_title)
            
            # Year bonus/penalty
            year_score = 1.0
            if year and album.release_year:
                year_diff = abs(year - album.release_year)
                if year_diff == 0:
                    year_score = 1.0
                elif year_diff == 1:
                    year_score = 0.9
                elif year_diff <= 2:
                    year_score = 0.7
                else:
                    year_score = 0.5
            
            # Combined score
            confidence = (
                artist_score * self.ARTIST_WEIGHT +
                title_score * self.TITLE_WEIGHT +
                year_score * self.YEAR_WEIGHT
            )
            
            # Only include candidates above minimum threshold
            if confidence >= self.MINIMUM_CONFIDENCE:
                candidates.append((album, confidence))
        
        # Sort by confidence, descending
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        return candidates[:limit]
    
    def match(
        self,
        artist: str,
        title: str,
        year: Optional[int] = None,
        mbid: Optional[str] = None,
    ) -> MatchResult:
        """
        Find the best matching album using all available methods.
        
        Args:
            artist: Artist name
            title: Album title
            year: Release year (optional)
            mbid: MusicBrainz ID (optional, highest priority)
            
        Returns:
            MatchResult with best match and confidence
        """
        # 1. Try MBID match (highest confidence)
        if mbid:
            album = self.match_by_mbid(mbid)
            if album:
                return MatchResult(
                    album=album,
                    confidence=1.0,
                    match_method='mbid',
                    details={'mbid': mbid}
                )
        
        # 2. Try exact match
        album = self.match_exact(artist, title)
        if album:
            return MatchResult(
                album=album,
                confidence=0.99,
                match_method='exact',
                details={
                    'artist': artist,
                    'title': title,
                    'matched_title': album.title,
                }
            )
        
        # 3. Try fuzzy match
        candidates = self.match_fuzzy(artist, title, year)
        if candidates:
            best_album, best_confidence = candidates[0]
            
            if best_confidence >= self.FUZZY_MATCH_THRESHOLD:
                return MatchResult(
                    album=best_album,
                    confidence=best_confidence,
                    match_method='fuzzy',
                    details={
                        'artist': artist,
                        'title': title,
                        'matched_artist': best_album.pa_artist_name_on_album,
                        'matched_title': best_album.title,
                        'candidates': len(candidates),
                    }
                )
        
        # No match found
        return MatchResult(
            album=None,
            confidence=0.0,
            match_method='none',
            details={
                'artist': artist,
                'title': title,
                'reason': 'No matching album found',
            }
        )
    
    def match_batch(
        self,
        albums: List[Dict[str, Any]],
        progress_callback: Optional[callable] = None,
    ) -> List[MatchResult]:
        """
        Match multiple albums.
        
        Args:
            albums: List of dicts with 'artist', 'title', 'year', 'mbid' keys
            progress_callback: Called with (current, total, result) after each
            
        Returns:
            List of MatchResult objects
        """
        results = []
        total = len(albums)
        
        for i, album_data in enumerate(albums):
            result = self.match(
                artist=album_data.get('artist', ''),
                title=album_data.get('title', ''),
                year=album_data.get('year'),
                mbid=album_data.get('mbid'),
            )
            results.append(result)
            
            if progress_callback:
                progress_callback(i + 1, total, result)
        
        return results
    
    def get_stats(self, results: List[MatchResult]) -> Dict[str, Any]:
        """
        Get statistics about matching results.
        
        Args:
            results: List of MatchResult objects
            
        Returns:
            Statistics dictionary
        """
        total = len(results)
        if total == 0:
            return {'total': 0}
        
        matched = sum(1 for r in results if r.is_match)
        by_method = {}
        
        for r in results:
            method = r.match_method
            by_method[method] = by_method.get(method, 0) + 1
        
        confidences = [r.confidence for r in results if r.is_match]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        return {
            'total': total,
            'matched': matched,
            'unmatched': total - matched,
            'match_rate': matched / total,
            'by_method': by_method,
            'avg_confidence': avg_confidence,
        }
