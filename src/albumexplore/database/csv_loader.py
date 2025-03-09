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
                    Album.title == title
                ).first()
                
                if existing:
                    db_logger.debug(f"Album already exists: {artist} - {title}")
                    continue
                
                # Create new album
                album = Album(
                    artist=artist,
                    title=title,
                    release_year=year,
                    genre=row.get('Genre', '').strip(),
                    country=row.get('Country', '').strip()
                )
                
                # Process tags
                tags_str = row.get('Tags', '').strip()
                if tags_str:
                    tags = [t.strip() for t in tags_str.split(',') if t.strip()]
                    for tag_name in tags:
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