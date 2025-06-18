"""Test script for verifying ProgArchives scraper URL handling."""
import logging
import sys
import json
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent.parent / 'src'
sys.path.append(str(src_path))

from albumexplore.data.scrapers.progarchives_scraper import ProgArchivesScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_url_functionality():
    """Test the scraper functionality with different URL patterns."""
    # Initialize scraper
    cache_dir = Path("cache/progarchives_test")
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    scraper = ProgArchivesScraper(cache_dir=cache_dir)  # Removed local_data_root
    
    # Test 1: Bands alphabetical listing
    logger.info("Testing bands alphabetical listing (bands-alpha.asp?letter=*)")
    try:
        # Get bands starting with 'A' as a sample
        bands = list(scraper._get_bands_for_letter('A'))
        logger.info(f"Found {len(bands)} bands starting with 'A'")
        if bands:
            logger.info(f"Sample band: {bands[0]['name']} - {bands[0]['url']}")
    except Exception as e:
        logger.error(f"Error in alphabetical listing test: {e}")
    
    # Test 2: Artist page
    logger.info("\nTesting artist page (artist.asp?id=)")
    try:
        # Use a known artist ID for testing
        artist_id = "3095"  # Some artist ID
        artist_url = f"{scraper.ARTIST_URL}?id={artist_id}"
        
        logger.info(f"Requesting artist with ID: {artist_id}")
        artist_data = scraper.get_band_details(artist_url)
        
        if 'error' in artist_data:
            logger.error(f"Error getting artist details: {artist_data['error']}")
        else:
            logger.info(f"Successfully retrieved artist: {artist_data.get('name')}")
            if 'albums' in artist_data:
                logger.info(f"Found {len(artist_data['albums'])} albums for this artist")
    except Exception as e:
        logger.error(f"Error in artist page test: {e}")
    
    # Test 3: Album page
    logger.info("\nTesting album page (album.asp?id=)")
    try:
        # Use a known album ID for testing
        album_id = "42765"  # Some album ID
        
        logger.info(f"Requesting album with ID: {album_id}")
        album_data = scraper.get_album_data(album_id)
        
        if 'error' in album_data:
            logger.error(f"Error getting album details: {album_data['error']}")
        else:
            logger.info(f"Successfully retrieved album: {album_data.get('title')} by {album_data.get('artist')}")
            logger.info(f"Album details: {album_data.get('year', 'N/A')} - {album_data.get('genre', 'N/A')}")
            if 'tracks' in album_data:
                logger.info(f"Found {len(album_data['tracks'])} tracks")
    except Exception as e:
        logger.error(f"Error in album page test: {e}")
    
    # Test 4: Album reviews page
    logger.info("\nTesting album reviews page (album-reviews.asp?id=)")
    try:
        # Use the same album ID
        album_id = "42765"
        
        logger.info(f"Requesting reviews for album with ID: {album_id}")
        review_data = scraper.get_album_reviews(album_id, max_reviews=3)
        
        if 'error' in review_data:
            logger.error(f"Error getting album reviews: {review_data['error']}")
        else:
            logger.info(f"Successfully retrieved reviews for: {review_data.get('title')}")
            if 'reviews' in review_data:
                logger.info(f"Found {len(review_data['reviews'])} reviews (limited to 3)")
                if review_data['reviews']:
                    sample_review = review_data['reviews'][0]
                    logger.info(f"Sample review by {sample_review.get('author', 'Anonymous')}: "
                               f"Rating: {sample_review.get('rating', 'N/A')}")
    except Exception as e:
        logger.error(f"Error in album reviews page test: {e}")

    # Test 5: Album search functionality
    logger.info("\nTesting album search functionality")
    try:
        # Search for a common term
        search_results = scraper.search_albums("dream theater")
        
        if search_results:
            logger.info(f"Search returned {len(search_results)} results")
            logger.info(f"Sample result: {search_results[0].get('title')} "
                       f"by {search_results[0].get('artist')}")
        else:
            logger.warning("Search returned no results")
    except Exception as e:
        logger.error(f"Error in search test: {e}")

    # Save a sample of the results for inspection
    try:
        output_file = Path("progarchives_test_results.json")
        results = {
            "bands_sample": bands[:5] if bands else [],
            "artist_data": artist_data,
            "album_data": album_data,
            "review_data": review_data,
            "search_results": search_results[:5] if search_results else []
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=str)
            
        logger.info(f"\nSaved test results to {output_file}")
    except Exception as e:
        logger.error(f"Error saving test results: {e}")

if __name__ == "__main__":
    test_url_functionality()