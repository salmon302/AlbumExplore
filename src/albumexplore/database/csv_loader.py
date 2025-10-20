"""CSV data loader for album database."""
import csv
import os
from pathlib import Path
from typing import Dict, Set, List, Optional
from datetime import datetime
import re
import uuid # Added import for uuid
import pandas as pd

from sqlalchemy.orm import Session

from albumexplore.database import get_session
from albumexplore.database.models import Album, Tag, TagCategory
from albumexplore.gui.gui_logging import db_logger
from albumexplore.tags.normalizer.tag_normalizer import TagNormalizer
from albumexplore.database.tag_validator import TagValidationFilter

# Initialize advanced tag normalizer and validator
_tag_normalizer = TagNormalizer()
_tag_validator = TagValidationFilter(strict_mode=False)  # Allow warnings but block errors

# Regex to identify "Month Day" strings (e.g., "Jan 1", "Feb 23", "March 3")
# Moved to module level for single compilation
DATE_PATTERN = re.compile(r"^(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?[.,]?|\d{4}-\d{2}-\d{2})$", re.IGNORECASE)

COMMON_FORMAT_STRINGS = ["lp", "ep", "single", "compilation", "live album", "demo", "mixtape", "album", "mini-album", "ost", "soundtrack", "cd", "vinyl", "digital", "cassette", 
                   "2xlp", "3xlp", "4xlp", "5xlp", "6xlp", "7xlp", "8xlp", "9xlp", "10xlp", "12xlp", "16xlp", "24xlp",
                   "2xcd", "3xcd", "4xcd", "5xcd", "6xcd", "7xcd", "8xcd", "10xcd", "12xcd",
                   # Additional format variations
                   "2lp", "3lp", "4lp", "5lp", "6lp", "double lp", "triple lp", "double cd", "triple cd",
                   "double album", "triple album", "split", "split ep", "split lp", "split album",
                   # Add simple digit prefixed formats without 'x'
                   "1lp", "1ep", "1cd", "1single", "2ep", "2single", "3ep", "4ep"]

POTENTIAL_DATE_TOKENS = [
    "tba", "tbd", "-", "q1", "q2", "q3", "q4", "early", "mid", "late", "spring", "summer", "fall", "autumn", "winter",
    "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec",
    "january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december",
    "2023", "2024", "2025", "2026", "2027", "2028", "2029", "2030"
]

# Vocal style extraction helpers
VOCAL_STYLE_PRIMARY_SPLIT_PATTERN = re.compile(r"[,/;]", re.IGNORECASE)
VOCAL_STYLE_SECONDARY_SPLIT_PATTERN = re.compile(r"\s+(?:&|\+|and|with)\s+", re.IGNORECASE)
VOCAL_STYLE_IGNORED_TOKENS = {"", "n/a", "na", "tbd", "?", "-", "unknown"}
VOCAL_STYLE_MAX_VALUE_LENGTH = 500
VOCAL_STYLE_MAX_TOKEN_LENGTH = 80

def _normalize_vocal_style_token(token: str) -> Optional[str]:
    """Convert a raw vocal style token into a normalized tag name."""
    if not token:
        return None

    cleaned = token.strip().lower()
    if not cleaned or cleaned in VOCAL_STYLE_IGNORED_TOKENS:
        return None

    # Remove parentheses content and punctuation that frequently appears in source data
    cleaned = re.sub(r"\(.*?\)", "", cleaned)
    cleaned = cleaned.replace("w/", "with").replace("%", "")
    cleaned = cleaned.replace("instr.", "instrumental").replace("instru.", "instrumental")
    cleaned = re.sub(r"[\.\!\?]$", "", cleaned).strip()

    if len(cleaned) > VOCAL_STYLE_MAX_TOKEN_LENGTH:
        return None

    # Canonical mappings
    if cleaned in {"instrumental", "instrumental only", "instrumental 100", "instrumental 100%", "instrumental (mostly)", "instr", "instru", "no vocals"}:
        return "instrumental"
    if cleaned in {"clean", "cleans", "clean vocals", "mostly clean", "all clean", "sung", "singing", "clean singing"}:
        return "clean vocals"
    if cleaned in {"harsh", "harsh vocals", "unclean", "extreme", "extreme vocals"}:
        return "harsh vocals"
    if cleaned in {"mixed", "both", "combo", "combined"}:
        return "mixed vocals"
    if cleaned in {"spoken", "spoken word", "narration", "narrated"}:
        return "spoken vocals"
    if cleaned in {"choir", "choral"}:
        return "choral vocals"
    if cleaned in {"operatic", "opera"}:
        return "operatic vocals"
    if cleaned in {"female", "female vocals"}:
        return "female vocals"
    if cleaned in {"male", "male vocals"}:
        return "male vocals"

    # Substring-based mappings (order matters to avoid misclassification)
    if "instrumental" in cleaned or cleaned.startswith("instr"):
        return "instrumental"
    if "clean" in cleaned:
        return "clean vocals"
    if any(keyword in cleaned for keyword in ["harsh", "growl", "growled", "growling", "scream", "screamed", "screaming", "death", "black", "unclean", "shout", "guttural", "raspy"]):
        return "harsh vocals"
    if "mixed" in cleaned or "both" in cleaned or "split" in cleaned:
        return "mixed vocals"
    if "spoken" in cleaned or "narr" in cleaned:
        return "spoken vocals"
    if "choir" in cleaned or "choral" in cleaned:
        return "choral vocals"
    if "operatic" in cleaned or "opera" in cleaned:
        return "operatic vocals"
    if cleaned in {"none", "n/a"}:
        return None

    # Default: keep descriptive token and ensure it ends with 'vocals' unless instrumental
    if cleaned == "instrumental":
        return "instrumental"

    if cleaned.endswith("vocals"):
        normalized = cleaned
    else:
        normalized = f"{cleaned} vocals"

    return normalized

