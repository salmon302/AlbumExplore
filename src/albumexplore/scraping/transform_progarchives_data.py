"""
Data transformation module for Phase 3 of the ProgArchives data acquisition.

This module cleans and transforms raw CSV data extracted from ProgArchives into
a structured format ready for database loading.
"""

import logging
import json
import re
import pandas as pd
import numpy as np
from pathlib import Path
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from uuid import uuid4
import sys
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional

# Add parent directory to path to find albumexplore modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from albumexplore.database.models import (
    Base, Album, Artist, Track, Review, Tag, TagCategory,
    album_tags
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Helper functions for data cleaning
def clean_text(text: str) -> str:
    """
    Clean text from HTML tags and normalize whitespace.
    
    Args:
        text: Raw text string that might contain HTML or extra whitespace
        
    Returns:
        Cleaned text
    """
    if pd.isna(text) or text is None:
        return None
    
    # Remove HTML tags
    clean = re.sub(r'<[^>]+>', '', str(text))
    
    # Normalize whitespace
    clean = re.sub(r'\s+', ' ', clean).strip()
    
    # Convert special HTML entities
    clean = clean.replace('&amp;', '&')
    clean = clean.replace('&lt;', '<')
    clean = clean.replace('&gt;', '>')
    clean = clean.replace('&quot;', '"')
    clean = clean.replace('&apos;', "'")
    
    return clean

def convert_duration_to_seconds(duration_str: str) -> Optional[int]:
    """
    Convert duration string (e.g., "4:35") to seconds (275).
    
    Args:
        duration_str: Time duration in MM:SS format
        
    Returns:
        Total seconds as integer, or None if conversion fails
    """
    if pd.isna(duration_str) or not duration_str:
        return None
    
    try:
        duration_str = str(duration_str).strip()
        
        # Handle edge case of just seconds
        if ':' not in duration_str:
            try:
                return int(duration_str)
            except ValueError:
                return None
        
        parts = duration_str.split(':')
        
        # Handle MM:SS format
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        
        # Handle HH:MM:SS format
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        
        return None
    except (ValueError, IndexError):
        logger.warning(f"Failed to convert duration: {duration_str}")
        return None

def generate_id(prefix: str = "") -> str:
    """
    Generate a unique ID for database entities.
    
    Args:
        prefix: Optional prefix for the ID
        
    Returns:
        Unique string ID
    """
    return f"{prefix}{str(uuid4())}"

# Main transformation functions
def link_artists(session, raw_artists_df) -> Dict[str, Artist]:
    """
    Process raw artist data and create Artist entities.
    
    Args:
        session: SQLAlchemy session
        raw_artists_df: DataFrame with raw artist data
        
    Returns:
        Dictionary mapping artist name to Artist entity
    """
    logger.info("Processing artists...")
    artist_map = {}
    
    for _, row in raw_artists_df.iterrows():
        if pd.isna(row.get('raw_artist_name_canonical')):
            continue
            
        canonical_name = clean_text(row['raw_artist_name_canonical'])
        
        # Skip if we already processed this artist
        if canonical_name.lower() in artist_map:
            continue
            
        # Check if artist already exists in database
        artist = session.query(Artist).filter(Artist.name == canonical_name).first()
        
        if not artist:
            # Create new artist
            artist_id = generate_id("art_")
            artist = Artist(
                id=artist_id,
                name=canonical_name,
                # Add other fields as needed, like country
            )
            session.add(artist)
            logger.debug(f"Created artist: {canonical_name}")
        
        artist_map[canonical_name.lower()] = artist
    
    # Commit to get artist IDs
    session.commit()
    logger.info(f"Processed {len(artist_map)} artists")
    return artist_map

def process_recording_type(raw_type: str) -> str:
    """
    Standardize recording type from raw string.
    
    Args:
        raw_type: Raw recording type from ProgArchives
        
    Returns:
        Standardized recording type
    """
    if pd.isna(raw_type) or not raw_type:
        return "Unknown"
        
    raw_lower = raw_type.lower().strip()
    
    recording_type_map = {
        'studio album': 'Studio',
        'studio': 'Studio',
        'live album': 'Live',
        'live': 'Live',
        'compilation': 'Compilation',
        'comp': 'Compilation',
        'ep': 'EP',
        'single': 'Single',
        'demo': 'Demo',
        'soundtrack': 'Soundtrack',
        'box set': 'Box Set'
    }
    
    # Try exact match first
    if raw_lower in recording_type_map:
        return recording_type_map[raw_lower]
    
    # Try partial match
    for key, value in recording_type_map.items():
        if key in raw_lower:
            return value
    
    # Default fallback
    return "Other"

