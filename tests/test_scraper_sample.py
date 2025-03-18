import json
import logging
from pathlib import Path
import sys

# Add src directory to Python path
src_path = Path(__file__).parent.parent / 'src'
sys.path.append(str(src_path))

from albumexplore.data.scrapers.progarchives_scraper import ProgArchivesScraper

def test_scraper_sample():
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    # Initialize scraper with cache and random sampling
    cache_dir = Path("cache/progarchives")
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    scraper = ProgArchivesScraper(
        cache_dir=cache_dir,
        max_bands=10,
        random_sample=True
    )
    
    # Collect data
    results = []
    try:
        for band in scraper.get_bands_all():
            try:
                logger.info(f"Processing band: {band.get('name', 'unknown')}")
                
                # Get full band details
                band_details = scraper.get_band_details(band['url'])
                band.update(band_details)
                results.append(band)
                
            except Exception as e:
                logger.error(f"Error processing band {band.get('name', 'unknown')}: {str(e)}")
                continue
            
        # Save results
        output_file = Path("scraper_test_results.json")
        with output_file.open('w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Results saved to {output_file}")
        
        # Basic analysis
        if results:
            total_bands = len(results)
            total_albums = sum(len(band.get('albums', [])) for band in results)
            bands_with_lineup = sum(1 for band in results 
                                if any(album.get('lineup') for album in band.get('albums', [])))
            albums_with_lineup = sum(1 for band in results 
                                   for album in band.get('albums', [])
                                   if album.get('lineup'))
            total_members = sum(len(band.get('members', [])) for band in results)
            
            logger.info(f"\nAnalysis:")
            logger.info(f"Total bands processed: {total_bands}")
            logger.info(f"Total albums found: {total_albums}")
            logger.info(f"Average albums per band: {total_albums/total_bands:.1f}")
            logger.info(f"Bands with any lineup info: {bands_with_lineup}/{total_bands}")
            logger.info(f"Albums with lineup info: {albums_with_lineup}/{total_albums}")
            logger.info(f"Total band members found: {total_members}")
            
            # Check for missing data
            for band in results:
                if not band.get('albums'):
                    logger.warning(f"No albums found for {band.get('name')}")
                if not band.get('members'):
                    logger.warning(f"No members found for {band.get('name')}")
                    
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        raise

if __name__ == '__main__':
    test_scraper_sample()