"""
Orchestrator script for Phase 2: Data Extraction from ProgArchives.
Parses HTML files and the subgenre definitions text file to produce
intermediate raw CSV files.
"""
import os
import pandas as pd
import logging
import glob
import re # For potential use in parsing
from pathlib import Path # Ensure Path is imported

# Import the scraper
from albumexplore.scraping.progarchives_scraper import ProgArchivesScraper

# --- Configuration ---
PROGARCHIVES_HTML_BASE_DIR = "ProgArchives Data/Website/ProgArchives/www.progarchives.com/"
PROGARCHIVES_SUBGENRE_FILE = "ProgArchives Data/ProgSubgenres" # Path to the subgenre definitions
RAW_DATA_OUTPUT_DIR = "./raw_data/"  # Output directory for CSVs
# Ensure log file is created in the same directory as the script
LOG_FILE_PATH = os.path.join(os.path.dirname(__file__), "orchestrator_debug.log")
# print(f"[DEBUG] Attempting to log to absolute path: {os.path.abspath(LOG_FILE_PATH)}") # Debug print for log path

# MAX_ALBUMS_TO_PROCESS = 2  # FOR DEBUGGING: Limit the number of albums processed

# CSV Column Definitions (align with transform_progarchives_data.py and data plan)
ALBUM_COLS = ['pa_album_id', 'raw_album_title', 'raw_artist_name', 'raw_release_year',
              'raw_recording_type', 'raw_subgenre_string', 'pa_average_rating',
              'pa_rating_count', 'pa_review_count',
              'pa_cover_image_url', 'pa_artist_page_link', 'pa_all_reviews_page_link']
ARTIST_COLS = ['pa_artist_id', 'raw_artist_name_canonical', 
               'raw_artist_country', 'raw_artist_style_main', 
               'raw_artist_style_secondary', 'raw_artist_status',
               'pa_artist_page_link_original', 'raw_artist_formation_year',
               'raw_artist_location', 'raw_artist_related_artists_summary',
               'raw_artist_lineup_current_summary', 'raw_artist_lineup_past_summary',
               'raw_artist_biography_summary'] # Match keys from artist_info dict
TRACK_COLS = ['pa_album_id', 'raw_track_number', 'raw_track_title', 'raw_track_duration',
              'is_subtrack', 'parent_track_number', 'is_bonus_track']
REVIEW_COLS = ['pa_album_id', 'raw_reviewer_name', 'raw_review_rating', 'raw_review_text', 'raw_review_date']
LINEUP_COLS = ['pa_album_id', 'raw_musician_name', 'raw_instruments_roles', 'is_guest']
SUBGENRE_COLS = ['raw_subgenre_name', 'raw_subgenre_definition']

# Logging Setup
root_logger = logging.getLogger() # Get the root logger
root_logger.setLevel(logging.DEBUG) # Set level on root logger TO DEBUG

# Remove any existing handlers from the root logger to prevent duplication
for handler in root_logger.handlers[:]:
    handler.close() # Close handler before removing
    root_logger.removeHandler(handler)

# File Handler
try:
    file_handler = logging.FileHandler(LOG_FILE_PATH, mode='w')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s'))
    root_logger.addHandler(file_handler)
except Exception as e:
    print(f"[CRITICAL LOGGING ERROR] Failed to create or add file handler: {e}")

# Console Handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO) # Explicitly set console to INFO
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s'))
root_logger.addHandler(console_handler)

root_logger.info("Orchestrator logging to file and console should be initiated.")

# Get a specific logger for this module, which will inherit root's handlers
logger = logging.getLogger(__name__) 

# --- Helper Functions ---

def find_album_html_files(base_dir):
    """Finds all album HTML files (e.g., albumXXXX.html) in the directory."""
    pattern = os.path.join(base_dir, "album[0-9a-zA-Z]*.html")
    album_files = glob.glob(pattern)
    # Filter out album-reviews files if any are caught by the glob
    album_files = [f for f in album_files if not os.path.basename(f).startswith("album-reviews")]
    logging.info(f"Found {len(album_files)} album files in {base_dir}")
    return album_files

