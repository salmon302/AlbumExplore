"""Test script for random discography scraping."""
import json
import logging
from pathlib import Path
from datetime import datetime
from albumexplore.data.scrapers.progarchives_scraper import ProgArchivesScraper

def main():
    # Set up logging
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f'random_discographies_test.log'),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)

    # Initialize scraper with cache
    cache_dir = Path("cache/progarchives")
    cache_dir.mkdir(parents=True, exist_ok=True)

    scraper = ProgArchivesScraper(
        cache_dir=cache_dir,
        max_bands=5,  # Test with 5 bands
        random_sample=True
    )

    results = []
    stats = {
        'total_bands': 0,
        'total_albums': 0,
        'albums_with_lineup': 0,
        'total_members': 0,
        'genres': set(),
        'countries': set(),
        'years': set()
    }

    logger.info("Starting random discography test...")

    try:
        for band in scraper.get_bands_all():
            stats['total_bands'] += 1
            logger.info(f"Processing band {stats['total_bands']}: {band['name']}")

            # Get full band details
            band_details = scraper.get_band_details(band['url'])
            band.update(band_details)

            # Collect statistics
            if 'albums' in band:
                band_albums = []
                for album in band['albums']:
                    try:
                        album_details = scraper.get_album_details(album['url'])
                        if album_details:
                            album.update(album_details)
                            stats['total_albums'] += 1
                            if album.get('lineup'):
                                stats['albums_with_lineup'] += 1
                            if album.get('year'):
                                stats['years'].add(album['year'])
                            band_albums.append(album)
                    except Exception as e:
                        logger.error(f"Error processing album {album.get('title', 'unknown')}: {e}")
                band['albums'] = band_albums

            if band.get('genre'):
                stats['genres'].add(band['genre'])
            if band.get('country'):
                stats['countries'].add(band['country'])
            if band.get('members'):
                stats['total_members'] += len(band['members'])

            results.append(band)

        # Save results
        output_file = Path(f"test_results_random_{timestamp}.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        # Print analysis
        logger.info("\nScraping Analysis:")
        logger.info(f"Total bands processed: {stats['total_bands']}")
        logger.info(f"Total albums found: {stats['total_albums']}")
        logger.info(f"Albums with lineup info: {stats['albums_with_lineup']}")
        logger.info(f"Total band members: {stats['total_members']}")
        logger.info(f"Unique genres: {', '.join(sorted(stats['genres']))}")
        logger.info(f"Countries represented: {', '.join(sorted(stats['countries']))}")
        logger.info(f"Year range: {min(stats['years'])} - {max(stats['years'])}")
        logger.info(f"\nResults saved to {output_file}")

    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        raise

if __name__ == '__main__':
    main()