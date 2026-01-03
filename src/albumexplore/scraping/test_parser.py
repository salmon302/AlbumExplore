import logging
import sys
from pathlib import Path
from albumexplore.scraping.progarchives_scraper import ProgArchivesScraper

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_parser():
    """
    Test the ProgArchivesScraper on a few files from the raw_data directory.
    """
    raw_data_dir = Path("raw_data/progarchives")
    if not raw_data_dir.exists():
        logger.error(f"Raw data directory not found: {raw_data_dir}")
        return

    # Find a few album files
    album_files = list(raw_data_dir.rglob("album*.html"))
    # Filter out album-reviews
    album_files = [f for f in album_files if "album-reviews" not in f.name]
    
    if not album_files:
        logger.error("No album HTML files found in raw_data/progarchives")
        return

    # Take up to 5 files
    test_files = album_files[:5]
    logger.info(f"Testing scraper on {len(test_files)} files...")

    scraper = ProgArchivesScraper(local_data_root=raw_data_dir)

    for file_path in test_files:
        logger.info(f"--- Processing {file_path.name} ---")
        try:
            data = scraper.get_album_data(file_path, use_cache=False)
            
            if 'error' in data:
                logger.error(f"Error parsing {file_path.name}: {data['error']}")
            else:
                logger.info(f"Title: {data.get('album_title')}")
                logger.info(f"Artist: {data.get('artist_name')}")
                logger.info(f"Rating: {data.get('rating_value')} (Count: {data.get('rating_count')})")
                logger.info(f"Reviews: {data.get('review_count')}")
                
                # Verification logic
                if data.get('rating_count') is None:
                    logger.warning("FAIL: Rating count is None!")
                else:
                    logger.info("PASS: Rating count extracted.")
                    
                if data.get('review_count') is None:
                    logger.warning("FAIL: Review count is None!")
                else:
                    logger.info("PASS: Review count extracted.")

        except Exception as e:
            logger.error(f"Exception processing {file_path.name}: {e}", exc_info=True)

if __name__ == "__main__":
    test_parser()
