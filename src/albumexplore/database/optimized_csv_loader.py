"""Optimized CSV data loader for improved performance after parsing."""
import csv
import os
from pathlib import Path
from typing import Dict, Set, List, Tuple
from datetime import datetime
import re
import uuid
import pandas as pd
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import text

from albumexplore.database import get_session
from albumexplore.database.models import Album, Tag, TagCategory
from albumexplore.gui.gui_logging import db_logger, performance_logger
from albumexplore.tags.normalizer.tag_normalizer import TagNormalizer
from albumexplore.database.tag_validator import TagValidationFilter

# Import vocal-style helpers (now with length checks)
from albumexplore.database.csv_loader import (
    extract_vocal_style_tags,
    build_raw_tags_string
)

# Initialize advanced tag normalizer and validator
_tag_normalizer = TagNormalizer()
_tag_validator = TagValidationFilter(strict_mode=False)

# Pre-compiled regex patterns for performance
_TAG_SPLIT_PATTERN = re.compile(r'[;,]')
_YEAR_PATTERN = re.compile(r'20\d{2}')

def load_dataframe_data_optimized(df: pd.DataFrame, session: Session) -> None:
    """Optimized version of load_dataframe_data with batch processing and caching."""
    start_time = datetime.now()
    db_logger.info(f"Starting optimized data loading from DataFrame. Rows: {len(df)}")
    performance_logger.info(f"[PERF] Starting optimized data load: {len(df)} rows")
    
    # Initialize performance monitoring
    try:
        from albumexplore.performance.performance_monitor import global_performance_monitor
        perf_monitor = global_performance_monitor
        perf_monitor.start_operation("Optimized Data Loading")
    except ImportError:
        perf_monitor = None

    try:
        # === PHASE 1: Data Preprocessing and Validation ===
        phase_start = datetime.now()
        db_logger.info("Phase 1: Preprocessing and validation...")
        if perf_monitor:
            perf_monitor.start_operation("Data Preprocessing")
        
        # Standardize DataFrame columns
        df.columns = [col.lower().strip() for col in df.columns]
        required_cols = {'artist', 'album'}
        if not required_cols.issubset(df.columns):
            raise ValueError(f"DataFrame must contain 'artist' and 'album' columns. Found: {df.columns}")

        # Batch filter out invalid rows
        valid_mask = (
            ~df['artist'].isna() & 
            ~df['album'].isna() & 
            (df['artist'].astype(str).str.strip() != '') & 
            (df['album'].astype(str).str.strip() != '') &
            ~df['artist'].astype(str).str.lower().isin(['nan', 'none', '']) &
            ~df['album'].astype(str).str.lower().isin(['nan', 'none', ''])
        )
        
        df_clean = df[valid_mask].copy()
        db_logger.info(f"Filtered {len(df) - len(df_clean)} invalid rows, {len(df_clean)} valid rows remaining")
        
        # Batch get existing albums to avoid duplicates
        existing_albums_query = session.query(Album.pa_artist_name_on_album, Album.title).all()
        existing_albums = {(artist, title) for artist, title in existing_albums_query}
        db_logger.info(f"Found {len(existing_albums)} existing albums in database")
        
        # Filter out duplicates using vectorized operations (much faster than apply)
        df_clean['artist_clean'] = df_clean['artist'].astype(str).str.strip()
        df_clean['album_clean'] = df_clean['album'].astype(str).str.strip()
        
        # Create tuples and check membership in set - vectorized approach
        album_tuples = list(zip(df_clean['artist_clean'], df_clean['album_clean']))
        df_clean['is_duplicate'] = [tuple_val in existing_albums for tuple_val in album_tuples]
        
        df_new = df_clean[~df_clean['is_duplicate']].copy()
        duplicates_count = len(df_clean) - len(df_new)
        db_logger.info(f"Filtered {duplicates_count} duplicate albums, {len(df_new)} new albums to process")
        
        phase_time = (datetime.now() - phase_start).total_seconds()
        performance_logger.info(f"[PERF] Phase 1 completed in {phase_time:.2f}s")
        if perf_monitor:
            perf_monitor.complete_operation("Data Preprocessing", len(df_new))

        # === PHASE 2: Batch Tag Processing ===
        phase_start = datetime.now()
        db_logger.info("Phase 2: Batch tag processing...")
        if perf_monitor:
            perf_monitor.start_operation("Tag Processing")
        
        # Vectorized NaN handling - much faster than iterating
        genre_col = 'genre / subgenres' if 'genre / subgenres' in df_new.columns else 'genre' if 'genre' in df_new.columns else 'genres'
        country_col = 'country / state' if 'country / state' in df_new.columns else 'country'
        vocal_col = 'vocal style' if 'vocal style' in df_new.columns else 'vocal_style'
        
        df_new[genre_col] = df_new[genre_col].fillna('').astype(str)
        if country_col in df_new.columns:
            df_new[country_col] = df_new[country_col].fillna('').astype(str)
        if vocal_col in df_new.columns:
            df_new[vocal_col] = df_new[vocal_col].fillna('').astype(str)
        
        # Collect all unique tags from all rows
        all_raw_tags = set()
        row_tag_mapping = {}  # row_index -> list of normalized tags
        row_vocal_style_tags = {}  # row_index -> list of vocal style tags
        row_vocal_style_display = {}  # row_index -> string for display
        
        total_rows = len(df_new)
        for row_num, (idx, row) in enumerate(df_new.iterrows()):
            if row_num % 1000 == 0:
                db_logger.info(f"Phase 2: Processing row {row_num}/{total_rows}...")
            
            genre_and_tags_str = row.get(genre_col, '')
            country_str = row.get(country_col, '')
            vocal_style_str = row.get(vocal_col, '')
            
            # Extract tags using pre-compiled regex
            row_tags = []
            if genre_and_tags_str:
                raw_tags = [tag.strip() for tag in _TAG_SPLIT_PATTERN.split(genre_and_tags_str) if tag.strip()]
                all_raw_tags.update(raw_tags)
                row_tags.extend(raw_tags)
            
            if country_str:
                countries = [c.strip() for c in _TAG_SPLIT_PATTERN.split(country_str) if c.strip()]
                all_raw_tags.update(countries)
                row_tags.extend(countries)

            if row_num == 0:
                db_logger.info(f"Phase 2: Row 0 vocal_style_str length={len(vocal_style_str)}, preview={repr(vocal_style_str[:100])}")
            
            vocal_style_tags = extract_vocal_style_tags(vocal_style_str)
            
            if row_num == 0:
                db_logger.info(f"Phase 2: Row 0 extracted {len(vocal_style_tags)} vocal tags")
            
            if vocal_style_tags:
                row_vocal_style_tags[idx] = vocal_style_tags
                row_vocal_style_display[idx] = ', '.join(vocal_style_tags)
                all_raw_tags.update(vocal_style_tags)
                row_tags.extend(vocal_style_tags)

            row_tag_mapping[idx] = row_tags
        
        db_logger.info(f"Phase 2: Tag collection complete. Collected {len(all_raw_tags)} unique raw tags across {total_rows} rows")
        
        # Batch validate all tags
        context = {'source': 'dataframe_import_batch'}
        all_tags_list = list(all_raw_tags)
        valid_tags, rejected_tags, validation_info = _tag_validator.filter_tags(all_tags_list, context)
        
        db_logger.info(f"Tag validation: {len(valid_tags)} valid, {len(rejected_tags)} rejected")
        if rejected_tags:
            db_logger.warning(f"Rejected tags: {rejected_tags[:10]}...")  # Show first 10
        
        # Batch normalize all valid tags using more efficient comprehension
        tag_normalization_cache = {
            tag: normalized 
            for tag in valid_tags 
            if (normalized := _tag_normalizer.normalize(tag)) is not None
        }
        
        db_logger.info(f"Normalized {len(tag_normalization_cache)} tags")
        
        phase_time = (datetime.now() - phase_start).total_seconds()
        performance_logger.info(f"[PERF] Phase 2 completed in {phase_time:.2f}s")
        if perf_monitor:
            perf_monitor.complete_operation("Tag Processing", len(tag_normalization_cache))

        # === PHASE 3: Batch Database Operations ===
        phase_start = datetime.now()
        db_logger.info("Phase 3: Batch database operations...")
        if perf_monitor:
            perf_monitor.start_operation("Database Operations")
        
        # Get all existing tags in one query
        unique_normalized_tags = set(tag_normalization_cache.values())
        existing_tags_query = session.query(Tag).filter(Tag.normalized_name.in_(unique_normalized_tags)).all()
        existing_tags_map = {tag.normalized_name: tag for tag in existing_tags_query}
        
        db_logger.info(f"Found {len(existing_tags_map)} existing tags in database")
        
        # Prepare new tags to create as dictionaries for bulk insert
        new_tags_to_insert = []
        new_tag_objects = {}  # Track new tags for tags_map
        tags_map = existing_tags_map.copy()  # Will contain all tags (existing + new)
        
        for normalized_tag in unique_normalized_tags:
            if normalized_tag not in existing_tags_map:
                tag_id = str(uuid.uuid4())
                new_tags_to_insert.append({
                    'id': tag_id,
                    'name': normalized_tag,
                    'normalized_name': normalized_tag,
                    'is_canonical': 1
                })
                # Create a minimal Tag object for relationship tracking
                tag_obj = Tag(id=tag_id, name=normalized_tag, normalized_name=normalized_tag, is_canonical=1)
                new_tag_objects[normalized_tag] = tag_obj
                tags_map[normalized_tag] = tag_obj
        
        # Bulk insert new tags using bulk_insert_mappings (faster than add_all)
        if new_tags_to_insert:
            session.bulk_insert_mappings(Tag, new_tags_to_insert)
            db_logger.info(f"Created {len(new_tags_to_insert)} new tags")
        
        phase_time = (datetime.now() - phase_start).total_seconds()
        performance_logger.info(f"[PERF] Phase 3 completed in {phase_time:.2f}s")
        if perf_monitor:
            perf_monitor.complete_operation("Database Operations", len(new_tags_to_insert))

        # === PHASE 4: Batch Album Creation ===
        phase_start = datetime.now()
        db_logger.info("Phase 4: Batch album creation...")
        if perf_monitor:
            perf_monitor.start_operation("Album Creation")
        
        # Use dictionaries for bulk insert - much faster than ORM objects
        albums_to_insert = []
        album_tag_associations = []  # List of dicts for album_tags association table
        album_id_map = {}  # idx -> album_id for relationship tracking
        
        # Pre-compute tag ID lookups for better performance in inner loop
        tag_id_cache = {normalized_tag: tag_obj.id for normalized_tag, tag_obj in tags_map.items()}
        
        current_time = datetime.now()
        for idx, row in df_new.iterrows():
            artist = row['artist_clean']
            album_title = row['album_clean']
            
            # Parse release date
            release_date_str = row.get('release date', '')
            if pd.isna(release_date_str):
                release_date_str = ''
            
            release_date_obj, release_year = _parse_release_date_optimized(
                release_date_str, row.get('_source_file', '')
            )
            
            # Get other fields
            genre_and_tags_str = row.get('genre / subgenres', '') or row.get('genre', '') or row.get('genres', '')
            country_str = row.get('country / state', '') or row.get('country', '')
            vocal_style_tags = row_vocal_style_tags.get(idx, [])
            vocal_style_display = row_vocal_style_display.get(idx, '')
            
            if pd.isna(genre_and_tags_str):
                genre_and_tags_str = ''
            if pd.isna(country_str):
                country_str = ''
            combined_raw_tags = build_raw_tags_string(genre_and_tags_str, vocal_style_tags)
            
            # Create album as dictionary for bulk insert
            album_id = str(uuid.uuid4())
            album_id_map[idx] = album_id
            
            album_dict = {
                'id': album_id,
                'pa_artist_name_on_album': artist,
                'title': album_title,
                'release_date': release_date_obj,
                'release_year': release_year,
                'vocal_style': vocal_style_display or None,
                'genre': genre_and_tags_str,
                'country': country_str,
                'raw_tags': combined_raw_tags,
                'last_updated': current_time
            }
            albums_to_insert.append(album_dict)
            
            # Prepare tag relationships as dictionaries using pre-computed cache
            row_raw_tags = row_tag_mapping.get(idx, [])
            album_tags = set()
            
            for raw_tag in row_raw_tags:
                normalized_tag = tag_normalization_cache.get(raw_tag)
                if normalized_tag and normalized_tag in tag_id_cache and normalized_tag not in album_tags:
                    album_tags.add(normalized_tag)
                    album_tag_associations.append({
                        'album_id': album_id,
                        'tag_id': tag_id_cache[normalized_tag]
                    })
        
        # Bulk insert albums using bulk_insert_mappings (much faster than add_all)
        if albums_to_insert:
            session.bulk_insert_mappings(Album, albums_to_insert)
            db_logger.info(f"Created {len(albums_to_insert)} new albums")
        
        # Bulk insert album-tag relationships using raw SQL for maximum performance
        if album_tag_associations:
            # Use executemany for bulk insert into association table
            from sqlalchemy import text as sql_text
            insert_stmt = sql_text(
                "INSERT INTO album_tags (album_id, tag_id) VALUES (:album_id, :tag_id)"
            )
            session.execute(insert_stmt, album_tag_associations)
            db_logger.info(f"Created {len(album_tag_associations)} album-tag relationships")
        
        phase_time = (datetime.now() - phase_start).total_seconds()
        performance_logger.info(f"[PERF] Phase 4 completed in {phase_time:.2f}s")
        if perf_monitor:
            perf_monitor.complete_operation("Album Creation", len(albums_to_insert))

        # === PHASE 5: Final Commit ===
        phase_start = datetime.now()
        db_logger.info("Phase 5: Final commit...")
        
        session.commit()
        
        phase_time = (datetime.now() - phase_start).total_seconds()
        performance_logger.info(f"[PERF] Phase 5 completed in {phase_time:.2f}s")

        # === SUMMARY ===
        total_time = (datetime.now() - start_time).total_seconds()
        total_tags = session.query(Tag).count()
        
        db_logger.info(f"Optimized data loading completed successfully in {total_time:.2f} seconds")
        db_logger.info(f"Processed {len(albums_to_create)} new albums. Total tags in database: {total_tags}")
        performance_logger.info(f"[PERF] Total optimized load time: {total_time:.2f}s for {len(albums_to_create)} albums")
        
        # Complete overall performance monitoring
        if perf_monitor:
            perf_monitor.complete_operation("Optimized Data Loading", len(albums_to_create))

    except Exception as e:
        session.rollback()
        db_logger.error(f"Error in optimized data loading: {str(e)}", exc_info=True)
        raise
    finally:
        session.close()


