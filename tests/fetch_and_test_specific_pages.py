import sys
import os
import logging
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from albumexplore.scraping.progarchives.crawler import ProgArchivesCrawler
from albumexplore.scraping.progarchives_scraper import ProgArchivesScraper

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

URLS_TO_TEST = [
    "https://www.progarchives.com/artist.asp?id=5433", # Haken (Artist)
    "https://www.progarchives.com/album.asp?id=5796",  # Haken - Aquarius
    "https://www.progarchives.com/album.asp?id=19263", # Haken - Vector
    "https://www.progarchives.com/album.asp?id=1829"   # Yes - Close to the Edge
]

def fetch_pages(output_dir):
    """Fetch pages using the crawler."""
    logger.info("Starting fetch...")
    crawled_files = []
    
    # Use headless=False to see what's happening if needed, but True is default
    with ProgArchivesCrawler(output_dir=str(output_dir), headless=False) as crawler:
        for url in URLS_TO_TEST:
            try:
                # We need to handle artist pages differently because _process_album_page expects album URLs
                # and names files album_ID.html.
                # But looking at the code, _process_album_page just fetches and saves.
                # It extracts ID from 'id='.
                # If it's an artist page, it will save as album_5433.html which is confusing but functional for storage.
                # Let's modify the filename logic slightly by subclassing or just letting it be and renaming later?
                # Actually, let's just use the crawler's internal method _fetch_url and save manually to control filenames.
                
                html = crawler._fetch_url(url, wait_time=3)
                
                if "artist.asp" in url:
                    prefix = "artist"
                else:
                    prefix = "album"
                
                obj_id = url.split('id=')[1].split('&')[0]
                filename = f"{prefix}_{obj_id}.html"
                file_path = crawler.daily_dir / filename
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(html)
                
                logger.info(f"Saved {url} to {file_path}")
                crawled_files.append(file_path)
                
            except Exception as e:
                logger.error(f"Failed to fetch {url}: {e}")
                
    return crawled_files

def test_parser(files):
    """Test the parser on the fetched files."""
    logger.info("Starting parser test...")
    
    # Initialize scraper with the directory containing the files
    # The files are in tests/fixtures/crawled/<date>/
    # We can pass the parent dir to the scraper
    if not files:
        logger.warning("No files to parse.")
        return

    data_root = files[0].parent.parent # tests/fixtures/crawled
    scraper = ProgArchivesScraper(local_data_root=data_root)
    
    for file_path in files:
        logger.info(f"\n{'='*50}\nTesting parser on {file_path.name}\n{'='*50}")
        
        try:
            if "artist" in file_path.name:
                data = scraper.get_band_details(file_path)
                print(f"Artist: {data.get('name')}")
                print(f"Genre: {data.get('genre')}")
                print(f"Country: {data.get('country')}")
                print(f"Albums found: {len(data.get('albums', []))}")
                if data.get('albums'):
                    print(f"Sample Album: {data['albums'][0]}")
            else:
                data = scraper.get_album_data(file_path)
                print(f"Title: {data.get('album_title')}")
                print(f"Artist: {data.get('artist_name')}")
                print(f"Year: {data.get('year')}")
                print(f"Type: {data.get('album_type')}")
                
                print("\n--- Lineup ---")
                for member in data.get('lineup', []):
                    print(f"- {member['musician']} ({member['instruments']}) [Guest: {member.get('is_guest')}]")
                    
                print("\n--- Releases Info ---")
                info = data.get('releases_info', {})
                print(f"Label: {info.get('label')}")
                print(f"Date: {info.get('release_date')}")
                
                print("\n--- Reviews ---")
                print(f"Total Reviews: {len(data.get('reviews', []))}")
                if data.get('reviews'):
                    r = data['reviews'][0]
                    print(f"Sample Review: ID={r.get('review_id')} | {r.get('reviewer')} | {r.get('rating')} stars")

        except Exception as e:
            logger.error(f"Failed to parse {file_path.name}: {e}", exc_info=True)

if __name__ == "__main__":
    output_dir = Path(__file__).parent / "fixtures" / "crawled"
    files = fetch_pages(output_dir)
    test_parser(files)
