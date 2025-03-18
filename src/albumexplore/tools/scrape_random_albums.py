"""Script to scrape random albums from ProgArchives.com."""
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
from albumexplore.data.scrapers.progarchives_scraper import ProgArchivesScraper

def save_results(albums: List[Dict], output_file: Path):
    """Save scraped album data to JSON file."""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(albums, f, indent=2, ensure_ascii=False)

def setup_logging(log_file: Path, verbose: bool = False):
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

def validate_html_structure(scraper: ProgArchivesScraper, html: str) -> bool:
    """Validate the HTML structure before processing."""
    if not html:
        return False
    return True  # Basic validation - can be enhanced with more specific checks

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Scrape random albums from ProgArchives')
    parser.add_argument('--max-bands', type=int, default=10,
                       help='Maximum number of bands to scrape (default: 10)')
    parser.add_argument('--cache-dir', type=Path,
                       help='Cache directory path (default: ./cache/progarchives)')
    parser.add_argument('--output-dir', type=Path,
                       help='Output directory path (default: ./data/progarchives)')
    parser.add_argument('--log-dir', type=Path,
                       help='Log directory path (default: ./logs)')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Enable verbose debug logging')
    parser.add_argument('--validate-html', action='store_true',
                       help='Validate HTML structure before processing')
    return parser.parse_args()

def main():
    """Run the scraper on random albums."""
    args = parse_args()
    
    # Set up paths
    output_dir = Path(".")
    cache_dir = Path("cache/progarchives")
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    # Set up logging
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = Path("logs") / f"random_discographies_{timestamp}.log"
    setup_logging(log_file, args.verbose)
    logger = logging.getLogger(__name__)
    
    try:
        scraper = ProgArchivesScraper(
            cache_dir=cache_dir,
            max_bands=args.max_bands,
            random_sample=True
        )
        
        # Track statistics
        stats = {
            'processed_bands': 0,
            'successful_bands': 0,
            'failed_bands': 0,
            'processed_albums': 0,
            'successful_albums': 0,
            'failed_albums': 0,
            'errors': []
        }
        
        all_albums = []
        processed_bands = set()
        
        try:
            # First try to get all bands
            logger.info("Fetching band list...")
            try:
                # Get initial band list
                bands = list(scraper.get_bands_all())  # Changed from get_all_bands to get_bands_all
                if not bands:
                    # Try backup method
                    logger.warning("Main band list retrieval failed, trying alternative method...")
                    bands = list(scraper.get_bands_all())
                
                if not bands:
                    logger.error("Could not retrieve any bands using any method")
                    return
                    
            except Exception as e:
                logger.error(f"Error retrieving band list: {str(e)}", exc_info=True)
                return
            
            logger.info(f"Found {len(bands)} bands total")
            
            for band in bands:
                if not band or not band.get('url'):
                    logger.warning("Skipping invalid band entry")
                    continue
                    
                if stats['processed_bands'] >= args.max_bands:
                    logger.info(f"Reached maximum number of bands ({args.max_bands})")
                    break
                
                stats['processed_bands'] += 1
                
                # Skip if we've seen this band before
                band_url = band.get('url', '')
                if band_url in processed_bands:
                    logger.debug(f"Skipping already processed band: {band['name']}")
                    continue
                    
                processed_bands.add(band_url)
                
                logger.info(f"Processing band {stats['processed_bands']}/{args.max_bands}: {band['name']} ({band.get('country', 'Unknown')})")
                
                try:
                    # Get band details including albums
                    band_details = scraper.get_band_details(band_url)
                    if 'error' in band_details:
                        error_msg = f"Error getting details for {band['name']}: {band_details['error']}"
                        logger.error(error_msg)
                        stats['errors'].append(error_msg)
                        stats['failed_bands'] += 1
                        continue
                    
                    logger.info(f"Found {len(band_details.get('albums', []))} albums for {band['name']}")
                    stats['successful_bands'] += 1
                    
                    # Process each album
                    band_albums = []
                    for album in band_details.get('albums', []):
                        stats['processed_albums'] += 1
                        logger.debug(f"Processing album {stats['processed_albums']}: {album.get('title', 'Unknown')} by {band['name']}")
                        
                        try:
                            # Validate album has required data
                            if not album or 'url' not in album:
                                logger.warning(f"Skipping invalid album entry for band {band['name']}")
                                continue
                            
                            # Get detailed album info including lineup
                            album_details = scraper.get_album_details(album['url'])
                            if not album_details or 'error' in album_details:
                                error_msg = f"Error getting album details for {album.get('title', 'Unknown')}: {album_details.get('error', 'Unknown error')}"
                                logger.error(error_msg)
                                stats['errors'].append(error_msg)
                                stats['failed_albums'] += 1
                                continue
                                
                            # Merge album info
                            album.update(album_details)
                            
                            # Add band info
                            album['band_name'] = band['name']
                            album['band_url'] = band_url
                            album['band_genre'] = band.get('genre', '')
                            album['band_country'] = band.get('country', '')
                            
                            band_albums.append(album)
                            stats['successful_albums'] += 1
                            logger.debug(f"Successfully processed album: {album['title']} by {band['name']} ({album.get('year', 'Unknown')})")
                            
                        except Exception as e:
                            error_msg = f"Error processing album {album.get('title', 'Unknown')}: {str(e)}"
                            logger.error(error_msg, exc_info=True)
                            stats['errors'].append(error_msg)
                            stats['failed_albums'] += 1
                            continue
                    
                    all_albums.extend(band_albums)
                    logger.info(f"Processed {len(band_albums)} albums for {band['name']}")
                    
                except Exception as e:
                    error_msg = f"Error processing band {band['name']}: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    stats['errors'].append(error_msg)
                    stats['failed_bands'] += 1
                    continue
            
            # Save results and stats
            if all_albums:
                # Save album data
                output_file = output_dir / f"test_results_random_{timestamp}.json"
                save_results(all_albums, output_file)
                logger.info(f"Saved {len(all_albums)} albums to {output_file}")
                
                # Save statistics
                stats_file = output_dir / f"stats_random_{timestamp}.json"
                with open(stats_file, 'w', encoding='utf-8') as f:
                    json.dump(stats, f, indent=2)
                logger.info(f"Saved scraping statistics to {stats_file}")
                
                # Log summary
                logger.info("Scraping completed successfully")
                logger.info(f"Processed {stats['processed_bands']} bands ({stats['successful_bands']} successful, {stats['failed_bands']} failed)")
                logger.info(f"Processed {stats['processed_albums']} albums ({stats['successful_albums']} successful, {stats['failed_albums']} failed)")
                if stats['errors']:
                    logger.info(f"Encountered {len(stats['errors'])} errors")
            else:
                logger.error("No albums were successfully scraped")
                
        except Exception as e:
            logger.error(f"Fatal error during scraping: {str(e)}", exc_info=True)
            raise
            
    except Exception as e:
        logger.error(f"Error initializing scraper: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    import argparse
    main()