def parse_subgenre_file(file_path):
    """
    Parses the ProgArchives subgenre definitions file.
    The file format is expected to have subgenre names in all caps with their definitions following.
    """
    subgenres = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split the content by two or more newlines to get individual subgenre blocks
        # Using a regex split to handle varying numbers of newlines robustly
        blocks = re.split(r'\n\s*\n+', content.strip()) # Ensures blocks are separated by at least two newlines, trims surrounding whitespace for each block
        
        title_pattern = r'^([A-Z][A-Z\s/-]+)(?:\n|:)' # Regex to find the title at the BEGINNING of a block, followed by newline or colon
        
        for i, block_text in enumerate(blocks):
            block_text = block_text.strip() # Clean each block
            if not block_text: # Skip empty blocks that might result from splitting
                continue

            match = re.match(title_pattern, block_text) # Try to match the title at the start of the block
            
            if match:
                subgenre_name = match.group(1).strip()
                
                if subgenre_name == "FOOTNOTE":
                    logger.debug(f"Skipping 'FOOTNOTE' as a subgenre. Block {i+1}")
                    continue # Skip processing this block further

                logger.debug(f"Extracted subgenre name: {subgenre_name} from block {i+1}")
                
                # Definition is the rest of the block after the matched title
                definition_text = block_text[match.end():].strip()
                
                # Further clean definition: remove lines like "A Progressive Rock Sub-genre" or "From Progarchives.com..."
                lines = definition_text.splitlines()
                cleaned_lines = []
                for line in lines:
                    line_lower = line.strip().lower()
                    # Catches "Canterbury Scene definition"
                    if not line_lower.startswith("a progressive rock sub-genre") and \
                       not line_lower.startswith("from progarchives.com") and \
                       not line_lower.endswith("definition") and \
                       line.strip(): # Add non-empty lines
                        cleaned_lines.append(line.strip())
                definition_text = "\n".join(cleaned_lines).strip()

                subgenres.append({
                    'raw_subgenre_name': subgenre_name,
                    'raw_subgenre_definition': definition_text
                })
            else:
                logger.debug(f"Block {i+1} did not start with a valid subgenre title. Content (first 100 chars): '{block_text[:100]}'")
        
        logging.info(f"Parsed {len(subgenres)} subgenre definitions from {file_path}")
        
    except FileNotFoundError:
        logging.error(f"Subgenre definition file not found: {file_path}")
    except Exception as e:
        logging.error(f"Error parsing subgenre file {file_path}: {e}", exc_info=True)
    
    return subgenres

# --- Main Orchestration ---

