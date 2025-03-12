"""Script to ethically scrape ProgArchives data."""
import argparse
import json
import logging
from pathlib import Path
from typing import Dict, List
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn
from rich.logging import RichHandler
from ..data.scrapers.progarchives_scraper import ProgArchivesScraper

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger("rich")

def save_json(data: Dict, filepath: Path):
    """Save data to JSON file with proper encoding."""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    parser = argparse.ArgumentParser(description='Scrape ProgArchives data ethically')
    parser.add_argument(
        '--cache-dir',
        type=Path,
        default=Path('cache/progarchives'),
        help='Directory to cache downloaded pages'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('data/progarchives'),
        help='Directory to save scraped data'
    )
    parser.add_argument(
        '--max-bands',
        type=int,
        default=None,
        help='Maximum number of bands to scrape (for testing)'
    )
    parser.add_argument(
        '--resume-from',
        type=str,
        help='Resume from this band URL'
    )
    args = parser.parse_args()

    # Create directories
    args.cache_dir.mkdir(parents=True, exist_ok=True)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize scraper
    scraper = ProgArchivesScraper(cache_dir=args.cache_dir)
    resume = False
    bands_data = []
    
    try:
        # Load existing data if resuming
        output_file = args.output_dir / 'bands.json'
        if args.resume_from and output_file.exists():
            with open(output_file, 'r', encoding='utf-8') as f:
                bands_data = json.load(f)
            logger.info(f"Loaded {len(bands_data)} existing band entries")
            resume = True

        with Progress(
            SpinnerColumn(),
            *Progress.get_default_columns(),
            TimeElapsedColumn(),
            transient=False
        ) as progress:
            # Get band list
            band_task = progress.add_task("[yellow]Getting band list...", total=None)
            bands = list(scraper.get_all_bands())
            progress.update(band_task, total=len(bands))
            logger.info(f"Found {len(bands)} bands")

            # Limit bands if testing
            if args.max_bands:
                bands = bands[:args.max_bands]
                logger.info(f"Limited to {args.max_bands} bands for testing")

            # Process each band
            band_task = progress.add_task(
                "[green]Processing bands...",
                total=len(bands)
            )

            for band in bands:
                # Skip if already processed when resuming
                if resume and band['url'] == args.resume_from:
                    resume = False
                if resume:
                    progress.advance(band_task)
                    continue

                try:
                    logger.info(f"Processing {band['name']}")
                    
                    # Get band details and albums
                    details = scraper.get_band_details(band['url'])
                    if 'error' in details:
                        logger.error(f"Error processing {band['name']}: {details['error']}")
                        continue

                    # Combine band info with details
                    band_data = {**band, **details}

                    # Process each album
                    albums_with_details = []
                    for album in band_data['albums']:
                        album_details = scraper.get_album_details(album['url'])
                        if 'error' not in album_details:
                            albums_with_details.append({**album, **album_details})
                        else:
                            logger.error(f"Error processing album {album['title']}: {album_details['error']}")
                            albums_with_details.append(album)

                    band_data['albums'] = albums_with_details
                    bands_data.append(band_data)

                    # Save progress regularly
                    save_json(bands_data, output_file)
                    
                except Exception as e:
                    logger.error(f"Error processing band {band['name']}: {str(e)}")
                finally:
                    progress.advance(band_task)

        logger.info("Scraping complete!")
        logger.info(f"Processed {len(bands_data)} bands")
        
        # Calculate some statistics
        total_albums = sum(len(b['albums']) for b in bands_data)
        albums_with_lineup = sum(
            1 for b in bands_data 
            for a in b['albums'] 
            if 'lineup' in a and a['lineup']
        )
        
        logger.info(f"Total albums: {total_albums}")
        logger.info(f"Albums with lineup info: {albums_with_lineup}")

    except KeyboardInterrupt:
        logger.warning("\nScraping interrupted! Saving progress...")
        save_json(bands_data, output_file)
        logger.info("Progress saved")

if __name__ == '__main__':
    main()