def extract_vocal_style_tags(raw_value: str) -> List[str]:
    """Parse and normalize vocal style values into a list of tag names."""
    if not raw_value:
        return []

    if isinstance(raw_value, float) and pd.isna(raw_value):  # type: ignore[arg-type]
        return []

    value = str(raw_value).strip()
    if not value:
        return []

    if len(value) > VOCAL_STYLE_MAX_VALUE_LENGTH:
        db_logger.debug(
            "Skipping vocal style parsing for unusually long value (len=%s)",
            len(value)
        )
        return []

    primary_tokens = [tok.strip() for tok in VOCAL_STYLE_PRIMARY_SPLIT_PATTERN.split(value) if tok.strip()]
    tokens: List[str] = []

    for token in primary_tokens:
        if len(token) > VOCAL_STYLE_MAX_TOKEN_LENGTH:
            continue

        subtokens = [sub.strip() for sub in VOCAL_STYLE_SECONDARY_SPLIT_PATTERN.split(token) if sub.strip()]
        if subtokens:
            tokens.extend(subtokens)
        else:
            tokens.append(token)

    normalized_tags: List[str] = []

    for token in tokens:
        normalized = _normalize_vocal_style_token(token)
        if not normalized:
            continue

        # Vocal-style tokens are already canonical (e.g., "clean vocals", "instrumental")
        # so skip the expensive tag normalizer for these specific terms
        if normalized and normalized not in normalized_tags:
            normalized_tags.append(normalized)

    return normalized_tags

def build_raw_tags_string(primary_tags: str, additional_tags: List[str]) -> str:
    """Combine primary genre tags with additional tags (e.g., vocal styles)."""
    parts: List[str] = []
    primary = (primary_tags or "").strip()
    if primary:
        parts.append(primary)
    if additional_tags:
        parts.append(", ".join(additional_tags))
    return ", ".join(parts)

def extract_year(filename: str) -> int:
    """Extract year from filename."""
    match = re.search(r'20\d{2}', filename)
    return int(match.group()) if match else None

def normalize_tag(tag: str) -> str:
    """Normalize tag string using advanced normalization system."""
    if not tag:
        return tag
    return _tag_normalizer.normalize(tag)

def is_iso_date(val_str: str) -> bool:
    """Check if string is in ISO date format (YYYY-MM-DD)."""
    if not val_str:
        return False
    return bool(re.match(r'^\d{4}-\d{2}-\d{2}$', val_str))

def is_format_string(val_str: str) -> bool:
    """Check if string is a format descriptor like '2xLP', '3xCD', etc."""
    if not val_str:
        return False
    
    # Normalize the string for comparison
    normalized = val_str.lower().strip()
    
    # Check if the string is in our predefined list (case-insensitive)
    if normalized in COMMON_FORMAT_STRINGS:
        return True
    
    # Check for patterns like "2xLP", "3xCD", etc. that might not be in our list
    if re.match(r'^\d+x[a-zA-Z]{1,5}$', normalized):
        return True
    
    # Check for simple numeric prefix format like "2LP", "3CD"
    if re.match(r'^\d+[a-zA-Z]{1,5}$', normalized):
        return True
        
    # Check for simple formats without multipliers (LP, EP, etc.)
    if normalized in ['lp', 'ep', 'single']:
        return True
        
    return False

