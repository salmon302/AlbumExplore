"""Test ProgArchives scraper against random artist discographies."""
import pytest
import logging
from pathlib import Path
import json
import random
from datetime import datetime
import time
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
    return ProgArchivesScraper(
        cache_dir=cache_dir,
        max_bands=100,  # Increased from 50 to 100 to get a better sample
        random_sample=True,
        min_request_interval=2.0  # Maintain ethical rate limiting
    )

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
    required_fields = ['title', 'url']  # Reduced requirements for initial test
    for field in required_fields:
        if field not in album:
            errors.append(f"Missing required field: {field}")
    
    # Add debug logging for album data
    logger.debug(f"Validating album data: {album}")
            
    # Optional but expected fields
    expected_fields = ['year', 'rating', 'genre', 'record_type', 'description']
    for field in expected_fields:
        if field not in album:
            logger.debug(f"Missing expected field: {field}")
            
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
    expected_fields = ['country', 'genre']  # Reduced requirements for initial test
    for field in expected_fields:
        if field not in band:
            logger.warning(f"Missing expected field: {field}")
            
    # Validate albums list if present
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
        logger.info("Starting band collection...")
        all_bands = []
        bands_per_page = 0
        
        # Collect bands with timeout protection
        try:
            for band in scraper.get_bands_all():
                logger.debug(f"Found band: {band['name']} from {band.get('url', 'unknown')}")
                all_bands.append(band)
                bands_per_page += 1
                
                if bands_per_page >= 50:
                    logger.info(f"Collected {len(all_bands)} bands so far...")
                    bands_per_page = 0
                
                # Small delay between fetches
                time.sleep(0.5)
        except Exception as e:
            logger.error(f"Error during band collection: {str(e)}", exc_info=True)
            raise
        
        logger.info(f"Band collection complete. Found {len(all_bands)} bands")
        
        if not all_bands:
            raise Exception("No bands found in initial collection")
        
        # Shuffle the band list
        random.shuffle(all_bands)
        
        # Find bands with minimum albums by checking details
        logger.info(f"Filtering bands to find {test_bands} with at least {min_albums} albums...")
        filtered_bands = []
        bands_checked = 0
        
        for band in all_bands:
            bands_checked += 1
            logger.info(f"Checking band {bands_checked}: {band['name']} ({band.get('url', 'unknown')})")
            
            try:
                details = scraper.get_band_details(band['url'])
                if 'error' in details:
                    logger.warning(f"Error getting details for {band['name']}: {details['error']}")
                    continue
                
                logger.debug(f"Raw details for {band['name']}: {details}")
                album_count = len(details.get('albums', []))
                logger.info(f"{band['name']} has {album_count} albums")
                
                if album_count >= min_albums:
                    logger.info(f"Adding {band['name']} to test set")
                    filtered_bands.append(band)
                    if len(filtered_bands) >= test_bands:
                        break
                
                # Rate limiting
                time.sleep(2)
                
            except Exception as e:
                logger.warning(f"Error checking band {band['name']}: {str(e)}")
                continue
        
        if not filtered_bands:
            raise Exception("No bands found with minimum number of albums")
        
        logger.info(f"Found {len(filtered_bands)} bands with {min_albums}+ albums")
        
        # Process test bands
        processed_urls = set()
        test_data = []
        
        for band in filtered_bands:
            stats['total_bands'] += 1
            band_data = {'name': band['name'], 'url': band['url'], 'errors': []}
            
            try:
                logger.info(f"\nTesting band: {band['name']}")
                details = scraper.get_band_details(band['url'])
                
                if 'error' in details:
                    raise Exception(f"Failed to get band details: {details['error']}")
                
                # Validate band data
                band_errors = validate_band_data(details)
                if band_errors:
                    band_data['errors'].extend(band_errors)
                    stats['band_errors'].extend(band_errors)
                
                # Process albums
                albums = []
                for album in details.get('albums', []):
                    stats['total_albums'] += 1
                    
                    try:
                        if album['url'] in processed_urls:
                            logger.warning(f"Skipping duplicate album URL: {album['url']}")
                            continue
                        processed_urls.add(album['url'])
                        
                        logger.info(f"Testing album: {album.get('title', 'Unknown')}")
                        
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
                        
                        # Rate limiting
                        time.sleep(2)
                        
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
        band_error_rate = stats['failed_bands'] / stats['total_bands'] if stats['total_bands'] > 0 else 1
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
        assert band_error_rate <= error_threshold, \
            f"Band error rate {band_error_rate:.1%} exceeds threshold {error_threshold:.1%}"
        assert album_error_rate <= error_threshold, \
            f"Album error rate {album_error_rate:.1%} exceeds threshold {error_threshold:.1%}"
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise

