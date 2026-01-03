"""
Transform Last.fm raw data to database format.

Processes raw JSON from the fetcher and enriches existing albums
or creates new entries.
"""
import json
import logging
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

import sys
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from albumexplore.database.models import (
    Base, Album, Artist, Tag, TagCategory, album_tags
)
from albumexplore.tags.normalizer.enhanced_normalizer import EnhancedTagNormalizer

logger = logging.getLogger(__name__)


def generate_id(prefix: str = "") -> str:
    """Generate a unique ID for database entities."""
    return f"{prefix}{str(uuid4())}"


def calculate_file_hash(file_path: Path) -> str:
    """Calculate MD5 hash of a file."""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except FileNotFoundError:
        return ""


class LastFmTransformer:
    """
    Transform Last.fm JSON data to database records.
    
    This transformer:
    1. Loads raw JSON files from raw_data/lastfm/
    2. Matches albums to existing database records
    3. Enriches with Last.fm specific data (playcount, listeners, tags)
    4. Creates new albums if no match found (optional)
    
    Usage:
        transformer = LastFmTransformer(db_uri="sqlite:///albumexplore.db")
        transformer.transform_all()
    """
    
    TAG_CATEGORY_NAME = "Last.fm User Tags"
    TAG_CATEGORY_DESC = "Tags from Last.fm user tagging"
    
    def __init__(
        self,
        db_uri: str = "sqlite:///albumexplore.db",
        raw_data_dir: str = "./raw_data/lastfm",
        create_new_albums: bool = False,
        min_tag_count: int = 10,
    ):
        """
        Initialize the transformer.
        
        Args:
            db_uri: SQLAlchemy database URI
            raw_data_dir: Directory containing raw Last.fm JSON
            create_new_albums: Whether to create albums not in DB
            min_tag_count: Minimum tag count to include
        """
        self.db_uri = db_uri
        self.raw_data_dir = Path(raw_data_dir)
        self.create_new_albums = create_new_albums
        self.min_tag_count = min_tag_count
        
        self.normalizer = EnhancedTagNormalizer()
        
        # Stats tracking
        self.stats = {
            "albums_enriched": 0,
            "albums_created": 0,
            "albums_not_matched": 0,
            "tags_added": 0,
            "errors": 0,
        }
    
    def _get_session(self) -> Session:
        """Create a database session."""
        engine = create_engine(self.db_uri)
        Base.metadata.create_all(engine)
        SessionClass = sessionmaker(bind=engine)
        return SessionClass()
    
    def _get_or_create_tag_category(self, session: Session) -> TagCategory:
        """Get or create the Last.fm tag category."""
        category = session.query(TagCategory).filter_by(
            name=self.TAG_CATEGORY_NAME
        ).first()
        
        if not category:
            category = TagCategory(
                id=generate_id("cat_"),
                name=self.TAG_CATEGORY_NAME,
                description=self.TAG_CATEGORY_DESC,
            )
            session.add(category)
            session.flush()
            logger.info(f"Created tag category: {self.TAG_CATEGORY_NAME}")
        
        return category
    
    def _find_matching_album(
        self,
        session: Session,
        artist_name: str,
        album_name: str,
        mbid: Optional[str] = None,
    ) -> Optional[Album]:
        """
        Find a matching album in the database.
        
        Matching priority:
        1. MBID exact match (if available)
        2. Artist name + album title (case-insensitive)
        """
        # Try MBID match first
        if mbid:
            album = session.query(Album).filter(Album.mbid == mbid).first()
            if album:
                return album
        
        # Try artist + title match
        # Note: This is a simple match; the matcher.py provides fuzzy matching
        artist_lower = artist_name.lower().strip()
        album_lower = album_name.lower().strip()
        
        # Check pa_artist_name_on_album field
        albums = session.query(Album).filter(
            Album.title.ilike(album_lower)
        ).all()
        
        for album in albums:
            if album.pa_artist_name_on_album:
                if album.pa_artist_name_on_album.lower().strip() == artist_lower:
                    return album
            # Also check via artist relationship
            if album.artist_obj and album.artist_obj.name.lower().strip() == artist_lower:
                return album
        
        return None
    
    def _process_tags(
        self,
        session: Session,
        tag_category: TagCategory,
        raw_tags: List[Dict[str, Any]],
    ) -> List[Tag]:
        """
        Process raw Last.fm tags into Tag objects.
        
        Args:
            session: Database session
            tag_category: Category for Last.fm tags
            raw_tags: List of tag dicts from Last.fm
            
        Returns:
            List of Tag objects
        """
        tags = []
        
        for tag_data in raw_tags:
            tag_name = tag_data.get('name', '').strip()
            tag_count = int(tag_data.get('count', 0))
            
            if not tag_name or tag_count < self.min_tag_count:
                continue
            
            # Normalize the tag name
            normalized_name = self.normalizer.normalize_enhanced(tag_name)
            if not normalized_name:
                continue
            
            # Find or create tag
            existing_tag = session.query(Tag).filter(
                Tag.name.ilike(normalized_name)
            ).first()
            
            if existing_tag:
                tags.append(existing_tag)
            else:
                new_tag = Tag(
                    id=generate_id("tag_"),
                    name=normalized_name,
                    normalized_name=normalized_name.lower(),
                    category_id=tag_category.id,
                    frequency=tag_count,
                )
                session.add(new_tag)
                tags.append(new_tag)
                self.stats["tags_added"] += 1
        
        return tags
    
    def _extract_playcount(self, data: Dict[str, Any]) -> Optional[int]:
        """Extract playcount from album data."""
        playcount = data.get('playcount')
        if playcount:
            try:
                return int(playcount)
            except (ValueError, TypeError):
                pass
        return None
    
    def _extract_listeners(self, data: Dict[str, Any]) -> Optional[int]:
        """Extract listener count from album data."""
        listeners = data.get('listeners')
        if listeners:
            try:
                return int(listeners)
            except (ValueError, TypeError):
                pass
        return None
    
    def _extract_mbid(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract MusicBrainz ID from album data."""
        mbid = data.get('mbid', '').strip()
        return mbid if mbid else None
    
    def _extract_image_url(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract best quality image URL."""
        images = data.get('image', [])
        if not images:
            return None
        
        # Prefer largest size
        for size in ['mega', 'extralarge', 'large', 'medium', 'small']:
            for img in images:
                if img.get('size') == size and img.get('#text'):
                    return img['#text']
        
        return None
    
    def transform_album_file(
        self,
        session: Session,
        file_path: Path,
        tag_category: TagCategory,
    ) -> bool:
        """
        Transform a single album JSON file.
        
        Args:
            session: Database session
            file_path: Path to JSON file
            tag_category: Category for new tags
            
        Returns:
            True if successful
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Could not read {file_path}: {e}")
            self.stats["errors"] += 1
            return False
        
        # Extract basic info
        artist_name = data.get('artist', '')
        if isinstance(artist_name, dict):
            artist_name = artist_name.get('name', '')
        album_name = data.get('name', '')
        mbid = self._extract_mbid(data)
        
        if not artist_name or not album_name:
            logger.warning(f"Missing artist or album name in {file_path}")
            return False
        
        # Find matching album
        album = self._find_matching_album(session, artist_name, album_name, mbid)
        
        if album:
            # Enrich existing album
            logger.debug(f"Enriching: {artist_name} - {album_name}")
            
            # Update Last.fm specific fields
            album.lastfm_playcount = self._extract_playcount(data)
            album.lastfm_listeners = self._extract_listeners(data)
            album.lastfm_url = data.get('url')
            
            if mbid and not album.mbid:
                album.mbid = mbid
            
            # Update cover if missing
            if not album.cover_image_url:
                album.cover_image_url = self._extract_image_url(data)
            
            # Process tags
            raw_tags = data.get('tags', {}).get('tag', [])
            if isinstance(raw_tags, dict):
                raw_tags = [raw_tags]
            
            # Also include separately fetched tags
            fetched_tags = data.get('_fetched_tags', [])
            all_tags = raw_tags + fetched_tags
            
            if all_tags:
                processed_tags = self._process_tags(session, tag_category, all_tags)
                for tag in processed_tags:
                    if tag not in album.tags:
                        album.tags.append(tag)
            
            self.stats["albums_enriched"] += 1
            return True
            
        elif self.create_new_albums:
            # Create new album
            logger.debug(f"Creating new album: {artist_name} - {album_name}")
            
            # Find or create artist
            artist = session.query(Artist).filter(
                Artist.name.ilike(artist_name)
            ).first()
            
            if not artist:
                artist = Artist(
                    id=generate_id("art_"),
                    name=artist_name,
                )
                session.add(artist)
                session.flush()
            
            # Create album
            new_album = Album(
                id=generate_id("alb_"),
                title=album_name,
                artist_id=artist.id,
                pa_artist_name_on_album=artist_name,
                mbid=mbid,
                lastfm_playcount=self._extract_playcount(data),
                lastfm_listeners=self._extract_listeners(data),
                lastfm_url=data.get('url'),
                cover_image_url=self._extract_image_url(data),
            )
            session.add(new_album)
            
            # Process tags
            raw_tags = data.get('tags', {}).get('tag', [])
            if isinstance(raw_tags, dict):
                raw_tags = [raw_tags]
            
            fetched_tags = data.get('_fetched_tags', [])
            all_tags = raw_tags + fetched_tags
            
            if all_tags:
                processed_tags = self._process_tags(session, tag_category, all_tags)
                for tag in processed_tags:
                    new_album.tags.append(tag)
            
            self.stats["albums_created"] += 1
            return True
            
        else:
            logger.debug(f"No match found for: {artist_name} - {album_name}")
            self.stats["albums_not_matched"] += 1
            return False
    
    def transform_all(
        self,
        dry_run: bool = False,
        date_filter: Optional[str] = None,
    ) -> Dict[str, int]:
        """
        Transform all raw Last.fm data.
        
        Args:
            dry_run: If True, don't commit changes
            date_filter: Only process files from this date (YYYYMMDD)
            
        Returns:
            Stats dictionary
        """
        logger.info(f"Starting Last.fm transformation from {self.raw_data_dir}")
        
        session = self._get_session()
        
        try:
            # Get or create tag category
            tag_category = self._get_or_create_tag_category(session)
            
            # Find all album JSON files
            search_dirs = []
            if date_filter:
                date_dir = self.raw_data_dir / date_filter
                if date_dir.exists():
                    search_dirs.append(date_dir)
            else:
                # Process all dated directories
                for subdir in self.raw_data_dir.iterdir():
                    if subdir.is_dir() and subdir.name.isdigit():
                        search_dirs.append(subdir)
            
            # Process files
            for search_dir in search_dirs:
                logger.info(f"Processing directory: {search_dir}")
                
                for json_file in search_dir.glob("album_*.json"):
                    self.transform_album_file(session, json_file, tag_category)
            
            # Commit or rollback
            if dry_run:
                logger.info("Dry run: rolling back changes")
                session.rollback()
            else:
                logger.info("Committing changes to database")
                session.commit()
            
            logger.info(f"Transformation complete: {self.stats}")
            return self.stats
            
        except Exception as e:
            logger.error(f"Transformation failed: {e}", exc_info=True)
            session.rollback()
            raise
        finally:
            session.close()


def transform_lastfm_data(
    raw_data_dir: str = "./raw_data/lastfm",
    db_uri: str = "sqlite:///albumexplore.db",
    dry_run: bool = False,
    create_new: bool = False,
    date_filter: Optional[str] = None,
) -> bool:
    """
    Main entry point for Last.fm transformation.
    
    Args:
        raw_data_dir: Directory with raw JSON files
        db_uri: Database URI
        dry_run: Don't commit changes
        create_new: Create albums not in DB
        date_filter: Only process specific date
        
    Returns:
        True if successful
    """
    transformer = LastFmTransformer(
        db_uri=db_uri,
        raw_data_dir=raw_data_dir,
        create_new_albums=create_new,
    )
    
    try:
        stats = transformer.transform_all(dry_run=dry_run, date_filter=date_filter)
        return stats["errors"] == 0
    except Exception as e:
        logger.error(f"Transform failed: {e}")
        return False


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Transform Last.fm data to database")
    parser.add_argument("--raw-data-dir", default="./raw_data/lastfm",
                        help="Directory containing raw JSON files")
    parser.add_argument("--db-uri", default="sqlite:///albumexplore.db",
                        help="Database URI")
    parser.add_argument("--dry-run", action="store_true",
                        help="Don't commit changes to database")
    parser.add_argument("--create-new", action="store_true",
                        help="Create albums not found in database")
    parser.add_argument("--date", default=None,
                        help="Only process files from this date (YYYYMMDD)")
    parser.add_argument("--log-level", default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                        help="Logging level")
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    success = transform_lastfm_data(
        raw_data_dir=args.raw_data_dir,
        db_uri=args.db_uri,
        dry_run=args.dry_run,
        create_new=args.create_new,
        date_filter=args.date,
    )
    
    return 0 if success else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