def process_lineups(raw_lineups_df) -> Dict[str, str]:
    """
    Transform raw lineup data into structured format.
    
    Args:
        raw_lineups_df: DataFrame with raw lineup data
        
    Returns:
        Dictionary mapping album ID to formatted lineup text
    """
    logger.info("Processing lineups...")
    album_lineups = {}
    
    for _, row in raw_lineups_df.iterrows():
        album_id = row['pa_album_id']
        
        if pd.isna(album_id) or album_id is None:
            continue
            
        musician = clean_text(row['raw_musician_name'])
        roles = clean_text(row['raw_instruments_roles'])
        
        if not musician or not roles:
            continue
        
        if album_id not in album_lineups:
            album_lineups[album_id] = []
            
        album_lineups[album_id].append({
            'musician': musician,
            'roles': roles
        })
    
    # Format as readable text
    formatted_lineups = {}
    for album_id, lineup in album_lineups.items():
        formatted = "\n".join([f"{m['musician']} - {m['roles']}" for m in lineup])
        formatted_lineups[album_id] = formatted
    
    logger.info(f"Processed lineups for {len(formatted_lineups)} albums")
    return formatted_lineups

def process_subgenres(session, raw_subgenre_df) -> Dict[str, Tag]:
    """
    Process ProgArchives subgenres into the tag system.
    
    Args:
        session: SQLAlchemy session
        raw_subgenre_df: DataFrame with raw subgenre data
        
    Returns:
        Dictionary mapping cleaned subgenre name to Tag entity
    """
    logger.info("Processing subgenres...")
    subgenre_tag_map = {}
    category_name = "Prog Archives Subgenre"
    description_text = "Subgenres as defined by ProgArchives.com"

    # Ensure DataFrame is not empty and required columns exist
    if raw_subgenre_df.empty or 'raw_subgenre_name' not in raw_subgenre_df.columns:
        logger.warning("Subgenre DataFrame is empty or missing 'raw_subgenre_name' column. Skipping subgenre processing.")
        return subgenre_tag_map

    # Get or create the TagCategory
    tag_category = session.query(TagCategory).filter_by(name=category_name).first()
    if not tag_category:
        logger.info(f"Creating TagCategory: {category_name}")
        tag_category_id = generate_id("cat_")
        tag_category = TagCategory(
            id=tag_category_id, 
            name=category_name,
            description=description_text # Add a description for clarity
        )
        session.add(tag_category)
        # We might need to flush to get the ID if not using deferred commits for this part
        # For now, assume commit happens later or ID is accessible.

    for _, row in raw_subgenre_df.iterrows():
        subgenre_name_raw = row.get('raw_subgenre_name')
        subgenre_definition_raw = row.get('raw_subgenre_definition')

        if pd.isna(subgenre_name_raw) or not str(subgenre_name_raw).strip():
            logger.debug("Skipping row with missing subgenre name.")
            continue
        
        subgenre_name = clean_text(str(subgenre_name_raw))
        subgenre_definition = clean_text(str(subgenre_definition_raw))

        if not subgenre_name:
            logger.debug("Skipping row with empty subgenre name after cleaning.")
            continue

        # Check if tag already exists (case-insensitive for the key, but store with original cleaned case for name)
        if subgenre_name.lower() in subgenre_tag_map:
            logger.debug(f"Subgenre '{subgenre_name}' already processed as a tag.")
            continue

        existing_tag = session.query(Tag).filter(
            Tag.name == subgenre_name,
            Tag.category_id == tag_category.id # Ensure it's in the same category if names can repeat across categories
        ).first()

        if existing_tag:
            tag = existing_tag
            # Optionally update definition if it's different and makes sense to do so
            if existing_tag.description != subgenre_definition and subgenre_definition:
                 logger.info(f"Updating description for existing tag '{subgenre_name}'.")
                 existing_tag.description = subgenre_definition
        else:
            tag_id = generate_id("tag_")
            tag = Tag(
                id=tag_id,
                name=subgenre_name,
                description=subgenre_definition,
                category_id=tag_category.id
                # category=tag_category # If relationship is set up for direct object assignment
            )
            session.add(tag)
            logger.debug(f"Created new tag: {subgenre_name} in category '{category_name}'.")
        
        subgenre_tag_map[subgenre_name.lower()] = tag

    # No commit here, will be handled by the main transformation function
    logger.info(f"Processed {len(subgenre_tag_map)} unique subgenres into tags.")
    return subgenre_tag_map

