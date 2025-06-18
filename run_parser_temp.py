import logging
import json
from pathlib import Path
from src.albumexplore.scraping.progarchives_scraper import ProgArchivesScraper
from logging.handlers import RotatingFileHandler
from bs4 import BeautifulSoup # Added for the new test function

# --- Logger Setup --- #
LOG_FILE_PATH = Path(__file__).parent / "parser_output.log"
# Max log file size: 5MB, keep 3 backup logs
max_bytes = 5 * 1024 * 1024
backup_count = 3

# Clear existing handlers
root_logger = logging.getLogger()
if root_logger.handlers:
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

# Configure basic logging
logging.basicConfig(
    level=logging.DEBUG, # Capture all levels
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        RotatingFileHandler(LOG_FILE_PATH, maxBytes=max_bytes, backupCount=backup_count, encoding='utf-8'),
        logging.StreamHandler() # To also see INFO and above in console
    ]
)
# For StreamHandler, only show INFO and above
for handler in logging.getLogger().handlers:
    if isinstance(handler, logging.StreamHandler):
        handler.setLevel(logging.INFO)

logger = logging.getLogger(__name__)
logger.info("Script started. Logging configured.")

# --- Configuration --- #
LOCAL_DATA_ROOT = Path(__file__).parent / "ProgArchives Data" / "Website" / "ProgArchives" / "www.progarchives.com"

# --- Test Pairs --- #
# Each tuple: (artist_file_name_str, album_file_name_str)
TEST_PAIRS = [
    ("artist1ce3.html", "album38b1.html"),   # Kansas - Leftoverture
    ("artistdc9b.html", "album588a.html"),   # Queensrÿche - Operation: Mindcrime
    ("artist6067.html", "album6307.html"),   # Focus - Focus II / Moving Waves
    ("artiste783.html", "album45e3.html"),   # ELP - Tarkus (album45e3.html) for focused review testing
    ("artistd5b4.html", "album8dcb.html"),   # Pair 5 (Le Orme - Felona e Sorona)
    ("artist7520.html", "albumc68c.html"),   # Pair 6 (Banco del Mutuo Soccorso - Darwin!)
    ("artist78d7.html", "album2e74.html"),   # Pair 7 (PFM - Per Un Amico)
    ("artist0f25.html", "albumed51.html"),   # Pair 8 (Al Di Meola - Elegant Gypsy)
    ("artistdfcd.html", "albumce62.html"),   # Pair 9 (Genesis - Selling England by the Pound)
    ("artist3f60.html", "albume3e5.html"),   # Pair 10 (Yes - Close to the Edge)
    ("artistd1ca.html", "album503e.html"),   # Pair 11 (Marillion - Misplaced Childhood)
    ("artistfc32.html", "albumffdb.html")    # Pair 12 (Dream Theater - Images and Words)
]

# Flag to run single review test instead of batch
RUN_SINGLE_REVIEW_TEST = False # Ensure this is False to run the TEST_PAIRS

# --- Test Single Review File Parsing --- #
def test_single_review_file_parsing(scraper: ProgArchivesScraper):
    logger.info("--- Starting Single Review File Parse Test ---")
    review_file_name = "review4cc3.html" # The file identified for testing
    review_file_path = LOCAL_DATA_ROOT / review_file_name

    logger.info(f"Attempting to parse single review file: {review_file_path}")

    html_content = scraper._read_local_html_content(review_file_path)
    if not html_content:
        logger.error(f"Could not read HTML content for {review_file_path}")
        return

    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Call _parse_reviews_from_page directly
    # Note: This is calling a protected member for direct testing purposes.
    extracted_reviews = scraper._parse_reviews_from_page(soup, source_file_path=review_file_path)

    if extracted_reviews:
        logger.info(f"Successfully extracted {len(extracted_reviews)} review(s) from {review_file_name}:")
        for i, review_data in enumerate(extracted_reviews):
            logger.info(f"--- Review {i+1} ---")
            logger.info(f"  Reviewer: {review_data.get('reviewer')}")
            logger.info(f"  Rating:   {review_data.get('rating')}")
            logger.info(f"  Date:     {review_data.get('date')}")
            logger.info(f"  Text:     {review_data.get('text', '')[:200]}...") # Log first 200 chars of text
    else:
        logger.warning(f"No reviews extracted from {review_file_name}. Check parsing logic and selectors in _parse_reviews_from_page.")
    
    logger.info("--- Finished Single Review File Parse Test ---")

# --- Main Execution --- #
def main():
    """Main function to initialize scraper and parse files."""
    scraper = ProgArchivesScraper(local_data_root=LOCAL_DATA_ROOT)
    
    if RUN_SINGLE_REVIEW_TEST:
        test_single_review_file_parsing(scraper)
        return # Exit after single review test
        
    batch_results = []
    successful_albums = 0
    failed_albums = 0
    successful_artists = 0
    failed_artists = 0

    for i, (artist_file_str, album_file_str) in enumerate(TEST_PAIRS):
        logger.info(f"--- Processing Pair {i+1}/{len(TEST_PAIRS)}: Artist '{artist_file_str}', Album '{album_file_str}' ---")
        
        current_pair_result = {
            "pair_number": i + 1,
            "artist_file": artist_file_str,
            "album_file": album_file_str,
            "album_data": None,
            "artist_data": None
        }

        # Construct full paths
        album_full_path = LOCAL_DATA_ROOT / album_file_str
        artist_full_path = LOCAL_DATA_ROOT / artist_file_str

        # Process Album
        logger.info(f"Processing album file: {album_full_path}")
        album_data = scraper.get_album_data(album_full_path) # Use get_album_data
        current_pair_result["album_data"] = album_data
        if "error" in album_data:
            logger.error(f"Failed to parse album {album_file_str}: {album_data.get('error')}")
            failed_albums += 1
        else:
            logger.info(f"Successfully parsed album: {album_data.get('album_title', album_file_str)}")
            successful_albums +=1
            
        # Process Artist
        logger.info(f"Processing artist file: {artist_full_path}")
        artist_data = scraper.get_band_details(artist_full_path)
        current_pair_result["artist_data"] = artist_data
        if "error" in artist_data:
            logger.error(f"Failed to parse artist {artist_file_str}: {artist_data.get('error')}")
            failed_artists += 1
        else:
            logger.info(f"Successfully parsed artist: {artist_data.get('name', artist_file_str)}")
            successful_artists += 1
            
        batch_results.append(current_pair_result)
        logger.info(f"--- Finished processing pair {i+1} ---")

    # Save batch results to a JSON file
    batch_output_file = Path(__file__).parent / "batch_parser_output.json" # Still save to batch for structure
    try:
        with open(batch_output_file, 'w', encoding='utf-8') as f:
            json.dump(batch_results, f, indent=2)
        logger.info(f"Batch parsing complete. All results saved to {batch_output_file}")
    except Exception as e:
        logger.error(f"Error saving batch results to {batch_output_file}: {e}")

    logger.info("--- Batch Processing Summary ---")
    logger.info(f"Total pairs processed: {len(TEST_PAIRS)}")
    logger.info(f"Successful album parses: {successful_albums}")
    logger.info(f"Failed album parses: {failed_albums}")
    logger.info(f"Successful artist parses: {successful_artists}")
    logger.info(f"Failed artist parses: {failed_artists}")
    logger.info(f"Detailed logs are in: {LOG_FILE_PATH}")

if __name__ == "__main__":
    main()

