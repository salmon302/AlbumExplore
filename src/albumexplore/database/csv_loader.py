"""CSV data loading module for database initialization."""
import logging
import pandas as pd
from pathlib import Path
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from ..data.parsers.csv_parser import CSVParser
from . import models, get_session

logger = logging.getLogger("albumexplore.database")

def parse_date(date_str: str) -> datetime:
    """Convert date string to datetime object."""
    try:
        if pd.isna(date_str):
            return None
        # Handle different date formats
        if isinstance(date_str, str):
            # Try full date format first
            try:
                return datetime.strptime(date_str.strip(), '%Y-%m-%d')
            except ValueError:
                pass
            # Try just month and year
            try:
                dt = datetime.strptime(date_str.strip(), '%B %Y')
                return dt.replace(day=1)
            except ValueError:
                pass
            # Try just year
            try:
                return datetime.strptime(date_str.strip(), '%Y')
            except ValueError:
                pass
        # If nothing else works, try pandas parsing
        return pd.to_datetime(date_str).to_pydatetime()
    except (ValueError, TypeError) as e:
        logger.warning(f"Could not parse date '{date_str}': {str(e)}")
        return None

def load_csv_data(csv_dir: Path) -> bool:
    """Load CSV data into the database."""
    with get_session() as db:
        try:
            logger.info("Loading CSV data...")
            parser = CSVParser(csv_dir)
            df = parser.parse()
            
            if df.empty:
                logger.warning("No data parsed from CSV files")
                return False
            
            logger.info(f"Parsed {len(df)} rows from CSV files")
            
            # Get current counts for ID generation
            album_count = db.query(models.Album).count()
            tag_count = db.query(models.Tag).count()
            
            # Keep track of existing tags
            tag_map = {}  # name -> Tag object
            
            # Check if the genre category exists once before processing
            genre_category = db.query(models.TagCategory).filter_by(id='genre').first()
            if not genre_category:
                logger.debug("Creating 'genre' category as it doesn't exist")
                genre_category = models.TagCategory(
                    id='genre',
                    name='Genre',
                    description='Musical genres and subgenres'
                )
                db.add(genre_category)
                # Commit the genre category immediately to avoid integrity errors later
                db.flush()
            
            # Process in chunks to avoid memory issues
            chunk_size = 500
            for chunk_start in range(0, len(df), chunk_size):
                chunk_df = df.iloc[chunk_start:chunk_start + chunk_size]
                logger.debug(f"Processing chunk {chunk_start}-{chunk_start + len(chunk_df)}")
                
                for i, row in chunk_df.iterrows():
                    # Create album with unique ID
                    album = models.Album(
                        id=f"a{album_count + i}",
                        artist=str(row['Artist']).strip(),
                        title=str(row['Album']).strip(),
                        release_date=parse_date(row['Release Date']),
                        length=str(row['Length']).strip() if pd.notna(row['Length']) else None,
                        vocal_style=str(row['Vocal Style']).strip() if pd.notna(row['Vocal Style']) else None,
                        country=str(row['Country / State']).strip() if pd.notna(row['Country / State']) else None
                    )
                    
                    # Extract release year from date if possible
                    if album.release_date:
                        album.release_year = album.release_date.year
                    
                    # Handle genre tags
                    # Add debug logging
                    logger.debug(f"Processing tags for album: {album.artist} - {album.title}")
                    
                    # Check if 'tags' exists and is usable
                    if 'tags' in row and isinstance(row['tags'], list) and len(row['tags']) > 0:
                        logger.debug(f"Using pre-processed tags: {row['tags']}")
                        tags = row['tags']
                    elif 'Genre / Subgenres' in row and not pd.isna(row['Genre / Subgenres']).all():
                        # Fallback to genre string if tags not processed
                        genre_str = str(row['Genre / Subgenres'])
                        logger.debug(f"Parsing tags from genre string: {genre_str}")
                        tags = [g.strip() for g in genre_str.split(',')]
                    else:
                        logger.debug("No tags found, using 'untagged'")
                        tags = ['untagged']
                    
                    # Create or get existing tags
                    for tag_name in tags:
                        tag_name = tag_name.strip().lower()
                        if not tag_name:
                            continue
                            
                        if tag_name not in tag_map:
                            tag = db.query(models.Tag).filter_by(name=tag_name).first()
                            if not tag:
                                tag_count += 1
                                # Debug the issue
                                logger.debug(f"Creating tag with name: {tag_name}")
                                
                                tag = models.Tag(
                                    id=f"t{tag_count}",
                                    name=tag_name,
                                    category_id='genre'  # Set the foreign key, not the relationship
                                )
                                logger.debug(f"Created tag: {tag}")
                                db.add(tag)
                            tag_map[tag_name] = tag
                        album.tags.append(tag_map[tag_name])
                    
                    db.add(album)
                
                try:
                    db.commit()
                    logger.info(f"Committed chunk of {len(chunk_df)} albums")
                except IntegrityError as e:
                    db.rollback()
                    logger.error(f"Integrity error in chunk: {str(e)}")
                    raise
                except Exception as e:
                    db.rollback()
                    logger.error(f"Error committing chunk: {str(e)}")
                    raise
            
            logger.info(f"Successfully loaded {len(df)} albums")
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error loading CSV data: {str(e)}")
            raise