def parse_subgenres(subgenre_string: str) -> List[str]:
    """
    Parse a subgenre string into a list of subgenres.
    
    Args:
        subgenre_string: Raw subgenre string from ProgArchives
        
    Returns:
        List of clean subgenre names
    """
    if pd.isna(subgenre_string) or not subgenre_string:
        return []
        
    # Split on slash or comma
    subgenres = [s.strip() for s in re.split(r'[/,]', subgenre_string)]
    return [s for s in subgenres if s]  # Filter out empty strings

def transform_progarchives_data(raw_data_dir: str, db_uri: str, dry_run: bool = False) -> bool:
    """
    Main function to orchestrate the data transformation pipeline.

    Args:
        raw_data_dir: Path to the directory containing raw CSV files
        db_uri: SQLAlchemy database URI
        dry_run: If True, simulate processing without committing to DB

    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Starting data transformation. Raw data from: {raw_data_dir}")
    raw_data_path = Path(raw_data_dir)

    # Define paths to raw CSV files
    albums_raw_file = raw_data_path / "pa_raw_albums.csv"
    artists_raw_file = raw_data_path / "pa_raw_artists.csv"
    tracks_raw_file = raw_data_path / "pa_raw_tracks.csv"
    reviews_raw_file = raw_data_path / "pa_raw_reviews.csv"
    lineups_raw_file = raw_data_path / "pa_raw_lineups.csv"
    subgenres_raw_file = raw_data_path / "pa_raw_subgenre_definitions.csv"

    # Load raw data
    try:
        logger.info("Loading raw CSV files...")
        raw_albums_df = pd.read_csv(albums_raw_file, encoding='utf-8')
        raw_artists_df = pd.read_csv(artists_raw_file, encoding='utf-8')
        raw_tracks_df = pd.read_csv(tracks_raw_file, encoding='utf-8')
        raw_reviews_df = pd.read_csv(reviews_raw_file, encoding='utf-8')
        raw_lineups_df = pd.read_csv(lineups_raw_file, encoding='utf-8')
        raw_subgenres_df = pd.read_csv(subgenres_raw_file, encoding='utf-8')
        logger.info("All raw CSV files loaded successfully.")
    except FileNotFoundError as e:
        logger.error(f"Error loading raw data: {e}. Please ensure all raw CSV files are present.")
        return False
    except pd.errors.EmptyDataError as e:
        logger.error(f"Error loading raw data: {e}. One or more CSV files are empty.")
        return False
    
    # Drop rows with all NaN values, which can occur if files are empty or just headers
    raw_albums_df.dropna(how='all', inplace=True)
    raw_artists_df.dropna(how='all', inplace=True)
    raw_tracks_df.dropna(how='all', inplace=True)
    raw_reviews_df.dropna(how='all', inplace=True)
    raw_lineups_df.dropna(how='all', inplace=True)
    raw_subgenres_df.dropna(how='all', inplace=True)

    if raw_albums_df.empty:
        logger.warning("No album data found in pa_raw_albums.csv. Processing will be limited.")
        # Depending on requirements, you might want to return False here or handle gracefully.

    # Setup database session
    engine = create_engine(db_uri)
    Base.metadata.create_all(engine)  # Create tables if they don't exist
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Phase 1: Process Artists
        # The link_artists function should handle artist creation/retrieval
        # and return a map of raw artist identifiers (e.g., canonical name or URL) to Artist objects.
        artist_map = link_artists(session, raw_artists_df) # Placeholder for actual artist identifiers

        # Phase 2: Process Subgenres (as Tags)
        subgenre_tag_map = process_subgenres(session, raw_subgenres_df)

        # Phase 3: Process Lineups
        # This function should return a structure that can be easily used when creating albums,
        # e.g., a dict mapping album_pa_id to formatted lineup string or structured data.
        album_lineups_processed = process_lineups(raw_lineups_df) # Keyed by 'pa_album_id'

        # Phase 4: Process Albums, Tracks, and Reviews
        logger.info("Processing albums, tracks, and reviews...")
        
        album_id_map = {} # Maps pa_album_id to internal Album object ID

        for index, album_row in raw_albums_df.iterrows():
            # Ensure pa_album_id is not NaN
            pa_album_id = album_row.get('pa_album_id')
            if pd.isna(pa_album_id):
                logger.warning(f"Skipping album row {index} due to missing 'pa_album_id'.")
                continue

            # --- 1. Link to Artist ---
            # The artist_link_local can be used if your artist_map is keyed by local links.
            # Or, use a canonical artist name if that's how artist_map is structured.
            # This part needs to align with how `link_artists` and `raw_artists_df` are structured.
            
            # Assuming 'raw_artist_name' from album data needs to be mapped to an Artist object
            raw_artist_name_on_album = clean_text(album_row.get('raw_artist_name'))
            album_artist_obj = None
            if raw_artist_name_on_album and raw_artist_name_on_album.lower() in artist_map:
                album_artist_obj = artist_map[raw_artist_name_on_album.lower()]
            else:
                logger.warning(f"Artist '{raw_artist_name_on_album}' for album '{album_row.get('raw_album_title')}' not found in artist_map. Skipping artist linkage for this album.")
                # Decide if you want to create a new artist here or skip. For now, skipping.

            # --- 2. Create Album Entity ---
            album_id = generate_id("alb_")
            album_title = clean_text(album_row.get('raw_album_title'))
            
            release_year_str = str(album_row.get('raw_release_year', '')).strip()
            release_year = None
            if release_year_str and release_year_str != 'nan' and release_year_str != '0':
                try:
                    release_year = int(float(release_year_str)) # float conversion handles cases like '1995.0'
                except ValueError:
                    logger.warning(f"Could not convert release year '{release_year_str}' to int for album '{album_title}'.")


            album_type_raw = album_row.get('raw_album_type')
            album_type_processed = process_recording_type(album_type_raw) # Already exists

            # Basic album data
            album_data = {
                'id': album_id,
                'title': album_title,
                'release_year': release_year,
                'type': album_type_processed,
                'cover_image_url': clean_text(album_row.get('raw_cover_image_url_local')),
                'pa_album_id': pa_album_id, # Store the original ProgArchives ID
                'pa_artist_name_on_album': raw_artist_name_on_album, # Store for reference
                'pa_rating_value': pd.to_numeric(album_row.get('raw_rating_value'), errors='coerce'),
                'pa_rating_count': pd.to_numeric(album_row.get('raw_rating_count'), errors='coerce'),
                'pa_review_count': pd.to_numeric(album_row.get('raw_review_count'), errors='coerce'),
                'source_html_file': album_row.get('source_html_file')
            }
            
            if album_artist_obj:
                album_data['artist_id'] = album_artist_obj.id
                # If your model supports direct object assignment:
                # album_data['artist'] = album_artist_obj

            album = Album(**album_data)
            session.add(album)
            album_id_map[pa_album_id] = album.id # Map PA ID to new internal Album ID

            # --- 3. Link Subgenres (Tags) ---
            # Assuming 'raw_subgenre' in album_row contains the subgenre name(s)
            album_subgenre_name = clean_text(album_row.get('raw_subgenre'))
            if album_subgenre_name and album_subgenre_name.lower() in subgenre_tag_map:
                tag_to_link = subgenre_tag_map[album_subgenre_name.lower()]
                if tag_to_link not in album.tags: # Avoid duplicate associations
                    album.tags.append(tag_to_link)
            elif album_subgenre_name:
                 logger.warning(f"Subgenre '{album_subgenre_name}' for album '{album_title}' not found in subgenre_tag_map.")


            # --- 4. Add Lineup ---
            # The `process_lineups` function returns a dict keyed by `pa_album_id`.
            # The value could be a pre-formatted string or structured data.
            # Let's assume it's a string to be stored in `Album.lineup_description`.
            if pa_album_id in album_lineups_processed:
                album.lineup_text_raw = album_lineups_processed[pa_album_id]
            else:
                album.lineup_text_raw = None # Or empty string, depending on preference
        
        logger.info(f"Processed {len(album_id_map)} albums. Committing album objects to get IDs.")
        if not dry_run:
            session.commit() # Commit albums to get their IDs for tracks and reviews

        # --- 5. Process Tracks ---
        logger.info("Processing tracks...")
        tracks_to_add = []
        for _, track_row in raw_tracks_df.iterrows():
            track_pa_album_id = track_row.get('pa_album_id')
            if pd.isna(track_pa_album_id) or track_pa_album_id not in album_id_map:
                logger.warning(f"Skipping track for pa_album_id '{track_pa_album_id}' as album was not found or not processed.")
                continue

            album_internal_id = album_id_map[track_pa_album_id]
            
            track_title = clean_text(track_row.get('raw_track_title'))
            if not track_title:  # Skip tracks with no title
                logger.debug(f"Skipping track for pa_album_id '{track_pa_album_id}' due to missing title.")
                continue

            is_subtrack_val = track_row.get('is_subtrack')
            processed_is_subtrack = None
            if pd.notna(is_subtrack_val):
                processed_is_subtrack = bool(is_subtrack_val)
            # If is_subtrack_val is NaN or None, processed_is_subtrack remains None, which is fine for a nullable Boolean column.

            track_data = {
                'id': generate_id("trk_"),
                'album_id': album_internal_id,
                'title': track_title,
                'track_number_raw': str(track_row.get('raw_track_number', '')).strip(), # Keep as string for flexibility
                'duration_seconds': convert_duration_to_seconds(track_row.get('raw_track_duration')),
                'is_subtrack': processed_is_subtrack
            }
            tracks_to_add.append(Track(**track_data))

        if tracks_to_add:
            session.add_all(tracks_to_add)
        logger.info(f"Processed {len(tracks_to_add)} tracks.")

        # --- 6. Process Reviews ---
        logger.info("Processing reviews...")
        reviews_to_add = []
        for _, review_row in raw_reviews_df.iterrows():
            review_pa_album_id = review_row.get('pa_album_id')
            if pd.isna(review_pa_album_id) or review_pa_album_id not in album_id_map:
                logger.warning(f"Skipping review for pa_album_id '{review_pa_album_id}' as album was not found or not processed.")
                continue
            
            album_internal_id = album_id_map[review_pa_album_id]

            review_text = clean_text(review_row.get('raw_review_text'))
            if not review_text: # Skip reviews with no text
                 logger.debug(f"Skipping review for pa_album_id '{review_pa_album_id}' due to missing text.")
                 continue

            review_date_str = review_row.get('raw_review_date')
            review_date = None
            if pd.notna(review_date_str):
                try:
                    # Example format: "2004-02-12" or "January 1, 2022"
                    # Pandas to_datetime is quite flexible
                    review_date = pd.to_datetime(review_date_str, errors='coerce').date()
                    if pd.isna(review_date): # if conversion failed
                        logger.warning(f"Could not parse review date '{review_date_str}' for album {review_pa_album_id}.")
                        review_date = None
                except Exception as e:
                    logger.warning(f"Error parsing review date '{review_date_str}': {e}")
                    review_date = None
            
            rating_str = str(review_row.get('raw_review_rating', '')).strip()
            rating_value = None
            if rating_str and rating_str.lower() != 'nan':
                # Assuming rating is like "4/5 stars" or just "4"
                match = re.search(r'(\d+)(?:/\d+)?', rating_str)
                if match:
                    try:
                        rating_value = int(match.group(1))
                    except ValueError:
                        logger.warning(f"Could not parse rating from '{rating_str}' for review on album {review_pa_album_id}")
                elif rating_str.isdigit(): # if it's just a number
                     try:
                        rating_value = int(rating_str)
                     except ValueError:
                        logger.warning(f"Could not parse rating from '{rating_str}' for review on album {review_pa_album_id}")


            review_data = {
                'id': generate_id("rev_"),
                'album_id': album_internal_id,
                'reviewer_name': clean_text(review_row.get('raw_reviewer_name')),
                'review_date': review_date,
                'rating': rating_value,
                'review_text': review_text,
                'source_html_file': review_row.get('source_html_file'), # from raw_reviews.csv
                'pa_review_id': review_row.get('pa_review_id') # from raw_reviews.csv
            }
            reviews_to_add.append(Review(**review_data))

        if reviews_to_add:
            session.add_all(reviews_to_add)
        logger.info(f"Processed {len(reviews_to_add)} reviews.")

        # --- Final Commit ---
        if not dry_run:
            logger.info("Committing all changes to the database...")
            session.commit()
            logger.info("Database commit successful.")
        else:
            logger.info("Dry run: Rolling back changes.")
            session.rollback()
            logger.info("Dry run: Rollback successful.")

        logger.info("Data transformation completed successfully.")
        return True

    except Exception as e:
        logger.error(f"An error occurred during data transformation: {e}", exc_info=True)
        if session: # Check if session was initialized
            session.rollback()
        return False
    finally:
        if session: # Check if session was initialized
            session.close()
            logger.info("Database session closed.")

def main():
    """
    Main entry point when running as script.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Transform raw ProgArchives data to database")
    parser.add_argument("--raw-data-dir", default="./raw_data", help="Directory containing raw CSV files")
    parser.add_argument("--db-uri", default="sqlite:///albumexplore.db", help="Database URI")
    parser.add_argument("--dry-run", action="store_true", help="Run without committing changes to database")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"], 
                        help="Set logging level")
    
    args = parser.parse_args()
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    success = transform_progarchives_data(
        raw_data_dir=args.raw_data_dir,
        db_uri=args.db_uri,
        dry_run=args.dry_run
    )
    
    if success:
        logger.info("Transformation completed successfully")
        return 0
    else:
        logger.error("Transformation failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
