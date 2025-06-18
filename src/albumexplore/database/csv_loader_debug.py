"""CSV data loader for album database with more detailed debugging."""
import csv
import os
from pathlib import Path
from typing import Dict, Set, List
from datetime import datetime
import re
import uuid
import time  # Added for sleep between processing
import traceback

from albumexplore.database import get_session
from albumexplore.database.models import Album, Tag, TagCategory
from albumexplore.gui.gui_logging import db_logger

def load_csv_data_with_debug(csv_dir: Path) -> None:
    """Load data from CSV files into database with detailed logging."""
    db_logger.info(f"Starting enhanced CSV data loading from {csv_dir}")
    
    start_time = datetime.now()
    db_logger.info(f"CSV loading started at {start_time.strftime('%H:%M:%S')}")
    
    session = get_session()
    try:
        # Count how many CSV files we need to process
        csv_files = list(csv_dir.glob('*.csv'))
        total_files = len(csv_files)
        db_logger.info(f"Found {total_files} CSV files to process")
        
        # Track processed albums by artist/title to detect duplicates
        processed_albums = {}
        
        # Process each CSV file
        for i, csv_file in enumerate(csv_files):
            try:
                year = extract_year(csv_file.name)
                if year:
                    db_logger.info(f"Processing file {i+1} of {total_files}: {csv_file.name} for year {year}")
                    
                    # Process file with regular error handling
                    try:
                        # Try to read headers to verify file is readable
                        with open(csv_file, 'r', encoding='utf-8') as f:
                            first_few_lines = ''.join([next(f) for _ in range(min(20, sum(1 for _ in open(csv_file))))])
                            db_logger.debug(f"First few lines of {csv_file.name}:\n{first_few_lines}")
                        
                        # If we get here, file is readable
                        db_logger.info(f"File {csv_file.name} is readable, proceeding with processing")
                        
                        # Process the file
                        from albumexplore.database.csv_loader import _process_csv_file
                        result = _process_csv_file(csv_file, year, session)
                        
                        # Add processed albums to our tracking dictionary
                        if hasattr(result, 'get') and result.get('albums'):
                            for album_info in result.get('albums', []):
                                key = f"{album_info['artist']}|{album_info['title']}"
                                if key in processed_albums:
                                    db_logger.warning(f"Duplicate album detected: {album_info['artist']} - {album_info['title']} (Original ID: {processed_albums[key]}, New ID: {album_info['id']})")
                                else:
                                    processed_albums[key] = album_info['id']
                        
                        # Try to commit after each file
                        try:
                            session.commit()
                            db_logger.info(f"Successfully committed changes for file {csv_file.name}")
                        except Exception as commit_err:
                            session.rollback()
                            db_logger.error(f"Error committing changes for file {csv_file.name}: {str(commit_err)}")
                            db_logger.error(f"Error details: {traceback.format_exc()}")
                        
                        # Add a small delay between files to make debugging easier
                        time.sleep(0.1)
                        
                    except Exception as file_error:
                        db_logger.error(f"Error processing file {csv_file.name}: {str(file_error)}", exc_info=True)
                        continue
                    
                    db_logger.info(f"Completed processing file {i+1} of {total_files}: {csv_file.name}")
            except Exception as e:
                db_logger.error(f"Critical error processing {csv_file}: {str(e)}", exc_info=True)
        
        # Final commit
        try:
            session.commit()
            db_logger.info("All CSV files processed and committed successfully")
        except Exception as e:
            session.rollback()
            db_logger.error(f"Error in final commit: {str(e)}", exc_info=True)
            db_logger.error(f"Error details: {traceback.format_exc()}")
        
        end_time = datetime.now()
        processing_time = end_time - start_time
        db_logger.info(f"CSV data loading completed at {end_time.strftime('%H:%M:%S')}")
        db_logger.info(f"Total processing time: {processing_time.total_seconds():.2f} seconds")
        
        # Check for problematic albums
        check_problematic_albums(session)
        
    except Exception as e:
        session.rollback()
        db_logger.error(f"Fatal error loading CSV data: {str(e)}", exc_info=True)
        raise
    finally:
        session.close()
        db_logger.info("Session closed")

def check_problematic_albums(session) -> None:
    """Check if the problematic albums were loaded successfully."""
    db_logger.info("Checking for problematic albums...")
    
    problematic_artists = [
        "Empire State Bastard", 
        "Rusty Bonez", 
        "Ihsahn", 
        "Black Country Communion", 
        "Moron Police"
    ]
    
    for artist in problematic_artists:
        albums = session.query(Album).filter(Album.artist == artist).all()
        if albums:
            for album in albums:
                db_logger.info(f"Found album: {album.artist} - {album.title} (ID: {album.id}, Release Date: {album.release_date.strftime('%Y-%m-%d') if album.release_date else 'None'})")
        else:
            db_logger.warning(f"No albums found for artist: {artist}")

def extract_year(filename: str) -> int:
    """Extract year from filename."""
    match = re.search(r'20\d{2}', filename)
    return int(match.group()) if match else None
