"""Command line interface for ProgArchives data collection."""
import click
import logging
from pathlib import Path
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn
from rich.console import Console
from datetime import datetime

from albumexplore.data.scrapers.progarchives_scraper import ProgArchivesScraper
from albumexplore.data.importers.progarchives_importer import ProgArchivesImporter
from albumexplore.database import get_session

# Set up logging
console = Console()
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(console=console, rich_tracebacks=True)]
)
logger = logging.getLogger("progarchives")

@click.group()
def cli():
    """ProgArchives.com data collection tools."""
    pass

@cli.command()
@click.option(
    '--cache-dir',
    type=click.Path(),
    default='cache/progarchives',
    help='Directory to store cached responses'
)
@click.option(
    '--max-bands',
    type=int,
    default=None,
    help='Maximum number of bands to process'
)
@click.option(
    '--random-sample',
    is_flag=True,
    help='Use random sampling strategy'
)
@click.option(
    '--subgenres',
    multiple=True,
    help='Only process specific subgenres'
)
@click.option(
    '--skip-existing/--update-existing',
    default=True,
    help='Skip or update existing records'
)
@click.option(
    '--import/--no-import',
    'import_db',
    default=True,
    help='Import data into database'
)
def collect(
    cache_dir: str,
    max_bands: int,
    random_sample: bool,
    subgenres: tuple,
    skip_existing: bool,
    import_db: bool
):
    """Collect data from ProgArchives.com."""
    try:
        cache_path = Path(cache_dir)
        cache_path.mkdir(parents=True, exist_ok=True)
        
        scraper = ProgArchivesScraper(
            cache_dir=cache_path,
            max_bands=max_bands,
            random_sample=random_sample
        )
        
        if import_db:
            session = get_session()
            importer = ProgArchivesImporter(session, cache_dir=cache_path)
        
        stats = {
            'bands_processed': 0,
            'albums_processed': 0,
            'errors': []
        }
        
        with Progress(
            SpinnerColumn(),
            *Progress.get_default_columns(),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            # Get filtered list of bands
            band_task = progress.add_task("Getting band list...", total=None)
            bands = list(scraper.get_bands_all())
            if subgenres:
                bands = [b for b in bands if b.get('subgenre') in subgenres]
            progress.update(band_task, total=len(bands))
            
            # Process each band
            for band in bands:
                try:
                    logger.info(f"Processing {band['name']}")
                    
                    if import_db:
                        artist = importer.import_band(band['url'])
                        if artist:
                            stats['albums_processed'] += len(artist.albums)
                    else:
                        details = scraper.get_band_details(band['url'])
                        if 'error' not in details:
                            stats['albums_processed'] += len(details.get('albums', []))
                    
                    stats['bands_processed'] += 1
                    progress.update(band_task, advance=1)
                    
                except Exception as e:
                    error = f"Error processing {band['name']}: {e}"
                    logger.error(error)
                    stats['errors'].append(error)
                    
                if max_bands and stats['bands_processed'] >= max_bands:
                    break
        
        # Print summary
        console.print("\n[bold]Collection Summary[/bold]")
        console.print(f"Bands processed: {stats['bands_processed']}")
        console.print(f"Albums processed: {stats['albums_processed']}")
        if stats['errors']:
            console.print(f"\nErrors encountered: {len(stats['errors'])}")
            for error in stats['errors']:
                console.print(f"  - {error}")
                
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise click.Abort()

@cli.command()
@click.argument('url')
@click.option(
    '--cache-dir',
    type=click.Path(),
    default='cache/progarchives',
    help='Directory to store cached responses'
)
@click.option(
    '--import/--no-import',
    'import_db',
    default=True,
    help='Import data into database'
)
def album(url: str, cache_dir: str, import_db: bool):
    """Process a single album URL."""
    try:
        cache_path = Path(cache_dir)
        cache_path.mkdir(parents=True, exist_ok=True)
        
        scraper = ProgArchivesScraper(cache_dir=cache_path)
        
        with console.status("Processing album..."):
            if import_db:
                session = get_session()
                importer = ProgArchivesImporter(session, cache_dir=cache_path)
                album = importer.import_album(url)
                if album:
                    console.print(f"Successfully imported: {album.title}")
                else:
                    console.print("Failed to import album", style="red")
                    raise click.Abort()
            else:
                details = scraper.get_album_details(url)
                if 'error' not in details:
                    console.print(details)
                else:
                    console.print(f"Error: {details['error']}", style="red")
                    raise click.Abort()
                    
    except Exception as e:
        logger.error(f"Error: {e}")
        raise click.Abort()

@cli.command()
@click.argument('url')
@click.option(
    '--cache-dir',
    type=click.Path(),
    default='cache/progarchives',
    help='Directory to store cached responses'
)
@click.option(
    '--import/--no-import',
    'import_db',
    default=True,
    help='Import data into database'
)
@click.option(
    '--skip-albums',
    is_flag=True,
    help="Don't process band's albums"
)
def band(url: str, cache_dir: str, import_db: bool, skip_albums: bool):
    """Process a single band URL."""
    try:
        cache_path = Path(cache_dir)
        cache_path.mkdir(parents=True, exist_ok=True)
        
        scraper = ProgArchivesScraper(cache_dir=cache_path)
        
        with console.status("Processing band..."):
            if import_db:
                session = get_session()
                importer = ProgArchivesImporter(session, cache_dir=cache_path)
                artist = importer.import_band(url)
                if artist:
                    console.print(f"Successfully imported: {artist.name}")
                    if not skip_albums:
                        console.print(f"Imported {len(artist.albums)} albums")
                else:
                    console.print("Failed to import band", style="red")
                    raise click.Abort()
            else:
                details = scraper.get_band_details(url)
                if 'error' not in details:
                    if skip_albums:
                        details.pop('albums', None)
                    console.print(details)
                else:
                    console.print(f"Error: {details['error']}", style="red")
                    raise click.Abort()
                    
    except Exception as e:
        logger.error(f"Error: {e}")
        raise click.Abort()

if __name__ == '__main__':
    cli()