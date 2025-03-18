"""Standalone test script for random ProgArchives discographies."""
import sys
from pathlib import Path
import logging
import json
import random
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional

# Add src to path
src_path = Path(__file__).parent.parent / 'src'
sys.path.append(str(src_path))

# Direct import of scraper to avoid package initialization
from albumexplore.scraping.progarchives_scraper import ProgArchivesScraper

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('random_discographies_test.log')
    ]
)
logger = logging.getLogger(__name__)

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

def main():
    """Run random discography tests."""
    # Configuration
    test_bands = 5  # Number of random bands to test
    error_threshold = 0.2  # Maximum acceptable error rate (20%)
    min_albums = 3  # Minimum albums a band should have
    
    # Initialize scraper
    cache_dir = Path("cache/progarchives/test_random")
    cache_dir.mkdir(parents=True, exist_ok=True)
    scraper = ProgArchivesScraper(cache_dir=cache_dir)
    
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
        'start_time': datetime.now().isoformat()
    }
    
    try:
        # Get list of bands
        logger.info("Getting band list...")
        all_bands = list(scraper.get_bands_all())
        logger.info(f"Found {len(all_bands)} total bands")
        
        # Filter bands with minimum albums and shuffle
        filtered_bands = [band for band in all_bands]  # We'll check album count later
        random.shuffle(filtered_bands)
        
        test_data = []
        processed_urls = set()
        
        # Process random selection
        for band in filtered_bands:
            if stats['total_bands'] >= test_bands:
                break
                
            stats['total_bands'] += 1
            band_data = {'name': band['name'], 'url': band['url'], 'errors': []}
            
            try:
                logger.info(f"\nTesting band: {band['name']}")
                
                # Get band details
                details = scraper.get_band_details(band['url'])
                if 'error' in details:
                    raise Exception(f"Failed to get band details: {details['error']}")
                
                # Skip if not enough albums
                if len(details.get('albums', [])) < min_albums:
                    logger.info(f"Skipping {band['name']} - only {len(details.get('albums', []))} albums")
                    stats['total_bands'] -= 1  # Don't count in stats
                    continue
                
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
        band_error_rate = stats['failed_bands'] / stats['total_bands'] if stats['total_bands'] > 0 else 1
        album_error_rate = stats['failed_albums'] / stats['total_albums'] if stats['total_albums'] > 0 else 1
        
        # Save test results
        results = {
            'test_date': datetime.now().isoformat(),
            'duration': str(datetime.now() - datetime.fromisoformat(stats['start_time'])),
            'configuration': {
                'test_bands': test_bands,
                'min_albums': min_albums,
                'error_threshold': error_threshold
            },
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
        
        # Check error rates
        success = True
        if band_error_rate > error_threshold:
            logger.error(f"Band error rate {band_error_rate:.1%} exceeds threshold {error_threshold:.1%}")
            success = False
        if album_error_rate > error_threshold:
            logger.error(f"Album error rate {album_error_rate:.1%} exceeds threshold {error_threshold:.1%}")
            success = False
            
        return 0 if success else 1
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        return 1

if __name__ == '__main__':
    sys.exit(main())