def load_dataframe_data(df, session: Session):
    """Load data from a pandas DataFrame into the database."""
    db_logger.info(f"Loading data from DataFrame into database. Rows: {len(df)}")
    load_start_time = datetime.now()

    try:
        # Get existing albums to avoid duplicates
        existing_albums = {
            (album.pa_artist_name_on_album, album.title)
            for album in session.query(Album.pa_artist_name_on_album, Album.title).all()
        }
        db_logger.info(f"Found {len(existing_albums)} existing albums in the database.")

        # Standardize DataFrame columns
        df.columns = [col.lower().strip() for col in df.columns]
        db_logger.info(f"DataFrame columns after standardization: {list(df.columns)}")
        
        required_cols = {'artist', 'album'}
        if not required_cols.issubset(df.columns):
            raise ValueError(f"DataFrame must contain 'artist' and 'album' columns. Found: {df.columns}")

        # Process each row in the DataFrame
        processed_count = 0
        for index, row in df.iterrows():
            artist = row.get('artist')
            album_title = row.get('album')

            # Check for missing or NaN values
            if (pd.isna(artist) or not artist or 
                pd.isna(album_title) or not album_title or
                str(artist).strip() == '' or str(album_title).strip() == ''):
                db_logger.warning(f"Skipping row {index}: missing artist ('{artist}') or album title ('{album_title}').")
                continue

            # Convert to strings and strip whitespace
            artist = str(artist).strip()
            album_title = str(album_title).strip()
            
            # Check for string representations of NaN
            if artist.lower() in ['nan', 'none', ''] or album_title.lower() in ['nan', 'none', '']:
                db_logger.warning(f"Skipping row {index}: invalid artist ('{artist}') or album title ('{album_title}').")
                continue

            # Check for duplicates
            if (artist, album_title) in existing_albums:
                db_logger.debug(f"Skipping duplicate album: {artist} - {album_title}")
                continue

            # Parse release date and extract year
            release_date_str = row.get('release date', '')
            # Handle NaN values in release date
            if pd.isna(release_date_str):
                release_date_str = ''
            release_date_obj = None
            release_year = None
            
            if release_date_str:
                # Try to parse the release date properly
                release_date_str = str(release_date_str).strip()
                
                # Try ISO date format first (YYYY-MM-DD)
                if is_iso_date(release_date_str):
                    try:
                        release_date_obj = datetime.strptime(release_date_str, '%Y-%m-%d')
                        release_year = release_date_obj.year
                        db_logger.debug(f"Parsed ISO date '{release_date_str}' for {artist} - {album_title}")
                    except ValueError:
                        db_logger.warning(f"Failed to parse ISO date '{release_date_str}' for {artist} - {album_title}")
                
                # Handle month abbreviations with day (e.g., "Jan 1", "Feb 23")
                elif re.match(r'^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}$', release_date_str, re.IGNORECASE):
                    # Extract year from source file if available
                    source_file = row.get('_source_file', '')
                    if source_file:
                        year_from_file = extract_year(source_file)
                        if year_from_file:
                            try:
                                date_with_year = f"{release_date_str} {year_from_file}"
                                release_date_obj = datetime.strptime(date_with_year, '%b %d %Y')
                                release_year = release_date_obj.year
                                db_logger.debug(f"Parsed month+day format '{release_date_str}' with year {year_from_file} for {artist} - {album_title}")
                            except ValueError:
                                db_logger.warning(f"Failed to parse month+day format '{release_date_str}' for {artist} - {album_title}")
                
                # Try to extract just the year from the string
                if not release_year:
                    year_match = re.search(r'20\d{2}', release_date_str)
                    if year_match:
                        release_year = int(year_match.group())
                        release_date_obj = datetime(release_year, 1, 1)  # Default to January 1st
                        db_logger.debug(f"Extracted year {release_year} from '{release_date_str}' for {artist} - {album_title}")
                
                # If still no year, try to get it from source file
                if not release_year:
                    source_file = row.get('_source_file', '')
                    if source_file:
                        year_from_file = extract_year(source_file)
                        if year_from_file:
                            release_year = year_from_file
                            release_date_obj = datetime(release_year, 1, 1)
                            db_logger.debug(f"Using year {release_year} from source file for {artist} - {album_title}")
            
            # If we still don't have a release year, set to None
            if not release_year:
                db_logger.warning(f"Could not determine release year for {artist} - {album_title}, release_date_str='{release_date_str}'")
            
            # Get genre and tags data
            genre_and_tags_str = row.get('genre / subgenres', '') or row.get('genre', '') or row.get('genres', '')
            vocal_style_str = row.get('vocal style', '') or row.get('vocal_style', '')
            country_str = row.get('country / state', '') or row.get('country', '')

            # Handle NaN values in genre, vocal style, and country fields
            if pd.isna(genre_and_tags_str):
                genre_and_tags_str = ''
            if pd.isna(vocal_style_str):
                vocal_style_str = ''
            if pd.isna(country_str):
                country_str = ''

            genre_and_tags_str = str(genre_and_tags_str).strip() if genre_and_tags_str else ''
            vocal_style_str = str(vocal_style_str).strip() if vocal_style_str else ''
            country_str = str(country_str).strip() if country_str else ''

            vocal_style_tags = extract_vocal_style_tags(vocal_style_str)
            vocal_style_display = ', '.join(vocal_style_tags) if vocal_style_tags else ''
            combined_raw_tags = build_raw_tags_string(genre_and_tags_str, vocal_style_tags)
            
            # Debug log for the first few rows to see what's happening with tags
            if processed_count < 5:  # Only log first 5 rows to avoid spam
                db_logger.info(f"Row {processed_count}: genre_and_tags_str='{genre_and_tags_str}', vocal_style_str='{vocal_style_str}', country_str='{country_str}'")

            # Create Album object
            album = Album(
                id=str(uuid.uuid4()),
                pa_artist_name_on_album=artist,
                title=album_title,
                release_date=release_date_obj,
                release_year=release_year,
                vocal_style=vocal_style_display or None,
                genre=genre_and_tags_str,
                country=country_str,
                raw_tags=combined_raw_tags,
                last_updated=datetime.now()
            )
            
            session.add(album)
            
            # Handle tags and genres - similar to CSV processing logic
            if genre_and_tags_str:
                # Split by commas and semicolons
                raw_tags = [tag.strip() for tag in re.split(r'[;,]', str(genre_and_tags_str)) if tag.strip()]
                if processed_count < 5:  # Debug log for first few rows
                    db_logger.info(f"Row {processed_count}: raw tags: {raw_tags}")
                
                # Validate tags first
                context = {
                    'artist': artist,
                    'album': album_title,
                    'source': 'dataframe_import'
                }
                valid_tags, rejected_tags, validation_info = _tag_validator.filter_tags(raw_tags, context)
                
                if rejected_tags:
                    db_logger.warning(f"Rejected {len(rejected_tags)} invalid tags for {artist} - {album_title}: {rejected_tags}")
                
                if processed_count < 5:  # Debug log for first few rows
                    db_logger.info(f"Row {processed_count}: validation - valid: {len(valid_tags)}, rejected: {len(rejected_tags)}")
                
                processed_tags = set()  # Use set to avoid duplicates after normalization
                for validated_tag in valid_tags:
                    normalized_tag = normalize_tag(validated_tag)
                    if normalized_tag and normalized_tag not in processed_tags:
                        processed_tags.add(normalized_tag)
                        
                        # Check if tag already exists (by normalized name)
                        existing_tag = session.query(Tag).filter(Tag.normalized_name == normalized_tag).first()
                        if not existing_tag:
                            # Create a new tag with a unique ID
                            tag_id = str(uuid.uuid4())
                            category = _tag_normalizer.get_category(normalized_tag)
                            new_tag = Tag(
                                id=tag_id,
                                name=normalized_tag,  # Use normalized form as primary name
                                normalized_name=normalized_tag,
                                is_canonical=1
                            )
                            session.add(new_tag)
                            session.flush()  # Flush to get the tag ID
                            # Add the relationship between album and tag
                            album.tags.append(new_tag)
                        else:
                            # Use the existing tag
                            album.tags.append(existing_tag)
                    
                if processed_count < 5:  # Debug log for first few rows
                    db_logger.info(f"Row {processed_count}: final normalized tags: {list(processed_tags)}")
            
            # Handle country tags if available
            if country_str:
                countries = [c.strip() for c in re.split(r'[;,]', str(country_str)) if c.strip()]
                processed_countries = set()  # Use set to avoid duplicates after normalization
                for country_name in countries:
                    normalized_country = normalize_tag(country_name)
                    if normalized_country and normalized_country not in processed_countries:
                        processed_countries.add(normalized_country)
                        
                        # Check if country tag already exists (by normalized name)
                        existing_country_tag = session.query(Tag).filter(Tag.normalized_name == normalized_country).first()
                        if not existing_country_tag:
                            # Create a new country tag with a unique ID
                            country_tag_id = str(uuid.uuid4())
                            new_country_tag = Tag(
                                id=country_tag_id,
                                name=normalized_country,  # Use normalized form as primary name
                                normalized_name=normalized_country,
                                is_canonical=1
                            )
                            session.add(new_country_tag)
                            session.flush()  # Flush to get the tag ID
                            # Add the relationship between album and country tag
                            album.tags.append(new_country_tag)
                        else:
                            # Use the existing country tag
                            album.tags.append(existing_country_tag)
            
            # Handle vocal style tags if available
            if vocal_style_tags:
                processed_vocal_styles = set()

                if processed_count < 5:
                    db_logger.info(f"Row {processed_count}: vocal style tags: {vocal_style_tags}")

                for normalized_vocal_style in vocal_style_tags:
                    if normalized_vocal_style in processed_vocal_styles:
                        continue

                    processed_vocal_styles.add(normalized_vocal_style)

                    existing_vocal_tag = session.query(Tag).filter(Tag.normalized_name == normalized_vocal_style).first()
                    if not existing_vocal_tag:
                        vocal_tag_id = str(uuid.uuid4())
                        new_vocal_tag = Tag(
                            id=vocal_tag_id,
                            name=normalized_vocal_style,
                            normalized_name=normalized_vocal_style,
                            is_canonical=1
                        )
                        session.add(new_vocal_tag)
                        session.flush()
                        album.tags.append(new_vocal_tag)

                        if processed_count < 5:
                            db_logger.info(f"Row {processed_count}: created new vocal style tag '{normalized_vocal_style}' for {artist} - {album_title}")
                    else:
                        album.tags.append(existing_vocal_tag)

                        if processed_count < 5:
                            db_logger.info(f"Row {processed_count}: using existing vocal style tag '{normalized_vocal_style}' for {artist} - {album_title}")
            
            # Add to existing albums set to handle duplicates within the dataframe
            existing_albums.add((artist, album_title))
            processed_count += 1

        session.commit()
        load_end_time = datetime.now()
        processing_time = load_end_time - load_start_time
        
        # Consolidate any duplicate tags created during loading
        consolidate_duplicate_tags(session)
        
        # Count total tags in database after loading
        total_tags = session.query(Tag).count()
        db_logger.info(f"DataFrame data loaded successfully in {processing_time.total_seconds():.2f} seconds")
        db_logger.info(f"Processed {processed_count} rows. Total tags in database: {total_tags}")

    except Exception as e:
        session.rollback()
        db_logger.error(f"Error loading DataFrame data: {str(e)}", exc_info=True)
        raise
    finally:
        session.close()

