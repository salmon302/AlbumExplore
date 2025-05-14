"""CSV data loader for album database."""
import csv
import os
from pathlib import Path
from typing import Dict, Set, List
from datetime import datetime
import re
from sqlalchemy.orm import Session
from albumexplore.database import get_session
from albumexplore.database.models import Album, Tag, TagCategory
from albumexplore.gui.gui_logging import db_logger

def extract_year(filename: str) -> int:
    """Extract year from filename."""
    match = re.search(r'20\d{2}', filename)
    return int(match.group()) if match else None

def normalize_tag(tag: str) -> str:
    """Normalize tag string."""
    return tag.strip().lower()

def load_csv_data(csv_dir: Path) -> None:
    """Load data from CSV files into database."""
    db_logger.info(f"Loading CSV data from {csv_dir}")
    
    session = get_session()
    try:
        # Process each CSV file
        for csv_file in csv_dir.glob('*.csv'):
            try:
                year = extract_year(csv_file.name)
                if year:
                    db_logger.info(f"Processing {csv_file.name} for year {year}")
                    _process_csv_file(csv_file, year, session)
            except Exception as e:
                db_logger.error(f"Error processing {csv_file}: {str(e)}", exc_info=True)
        
        session.commit()
        db_logger.info("CSV data loaded successfully")
        
    except Exception as e:
        session.rollback()
        db_logger.error(f"Error loading CSV data: {str(e)}", exc_info=True)
        raise
    finally:
        session.close()

def _process_csv_file(csv_file: Path, year: int, session: Session) -> None:
    """Process a single CSV file."""
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            try:
                # Extract album data
                artist = row.get('Artist', '').strip()
                title = row.get('Album', '').strip()
                
                if not artist or not title:
                    continue
                
                # Check if album already exists
                existing = session.query(Album).filter(
                    Album.artist == artist,
                    Album.title == title,
                    Album.release_year == year # Also check year to differentiate re-releases if any
                ).first()
                
                if existing:
                    db_logger.debug(f"Album already exists: {artist} - {title} ({year})")
                    # Optionally, update existing record if new data is more complete
                    # For now, we skip if it exists with the same year.
                    continue
                
                # Attempt to parse the full release date
                release_date_str = row.get('Release Date', '').strip()
                parsed_release_date = None
                if release_date_str:
                    try:
                        # Handle potential "TBD" or other non-date strings
                        if release_date_str.upper() == "TBD":
                            db_logger.debug(f"Release date is TBD for {artist} - {title}")
                        else:
                            # Try to parse formats like "Month Day" e.g. "April 29"
                            # Add the year from the filename to complete the date
                            full_date_str = f"{release_date_str} {year}"
                            parsed_release_date = datetime.strptime(full_date_str, "%B %d %Y").date()
                    except ValueError:
                        db_logger.warning(f"Could not parse date: '{release_date_str}' for {artist} - {title} in year {year}. Row: {row}")
                
                # Create new album
                album = Album(
                    artist=artist,
                    title=title,
                    release_year=year, # Year from filename
                    release_date=parsed_release_date, # Parsed full date (Month, Day, Year)
                    genre=row.get('Genre', '').strip(), # Assuming 'Genre' might be the primary genre string
                    # country=row.get('Country', '').strip() # 'Country' seems to be missing from provided CSV snippets, ensure it exists or handle
                    country=row.get('Country of Origin', row.get('Country', '')).strip(), # Check for 'Country of Origin' or 'Country'
                    # Ensure other fields from your Album model are populated if available in CSV
                    # e.g., length, vocal_style, raw_tags, platforms
                    raw_tags=row.get('Tags', '').strip() # Assuming 'Tags' column from CSV maps to raw_tags
                )
                
                # Process tags (from 'Genre / Subgenres' or a dedicated 'Tags' column if different)
                # The existing code uses 'Tags' for tag processing. Let's assume 'Genre / Subgenres' is for the main genre field
                # and 'Tags' column (if it exists and is different) or 'Genre / Subgenres' can be used for the tag list.
                # For clarity, let's assume the 'Tags' column in the CSV is what should be split into multiple tags.
                # If 'Tags' is not present, but 'Genre / Subgenres' is, and it's meant to be split, adjust accordingly.
                
                tags_source_column = 'Tags' # Default to 'Tags' column for individual tags
                if tags_source_column not in row and 'Genre / Subgenres' in row:
                    tags_source_column = 'Genre / Subgenres' # Fallback if 'Tags' isn't there but 'Genre / Subgenres' is

                tags_str_from_csv = row.get(tags_source_column, '').strip()
                if tags_str_from_csv:
                    # Split by comma, semicolon, or other common delimiters if necessary
                    # The original code splits by comma. If other delimiters are used, expand this.
                    individual_tags = [t.strip() for t in re.split(r'[,;/]', tags_str_from_csv) if t.strip()]
                    for tag_name in individual_tags:
                        # Get or create tag
                        tag = session.query(Tag).filter(
                            Tag.name == tag_name
                        ).first()
                        
                        if not tag:
                            tag = Tag(
                                name=tag_name,
                                normalized_name=normalize_tag(tag_name)
                            )
                            session.add(tag)
                        
                        album.tags.append(tag)
                
                session.add(album)
                db_logger.debug(f"Added album: {artist} - {title}")
                
            except Exception as e:
                db_logger.error(f"Error processing row: {row}", exc_info=True)
                raise

def get_tag_statistics() -> Dict:
    """Get statistics about tags in the database."""
    session = get_session()
    try:
        total_tags = session.query(Tag).count()
        total_albums = session.query(Album).count()
        
        # Get top tags
        top_tags = session.query(Tag).order_by(Tag.frequency.desc()).limit(10).all()
        
        return {
            'total_tags': total_tags,
            'total_albums': total_albums,
            'top_tags': [(tag.name, tag.frequency) for tag in top_tags]
        }
    finally:
        session.close()