def _parse_release_date_optimized(release_date_str: str, source_file: str = '') -> Tuple[datetime, int]:
    """Optimized release date parsing with caching potential."""
    if not release_date_str:
        # Try to extract year from source file
        if source_file:
            year_match = _YEAR_PATTERN.search(source_file)
            if year_match:
                year = int(year_match.group())
                return datetime(year, 1, 1), year
        return None, None
    
    release_date_str = str(release_date_str).strip()
    
    # ISO date format (YYYY-MM-DD)
    if re.match(r'^\d{4}-\d{2}-\d{2}$', release_date_str):
        try:
            date_obj = datetime.strptime(release_date_str, '%Y-%m-%d')
            return date_obj, date_obj.year
        except ValueError:
            pass
    
    # Extract year from any format using pre-compiled pattern
    year_match = _YEAR_PATTERN.search(release_date_str)
    if year_match:
        year = int(year_match.group())
        
        # Month + day format (e.g., "Jan 1", "Feb 23")
        month_day_match = re.match(r'^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}$', release_date_str, re.IGNORECASE)
        if month_day_match:
            try:
                date_with_year = f"{release_date_str} {year}"
                date_obj = datetime.strptime(date_with_year, '%b %d %Y')
                return date_obj, year
            except ValueError:
                pass
        
        # Default to January 1st of the year
        return datetime(year, 1, 1), year
    
    # If no year found, try source file
    if source_file:
        year_match = re.search(r'20\d{2}', source_file)
        if year_match:
            year = int(year_match.group())
            return datetime(year, 1, 1), year
    
    return None, None


