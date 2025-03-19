#!/usr/bin/env python
"""Test script for the updated ProgArchives scraper."""
import json
import logging
import time
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('progarchives_test.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Import our scraper
try:
    from src.albumexplore.data.scrapers.progarchives_scraper import ProgArchivesScraper
except ImportError:
    # Adjust Python path if needed
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from src.albumexplore.data.scrapers.progarchives_scraper import ProgArchivesScraper

def test_band_listing():
    """Test retrieving a list of bands."""
    logger.info("Testing band listing functionality")
    
    # Initialize scraper with a test cache directory
    scraper = ProgArchivesScraper(
        cache_dir=Path("cache/progarchives_test"),
        max_bands=20  # Limit to 20 bands for testing
    )
    
    # Get bands for letter 'K' (a smaller subset)
    bands = []
    for i, band in enumerate(scraper._get_bands_for_letter("K", use_cache=True)):
        bands.append(band)
        logger.info(f"Found band: {band.get('name')} [{band.get('genre')}, {band.get('country')}]")
        if i >= 10:  # Limit to first 10 bands for brevity
            break
    
    # Save results
    with open("progarchives_test_results.json", "w") as f:
        json.dump({"bands": bands}, f, indent=2)
    
    logger.info(f"Found {len(bands)} bands for letter K")
    return len(bands) > 0

def test_artist_page():
    """Test retrieving artist details."""
    logger.info("Testing artist page functionality")
    
    # Initialize scraper with a test cache directory
    scraper = ProgArchivesScraper(cache_dir=Path("cache/progarchives_test"))
    
    # Test with a few known artist IDs
    artist_ids = [
        "3",       # Genesis
        "147",     # Rush
        "3095",    # Ne Zhdali
    ]
    
    results = {}
    for artist_id in artist_ids:
        logger.info(f"Retrieving artist data for ID {artist_id}")
        try:
            artist_data = scraper.get_band_details(artist_id)
            
            # Log basic info
            logger.info(f"Artist: {artist_data.get('name')}")
            logger.info(f"Genre: {artist_data.get('genre')}")
            logger.info(f"Country: {artist_data.get('country')}")
            logger.info(f"Albums: {len(artist_data.get('albums', []))}")
            
            # Store only essential data to avoid large output
            results[artist_id] = {
                "name": artist_data.get("name"),
                "genre": artist_data.get("genre"),
                "country": artist_data.get("country"),
                "albums_count": len(artist_data.get("albums", [])),
                "albums": [a.get("title") for a in artist_data.get("albums", [])][:3]  # First 3 albums
            }
            
            # Be nice to the server
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"Error retrieving artist {artist_id}: {e}")
            results[artist_id] = {"error": str(e)}
    
    # Save results
    with open("progarchives_test_results.json", "r+") as f:
        data = json.load(f)
        data["artists"] = results
        f.seek(0)
        json.dump(data, f, indent=2)
        f.truncate()
    
    return all("name" in data for data in results.values())

def test_album_page():
    """Test retrieving album details."""
    logger.info("Testing album page functionality")
    
    # Initialize scraper with a test cache directory
    scraper = ProgArchivesScraper(cache_dir=Path("cache/progarchives_test"))
    
    # Test with a few known album IDs
    album_ids = [
        "1954",     # Genesis - Selling England By The Pound
        "42765",    # The Dillinger Escape Plan - Calculating Infinity
        "16081",    # Ne Zhdali - Transformed Traffic Jam
    ]
    
    results = {}
    for album_id in album_ids:
        logger.info(f"Retrieving album data for ID {album_id}")
        try:
            album_data = scraper.get_album_data(album_id)
            
            # Log basic info
            logger.info(f"Album: {album_data.get('title')} by {album_data.get('artist')}")
            logger.info(f"Year: {album_data.get('year')}")
            logger.info(f"Type: {album_data.get('type')}")
            logger.info(f"Rating: {album_data.get('reviews', {}).get('avg_rating')}")
            logger.info(f"Tracks: {len(album_data.get('tracks', []))}")
            
            # Store only essential data
            results[album_id] = {
                "title": album_data.get("title"),
                "artist": album_data.get("artist"),
                "year": album_data.get("year"),
                "type": album_data.get("type"),
                "rating": album_data.get("reviews", {}).get("avg_rating"),
                "tracks_count": len(album_data.get("tracks", [])),
                "tracks": [t.get("title") for t in album_data.get("tracks", [])][:3]  # First 3 tracks
            }
            
            # Be nice to the server
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"Error retrieving album {album_id}: {e}")
            results[album_id] = {"error": str(e)}
    
    # Save results
    with open("progarchives_test_results.json", "r+") as f:
        data = json.load(f)
        data["albums"] = results
        f.seek(0)
        json.dump(data, f, indent=2)
        f.truncate()
    
    return all("title" in data for data in results.values())

def test_album_reviews():
    """Test retrieving album reviews."""
    logger.info("Testing album reviews functionality")
    
    # Initialize scraper with a test cache directory
    scraper = ProgArchivesScraper(cache_dir=Path("cache/progarchives_test"))
    
    # Test with a few known album IDs that likely have reviews
    album_ids = [
        "1954",     # Genesis - Selling England By The Pound (should have many reviews)
        "42765",    # The Dillinger Escape Plan - Calculating Infinity
    ]
    
    results = {}
    for album_id in album_ids:
        logger.info(f"Retrieving reviews for album ID {album_id}")
        try:
            review_data = scraper.get_album_reviews(album_id, max_reviews=5)  # Limit to 5 reviews
            
            # Log basic info
            logger.info(f"Album: {review_data.get('title')} by {review_data.get('artist')}")
            logger.info(f"Reviews found: {len(review_data.get('reviews', []))}")
            
            # Store only essential data
            results[album_id] = {
                "title": review_data.get("title"),
                "artist": review_data.get("artist"),
                "reviews_count": len(review_data.get("reviews", [])),
                "sample_review": review_data.get("reviews", [])[0] if review_data.get("reviews") else None
            }
            
            # Be nice to the server
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"Error retrieving reviews for album {album_id}: {e}")
            results[album_id] = {"error": str(e)}
    
    # Save results
    with open("progarchives_test_results.json", "r+") as f:
        data = json.load(f)
        data["reviews"] = results
        f.seek(0)
        json.dump(data, f, indent=2)
        f.truncate()
    
    return True

def main():
    """Run all tests."""
    logger.info("Starting ProgArchives scraper tests")
    
    # Initialize results file
    with open("progarchives_test_results.json", "w") as f:
        json.dump({}, f)
    
    # Run tests and collect results
    results = {
        "band_listing": test_band_listing(),
        "artist_page": test_artist_page(),
        "album_page": test_album_page(),
        "album_reviews": test_album_reviews()
    }
    
    # Output summary
    logger.info("=== Test Summary ===")
    for test_name, success in results.items():
        logger.info(f"{test_name}: {'✓ Passed' if success else '✗ Failed'}")
    
    # Update results file with summary
    with open("progarchives_test_results.json", "r+") as f:
        data = json.load(f)
        data["test_summary"] = results
        f.seek(0)
        json.dump(data, f, indent=2)
        f.truncate()
    
    logger.info("Tests completed. Results saved to progarchives_test_results.json")

if __name__ == "__main__":
    main()