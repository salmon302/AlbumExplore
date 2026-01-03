"""
Parser for ProgArchives HTML files.
Walks the raw_data directory, parses album HTML files, and outputs CSVs.
"""
import os
import logging
import pandas as pd
import re
from pathlib import Path
from typing import List, Dict
import argparse

from albumexplore.scraping.progarchives_scraper import ProgArchivesScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# CSV Column Definitions
ALBUM_COLS = ['pa_album_id', 'raw_album_title', 'raw_artist_name', 'raw_release_year',
              'raw_recording_type', 'raw_subgenre_string', 'pa_average_rating',
              'pa_rating_count', 'pa_review_count',
              'pa_cover_image_url', 'pa_artist_page_link', 'pa_all_reviews_page_link']

TRACK_COLS = ['pa_album_id', 'raw_track_number', 'raw_track_title', 'raw_track_duration',
              'is_subtrack', 'parent_track_number', 'is_bonus_track']

REVIEW_COLS = ['pa_album_id', 'raw_reviewer_name', 'raw_review_rating', 'raw_review_text', 'raw_review_date']

LINEUP_COLS = ['pa_album_id', 'raw_musician_name', 'raw_instruments_roles', 'is_guest']

SUBGENRE_COLS = ['raw_subgenre_name', 'raw_subgenre_definition']

def parse_subgenre_file(file_path: Path):
    """
    Parses the ProgArchives subgenre definitions file.
    The file format is expected to have subgenre names in all caps with their definitions following.
    """
    subgenres = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split the content by two or more newlines to get individual subgenre blocks
        blocks = re.split(r'\n\s*\n+', content.strip())
        
        title_pattern = r'^([A-Z][A-Z\s/-]+)(?:\n|:)'
        
        for i, block_text in enumerate(blocks):
            block_text = block_text.strip()
            if not block_text:
                continue

            match = re.match(title_pattern, block_text)
            
            if match:
                subgenre_name = match.group(1).strip()
                
                if subgenre_name == "FOOTNOTE":
                    continue

                definition_text = block_text[match.end():].strip()
                
                lines = definition_text.splitlines()
                cleaned_lines = []
                for line in lines:
                    line_lower = line.strip().lower()
                    if not line_lower.startswith("a progressive rock sub-genre") and \
                       not line_lower.startswith("from progarchives.com") and \
                       not line_lower.endswith("definition") and \
                       line.strip():
                        cleaned_lines.append(line.strip())
                definition_text = "\n".join(cleaned_lines).strip()

                subgenres.append({
                    'raw_subgenre_name': subgenre_name,
                    'raw_subgenre_definition': definition_text
                })
        
        logger.info(f"Parsed {len(subgenres)} subgenre definitions from {file_path}")
        
    except FileNotFoundError:
        logger.warning(f"Subgenre definition file not found: {file_path}")
    except Exception as e:
        logger.error(f"Error parsing subgenre file {file_path}: {e}", exc_info=True)
    
    return subgenres

