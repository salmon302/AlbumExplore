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

# Initialize advanced tag normalizer and validator
_tag_normalizer = TagNormalizer()
_tag_validator = TagValidationFilter(strict_mode=False)

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
        
        # Filter out duplicates
        df_clean['artist_clean'] = df_clean['artist'].astype(str).str.strip()
        df_clean['album_clean'] = df_clean['album'].astype(str).str.strip()
        df_clean['is_duplicate'] = df_clean.apply(
            lambda row: (row['artist_clean'], row['album_clean']) in existing_albums, axis=1
        )
        
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
        
        # Collect all unique tags from all rows
        all_raw_tags = set()
        row_tag_mapping = {}  # row_index -> list of normalized tags
        
        for idx, row in df_new.iterrows():
            genre_and_tags_str = row.get('genre / subgenres', '') or row.get('genre', '') or row.get('genres', '')
            country_str = row.get('country / state', '') or row.get('country', '')
            
            # Handle NaN values
            if pd.isna(genre_and_tags_str):
                genre_and_tags_str = ''
            if pd.isna(country_str):
                country_str = ''
            
            # Extract tags
            row_tags = []
            if genre_and_tags_str:
                raw_tags = [tag.strip() for tag in re.split(r'[;,]', str(genre_and_tags_str)) if tag.strip()]
                all_raw_tags.update(raw_tags)
                row_tags.extend(raw_tags)
            
            if country_str:
                countries = [c.strip() for c in re.split(r'[;,]', str(country_str)) if c.strip()]
                all_raw_tags.update(countries)
                row_tags.extend(countries)
            
            row_tag_mapping[idx] = row_tags
        
        db_logger.info(f"Collected {len(all_raw_tags)} unique raw tags across all rows")
        
        # Batch validate all tags
        context = {'source': 'dataframe_import_batch'}
        all_tags_list = list(all_raw_tags)
        valid_tags, rejected_tags, validation_info = _tag_validator.filter_tags(all_tags_list, context)
        
        db_logger.info(f"Tag validation: {len(valid_tags)} valid, {len(rejected_tags)} rejected")
        if rejected_tags:
            db_logger.warning(f"Rejected tags: {rejected_tags[:10]}...")  # Show first 10
        
        # Batch normalize all valid tags
        tag_normalization_cache = {}
        for tag in valid_tags:
            normalized = _tag_normalizer.normalize(tag)
            if normalized:
                tag_normalization_cache[tag] = normalized
        
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
        
        # Prepare new tags to create
        new_tags_to_create = []
        tags_map = existing_tags_map.copy()  # Will contain all tags (existing + new)
        
        for normalized_tag in unique_normalized_tags:
            if normalized_tag not in existing_tags_map:
                new_tag = Tag(
                    id=str(uuid.uuid4()),
                    name=normalized_tag,
                    normalized_name=normalized_tag,
                    is_canonical=1
                )
                new_tags_to_create.append(new_tag)
                tags_map[normalized_tag] = new_tag
        
        # Batch insert new tags
        if new_tags_to_create:
            session.add_all(new_tags_to_create)
            session.flush()  # Get IDs for new tags
            db_logger.info(f"Created {len(new_tags_to_create)} new tags")
        
        phase_time = (datetime.now() - phase_start).total_seconds()
        performance_logger.info(f"[PERF] Phase 3 completed in {phase_time:.2f}s")
        if perf_monitor:
            perf_monitor.complete_operation("Database Operations", len(new_tags_to_create))

        # === PHASE 4: Batch Album Creation ===
        phase_start = datetime.now()
        db_logger.info("Phase 4: Batch album creation...")
        if perf_monitor:
            perf_monitor.start_operation("Album Creation")
        
        albums_to_create = []
        album_tag_relationships = []  # List of (album_id, tag_id) tuples
        
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
            
            if pd.isna(genre_and_tags_str):
                genre_and_tags_str = ''
            if pd.isna(country_str):
                country_str = ''
            
            # Create album
            album_id = str(uuid.uuid4())
            album = Album(
                id=album_id,
                pa_artist_name_on_album=artist,
                title=album_title,
                release_date=release_date_obj,
                release_year=release_year,
                genre=genre_and_tags_str,
                country=country_str,
                raw_tags=genre_and_tags_str,
                last_updated=datetime.now()
            )
            albums_to_create.append(album)
            
            # Prepare tag relationships
            row_raw_tags = row_tag_mapping.get(idx, [])
            album_tags = set()
            
            for raw_tag in row_raw_tags:
                if raw_tag in tag_normalization_cache:
                    normalized_tag = tag_normalization_cache[raw_tag]
                    if normalized_tag in tags_map and normalized_tag not in album_tags:
                        album_tags.add(normalized_tag)
                        tag_obj = tags_map[normalized_tag]
                        album_tag_relationships.append((album, tag_obj))
        
        # Batch insert albums
        session.add_all(albums_to_create)
        session.flush()  # Get IDs for albums
        
        db_logger.info(f"Created {len(albums_to_create)} new albums")
        
        # Batch create tag relationships
        for album, tag in album_tag_relationships:
            album.tags.append(tag)
        
        db_logger.info(f"Created {len(album_tag_relationships)} album-tag relationships")
        
        phase_time = (datetime.now() - phase_start).total_seconds()
        performance_logger.info(f"[PERF] Phase 4 completed in {phase_time:.2f}s")
        if perf_monitor:
            perf_monitor.complete_operation("Album Creation", len(albums_to_create))

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
            year_match = re.search(r'20\d{2}', source_file)
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
    
    # Extract year from any format
    year_match = re.search(r'20\d{2}', release_date_str)
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
