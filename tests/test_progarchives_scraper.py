"""Tests for ProgArchives scraper implementation."""
import pytest
import json
import logging
from pathlib import Path
from datetime import datetime
from albumexplore.data.scrapers.progarchives_scraper import ProgArchivesScraper

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.fixture
def cache_dir(tmp_path):
    """Create a temporary cache directory."""
    cache = tmp_path / "cache" / "progarchives"
    cache.mkdir(parents=True)
    return cache

@pytest.fixture
def scraper(cache_dir):
    """Initialize scraper with test configuration."""
    return ProgArchivesScraper(
        cache_dir=cache_dir,
        max_bands=10,  # Small sample size for testing
        random_sample=True  # Enable random sampling
    )

def test_random_artist_scraping(scraper):
    """Test scraping random artists' discographies."""
    results = []
    stats = {
        'total_bands': 0,
        'total_albums': 0,
        'bands_with_lineup': 0,
        'albums_with_lineup': 0,
        'total_members': 0
    }
    
    # Process each random band
    for band in scraper.get_bands_all():
        stats['total_bands'] += 1
        logger.info(f"Processing band: {band['name']}")
        
        # Get detailed band info
        details = scraper.get_band_details(band['url'])
        assert 'error' not in details, f"Error getting details for {band['name']}"
        
        # Validate band details
        assert details['name'], "Band name should be present"
        assert details['genre'], "Band genre should be present"
        assert isinstance(details.get('albums', []), list), "Albums should be a list"
        
        # Track statistics
        albums = details.get('albums', [])
        stats['total_albums'] += len(albums)
        stats['total_members'] += len(details.get('members', []))
        
        if details.get('members'):
            stats['bands_with_lineup'] += 1
        
        # Check each album
        for album in albums:
            assert album['title'], "Album title should be present"
            assert album['year'], "Album year should be present"
            assert album['type'] in ['Studio Album', 'Single/EP', 'Live', 'Compilation'], f"Invalid album type: {album['type']}"
            
            if album.get('lineup'):
                stats['albums_with_lineup'] += 1
        
        results.append({**band, **details})
    
    # Validate overall results
    assert stats['total_bands'] > 0, "Should have processed some bands"
    assert stats['total_albums'] > 0, "Should have found some albums"
    assert stats['bands_with_lineup'] > 0, "Some bands should have lineup info"
    assert stats['albums_with_lineup'] > 0, "Some albums should have lineup info"
    
    # Save test results for analysis
    results_file = Path(__file__).parent / f"test_results_random_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump({
            'stats': stats,
            'results': results
        }, f, indent=2)
    
    logger.info(f"Test Results:")
    logger.info(f"Total Bands: {stats['total_bands']}")
    logger.info(f"Total Albums: {stats['total_albums']}")
    logger.info(f"Bands with Lineup: {stats['bands_with_lineup']}")
    logger.info(f"Albums with Lineup: {stats['albums_with_lineup']}")
    logger.info(f"Total Members: {stats['total_members']}")
    logger.info(f"Results saved to: {results_file}")

def test_rate_limiting(scraper):
    """Test rate limiting functionality."""
    from time import time
    
    # Make a few requests and check timing
    start = time()
    for _ in range(3):
        band = next(scraper.get_bands_all())
        scraper.get_band_details(band['url'])
    duration = time() - start
    
    # Should take at least 10 seconds due to rate limiting
    assert duration >= 10, "Rate limiting should enforce delays between requests"

def test_caching(scraper, cache_dir):
    """Test caching functionality."""
    # First request should cache
    band = next(scraper.get_bands_all())
    details1 = scraper.get_band_details(band['url'])
    
    # Verify cache file exists
    cache_files = list(cache_dir.glob('*.html'))
    assert len(cache_files) > 0, "Should have created cache files"
    
    # Second request should use cache
    details2 = scraper.get_band_details(band['url'])
    assert details1 == details2, "Cached results should match"

def test_error_handling(scraper):
    """Test error handling for invalid URLs."""
    with pytest.raises(Exception):
        scraper.get_band_details("https://www.progarchives.com/invalid-band-url")

def test_data_validation(scraper):
    """Test data validation and cleaning."""
    band = next(scraper.get_bands_all())
    details = scraper.get_band_details(band['url'])
    
    # Check data cleaning
    assert not any(k for k in details if k.strip() != k), "Keys should be stripped"
    assert not any(v for v in details.values() if isinstance(v, str) and v.strip() != v), "String values should be stripped"
    
    # Validate required fields
    required_fields = ['name', 'genre', 'country']
    for field in required_fields:
        assert field in details, f"Missing required field: {field}"
        assert details[field], f"Required field {field} should not be empty"