def parse_directory(input_dir: Path, output_dir: Path):
    """
    Recursively parse all album HTML files in input_dir and save CSVs to output_dir.
    """
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    scraper = ProgArchivesScraper(local_data_root=input_dir)
    
    all_albums_data = []
    all_tracks_data = []
    all_reviews_data = []
    all_lineups_data = []
    
    # Find all album HTML files
    # Matches album_*.html (new crawler) and album*.html (legacy)
    album_files = list(input_dir.rglob("album*.html"))
    # Filter out album-reviews files
    album_files = [f for f in album_files if "album-reviews" not in f.name]
    
    logger.info(f"Found {len(album_files)} album files to process in {input_dir}")
    
    for i, album_file in enumerate(album_files):
        try:
            logger.info(f"Processing {i+1}/{len(album_files)}: {album_file.name}")
            
            # Extract ID from filename
            # album_123.html -> 123
            # album123.html -> 123
            stem = album_file.stem
            if stem.startswith("album_"):
                album_id = stem.replace("album_", "")
            else:
                album_id = stem.replace("album", "")
            
            # Parse data
            parsed_data = scraper.get_album_data(album_file)
            
            if not parsed_data or 'error' in parsed_data:
                logger.error(f"Failed to parse {album_file}: {parsed_data.get('error')}")
                continue
                
            # 1. Album Data
            album_info = {
                'pa_album_id': album_id,
                'raw_album_title': parsed_data.get('album_title', ''),
                'raw_artist_name': parsed_data.get('artist_name', ''),
                'raw_release_year': parsed_data.get('year'),
                'raw_recording_type': parsed_data.get('album_type', ''),
                'raw_subgenre_string': parsed_data.get('genre', ''),
                'pa_average_rating': parsed_data.get('rating_value'),
                'pa_rating_count': parsed_data.get('rating_count'),
                'pa_review_count': parsed_data.get('review_count'),
                'pa_cover_image_url': parsed_data.get('cover_image_url', ''),
                'pa_artist_page_link': parsed_data.get('artist_page_link_local', ''),
                'pa_all_reviews_page_link': '' # Not currently extracted by scraper in this field
            }
            all_albums_data.append(album_info)
            
            # 2. Tracks
            if 'tracks' in parsed_data and parsed_data['tracks']:
                for track in parsed_data['tracks']:
                    all_tracks_data.append({
                        'pa_album_id': album_id,
                        'raw_track_number': track.get('number'),
                        'raw_track_title': track.get('title'),
                        'raw_track_duration': track.get('duration'),
                        'is_subtrack': track.get('is_sub_track', False),
                        'parent_track_number': None, # Logic for parent track could be added
                        'is_bonus_track': False # Logic for bonus track could be added
                    })
            
            # 3. Reviews
            if 'reviews' in parsed_data and parsed_data['reviews']:
                for review in parsed_data['reviews']:
                    all_reviews_data.append({
                        'pa_album_id': album_id,
                        'raw_reviewer_name': review.get('reviewer'),
                        'raw_review_rating': review.get('rating'),
                        'raw_review_text': review.get('text'),
                        'raw_review_date': review.get('date')
                    })
                    
            # 4. Lineup
            if 'lineup' in parsed_data and parsed_data['lineup']:
                for member in parsed_data['lineup']:
                    all_lineups_data.append({
                        'pa_album_id': album_id,
                        'raw_musician_name': member.get('musician'),
                        'raw_instruments_roles': member.get('instruments'),
                        'is_guest': False # Logic for guest could be added
                    })
                    
        except Exception as e:
            logger.error(f"Exception processing {album_file}: {e}", exc_info=True)

    # Save to CSV
    logger.info(f"Saving parsed data to {output_dir}")
    
    pd.DataFrame(all_albums_data, columns=ALBUM_COLS).to_csv(
        output_dir / "pa_raw_albums.csv", index=False
    )
    pd.DataFrame(all_tracks_data, columns=TRACK_COLS).to_csv(
        output_dir / "pa_raw_tracks.csv", index=False
    )
    pd.DataFrame(all_reviews_data, columns=REVIEW_COLS).to_csv(
        output_dir / "pa_raw_reviews.csv", index=False
    )
    pd.DataFrame(all_lineups_data, columns=LINEUP_COLS).to_csv(
        output_dir / "pa_raw_lineups.csv", index=False
    )
    
    # Parse and save subgenres
    # Assuming the subgenre file is in a standard location relative to the project root
    # or we can look for it in the input_dir or a parent of it.
    # For now, let's try to find "ProgSubgenres" in "ProgArchives Data" relative to CWD
    subgenre_file = Path("ProgArchives Data/ProgSubgenres")
    if subgenre_file.exists():
        subgenres_data = parse_subgenre_file(subgenre_file)
        pd.DataFrame(subgenres_data, columns=SUBGENRE_COLS).to_csv(
            output_dir / "pa_raw_subgenre_definitions.csv", index=False
        )
    else:
        # Create empty DataFrame if file not found to prevent transformer errors
        logger.warning(f"Subgenre file not found at {subgenre_file}. Creating empty subgenre CSV.")
        pd.DataFrame([], columns=SUBGENRE_COLS).to_csv(
            output_dir / "pa_raw_subgenre_definitions.csv", index=False
        )
    
    # Create empty artists CSV if not present (since we don't parse artists yet)
    # Transformer expects pa_raw_artists.csv
    pd.DataFrame([], columns=['pa_artist_id', 'raw_artist_name_canonical']).to_csv(
        output_dir / "pa_raw_artists.csv", index=False
    )

    logger.info("Parsing complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse ProgArchives HTML files")
    parser.add_argument("--input-dir", default="raw_data/progarchives", help="Input directory containing HTML files")
    parser.add_argument("--output-dir", default="raw_data/progarchives/parsed", help="Output directory for CSV files")
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    
    args = parser.parse_args()
    
    logging.getLogger().setLevel(getattr(logging, args.log_level.upper()))
    
    parse_directory(args.input_dir, args.output_dir)
