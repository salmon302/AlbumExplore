"""
Extractor Configured for Hybrid Pipeline Data (Artist HTMLs -> CSVs).
"""
import os
import pandas as pd
import logging
import glob
import re
import argparse
from pathlib import Path
from albumexplore.scraping.progarchives.parser import ProgArchivesParser

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Columns (Must match transformer.py expectations)
ALBUM_COLS = ['pa_album_id', 'raw_album_title', 'raw_artist_name', 'raw_release_year',
              'raw_recording_type', 'raw_subgenre_string', 'pa_average_rating',
              'pa_rating_count', 'pa_review_count',
              'pa_cover_image_url', 'pa_artist_page_link', 'pa_all_reviews_page_link', 'source_html_file']
ARTIST_COLS = ['pa_artist_id', 'raw_artist_name_canonical', 'raw_artist_country', 
               'raw_artist_style_main', 'raw_artist_style_secondary', 'raw_artist_status',
               'pa_artist_page_link_original', 'raw_artist_formation_year',
               'raw_artist_location', 'raw_artist_related_artists_summary',
               'raw_artist_lineup_current_summary', 'raw_artist_lineup_past_summary',
               'raw_artist_biography_summary']
TRACK_COLS = ['pa_album_id', 'raw_track_number', 'raw_track_title', 'raw_track_duration',
              'is_subtrack', 'parent_track_number', 'is_bonus_track']
# We won't have reviews or lineups per album from Artist pages mostly, but we create empty DFs
REVIEW_COLS = ['pa_album_id', 'raw_reviewer_name', 'raw_review_rating', 'raw_review_text', 'raw_review_date']
LINEUP_COLS = ['pa_album_id', 'raw_musician_name', 'raw_instruments_roles', 'is_guest']
SUBGENRE_COLS = ['raw_subgenre_name', 'raw_subgenre_definition']

