"""ProgArchives data importer with deduplication and database integration."""
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set
from sqlalchemy.orm import Session
from datetime import datetime
from ...database.models import Album, Artist, Review, Tag, Track # Added Track
from ..scrapers.progarchives_scraper import ProgArchivesScraper
from ..parsers.progarchives_parser import ProgArchivesParser

logger = logging.getLogger(__name__)

class ProgArchivesImporter:
    """Import ProgArchives data with deduplication and database integration."""
    
    def __init__(self, session: Session):  # Removed local_data_root and cache_dir
        """Initialize importer with database session."""
        self.session = session
        self.scraper = ProgArchivesScraper()  # Initialize without arguments
        self.parser = ProgArchivesParser() # Initialize ProgArchivesParser without arguments
        self._seen_albums: Set[str] = set()  # Track processed albums
        
    def import_album(self, url: str, use_cache: bool = True) -> Optional[Album]:
        """Import a single album, including artist and all related data."""
        if url in self._seen_albums:
            logger.debug(f"Skipping already processed album: {url}")
            return None
            
        try:
            # Get album data
            album_data = self.scraper.get_album_details(url)
            if 'error' in album_data:
                logger.error(f"Error getting album data: {album_data['error']}")
                return None
                
            # Check if album already exists
            existing = self._find_existing_album(album_data)
            if existing:
                logger.info(f"Found existing album: {existing.title}")
                self._update_album(existing, album_data)
                return existing
                
            # Create new album
            album = self._create_album(album_data)
            if album:
                self._seen_albums.add(url)
                
            return album
            
        except Exception as e:
            logger.error(f"Error importing album {url}: {e}")
            return None
            
    def import_band(self, url: str, use_cache: bool = True) -> Optional[Artist]:
        """Import a band and all their albums."""
        try:
            # Get band data
            band_data = self.scraper.get_band_details(url)
            if 'error' in band_data:
                logger.error(f"Error getting band data: {band_data['error']}")
                return None
                
            # Check if artist exists
            existing = self._find_existing_artist(band_data)
            if existing:
                logger.info(f"Found existing artist: {existing.name}")
                self._update_artist(existing, band_data)
                return existing
                
            # Create new artist
            artist = self._create_artist(band_data)
            if not artist:
                return None
                
            # Import all albums
            for album_data in band_data.get('albums', []):
                if 'url' in album_data:
                    try:
                        album = self.import_album(album_data['url'], use_cache)
                        if album and album not in artist.albums:
                            artist.albums.append(album)
                    except Exception as e:
                        logger.error(f"Error importing album {album_data.get('title', 'unknown')}: {e}")
                        
            self.session.commit()
            return artist
            
        except Exception as e:
            logger.error(f"Error importing band {url}: {e}")
            return None
            
    def _find_existing_album(self, album_data: Dict) -> Optional[Album]:
        """Find existing album in database."""
        if not album_data.get('title') or not album_data.get('artist'):
            return None
            
        return (
            self.session.query(Album)
            .filter(Album.title == album_data['title'])
            .filter(Album.artist_name == album_data['artist'])
            .first()
        )
        
    def _find_existing_artist(self, artist_data: Dict) -> Optional[Artist]:
        """Find existing artist in database."""
        if not artist_data.get('name'):
            return None
            
        return (
            self.session.query(Artist)
            .filter(Artist.name == artist_data['name'])
            .first()
        )
        
    def _create_album(self, data: Dict) -> Optional[Album]:
        """Create new album record with all related data."""
        try:
            album = Album(
                title=data['title'],
                artist_name=data['artist'],
                year=data.get('year'),
                description=data.get('description', ''),
                url=data.get('url'),
                record_type=data.get('record_type'),
                rating=data.get('rating'),
                progarchives_id=self._extract_id(data.get('url', ''))
            )
            
            # Add tracks
            for track_data in data.get('tracks', []):
                track = Track(
                    title=track_data['title'],
                    length=track_data.get('length'),
                    track_number=track_data.get('track_number')
                )
                album.tracks.append(track)

            # Add reviews
            for review_data in data.get('reviews', []):
                review = Review(
                    text=review_data['text'],
                    rating=review_data.get('rating'),
                    author=review_data.get('author'),
                    date=self._parse_date(review_data.get('date')),
                    source='progarchives'
                )
                album.reviews.append(review)
                
            # Add tags
            self._add_tags(album, data)
            
            self.session.add(album)
            self.session.commit()
            return album
            
        except Exception as e:
            logger.error(f"Error creating album: {e}")
            self.session.rollback()
            return None
            
    def _create_artist(self, data: Dict) -> Optional[Artist]:
        """Create new artist record."""
        try:
            artist = Artist(
                name=data['name'],
                country=data.get('country'),
                description=data.get('description', ''),
                url=data.get('url'),
                progarchives_id=self._extract_id(data.get('url', ''))
            )
            
            self.session.add(artist)
            self.session.commit()
            return artist
            
        except Exception as e:
            logger.error(f"Error creating artist: {e}")
            self.session.rollback()
            return None
            
    def _update_album(self, album: Album, data: Dict) -> None:
        """Update existing album with new data."""
        try:
            # Update basic info if newer
            if data.get('scraped_at'):
                scraped_at = datetime.fromisoformat(data['scraped_at'])
                if not album.last_updated or scraped_at > album.last_updated:
                    album.description = data.get('description', album.description)
                    album.rating = data.get('rating', album.rating)
                    album.last_updated = scraped_at
            
            # Add new reviews
            existing_reviews = {r.text for r in album.reviews}
            for review_data in data.get('reviews', []):
                if review_data['text'] not in existing_reviews:
                    review = Review(
                        text=review_data['text'],
                        rating=review_data.get('rating'),
                        author=review_data.get('author'),
                        date=self._parse_date(review_data.get('date')),
                        source='progarchives'
                    )
                    album.reviews.append(review)
            
            # Update tags
            self._add_tags(album, data)
            
            self.session.commit()

        except Exception as e:
            logger.error(f"Error updating album {album.title}: {e}")
            self.session.rollback()
            
    def _update_artist(self, artist: Artist, data: Dict) -> None:
        """Update existing artist with new data."""
        try:
            # Update basic info if newer
            if data.get('scraped_at'):
                scraped_at = datetime.fromisoformat(data['scraped_at'])
                if not artist.last_updated or scraped_at > artist.last_updated:
                    artist.description = data.get('description', artist.description)
                    artist.country = data.get('country', artist.country)
                    artist.last_updated = scraped_at
            
            self.session.commit()
            
        except Exception as e:
            logger.error(f"Error updating artist {artist.name}: {e}")
            self.session.rollback()
            
    def _add_tags(self, album: Album, data: Dict) -> None:
        """Add genre tags from ProgArchives data."""
        if 'subgenre' in data:
            tag_name = f"progarchives:{data['subgenre'].lower()}"
            tag = (
                self.session.query(Tag)
                .filter(Tag.name == tag_name)
                .first()
            )
            if not tag:
                tag = Tag(
                    name=tag_name,
                    category='genre',
                    source='progarchives'
                )
                self.session.add(tag)
            
            if tag not in album.tags:
                album.tags.append(tag)
                
    def _extract_id(self, url: str) -> Optional[int]:
        """Extract ProgArchives ID from URL."""
        try:
            return int(url.split('id=')[1])
        except (IndexError, ValueError):
            return None
            
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string from ProgArchives."""
        if not date_str:
            return None
            
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            try:
                return datetime.strptime(date_str, '%d/%m/%Y')
            except ValueError:
                return None