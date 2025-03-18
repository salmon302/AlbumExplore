"""Test ProgArchives scraper against random artist discographies."""
import pytest
import logging
from pathlib import Path
import json
import random
from datetime import datetime
from bs4 import BeautifulSoup
import requests
from typing import List, Dict, Optional
import sqlite3
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from albumexplore.scraping import ProgArchivesScraper

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@pytest.fixture
def scraper():
    """Create scraper instance with cache."""
    cache_dir = Path("cache/progarchives/test_random")
    cache_dir.mkdir(parents=True, exist_ok=True)
    return ProgArchivesScraper(cache_dir=cache_dir)

@pytest.fixture
def db_session():
    """Create a test database session."""
    engine = create_engine('sqlite:///:memory:')
    Session = sessionmaker(bind=engine)
    return Session()

def validate_album_data(album: Dict) -> List[str]:
    """Validate album data structure and content."""
    errors = []
    
    # Required fields
    required_fields = ['title', 'artist', 'url']
    for field in required_fields:
        if field not in album:
            errors.append(f"Missing required field: {field}")
            
    # Optional but expected fields
    expected_fields = ['year', 'rating', 'genre', 'record_type', 'description']
    for field in expected_fields:
        if field not in album:
            logger.warning(f"Missing expected field: {field}")
            
    # Validate tracks if present
    if 'tracks' in album:
        for i, track in enumerate(album['tracks']):
            if not isinstance(track, dict):
                errors.append(f"Invalid track format at index {i}")
                continue
            if 'title' not in track:
                errors.append(f"Track at index {i} missing title")
            if 'number' in track and not isinstance(track['number'], (int, type(None))):
                errors.append(f"Invalid track number format at index {i}")
                
    # Validate lineup if present
    if 'lineup' in album:
        for i, member in enumerate(album['lineup']):
            if not isinstance(member, dict):
                errors.append(f"Invalid lineup member format at index {i}")
                continue
            if 'name' not in member:
                errors.append(f"Lineup member at index {i} missing name")
                
    return errors

def validate_band_data(band: Dict) -> List[str]:
    """Validate band data structure and content."""
    errors = []
    
    # Required fields
    required_fields = ['name', 'url']
    for field in required_fields:
        if field not in band:
            errors.append(f"Missing required field: {field}")
            
    # Optional but expected fields
    expected_fields = ['country', 'genre', 'description']
    for field in expected_fields:
        if field not in band:
            logger.warning(f"Missing expected field: {field}")
            
    # Validate albums list
    if 'albums' in band:
        if not isinstance(band['albums'], list):
            errors.append("Albums field is not a list")
        else:
            for i, album in enumerate(band['albums']):
                album_errors = validate_album_data(album)
                if album_errors:
                    errors.extend([f"Album {i} ({album.get('title', 'Unknown')}): {err}" 
                                 for err in album_errors])
                    
    return errors