def run_extraction(input_dir: str, output_dir: str):
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Scanning {input_path} for artist HTML files...")
    
    # Try finding in root or artists/ subdir
    artist_files = list(input_path.glob("artist*.html"))
    if not artist_files:
        artist_files = list((input_path / "artists").glob("artist*.html"))
        if artist_files:
             # Update scraper root if we fell into a subdir
             input_path = input_path / "artists"
    
    logger.info(f"Found {len(artist_files)} artist files.")
    
    scraper = ProgArchivesParser(local_data_root=input_path)
    
    all_albums = []
    all_artists = []
    all_tracks = []
    all_reviews = []
    all_lineups = []
    
    seen_artists = set()
    processed_albums = set()

    # 1. Process Artist Files
    for f in artist_files:
        try:
            # Parse Artist
            # Filename example: artist_123.html
            pa_artist_id = f.stem.replace('artist_', '').replace('artist', '')
            
            details = scraper.get_band_details(f)
            if 'error' in details:
                logger.warning(f"Error parsing {f}: {details['error']}")
                continue
                
            artist_name = details.get('name')
            if not artist_name:
                continue
                
            # Artist Data
            if artist_name not in seen_artists:
                all_artists.append({
                    'pa_artist_id': pa_artist_id,
                    'raw_artist_name_canonical': artist_name,
                    'raw_artist_country': details.get('country'),
                    'raw_artist_style_main': details.get('genre'),
                    'raw_artist_biography_summary': details.get('biography'),
                    # Defaults
                    'raw_artist_style_secondary': '',
                    'raw_artist_status': '',
                    'pa_artist_page_link_original': f.name,
                    'raw_artist_formation_year': '',
                    'raw_artist_location': '',
                    'raw_artist_related_artists_summary': '',
                    'raw_artist_lineup_current_summary': '',
                    'raw_artist_lineup_past_summary': ''
                })
                seen_artists.add(artist_name)
            
            # Album Data (Discography)
            for alb in details.get('albums', []):
                # We need to generate a PA ID. 
                # If local_path is like "album_123.html", extract ID.
                # If it's relative "album123.html", extract ID.
                # But 'local_path' from parser might comprise folders.
                alb_path = alb.get('local_path', '')
                alb_id_match = re.search(r'album[_-]?(\d+)', alb_path)
                pa_album_id = alb_id_match.group(1) if alb_id_match else f"gen_{hash(alb['title'])}"
                
                all_albums.append({
                    'pa_album_id': pa_album_id,
                    'raw_album_title': alb.get('title'),
                    'raw_artist_name': artist_name,
                    'raw_release_year': alb.get('year'),
                    'raw_recording_type': alb.get('type'),
                    'pa_average_rating': alb.get('rating'),
                    # Defaults
                    'raw_subgenre_string': details,
                    'source_html_file': f.name # Fallback to artist file if we don't have album file yet
                })
                
        except Exception as e:
            logger.error(f"Failed to process artist file {f.name}: {e}")

    # 2. Process Album Files (for richer data)
    album_files = list(input_path.glob("album*.html"))
    logger.info(f"Found {len(album_files)} album files. Processing details...")

    for f in album_files:
        try:
            # Extract PA Album ID from filename
            pa_album_id_match = re.search(r'album[_-]?(\d+)', f.name)
            pa_album_id = pa_album_id_match.group(1) if pa_album_id_match else f"gen_{hash(f.name)}"
            
            data = scraper.get_album_data(f)
            if 'error' in data:
                logger.warning(f"Error parsing album {f}: {data['error']}")
                continue

            # Update/Add Album Record
            # We prioritize this data over what we got from the artist page
            
            # Remove simplified entry if exists (from artist loop) to replace with detailed one
            # Using list comprehension to filter might be slow, but for now reasonable
            # Optimization: Use a dictionary keyed by pa_album_id instead of list for all_albums
            
            # Prepare detailed record
            detailed_album = {
                'pa_album_id': pa_album_id,
                'raw_album_title': data.get('album_title'),
                'raw_artist_name': data.get('artist_name'), # We might need to ensure this matches canonical artist name
                'raw_release_year': data.get('year'),
                'raw_recording_type': data.get('album_type'),
                'pa_average_rating': data.get('rating_value'),
                'pa_rating_count': data.get('rating_count'),
                'pa_review_count': data.get('review_count'),
                'pa_cover_image_url': data.get('cover_image_url'),
                'raw_subgenre_string': data.get('genre'),
                'pa_artist_page_link': data.get('artist_page_link_local'),
                'pa_all_reviews_page_link': '',
                'source_html_file': f.name
            }
            
            # Since we maintain a flat list, we'll append. 
            # Ideally the transformer handles deduplication/updates, but let's filter the generic one from artist pass if we can.
            # Actually, `processed_albums` set helps us track what we have detailed info for.
            all_albums.append(detailed_album)
            processed_albums.add(pa_album_id)

            # Tracks
            for trk in data.get('tracks', []):
                all_tracks.append({
                    'pa_album_id': pa_album_id,
                    'raw_track_number': trk.get('number'),
                    'raw_track_title': trk.get('title'),
                    'raw_track_duration': trk.get('duration'),
                    'is_subtrack': trk.get('is_sub_track'),
                    'parent_track_number': '', # Parser logic for parent not fully exposed in list dict yet
                    'is_bonus_track': ''
                })

            # Lineup
            for musician in data.get('lineup', []):
                all_lineups.append({
                    'pa_album_id': pa_album_id,
                    'raw_musician_name': musician.get('musician'),
                    'raw_instruments_roles': musician.get('instruments'),
                    'is_guest': musician.get('is_guest')
                })

            # Reviews
            for rev in data.get('reviews', []):
                all_reviews.append({
                    'pa_album_id': pa_album_id,
                    'raw_reviewer_name': rev.get('reviewer'),
                    'raw_review_rating': rev.get('rating'),
                    'raw_review_text': rev.get('text'),
                    'raw_review_date': rev.get('date')
                })

        except Exception as e:
            logger.error(f"Failed to process album file {f.name}: {e}")

    # Convert to DataFrames
    # Deduplicate albums (keep detailed ones)
    df_albums = pd.DataFrame(all_albums, columns=ALBUM_COLS)
    # If duplicates exist (same ID), drop the one from Source HTML = artist_*.html if one exists from album_*.html
    # We can sort by source_html_file descending (album_*.html > artist_*.html lexicographically? No.)
    # Better: explicit dedup logic.
    # Group by ID, pick the one where source_html_file starts with 'album' if available.
    if not df_albums.empty:
        df_albums['is_detailed'] = df_albums['source_html_file'].str.startswith('album')
        df_albums = df_albums.sort_values('is_detailed', ascending=False).drop_duplicates('pa_album_id').drop('is_detailed', axis=1)

    # Save
    df_albums.to_csv(output_path / "pa_raw_albums.csv", index=False)
    pd.DataFrame(all_artists, columns=ARTIST_COLS).to_csv(output_path / "pa_raw_artists.csv", index=False)
    
    # Save populated details
    pd.DataFrame(all_tracks, columns=TRACK_COLS).to_csv(output_path / "pa_raw_tracks.csv", index=False)
    pd.DataFrame(all_reviews, columns=REVIEW_COLS).to_csv(output_path / "pa_raw_reviews.csv", index=False)
    pd.DataFrame(all_lineups, columns=LINEUP_COLS).to_csv(output_path / "pa_raw_lineups.csv", index=False)
    
    # Subgenres (unchanged logic for now as mostly staticdex=False)
    # Empty CSVs for tracks/reviews to satisfy transformer - ONLY for subgenres which we don't extract yet
    pd.DataFrame([], columns=SUBGENRE_COLS).to_csv(output_path / "pa_raw_subgenre_definitions.csv", index=False)
    
    logger.info(f"Extraction complete. Saved to {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    run_extraction(args.input_dir, args.output_dir)