def test_data_consistency(scraper):
    """Test data consistency across multiple fetches."""
    # Get a random band
    band = next(scraper.get_bands_all())
    
    # Fetch details multiple times
    details1 = scraper.get_band_details(band['url'])
    time.sleep(2)  # Wait between requests
    details2 = scraper.get_band_details(band['url'])
    
    # Compare core fields
    assert details1['name'] == details2['name'], "Band name should be consistent"
    assert details1['genre'] == details2['genre'], "Genre should be consistent"
    assert len(details1['albums']) == len(details2['albums']), "Album count should be consistent"
    
    # Compare album details
    for album1, album2 in zip(details1['albums'], details2['albums']):
        assert album1['title'] == album2['title'], "Album titles should be consistent"
        assert album1['url'] == album2['url'], "Album URLs should be consistent"
        if 'year' in album1 and 'year' in album2:
            assert album1['year'] == album2['year'], "Album years should be consistent"

def test_review_validation(scraper):
    """Test validation of review data."""
    # Find a band with reviews
    for band in scraper.get_bands_all():
        details = scraper.get_band_details(band['url'])
        if not details.get('albums'):
            continue
            
        for album in details['albums']:
            album_details = scraper.get_album_details(album['url'])
            if album_details.get('reviews'):
                # Validate review structure
                for review in album_details['reviews']:
                    assert isinstance(review.get('text', ''), str), "Review text should be string"
                    if 'rating' in review:
                        assert isinstance(review['rating'], (int, float)), "Rating should be numeric"
                        assert 0 <= review['rating'] <= 5, "Rating should be between 0 and 5"
                    if 'date' in review:
                        assert isinstance(review['date'], str), "Date should be string"
                return  # Found and validated reviews
                
        time.sleep(2)  # Rate limiting

def test_error_recovery(scraper):
    """Test error recovery and retry mechanism."""
    # Test with invalid URLs
    invalid_urls = [
        "https://www.progarchives.com/notreal",
        "https://www.progarchives.com/artist.asp?id=999999",
        "https://www.progarchives.com/album.asp?id=999999",
        "malformed_url",
        ""
    ]
    
    for url in invalid_urls:
        result = scraper.get_band_details(url)
        assert 'error' in result, f"Should handle invalid URL gracefully: {url}"
        time.sleep(2)  # Rate limiting

def test_genre_handling(scraper):
    """Test genre and subgenre handling."""
    genres_found = set()
    subgenres_found = set()
    
    for band in scraper.get_bands_all():
        if len(genres_found) >= 5 and len(subgenres_found) >= 5:
            break
            
        details = scraper.get_band_details(band['url'])
        if 'genre' in details:
            genres_found.add(details['genre'])
        if 'subgenres' in details:
            subgenres_found.update(details['subgenres'])
            
        time.sleep(2)  # Rate limiting
    
    # Verify we found some genres and subgenres
    assert len(genres_found) > 0, "Should find at least one genre"
    logger.info(f"Found genres: {genres_found}")
    if subgenres_found:
        logger.info(f"Found subgenres: {subgenres_found}")

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
            
            # Remove timestamp that will naturally differ
            if 'scraped_at' in data:
                del data['scraped_at']
            
            responses.append(data)
            time.sleep(2)  # Rate limiting between fetches
        
        # Compare responses
        for i in range(1, len(responses)):
            assert responses[0] == responses[i], \
                f"Inconsistent data between fetches for {url}"

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
        
        time.sleep(2)  # Rate limiting between tests

if __name__ == '__main__':
    pytest.main([__file__, '-v'])