def load_csv_data(csv_dir: Path) -> None:
    """Load data from CSV files into database."""
    db_logger.info(f"Loading CSV data from {csv_dir}")
    
    # Check if CSV data has already been loaded to prevent duplicates
    session = get_session()
    try:
        existing_count = session.query(Album).count()
        db_logger.info(f"Current album count in database: {existing_count}")
        
        # Check for any albums that look like they're from Reddit CSV (normal capitalization)
        sample_albums = session.query(Album).limit(10).all()
        has_reddit_data = any(
            not album.title.isupper() and not album.pa_artist_name_on_album.isupper() 
            for album in sample_albums 
            if album.pa_artist_name_on_album and album.title
        )
        
        if has_reddit_data:
            db_logger.info("Reddit CSV data appears to already be loaded (found non-uppercase albums). Skipping CSV loading.")
            return
        
        if existing_count > 10000:  # If we have a lot of data, probably already loaded
            db_logger.info(f"Large number of albums ({existing_count}) already in database. Checking if CSV reload is needed...")
            # You might want to add more sophisticated checking here
    
    except Exception as e:
        db_logger.warning(f"Error checking existing data: {e}")
    finally:
        session.close()
    
    # Continue with original loading logic
    load_start_time = datetime.now()
    db_logger.info(f"CSV loading started at {load_start_time.strftime('%H:%M:%S')}")
    
    session = get_session()
    try:
        # Process each CSV file
        csv_files = list(csv_dir.glob('*.csv'))
        db_logger.info(f"Found {len(csv_files)} CSV files to process")
        
        for csv_file in csv_files:
            try:
                year = extract_year(csv_file.name)
                if year:
                    file_start_time = datetime.now()
                    db_logger.info(f"Processing {csv_file.name} for year {year}, started at {file_start_time.strftime('%H:%M:%S')}")
                    _process_csv_file(csv_file, year, session)
                    file_end_time = datetime.now()
                    file_processing_time = file_end_time - file_start_time
                    db_logger.info(f"Finished processing {csv_file.name} in {file_processing_time.total_seconds():.2f} seconds")
            except Exception as e:
                db_logger.error(f"Error processing {csv_file}: {str(e)}", exc_info=True)
        
        session.commit()
        load_end_time = datetime.now()
        processing_time = load_end_time - load_start_time
        
        # Consolidate any duplicate tags created during CSV loading
        consolidate_duplicate_tags(session)
        
        db_logger.info(f"CSV data loaded successfully in {processing_time.total_seconds():.2f} seconds")
        
    except Exception as e:
        session.rollback()
        db_logger.error(f"Error loading CSV data: {str(e)}", exc_info=True)
        raise
    finally:
        session.close()

