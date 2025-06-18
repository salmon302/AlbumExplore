"""Command line interface for ProgArchives local file parser."""
import click
import json
from pathlib import Path
from ..scraping.progarchives_scraper import ProgArchivesScraper
from ..data.importers.progarchives_importer import ProgArchivesImporter
from ..database import get_session
import logging
import glob

logger = logging.getLogger(__name__)

@click.group()
def cli():
    """ProgArchives.com local data processing tools."""
    pass

@cli.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output JSON file path')
@click.option('--no-cache', is_flag=True, help='Disable cache usage')
@click.option('--import-db', is_flag=True, help='Import data into database')
def process_album(file_path: str, output: str, no_cache: bool, import_db: bool):
    """Process album data from a local ProgArchives.com album HTML file."""
    try:
        scraper = ProgArchivesScraper()
        album_path = Path(file_path)
        data = scraper.get_album_data(album_path, use_cache=not no_cache)
        
        if data and 'error' not in data:
            if import_db:
                session = get_session()
                importer = ProgArchivesImporter(session)
                album = importer.import_album_from_data(data)
                if album:
                    click.echo(f"Successfully imported album '{album.title}' to database")
                else:
                    click.echo("Failed to import album to database", err=True)
                    exit(1)

            if output:
                output_path = Path(output)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w') as f:
                    json.dump(data, f, indent=2)
                click.echo(f"Data saved to {output}")
            else:
                click.echo(json.dumps(data, indent=2))
        else:
            error_msg = data.get('error', 'Failed to process album data')
            click.echo(f"Error: {error_msg}", err=True)
            exit(1)
            
    except Exception as e:
        logger.error(f"Error: {e}")
        click.echo(f"Error: {e}", err=True)
        exit(1)

@cli.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output JSON file path')
@click.option('--no-cache', is_flag=True, help='Disable cache usage')
@click.option('--import-db', is_flag=True, help='Import data into database')
def process_artist(file_path: str, output: str, no_cache: bool, import_db: bool):
    """Process artist data from a local ProgArchives.com artist HTML file."""
    try:
        scraper = ProgArchivesScraper()
        artist_path = Path(file_path)
        data = scraper.get_band_details(artist_path, use_cache=not no_cache)
        
        if data and 'error' not in data:
            if import_db:
                session = get_session()
                importer = ProgArchivesImporter(session)
                artist = importer.import_artist_from_data(data)
                if artist:
                    click.echo(f"Successfully imported artist '{artist.name}' to database")
                else:
                    click.echo("Failed to import artist to database", err=True)
                    exit(1)

            if output:
                output_path = Path(output)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w') as f:
                    json.dump(data, f, indent=2)
                click.echo(f"Data saved to {output}")
            else:
                click.echo(json.dumps(data, indent=2))
        else:
            error_msg = data.get('error', 'Failed to process artist data')
            click.echo(f"Error: {error_msg}", err=True)
            exit(1)
            
    except Exception as e:
        logger.error(f"Error: {e}")
        click.echo(f"Error: {e}", err=True)
        exit(1)

@cli.command()
@click.argument('directory', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option('--pattern', default='*.html', help='File pattern to match (default: *.html)')
@click.option('--album-dir', help='Subdirectory for album files (e.g. "albums")')
@click.option('--artist-dir', help='Subdirectory for artist files (e.g. "artists")')
@click.option('--output-dir', type=click.Path(), help='Directory to save processed JSON files')
@click.option('--import-db', is_flag=True, help='Import data into database')
@click.option('--no-cache', is_flag=True, help='Disable cache usage')
@click.option('--limit', type=int, help='Maximum number of files to process')
def import_local_dump(directory: str, pattern: str, album_dir: str, artist_dir: str, 
                      output_dir: str, import_db: bool, no_cache: bool, limit: int):
    """Bulk process local ProgArchives HTML files."""
    try:
        base_dir = Path(directory)
        output_base = Path(output_dir) if output_dir else None
        if output_base:
            output_base.mkdir(parents=True, exist_ok=True)
        
        scraper = ProgArchivesScraper(local_data_root=base_dir)
        
        # Process album files
        album_files = []
        if album_dir:
            album_path = base_dir / album_dir
            if album_path.exists():
                pattern_path = str(album_path / pattern)
                album_files = list(glob.glob(pattern_path))
                logger.info(f"Found {len(album_files)} album files in {album_path}")
        
        # Process artist files
        artist_files = []
        if artist_dir:
            artist_path = base_dir / artist_dir
            if artist_path.exists():
                pattern_path = str(artist_path / pattern)
                artist_files = list(glob.glob(pattern_path))
                logger.info(f"Found {len(artist_files)} artist files in {artist_path}")
        
        # Apply limit if specified
        if limit:
            if album_files:
                album_files = album_files[:min(limit, len(album_files))]
            if artist_files:
                artist_files = artist_files[:min(limit, len(artist_files))]
        
        # Set up database session if importing
        session = None
        importer = None
        if import_db:
            session = get_session()
            importer = ProgArchivesImporter(session)
        
        # Process albums
        albums_processed = 0
        albums_failed = 0
        if album_files:
            with click.progressbar(album_files, label='Processing albums') as bar:
                for album_file in bar:
                    try:
                        file_path = Path(album_file)
                        data = scraper.get_album_data(file_path, use_cache=not no_cache)
                        
                        if data and 'error' not in data:
                            # Save to output directory
                            if output_base:
                                output_file = output_base / 'albums' / f"{file_path.stem}.json"
                                output_file.parent.mkdir(parents=True, exist_ok=True)
                                with open(output_file, 'w') as f:
                                    json.dump(data, f, indent=2)
                            
                            # Import to database
                            if import_db and importer:
                                album = importer.import_album_from_data(data)
                                if not album:
                                    logger.warning(f"Failed to import album from {file_path}")
                            
                            albums_processed += 1
                        else:
                            logger.warning(f"Failed to process album file {file_path}")
                            albums_failed += 1
                    except Exception as e:
                        logger.error(f"Error processing {album_file}: {e}")
                        albums_failed += 1
        
        # Process artists
        artists_processed = 0
        artists_failed = 0
        if artist_files:
            with click.progressbar(artist_files, label='Processing artists') as bar:
                for artist_file in bar:
                    try:
                        file_path = Path(artist_file)
                        data = scraper.get_band_details(file_path, use_cache=not no_cache)
                        
                        if data and 'error' not in data:
                            # Save to output directory
                            if output_base:
                                output_file = output_base / 'artists' / f"{file_path.stem}.json"
                                output_file.parent.mkdir(parents=True, exist_ok=True)
                                with open(output_file, 'w') as f:
                                    json.dump(data, f, indent=2)
                            
                            # Import to database
                            if import_db and importer:
                                artist = importer.import_artist_from_data(data)
                                if not artist:
                                    logger.warning(f"Failed to import artist from {file_path}")
                            
                            artists_processed += 1
                        else:
                            logger.warning(f"Failed to process artist file {file_path}")
                            artists_failed += 1
                    except Exception as e:
                        logger.error(f"Error processing {artist_file}: {e}")
                        artists_failed += 1
        
        # Print summary
        click.echo(f"Processing complete: "
                 f"{albums_processed} albums processed, {albums_failed} albums failed, "
                 f"{artists_processed} artists processed, {artists_failed} artists failed")
        
        if albums_failed > 0 or artists_failed > 0:
            exit(1)
            
    except Exception as e:
        logger.error(f"Error: {e}")
        click.echo(f"Error: {e}", err=True)
        exit(1)

if __name__ == '__main__':
    cli()