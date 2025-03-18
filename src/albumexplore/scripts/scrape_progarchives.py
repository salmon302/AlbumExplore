"""Script to scrape ProgArchives data ethically."""
import argparse
import json
import logging
from pathlib import Path
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn, TextColumn
from rich.logging import RichHandler
import sys
from typing import List, Dict

from albumexplore.data.scrapers.progarchives_scraper import ProgArchivesScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger("rich")

def save_json(data: List[Dict], file_path: Path) -> None:
    """Save data to JSON file with error handling."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error saving data to {file_path}: {str(e)}")

def load_json(file_path: Path) -> List[Dict]:
    """Load data from JSON file with error handling."""
    if file_path.exists():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading data from {file_path}: {str(e)}")
    return []

def deduplicate_albums(bands_data: List[Dict]) -> List[Dict]:
    """Remove duplicate albums and review entries."""
    for band in bands_data:
        if 'albums' in band:
            seen = set()
            unique_albums = []
            
            for album in band.get('albums', []):
                if 'title' not in album or 'Review this album' in album['title']:
                    continue
                    
                title = album['title'].lower().strip()
                year = album.get('year')
                key = f"{title}:{year}"
                
                if key not in seen:
                    seen.add(key)
                    unique_albums.append(album)
            
            band['albums'] = unique_albums
    
    return bands_data

def main() -> int:
    """Main entry point. Returns exit code."""
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
        default=10,
        help='Maximum number of bands to scrape'
    )
    parser.add_argument(
        '--resume-from',
        type=str,
        help='Resume from this band URL'
    )
    parser.add_argument(
        '--random-sample',
        action='store_true',
        help='Use random sampling strategy (first 5 + 5 random)'
    )
    args = parser.parse_args()

    try:
        # Create directories
        args.cache_dir.mkdir(parents=True, exist_ok=True)
        args.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize scraper
        scraper = ProgArchivesScraper(
            cache_dir=args.cache_dir,
            max_bands=args.max_bands,
            random_sample=args.random_sample
        )

        # Setup output file and load existing data if resuming
        output_file = args.output_dir / 'bands.json'
        bands_data = load_json(output_file) if args.resume_from else []
        resume = bool(args.resume_from)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            *Progress.get_default_columns(),
            TimeElapsedColumn(),
            transient=False
        ) as progress:
            # Get band list
            band_task = progress.add_task("[yellow]Getting band list...", total=None)
            bands = list(scraper.get_all_bands())
            progress.remove_task(band_task)

            # Setup progress bar for band processing
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
                    bands_data.append(band_data)

                    # Save progress regularly
                    deduplicated_data = deduplicate_albums(bands_data)
                    save_json(deduplicated_data, output_file)
                    
                except Exception as e:
                    logger.error(f"Error processing band {band['name']}: {str(e)}")
                finally:
                    progress.advance(band_task)

            # Final deduplication and stats
            bands_data = deduplicate_albums(bands_data)
            total_albums = sum(len(band.get('albums', [])) for band in bands_data)
            albums_with_lineup = sum(
                1 for band in bands_data 
                for album in band.get('albums', [])
                if album.get('lineup', [])
            )
            
            logger.info("Scraping complete!")
            logger.info(f"Processed {len(bands_data)} bands")
            logger.info(f"Total albums: {total_albums}")
            logger.info(f"Albums with lineup info: {albums_with_lineup}")

        return 0  # Success

    except KeyboardInterrupt:
        logger.info("Saving progress before exit...")
        if bands_data:
            deduplicated_data = deduplicate_albums(bands_data)
            save_json(deduplicated_data, output_file)
        return 0  # Clean exit
        
    except Exception as e:
        logger.error(f"Error during execution: {str(e)}")
        if 'bands_data' in locals() and bands_data:
            deduplicated_data = deduplicate_albums(bands_data)
            save_json(deduplicated_data, output_file)
        return 1  # Error exit

if __name__ == '__main__':
    sys.exit(main())