def _process_csv_file(csv_file: Path, year: int, session: Session) -> None:
    """Process a single CSV file."""
    debug_log_counts = {}
    MAX_DEBUG_LOGS_PER_TYPE = 10
    
    # Add a start timestamp for processing each file
    start_time = datetime.now()
    db_logger.info(f"Started processing {csv_file.name} at {start_time.strftime('%H:%M:%S')}")
    
    processed_rows = 0
    skipped_rows = 0
    processed_count = 0
    skipped_count = 0
    processed_albums = []  # List to track all processed albums

    def is_potential_date_val(val_str: str) -> bool:
        if not val_str:
            return False
        # Check for ISO date format first
        if is_iso_date(val_str):
            return True
        return val_str.strip().lower() in POTENTIAL_DATE_TOKENS

    # First, we need to find the actual header row
    actual_header_row = 0
    with open(csv_file, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if line.strip().startswith("Artist,Album,Release Date"):
                actual_header_row = i
                break
        
    if actual_header_row == 0:
        db_logger.warning(f"Could not find header row in {csv_file.name}, using default")
        actual_header_row = 12  # Default based on observed files
    
    db_logger.info(f"Found header row at line {actual_header_row} in {csv_file.name}")
    
    db_logger.info(f"[_process_csv_file] About to open {csv_file.name}") # New log before open
    # Now read the CSV with the correct header row
    with open(csv_file, 'r', encoding='utf-8') as f:
        db_logger.info(f"[_process_csv_file] Successfully opened {csv_file.name}") # New log after open
        try:
            db_logger.info("Attempting to skip lines (simple log)") # Changed log statement
            # db_logger.info(f"Attempting to skip {actual_header_row} lines in {csv_file.name}") # Original log commented out
            for i in range(actual_header_row):
                line_content = next(f).strip()
                # Log sparingly, e.g., first and last skipped line, or if it's an important line
                if i == 0 or i == actual_header_row - 1:
                    db_logger.debug(f"Skipped line {i+1}/{actual_header_row}: {line_content[:100]}") # Log first 100 chars
            db_logger.info(f"Successfully skipped {actual_header_row} lines.")
            
            # Peek at the next line which should be the header for DictReader
            try:
                potential_header = f.readline().strip()
                db_logger.info(f"Line to be used as header by DictReader: {potential_header[:200]}") # Log first 200 chars
                # We need to put this line back or use a reader that can handle a pre-read line,
                # or re-open. For simplicity, let's re-open and skip again,
                # this time without peeking. This is slightly inefficient but good for debugging.
            except StopIteration:
                db_logger.error(f"StopIteration after skipping lines, before DictReader: File may be shorter than expected or header row was last line.")
                return # Cant proceed

            # Re-open file and skip lines to reset iterator state for DictReader
            f.seek(0) 
            for _ in range(actual_header_row):
                next(f)
            # Now f is positioned right before the true header line for DictReader

            db_logger.info(f"Initializing csv.DictReader for {csv_file.name}")
            reader = csv.DictReader(f)
            db_logger.info(f"csv.DictReader initialized. Fieldnames: {reader.fieldnames}")

        except StopIteration:
            db_logger.error(f"StopIteration occurred while skipping to header in {csv_file.name}. File might be shorter than expected or header row count is off. Skipped {i+1} lines before error.", exc_info=True)
            return # Can't proceed
        except Exception as e:
            db_logger.error(f"An error occurred setting up DictReader for {csv_file.name}: {str(e)}", exc_info=True)
            return # Can't proceed
        
        # Format the header names with proper line breaks to avoid truncation in logs
        headers_str = ', '.join(str(field) for field in reader.fieldnames) if reader.fieldnames else "None"
        db_logger.debug(f"CSV Headers for {csv_file.name}: [{headers_str}]")
        
        if not reader.fieldnames or len(reader.fieldnames) < 3:
            db_logger.warning(f"Skipping file {csv_file.name}: Insufficient columns in header (need at least 3, found {len(reader.fieldnames) if reader.fieldnames else 0}). Headers: [{headers_str}]")
            return

        # Expected column names based on observed files
        artist_col = "Artist"
        album_col = "Album"
        release_date_col = "Release Date"
        length_col = "Length"  # Often contains LP/EP info
        genre_col = "Genre / Subgenres"
        vocal_style_col = "Vocal Style"
        country_col = "Country / State"
        
        # Make sure we're using the actual column names from the file
        artist_col_key = next((col for col in reader.fieldnames if col and "artist" in col.lower()), reader.fieldnames[0])
        album_col_key = next((col for col in reader.fieldnames if col and "album" in col.lower()), reader.fieldnames[1] if len(reader.fieldnames) > 1 else None)
        release_date_col_key = next((col for col in reader.fieldnames if col and "release" in col.lower()), reader.fieldnames[2] if len(reader.fieldnames) > 2 else None)
        length_col_key = next((col for col in reader.fieldnames if col and "length" in col.lower()), None)
        genre_col_key = next((col for col in reader.fieldnames if col and "genre" in col.lower()), None)
        vocal_style_col_key = next((col for col in reader.fieldnames if col and "vocal" in col.lower()), None)
        country_col_key = next((col for col in reader.fieldnames if col and "country" in col.lower()), None)
        
        db_logger.debug(f"Using columns: Artist='{artist_col_key}', Album='{album_col_key}', Release Date='{release_date_col_key}', Length='{length_col_key}', Genre='{genre_col_key}', Vocal Style='{vocal_style_col_key}', Country='{country_col_key}'")
        
        processing_started_for_file = False
        row_count = 0
        processed_count = 0
        skipped_count = 0
        log_interval = 100  # Log progress every 100 rows
        
        # Start timer for row processing
        row_processing_start = datetime.now()
        db_logger.info(f"Starting row processing for {csv_file.name} at {row_processing_start.strftime('%H:%M:%S')}")
        
        for row_num, row in enumerate(reader):
            # Removed excessive INFO logging that was causing hangs
            # db_logger.info(f"Processing row {row_num + 1} in {csv_file.name}")
            processing_started_for_file = True
            row_count += 1
            
            # Log progress at intervals
            if row_count % log_interval == 0:
                current_time = datetime.now()
                elapsed = current_time - row_processing_start
                db_logger.info(f"Processing {csv_file.name}: {row_count} rows processed so far ({processed_count} added, {skipped_count} skipped) in {elapsed.total_seconds():.2f} seconds")
            
            try:
                # Extract basic information
                artist = row.get(artist_col_key, '').strip()
                album_title = row.get(album_col_key, '').strip()
                release_date_str = row.get(release_date_col_key, '').strip()
                length_info = row.get(length_col_key, '').strip() if length_col_key else ''
                genre_and_tags_str = row.get(genre_col_key, '').strip() if genre_col_key else ''
                vocal_style_str = row.get(vocal_style_col_key, '').strip() if vocal_style_col_key else ''
                country_str = row.get(country_col_key, '').strip() if country_col_key else ''

                vocal_style_tags = extract_vocal_style_tags(vocal_style_str)
                vocal_style_display = ', '.join(vocal_style_tags) if vocal_style_tags else ''
                combined_raw_tags = build_raw_tags_string(genre_and_tags_str, vocal_style_tags)
                
                # Skip empty rows and header-like rows
                if not artist or artist.lower() in ["artist", "albums:", "singles:", "eps:"]:
                    db_logger.debug(f"Skipping row {row_num + 1}: Missing or invalid artist ('{artist}')")
                    skipped_count += 1
                    continue
                
                # Clean up album title
                if album_title.lower() in ["album", "release date", "format", ""]:
                    db_logger.debug(f"Skipping row {row_num + 1}: Invalid album title ('{album_title}')")
                    skipped_count += 1
                    continue
                
                # Handle format information (LP, EP, etc.)
                format_info = None
                # Check if length_info is a format designation (like LP, EP, 2LP)
                if length_info and is_format_string(length_info):
                    format_info = length_info
                    db_logger.debug(f"Extracted format '{format_info}' from length column for {artist} - {album_title}")
                
                # Sometimes the album title itself might be a format string (like "2LP")
                # Only skip if it's a bare format with no artist
                if is_format_string(album_title) and not artist:
                    db_logger.debug(f"Skipping row {row_num + 1}: Album title is a format string ('{album_title}') with no artist")
                    skipped_count += 1
                    continue
                elif is_format_string(album_title) and artist:
                    db_logger.info(f"Album title is a format string ('{album_title}') for artist '{artist}' but will be processed anyway")
                
                # Enhanced release date handling
                release_date_obj = None
                extracted_year = year  # Default to the year from the filename

                # Try to parse ISO date first
                if release_date_str and is_iso_date(release_date_str):
                    try:
                        release_date_obj = datetime.strptime(release_date_str, '%Y-%m-%d')
                        db_logger.debug(f"Parsed ISO date '{release_date_str}' for {artist} - {album_title}")
                    except ValueError:
                        db_logger.warning(f"Failed to parse ISO date '{release_date_str}' for {artist} - {album_title}")
                
                # Handle edge cases for release date
                elif release_date_str:
                    # Handle dash as release date (e.g., Empire State Bastard)
                    if release_date_str.strip() == "-":
                        db_logger.info(f"Found dash as release date for {artist} - {album_title}, using year {year} from filename")
                        # Use January 1st of the year as a placeholder
                        release_date_obj = datetime(year, 1, 1)
                    
                    # Handle typo "Mat" instead of "Mar" (e.g., Rusty Bonez)
                    elif re.match(r'^Mat\s+\d{1,2}$', release_date_str, re.IGNORECASE):
                        # Assume "Mat" is a typo for "Mar"
                        corrected_date_str = f"Mar {release_date_str.split()[1]} {year}"
                        try:
                            release_date_obj = datetime.strptime(corrected_date_str, '%b %d %Y')
                            db_logger.info(f"Corrected typo 'Mat' to 'Mar' for {artist} - {album_title}: {corrected_date_str}")
                        except ValueError:
                            db_logger.warning(f"Failed to parse corrected date '{corrected_date_str}' for {artist} - {album_title}")
                    
                    # Handle month abbreviations with day
                    elif re.match(r'^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}$', release_date_str, re.IGNORECASE):
                        try:
                            date_with_year = f"{release_date_str} {year}"
                            release_date_obj = datetime.strptime(date_with_year, '%b %d %Y')
                            db_logger.debug(f"Parsed month+day format '{release_date_str}' with year {year} for {artist} - {album_title}")
                        except ValueError:
                            db_logger.warning(f"Failed to parse month+day format '{release_date_str}' for {artist} - {album_title}")
                    
                    # Handle descriptive dates like "Early 2024", "Late 2023", etc.
                    elif any(word in release_date_str.lower() for word in ["early", "mid", "late", "spring", "summer", "fall", "autumn", "winter"]):
                        # Try to extract year from descriptive date
                        year_match = re.search(r'20\d{2}', release_date_str)
                        if year_match:
                            extracted_year = int(year_match.group())
                            db_logger.info(f"Extracted year {extracted_year} from descriptive date '{release_date_str}' for {artist} - {album_title}")
                        # Create a date object with the extracted year and approximate month
                        if "early" in release_date_str.lower():
                            release_date_obj = datetime(extracted_year, 3, 1)  # March 1st
                        elif "mid" in release_date_str.lower():
                            release_date_obj = datetime(extracted_year, 6, 1)  # June 1st
                        elif "late" in release_date_str.lower():
                            release_date_obj = datetime(extracted_year, 10, 1)  # October 1st
                        elif "spring" in release_date_str.lower():
                            release_date_obj = datetime(extracted_year, 4, 1)  # April 1st
                        elif "summer" in release_date_str.lower():
                            release_date_obj = datetime(extracted_year, 7, 1)  # July 1st
                        elif "fall" in release_date_str.lower() or "autumn" in release_date_str.lower():
                            release_date_obj = datetime(extracted_year, 9, 1)  # September 1st
                        elif "winter" in release_date_str.lower():
                            release_date_obj = datetime(extracted_year, 12, 1)  # December 1st
                        else:
                            # Default to January 1st of the extracted year
                            release_date_obj = datetime(extracted_year, 1, 1)
                            
                        db_logger.info(f"Used approximate date {release_date_obj.strftime('%Y-%m-%d')} for descriptive date '{release_date_str}' ({artist} - {album_title})")
                    
                    # Handle quarter specifications (Q1, Q2, Q3, Q4)
                    elif re.match(r'^Q[1-4](\s+20\d{2})?$', release_date_str, re.IGNORECASE):
                        quarter_match = re.match(r'^Q([1-4])(?:\s+(20\d{2}))?$', release_date_str, re.IGNORECASE)
                        if quarter_match:
                            quarter = int(quarter_match.group(1))
                            # Check if there's a year in the string
                            if quarter_match.group(2):
                                extracted_year = int(quarter_match.group(2))
                            
                            # Map quarter to month
                            month_mapping = {1: 2, 2: 5, 3: 8, 4: 11}  # Middle of each quarter
                            release_date_obj = datetime(extracted_year, month_mapping[quarter], 15)
                            db_logger.info(f"Mapped quarter '{release_date_str}' to date {release_date_obj.strftime('%Y-%m-%d')} for {artist} - {album_title}")
                    
                    # Handle just month name (e.g., "January", "February")
                    elif re.match(r'^(January|February|March|April|May|June|July|August|September|October|November|December)(\s+20\d{2})?$', release_date_str, re.IGNORECASE):
                        month_match = re.match(r'^(January|February|March|April|May|June|July|August|September|October|November|December)(?:\s+(20\d{2}))?$', release_date_str, re.IGNORECASE)
                        if month_match:
                            month_name = month_match.group(1)
                            # Check if there's a year in the string
                            if month_match.group(2):
                                extracted_year = int(month_match.group(2))
                            
                            # Convert month name to month number
                            month_mapping = {
                                "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
                                "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
                            }
                            month_num = month_mapping.get(month_name.lower(), 1)
                            release_date_obj = datetime(extracted_year, month_num, 15)  # Middle of the month
                            db_logger.info(f"Converted month name '{release_date_str}' to date {release_date_obj.strftime('%Y-%m-%d')} for {artist} - {album_title}")
                    
                    # Handle month abbreviation (e.g., "Jan", "Feb")
                    elif re.match(r'^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)(\s+20\d{2})?$', release_date_str, re.IGNORECASE):
                        month_match = re.match(r'^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)(?:\s+(20\d{2}))?$', release_date_str, re.IGNORECASE)
                        if month_match:
                            month_abbr = month_match.group(1)
                            # Check if there's a year in the string
                            if month_match.group(2):
                                extracted_year = int(month_match.group(2))
                            
                            # Parse the date
                            date_with_day = f"{month_abbr} 15 {extracted_year}"  # Use middle of the month
                            try:
                                release_date_obj = datetime.strptime(date_with_day, '%b %d %Y')
                                db_logger.info(f"Parsed month abbreviation '{release_date_str}' to date {release_date_obj.strftime('%Y-%m-%d')} for {artist} - {album_title}")
                            except ValueError:
                                db_logger.warning(f"Failed to parse month abbreviation '{release_date_str}' for {artist} - {album_title}")
                    
                    # If we couldn't parse the date, use a default date for the year
                    if not release_date_obj:
                        db_logger.warning(f"Could not parse release date '{release_date_str}' for {artist} - {album_title}, using default date for year {extracted_year}")
                        release_date_obj = datetime(extracted_year, 1, 1)  # January 1st
                
                # If we still don't have a release date, use the year from the filename
                if not release_date_obj:
                    release_date_obj = datetime(year, 1, 1)  # January 1st of the year from the filename
                    db_logger.debug(f"Using default date {release_date_obj.strftime('%Y-%m-%d')} for {artist} - {album_title}")
                
                # Generate a unique ID for the album
                album_id = str(uuid.uuid4())
                
                # Create the album object
                album = Album(
                    id=album_id,
                    title=album_title,
                    pa_artist_name_on_album=artist,
                    release_date=release_date_obj,
                    release_year=release_date_obj.year,
                    length=length_info if not format_info else length_info,
                    vocal_style=vocal_style_display or None,
                    genre=genre_and_tags_str,
                    country=country_str,
                    raw_tags=combined_raw_tags,
                    last_updated=datetime.now()
                )
                session.add(album)
                
                # Handle tags and genres
                if genre_and_tags_str:
                    # Split by commas and semicolons
                    raw_tags = [tag.strip() for tag in re.split(r'[;,]', str(genre_and_tags_str)) if tag.strip()]
                    if processed_count < 5:  # Debug log for first few rows
                        db_logger.info(f"Row {processed_count}: raw tags: {raw_tags}")
                    
                    # Validate tags first
                    context = {
                        'artist': artist,
                        'album': album_title,
                        'source': 'dataframe_import'
                    }
                    valid_tags, rejected_tags, validation_info = _tag_validator.filter_tags(raw_tags, context)
                    
                    if rejected_tags:
                        db_logger.warning(f"Rejected {len(rejected_tags)} invalid tags for {artist} - {album_title}: {rejected_tags}")
                    
                    if processed_count < 5:  # Debug log for first few rows
                        db_logger.info(f"Row {processed_count}: validation - valid: {len(valid_tags)}, rejected: {len(rejected_tags)}")
                    
                    processed_tags = set()  # Use set to avoid duplicates after normalization
                    for validated_tag in valid_tags:
                        normalized_tag = normalize_tag(validated_tag)
                        if normalized_tag and normalized_tag not in processed_tags:
                            processed_tags.add(normalized_tag)
                            
                            # Check if tag already exists (by normalized name)
                            existing_tag = session.query(Tag).filter(Tag.normalized_name == normalized_tag).first()
                            if not existing_tag:
                                # Create a new tag with a unique ID
                                tag_id = str(uuid.uuid4())
                                category = _tag_normalizer.get_category(normalized_tag)
                                new_tag = Tag(
                                    id=tag_id,
                                    name=normalized_tag,  # Use normalized form as primary name
                                    normalized_name=normalized_tag,
                                    is_canonical=1
                                )
                                session.add(new_tag)
                                session.flush()  # Flush to get the tag ID
                                # Add the relationship between album and tag
                                album.tags.append(new_tag)
                            else:
                                # Use the existing tag
                                album.tags.append(existing_tag)
                    
                    if processed_count < 5:  # Debug log for first few rows
                        db_logger.info(f"Row {processed_count}: final normalized tags: {list(processed_tags)}")
                
                # Handle country tags if available
                if country_str:
                    countries = [c.strip() for c in re.split(r'[;,]', country_str) if c.strip()]
                    processed_countries = set()  # Use set to avoid duplicates after normalization
                    for country_name in countries:
                        normalized_country = normalize_tag(country_name)
                        if normalized_country and normalized_country not in processed_countries:
                            processed_countries.add(normalized_country)
                            
                            # Check if country tag already exists (by normalized name)
                            existing_country_tag = session.query(Tag).filter(Tag.normalized_name == normalized_country).first()
                            if not existing_country_tag:
                                # Create a new country tag with a unique ID
                                country_tag_id = str(uuid.uuid4())
                                new_country_tag = Tag(
                                    id=country_tag_id,
                                    name=normalized_country,  # Use normalized form as primary name
                                    normalized_name=normalized_country,
                                    is_canonical=1
                                )
                                session.add(new_country_tag)
                                session.flush()  # Flush to get the tag ID
                                # Add the relationship between album and country tag
                                album.tags.append(new_country_tag)
                            else:
                                # Use the existing country tag
                                album.tags.append(existing_country_tag)
                
                # Handle vocal style tags if available
                if vocal_style_tags:
                    processed_vocal_styles = set()

                    if processed_count < 5:
                        db_logger.info(f"Row {processed_count}: vocal style tags: {vocal_style_tags}")

                    for normalized_vocal_style in vocal_style_tags:
                        if normalized_vocal_style in processed_vocal_styles:
                            continue

                        processed_vocal_styles.add(normalized_vocal_style)

                        existing_vocal_tag = session.query(Tag).filter(Tag.normalized_name == normalized_vocal_style).first()
                        if not existing_vocal_tag:
                            vocal_tag_id = str(uuid.uuid4())
                            new_vocal_tag = Tag(
                                id=vocal_tag_id,
                                name=normalized_vocal_style,
                                normalized_name=normalized_vocal_style,
                                is_canonical=1
                            )
                            session.add(new_vocal_tag)
                            session.flush()
                            album.tags.append(new_vocal_tag)

                            if processed_count < 5:
                                db_logger.info(f"Row {processed_count}: created new vocal style tag '{normalized_vocal_style}' for {artist} - {album_title}")
                        else:
                            album.tags.append(existing_vocal_tag)

                            if processed_count < 5:
                                db_logger.info(f"Row {processed_count}: using existing vocal style tag '{normalized_vocal_style}' for {artist} - {album_title}")
                
                processed_count += 1
                db_logger.debug(f"Added album: {artist} - {album_title} (ID: {album_id}, Release Date: {release_date_obj.strftime('%Y-%m-%d')})")
                
                # Add to processed albums list for tracking
                processed_albums.append({
                    "id": album_id,
                    "artist": artist,
                    "title": album_title,
                    "release_date": release_date_obj.strftime('%Y-%m-%d')
                })
                
                # Every 50 rows, try to commit to avoid large transactions
                if processed_count % 50 == 0:
                    try:
                        session.flush()
                        db_logger.debug(f"Flushed after {processed_count} rows")
                    except Exception as e:
                        db_logger.error(f"Error flushing after {processed_count} rows: {str(e)}", exc_info=True)
            
            except Exception as e:
                db_logger.error(f"Error processing row {row_num + 1} in {csv_file.name}: {str(e)}", exc_info=True)
                # Optionally, you can skip to the next row or re-raise the exception
                skipped_count += 1
                continue
    
    # Add an info log at the end of processing each file
    end_time = datetime.now()
    elapsed_time = end_time - start_time
    db_logger.info(f"Finished processing {csv_file.name} at {end_time.strftime('%H:%M:%S')} (Elapsed time: {str(elapsed_time).split('.')[0]})")
    
    # Log summary of processed and skipped rows
    db_logger.info(f"Processed {processed_count} rows, skipped {skipped_count} rows in {csv_file.name}")
    
    # Return summary statistics including processed albums
    return {
        "processed": processed_count,
        "skipped": skipped_count,
        "file": csv_file.name,
        "year": year,
        "start_time": start_time,
        "end_time": end_time,
        "elapsed_time": elapsed_time,
        "albums": processed_albums  # Add this to track processed albums
    }

def debug_database_tags():
    """Debug function to inspect what's actually in the database."""
    print("=== DEBUG_DATABASE_TAGS CALLED ===")  # Simple print to ensure function is called
    db_logger.info("=== DEBUG_DATABASE_TAGS FUNCTION STARTED ===")
    session = get_session()
    try:
        # Get first 10 albums and their genre/raw_tags fields
        albums = session.query(Album).limit(10).all()
        db_logger.info(f"=== DATABASE DEBUG - First 10 albums ===")
        for i, album in enumerate(albums):
            db_logger.info(f"Album {i}: {album.pa_artist_name_on_album} - {album.title}")
            db_logger.info(f"  genre: '{album.genre}'")
            db_logger.info(f"  raw_tags: '{album.raw_tags}'")
            db_logger.info(f"  country: '{album.country}'")
            db_logger.info(f"  tags relationship count: {len(album.tags)}")
            
        # Count total tags in database
        total_tags = session.query(Tag).count()
        db_logger.info(f"Total tags in database: {total_tags}")
        
        # Show a few sample tags if they exist
        if total_tags > 0:
            sample_tags = session.query(Tag).limit(5).all()
            db_logger.info(f"Sample tags:")
            for tag in sample_tags:
                db_logger.info(f"  - {tag.name} (canonical: {tag.is_canonical})")
        
        db_logger.info(f"=== END DATABASE DEBUG ===")
        
    except Exception as e:
        db_logger.error(f"Error in debug_database_tags: {e}")
    finally:
        session.close()

def consolidate_duplicate_tags(session: Session):
    """Consolidate duplicate tags that may have been created during loading."""
    db_logger.info("Starting tag consolidation process...")
    
    # Find tags with the same normalized name
    duplicate_groups = {}
    all_tags = session.query(Tag).all()
    
    for tag in all_tags:
        normalized = tag.normalized_name or normalize_tag(tag.name)
        if normalized not in duplicate_groups:
            duplicate_groups[normalized] = []
        duplicate_groups[normalized].append(tag)
    
    # Process groups with duplicates
    merged_count = 0
    for normalized_name, tags in duplicate_groups.items():
        if len(tags) > 1:
            # Choose canonical tag (prefer the one with most albums)
            canonical_tag = max(tags, key=lambda t: len(t.albums))
            other_tags = [t for t in tags if t != canonical_tag]
            
            db_logger.info(f"Consolidating {len(other_tags)} duplicate tags into '{canonical_tag.name}'")
            
            for duplicate_tag in other_tags:
                # Transfer all album associations to canonical tag
                for album in duplicate_tag.albums:
                    if canonical_tag not in album.tags:
                        album.tags.append(canonical_tag)
                    album.tags.remove(duplicate_tag)
                
                # Delete the duplicate tag
                session.delete(duplicate_tag)
                merged_count += 1
    
    if merged_count > 0:
        session.commit()
        db_logger.info(f"Consolidated {merged_count} duplicate tags")
    else:
        db_logger.info("No duplicate tags found to consolidate")
    
    return merged_count