import uuid
import logging
from typing import Dict, Any, List, Optional, Set
from sqlalchemy.orm import Session
from sqlalchemy import func
from tqdm import tqdm

from albumexplore.database import models
from albumexplore.scraping.metalarchives.loader import MetalArchivesLoader

logger = logging.getLogger(__name__)

class MetalArchivesImporter:
    """
    Imports data from MetalArchives dump into the main database.
    Handles data normalization, provenance tracking, and deduplication.
    """
    
    SOURCE_NAME = 'metalarchives'

    def __init__(self, session: Session, data_dir: str = "data/MetalArchives"):
        self.session = session
        self.loader = MetalArchivesLoader(data_dir=data_dir)
        self.stats = {
            "artists_processed": 0,
            "artists_created": 0,
            "artists_skipped": 0,
            "albums_processed": 0,
            "albums_created": 0,
            "albums_skipped": 0,
        }
        
    def _get_or_create_artist(self, band_id: str, band_data: Dict[str, Any]) -> models.Artist:
        """
        Gets existing Artist (linked via ArtistSource) or creates a new one.
        Handles name collision by checking existing 'Artist' sources.
        """
        # 1. Check if we already imported this MetalArchives ID
        existing_source = self.session.query(models.ArtistSource).filter_by(
            source_name=self.SOURCE_NAME,
            source_id=band_id
        ).first()

        if existing_source:
            self.stats["artists_skipped"] += 1
            return existing_source.artist

        # 2. Prepare new artist data
        raw_name = band_data.get('name') or f"Unknown Band {band_id}"
        country = band_data.get('country')
        
        # 3. Check for name collision in the main Artist table
        # If name exists but isn't linked to this MA ID (per step 1), it's a conflict
        collision = self.session.query(models.Artist).filter(
            func.lower(models.Artist.name) == raw_name.lower()
        ).first()
        
        final_name = raw_name
        if collision:
            # Simple collision resolution for now: append ID
            # Ideally we might check if they ARE the same band via other metadata, 
            # but without robust matching, we assume different identities to be safe.
            final_name = f"{raw_name} (MA-{band_id})"
            
        # 4. Create Artist
        new_artist = models.Artist(
            id=str(uuid.uuid4()),
            name=final_name,
            country=country,
            # formation_year could be parsed from Status if available or other files, but distinct here
        )
        self.session.add(new_artist)
        
        # 5. Create Source
        new_source = models.ArtistSource(
            artist=new_artist,
            source_name=self.SOURCE_NAME,
            source_id=band_id,
            confidence=1.0 # Source of truth for this specific entry
        )
        self.session.add(new_source)
        
        self.stats["artists_created"] += 1
        return new_artist

    def import_batch(self, limit: Optional[int] = None, dry_run: bool = False):
        """
        Runs the import process.
        """
        # Load all data into memory (loader handles CSV parsing)
        logger.info("Loading MetalArchives data into memory...")
        bands_map = self.loader.load_bands()
        discography = self.loader.load_discography(limit=limit)
        
        if not discography:
            logger.warning("No discography data found to import.")
            return

        logger.info(f"Starting import of {len(discography)} albums...")
        
        # Cache for artist objects in this session to avoid DB lookups
        # Key: band_id -> Artist object
        artist_cache: Dict[str, models.Artist] = {}

        for album_data in tqdm(discography, desc="Importing Albums"):
            band_id = album_data['band_id']
            
            # --- Handle Artist ---
            if band_id not in artist_cache:
                band_info = bands_map.get(band_id, {'name': album_data.get('artist_name')})
                if not band_info.get('name'):
                    # Skip if we genuinely can't name the band
                    continue
                    
                artist_obj = self._get_or_create_artist(band_id, band_info)
                artist_cache[band_id] = artist_obj
                self.stats["artists_processed"] += 1
            
            artist_obj = artist_cache[band_id]
            
            # --- Handle Album ---
            # Composite identity for MA album: band_id + title + year + type
            # (Since there is no Album ID in the CSV export we have)
            
            title = album_data['title']
            year = album_data['year']
            atype = album_data['type']
            
            # Check for existing AlbumSource for this album
            # Since we don't have MA Album ID, we construct a pseudo-ID or match properties
            # We'll use "MA-{band_id}-{slug_title}" or just check db existence
            
            # Check if this artist already has this album (by title)
            # This is a 'soft' match to avoid duplicates if re-imported
            existing_album = None
            if artist_obj.albums:
                for alb in artist_obj.albums:
                    if alb.title.lower() == title.lower() and alb.release_year == year:
                        existing_album = alb
                        break
            
            if existing_album:
                # Could update fields (reviews, ratings) here if needed
                # For now, skip
                self.stats["albums_skipped"] += 1
                continue
            
            # Create Album
            new_album = models.Album(
                id=str(uuid.uuid4()),
                title=title,
                artist_obj=artist_obj,
                release_year=year,
                type=atype,
                # Store extra MA metadata
                pa_rating_count=album_data.get('review_count'), # Reuse PA field or migrate to generic?
                                                                # Schema has 'pa_rating_count', let's use it for now 
                                                                # or assume we need generic rating fields later.
                genre=album_data.get('artist_genre'), # Store raw genre string
                last_updated=func.now()
            )
            
            # We map specific MetalArchives review stats to available fields
            # Currently 'pa_rating_count' implies ProgArchives. 
            # Ideally we add 'ma_rating_count', or just use a generic one if we refactor.
            # For now, I will NOT overload PA fields to avoid confusion.
            # I will leave them null or add them if schema permits.
            
            self.session.add(new_album)
            
            # Add Source
            # Identity: we lack a unique source ID for the album itself from this CSV.
            # We construct one: "ma-album-{band_id}-{safe_title}-{year}"
            safe_title = "".join(x for x in title if x.isalnum())
            pseudo_id = f"ma-album-{band_id}-{safe_title}-{year}"
            
            src = models.AlbumSource(
                album=new_album,
                source_name=self.SOURCE_NAME,
                source_id=pseudo_id,
                confidence=1.0
            )
            self.session.add(src)
            
            self.stats["albums_created"] += 1
            self.stats["albums_processed"] += 1
            
            # Commit every X items to prevent massive memory usage
            if not dry_run and self.stats["albums_processed"] % 1000 == 0:
                self.session.commit()
                
        if dry_run:
            self.session.rollback()
            logger.info("Dry run complete - Rolled back changes.")
        else:
            self.session.commit()
            logger.info("Import complete - Committed changes.")
            
        logger.info(f"Stats: {self.stats}")