def benchmark_data_loading(df: pd.DataFrame, session: Session) -> Dict[str, float]:
    """Benchmark both original and optimized data loading methods."""
    from albumexplore.database.csv_loader import load_dataframe_data
    
    # Create a smaller sample for benchmarking
    sample_size = min(100, len(df))
    df_sample = df.head(sample_size).copy()
    
    results = {}
    
    # Clear database for fair comparison
    session.query(Album).delete()
    session.query(Tag).delete()
    session.commit()
    
    # Benchmark original method
    start_time = datetime.now()
    try:
        load_dataframe_data(df_sample, session)
        original_time = (datetime.now() - start_time).total_seconds()
        results['original'] = original_time
        db_logger.info(f"Original method: {original_time:.2f}s for {sample_size} rows")
    except Exception as e:
        db_logger.error(f"Original method failed: {e}")
        results['original'] = -1
    
    # Clear database again
    session.query(Album).delete()
    session.query(Tag).delete()
    session.commit()
    
    # Benchmark optimized method
    start_time = datetime.now()
    try:
        load_dataframe_data_optimized(df_sample, session)
        optimized_time = (datetime.now() - start_time).total_seconds()
        results['optimized'] = optimized_time
        db_logger.info(f"Optimized method: {optimized_time:.2f}s for {sample_size} rows")
    except Exception as e:
        db_logger.error(f"Optimized method failed: {e}")
        results['optimized'] = -1
    
    # Calculate improvement
    if results['original'] > 0 and results['optimized'] > 0:
        improvement = ((results['original'] - results['optimized']) / results['original']) * 100
        results['improvement_percent'] = improvement
        db_logger.info(f"Performance improvement: {improvement:.1f}%")
    
    return results