def main():
    try:
        logger.info("Starting Phase 2: Data Extraction from ProgArchives.")

        os.makedirs(RAW_DATA_OUTPUT_DIR, exist_ok=True)
        logger.info(f"Raw CSVs will be saved to: {RAW_DATA_OUTPUT_DIR}")

        # Initialize the ProgArchivesScraper with the HTML base directory
        scraper = ProgArchivesScraper(local_data_root=Path(PROGARCHIVES_HTML_BASE_DIR))
        logger.info(f"ProgArchivesScraper initialized with base HTML directory: {PROGARCHIVES_HTML_BASE_DIR}")

        # Initialize data lists
        all_albums_data = []
        all_artists_data = {}  # Use dict for deduplication by artist_page_link_local
        all_tracks_data = []
        all_reviews_data = []
        all_lineups_data = []
        unique_artist_page_links = set() # To collect unique artist file paths

        album_html_files = find_album_html_files(PROGARCHIVES_HTML_BASE_DIR)
        logger.info(f"Found {len(album_html_files)} album HTML files to process.")

        logger.info(f"!!! SCRIPT EXECUTION REACHED MAIN ALBUM LOOP !!!")

        # --- Main Loop for Album Processing ---
        for i, album_file_path_str in enumerate(album_html_files):
            album_file_path = Path(album_file_path_str) # Ensure it's a Path object
            logger.info(f"Processing album {i+1}/{len(album_html_files)}: {album_file_path.name}")
            try:
                album_id = album_file_path.stem.replace('album', '') # album_id from filename like 'albumXXXX'

                # Parse album data
                parsed_data = scraper.get_album_data(album_file_path) # Pass Path object

                if not parsed_data or 'error' in parsed_data:
                    logger.error(f"Error processing album {album_file_path}: {parsed_data.get('error', 'No data returned') if parsed_data else 'No data returned'}")
                    continue

                # Extract album info
                album_info = {
                    'pa_album_id': album_id,
                    'raw_album_title': parsed_data.get('album_title', ''),
                    'raw_artist_name': parsed_data.get('artist_name', ''),
                    'raw_release_year': parsed_data.get('year'),
                    'raw_recording_type': parsed_data.get('album_type', ''),
                    'raw_subgenre_string': parsed_data.get('genre', ''), # This is the main genre string
                    'pa_average_rating': parsed_data.get('rating_value'),
                    'pa_rating_count': parsed_data.get('rating_count'),
                    'pa_review_count': parsed_data.get('review_count'), # Total reviews for the album
                    'pa_cover_image_url': parsed_data.get('cover_image_url', ''),
                    'pa_artist_page_link': parsed_data.get('artist_page_link_local', ''), # Store the local link
                    'pa_all_reviews_page_link': parsed_data.get('all_reviews_page_link_local', '') # Local link to all reviews page
                }
                all_albums_data.append(album_info)

                # Collect artist page link for later processing
                artist_link_local = parsed_data.get('artist_page_link_local')
                if artist_link_local:
                    unique_artist_page_links.add(artist_link_local)

                # Extract tracks
                if 'tracks' in parsed_data and parsed_data['tracks']:
                    for track_num, track_info in enumerate(parsed_data['tracks'], 1):
                        all_tracks_data.append({
                            'pa_album_id': album_id,
                            'raw_track_title': track_info.get('title', ''),
                            'raw_track_length': track_info.get('duration', ''),
                            'raw_track_number': track_info.get('number', track_num) # Use number if present, else enumerate
                        })

                # Extract reviews from main album page
                if 'reviews' in parsed_data and parsed_data['reviews']:
                    for review_info in parsed_data['reviews']:
                        all_reviews_data.append({
                            'pa_album_id': album_id, # Link review to album
                            'pa_review_id': review_info.get('review_id', ''),
                            'raw_reviewer_name': review_info.get('reviewer', ''),
                            'raw_review_date': review_info.get('date', ''),
                            'raw_review_rating': review_info.get('rating'),
                            'raw_review_text': review_info.get('text', ''),
                            'pa_review_source_page': album_file_path.name # Source: main album page
                        })
                
                # Extract lineup if available (assuming it's part of main album data for now)
                # The scraper's get_album_data might need to be augmented if lineups are separate.
                # For now, let's assume 'lineup' is a list of dicts like {'musician': name, 'instruments': roles_str}
                if i == 0: # For the very first album
                    print(f"DEBUG PRINT: Album {album_id} - Attempting to get lineup data from parsed_data. Keys: {list(parsed_data.keys())}")
                
                album_lineup_data = parsed_data.get('lineup')
                
                if i < 5: # Log for the first 5 albums
                    #This log should appear if the print statement above appears
                    logger.info(f"Album {album_id} (extract_progarchives_data.py) - Lineup data from scraper: {album_lineup_data}")

                if album_lineup_data: # Check if lineup_data is not None and not empty
                    for lineup_member in album_lineup_data:
                        all_lineups_data.append({
                            'pa_album_id': album_id,
                            'raw_musician_name': lineup_member.get('musician', ''),
                            'raw_instruments_roles': lineup_member.get('instruments', '')
                        })
                elif i < 5: # Log if lineup_data is missing or empty for the first 5 albums
                    logger.warning(f"Album {album_id} (extract_progarchives_data.py) - No lineup data found or lineup data is empty.")
                
                # TODO: Handle dedicated review pages if 'all_reviews_page_link_local' is present and scraper supports it

            except Exception as e:
                logger.error(f"Unhandled exception processing album {album_file_path}: {e}", exc_info=True)

        logger.info(f"Finished processing {len(all_albums_data)} albums.")
        logger.info(f"Found {len(unique_artist_page_links)} unique artist page links to process.")

        # --- Artist Data Processing ---
        artist_id_counter = 1 # Simple counter for pa_artist_id if no natural ID from filename
        processed_artist_links = set()

        for i, artist_link_local in enumerate(unique_artist_page_links):
            if not artist_link_local or artist_link_local in processed_artist_links:
                continue
            
            logger.info(f"Processing artist {i+1}/{len(unique_artist_page_links)}: {artist_link_local}")
            try:
                # artist_link_local is like "artistXXXX.html?id=YYY" or just "artistXXXX.html"
                # We need the base filename for the scraper's get_band_details
                artist_base_filename = artist_link_local.split('?')[0]
                artist_file_path_to_parse = Path(PROGARCHIVES_HTML_BASE_DIR) / artist_base_filename

                # Use artist_link_local as the key for all_artists_data to avoid duplicates if scraper is called multiple times
                # for the same artist link due to different query params (though we expect only base filename here)
                if artist_link_local in all_artists_data: 
                    logger.debug(f"Skipping already processed (or queued for processing) artist link: {artist_link_local}")
                    continue

                parsed_artist_data = scraper.get_band_details(artist_file_path_to_parse) # Pass Path object

                if not parsed_artist_data or 'error' in parsed_artist_data:
                    logger.error(f"Error processing artist file {artist_file_path_to_parse} (from link {artist_link_local}): {parsed_artist_data.get('error', 'No data returned') if parsed_artist_data else 'No data returned'}")
                    all_artists_data[artist_link_local] = {'error': f"Failed to parse {artist_file_path_to_parse}"} # Store error
                    continue
                
                # Extract PA Artist ID from filename if possible (e.g., artistXXXX.html -> XXXX)
                pa_artist_id_from_file = re.search(r'artist([a-zA-Z0-9]+)', artist_base_filename)
                pa_artist_id = pa_artist_id_from_file.group(1) if pa_artist_id_from_file else f"generated_{artist_id_counter}"
                if not pa_artist_id_from_file:
                    artist_id_counter += 1

                artist_info = {
                    'pa_artist_id': pa_artist_id, # From filename or generated
                    'raw_artist_name_canonical': parsed_artist_data.get('name', ''), # Corrected key to 'name'
                    'raw_artist_country': parsed_artist_data.get('country', ''),
                    'raw_artist_style_main': parsed_artist_data.get('genre', ''), # Corrected key to 'genre'
                    'raw_artist_style_secondary': parsed_artist_data.get('secondary_genre', ''), # Secondary genre
                    'raw_artist_status': parsed_artist_data.get('status', ''),
                    'pa_artist_page_link_original': artist_link_local, # The original link including params
                    'raw_artist_formation_year': parsed_artist_data.get('formation_year'),
                    'raw_artist_location': parsed_artist_data.get('location_info'), # City, State etc.
                    'raw_artist_related_artists_summary': ", ".join(parsed_artist_data.get('related_artists', [])), # Comma-sep string
                    'raw_artist_lineup_current_summary': parsed_artist_data.get('current_lineup_summary', ''),
                    'raw_artist_lineup_past_summary': parsed_artist_data.get('past_members_summary', ''),
                    'raw_artist_biography_summary': parsed_artist_data.get('biography', ''), # Corrected key to 'biography'
                    # Add other fields from get_band_details as needed
                }
                # Store artist data using the unique artist_link_local as key to avoid duplicates
                all_artists_data[artist_link_local] = artist_info
                processed_artist_links.add(artist_link_local)

            except Exception as e:
                logger.error(f"Unhandled exception processing artist link {artist_link_local}: {e}", exc_info=True)
                all_artists_data[artist_link_local] = {'error': f"Exception processing artist link {artist_link_local}"}


        logger.info(f"Finished processing artists. Collected data for {len(all_artists_data) - sum(1 for ad in all_artists_data.values() if 'error' in ad)} unique artists.")
        
        # Convert artist data from dict to list for DataFrame creation
        final_artist_list = [data for data in all_artists_data.values() if 'error' not in data]


        # --- Subgenre File Processing ---
        logger.info(f"Processing subgenre definitions from: {PROGARCHIVES_SUBGENRE_FILE}")
        subgenre_definitions_data = parse_subgenre_file(PROGARCHIVES_SUBGENRE_FILE)

        # --- Create and Save DataFrames ---
        try:
            df_albums = pd.DataFrame(all_albums_data, columns=ALBUM_COLS)
            df_albums.to_csv(os.path.join(RAW_DATA_OUTPUT_DIR, "pa_raw_albums.csv"), index=False)
            logger.info(f"Saved pa_raw_albums.csv with {len(df_albums)} rows.")

            # Convert artist dict values to list for DataFrame
            df_artists = pd.DataFrame(final_artist_list, columns=ARTIST_COLS)
            df_artists.to_csv(os.path.join(RAW_DATA_OUTPUT_DIR, "pa_raw_artists.csv"), index=False)
            logger.info(f"Saved pa_raw_artists.csv with {len(df_artists)} rows.")

            df_tracks = pd.DataFrame(all_tracks_data, columns=TRACK_COLS)
            df_tracks.to_csv(os.path.join(RAW_DATA_OUTPUT_DIR, "pa_raw_tracks.csv"), index=False)
            logger.info(f"Saved pa_raw_tracks.csv with {len(df_tracks)} rows.")

            df_reviews = pd.DataFrame(all_reviews_data, columns=REVIEW_COLS)
            df_reviews.to_csv(os.path.join(RAW_DATA_OUTPUT_DIR, "pa_raw_reviews.csv"), index=False)
            logger.info(f"Saved pa_raw_reviews.csv with {len(df_reviews)} rows.")

            df_lineups = pd.DataFrame(all_lineups_data, columns=LINEUP_COLS)
            df_lineups.to_csv(os.path.join(RAW_DATA_OUTPUT_DIR, "pa_raw_lineups.csv"), index=False)
            logger.info(f"Saved pa_raw_lineups.csv with {len(df_lineups)} rows.")
            
            df_subgenres = pd.DataFrame(subgenre_definitions_data, columns=SUBGENRE_COLS)
            df_subgenres.to_csv(os.path.join(RAW_DATA_OUTPUT_DIR, "pa_raw_subgenre_definitions.csv"), index=False)
            logger.info(f"Saved pa_raw_subgenre_definitions.csv with {len(df_subgenres)} rows.")

        except Exception as e:
            logger.error(f"Error saving CSV files: {e}", exc_info=True)

        logger.info("Phase 2: Data Extraction script finished.")

    finally:
        # Ensure all handlers are flushed and closed.
        for handler in logging.getLogger().handlers[:]: # Iterate over a copy
            handler.close()
            logging.getLogger().removeHandler(handler)

if __name__ == "__main__":
    main() 