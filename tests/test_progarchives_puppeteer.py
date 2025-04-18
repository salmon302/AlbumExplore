"""Tests for Puppeteer-based ProgArchives scraper."""
import json
import logging
from datetime import datetime
from pathlib import Path
import pytest
import pytest_asyncio
import asyncio
from albumexplore.data.scrapers.progarchives_puppeteer import ProgArchivesPuppeteerScraper

logger = logging.getLogger(__name__)

@pytest_asyncio.fixture
async def scraper():
    """Create a test scraper instance."""
    s = ProgArchivesPuppeteerScraper(
        cache_dir=Path("cache/progarchives_test"),
        headless=True
    )
    await s.init()  # Initialize browser
    yield s
    await s.close()  # Cleanup

@pytest.mark.asyncio
async def test_get_album_details(scraper):
    """Test retrieving album details."""
    albums_to_test = [
        "King Crimson - In The Court Of The Crimson King",
        "Tool - Lateralus",
        "Dream Theater - Images and Words"
    ]
    
    results = {}
    for album in albums_to_test:
        logger.info(f"Testing album lookup: {album}")
        try:
            details = await scraper.get_album_details(album)
            assert details is not None
            assert 'error' not in details
            assert details['title']
            assert details['artist']

            # Log basic info
            logger.info(f"Found: {details['artist']} - {details['title']}")
            logger.info(f"Year: {details.get('year')}")
            logger.info(f"Rating: {details.get('rating')}")
            logger.info(f"Tracks: {len(details.get('tracks', []))}")

            results[album] = {
                'title': details['title'],
                'artist': details['artist'],
                'year': details.get('year'),
                'rating': details.get('rating'),
                'track_count': len(details.get('tracks', [])),
                'first_3_tracks': [t['title'] for t in details.get('tracks', [])[:3]]
            }

        except Exception as e:
            logger.error(f"Error testing {album}: {e}")
            results[album] = {'error': str(e)}
    
    # Save results for analysis
    output_file = Path("test_results_puppeteer.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'test_date': datetime.now().isoformat(),
            'results': results
        }, f, indent=2)
    
    # Ensure we got some valid results
    assert any('error' not in album for album in results.values())

@pytest.mark.asyncio
async def test_get_band_details(scraper):
    """Test retrieving band details."""
    bands_to_test = [
        "King Crimson",
        "Tool",
        "Dream Theater"
    ]
    
    results = {}
    for band in bands_to_test:
        logger.info(f"Testing band lookup: {band}")
        try:
            details = await scraper.get_band_details(band)
            assert details is not None
            assert 'error' not in details
            assert details['name']

            # Log basic info
            logger.info(f"Found: {details['name']}")
            logger.info(f"Genre: {details.get('genre')}")
            logger.info(f"Country: {details.get('country')}")
            logger.info(f"Albums: {len(details.get('albums', []))}")

            results[band] = {
                'name': details['name'],
                'genre': details['genre'],
                'country': details['country'],
                'album_count': len(details.get('albums', [])),
                'first_3_albums': [
                    {
                        'title': a['title'],
                        'year': a.get('year'),
                        'rating': a.get('rating')
                    }
                    for a in details.get('albums', [])[:3]
                ]
            }

        except Exception as e:
            logger.error(f"Error testing {band}: {e}")
            results[band] = {'error': str(e)}
    
    # Save results for analysis
    output_file = Path("test_results_puppeteer_bands.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'test_date': datetime.now().isoformat(),
            'results': results
        }, f, indent=2)
    
    # Ensure we got some valid results
    assert any('error' not in band for band in results.values())

async def test_album_info():
    """Test getting album info using Puppeteer."""
    # Initialize scraper
    scraper = ProgArchivesPuppeteerScraper(
        cache_dir=Path("cache/progarchives_test"),
        headless=True
    )
    
    try:
        # Test with some well-known prog albums
        test_albums = [
            "King Crimson - In The Court Of The Crimson King",
            "Tool - Lateralus",
            "Dream Theater - Images And Words"
        ]
        
        results = {}
        
        # Get info for each album
        for album in test_albums:
            info = await scraper.get_album_info(album)
            results[album.split(" - ")[0]] = info
            
        # Save test results
        with open("test_results_puppeteer.json", "w") as f:
            json.dump({
                "test_date": "2025-03-21",
                "results": results
            }, f, indent=2)
            
    finally:
        await scraper.close()

if __name__ == "__main__":
    asyncio.run(test_album_info())