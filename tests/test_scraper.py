"""Test script for ProgArchives scraper."""
import json
import logging
from pathlib import Path
from albumexplore.data.scrapers.progarchives_scraper import ProgArchivesScraper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Run scraping test on a sample of bands."""
    # Set up cache directory for testing
    cache_dir = Path(__file__).parent.parent / "cache" / "progarchives"
    
    # Initialize scraper with small test sample
    scraper = ProgArchivesScraper(cache_dir=cache_dir, max_bands=10)
    
    results = []
    total_albums = 0
    total_members = 0
    bands_with_lineup = 0
    albums_with_lineup = 0
    
    # Process each band
    for band in scraper.get_bands_all():
        logger.info(f"Processing band: {band['name']}")
        details = scraper.get_band_details(band['url'])
        
        if 'error' not in details:
            # Track statistics
            num_albums = len(details.get('albums', []))
            total_albums += num_albums
            total_members += len(details.get('members', []))
            
            # Check for valid lineup info
            if details.get('members'):
                bands_with_lineup += 1
            
            for album in details.get('albums', []):
                if album.get('lineup'):
                    albums_with_lineup += 1
            
            results.append({
                'name': band['name'],
                'url': band['url'],
                'num_albums': num_albums,
                'num_members': len(details.get('members', [])),
                'albums_with_lineup': sum(1 for a in details.get('albums', []) if a.get('lineup'))
            })
    
    # Save results
    with open('scraper_test_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    # Print analysis
    logger.info("\nAnalysis:")
    logger.info(f"Total bands processed: {len(results)}")
    logger.info(f"Total albums found: {total_albums}")
    logger.info(f"Average albums per band: {total_albums/len(results) if results else 0:.1f}")
    logger.info(f"Bands with any lineup info: {bands_with_lineup}/{len(results)}")
    logger.info(f"Albums with lineup info: {albums_with_lineup}/{total_albums}")
    logger.info(f"Total band members found: {total_members}")

if __name__ == "__main__":
    main()