def test_random_discographies(scraper):
    """Test scraping random artist discographies."""
    # Configuration
    test_bands = 5  # Number of random bands to test
    error_threshold = 0.2  # Maximum acceptable error rate (20%)
    min_albums = 3  # Minimum albums a band should have
    
    # Statistics tracking
    stats = {
        'total_bands': 0,
        'total_albums': 0,
        'successful_bands': 0,
        'successful_albums': 0,
        'failed_bands': 0,
        'failed_albums': 0,
        'band_errors': [],
        'album_errors': [],
        'start_time': datetime.now()
    }
    
    try:
        # Get list of bands
        logger.info("Getting band list...")
        all_bands = list(scraper.get_bands_all())
        
        # Filter bands with minimum albums and shuffle
        filtered_bands = [band for band in all_bands 
                         if len(band.get('albums', [])) >= min_albums]
        random.shuffle(filtered_bands)
        
        test_data = []
        processed_urls = set()
        
        # Process random selection
        for band in filtered_bands[:test_bands]:
            stats['total_bands'] += 1
            band_data = {'name': band['name'], 'url': band['url'], 'errors': []}
            
            try:
                logger.info(f"\nTesting band: {band['name']}")
                
                # Get band details
                details = scraper.get_band_details(band['url'])
                if 'error' in details:
                    raise Exception(f"Failed to get band details: {details['error']}")
                
                # Validate band data
                band_errors = validate_band_data(details)
                if band_errors:
                    band_data['errors'].extend(band_errors)
                    stats['band_errors'].extend(band_errors)
                
                # Track albums
                albums = []
                for album in details.get('albums', []):
                    stats['total_albums'] += 1
                    
                    try:
                        if album['url'] in processed_urls:
                            logger.warning(f"Skipping duplicate album URL: {album['url']}")
                            continue
                        processed_urls.add(album['url'])
                        
                        logger.info(f"Testing album: {album.get('title', 'Unknown')}")
                        
                        # Get album details
                        album_details = scraper.get_album_details(album['url'])
                        if 'error' in album_details:
                            raise Exception(f"Failed to get album details: {album_details['error']}")
                            
                        # Validate album data
                        album_errors = validate_album_data(album_details)
                        if album_errors:
                            stats['album_errors'].extend(album_errors)
                            album_details['errors'] = album_errors
                        
                        albums.append(album_details)
                        stats['successful_albums'] += 1
                        
                    except Exception as e:
                        logger.error(f"Error processing album: {str(e)}")
                        stats['failed_albums'] += 1
                        albums.append({
                            'url': album.get('url', 'unknown'),
                            'error': str(e)
                        })
                
                band_data['albums'] = albums
                band_data['albums_total'] = len(details.get('albums', []))
                band_data['albums_processed'] = len(albums)
                
                test_data.append(band_data)
                stats['successful_bands'] += 1
                
            except Exception as e:
                logger.error(f"Error processing band {band['name']}: {str(e)}")
                stats['failed_bands'] += 1
                band_data['error'] = str(e)
                test_data.append(band_data)
        
        # Calculate error rates
        band_error_rate = stats['failed_bands'] / stats['total_bands']
        album_error_rate = stats['failed_albums'] / stats['total_albums'] if stats['total_albums'] > 0 else 1
        
        # Save test results
        results = {
            'test_date': datetime.now().isoformat(),
            'duration': str(datetime.now() - stats['start_time']),
            'statistics': {
                'bands_total': stats['total_bands'],
                'bands_successful': stats['successful_bands'],
                'bands_failed': stats['failed_bands'],
                'band_error_rate': band_error_rate,
                'albums_total': stats['total_albums'],
                'albums_successful': stats['successful_albums'],
                'albums_failed': stats['failed_albums'],
                'album_error_rate': album_error_rate
            },
            'band_errors': stats['band_errors'],
            'album_errors': stats['album_errors'],
            'test_data': test_data
        }
        
        output_file = Path(f"test_results_random_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
            
        # Log summary
        logger.info("\nTest Summary:")
        logger.info(f"Total bands processed: {stats['total_bands']}")
        logger.info(f"Successful bands: {stats['successful_bands']}")
        logger.info(f"Failed bands: {stats['failed_bands']}")
        logger.info(f"Band error rate: {band_error_rate:.1%}")
        logger.info(f"Total albums processed: {stats['total_albums']}")
        logger.info(f"Successful albums: {stats['successful_albums']}")
        logger.info(f"Failed albums: {stats['failed_albums']}")
        logger.info(f"Album error rate: {album_error_rate:.1%}")
        logger.info(f"\nResults saved to: {output_file}")
        
        # Assert acceptable error rates
        assert band_error_rate <= error_threshold, f"Band error rate {band_error_rate:.1%} exceeds threshold {error_threshold:.1%}"
        assert album_error_rate <= error_threshold, f"Album error rate {album_error_rate:.1%} exceeds threshold {error_threshold:.1%}"
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise

def test_data_consistency(scraper):
    """Test data consistency across multiple fetches."""
    test_urls = []
    
    # Get some random band URLs first
    all_bands = list(scraper.get_bands_all())
    if all_bands:
        random.shuffle(all_bands)
        test_urls.extend(band['url'] for band in all_bands[:2])
    
    # Get some album URLs from these bands
    for band_url in test_urls[:]:
        details = scraper.get_band_details(band_url)
        if details and 'albums' in details:
            albums = details['albums']
            if albums:
                random.shuffle(albums)
                test_urls.extend(album['url'] for album in albums[:2])
    
    # Test each URL multiple times
    for url in test_urls:
        logger.info(f"\nTesting consistency for URL: {url}")
        
        # Fetch same URL multiple times
        responses = []
        for i in range(3):
            logger.info(f"Fetch {i+1}")
            if 'artist.asp' in url:
                data = scraper.get_band_details(url)
            else:
                data = scraper.get_album_details(url)
            responses.append(data)
        
        # Compare responses
        for i in range(1, len(responses)):
            assert responses[0] == responses[i], f"Inconsistent data between fetches for {url}"
            
def test_error_handling(scraper):
    """Test scraper's error handling capabilities."""
    # Test invalid URLs
    invalid_urls = [
        "https://www.progarchives.com/notreal",
        "https://www.progarchives.com/artist.asp?id=999999",
        "https://www.progarchives.com/album.asp?id=999999",
        "malformed_url",
        ""
    ]
    
    for url in invalid_urls:
        logger.info(f"\nTesting invalid URL: {url}")
        
        # Should handle error gracefully
        if 'album.asp' in url:
            result = scraper.get_album_details(url)
        else:
            result = scraper.get_band_details(url)
            
        assert 'error' in result, f"Expected error for invalid URL {url}"
        logger.info(f"Got expected error: {result['error']}")

if __name__ == '__main__':
    pytest.main([__file__, '-v'])